#!/usr/bin/env python3
"""Normalize a FactGrid ancient-settlement CDLI ID2 query export.

The expected source is a CSV query result with:

- `Ancient_settlement`: FactGrid entity URI or QID
- `Ancient_settlementLabel`: English label
- `CDLI_ID2`: CDLI provenience/place identifier

The output follows the same lightweight lookup columns used by the CDLI
artifact staging scripts.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd


WORKFLOW_ROOT = Path(__file__).resolve().parents[1]
INPUT_ROOT = WORKFLOW_ROOT / "inputs" / "cdli_lookup_sources"
DEFAULT_SOURCE = Path("/Users/aa/Downloads/AncientSettlement_CDLI2.csv")
DEFAULT_OUTPUT = INPUT_ROOT / "proveniences_FG_AncientSettlement_CDLI2_query.csv"
DEFAULT_MERGED = INPUT_ROOT / "proveniences_FG_all_with_p694_and_ancient_settlements.csv"
DEFAULT_EXISTING = INPUT_ROOT / "proveniences_FG_all_with_p694_live.csv"
DEFAULT_SUMMARY = WORKFLOW_ROOT / "published" / "factgrid_model_samples" / "factgrid_ancient_settlement_cdli2_lookup_summary.csv"


def clean(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null"}:
        return ""
    if text.endswith(".0") and text[:-2].isdigit():
        return text[:-2]
    return text


def qid_from_uri(value: object) -> str:
    text = clean(value)
    match = re.search(r"(Q\d+)(?:$|[/?#])", text)
    return match.group(1) if match else text


def first_existing(df: pd.DataFrame, names: list[str]) -> str:
    lowered = {c.casefold(): c for c in df.columns}
    for name in names:
        if name.casefold() in lowered:
            return lowered[name.casefold()]
    return ""


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, low_memory=False).fillna("")


def normalize_query_export(path: Path) -> pd.DataFrame:
    df = read_csv(path)
    if df.empty:
        return pd.DataFrame(columns=["FG_qid", "FG_qid_url", "Len", "Aen", "P694", "P48", "P2", "description_en", "source_file"])

    qid_col = first_existing(df, ["Ancient_settlement", "ancient_settlement", "item", "FG_qid", "qid"])
    label_col = first_existing(df, ["Ancient_settlementLabel", "ancient_settlementLabel", "itemLabel", "Len", "label"])
    cdli_col = first_existing(df, ["CDLI_ID2", "P694", "cdli_id2", "cdli_provenience_id"])
    if not qid_col or not cdli_col:
        raise RuntimeError(f"Could not find required QID/CDLI columns in {path}: {list(df.columns)}")

    rows = []
    for _, row in df.iterrows():
        qid = qid_from_uri(row.get(qid_col))
        cdli_id2 = clean(row.get(cdli_col))
        if not qid or not cdli_id2:
            continue
        rows.append(
            {
                "FG_qid": qid,
                "FG_qid_url": f"https://database.factgrid.de/entity/{qid}",
                "Len": clean(row.get(label_col)) if label_col else "",
                "Aen": "",
                "P694": cdli_id2,
                "P48": clean(row.get("P48")),
                "P2": clean(row.get("P2")),
                "description_en": clean(row.get("description_en")),
                "source_file": str(path),
            }
        )
    return pd.DataFrame(rows).drop_duplicates(["FG_qid", "P694"], keep="last")


def merge_lookup(existing_path: Path, query_lookup: pd.DataFrame) -> pd.DataFrame:
    existing = read_csv(existing_path)
    if existing.empty:
        return query_lookup
    out = pd.concat([existing, query_lookup], ignore_index=True).fillna("")
    project_like = (
        out.get("P2", pd.Series("", index=out.index)).map(clean).str.contains("Q417872", regex=False)
        | out.get("Len", pd.Series("", index=out.index)).map(clean).eq("Geomapping Landscapes of Writing (GLoW)")
        | out.get("Aen", pd.Series("", index=out.index)).map(clean).eq("GLoW")
    )
    out = out[~project_like].copy()
    out["_dedupe"] = out["FG_qid"].map(qid_from_uri) + "|" + out["P694"].map(clean)
    return out.drop_duplicates("_dedupe", keep="last").drop(columns=["_dedupe"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--existing", type=Path, default=DEFAULT_EXISTING)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--merged-output", type=Path, default=DEFAULT_MERGED)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--preview", type=int, default=20)
    args = parser.parse_args()

    lookup = normalize_query_export(args.source)
    merged = merge_lookup(args.existing, lookup)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    lookup.to_csv(args.output, index=False)
    merged.to_csv(args.merged_output, index=False)

    summary = pd.DataFrame(
        [
            {"metric": "source_rows", "value": len(read_csv(args.source))},
            {"metric": "normalized_lookup_rows", "value": len(lookup)},
            {"metric": "normalized_unique_qids", "value": lookup["FG_qid"].nunique() if not lookup.empty else 0},
            {"metric": "normalized_unique_cdli_id2", "value": lookup["P694"].nunique() if not lookup.empty else 0},
            {"metric": "merged_lookup_rows", "value": len(merged)},
        ]
    )
    summary.to_csv(args.summary, index=False)
    print(summary.to_string(index=False))
    if args.preview and not lookup.empty:
        print(lookup.head(args.preview).to_string(index=False))
    print(f"Wrote ancient-settlement CDLI ID2 lookup -> {args.output}")
    print(f"Wrote merged lookup -> {args.merged_output}")
    print(f"Wrote summary -> {args.summary}")


if __name__ == "__main__":
    main()
