#!/usr/bin/env python3
"""Build a prior FactGrid QID lookup from the OA/Kultepe tablet sheet.

The source Google Sheet has four header/meta rows and many columns prepared for
FactGrid import. For duplicate prevention we only need a narrow register:
CDLI IDs, OARE IDs, B-numbers, labels, aliases, and the existing FactGrid QID.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

from write_cdli_new_artifact_items import clean, format_cdli_id


WORKFLOW_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = WORKFLOW_ROOT / "inputs" / "factgrid_tablet_sources" / "FG_OA_Published_export.csv"
DEFAULT_OUTPUT = WORKFLOW_ROOT / "inputs" / "factgrid_tablet_sources" / "FG_OA_Published_prior_qid_lookup.csv"
DEFAULT_SUMMARY = WORKFLOW_ROOT / "inputs" / "factgrid_tablet_sources" / "FG_OA_Published_prior_qid_lookup_summary.csv"


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path, dtype=str, low_memory=False).fillna("")


def split_values(value: object) -> list[str]:
    text = clean(value)
    if not text:
        return []
    parts = re.split(r"\s*\|\s*|;\s*", text)
    return [clean(part) for part in parts if clean(part)]


def qid_number(qid: str) -> int:
    match = re.fullmatch(r"Q(\d+)", clean(qid))
    return int(match.group(1)) if match else 10**18


def cdli_key(value: object) -> str:
    text = clean(value)
    if not text:
        return ""
    return format_cdli_id(text)


def complete_aliases(row: pd.Series) -> list[str]:
    aliases: list[str] = []
    for column in ["Aen2", "Aen1", "Aen3", "Len"]:
        for value in split_values(row.get(column)):
            if value and value not in aliases:
                aliases.append(value)
    return aliases


def add_record(records: list[dict[str, str]], row: pd.Series, key_type: str, key_value: str) -> None:
    key_value = clean(key_value)
    qid = clean(row.get("FG_qid"))
    if not re.fullmatch(r"Q\d+", qid) or not key_value:
        return
    records.append(
        {
            "match_key_type": key_type,
            "match_key": key_value,
            "factgrid_qid": qid,
            "factgrid_qid_number": str(qid_number(qid)),
            "source_label": clean(row.get("Len")),
            "source_aliases_en": " | ".join(complete_aliases(row)),
            "source_cdli_id_raw": clean(row.get("P2474")),
            "source_oare_id": clean(row.get("Unnamed: 6")),
            "source_b_number": clean(row.get("WD")),
        }
    )


def build_lookup(source: Path) -> pd.DataFrame:
    df = read_csv(source)
    required = {"FG_qid", "P2474", "Len", "Unnamed: 6", "Aen1", "Aen2", "WD"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise RuntimeError(f"{source} is missing expected columns: {', '.join(missing)}")

    records: list[dict[str, str]] = []
    for _, row in df.iterrows():
        qid = clean(row.get("FG_qid"))
        if not re.fullmatch(r"Q\d+", qid):
            continue
        for value in split_values(row.get("P2474")):
            key = cdli_key(value)
            if key:
                add_record(records, row, "cdli_id", key)
        oare_id = clean(row.get("Unnamed: 6"))
        if oare_id:
            add_record(records, row, "oare_id", oare_id)
        b_number = clean(row.get("WD"))
        if re.fullmatch(r"B\d+", b_number):
            add_record(records, row, "b_number", b_number)

    if not records:
        return pd.DataFrame(
            columns=[
                "match_key_type",
                "match_key",
                "factgrid_qid",
                "factgrid_qid_number",
                "source_label",
                "source_aliases_en",
                "source_cdli_id_raw",
                "source_oare_id",
                "source_b_number",
            ]
        )
    out = pd.DataFrame(records)
    out = out.sort_values(["match_key_type", "match_key", "factgrid_qid_number"], kind="stable")
    out = out.drop_duplicates(["match_key_type", "match_key"], keep="first")
    return out


def write_summary(lookup: pd.DataFrame, summary_path: Path) -> None:
    rows = [
        {"metric": "lookup_rows", "value": len(lookup)},
        {"metric": "unique_factgrid_qids", "value": lookup["factgrid_qid"].nunique() if not lookup.empty else 0},
    ]
    if not lookup.empty:
        for key_type, count in lookup["match_key_type"].value_counts().sort_index().items():
            rows.append({"metric": f"{key_type}_keys", "value": int(count)})
    pd.DataFrame(rows).to_csv(summary_path, index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--preview", type=int, default=20)
    args = parser.parse_args()

    lookup = build_lookup(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    lookup.to_csv(args.output, index=False)
    write_summary(lookup, args.summary)

    print(f"Wrote prior FactGrid QID lookup -> {args.output}")
    print(f"Wrote summary -> {args.summary}")
    print(pd.read_csv(args.summary).to_string(index=False))
    if len(lookup):
        print("\nPreview:")
        print(lookup.head(args.preview).to_string(index=False))


if __name__ == "__main__":
    main()
