#!/usr/bin/env python3
"""Match CDLI holding institutions against FactGrid and stage missing museums.

The input CSV is the CDLI collection list that surfaced while writing present
holding statements. This script matches it against the local FactGrid museum
lookup by CDLI collection ID, Wikidata ID, and normalized labels, then writes:

- a full matched review table;
- a create-staging table for collection/holding items still missing in FactGrid.
"""

from __future__ import annotations

import argparse
import re
import unicodedata
from pathlib import Path

import pandas as pd


WORKFLOW_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MISSING_COLLECTIONS = Path("/Users/aa/Downloads/LOD Tablet Dictionary (FG Cuneiform) - missing_museums_CDLI.csv")
DEFAULT_FACTGRID_MUSEUMS = WORKFLOW_ROOT / "inputs" / "cdli_lookup_sources" / "museum_FG.csv"
DEFAULT_OUTPUT_DIR = WORKFLOW_ROOT / "published" / "factgrid_museum_staging"
DEFAULT_MATCHES = DEFAULT_OUTPUT_DIR / "cdli_missing_museums_factgrid_match_review.csv"
DEFAULT_STAGING = DEFAULT_OUTPUT_DIR / "factgrid_missing_museum_item_staging.csv"
DEFAULT_SUMMARY = DEFAULT_OUTPUT_DIR / "factgrid_missing_museum_item_staging_summary.csv"


