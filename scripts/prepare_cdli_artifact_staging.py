#!/usr/bin/env python3
"""Flatten CDLI artifact JSON files into a TokenWorks artifact staging CSV.

The first use of this CSV is QID reuse reservation. Later stages can map the
same rows to TokenWorks statements.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import islice
import json
from pathlib import Path

import pandas as pd


DEFAULT_JSON_DIR = Path("/Users/aa/Documents/FactGrid/FactgridCuneiform/Datasets/CDLI/2026_GET/artifacts_json")
WORKFLOW_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = WORKFLOW_ROOT / "published" / "cdli_artifact_staging.csv"
DEFAULT_SUMMARY = WORKFLOW_ROOT / "published" / "cdli_artifact_staging_summary.csv"


def clean(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null"}:
        return ""
    if text.endswith(".0") and text[:-2].isdigit():
        return text[:-2]
    return text


def first_nonblank(*values: object) -> str:
    for value in values:
        text = clean(value)
        if text:
            return text
    return ""


def nested(data: dict, *keys: str) -> object:
    cur: object = data
    for key in keys:
        if not isinstance(cur, dict):
            return ""
        cur = cur.get(key)
    return cur


def join_values(values: list[str]) -> str:
    out = []
    seen = set()
    for value in values:
        text = clean(value)
        if not text or text in seen:
            continue
        out.append(text)
        seen.add(text)
    return " | ".join(out)


def list_nested(items: object, *keys: str) -> str:
    if not isinstance(items, list):
        return ""
    values = []
    for item in items:
        values.append(clean(nested(item, *keys)))
    return join_values(values)


def publication_values(items: object, *keys: str) -> str:
    if not isinstance(items, list):
        return ""
    values = []
    for item in items:
        pub = item.get("publication") if isinstance(item, dict) else None
        if not isinstance(pub, dict):
            continue
        cur: object = pub
        for key in keys:
            if not isinstance(cur, dict):
                cur = ""
                break
            cur = cur.get(key)
        values.append(clean(cur))
    return join_values(values)


def external_resource_values(items: object, key: str) -> str:
    if not isinstance(items, list):
        return ""
    values = []
    for item in items:
        if isinstance(item, dict):
            values.append(clean(item.get(key)))
    return join_values(values)


def flatten_artifact(path: Path) -> dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    artifact_id = clean(data.get("id")) or path.stem
    designation = clean(data.get("designation"))
    museum_no = clean(data.get("museum_no"))
    accession_no = clean(data.get("accession_no"))
    artifact_type = clean(nested(data, "artifact_type", "artifact_type"))
    label = first_nonblank(designation, museum_no, accession_no, f"CDLI artifact {artifact_id}")
    collections = data.get("collections")
    first_collection = collections[0].get("collection") if isinstance(collections, list) and collections and isinstance(collections[0], dict) else {}
    if not isinstance(first_collection, dict):
        first_collection = {}
    return {
        "id": artifact_id,
        "cdli_id": artifact_id,
        "label": label,
        "type": artifact_type or "artifact",
        "designation": designation,
        "museum_no": museum_no,
        "accession_no": accession_no,
        "artifact_type_id": clean(nested(data, "artifact_type", "id")),
        "artifact_type": artifact_type,
        "period_id": clean(nested(data, "period", "id")),
        "period": first_nonblank(nested(data, "period", "name"), nested(data, "period", "period")),
        "period_time_range": clean(nested(data, "period", "time_range")),
        "provenience_id": clean(nested(data, "provenience", "id")),
        "provenience": clean(nested(data, "provenience", "provenience")),
        "provenience_location_id": clean(nested(data, "provenience", "location_id")),
        "provenience_place_id": clean(nested(data, "provenience", "place_id")),
        "provenience_region_id": clean(nested(data, "provenience", "region_id")),
        "materials": list_nested(data.get("materials"), "material", "material"),
        "material_ids": list_nested(data.get("materials"), "material", "id"),
        "languages": list_nested(data.get("languages"), "language", "language"),
        "language_ids": list_nested(data.get("languages"), "language", "id"),
        "language_codes": list_nested(data.get("languages"), "language", "inline_code"),
        "genres": list_nested(data.get("genres"), "genre", "genre"),
        "genre_ids": list_nested(data.get("genres"), "genre", "id"),
        "collections": list_nested(data.get("collections"), "collection", "collection"),
        "collection_ids": list_nested(data.get("collections"), "collection", "id"),
        "primary_collection": clean(first_collection.get("collection")),
        "primary_collection_country_iso": clean(first_collection.get("country_iso")),
        "primary_collection_latitude": clean(first_collection.get("location_latitude_wgs1984")),
        "primary_collection_longitude": clean(first_collection.get("location_longitude_wgs1984")),
        "publication_designations": publication_values(data.get("publications"), "designation"),
        "publication_bibtexkeys": publication_values(data.get("publications"), "bibtexkey"),
        "publication_years": publication_values(data.get("publications"), "year"),
        "publication_series": publication_values(data.get("publications"), "series"),
        "publication_volumes": publication_values(data.get("publications"), "volume"),
        "exact_references": list_nested(data.get("publications"), "exact_reference"),
        "external_resource_urls": external_resource_values(data.get("external_resources"), "external_resource_url"),
        "external_resource_names": external_resource_values(data.get("external_resources"), "external_resource_name"),
        "source_json": str(path),
    }


def prepare(args: argparse.Namespace) -> None:
    json_dir = Path(args.json_dir)
    file_iter = json_dir.glob("*.json")
    if args.sort:
        file_iter = iter(sorted(file_iter))
    if args.offset:
        file_iter = islice(file_iter, args.offset, None)
    if args.limit:
        file_iter = islice(file_iter, args.limit)
    files = list(file_iter)
    print(f"selected {len(files)} artifact JSON files from {json_dir}", flush=True)
    rows = []
    errors = []
    if args.workers > 1:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            future_to_path = {pool.submit(flatten_artifact, path): path for path in files}
            for i, future in enumerate(as_completed(future_to_path), start=1):
                path = future_to_path[future]
                try:
                    rows.append(future.result())
                except Exception as exc:
                    errors.append({"source_json": str(path), "error": f"{type(exc).__name__}: {exc}"[:500]})
                if args.progress_every and i % args.progress_every == 0:
                    print(f"processed {i}/{len(files)} artifact JSON files", flush=True)
    else:
        for i, path in enumerate(files, start=1):
            try:
                rows.append(flatten_artifact(path))
            except Exception as exc:
                errors.append({"source_json": str(path), "error": f"{type(exc).__name__}: {exc}"[:500]})
            if args.progress_every and i % args.progress_every == 0:
                print(f"processed {i}/{len(files)} artifact JSON files", flush=True)
    out = pd.DataFrame(rows)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output, index=False)
    summary = pd.DataFrame(
        [
            ("json_files_considered", len(files)),
            ("staging_rows", len(out)),
            ("error_rows", len(errors)),
            ("unique_cdli_ids", out["cdli_id"].nunique() if not out.empty else 0),
            ("rows_with_label", int(out["label"].map(clean).ne("").sum()) if not out.empty else 0),
            ("rows_with_museum_no", int(out["museum_no"].map(clean).ne("").sum()) if not out.empty else 0),
            ("rows_with_period", int(out["period"].map(clean).ne("").sum()) if not out.empty else 0),
            ("rows_with_provenience", int(out["provenience"].map(clean).ne("").sum()) if not out.empty else 0),
            ("rows_with_language", int(out["languages"].map(clean).ne("").sum()) if not out.empty else 0),
            ("rows_with_collection", int(out["collections"].map(clean).ne("").sum()) if not out.empty else 0),
        ],
        columns=["metric", "value"],
    )
    summary.to_csv(args.summary, index=False)
    if errors:
        pd.DataFrame(errors).to_csv(Path(args.output).with_name(Path(args.output).stem + "_errors.csv"), index=False)
    print(summary.to_string(index=False))
    print(f"Wrote artifact staging -> {args.output}")
    print(f"Wrote summary -> {args.summary}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-dir", default=DEFAULT_JSON_DIR)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", default=DEFAULT_SUMMARY)
    parser.add_argument("--offset", type=int, default=0, help="Skip this many JSON files before applying --limit.")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--progress-every", type=int, default=10000)
    parser.add_argument("--workers", type=int, default=1, help="Parallel JSON readers. Useful for pilots and full export staging.")
    parser.add_argument("--sort", action="store_true", help="Sort JSON paths before processing. Slower for the full CDLI export.")
    args = parser.parse_args()
    prepare(args)


if __name__ == "__main__":
    main()
