#!/usr/bin/env python3
"""Repair finding-spot claims flagged by the context audit.

This consumes ``finding_spot_context_audit.csv`` from
``audit_finding_spot_claims_from_context.py`` and repairs rows where the CDLI
context resolves to a concrete expected TokenWorks QID that differs from the
currently written P224 value.
"""

from __future__ import annotations

import argparse
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
DEFAULT_AUDIT = PILOT_ROOT / "finding_spot_context_audit.csv"
DEFAULT_RESULTS = PILOT_ROOT / "finding_spot_context_audit_repair_results.csv"
TW_API = "https://wikibase.tk-wiki-kg.com/w/api.php"
FINDING_SPOT_PID = "P224"


def clean(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null"}:
        return ""
    if text.endswith(".0") and text[:-2].isdigit():
        return text[:-2]
    return text


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, low_memory=False).fillna("")


def api_login() -> WikibaseIntegrator:
    username = os.environ.get("TW_USER") or input("TokenWorks username: ")
    password = os.environ.get("TW_PASS") or getpass.getpass("TokenWorks password: ")
    config["MEDIAWIKI_API_URL"] = TW_API
    config["PROPERTY_CONSTRAINTS_CHECK"] = False
    login = Login(user=username, password=password)
    return WikibaseIntegrator(login=login)


@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=2, min=5, max=60), retry=retry_if_exception_type(Exception), reraise=True)
def robust_write(entity, summary: str):
    return entity.write(summary=summary)


def claim_item_value(claim) -> str:
    try:
        value = claim.mainsnak.datavalue["value"]
        if isinstance(value, dict):
            return clean(value.get("id") or value.get("numeric-id"))
        return clean(value)
    except Exception:
        return ""


def build_plan(args: argparse.Namespace) -> pd.DataFrame:
    audit = load_csv(args.audit)
    if audit.empty:
        raise RuntimeError(f"No audit rows found in {args.audit}")
    required = {"tw_qid", "current_tokenworks_value_qid", "expected_tokenworks_qid", "audit_status"}
    missing = required - set(audit.columns)
    if missing:
        raise RuntimeError(f"Audit file missing required columns: {', '.join(sorted(missing))}")
    plan = audit[
        audit["audit_status"].eq("mismatch")
        & audit["current_tokenworks_value_qid"].map(clean).ne("")
        & audit["expected_tokenworks_qid"].map(clean).ne("")
        & audit["tw_qid"].map(clean).ne("")
    ].copy()
    previous = load_csv(args.results)
    if not previous.empty and {"tw_qid", "old_tokenworks_value_qid", "new_tokenworks_value_qid", "repair_status"}.issubset(previous.columns):
        written = set(
            zip(
                previous.loc[previous["repair_status"].eq("written"), "tw_qid"].map(clean),
                previous.loc[previous["repair_status"].eq("written"), "old_tokenworks_value_qid"].map(clean),
                previous.loc[previous["repair_status"].eq("written"), "new_tokenworks_value_qid"].map(clean),
            )
        )
        plan = plan[
            ~plan.apply(
                lambda row: (
                    clean(row.get("tw_qid")),
                    clean(row.get("current_tokenworks_value_qid")),
                    clean(row.get("expected_tokenworks_qid")),
                )
                in written,
                axis=1,
            )
        ].copy()
    plan["old_tokenworks_value_qid"] = plan["current_tokenworks_value_qid"].map(clean)
    plan["new_tokenworks_value_qid"] = plan["expected_tokenworks_qid"].map(clean)
    if args.limit:
        plan = plan.head(args.limit).copy()
    return plan


def repair_one(wbi: WikibaseIntegrator, qid: str, old_qid: str, new_qid: str) -> tuple[int, bool]:
    item = wbi.item.get(entity_id=qid)
    removed = 0
    already_has_new = False
    for claim in list(item.claims.get(FINDING_SPOT_PID)):
        value = claim_item_value(claim)
        if value == old_qid:
            claim.remove()
            removed += 1
        elif value == new_qid:
            already_has_new = True
    if not already_has_new:
        item.claims.add(
            datatypes.Item(prop_nr=FINDING_SPOT_PID, value=new_qid),
            action_if_exists=ActionIfExists.APPEND_OR_REPLACE,
        )
    robust_write(item, f"Repair finding spot from CDLI context on {qid}")
    return removed, not already_has_new


def repair(args: argparse.Namespace) -> pd.DataFrame:
    plan = build_plan(args)
    print(f"finding-spot context mismatches to repair: {len(plan)}")
    preview_cols = [
        "cdli_id",
        "tw_qid",
        "artifact_label",
        "finding_spot_context",
        "written_value_label",
        "expected_label",
        "old_tokenworks_value_qid",
        "new_tokenworks_value_qid",
    ]
    if len(plan):
        print(plan[[col for col in preview_cols if col in plan.columns]].head(args.preview).to_string(index=False))
    args.results.parent.mkdir(parents=True, exist_ok=True)
    if args.dry_run:
        plan.to_csv(args.results, index=False)
        print("DRY_RUN: no finding-spot claims repaired.")
        print(f"Wrote repair preview -> {args.results}")
        return plan

    previous = load_csv(args.results)
    rows = []
    wbi = api_login()
    for _, row in tqdm(plan.iterrows(), total=len(plan)):
        result = row.to_dict()
        qid = clean(row.get("tw_qid"))
        old_qid = clean(row.get("old_tokenworks_value_qid"))
        new_qid = clean(row.get("new_tokenworks_value_qid"))
        try:
            removed, added = repair_one(wbi, qid, old_qid, new_qid)
            result["removed_old_claim_count"] = str(removed)
            result["added_new_claim"] = "yes" if added else "already_present"
            result["repair_status"] = "written"
            result["repair_error"] = ""
            print(f"repaired {qid}: removed {removed} {FINDING_SPOT_PID}={old_qid}; added {new_qid}", flush=True)
        except Exception as exc:
            result["repair_status"] = "error"
            result["repair_error"] = f"{type(exc).__name__}: {exc}"[:500]
            print(f"repair error {qid}: {result['repair_error']}", flush=True)
            rows.append(result)
            pd.concat([previous, pd.DataFrame(rows)], ignore_index=True).drop_duplicates(
                ["tw_qid", "old_tokenworks_value_qid", "new_tokenworks_value_qid"],
                keep="last",
            ).to_csv(args.results, index=False)
            if not args.continue_on_row_error:
                raise
            time.sleep(args.sleep)
            continue
        rows.append(result)
        pd.concat([previous, pd.DataFrame(rows)], ignore_index=True).drop_duplicates(
            ["tw_qid", "old_tokenworks_value_qid", "new_tokenworks_value_qid"],
            keep="last",
        ).to_csv(args.results, index=False)
        time.sleep(args.sleep)
    return pd.concat([previous, pd.DataFrame(rows)], ignore_index=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--preview", type=int, default=30)
    parser.add_argument("--sleep", type=float, default=2.0)
    parser.add_argument("--dry-run", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--continue-on-row-error", action="store_true")
    args = parser.parse_args()
    repair(args)


if __name__ == "__main__":
    main()
