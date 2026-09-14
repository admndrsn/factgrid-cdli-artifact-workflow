#!/usr/bin/env python3
"""Create or update CDLI artifact items in FactGrid.

This is a FactGrid-target companion to the TokenWorks CDLI artifact writers.
It reads the same local CDLI artifact staging and statement staging files, but
uses the `fg_pid` and FactGrid QID values from the statement plan.

The script is intentionally resumable:

- dry-run by default;
- `--write` is required for API changes;
- previous `written` rows in the results CSV are skipped;
- `--limit` keeps batches small enough for polite API use.
"""

from __future__ import annotations

import argparse
import getpass
import logging
import os
import re
import time
import unicodedata
from pathlib import Path

import pandas as pd
import requests
from tenacity import RetryError, retry, retry_if_exception, stop_after_attempt, wait_exponential
from tqdm.auto import tqdm
from wikibaseintegrator import WikibaseIntegrator, datatypes
from wikibaseintegrator.models import Qualifiers
from wikibaseintegrator.wbi_config import config
from wikibaseintegrator.wbi_enums import ActionIfExists
from wikibaseintegrator.wbi_login import Login

from write_cdli_new_artifact_items import alias_values, artifact_label_for, clean, description_for, format_cdli_id


WORKFLOW_ROOT = Path(__file__).resolve().parents[1]
PILOT_ROOT = WORKFLOW_ROOT / "published" / "pilots"
DEFAULT_ARTIFACTS = PILOT_ROOT / "cdli_artifact_staging_tranche_10001_35000.csv"
DEFAULT_STATEMENTS = PILOT_ROOT / "cdli_artifact_statement_staging_tranche_10001_35000.csv"
DEFAULT_FACTGRID_CDLI = WORKFLOW_ROOT / "inputs" / "factgrid_tablet_sources" / "FG_CDLI_ID.csv"
DEFAULT_PRIOR_FACTGRID_QID_LOOKUPS = (
    WORKFLOW_ROOT / "inputs" / "factgrid_tablet_sources" / "FG_OA_Published_prior_qid_lookup.csv",
    WORKFLOW_ROOT / "inputs" / "factgrid_tablet_sources" / "factgrid_existing_live_cdli_lookup.csv",
)
DEFAULT_FACTGRID_UPLOAD_TABLE = Path("/Users/aa/Documents/FactGrid/FactgridCuneiform/_upload2FG/working_factgrid_df.csv")
DEFAULT_RESULTS = PILOT_ROOT / "factgrid_cdli_artifact_write_results_tranche_10001_35000.csv"
DEFAULT_PLAN = PILOT_ROOT / "factgrid_cdli_artifact_write_plan_tranche_10001_35000.csv"
DEFAULT_COLLECTION_MATCHES = WORKFLOW_ROOT / "published" / "factgrid_museum_staging" / "cdli_missing_museums_factgrid_match_review.csv"
DEFAULT_REUSE_POOL = PILOT_ROOT / "factgrid_cdli_artifact_qid_reuse_pool.csv"
FACTGRID_API = "https://database.factgrid.de/w/api.php"
FACTGRID_CDLI_ID_PROPERTY = "P692"
FACTGRID_INVENTORY_NUMBER_FIELD = "inventory_number"
FACTGRID_INVENTORY_NUMBER_QUALIFIER_PROPERTY = "P10"
FACTGRID_FINDING_SPOT_CONTEXT_FIELD = "finding_spot_context"
FACTGRID_PRESENT_HOLDING_PROPERTY = "P329"
FACTGRID_RESEARCH_PROJECT_PROPERTY = "P131"
TOKENWORKS_FACTGRID_QID = "Q1894741"
DEFAULT_RESEARCH_PROJECT_QIDS = ",".join([TOKENWORKS_FACTGRID_QID, "Q389597", "Q393513"])
FACTGRID_OBJECT_TYPE_INSTANCE_OF = {
    "amulet": ("Q1083363", "Amulet"),
    "barrel": ("Q512054", "Clay barrel"),
    "block": ("Q512055", "Clay block"),
    "brick": ("Q512056", "Clay brick"),
    "bulla": ("Q512057", "Clay bulla"),
    "cone": ("Q512058", "Clay cone"),
    "cylinder": ("Q512059", "Clay cylinder"),
    "docket": ("Q512060", "Clay docket"),
    "envelope": ("Q512061", "Clay envelope"),
    "lentil": ("Q512062", "Clay lentil tablet"),
    "prism": ("Q512063", "Clay prism"),
    "prismatic cylinder": ("Q512064", "Clay prismatic cylinder"),
    "seal": ("Q512065", "seal"),
    "sealing": ("Q512066", "Clay sealing"),
    "tablet": ("Q512006", "Clay tablet"),
    "tag": ("Q512067", "Clay tag"),
    "vase": ("Q512068", "Clay vase"),
    "vessel": ("Q512069", "Clay vessel"),
    "cylinder seal": ("Q512065", "seal"),
    "seal (not impression)": ("Q512065", "seal"),
    "stamp seal": ("Q512065", "seal"),
}


