#!/usr/bin/env python3
"""Create new TokenWorks Wikibase items for staged CDLI artifacts.

This is the companion to ``write_cdli_artifact_pilot.py``. That script rewrites
reserved duplicate-publication QIDs; this one creates fresh QIDs for artifacts
whose reservation status is ``needs_new_qid``.
"""

from __future__ import annotations

import argparse
import getpass
import logging
import os
import re
import time
from pathlib import Path

import pandas as pd
import requests
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential
from tqdm.auto import tqdm
from wikibaseintegrator import WikibaseIntegrator, datatypes
from wikibaseintegrator.wbi_config import config
from wikibaseintegrator.wbi_enums import ActionIfExists
from wikibaseintegrator.wbi_login import Login


WORKFLOW_ROOT = Path(__file__).resolve().parents[1]
PILOT_ROOT = WORKFLOW_ROOT / "published" / "pilots"
DEFAULT_ARTIFACTS = PILOT_ROOT / "cdli_artifact_staging_pilot_10000.csv"
DEFAULT_STATEMENTS = PILOT_ROOT / "cdli_artifact_statement_staging_pilot_10000_with_lookups.csv"
DEFAULT_RESERVATIONS = PILOT_ROOT / "cdli_artifact_qid_reuse_reservations_pilot_10000.csv"
DEFAULT_AUTHORITY_RESULTS = PILOT_ROOT / "cdli_authority_item_results_pilot_10000.csv"
DEFAULT_RESULTS = PILOT_ROOT / "cdli_artifact_new_item_results_pilot_10000.csv"
DEFAULT_PLAN = PILOT_ROOT / "cdli_artifact_new_item_plan_pilot_10000.csv"
TW_API = "https://wikibase.tk-wiki-kg.com/w/api.php"


def clean(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null"}:
        return ""
    if text.endswith(".0") and text[:-2].isdigit():
        return text[:-2]
    return text


def format_cdli_id(value: object) -> str:
    text = clean(value)
    match = re.search(r"(\d+)", text)
    if not match:
        return text
    return f"P{int(match.group(1)):06d}"


def api_login(skip_preflight: bool = False) -> WikibaseIntegrator:
    username = os.environ.get("TW_USER") or input("TokenWorks username: ")
    password = os.environ.get("TW_PASS") or getpass.getpass("TokenWorks password: ")
    config["MEDIAWIKI_API_URL"] = TW_API
    config["PROPERTY_CONSTRAINTS_CHECK"] = False
    if not skip_preflight:
        preflight_api()
    logging.getLogger("backoff").setLevel(logging.ERROR)
    try:
        login = Login(user=username, password=password)
    except Exception as exc:
        cause = getattr(exc, "__cause__", None)
        detail = f"{type(exc).__name__}: {exc}"
        if cause:
            detail += f" | cause={type(cause).__name__}: {cause}"
        detail = detail.replace(password, "[redacted]") if password else detail
        raise RuntimeError(
            "TokenWorks login failed. If the credentials are correct, the API may still be returning "
            "an HTML error page instead of JSON; try the preflight URL in a browser or rerun in a few minutes. "
            f"Underlying error: {detail[:500]}"
        ) from None
    return WikibaseIntegrator(login=login)


def preflight_api() -> None:
    try:
        response = requests.get(
            TW_API,
            params={"action": "query", "meta": "tokens", "type": "login", "format": "json"},
            headers={"User-Agent": "TokenWorks-CDLI-artifact-writer/1.0"},
            timeout=30,
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"TokenWorks API preflight failed: {type(exc).__name__}: {exc}") from exc
    content_type = response.headers.get("content-type", "")
    if response.status_code != 200 or "json" not in content_type.lower():
        snippet = response.text[:500].replace("\n", " ")
        raise RuntimeError(
            f"TokenWorks API preflight expected JSON from {TW_API}, but received "
            f"status={response.status_code}, content-type={content_type!r}. First 500 chars: {snippet}"
        )
    try:
        response.json()
    except ValueError as exc:
        snippet = response.text[:500].replace("\n", " ")
        raise RuntimeError(f"TokenWorks API preflight received invalid JSON. First 500 chars: {snippet}") from exc


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=5, max=60),
    retry=retry_if_exception(lambda exc: not is_invalid_csrf(exc)),
)
def robust_write(entity, summary: str):
    return entity.write(summary=summary)


