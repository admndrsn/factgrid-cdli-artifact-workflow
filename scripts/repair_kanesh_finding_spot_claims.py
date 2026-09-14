#!/usr/bin/env python3
"""Repair artifact finding-spot claims for Kanesh (mod. Kultepe).

The downloaded lookup row for ``Kanesh (mod. Kültepe)`` incorrectly mapped it
to FactGrid ``Q389713`` / Dah-e-No. Artifact claims written from that staging
therefore point to TokenWorks ``Q132027``. The correct existing TokenWorks
authority item for Kültepe/Kanesh is ``Q132050`` (FactGrid ``Q390036``).

This script prepares candidates from prior write-result CSVs and the statement
staging context rows, then replaces only ``P224 = Q132027`` on those specific
items with ``P224 = Q132050``.
"""

from __future__ import annotations

import argparse
import glob
import getpass
import os
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
PILOT_ROOT = WORKFLOW_ROOT / "published" / "pilots"
DEFAULT_STATEMENTS = PILOT_ROOT / "cdli_artifact_statement_staging_pilot_10000_with_lookups.csv"
DEFAULT_RESULTS_GLOB = str(PILOT_ROOT / "cdli_artifact_authority_claim*results*.csv")
DEFAULT_OUTPUT = PILOT_ROOT / "kanesh_finding_spot_repair_results.csv"
TW_API = "https://wikibase.tk-wiki-kg.com/w/api.php"
FINDING_SPOT_PID = "P224"
OLD_TW_QID = "Q132027"
NEW_TW_QID = "Q132050"


def clean(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null"}:
        return ""
    if text.endswith(".0") and text[:-2].isdigit():
        return text[:-2]
    return text


def api_login() -> WikibaseIntegrator:
    username = os.environ.get("TW_USER") or input("TokenWorks username: ")
    password = os.environ.get("TW_PASS") or getpass.getpass("TokenWorks password: ")
    config["MEDIAWIKI_API_URL"] = TW_API
    config["PROPERTY_CONSTRAINTS_CHECK"] = False
    login = Login(user=username, password=password)
    return WikibaseIntegrator(login=login)


@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=2, min=5, max=60), retry=retry_if_exception_type(Exception))
def robust_write(entity, summary: str):
    return entity.write(summary=summary)


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, low_memory=False).fillna("")


def load_written_results(pattern: str) -> pd.DataFrame:
    frames = []
    for filename in sorted(glob.glob(pattern)):
        df = load_csv(Path(filename))
        if df.empty:
            continue
        df["source_results_file"] = filename
        frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def build_context_map(statements: pd.DataFrame) -> dict[tuple[str, str], str]:
    if statements.empty:
        return {}
    context = statements[statements["field_name"].eq("finding_spot_context")].copy()
    return {
        (clean(row.get("cdli_id")), clean(row.get("tw_qid"))): clean(row.get("value"))
        for _, row in context.iterrows()
        if clean(row.get("cdli_id")) and clean(row.get("tw_qid"))
    }


def build_candidates(args: argparse.Namespace) -> pd.DataFrame:
    statements = load_csv(args.statements)
    results = load_written_results(args.results_glob)
    if statements.empty:
        raise RuntimeError(f"No statement staging found in {args.statements}")
    if results.empty:
        raise RuntimeError(f"No prior authority claim results matched {args.results_glob}")

    context_by_key = build_context_map(statements)
    rows = results[
        results["write_status"].eq("written")
        & results["field_name"].eq("finding_spot")
        & results["tw_pid"].eq(FINDING_SPOT_PID)
        & results["tokenworks_value_qid"].eq(args.old_qid)
    ].copy()
    rows["finding_spot_context"] = rows.apply(
        lambda row: context_by_key.get((clean(row.get("cdli_id")), clean(row.get("tw_qid"))), ""),
        axis=1,
    )
    rows = rows[rows["finding_spot_context"].map(lambda value: clean(value).casefold() == args.context.casefold())].copy()
    rows["old_tokenworks_value_qid"] = args.old_qid
    rows["new_tokenworks_value_qid"] = args.new_qid
    rows["repair_status"] = "not_started"
    rows["repair_error"] = ""
    rows = rows.drop_duplicates(["cdli_id", "tw_qid", "old_tokenworks_value_qid", "new_tokenworks_value_qid"])
    if args.limit:
        rows = rows.head(args.limit).copy()
    return rows