def read_csv(path: str | Path) -> pd.DataFrame:
    if not path:
        return pd.DataFrame()
    p = Path(path)
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p, dtype=str, low_memory=False).fillna("")


def qid_from_uri(value: object) -> str:
    text = clean(value)
    match = re.search(r"(Q\d+)$", text)
    return match.group(1) if match else text


def qid_number(qid: object) -> int:
    match = re.fullmatch(r"Q(\d+)", clean(qid))
    return int(match.group(1)) if match else 10**18


def set_lowest_qid(out: dict[str, str], key: str, qid: str) -> None:
    if not key or not re.fullmatch(r"Q\d+", qid):
        return
    current = out.get(key, "")
    if not current or qid_number(qid) < qid_number(current):
        out[key] = qid


def cdli_keys(value: object) -> set[str]:
    text = clean(value)
    if not text:
        return set()
    normalized = format_cdli_id(text)
    digits = re.sub(r"\D+", "", text)
    return {v for v in {text, normalized, digits} if v}


def normalize_object_type(value: object) -> str:
    return re.sub(r"\s+", " ", clean(value).casefold())


def normalize(value: object) -> str:
    text = unicodedata.normalize("NFKD", clean(value))
    text = text.encode("ascii", "ignore").decode("ascii").casefold()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def split_pipe_values(value: object) -> list[str]:
    return [clean(part) for part in clean(value).split("|") if clean(part)]


def parse_qid_list(value: object) -> list[str]:
    qids: list[str] = []
    for part in re.split(r"[,;|\s]+", clean(value)):
        if re.fullmatch(r"Q\d+", part) and part not in qids:
            qids.append(part)
    return qids


def load_existing_factgrid_qids(path: Path) -> dict[str, str]:
    df = read_csv(path)
    if df.empty:
        return {}
    lowered = {c.casefold(): c for c in df.columns}
    cdli_col = lowered.get("cdli_id") or lowered.get("p692") or lowered.get("cdli")
    qid_col = lowered.get("clay_tablet") or lowered.get("factgrid_qid") or lowered.get("qid")
    if not cdli_col or not qid_col:
        return {}
    out: dict[str, str] = {}
    for _, row in df.iterrows():
        qid = qid_from_uri(row.get(qid_col))
        if not qid:
            continue
        for key in cdli_keys(row.get(cdli_col)):
            set_lowest_qid(out, key, qid)
    return out


def load_prior_factgrid_qid_lookups(paths: list[Path]) -> dict[str, str]:
    out: dict[str, str] = {}
    for path in paths:
        df = read_csv(path)
        if df.empty:
            continue
        required = {"match_key_type", "match_key", "factgrid_qid"}
        if not required.issubset(df.columns):
            continue
        for _, row in df.iterrows():
            qid = clean(row.get("factgrid_qid"))
            match_key_type = clean(row.get("match_key_type"))
            if match_key_type == "cdli_id":
                for key in cdli_keys(row.get("match_key")):
                    set_lowest_qid(out, key, qid)
            elif match_key_type == "label_or_alias":
                set_lowest_qid(out, normalize(row.get("match_key")), qid)
    return out


def load_written_result_qids(path: Path) -> dict[str, str]:
    df = read_csv(path)
    if df.empty or not {"cdli_id", "factgrid_qid", "write_status"}.issubset(df.columns):
        return {}
    out: dict[str, str] = {}
    rows = df[df["write_status"].eq("written")].copy()
    for _, row in rows.iterrows():
        qid = clean(row.get("factgrid_qid"))
        if not re.fullmatch(r"Q\d+", qid):
            continue
        for key in cdli_keys(row.get("cdli_id")):
            set_lowest_qid(out, key, qid)
    if "label_collision_qid" in df.columns:
        collision_rows = df[df["write_status"].eq("label_collision")].copy()
        for _, row in collision_rows.iterrows():
            qid = clean(row.get("label_collision_qid"))
            if not re.fullmatch(r"Q\d+", qid):
                continue
            for key in cdli_keys(row.get("cdli_id")):
                set_lowest_qid(out, key, qid)
    return out


