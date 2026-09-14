#!/usr/bin/env python3
"""Stage duplicate reconciliation actions for FactGrid CDLI artifact writes.

This compares newly written FactGrid artifact results against an older prior-QID
lookup, such as the OA/Kultepe sheet export. When a current result created a
larger QID for a CDLI ID that already has an older FactGrid QID, the older QID
is treated as canonical.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

from write_cdli_new_artifact_items import clean, format_cdli_id


WORKFLOW_ROOT = Path(__file__).resolve().parents[1]
PILOT_ROOT = WORKFLOW_ROOT / "published" / "pilots"
DEFAULT_RESULTS = PILOT_ROOT / "factgrid_cdli_artifact_write_results_tranche_10001_35000.csv"
DEFAULT_LOOKUP = WORKFLOW_ROOT / "inputs" / "factgrid_tablet_sources" / "FG_OA_Published_prior_qid_lookup.csv"
DEFAULT_OUTPUT = PILOT_ROOT / "factgrid_cdli_artifact_duplicate_reconciliation_staging.csv"
DEFAULT_SUMMARY = PILOT_ROOT / "factgrid_cdli_artifact_duplicate_reconciliation_summary.csv"


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, low_memory=False).fillna("")


def qid_number(qid: object) -> int:
    match = re.fullmatch(r"Q(\d+)", clean(qid))
    return int(match.group(1)) if match else 10**18


def split_aliases(value: object) -> list[str]:
    return [clean(part) for part in clean(value).split("|") if clean(part)]


def build_reconciliation(results_path: Path, lookup_path: Path) -> pd.DataFrame:
    results = read_csv(results_path)
    lookup = read_csv(lookup_path)
    if results.empty or lookup.empty:
        return pd.DataFrame()
    required_results = {"cdli_id", "factgrid_qid", "artifact_label", "write_action", "write_status"}
    required_lookup = {"match_key_type", "match_key", "factgrid_qid", "source_label", "source_aliases_en"}
    if not required_results.issubset(results.columns):
        raise RuntimeError(f"{results_path} is missing expected columns: {sorted(required_results - set(results.columns))}")
    if not required_lookup.issubset(lookup.columns):
        raise RuntimeError(f"{lookup_path} is missing expected columns: {sorted(required_lookup - set(lookup.columns))}")

    prior = lookup[lookup["match_key_type"].eq("cdli_id")].copy()
    prior["_cdli_id"] = prior["match_key"].map(format_cdli_id)
    prior = prior.sort_values("_cdli_id", kind="stable").drop_duplicates("_cdli_id", keep="first")

    written = results[results["write_status"].eq("written")].copy()
    written["_cdli_id"] = written["cdli_id"].map(format_cdli_id)
    merged = written.merge(prior, on="_cdli_id", how="inner", suffixes=("_written", "_prior"))

    rows: list[dict[str, str]] = []
    for _, row in merged.iterrows():
        duplicate_qid = clean(row.get("factgrid_qid_written"))
        canonical_qid = clean(row.get("factgrid_qid_prior"))
        if not re.fullmatch(r"Q\d+", duplicate_qid) or not re.fullmatch(r"Q\d+", canonical_qid):
            continue
        if qid_number(canonical_qid) >= qid_number(duplicate_qid):
            continue
        aliases: list[str] = []
        for value in [row.get("artifact_label"), row.get("source_label")]:
            value = clean(value)
            if value and value not in aliases:
                aliases.append(value)
        for value in split_aliases(row.get("source_aliases_en")):
            if value and value not in aliases:
                aliases.append(value)
        rows.append(
            {
                "cdli_id": clean(row.get("_cdli_id")),
                "canonical_factgrid_qid": canonical_qid,
                "duplicate_factgrid_qid": duplicate_qid,
                "canonical_label": clean(row.get("source_label")),
                "duplicate_label": clean(row.get("artifact_label")),
                "suggested_aliases_en": " | ".join(aliases),
                "recommended_action": "keep_smaller_qid_add_aliases_and_missing_claims",
                "write_action_seen": clean(row.get("write_action")),
            }
        )
    return pd.DataFrame(rows).sort_values(["canonical_factgrid_qid", "duplicate_factgrid_qid"], kind="stable")


def write_summary(staging: pd.DataFrame, summary_path: Path) -> None:
    rows = [
        {"metric": "duplicate_reconciliation_rows", "value": len(staging)},
        {"metric": "canonical_qids", "value": staging["canonical_factgrid_qid"].nunique() if not staging.empty else 0},
        {"metric": "duplicate_qids", "value": staging["duplicate_factgrid_qid"].nunique() if not staging.empty else 0},
    ]
    pd.DataFrame(rows).to_csv(summary_path, index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--lookup", type=Path, default=DEFAULT_LOOKUP)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--preview", type=int, default=20)
    args = parser.parse_args()

    staging = build_reconciliation(args.results, args.lookup)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    staging.to_csv(args.output, index=False)
    write_summary(staging, args.summary)

    print(f"Wrote duplicate reconciliation staging -> {args.output}")
    print(f"Wrote summary -> {args.summary}")
    print(pd.read_csv(args.summary).to_string(index=False))
    if len(staging):
        print("\nPreview:")
        print(staging.head(args.preview).to_string(index=False))


if __name__ == "__main__":
    main()
