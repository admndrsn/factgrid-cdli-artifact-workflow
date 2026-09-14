#!/usr/bin/env python3
"""Stage CDLI proveniences that do not yet have FactGrid QIDs.

The output is a review CSV for future TokenWorks authority item creation. It
does not write to TokenWorks.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd


WORKFLOW_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = WORKFLOW_ROOT / "inputs" / "cdli_lookup_sources" / "proveniences_safe_to_add.csv"
DEFAULT_OUTPUT = WORKFLOW_ROOT / "published" / "factgrid_model_samples" / "cdli_provenience_new_item_staging.csv"
DEFAULT_SUMMARY = WORKFLOW_ROOT / "published" / "factgrid_model_samples" / "cdli_provenience_new_item_staging_summary.csv"


def clean(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null"}:
        return ""
    return text


def norm(value: object) -> str:
    return re.sub(r"\s+", " ", clean(value).casefold())


def first_existing(df: pd.DataFrame, names: list[str]) -> str:
    lowered = {c.casefold(): c for c in df.columns}
    for name in names:
        if name.casefold() in lowered:
            return lowered[name.casefold()]
    return ""


def has_qid(value: object) -> bool:
    return bool(re.search(r"\bQ\d+\b", clean(value)))


def unique_join(values: list[object], sep: str = " | ") -> str:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = clean(value)
        if not text:
            continue
        key = norm(text)
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
    return sep.join(out)


def prepare(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame]:
    source = Path(args.input)
    if not source.exists():
        raise RuntimeError(f"Input not found: {source}")
    df = pd.read_csv(source, dtype=str).fillna("")
    if df.empty:
        raise RuntimeError(f"No rows found in {source}")

    label_col = first_existing(df, ["Len", "Aen (update)", "Aen", "Aen2", "provenience"])
    english_col = first_existing(df, ["Aen", "Aen (update)", "Aen2"])
    alt_cols = [col for col in ["alt_1", "alt_2", "Aen2"] if col in df.columns]
    fg_col = first_existing(df, ["FG-Q", "FG_qid", "factgrid_qid", "qid"])
    cdli_id_col = first_existing(df, ["P694", "id_text2", "CDLI_ID2"])
    coord_col = first_existing(df, ["P48", "coord", "coordinate"])
    p2_cols = [col for col in ["P2_1", "P2_2"] if col in df.columns]
    p131_cols = [col for col in ["P131_1", "P131_2"] if col in df.columns]
    if not label_col:
        raise RuntimeError(f"No label column found in {source}")

    rows: list[dict[str, str]] = []
    seen_labels: set[str] = set()
    for idx, row in df.iterrows():
        if fg_col and has_qid(row.get(fg_col)):
            continue
        label = clean(row.get(label_col)) or clean(row.get(english_col))
        if not label:
            continue
        label_key = norm(label)
        if label_key in seen_labels:
            continue
        seen_labels.add(label_key)
        aliases = unique_join([row.get(col) for col in alt_cols] + [row.get(english_col)])
        cdli_id2 = clean(row.get(cdli_id_col)) if cdli_id_col else ""
        coord = clean(row.get(coord_col)) if coord_col else ""
        rows.append(
            {
                "source_row_number": str(idx + 2),
                "label_en": label,
                "description_en": f"CDLI provenience authority item; not yet aligned to FactGrid",
                "aliases_en": aliases,
                "cdli_id2": cdli_id2,
                "coordinate": coord,
                "instance_of_source_values": unique_join([row.get(col) for col in p2_cols]),
                "research_project_source_values": unique_join([row.get(col) for col in p131_cols]),
                "source_sheet": source.name,
                "factgrid_qid": "",
                "tokenworks_qid": "",
                "review_status": "needs_review",
                "notes": "",
            }
        )

    out = pd.DataFrame(rows)
    summary = pd.DataFrame(
        [
            {"metric": "source_rows", "value": len(df)},
            {"metric": "staged_new_proveniences", "value": len(out)},
            {"metric": "rows_with_cdli_id2", "value": int(out["cdli_id2"].astype(bool).sum()) if not out.empty else 0},
            {"metric": "rows_with_coordinate", "value": int(out["coordinate"].astype(bool).sum()) if not out.empty else 0},
        ]
    )
    return out, summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=DEFAULT_INPUT)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", default=DEFAULT_SUMMARY)
    parser.add_argument("--preview", type=int, default=20)
    args = parser.parse_args()

    out, summary = prepare(args)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output, index=False)
    summary.to_csv(args.summary, index=False)
    print(summary.to_string(index=False))
    if args.preview:
        print(out.head(args.preview).to_string(index=False))
    print(f"Wrote new CDLI provenience staging -> {args.output}")
    print(f"Wrote summary -> {args.summary}")


if __name__ == "__main__":
    main()