def is_invalid_csrf(exc: BaseException) -> bool:
    text = f"{type(exc).__name__}: {exc}"
    cause = getattr(exc, "__cause__", None)
    if cause:
        text += f" | cause={type(cause).__name__}: {cause}"
    return "Invalid CSRF token" in text


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, low_memory=False).fillna("")


def load_many_csv(paths: list[Path]) -> pd.DataFrame:
    frames = [load_csv(path) for path in paths if path]
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True).fillna("")


def split_values(value: object) -> list[str]:
    out = []
    seen = set()
    for part in clean(value).split("|"):
        text = clean(part)
        if not text or text in seen:
            continue
        out.append(text)
        seen.add(text)
    return out


def publication_reference_aliases(artifact: pd.Series) -> list[str]:
    publications = split_values(artifact.get("publication_designations"))
    references = split_values(artifact.get("exact_references"))
    if not publications or not references:
        return []
    aliases = []
    for publication in publications:
        for reference in references:
            aliases.append(f"{publication}, {reference}")
    return aliases


def is_generic_artifact_label(value: object) -> bool:
    text = clean(value)
    if not text:
        return True
    normalized = re.sub(r"[^a-z0-9]+", " ", text.casefold())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if len(normalized) < 3:
        return True
    generic_values = {
        "unknown",
        "unassigned",
        "unpublished unassigned",
        "bm",
        "im",
        "nmsd",
        "nmsi",
        "va",
        "vat",
        "sb",
        "amm",
    }
    if normalized in generic_values:
        return True
    if "unknown" in normalized or "unassigned" in normalized:
        return True
    return False


def artifact_label_for(artifact: pd.Series) -> str:
    label = clean(artifact.get("label"))
    artifact_type = clean(artifact.get("artifact_type")).lower()
    cdli_id = clean(artifact.get("cdli_id"))
    if is_generic_artifact_label(label):
        label = format_cdli_id(cdli_id) if cdli_id else "CDLI artifact"
    if label.lower().startswith(("cuneiform tablet", "cuneiform artifact")):
        return label[:250]
    if "tablet" in artifact_type:
        return f"Cuneiform Tablet {label}"[:250]
    return f"Cuneiform Artifact {label}"[:250]


def alias_values(artifact: pd.Series) -> list[str]:
    aliases = []
    original_label = clean(artifact.get("label"))
    if original_label:
        aliases.append(original_label)
    for col in ["designation", "museum_no", "accession_no"]:
        aliases.extend(split_values(artifact.get(col)))
    aliases.extend(publication_reference_aliases(artifact))
    label = artifact_label_for(artifact)
    out = []
    seen = set()
    for value in aliases:
        text = clean(value)
        if not text or text == label or text in seen:
            continue
        out.append(text[:250])
        seen.add(text)
    return out


def description_for(artifact: pd.Series) -> str:
    parts = []
    artifact_type = clean(artifact.get("artifact_type")) or clean(artifact.get("type"))
    period = clean(artifact.get("period"))
    provenience = clean(artifact.get("provenience"))
    holding = clean(artifact.get("primary_collection"))
    cdli_id = clean(artifact.get("cdli_id"))
    if artifact_type:
        parts.append(artifact_type)
    if provenience:
        parts.append(f"from {provenience}")
    if period:
        parts.append(period)
    if holding:
        parts.append(f"held by {holding}")
    description = "CDLI artifact"
    if parts:
        description += ": " + "; ".join(parts)
    if cdli_id:
        description += f"; CDLI {format_cdli_id(cdli_id)}"
    return description[:250]