def merge_existing_qid_maps(*maps: dict[str, str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for mapping in maps:
        for key, qid in mapping.items():
            set_lowest_qid(out, key, qid)
    return out


def load_collection_matches(path: Path) -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]]]:
    df = read_csv(path)
    if df.empty or "factgrid_qid" not in df.columns:
        return {}, {}
    by_cdli_id: dict[str, dict[str, str]] = {}
    by_name: dict[str, dict[str, str]] = {}
    for _, row in df.iterrows():
        qid = clean(row.get("factgrid_qid"))
        if not re.fullmatch(r"Q\d+", qid):
            continue
        record = {
            "factgrid_qid": qid,
            "factgrid_label": clean(row.get("factgrid_label")) or clean(row.get("collection_label")),
        }
        cdli_collection_id = clean(row.get("cdli_collection_id"))
        if cdli_collection_id:
            by_cdli_id.setdefault(cdli_collection_id, record)
        for column in ["collection_label", "collection", "best_cdli_match"]:
            key = normalize(row.get(column))
            if key:
                by_name.setdefault(key, record)
    return by_cdli_id, by_name


def load_available_reuse_qids(
    path: Path,
    results: pd.DataFrame,
    allow_hold: bool = False,
    allow_unapproved: bool = False,
) -> list[str]:
    df = read_csv(path)
    if df.empty or "qid_available_for_future_entity" not in df.columns:
        return []
    if "reuse_pool_status" in df.columns:
        allowed_status = {"candidate"}
        if allow_hold:
            allowed_status.add("hold_until_canonical_repair")
        df = df[df["reuse_pool_status"].isin(allowed_status)].copy()
    if "future_reuse_status" in df.columns and not allow_unapproved:
        approved = {"approved", "approved_for_reuse", "yes", "y"}
        df = df[df["future_reuse_status"].map(clean).str.casefold().isin(approved)].copy()
    used: set[str] = set()
    if not results.empty and {"factgrid_qid", "write_status", "write_action"}.issubset(results.columns):
        used = set(
            results.loc[
                results["write_status"].isin(["written", "rewrite_ambiguous"])
                & results["write_action"].eq("rewrite"),
                "factgrid_qid",
            ].map(clean)
        )
    qids = []
    for qid in df["qid_available_for_future_entity"].map(clean):
        if re.fullmatch(r"Q\d+", qid) and qid not in used and qid not in qids:
            qids.append(qid)
    return qids


def load_factgrid_upload_overrides(path: Path) -> dict[str, dict[str, str]]:
    df = read_csv(path)
    if df.empty:
        return {}
    field_columns = {
        "cdli_id": "cdli",
        "instance_of": "obj type",
        "language": "lang",
        "material": "material",
        "present_holding": "collection",
        "inventory_number": "inventory number",
        "finding_spot": "finding spot",
        "finding_spot_context": "inventory number.1",
        "type_of_work": "genre",
        "period": "period",
    }
    if not all(col in df.columns for col in ["cdli", "period"]):
        return {}
    out: dict[str, dict[str, str]] = {}
    for _, row in df.iterrows():
        cdli = clean(row.get("cdli"))
        if not cdli or cdli.casefold() == "p692":
            continue
        values: dict[str, str] = {}
        for field_name, column in field_columns.items():
            if column in df.columns:
                values[field_name] = clean(row.get(column))
        for key in cdli_keys(cdli):
            out.setdefault(key, values)
    return out


def api_login() -> WikibaseIntegrator:
    username = os.environ.get("FG_USER") or input("FactGrid username: ")
    password = os.environ.get("FG_PASS") or getpass.getpass("FactGrid password: ")
    config["MEDIAWIKI_API_URL"] = FACTGRID_API
    config["PROPERTY_CONSTRAINTS_CHECK"] = False
    logging.getLogger("backoff").setLevel(logging.ERROR)
    try:
        login = Login(user=username, password=password, mediawiki_api_url=FACTGRID_API)
    except Exception as exc:
        detail = f"{type(exc).__name__}: {exc}"
        detail = detail.replace(password, "[redacted]") if password else detail
        raise RuntimeError(f"FactGrid login failed. Underlying error: {detail[:500]}") from None
    return WikibaseIntegrator(login=login)


def deepest_exception(exc: BaseException) -> BaseException:
    if isinstance(exc, RetryError):
        try:
            return exc.last_attempt.exception() or exc
        except Exception:
            return exc
    return exc


def exception_message(exc: BaseException) -> str:
    parts = []
    current = deepest_exception(exc)
    parts.append(f"{type(current).__name__}: {current}")
    cause = getattr(current, "__cause__", None)
    if cause:
        parts.append(f"cause={type(cause).__name__}: {cause}")
    return " | ".join(parts)


def label_collision_qid(message: str) -> str:
    match = re.search(r"Item \[\[Item:(Q\d+)\|Q\d+\]\] already has label", message)
    return match.group(1) if match else ""


def is_bad_sitelink_error(message: str) -> bool:
    return "external client site" in message and "did not provide page information" in message


