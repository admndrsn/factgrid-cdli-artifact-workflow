#!/usr/bin/env python3
"""Write a tiny CDLI artifact pilot to TokenWorks Wikibase.

This script is intentionally cautious. It is designed for the first artifact
write test using QIDs reserved from the publication duplicate reuse pool.

By default it only previews work. To actually reuse an existing QID, pass both
`--write` and `--clear-existing`; this replaces the old duplicate-publication
item content with the staged artifact label, description, aliases, and ready
artifact statements.
"""

from __future__ import annotations

import argparse
import getpass
import os
import re
import time
from pathlib import Path

import pandas as pd
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from tqdm.auto import tqdm
from wikibaseintegrator import WikibaseIntegrator, datatypes
from wikibaseintegrator.wbi_config import config
from wikibaseintegrator.wbi_enums import ActionIfExists
from wikibaseintegrator.wbi_login import Login


WORKFLOW_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACTS = WORKFLOW_ROOT / "published" / "pilots" / "cdli_artifact_staging_pilot_10000.csv"
DEFAULT_STATEMENTS = WORKFLOW_ROOT / "published" / "pilots" / "cdli_artifact_statement_staging_pilot_10000_with_lookups.csv"
DEFAULT_RESERVATIONS = WORKFLOW_ROOT / "published" / "pilots" / "cdli_artifact_qid_reuse_reservations_pilot_10000.csv"
DEFAULT_RESULTS = WORKFLOW_ROOT / "published" / "pilots" / "cdli_artifact_write_pilot_results.csv"
DEFAULT_PLAN = WORKFLOW_ROOT / "published" / "pilots" / "cdli_artifact_write_pilot_plan.csv"
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


def api_login() -> WikibaseIntegrator:
    username = os.environ.get("TW_USER") or input("TokenWorks username: ")
    password = os.environ.get("TW_PASS") or getpass.getpass("TokenWorks password: ")
    config["MEDIAWIKI_API_URL"] = TW_API
    config["PROPERTY_CONSTRAINTS_CHECK"] = False
    login = Login(user=username, password=password)
    return WikibaseIntegrator(login=login)


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=5, max=60),
    retry=retry_if_exception_type(Exception),
)
def robust_write(entity, summary: str, clear: bool = False):
    return entity.write(summary=summary, clear=clear)


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


def artifact_label_for(artifact: pd.Series) -> str:
    label = clean(artifact.get("label"))
    artifact_type = clean(artifact.get("artifact_type")).lower()
    if not label:
        cdli_id = clean(artifact.get("cdli_id"))
        label = f"CDLI P{cdli_id}" if cdli_id else "CDLI artifact"
    if label.lower().startswith(("cuneiform tablet", "cuneiform artifact")):
        return label[:250]
    if "tablet" in artifact_type:
        return f"Cuneiform Tablet {label}"[:250]
    return f"Cuneiform Artifact {label}"[:250]


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
        description += f"; CDLI P{cdli_id}"
    return description[:250]


def claim_from_row(row: pd.Series):
    prop = clean(row.get("tw_pid"))
    datatype = clean(row.get("datatype"))
    value = clean(row.get("value"))
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
    raise ValueError(f"Unsupported datatype in artifact write pilot: {datatype}")


def build_workset(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame]:
    artifacts = load_csv(args.artifacts)
    statements = load_csv(args.statements)
    reservations = load_csv(args.reservations)
    previous = load_many_csv([args.results, *args.prior_results])

    if artifacts.empty:
        raise RuntimeError(f"No artifact rows found in {args.artifacts}")
    if statements.empty:
        raise RuntimeError(f"No statement rows found in {args.statements}")
    if reservations.empty:
        raise RuntimeError(f"No QID reservation rows found in {args.reservations}")

    reserved = reservations[reservations["reservation_status"].eq("reserved")].copy()
    reserved = reserved[reserved["reserved_qid"].map(clean).ne("")]
    reserved = reserved.drop_duplicates("incoming_source_id", keep="last")
    if args.retry_errors_from:
        error_results = load_csv(args.retry_errors_from)
        if error_results.empty or "write_status" not in error_results.columns:
            raise RuntimeError(f"No write-status rows found in {args.retry_errors_from}")
        retry_cdli_ids = set(error_results.loc[error_results["write_status"].eq("error"), "cdli_id"].map(clean))
        current_results = load_csv(args.results)
        if not current_results.empty and {"cdli_id", "write_status"}.issubset(current_results.columns):
            already_retried = set(current_results.loc[current_results["write_status"].eq("written"), "cdli_id"].map(clean))
            retry_cdli_ids -= already_retried
        reserved = reserved[reserved["incoming_source_id"].map(clean).isin(retry_cdli_ids)].copy()
        previous = pd.DataFrame()
    if not args.repair_written and not previous.empty and {"cdli_id", "write_status"}.issubset(previous.columns):
        written = set(previous.loc[previous["write_status"].eq("written"), "cdli_id"].map(clean))
        reserved = reserved[~reserved["incoming_source_id"].map(clean).isin(written)]
    if args.limit:
        reserved = reserved.head(args.limit).copy()

    artifacts = artifacts.copy()
    artifacts["_cdli_key"] = artifacts["cdli_id"].map(clean)
    reserved = reserved.copy()
    reserved["_cdli_key"] = reserved["incoming_source_id"].map(clean)
    work = reserved.merge(artifacts, on="_cdli_key", how="left", suffixes=("_reservation", ""))
    work["cdli_id"] = work["_cdli_key"]
    work = work[work["label"].map(clean).ne("")]

    selected = set(work["cdli_id"].map(clean))
    plan = statements[
        statements["cdli_id"].map(clean).isin(selected)
        & statements["tw_qid"].map(clean).isin(set(work["reserved_qid"].map(clean)))
        & statements["plan_status"].eq("ready")
    ].copy()
    if not args.include_wikibase_item_claims:
        plan = plan[plan["datatype"].ne("wikibase-item")].copy()
    if args.only_field_names:
        fields = {field.strip() for field in args.only_field_names.split(",") if field.strip()}
        plan = plan[plan["field_name"].isin(fields)].copy()
    return work, plan