def claim_from_row(row: pd.Series):
    prop = clean(row.get("tw_pid"))
    datatype = clean(row.get("datatype"))
    value = clean(row.get("tokenworks_value_qid")) if datatype == "wikibase-item" else clean(row.get("value"))
    if not prop or not value:
        return None
    if datatype == "wikibase-item":
        return datatypes.Item(prop_nr=prop, value=value)
    if datatype == "external-id":
        if prop == "P223":
            value = format_cdli_id(value)
        return datatypes.ExternalID(prop_nr=prop, value=value)
    if datatype == "string":
        return datatypes.String(prop_nr=prop, value=value[:400])
    if datatype == "quantity":
        amount = value if value.startswith(("+", "-")) else f"+{value}"
        return datatypes.Quantity(prop_nr=prop, amount=amount)
    raise ValueError(f"Unsupported datatype in new artifact item write: {datatype}")


def authority_map(path: Path) -> dict[str, str]:
    authority = load_csv(path)
    if authority.empty:
        return {}
    required = {"factgrid_qid", "tw_qid", "create_status"}
    if not required.issubset(authority.columns):
        raise RuntimeError(f"Authority results missing columns {sorted(required - set(authority.columns))}: {path}")
    created = authority[authority["create_status"].eq("created") & authority["tw_qid"].map(clean).ne("")]
    return dict(zip(created["factgrid_qid"].map(clean), created["tw_qid"].map(clean)))


def build_workset(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame]:
    artifacts = load_csv(args.artifacts)
    statements = load_csv(args.statements)
    reservations = load_csv(args.reservations)
    previous = load_many_csv([args.results, *args.prior_results])
    fg_to_tw = authority_map(args.authority_results)

    if artifacts.empty:
        raise RuntimeError(f"No artifact rows found in {args.artifacts}")
    if statements.empty:
        raise RuntimeError(f"No statement rows found in {args.statements}")
    if reservations.empty:
        raise RuntimeError(f"No QID reservation rows found in {args.reservations}")

    todo = reservations[reservations["reservation_status"].eq("needs_new_qid")].copy()
    todo = todo.drop_duplicates("incoming_source_id", keep="last")

    if args.retry_errors_from:
        error_results = load_csv(args.retry_errors_from)
        if error_results.empty or "write_status" not in error_results.columns:
            raise RuntimeError(f"No write-status rows found in {args.retry_errors_from}")
        retry_cdli_ids = set(error_results.loc[error_results["write_status"].eq("error"), "cdli_id"].map(clean))
        current_results = load_csv(args.results)
        if not current_results.empty and {"cdli_id", "write_status"}.issubset(current_results.columns):
            written_now = set(current_results.loc[current_results["write_status"].eq("written"), "cdli_id"].map(clean))
            retry_cdli_ids -= written_now
        todo = todo[todo["incoming_source_id"].map(clean).isin(retry_cdli_ids)].copy()
        previous = pd.DataFrame()

    if not previous.empty and {"cdli_id", "write_status"}.issubset(previous.columns):
        written = set(previous.loc[previous["write_status"].eq("written"), "cdli_id"].map(clean))
        todo = todo[~todo["incoming_source_id"].map(clean).isin(written)].copy()

    if args.limit:
        todo = todo.head(args.limit).copy()

    artifacts = artifacts.copy()
    artifacts["_cdli_key"] = artifacts["cdli_id"].map(clean)
    todo = todo.copy()
    todo["_cdli_key"] = todo["incoming_source_id"].map(clean)
    work = todo.merge(artifacts, on="_cdli_key", how="left", suffixes=("_reservation", ""))
    work["cdli_id"] = work["_cdli_key"]
    work = work[work["label"].map(clean).ne("")].copy()

    selected = set(work["cdli_id"].map(clean))
    plan = statements[
        statements["cdli_id"].map(clean).isin(selected)
        & statements["tw_qid"].map(clean).eq("NEEDS_QID")
        & statements["plan_status"].isin(["ready", "needs_lookup_qid"])
    ].copy()

    plan["tokenworks_value_qid"] = ""
    is_item = plan["datatype"].eq("wikibase-item")
    ready_item = is_item & plan["plan_status"].eq("ready")
    plan.loc[ready_item, "tokenworks_value_qid"] = plan.loc[ready_item, "value"].map(lambda value: fg_to_tw.get(clean(value), ""))
    plan["claim_status"] = "skip"
    plan.loc[plan["datatype"].ne("wikibase-item") & plan["plan_status"].eq("ready"), "claim_status"] = "ready"
    plan.loc[ready_item & plan["tokenworks_value_qid"].map(clean).ne(""), "claim_status"] = "ready"
    plan.loc[ready_item & plan["tokenworks_value_qid"].map(clean).eq(""), "claim_status"] = "missing_authority_tw_qid"
    plan.loc[plan["plan_status"].eq("needs_lookup_qid"), "claim_status"] = "needs_lookup_qid"

    if args.only_field_names:
        fields = {field.strip() for field in args.only_field_names.split(",") if field.strip()}
        plan = plan[plan["field_name"].isin(fields)].copy()
    return work, plan


