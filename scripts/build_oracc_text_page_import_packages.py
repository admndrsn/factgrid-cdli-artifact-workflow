#!/usr/bin/env python3
"""Build checksum-bound ORACC text-page import packages.

The admin importer accepts small zip packages. This script converts the
existing ORACC text-page staging CSV plus generated wikitext files into one or
more deterministic zip packages under a configurable size ceiling.

It does not contact TokenWorks and does not write to the Wikibase.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


WORKFLOW_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STAGING = WORKFLOW_ROOT / "published" / "oracc_text_pages" / "oracc_text_page_staging.csv"
DEFAULT_RESULTS = WORKFLOW_ROOT / "published" / "oracc_text_pages" / "oracc_text_page_write_results.csv"
DEFAULT_OUTPUT_DIR = WORKFLOW_ROOT / "published" / "oracc_text_pages" / "import_packages"
DEFAULT_SUMMARY = DEFAULT_OUTPUT_DIR / "oracc_text_page_import_package_summary.csv"


def clean(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null"}:
        return ""
    return text


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, low_memory=False).fillna("")


def written_keys(results: pd.DataFrame) -> set[tuple[str, str]]:
    if results.empty or not {"tw_qid", "page_url", "write_status"}.issubset(results.columns):
        return set()
    written = results[results["write_status"].eq("written")]
    return set(zip(written["tw_qid"].map(clean), written["page_url"].map(clean)))


def load_rows(staging_path: Path, results_path: Path, include_written: bool) -> list[dict[str, str]]:
    staging = load_csv(staging_path)
    if staging.empty:
        raise RuntimeError(f"No staging rows found in {staging_path}")
    required = {"cdli_id", "tw_qid", "page_title", "page_url", "page_path", "p196_property"}
    missing = required - set(staging.columns)
    if missing:
        raise RuntimeError(f"Staging file is missing columns: {', '.join(sorted(missing))}")

    if not include_written:
        already_written = written_keys(load_csv(results_path))
        if already_written:
            staging = staging[
                ~staging.apply(lambda row: (clean(row.get("tw_qid")), clean(row.get("page_url"))) in already_written, axis=1)
            ].copy()

    rows = []
    for _, row in staging.iterrows():
        page_path = Path(clean(row.get("page_path")))
        if not page_path.exists():
            raise RuntimeError(f"Missing page file for {clean(row.get('tw_qid'))}: {page_path}")
        rows.append(
            {
                "cdli_id": clean(row.get("cdli_id")),
                "qid": clean(row.get("tw_qid")),
                "artifact_label": clean(row.get("artifact_label")),
                "page_title": clean(row.get("page_title")),
                "page_url": clean(row.get("page_url")),
                "page_file": f"pages/{page_path.name}",
                "p196_property": clean(row.get("p196_property")) or "P196",
                "token_count": clean(row.get("token_count")),
                "line_count": clean(row.get("line_count")),
                "source": "ORACC word-level export",
                "_page_path": str(page_path),
            }
        )
    return rows


def csv_bytes(rows: list[dict[str, str]]) -> bytes:
    public_fields = [field for field in rows[0].keys() if not field.startswith("_")]
    from io import StringIO

    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=public_fields, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue().encode("utf-8")


@dataclass
class Package:
    index: int
    rows: list[dict[str, str]]


def estimated_uncompressed_size(rows: list[dict[str, str]]) -> int:
    total = len(csv_bytes(rows))
    for row in rows:
        total += Path(row["_page_path"]).stat().st_size
    return total


def split_packages(rows: list[dict[str, str]], max_uncompressed_bytes: int) -> list[Package]:
    packages: list[Package] = []
    current: list[dict[str, str]] = []
    for row in rows:
        candidate = current + [row]
        if current and estimated_uncompressed_size(candidate) > max_uncompressed_bytes:
            packages.append(Package(index=len(packages) + 1, rows=current))
            current = [row]
        else:
            current = candidate
    if current:
        packages.append(Package(index=len(packages) + 1, rows=current))
    return packages


def write_package(package: Package, output_dir: Path, prefix: str) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_data = csv_bytes(package.rows)
    manifest = {
        "package_name": f"{prefix}_{package.index:03d}",
        "row_count": len(package.rows),
        "csv_file": "import.csv",
        "csv_sha256": sha256_bytes(csv_data),
        "files": [],
    }
    for row in package.rows:
        page_path = Path(row["_page_path"])
        manifest["files"].append(
            {
                "path": row["page_file"],
                "source_path": str(page_path),
                "sha256": sha256_file(page_path),
                "bytes": page_path.stat().st_size,
            }
        )

    manifest_data = json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True).encode("utf-8")
    zip_path = output_dir / f"{prefix}_{package.index:03d}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        archive.writestr("import.csv", csv_data)
        archive.writestr("manifest.json", manifest_data)
        for row in package.rows:
            archive.write(Path(row["_page_path"]), arcname=row["page_file"])

    return {
        "package": zip_path.name,
        "package_path": str(zip_path),
        "row_count": len(package.rows),
        "first_qid": package.rows[0]["qid"],
        "last_qid": package.rows[-1]["qid"],
        "zip_bytes": zip_path.stat().st_size,
        "uncompressed_estimate_bytes": estimated_uncompressed_size(package.rows),
        "manifest_sha256": sha256_bytes(manifest_data),
    }


def build(args: argparse.Namespace) -> None:
    rows = load_rows(args.staging, args.results, args.include_written)
    if args.limit:
        rows = rows[: args.limit]
    if not rows:
        raise RuntimeError("No rows to package")

    packages = split_packages(rows, args.max_uncompressed_mb * 1024 * 1024)
    summary_rows = [write_package(package, args.output_dir, args.prefix) for package in packages]
    summary = pd.DataFrame(summary_rows)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.summary, index=False)

    print(f"ORACC text-page rows packaged: {len(rows)}")
    print(f"packages written: {len(summary)}")
    print(summary.to_string(index=False))
    print(f"Wrote summary -> {args.summary}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staging", type=Path, default=DEFAULT_STAGING)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--prefix", default="oracc_text_page_p196_import")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--max-uncompressed-mb", type=int, default=4)
    parser.add_argument("--include-written", action="store_true")
    args = parser.parse_args()
    build(args)


if __name__ == "__main__":
    main()