def claim_item_value(claim) -> str:
    try:
        value = claim.mainsnak.datavalue["value"]
        if isinstance(value, dict):
            return clean(value.get("id") or value.get("numeric-id"))
        return clean(value)
    except Exception:
        return ""


def repair_one(wbi: WikibaseIntegrator, qid: str, old_qid: str, new_qid: str) -> tuple[int, bool]:
    item = wbi.item.get(entity_id=qid)
    removed = 0
    for claim in list(item.claims.get(FINDING_SPOT_PID)):
        if claim_item_value(claim) == old_qid:
            claim.remove()
            removed += 1
    item.claims.add(
        datatypes.Item(prop_nr=FINDING_SPOT_PID, value=new_qid),
        action_if_exists=ActionIfExists.APPEND_OR_REPLACE,
    )
    robust_write(item, f"Repair Kanesh finding spot on {qid}")
    return removed, True


def repair(args: argparse.Namespace) -> pd.DataFrame:
    candidates = build_candidates(args)
    print(f"Kanesh finding-spot repair candidates: {len(candidates)}")
    preview_cols = [
        "cdli_id",
        "tw_qid",
        "artifact_label",
        "finding_spot_context",
        "old_tokenworks_value_qid",
        "new_tokenworks_value_qid",
    ]
    if len(candidates):
        print(candidates[[col for col in preview_cols if col in candidates.columns]].head(args.preview).to_string(index=False))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.dry_run:
        candidates.to_csv(args.output, index=False)
        print("DRY_RUN: no finding-spot claims repaired.")
        print(f"Wrote candidate preview -> {args.output}")
        return candidates

    previous = load_csv(args.output)
    if not previous.empty and {"tw_qid", "repair_status"}.issubset(previous.columns):
        done = set(previous.loc[previous["repair_status"].eq("written"), "tw_qid"].map(clean))
        candidates = candidates[~candidates["tw_qid"].map(clean).isin(done)].copy()

    rows = []
    wbi = api_login()
    for _, row in tqdm(candidates.iterrows(), total=len(candidates)):
        result = row.to_dict()
        qid = clean(row.get("tw_qid"))
        try:
            removed, added = repair_one(wbi, qid, args.old_qid, args.new_qid)
            result["removed_old_claim_count"] = str(removed)
            result["added_new_claim"] = "yes" if added else "no"
            result["repair_status"] = "written"
            result["repair_error"] = ""
            print(f"repaired {qid}: removed {removed} {FINDING_SPOT_PID}={args.old_qid}; added {args.new_qid}", flush=True)
        except Exception as exc:
            result["repair_status"] = "error"
            result["repair_error"] = f"{type(exc).__name__}: {exc}"[:500]
            print(f"repair error {qid}: {result['repair_error']}", flush=True)
            rows.append(result)
            pd.concat([previous, pd.DataFrame(rows)], ignore_index=True).drop_duplicates(
                ["tw_qid", "old_tokenworks_value_qid", "new_tokenworks_value_qid"],
                keep="last",
            ).to_csv(args.output, index=False)
            if not args.continue_on_row_error:
                raise
            time.sleep(args.sleep)
            continue
        rows.append(result)
        pd.concat([previous, pd.DataFrame(rows)], ignore_index=True).drop_duplicates(
            ["tw_qid", "old_tokenworks_value_qid", "new_tokenworks_value_qid"],
            keep="last",
        ).to_csv(args.output, index=False)
        time.sleep(args.sleep)
    return pd.concat([previous, pd.DataFrame(rows)], ignore_index=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--statements", type=Path, default=DEFAULT_STATEMENTS)
    parser.add_argument("--results-glob", default=DEFAULT_RESULTS_GLOB)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--old-qid", default=OLD_TW_QID)
    parser.add_argument("--new-qid", default=NEW_TW_QID)
    parser.add_argument("--context", default="Kanesh (mod. Kültepe)")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--preview", type=int, default=30)
    parser.add_argument("--sleep", type=float, default=2.0)
    parser.add_argument("--dry-run", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--continue-on-row-error", action="store_true")
    args = parser.parse_args()
    repair(args)


if __name__ == "__main__":
    main()