def clean(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.casefold() in {"nan", "none", "null"}:
        return ""
    if text.endswith(".0") and text[:-2].isdigit():
        return text[:-2]
    return text


def normalize(value: object) -> str:
    text = unicodedata.normalize("NFKD", clean(value))
    text = text.encode("ascii", "ignore").decode("ascii").casefold()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def pipe_join(values) -> str:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        text = clean(value)
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return " | ".join(out)


def extract_qids(value: object) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for qid in re.findall(r"Q\d+", clean(value)):
        if qid not in seen:
            seen.add(qid)
            out.append(qid)
    return out


def extract_urls(value: object) -> list[str]:
    return re.findall(r"https?://[^;\s]+", clean(value))


def label_from_row(row: pd.Series) -> str:
    for column in ["names", "collection", "Best_CDLI_Match", "missing_collections"]:
        value = clean(row.get(column))
        if not value:
            continue
        if column == "names":
            # The CDLI export stores names like "British Museum [en]; Musée ..."
            first = value.split(";")[0].strip()
            first = re.sub(r"\s*\[[a-z-]+\]\s*$", "", first).strip()
            if first:
                return first
        return value
    return ""


def aliases_from_row(row: pd.Series, label: str) -> str:
    values: list[str] = []
    for column in ["collection", "Best_CDLI_Match", "missing_collections"]:
        values.append(clean(row.get(column)))
    for part in clean(row.get("names")).split(";"):
        values.append(re.sub(r"\s*\[[a-z-]+\]\s*$", "", part).strip())
    return pipe_join(value for value in values if normalize(value) != normalize(label))


def collection_kind(row: pd.Series) -> str:
    actor = clean(row.get("collection_actor"))
    holding = clean(row.get("collection_holding"))
    if actor and holding:
        return f"{actor}; {holding}"
    return actor or holding


def build_factgrid_indexes(fg: pd.DataFrame) -> tuple[dict[str, dict], dict[str, dict], dict[str, dict]]:
    by_cdli: dict[str, dict] = {}
    by_wd: dict[str, dict] = {}
    by_name: dict[str, dict] = {}
    for _, row in fg.iterrows():
        qid = clean(row.get("qid"))
        if not re.fullmatch(r"Q\d+", qid):
            continue
        record = {
            "factgrid_qid": qid,
            "factgrid_label": clean(row.get("Len")),
            "factgrid_description": clean(row.get("Den")),
            "factgrid_cdli_id": clean(row.get("cdli_id")) or clean(row.get("collection_id")),
            "factgrid_wikidata_id": clean(row.get("P771")),
        }
        for column in ["cdli_id", "collection_id"]:
            key = clean(row.get(column))
            if key:
                by_cdli.setdefault(key, record)
        for column in ["P771", "wikidata_id"]:
            for qid_value in extract_qids(row.get(column)):
                by_wd.setdefault(qid_value, record)
        for column in ["Len", "Den", "Aen"]:
            key = normalize(row.get(column))
            if key:
                by_name.setdefault(key, record)
    return by_cdli, by_wd, by_name


def find_match(row: pd.Series, by_cdli: dict[str, dict], by_wd: dict[str, dict], by_name: dict[str, dict]) -> tuple[str, dict]:
    cdli_id = clean(row.get("id"))
    if cdli_id in by_cdli:
        return "cdli_id", by_cdli[cdli_id]
    for qid in extract_qids(row.get("external_resources")):
        if qid in by_wd:
            return "wikidata_id", by_wd[qid]
    for column in ["collection", "Best_CDLI_Match", "missing_collections", "names"]:
        key = normalize(row.get(column))
        if key in by_name:
            return "name_exact", by_name[key]
    return "", {}


def prepare(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    missing = pd.read_csv(args.missing_collections, dtype=str, low_memory=False).fillna("")
    fg = pd.read_csv(args.factgrid_museums, dtype=str, low_memory=False).fillna("")
    by_cdli, by_wd, by_name = build_factgrid_indexes(fg)

    match_rows: list[dict[str, object]] = []
    staging_rows: list[dict[str, object]] = []
    for _, row in missing.iterrows():
        method, match = find_match(row, by_cdli, by_wd, by_name)
        label = label_from_row(row)
        external_urls = extract_urls(row.get("external_resources"))
        wikidata_qids = extract_qids(row.get("external_resources"))
        review_row = {
            "cdli_collection_id": clean(row.get("id")),
            "collection_label": label,
            "collection": clean(row.get("collection")),
            "best_cdli_match": clean(row.get("Best_CDLI_Match")),
            "aliases_en": aliases_from_row(row, label),
            "collection_kind": collection_kind(row),
            "country_iso": clean(row.get("country_iso")),
            "region_gadm": clean(row.get("region_gadm")),
            "district_gadm": clean(row.get("district_gadm")),
            "longitude": clean(row.get("location_longitude_wgs1984")),
            "latitude": clean(row.get("location_latitude_wgs1984")),
            "collection_url": clean(row.get("collection_url")),
            "wikidata_qids": " | ".join(wikidata_qids),
            "external_urls": " | ".join(external_urls),
            "factgrid_qid": clean(match.get("factgrid_qid")),
            "factgrid_label": clean(match.get("factgrid_label")),
            "factgrid_match_method": method or "unmatched",
        }
        match_rows.append(review_row)
        if method:
            continue
        staging_rows.append(
            {
                **review_row,
                "label_en": label,
                "description_en": f"CDLI holding institution or collection; CDLI collection {clean(row.get('id'))}",
                "create_status": "",
                "create_error": "",
            }
        )

    matches = pd.DataFrame(match_rows)
    staging = pd.DataFrame(staging_rows)
    if args.limit:
        staging = staging.head(args.limit).copy()
    summary = pd.DataFrame(
        [
            {"metric": "input_rows", "value": len(missing)},
            {"metric": "matched_rows", "value": int(matches["factgrid_qid"].map(clean).ne("").sum())},
            {"metric": "missing_factgrid_rows", "value": int(matches["factgrid_qid"].map(clean).eq("").sum())},
            {"metric": "staged_rows", "value": len(staging)},
            {"metric": "rows_with_wikidata_qid", "value": int(matches["wikidata_qids"].map(clean).ne("").sum())},
            {"metric": "rows_with_coordinates", "value": int((matches["latitude"].map(clean).ne("") & matches["longitude"].map(clean).ne("")).sum())},
        ]
    )
    return matches, staging, summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--missing-collections", type=Path, default=DEFAULT_MISSING_COLLECTIONS)
    parser.add_argument("--factgrid-museums", type=Path, default=DEFAULT_FACTGRID_MUSEUMS)
    parser.add_argument("--matches", type=Path, default=DEFAULT_MATCHES)
    parser.add_argument("--output", type=Path, default=DEFAULT_STAGING)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--preview", type=int, default=30)
    args = parser.parse_args()

    matches, staging, summary = prepare(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    matches.to_csv(args.matches, index=False)
    staging.to_csv(args.output, index=False)
    summary.to_csv(args.summary, index=False)

    print(summary.to_string(index=False))
    print("\nMatch methods:")
    print(matches["factgrid_match_method"].value_counts(dropna=False).to_string())
    print("\nMissing museum staging preview:")
    preview_cols = ["cdli_collection_id", "label_en", "collection_kind", "country_iso", "wikidata_qids", "collection_url"]
    if not staging.empty:
        print(staging[[col for col in preview_cols if col in staging.columns]].head(args.preview).to_string(index=False))
    print(f"\nWrote match review -> {args.matches}")
    print(f"Wrote missing museum staging -> {args.output}")
    print(f"Wrote summary -> {args.summary}")


if __name__ == "__main__":
    main()