def add_ready_claims(item, plan: pd.DataFrame) -> tuple[int, int, int]:
    scalar_count = 0
    authority_count = 0
    skipped_count = 0
    for _, statement in plan.iterrows():
        if clean(statement.get("claim_status")) != "ready":
            skipped_count += 1
            continue
        claim = claim_from_row(statement)
        if claim is None:
            skipped_count += 1
            continue
        item.claims.add(claim, action_if_exists=ActionIfExists.APPEND_OR_REPLACE)
        if clean(statement.get("datatype")) == "wikibase-item":
            authority_count += 1
        else:
            scalar_count += 1
    return scalar_count, authority_count, skipped_count


def build_item(wbi: WikibaseIntegrator, artifact: pd.Series, item_plan: pd.DataFrame):
    item = wbi.item.new()
    label = artifact_label_for(artifact)
    item.labels.set(language="en", value=label)
    item.descriptions.set(language="en", value=description_for(artifact))
    aliases = alias_values(artifact)
    if aliases:
        item.aliases.set(language="en", values=aliases, action_if_exists=ActionIfExists.APPEND_OR_REPLACE)
    scalar_count, authority_count, skipped_count = add_ready_claims(item, item_plan)
    return item, label, scalar_count, authority_count, skipped_count


def write_item_with_csrf_refresh(
    wbi: WikibaseIntegrator,
    artifact: pd.Series,
    item_plan: pd.DataFrame,
    cdli_id: str,
    max_csrf_refreshes: int,
    skip_api_preflight: bool,
):
    for attempt in range(max_csrf_refreshes + 1):
        item, label, scalar_count, authority_count, skipped_count = build_item(wbi, artifact, item_plan)
        try:
            written = robust_write(item, f"Create TokenWorks CDLI artifact {format_cdli_id(cdli_id)}: {label[:80]}")
            return written, label, scalar_count, authority_count, skipped_count, wbi
        except Exception as exc:
            if not is_invalid_csrf(exc) or attempt >= max_csrf_refreshes:
                raise
            print(f"refreshing TokenWorks login after invalid CSRF token for {format_cdli_id(cdli_id)}", flush=True)
            wbi = api_login(skip_api_preflight)
    raise RuntimeError("Unreachable CSRF refresh state")