def is_service_unavailable_error(message: str) -> bool:
    return (
        "Service unavailable" in message
        or "HTTP Code 502" in message
        or "HTTP Code 503" in message
        or "HTTP Code 504" in message
        or "502 Server Error" in message
        or "503 Server Error" in message
        or "504 Server Error" in message
    )


def is_invalid_csrf(exc: BaseException) -> bool:
    text = f"{type(exc).__name__}: {exc}"
    cause = getattr(exc, "__cause__", None)
    if cause:
        text += f" | cause={type(cause).__name__}: {cause}"
    return "Invalid CSRF token" in text


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=5, max=60),
    retry=retry_if_exception(lambda exc: not is_invalid_csrf(exc)),
)
def robust_write_with_retries(entity, summary: str):
    return entity.write(summary=summary, clear=False)


def robust_write(entity, summary: str, action: str, clear: bool = False):
    if clear or action == "create":
        # Create and clear-rewrite writes can partially succeed even when the
        # HTTP response times out. Retrying them can mint duplicate items or
        # clear the same item repeatedly, so keep these single-shot.
        return entity.write(summary=summary, clear=clear)
    return robust_write_with_retries(entity, summary)


def factgrid_claim(row: pd.Series, qualifiers: Qualifiers | None = None):
    prop = clean(row.get("fg_pid"))
    datatype = clean(row.get("datatype"))
    value = clean(row.get("value"))
    if not prop or not value:
        return None
    if datatype == "wikibase-item":
        if not re.fullmatch(r"Q\d+", value):
            return None
        return datatypes.Item(prop_nr=prop, value=value, qualifiers=qualifiers)
    if datatype == "external-id":
        if prop == FACTGRID_CDLI_ID_PROPERTY:
            value = format_cdli_id(value)
        return datatypes.ExternalID(prop_nr=prop, value=value, qualifiers=qualifiers)
    if datatype == "string":
        return datatypes.String(prop_nr=prop, value=value[:400], qualifiers=qualifiers)
    return None


def normalize_claim_datavalue(value: object) -> str:
    if isinstance(value, dict):
        if value.get("id"):
            return clean(value.get("id"))
        if value.get("numeric-id"):
            return f"Q{clean(value.get('numeric-id'))}"
    return clean(value)


def claim_main_value(claim) -> str:
    try:
        return normalize_claim_datavalue(claim.mainsnak.datavalue["value"])
    except Exception:
        return ""


def new_claim_main_value(claim) -> tuple[str, str]:
    try:
        mainsnak = claim.get_json().get("mainsnak", {})
        return clean(mainsnak.get("property")), normalize_claim_datavalue(mainsnak.get("datavalue", {}).get("value"))
    except Exception:
        return "", ""


def item_has_claim_main_value(item, claim) -> bool:
    prop, value = new_claim_main_value(claim)
    if not prop or not value:
        return False
    return any(claim_main_value(existing) == value for existing in item.claims.get(prop))


def inventory_number_qualifiers(item_plan: pd.DataFrame) -> Qualifiers | None:
    inventory_values = []
    for value in item_plan.loc[item_plan["field_name"].eq(FACTGRID_INVENTORY_NUMBER_FIELD), "value"].map(clean):
        if value and value not in inventory_values:
            inventory_values.append(value)
    if not inventory_values:
        return None
    qualifiers = Qualifiers()
    for value in inventory_values:
        qualifiers.add(datatypes.String(prop_nr=FACTGRID_INVENTORY_NUMBER_QUALIFIER_PROPERTY, value=value[:400]))
    return qualifiers


def add_claims(item, item_plan: pd.DataFrame, research_project_qids: list[str]) -> tuple[int, int]:
    written = 0
    skipped = 0
    present_holding_qualifiers = inventory_number_qualifiers(item_plan)
    for research_project_qid in research_project_qids:
        item.claims.add(
            datatypes.Item(prop_nr=FACTGRID_RESEARCH_PROJECT_PROPERTY, value=research_project_qid),
            action_if_exists=ActionIfExists.APPEND_OR_REPLACE,
        )
        written += 1
    for _, row in item_plan.iterrows():
        field_name = clean(row.get("field_name"))
        prop = clean(row.get("fg_pid"))
        if field_name == FACTGRID_INVENTORY_NUMBER_FIELD:
            skipped += 1
            continue
        if field_name == FACTGRID_FINDING_SPOT_CONTEXT_FIELD:
            skipped += 1
            continue
        qualifiers = present_holding_qualifiers if prop == FACTGRID_PRESENT_HOLDING_PROPERTY else None
        claim = factgrid_claim(row, qualifiers=qualifiers)
        if claim is None:
            skipped += 1
            continue
        if item_has_claim_main_value(item, claim):
            skipped += 1
            continue
        item.claims.add(claim, action_if_exists=ActionIfExists.APPEND_OR_REPLACE)
        written += 1
    return written, skipped


