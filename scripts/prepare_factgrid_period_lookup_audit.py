#!/usr/bin/env python3
"""Summarize unresolved CDLI period lookup coverage from the live FactGrid audit."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


WORKFLOW_ROOT = Path(__file__).resolve().parents[1]
PILOT_ROOT = WORKFLOW_ROOT / "published" / "pilots"
AUDIT_ROOT = WORKFLOW_ROOT / "published" / "period_audit"
DEFAULT_AUDIT = AUDIT_ROOT / "factgrid_period_claim_audit.csv"
DEFAULT_ARTIFACTS = PILOT_ROOT / "cdli_artifact_staging_tranche_35001_60000.csv"
DEFAULT_STATEMENTS = PILOT_ROOT / "cdli_artifact_statement_staging_tranche_35001_60000.csv"
DEFAULT_REVIEW = AUDIT_ROOT / "factgrid_period_lookup_gap_review.csv"
DEFAULT_SUMMARY = AUDIT_ROOT / "factgrid_period_lookup_gap_summary.csv"
DEFAULT_STATUS_SUMMARY = AUDIT_ROOT / "factgrid_period_lookup_gap_status_summary.csv"


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, low_memory=False).fillna("")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--artifacts", type=Path, default=DEFAULT_ARTIFACTS)
    parser.add_argument("--statements", type=Path, default=DEFAULT_STATEMENTS)
    parser.add_argument("--review", type=Path, default=DEFAULT_REVIEW)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--status-summary", type=Path, default=DEFAULT_STATUS_SUMMARY)
    args = parser.parse_args()

    audit = read_csv(args.audit)
    artifacts = read_csv(args.artifacts)
    statements = read_csv(args.statements)
    if audit.empty:
        raise RuntimeError(f"No audit rows found in {args.audit}")
    if artifacts.empty:
        raise RuntimeError(f"No artifact rows found in {args.artifacts}")

    period_statements = pd.DataFrame(columns=["cdli_id", "statement_value", "statement_value_label", "statement_status", "statement_source"])
    if not statements.empty:
        period_statements = statements[statements["field_name"].eq("period")].copy()
        period_statements = period_statements[
            ["cdli_id", "value", "value_label", "plan_status", "source"]
        ].rename(
            columns={
                "value": "statement_value",
                "value_label": "statement_value_label",
                "plan_status": "statement_status",
                "source": "statement_source",
            }
        )

    artifact_columns = [
        "cdli_id",
        "label",
        "artifact_type",
        "period_id",
        "period",
        "period_time_range",
        "provenience",
        "primary_collection",
    ]
    review = (
        audit.merge(artifacts[[c for c in artifact_columns if c in artifacts.columns]], on="cdli_id", how="left")
        .merge(period_statements, on="cdli_id", how="left")
        .fillna("")
    )
    review = review[review["audit_status"].isin(["unexpected_live_period", "no_expected_no_live", "missing_live_period"])].copy()

    review_columns = [
        "audit_status",
        "cdli_id",
        "factgrid_qid",
        "live_cdli_id",
        "live_label_en",
        "live_description_en",
        "label",
        "artifact_type",
        "period_id",
        "period",
        "period_time_range",
        "statement_status",
        "statement_value",
        "statement_value_label",
        "live_period_property",
        "live_period_qid",
        "live_period_label",
        "provenience",
        "primary_collection",
    ]
    review = review[[c for c in review_columns if c in review.columns]].sort_values(
        ["audit_status", "period_id", "period", "live_period_qid", "cdli_id"]
    )

    summary = (
        review.groupby(
            [
                "audit_status",
                "period_id",
                "period",
                "period_time_range",
                "statement_status",
                "live_period_qid",
                "live_period_label",
            ],
            dropna=False,
        )
        .size()
        .rename("count")
        .reset_index()
        .sort_values(["audit_status", "count"], ascending=[True, False])
    )
    status_summary = review["audit_status"].value_counts(dropna=False).rename_axis("audit_status").reset_index(name="count")

    for path, frame in [(args.review, review), (args.summary, summary), (args.status_summary, status_summary)]:
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(path, index=False)

    print(status_summary.to_string(index=False))
    print("\nTop lookup gaps:")
    print(summary.head(30).to_string(index=False))
    print(f"Wrote review -> {args.review}")
    print(f"Wrote summary -> {args.summary}")
    print(f"Wrote status summary -> {args.status_summary}")


if __name__ == "__main__":
    main()
