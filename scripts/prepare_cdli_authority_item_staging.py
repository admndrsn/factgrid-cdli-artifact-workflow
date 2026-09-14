#!/usr/bin/env python3
"""Prepare TokenWorks authority-item staging from CDLI artifact statements.

The artifact statement staging currently carries FactGrid QIDs for authority
values such as material, period, language, provenience, collection, and object
type. Those QIDs cannot be written directly to TokenWorks. This script dedupes
the authority values and prepares one TokenWorks item-create row per FactGrid
QID.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


WORKFLOW_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATEMENTS = WORKFLOW_ROOT / "published" / "pilots" / "cdli_artifact_statement_staging_pilot_10000_with_lookups.csv"
DEFAULT_RESULTS = WORKFLOW_ROOT / "published" / "pilots" / "cdli_authority_item_staging_pilot_10000.csv"
DEFAULT_SUMMARY = WORKFLOW_ROOT / "published" / "pilots" / "cdli_authority_item_staging_pilot_10000_summary.csv"


FIELD_DESCRIPTIONS = {
    "finding_spot": "CDLI provenience / finding spot authority value",
    "instance_of": "CDLI artifact type authority value",
    "language": "CDLI language authority value",
    "material": "CDLI material authority value",
    "period": "CDLI period/style authority value",
    "present_holding": "CDLI holding institution or collection authority value",
    "type_of_work": "CDLI genre / type of work authority value",
}


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


def prepare(args: argparse.Namespace) -> pd.DataFrame:
    statements = pd.read_csv(args.statements, dtype=str, low_memory=False).fillna("")
    existing_factgrid_qids = set()
    for path in args.existing_authority_results:
        if not path.exists():
            continue
        existing = pd.read_csv(path, dtype=str, low_memory=False).fillna("")
        if {"factgrid_qid", "tw_qid"}.issubset(existing.columns):
            existing_factgrid_qids.update(
                existing.loc[
                    existing["factgrid_qid"].map(clean).ne("") & existing["tw_qid"].map(clean).ne(""),
                    "factgrid_qid",
                ].map(clean)
            )
    item_rows = statements[
        statements["datatype"].eq("wikibase-item")
        & statements["plan_status"].eq("ready")
        & statements["value"].map(clean).str.match(r"^Q\d+$")
        & statements["value_label"].map(clean).ne("")
    ].copy()
    if args.only_cdli_ids:
        cdli_ids = {clean(part) for part in args.only_cdli_ids.split(",") if clean(part)}
        item_rows = item_rows[item_rows["cdli_id"].map(clean).isin(cdli_ids)].copy()
    if args.only_field_names:
        fields = {clean(part) for part in args.only_field_names.split(",") if clean(part)}
        item_rows = item_rows[item_rows["field_name"].isin(fields)].copy()

    grouped = []
    for fg_qid, group in item_rows.groupby("value", sort=True):
        label = clean(group["value_label"].mode().iloc[0] if len(group["value_label"].mode()) else group["value_label"].iloc[0])
        fields = pipe_join(sorted(group["field_name"].unique()))
        field_for_description = clean(group["field_name"].iloc[0])
        description = FIELD_DESCRIPTIONS.get(field_for_description, "CDLI authority value")
        grouped.append(
            {
                "factgrid_qid": clean(fg_qid),
                "label_en": label,
                "description_en": f"{description}; aligned with FactGrid {clean(fg_qid)}",
                "aliases_en": "",
                "source_fields": fields,
                "source_count": len(group),
                "source_cdli_count": group["cdli_id"].map(clean).nunique(),
                "tw_qid": "",
                "create_status": "",
                "create_error": "",
            }
        )

    out = pd.DataFrame(grouped).sort_values(["source_count", "label_en"], ascending=[False, True])
    if existing_factgrid_qids and not out.empty:
        out = out[~out["factgrid_qid"].isin(existing_factgrid_qids)].copy()
    if args.limit:
        out = out.head(args.limit).copy()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output, index=False)
    summary = (
        out.assign(source_fields=out["source_fields"].str.split(" \\| "))
        .explode("source_fields")
        .groupby("source_fields", dropna=False)
        .agg(authority_items=("factgrid_qid", "count"), source_count=("source_count", "sum"))
        .reset_index()
        .rename(columns={"source_fields": "field_name"})
        .sort_values(["source_count", "authority_items"], ascending=[False, False])
    )
    summary.to_csv(args.summary, index=False)

    print(f"authority items staged: {len(out)}")
    print("\nSummary:")
    print(summary.to_string(index=False))
    print("\nPreview:")
    print(out.head(args.preview).to_string(index=False))
    print(f"\nWrote staging -> {args.output}")
    print(f"Wrote summary -> {args.summary}")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--statements", type=Path, default=DEFAULT_STATEMENTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--only-cdli-ids", default="", help="Optional comma-separated CDLI IDs for a tiny authority pilot.")
    parser.add_argument("--only-field-names", default="", help="Optional comma-separated field names to stage.")
    parser.add_argument(
        "--existing-authority-results",
        type=Path,
        action="append",
        default=[],
        help="Existing authority result CSV(s) with factgrid_qid/tw_qid to exclude from new staging.",
    )
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--preview", type=int, default=30)
    args = parser.parse_args()
    prepare(args)


if __name__ == "__main__":
    main()