def apply_factgrid_overrides(statements: pd.DataFrame, overrides: dict[str, dict[str, str]]) -> pd.DataFrame:
    if statements.empty or not overrides:
        return statements
    out = statements.copy()
    for idx, row in out.iterrows():
        field_name = clean(row.get("field_name"))
        if not field_name:
            continue
        value = ""
        for key in cdli_keys(row.get("cdli_id")):
            value = overrides.get(key, {}).get(field_name, "")
            if value:
                break
        if not value:
            continue
        datatype = clean(row.get("datatype"))
        if datatype == "wikibase-item" and re.fullmatch(r"Q\d+", value):
            out.at[idx, "value"] = value
            if clean(row.get("plan_status")) != "ready":
                out.at[idx, "plan_status"] = "ready"
                out.at[idx, "source"] = f"{clean(row.get('source'))}|factgrid_upload_table"
        elif datatype == "external-id" and field_name == "cdli_id":
            out.at[idx, "value"] = format_cdli_id(value)
            out.at[idx, "plan_status"] = "ready"
        elif datatype == "string" and field_name in {"inventory_number", "finding_spot_context"}:
            out.at[idx, "value"] = value
            out.at[idx, "plan_status"] = "ready"
    return out


def apply_object_type_instance_overrides(statements: pd.DataFrame, artifacts: pd.DataFrame) -> pd.DataFrame:
    if statements.empty or artifacts.empty or "artifact_type" not in artifacts.columns:
        return statements
    artifact_types: dict[str, str] = {}
    for _, row in artifacts.iterrows():
        artifact_type = normalize_object_type(row.get("artifact_type"))
        if not artifact_type:
            continue
        for key in cdli_keys(row.get("cdli_id")):
            artifact_types.setdefault(key, artifact_type)

    out = statements.copy()
    mask = out["field_name"].eq("instance_of")
    for idx, row in out.loc[mask].iterrows():
        current_value = clean(row.get("value"))
        current_status = clean(row.get("plan_status"))
        if current_status == "ready" and re.fullmatch(r"Q\d+", current_value):
            continue
        artifact_type = ""
        for key in cdli_keys(row.get("cdli_id")):
            artifact_type = artifact_types.get(key, "")
            if artifact_type:
                break
        mapped = FACTGRID_OBJECT_TYPE_INSTANCE_OF.get(artifact_type)
        if not mapped:
            continue
        qid, label = mapped
        out.at[idx, "value"] = qid
        out.at[idx, "value_label"] = label
        out.at[idx, "plan_status"] = "ready"
        out.at[idx, "source"] = f"{clean(row.get('source'))}|factgrid_object_type_map"
    return out


def apply_collection_present_holding_overrides(
    statements: pd.DataFrame,
    artifacts: pd.DataFrame,
    collection_matches: tuple[dict[str, dict[str, str]], dict[str, dict[str, str]]],
) -> pd.DataFrame:
    if statements.empty or artifacts.empty:
        return statements
    by_collection_id, by_collection_name = collection_matches
    if not by_collection_id and not by_collection_name:
        return statements

    artifact_collections: dict[str, dict[str, str]] = {}
    for _, row in artifacts.iterrows():
        match = {}
        for collection_id in split_pipe_values(row.get("collection_ids")):
            match = by_collection_id.get(collection_id, {})
            if match:
                break
        if not match:
            for collection_name in split_pipe_values(row.get("collections")) + [clean(row.get("primary_collection"))]:
                match = by_collection_name.get(normalize(collection_name), {})
                if match:
                    break
        if not match:
            continue
        for key in cdli_keys(row.get("cdli_id")):
            artifact_collections.setdefault(key, match)

    out = statements.copy()
    mask = out["field_name"].eq("present_holding")
    for idx, row in out.loc[mask].iterrows():
        current_value = clean(row.get("value"))
        current_status = clean(row.get("plan_status"))
        if current_status == "ready" and re.fullmatch(r"Q\d+", current_value):
            continue
        match = {}
        for key in cdli_keys(row.get("cdli_id")):
            match = artifact_collections.get(key, {})
            if match:
                break
        qid = clean(match.get("factgrid_qid"))
        if not re.fullmatch(r"Q\d+", qid):
            continue
        out.at[idx, "value"] = qid
        out.at[idx, "value_label"] = clean(match.get("factgrid_label"))
        out.at[idx, "plan_status"] = "ready"
        out.at[idx, "source"] = f"{clean(row.get('source'))}|factgrid_collection_match_review"
    return out


