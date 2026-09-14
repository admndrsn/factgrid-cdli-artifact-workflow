#!/usr/bin/env python3
"""Prepare vetted FactGrid period-claim repairs from a live-state audit."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd


WORKFLOW_ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = WORKFLOW_ROOT / "published" / "period_audit"
DEFAULT_AUDIT = AUDIT_ROOT / "factgrid_period_claim_audit.csv"
DEFAULT_OUTPUT = AUDIT_ROOT / "factgrid_period_claim_repair_candidates_live_cdli_verified.csv"
DEFAULT_SUMMARY = AUDIT_ROOT / "factgrid_period_claim_repair_candidates_live_cdli_verified_summary.csv"


def clean(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none", "null"} else text


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, low_memory=False).fillna("")


def cdli_key(value: object) -> str:
    digits = re.sub(r"\D+", "", clean(value))
    return digits.lstrip("0") or ("0" if digits else "")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    args = parser.parse_args()

    audit = read_csv(args.audit)
    required = {
        "audit_status",
        "cdli_id",
        "factgrid_qid",
        "live_cdli_id",
        "live_period_property",
        "live_period_qid",
        "live_period_label",
        "expected_period_qid",
        "expected_period_label",
    }
    missing = required - set(audit.columns)
    if missing:
        raise RuntimeError(f"Audit CSV missing columns: {sorted(missing)}")

    rows = audit[
        audit["audit_status"].eq("mismatch")
        & audit["factgrid_qid"].map(clean).str.fullmatch(r"Q\d+", na=False)
        & audit["live_period_property"].map(clean).str.fullmatch(r"P\d+", na=False)
        & audit["live_period_qid"].map(clean).str.fullmatch(r"Q\d+", na=False)
        & audit["expected_period_qid"].map(clean).str.fullmatch(r"Q\d+", na=False)
    ].copy()
    rows["cdli_key"] = rows["cdli_id"].map(cdli_key)
    rows["live_cdli_key"] = rows["live_cdli_id"].map(cdli_key)
    rows = rows[rows["cdli_key"].eq(rows["live_cdli_key"]) & rows["cdli_key"].ne("")].copy()
    rows["correct_period_qid"] = rows["expected_period_qid"]
    rows["repair_status"] = "ready"
    rows["repair_note"] = (
        "Replace live period claim with the period expected from the current live FactGrid P692 CDLI ID."
    )
    columns = [
        "repair_status",
        "cdli_id",
        "live_cdli_id",
        "factgrid_qid",
        "artifact_label",
        "live_label_en",
        "live_description_en",
        "live_period_property",
        "live_period_qid",
        "live_period_label",
        "expected_period_label",
        "correct_period_qid",
        "repair_note",
    ]
    rows = rows[[col for col in columns if col in rows.columns]].drop_duplicates()

    summary = (
        rows.groupby(["live_period_label", "expected_period_label", "live_period_qid", "correct_period_qid"], dropna=False)
        .size()
        .rename("count")
        .reset_index()
        .sort_values("count", ascending=False)
    )
    summary_total = pd.DataFrame(
        [
            {"metric": "repair_candidate_rows", "value": len(rows)},
            {"metric": "repair_candidate_items", "value": rows["factgrid_qid"].nunique() if not rows.empty else 0},
        ]
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    rows.to_csv(args.output, index=False)
    pd.concat([summary_total, summary], ignore_index=True).to_csv(args.summary, index=False)
    print(f"period repair candidates: {len(rows)}")
    if len(rows):
        print(
            rows[
                [
                    "cdli_id",
                    "factgrid_qid",
                    "live_label_en",
                    "live_period_label",
                    "live_period_qid",
                    "expected_period_label",
                    "correct_period_qid",
                ]
            ]
            .head(20)
            .to_string(index=False)
        )
    print(f"Wrote candidates -> {args.output}")
    print(f"Wrote summary -> {args.summary}")


if __name__ == "__main__":
    main()
