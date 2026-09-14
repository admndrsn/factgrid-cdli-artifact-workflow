#!/usr/bin/env python3
"""Prepare a FactGrid QID reuse pool from duplicate artifact reconciliation.

The duplicate QIDs are not deleted. They become candidates for deliberate
future reuse after the older canonical item has been repaired and the old
identity is preserved in this CSV.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

from write_cdli_new_artifact_items import clean


WORKFLOW_ROOT = Path(__file__).resolve().parents[1]
PILOT_ROOT = WORKFLOW_ROOT / "published" / "pilots"
DEFAULT_RECONCILIATION = PILOT_ROOT / "factgrid_cdli_artifact_duplicate_reconciliation_staging.csv"
DEFAULT_CANONICAL_REPAIR_RESULTS = PILOT_ROOT / "factgrid_cdli_artifact_duplicate_canonical_repair_results.csv"
DEFAULT_OUTPUT = PILOT_ROOT / "factgrid_cdli_artifact_qid_reuse_pool.csv"
DEFAULT_SUMMARY = PILOT_ROOT / "factgrid_cdli_artifact_qid_reuse_pool_summary.csv"


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, low_memory=False).fillna("")


def qid_number(qid: object) -> int:
    match = re.fullmatch(r"Q(\d+)", clean(qid))
    return int(match.group(1)) if match else 10**18


def prepare_pool(args: argparse.Namespace) -> pd.DataFrame:
    reconciliation = read_csv(args.reconciliation)
    if reconciliation.empty:
        raise RuntimeError(f"No reconciliation rows found in {args.reconciliation}")
    repairs = read_csv(args.canonical_repair_results)
    repaired_cdli_ids = set()
    if not repairs.empty and {"cdli_id", "repair_status"}.issubset(repairs.columns):
        repaired_cdli_ids = set(repairs.loc[repairs["repair_status"].eq("written"), "cdli_id"].map(clean))

    rows = []
    for _, row in reconciliation.iterrows():
        cdli_id = clean(row.get("cdli_id"))
        duplicate_qid = clean(row.get("duplicate_factgrid_qid"))
        canonical_qid = clean(row.get("canonical_factgrid_qid"))
        if not re.fullmatch(r"Q\d+", duplicate_qid) or not re.fullmatch(r"Q\d+", canonical_qid):
            continue
        status = "candidate" if cdli_id in repaired_cdli_ids else "hold_until_canonical_repair"
        rows.append(
            {
                "reuse_pool_status": status,
                "reuse_candidate_class": "accidental_cdli_duplicate",
                "qid_available_for_future_entity": duplicate_qid,
                "canonical_factgrid_qid": canonical_qid,
                "old_cdli_id": cdli_id,
                "old_duplicate_label_to_preserve": clean(row.get("duplicate_label")),
                "canonical_label": clean(row.get("canonical_label")),
                "old_aliases_to_preserve": clean(row.get("suggested_aliases_en")),
                "reuse_precondition_1": "canonical_factgrid_qid has received useful aliases and missing claims",
                "reuse_precondition_2": "old duplicate identity is preserved in this CSV before the item is repurposed",
                "reuse_precondition_3": "manual approval or future_reuse_status=approved before clear=True rewrite",
                "future_entity_type": "",
                "future_entity_label": "",
                "future_reuse_status": "",
            }
        )
    out = pd.DataFrame(rows)
    if not out.empty:
        out["_qid_number"] = out["qid_available_for_future_entity"].map(qid_number)
        out = out.sort_values("_qid_number", kind="stable").drop(columns=["_qid_number"])
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reconciliation", type=Path, default=DEFAULT_RECONCILIATION)
    parser.add_argument("--canonical-repair-results", type=Path, default=DEFAULT_CANONICAL_REPAIR_RESULTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--preview", type=int, default=20)
    args = parser.parse_args()

    pool = prepare_pool(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    pool.to_csv(args.output, index=False)
    summary = (
        pool.groupby(["reuse_pool_status", "reuse_candidate_class"], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(["reuse_pool_status", "reuse_candidate_class"])
        if not pool.empty
        else pd.DataFrame(columns=["reuse_pool_status", "reuse_candidate_class", "count"])
    )
    summary.to_csv(args.summary, index=False)
    print(summary.to_string(index=False))
    print(f"Wrote FactGrid artifact reuse pool -> {args.output}")
    print(f"Wrote summary -> {args.summary}")
    if len(pool):
        print("\nPreview:")
        print(pool.head(args.preview).to_string(index=False))


if __name__ == "__main__":
    main()