def assign_reuse_qids(artifacts: pd.DataFrame, reuse_qids: list[str]) -> pd.DataFrame:
    if artifacts.empty or not reuse_qids:
        return artifacts
    out = artifacts.copy()
    create_idx = list(out.index[out["factgrid_action"].eq("create")])
    for idx, qid in zip(create_idx, reuse_qids):
        out.at[idx, "factgrid_qid"] = qid
        out.at[idx, "factgrid_action"] = "rewrite"
    return out


def build_workset(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame]:
    artifacts = read_csv(args.artifacts)
    statements = read_csv(args.statements)
    existing = merge_existing_qid_maps(
        load_existing_factgrid_qids(args.factgrid_cdli),
        load_prior_factgrid_qid_lookups(args.prior_factgrid_qid_lookup),
        load_written_result_qids(args.results),
    )
    upload_overrides = load_factgrid_upload_overrides(args.factgrid_upload_table)
    collection_matches = load_collection_matches(args.collection_matches)
    results = read_csv(args.results)

    if artifacts.empty:
        raise RuntimeError(f"No artifact rows found in {args.artifacts}")
    if statements.empty:
        raise RuntimeError(f"No statement rows found in {args.statements}")

    artifacts["_cdli_key"] = artifacts["cdli_id"].map(clean)
    artifacts["factgrid_qid"] = artifacts.apply(
        lambda row: next((existing[k] for k in cdli_keys(row.get("cdli_id")) if k in existing), "")
        or existing.get(normalize(row.get("label")), ""),
        axis=1,
    )
    artifacts["factgrid_action"] = artifacts["factgrid_qid"].map(lambda v: "update" if clean(v) else "create")

    if args.only_cdli_ids:
        allowed_cdli_ids = {format_cdli_id(v) for v in re.split(r"[,;\s]+", clean(args.only_cdli_ids)) if clean(v)}
        artifacts = artifacts[artifacts["_cdli_key"].map(format_cdli_id).isin(allowed_cdli_ids)].copy()
    if args.only_missing_factgrid:
        artifacts = artifacts[artifacts["factgrid_qid"].map(clean).eq("")].copy()
    if args.only_existing_factgrid:
        artifacts = artifacts[artifacts["factgrid_qid"].map(clean).ne("")].copy()

    if not results.empty and {"cdli_id", "write_status"}.issubset(results.columns):
        done_statuses = {"written", "blocked_bad_sitelink", "rewrite_ambiguous", "create_ambiguous"}
        done = set(results.loc[results["write_status"].isin(done_statuses), "cdli_id"].map(clean))
        artifacts = artifacts[~artifacts["_cdli_key"].isin(done)].copy()

    statements = apply_factgrid_overrides(statements, upload_overrides)
    statements = apply_object_type_instance_overrides(statements, artifacts)
    statements = apply_collection_present_holding_overrides(statements, artifacts, collection_matches)
    selected = set(artifacts["_cdli_key"].map(clean))
    plan = statements[
        statements["cdli_id"].map(clean).isin(selected)
        & statements["plan_status"].eq("ready")
        & statements["fg_pid"].map(clean).ne("")
    ].copy()
    # FactGrid P425 is item-valued; the local finding_spot_context is a raw CDLI string.
    # Keep it out of this writer until we map context text to the correct FactGrid QIDs.
    plan = plan[~plan["field_name"].eq(FACTGRID_FINDING_SPOT_CONTEXT_FIELD)].copy()
    plan = plan[
        ~(
            plan["field_name"].eq("finding_spot")
            & (
                plan["value_label"].map(normalize).isin({"unknown", "uncertain", "uncertain mod uncertain"})
                | plan["value"].map(clean).eq("Q389782")
            )
        )
    ].copy()
    if args.only_field_names:
        allowed = {clean(v) for v in args.only_field_names.split(",") if clean(v)}
        plan = plan[plan["field_name"].isin(allowed)].copy()
    create_keys = set(artifacts.loc[artifacts["factgrid_action"].isin(["create", "rewrite"]), "_cdli_key"].map(clean))
    keys_with_instance_of = set(
        plan.loc[
            plan["field_name"].eq("instance_of")
            & plan["fg_pid"].eq("P2")
            & plan["value"].map(clean).str.fullmatch(r"Q\d+", na=False),
            "cdli_id",
        ].map(clean)
    )
    missing_instance_of = create_keys - keys_with_instance_of
    if missing_instance_of:
        missing_types = (
            artifacts.loc[artifacts["_cdli_key"].isin(missing_instance_of), ["cdli_id", "artifact_type"]]
            .drop_duplicates()
            .sort_values(["artifact_type", "cdli_id"])
        )
        print("\nSkipping new FactGrid items without a resolved P2 instance_of:")
        print(missing_types.head(args.preview).to_string(index=False))
        artifacts = artifacts[~artifacts["_cdli_key"].isin(missing_instance_of)].copy()
        plan = plan[~plan["cdli_id"].map(clean).isin(missing_instance_of)].copy()
    if args.reuse_pool and not args.only_existing_factgrid:
        reuse_qids = load_available_reuse_qids(
            args.reuse_pool,
            results,
            allow_hold=args.allow_unrepaired_reuse,
            allow_unapproved=args.allow_unapproved_reuse,
        )
        artifacts = assign_reuse_qids(artifacts, reuse_qids)
    artifacts["write_label"] = artifacts.apply(artifact_label_for, axis=1)
    if args.limit:
        artifacts = artifacts.head(args.limit).copy()
        selected = set(artifacts["_cdli_key"].map(clean))
        plan = plan[plan["cdli_id"].map(clean).isin(selected)].copy()
    return artifacts, plan