def create_items(args: argparse.Namespace) -> None:
    work, plan = build_workset(args)
    args.plan.parent.mkdir(parents=True, exist_ok=True)
    args.results.parent.mkdir(parents=True, exist_ok=True)
    plan.to_csv(args.plan, index=False)

    print(f"new artifact items to create: {len(work)}")
    if len(plan):
        print("\nStatement plan summary:")
        print(
            plan.groupby(["field_name", "claim_status", "datatype"])
            .size()
            .reset_index(name="count")
            .to_string(index=False)
        )
    preview_cols = ["cdli_id", "label", "artifact_type", "period", "provenience", "primary_collection"]
    print("\nItem preview:")
    print(work[[col for col in preview_cols if col in work.columns]].head(args.preview).to_string(index=False))

    if not args.write:
        print("\nDRY_RUN: no new artifact items written. Pass --write to create items.")
        return

    results = load_csv(args.results)
    if results.empty:
        results = pd.DataFrame()
    rows = []
    wbi = api_login(args.skip_api_preflight)
    for _, artifact in tqdm(work.iterrows(), total=len(work)):
        cdli_id = clean(artifact.get("cdli_id"))
        item_plan = plan[plan["cdli_id"].map(clean).eq(cdli_id)].copy()
        try:
            written, label, scalar_count, authority_count, skipped_count, wbi = write_item_with_csrf_refresh(
                wbi,
                artifact,
                item_plan,
                cdli_id,
                args.max_csrf_refreshes,
                args.skip_api_preflight,
            )
            print(
                f"created {written.id} — {label} "
                f"({scalar_count} scalar claims; {authority_count} authority claims; {skipped_count} skipped)",
                flush=True,
            )
            rows.append(
                {
                    "cdli_id": cdli_id,
                    "tw_qid": written.id,
                    "artifact_label": label,
                    "scalar_claims_written": scalar_count,
                    "authority_claims_written": authority_count,
                    "claims_skipped": skipped_count,
                    "write_status": "written",
                    "write_error": "",
                }
            )
            time.sleep(args.sleep)
        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"[:500]
            print(f"row error: P{cdli_id} — {message}", flush=True)
            rows.append(
                {
                    "cdli_id": cdli_id,
                    "tw_qid": "",
                    "artifact_label": artifact_label_for(artifact),
                    "scalar_claims_written": 0,
                    "authority_claims_written": 0,
                    "claims_skipped": len(item_plan),
                    "write_status": "error",
                    "write_error": message,
                }
            )
            if not args.continue_on_row_error:
                raise
            time.sleep(args.sleep)
        finally:
            pd.concat([results, pd.DataFrame(rows)], ignore_index=True).drop_duplicates(["cdli_id"], keep="last").to_csv(
                args.results, index=False
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, default=DEFAULT_ARTIFACTS)
    parser.add_argument("--statements", type=Path, default=DEFAULT_STATEMENTS)
    parser.add_argument("--reservations", type=Path, default=DEFAULT_RESERVATIONS)
    parser.add_argument("--authority-results", type=Path, default=DEFAULT_AUTHORITY_RESULTS)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument(
        "--prior-results",
        type=Path,
        action="append",
        default=[],
        help="Additional previous result CSV to skip already written artifacts while writing to a new results file.",
    )
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--preview", type=int, default=10)
    parser.add_argument("--sleep", type=float, default=2.0)
    parser.add_argument("--only-field-names", default="")
    parser.add_argument("--write", action="store_true", help="Actually write to TokenWorks. Omit for dry-run.")
    parser.add_argument("--retry-errors-from", type=Path, help="Only reprocess rows marked error in this previous results CSV.")
    parser.add_argument("--max-csrf-refreshes", type=int, default=2)
    parser.add_argument("--continue-on-row-error", action="store_true")
    parser.add_argument(
        "--skip-api-preflight",
        action="store_true",
        help="Skip the anonymous API JSON preflight. Useful when /w/api.php intentionally returns 401 before login.",
    )
    args = parser.parse_args()
    create_items(args)


if __name__ == "__main__":
    main()
