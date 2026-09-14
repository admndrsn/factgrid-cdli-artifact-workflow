#!/usr/bin/env python3
"""Stage missing finding-spot authority items from the context audit."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


WORKFLOW_ROOT = Path(__file__).resolve().parents[1]
PILOT_ROOT = WORKFLOW_ROOT / "published" / "pilots"
DEFAULT_AUDIT = PILOT_ROOT / "finding_spot_context_audit.csv"
DEFAULT_OUTPUT = PILOT_ROOT / "finding_spot_missing_authority_item_staging.csv"
DEFAULT_SUMMARY = PILOT_ROOT / "finding_spot_missing_authority_item_staging_summary.csv"


def clean(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null"}:
        return ""
    if text.endswith(".0") and text[:-2].isdigit():
        return text[:-2]
    return text


def pipe_join(values) -> str:
    seen = set()
    out = []
    for value in values:
        text = clean(value)
        if not text or text in seen:
            continue
        out.append(text)
        seen.add(text)
    return " | ".join(out)


def prepare(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame]:
    audit = pd.read_csv(args.audit, dtype=str, low_memory=False).fillna("")
    rows = audit[
        audit["audit_status"].eq("missing_expected_tw_qid")
        & audit["expected_factgrid_qid"].map(clean).ne("")
        & audit["expected_label"].map(clean).ne("")
    ].copy()
    if args.limit_context_rows:
        rows = rows.head(args.limit_context_rows).copy()

    grouped = []
    for fg_qid, group in rows.groupby("expected_factgrid_qid", sort=True):
        label = clean(group["expected_label"].mode().iloc[0] if len(group["expected_label"].mode()) else group["expected_label"].iloc[0])
        aliases = pipe_join(group["finding_spot_context"].unique())
        grouped.append(
            {
                "factgrid_qid": clean(fg_qid),
                "label_en": label,
                "description_en": f"CDLI provenience / finding spot authority value; aligned with FactGrid {clean(fg_qid)}",
                "aliases_en": aliases if aliases != label else "",
                "source_fields": "finding_spot",
                "source_count": len(group),
                "source_cdli_count": group["cdli_id"].map(clean).nunique(),
                "source_contexts": aliases,
                "tw_qid": "",
                "create_status": "",
                "create_error": "",
            }
        )

    out = pd.DataFrame(grouped).sort_values(["source_count", "label_en"], ascending=[False, True])
    if args.limit_items:
        out = out.head(args.limit_items).copy()
    summary = pd.DataFrame(
        [
            {"metric": "audit_rows_missing_expected_tw_qid", "value": len(rows)},
            {"metric": "authority_items_to_stage", "value": len(out)},
            {"metric": "source_cdli_count", "value": int(rows["cdli_id"].map(clean).nunique()) if not rows.empty else 0},
        ]
    )
    return out, summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--limit-context-rows", type=int, default=0)
    parser.add_argument("--limit-items", type=int, default=0)
    parser.add_argument("--preview", type=int, default=30)
    args = parser.parse_args()

    out, summary = prepare(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output, index=False)
    summary.to_csv(args.summary, index=False)
    print(summary.to_string(index=False))
    if args.preview and not out.empty:
        print(out.head(args.preview).to_string(index=False))
    print(f"Wrote missing finding-spot authority staging -> {args.output}")
    print(f"Wrote summary -> {args.summary}")


if __name__ == "__main__":
    main()