def build_item(
    wbi: WikibaseIntegrator,
    artifact: pd.Series,
    item_plan: pd.DataFrame,
    research_project_qids: list[str],
    preserve_update_labels: bool,
):
    qid = clean(artifact.get("factgrid_qid"))
    item = wbi.item.get(qid) if qid else wbi.item.new()
    label = artifact_label_for(artifact)
    if qid and clean(artifact.get("factgrid_action")) == "rewrite":
        reset_loaded_item_for_reuse(item)
        item.labels.set(language="en", value=label)
        item.descriptions.set(language="en", value=description_for(artifact))
        aliases = alias_values(artifact)
    elif qid and preserve_update_labels:
        aliases = [label] + alias_values(artifact)
    else:
        item.labels.set(language="en", value=label)
        item.descriptions.set(language="en", value=description_for(artifact))
        aliases = alias_values(artifact)
    if aliases:
        item.aliases.set(language="en", values=aliases, action_if_exists=ActionIfExists.APPEND_OR_REPLACE)
    claim_count, skipped_count = add_claims(item, item_plan, research_project_qids)
    return item, label, claim_count, skipped_count


def reset_loaded_item_for_reuse(item) -> None:
    """Remove in-memory old item content before clear=True rewrite."""

    item.claims.claims.clear()
    item.labels._LanguageValues__values.clear()
    item.descriptions._LanguageValues__values.clear()
    item.aliases._Aliases__aliases.clear()
    item.sitelinks.sitelinks.clear()