def add_ready_claims(item, plan: pd.DataFrame) -> int:
    count = 0
    for _, statement in plan.iterrows():
        claim = claim_from_row(statement)
        if claim is None:
            continue
        item.claims.add(claim, action_if_exists=ActionIfExists.APPEND_OR_REPLACE)
        count += 1
    return count


def reset_loaded_item_for_reuse(item) -> None:
    """Remove in-memory old item content before clear=True rewrite.

    WikibaseIntegrator loads the old claims/terms when fetching an existing
    item. `clear=True` only helps if the outgoing JSON does not still contain
    those old values, so we empty the local containers before adding artifact
    metadata.
    """

    item.claims.claims.clear()
    item.labels._LanguageValues__values.clear()
    item.descriptions._LanguageValues__values.clear()
    item.aliases._Aliases__aliases.clear()
    item.sitelinks.sitelinks.clear()


def write_pilot(args: argparse.Namespace) -> None:
    work, plan = build_workset(args)
    args.plan.parent.mkdir(parents=True, exist_ok=True)
    plan.to_csv(args.plan, index=False)

    print(f"artifact items to rewrite from reserved QIDs: {len(work)}")
    if len(plan):
        print("\nStatement plan summary:")
        print(plan.groupby(["field_name", "plan_status", "datatype"]).size().reset_index(name="count").to_string(index=False))
    preview_cols = ["reserved_qid", "cdli_id", "label", "artifact_type", "period", "provenience", "primary_collection"]
    print("\nItem preview:")
    print(work[[col for col in preview_cols if col in work.columns]].head(args.preview).to_string(index=False))

    if not args.write:
        print("\nDRY_RUN: no artifact items written. Pass --write --clear-existing to rewrite reserved QIDs.")
        return
    if not args.clear_existing:
        raise RuntimeError("Refusing to rewrite reserved QIDs without --clear-existing.")

    results = load_csv(args.results)
    if results.empty:
        results = pd.DataFrame()
    rows = []
    wbi = api_login()
    for _, artifact in tqdm(work.iterrows(), total=len(work)):
        cdli_id = clean(artifact.get("cdli_id"))
        qid = clean(artifact.get("reserved_qid"))
        item_plan = plan[plan["tw_qid"].map(clean).eq(qid)].copy()
        try:
            item = wbi.item.get(entity_id=qid)
            reset_loaded_item_for_reuse(item)
            label = artifact_label_for(artifact)
            item.labels.set(language="en", value=label)
            item.descriptions.set(language="en", value=description_for(artifact))
            aliases = alias_values(artifact)
            if aliases:
                item.aliases.set(language="en", values=aliases, action_if_exists=ActionIfExists.APPEND_OR_REPLACE)
            claim_count = add_ready_claims(item, item_plan)
            written = robust_write(item, f"Reuse TokenWorks QID for CDLI artifact P{cdli_id}: {label[:80]}", clear=True)
            print(f"rewritten {written.id} — {label} ({claim_count} claims)", flush=True)
            rows.append(
                {
                    "cdli_id": cdli_id,
                    "tw_qid": written.id,
                    "artifact_label": label,
                    "ready_claims_written": claim_count,
                    "write_status": "written",
                    "write_error": "",
                }
            )
            time.sleep(args.sleep)
        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"[:500]
            print(f"row error: {qid} / P{cdli_id} — {message}", flush=True)
            rows.append(
                {
                    "cdli_id": cdli_id,
                    "tw_qid": qid,
                    "artifact_label": artifact_label_for(artifact),
                    "ready_claims_written": 0,
                    "write_status": "error",
                    "write_error": message,
                }
            )
            pd.concat([results, pd.DataFrame(rows)], ignore_index=True).drop_duplicates(["cdli_id", "tw_qid"], keep="last").to_csv(
                args.results, index=False
            )
            if not args.continue_on_row_error:
                raise
            time.sleep(args.sleep)
        finally:
            pd.concat([results, pd.DataFrame(rows)], ignore_index=True).drop_duplicates(["cdli_id", "tw_qid"], keep="last").to_csv(
                args.results, index=False
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, default=DEFAULT_ARTIFACTS)
    parser.add_argument("--statements", type=Path, default=DEFAULT_STATEMENTS)
    parser.add_argument("--reservations", type=Path, default=DEFAULT_RESERVATIONS)
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
    parser.add_argument(
        "--include-wikibase-item-claims",
        action="store_true",
        help="Also write item-valued claims. Use only after the referenced TokenWorks Q-items exist.",
    )
    parser.add_argument("--write", action="store_true", help="Actually write to TokenWorks. Omit for dry-run.")
    parser.add_argument("--clear-existing", action="store_true", help="Required with --write when reusing old duplicate-publication QIDs.")
    parser.add_argument("--repair-written", action="store_true", help="Reprocess rows already marked written in the results CSV.")
    parser.add_argument("--retry-errors-from", type=Path, help="Only reprocess rows marked error in this previous results CSV.")
    parser.add_argument("--continue-on-row-error", action="store_true")
    args = parser.parse_args()
    write_pilot(args)


if __name__ == "__main__":
    main()
