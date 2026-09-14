#!/usr/bin/env python3
"""Prepare a FactGrid QID list from the reviewed provenience sheet export."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd


WORKFLOW_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = WORKFLOW_ROOT / "inputs" / "cdli_lookup_sources" / "proveniences_FG_Proveniences.csv"
DEFAULT_OUTPUT = WORKFLOW_ROOT / "published" / "factgrid_model_samples" / "factgrid_provenience_qids.csv"
DEFAULT_SUMMARY = WORKFLOW_ROOT / "published" / "factgrid_model_samples" / "factgrid_provenience_qids_summary.csv"


def clean(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null"}:
        return ""
    return text


def qid_from_value(value: object) -> str:
    text = clean(value)
    match = re.search(r"(Q\d+)(?:$|[/?#])", text)
    if match:
        return match.group(1)
    match = re.search(r"(Q\d+)$", text)
    return match.group(1) if match else ""


def first_existing(df: pd.DataFrame, names: list[str]) -> str:
    lowered = {c.casefold(): c for c in df.columns}
    for name in names:
        if name.casefold() in lowered:
            return lowered[name.casefold()]
    return ""


def read_source(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str).fillna("")
    if df.empty:
        return df
    first_row = [clean(v) for v in df.iloc[0].tolist()]
    if {"fg_qid", "ancientplace"}.intersection({v.casefold() for v in first_row}):
        out = df.iloc[1:].copy()
        out.columns = [value if value else f"unnamed_{i}" for i, value in enumerate(first_row)]
        return out.fillna("")
    return df


def prepare(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame]:
    source = Path(args.input)
    if not source.exists():
        raise RuntimeError(f"Input not found: {source}")
    df = read_source(source)
    if df.empty:
        raise RuntimeError(f"No rows found in {source}")

    qid_cols = [c for c in ["FG_qid", "ancientplace", "FG_Qid", "FG-Q", "qid"] if c in df.columns]
    label_col = first_existing(df, ["Len", "transciption_name", "transcription_name", "Aen"])
    cdli_label_col = first_existing(df, ["Aen", "cdli_legacy_'Len'", "provenience"])
    cdli_id_col = first_existing(df, ["P694", "id_text2", "CDLI_ID2"])
    coord_col = first_existing(df, ["P48", "coord", "coordinate"])
    if not qid_cols:
        raise RuntimeError(f"No FactGrid QID columns found in {source}")

    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for _, row in df.iterrows():
        qid = ""
        source_col = ""
        for col in qid_cols:
            qid = qid_from_value(row.get(col))
            if qid:
                source_col = col
                break
        if not qid or qid in seen:
            continue
        seen.add(qid)
        rows.append(
            {
                "factgrid_qid": qid,
                "label": clean(row.get(label_col)) if label_col else "",
                "cdli_provenience_label": clean(row.get(cdli_label_col)) if cdli_label_col else "",
                "cdli_id2": clean(row.get(cdli_id_col)) if cdli_id_col else "",
                "coordinate": clean(row.get(coord_col)) if coord_col else "",
                "source_qid_column": source_col,
            }
        )

    out = pd.DataFrame(rows).sort_values(["factgrid_qid"]).reset_index(drop=True)
    summary = pd.DataFrame(
        [
            {"metric": "source_rows", "value": len(df)},
            {"metric": "unique_factgrid_qids", "value": len(out)},
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
    print(f"Wrote FactGrid provenience QID list -> {args.output}")
    print(f"Wrote summary -> {args.summary}")


if __name__ == "__main__":
    main()