def write_items(args: argparse.Namespace) -> None:
    work, plan = build_workset(args)
    args.plan.parent.mkdir(parents=True, exist_ok=True)
    args.results.parent.mkdir(parents=True, exist_ok=True)
    plan.to_csv(args.plan, index=False)

    print(f"FactGrid artifact rows selected: {len(work)}")
    if len(work):
        print(work["factgrid_action"].value_counts(dropna=False).rename_axis("action").reset_index(name="count").to_string(index=False))
    if len(plan):
        print("\nStatement plan summary:")
        print(plan.groupby(["field_name", "fg_pid", "datatype"]).size().reset_index(name="count").to_string(index=False))
        if plan["field_name"].eq(FACTGRID_INVENTORY_NUMBER_FIELD).any():
            print(f"\nNote: inventory_number source rows are written as {FACTGRID_INVENTORY_NUMBER_QUALIFIER_PROPERTY} qualifiers on {FACTGRID_PRESENT_HOLDING_PROPERTY}, not as main statements.")
        print(f"Note: each written item also receives {FACTGRID_RESEARCH_PROJECT_PROPERTY} statements for: {', '.join(parse_qid_list(args.research_project_qids))}.")
        print("\nReady statement preview:")
        print(
            plan[["cdli_id", "field_name", "fg_pid", "datatype", "value", "value_label"]]
            .head(args.preview * 3)
            .to_string(index=False)
        )
    preview_cols = ["cdli_id", "factgrid_action", "factgrid_qid", "write_label", "label", "artifact_type", "period", "provenience", "primary_collection"]
    print("\nItem preview:")
    print(work[[col for col in preview_cols if col in work.columns]].head(args.preview).to_string(index=False))

    if not args.write:
        print("\nDRY_RUN: no FactGrid items written. Pass --write to create/update/rewrite items.")
        return
    if work["factgrid_action"].eq("rewrite").any() and not args.clear_existing_reuse:
        raise RuntimeError("Refusing to rewrite reusable FactGrid QIDs without --clear-existing-reuse.")

    results = read_csv(args.results)
    out_rows: list[dict[str, object]] = []
    research_project_qids = parse_qid_list(args.research_project_qids)
    wbi = api_login()
    for _, artifact in tqdm(work.iterrows(), total=len(work)):
        cdli_id = clean(artifact.get("cdli_id"))
        item_plan = plan[plan["cdli_id"].map(clean).eq(cdli_id)].copy()
        action = clean(artifact.get("factgrid_action"))
        is_rewrite = action == "rewrite"
        try:
            item, label, claim_count, skipped_count = build_item(
                wbi,
                artifact,
                item_plan,
                research_project_qids,
                args.preserve_update_labels,
            )
            written = robust_write(
                item,
                f"{action.title()} FactGrid CDLI artifact {format_cdli_id(cdli_id)}: {label[:80]}",
                action=action,
                clear=is_rewrite,
            )
            print(f"{action}d {written.id} — {label} ({claim_count} claims; {skipped_count} skipped)", flush=True)
            out_rows.append(
                {
                    "cdli_id": cdli_id,
                    "factgrid_qid": written.id,
                    "artifact_label": label,
                    "write_action": action,
                    "claims_written": claim_count,
                    "claims_skipped": skipped_count,
                    "write_status": "written",
                    "write_error": "",
                    "label_collision_qid": "",
                }
            )
        except Exception as exc:
            message = exception_message(exc)[:500]
            collision_qid = label_collision_qid(message)
            if collision_qid:
                status = "label_collision"
            elif is_bad_sitelink_error(message):
                status = "blocked_bad_sitelink"
            elif is_rewrite and is_service_unavailable_error(message):
                status = "rewrite_ambiguous"
            elif action == "create" and is_service_unavailable_error(message):
                status = "create_ambiguous"
            else:
                status = "error"
            print(f"row error: {format_cdli_id(cdli_id)} — {message}", flush=True)
            out_rows.append(
                {
                    "cdli_id": cdli_id,
                    "factgrid_qid": clean(artifact.get("factgrid_qid")),
                    "artifact_label": artifact_label_for(artifact),
                    "write_action": action,
                    "claims_written": 0,
                    "claims_skipped": len(item_plan),
                    "write_status": status,
                    "write_error": message,
                    "label_collision_qid": collision_qid,
                }
            )
            if not args.continue_on_row_error:
                raise
        finally:
            pd.concat([results, pd.DataFrame(out_rows)], ignore_index=True).drop_duplicates(["cdli_id"], keep="last").to_csv(args.results, index=False)
        time.sleep(args.sleep)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, default=DEFAULT_ARTIFACTS)
    parser.add_argument("--statements", type=Path, default=DEFAULT_STATEMENTS)
    parser.add_argument("--factgrid-cdli", type=Path, default=DEFAULT_FACTGRID_CDLI)
    parser.add_argument(
        "--prior-factgrid-qid-lookup",
        type=Path,
        action="append",
        default=list(DEFAULT_PRIOR_FACTGRID_QID_LOOKUPS),
        help="Additional lookup CSV with match_key_type, match_key, factgrid_qid columns. Can be repeated.",
    )
    parser.add_argument("--factgrid-upload-table", type=Path, default=DEFAULT_FACTGRID_UPLOAD_TABLE)
    parser.add_argument("--collection-matches", type=Path, default=DEFAULT_COLLECTION_MATCHES)
    parser.add_argument("--reuse-pool", type=Path, default=None)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--preview", type=int, default=10)
    parser.add_argument("--sleep", type=float, default=2.0)
    parser.add_argument("--only-field-names", default="")
    parser.add_argument("--only-cdli-ids", default="", help="Comma/space-separated CDLI IDs to include, e.g. P360228,216426")
    parser.add_argument("--only-missing-factgrid", action="store_true")
    parser.add_argument("--only-existing-factgrid", action="store_true")
    parser.add_argument("--research-project-qids", default=DEFAULT_RESEARCH_PROJECT_QIDS)
    parser.add_argument("--research-project-qid", dest="research_project_qids", help=argparse.SUPPRESS)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--clear-existing-reuse", action="store_true", help="Required with --write when rewriting reusable duplicate QIDs.")
    parser.add_argument("--allow-unrepaired-reuse", action="store_true", help="Allow reuse-pool rows still marked hold_until_canonical_repair.")
    parser.add_argument("--allow-unapproved-reuse", action="store_true", help="Allow reuse-pool rows without future_reuse_status approval.")
    parser.add_argument(
        "--preserve-update-labels",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="For existing FactGrid items, keep the current label/description and add incoming names as aliases.",
    )
    parser.add_argument("--continue-on-row-error", action="store_true")
    args = parser.parse_args()
    if args.only_missing_factgrid and args.only_existing_factgrid:
        raise RuntimeError("Use only one of --only-missing-factgrid or --only-existing-factgrid")
    write_items(args)


if __name__ == "__main__":
    main()
