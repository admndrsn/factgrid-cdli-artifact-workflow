#!/usr/bin/env python3
"""Build checksum-bound CDLI artifact item import packages.

This script prepares importer-friendly zip packages from the same staged CDLI
artifact rows used by the direct API writers. It does not contact TokenWorks and
does not write to the Wikibase.

Package layout:

- `items.csv`: one row per artifact item to create.
- `statements.csv`: ready statements for those items, linked by `local_id`.
- `manifest.json`: package metadata and SHA-256 checksums.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import zipfile
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from write_cdli_new_artifact_items import (
    DEFAULT_AUTHORITY_RESULTS,
    alias_values,
    artifact_label_for,
    build_workset,
    clean,
    description_for,
    format_cdli_id,
)


WORKFLOW_ROOT = Path(__file__).resolve().parents[1]
PILOT_ROOT = WORKFLOW_ROOT / "published" / "pilots"
DEFAULT_OUTPUT_DIR = WORKFLOW_ROOT / "published" / "import_packages"
DEFAULT_SUMMARY = DEFAULT_OUTPUT_DIR / "cdli_artifact_import_package_summary.csv"
DEFAULT_ARTIFACTS = PILOT_ROOT / "cdli_artifact_staging_tranche_10001_35000.csv"
DEFAULT_STATEMENTS = PILOT_ROOT / "cdli_artifact_statement_staging_tranche_10001_35000.csv"
DEFAULT_RESERVATIONS = PILOT_ROOT / "cdli_artifact_qid_reuse_reservations_tranche_10001_35000.csv"
DEFAULT_RESULTS = PILOT_ROOT / "cdli_artifact_new_item_results_tranche_10001_35000.csv"
DEFAULT_PLAN = PILOT_ROOT / "cdli_artifact_import_package_plan_tranche_10001_35000.csv"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def csv_bytes(rows: list[dict[str, object]]) -> bytes:
    if not rows:
        return b""
    fields = list(rows[0].keys())
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue().encode("utf-8")


def split_values(value: object) -> list[str]:
    out = []
    seen = set()
    for part in clean(value).split("|"):
        text = clean(part)
        if not text or text in seen:
            continue
        out.append(text)
        seen.add(text)
    return out


def item_row(artifact: pd.Series) -> dict[str, object]:
    cdli_id = format_cdli_id(artifact.get("cdli_id"))
    source_json = clean(artifact.get("source_json"))
    return {
        "local_id": f"cdli:{cdli_id}",
        "entity_type": "item",
        "qid": "",
        "cdli_id": cdli_id,
        "label_en": artifact_label_for(artifact),
        "description_en": description_for(artifact),
        "aliases_en": " | ".join(alias_values(artifact)),
        "source_json": Path(source_json).name if source_json else "",
        "import_status": "not_started",
    }


def statement_rows_for(local_id: str, item_plan: pd.DataFrame) -> list[dict[str, object]]:
    rows = []
    ready = item_plan[item_plan["claim_status"].eq("ready")].copy()
    for rank, statement in enumerate(ready.to_dict("records"), start=1):
        datatype = clean(statement.get("datatype"))
        value = clean(statement.get("tokenworks_value_qid")) if datatype == "wikibase-item" else clean(statement.get("value"))
        if not value:
            continue
        rows.append(
            {
                "local_id": local_id,
                "statement_rank": rank,
                "field_name": clean(statement.get("field_name")),
                "property_id": clean(statement.get("tw_pid")),
                "property_datatype": datatype,
                "value": value,
                "value_label": clean(statement.get("value_label")),
                "source": clean(statement.get("source")),
                "factgrid_property_id": clean(statement.get("fg_pid")),
                "note": clean(statement.get("note")),
                "import_status": "not_started",
            }
        )
    return rows


@dataclass
class Package:
    index: int
    item_rows: list[dict[str, object]]
    statement_rows: list[dict[str, object]]


def package_size(item_rows: list[dict[str, object]], statement_rows: list[dict[str, object]]) -> int:
    manifest_overhead = 3000
    return len(csv_bytes(item_rows)) + len(csv_bytes(statement_rows)) + manifest_overhead


def split_packages(
    items: list[dict[str, object]],
    statements_by_local_id: dict[str, list[dict[str, object]]],
    max_uncompressed_bytes: int,
) -> list[Package]:
    packages: list[Package] = []
    current_items: list[dict[str, object]] = []
    current_statements: list[dict[str, object]] = []
    for item in items:
        local_id = clean(item.get("local_id"))
        next_statements = statements_by_local_id.get(local_id, [])
        candidate_items = current_items + [item]
        candidate_statements = current_statements + next_statements
        if current_items and package_size(candidate_items, candidate_statements) > max_uncompressed_bytes:
            packages.append(Package(len(packages) + 1, current_items, current_statements))
            current_items = [item]
            current_statements = list(next_statements)
        else:
            current_items = candidate_items
            current_statements = candidate_statements
    if current_items:
        packages.append(Package(len(packages) + 1, current_items, current_statements))
    return packages


def write_package(package: Package, output_dir: Path, prefix: str) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    items_data = csv_bytes(package.item_rows)
    statements_data = csv_bytes(package.statement_rows)
    manifest = {
        "package_name": f"{prefix}_{package.index:03d}",
        "template_hint": "CDLI artifact metadata",
        "item_count": len(package.item_rows),
        "statement_count": len(package.statement_rows),
        "files": [
            {"path": "items.csv", "sha256": sha256_bytes(items_data), "bytes": len(items_data)},
            {"path": "statements.csv", "sha256": sha256_bytes(statements_data), "bytes": len(statements_data)},
        ],
    }
    manifest_data = json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True).encode("utf-8")
    zip_path = output_dir / f"{prefix}_{package.index:03d}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        archive.writestr("items.csv", items_data)
        archive.writestr("statements.csv", statements_data)
        archive.writestr("manifest.json", manifest_data)
    return {
        "package": zip_path.name,
        "package_path": str(zip_path),
        "item_count": len(package.item_rows),
        "statement_count": len(package.statement_rows),
        "first_local_id": package.item_rows[0]["local_id"],
        "last_local_id": package.item_rows[-1]["local_id"],
        "zip_bytes": zip_path.stat().st_size,
        "uncompressed_estimate_bytes": package_size(package.item_rows, package.statement_rows),
        "manifest_sha256": sha256_bytes(manifest_data),
    }


def package_args(args: argparse.Namespace) -> SimpleNamespace:
    return SimpleNamespace(
        artifacts=args.artifacts,
        statements=args.statements,
        reservations=args.reservations,
        authority_results=args.authority_results,
        results=args.results,
        prior_results=args.prior_results,
        retry_errors_from=args.retry_errors_from,
        plan=args.plan,
        limit=args.limit,
        preview=args.preview,
        sleep=0,
        only_field_names=args.only_field_names,
        write=False,
        max_csrf_refreshes=0,
        continue_on_row_error=True,
    )


def build(args: argparse.Namespace) -> None:
    work, plan = build_workset(package_args(args))
    args.plan.parent.mkdir(parents=True, exist_ok=True)
    plan.to_csv(args.plan, index=False)

    items = []
    statements_by_local_id: dict[str, list[dict[str, object]]] = {}
    for _, artifact in work.iterrows():
        item = item_row(artifact)
        items.append(item)
        cdli_id = clean(artifact.get("cdli_id"))
        local_id = clean(item["local_id"])
        item_plan = plan[plan["cdli_id"].map(clean).eq(cdli_id)].copy()
        statements_by_local_id[local_id] = statement_rows_for(local_id, item_plan)

    if not items:
        raise RuntimeError("No artifact rows selected for packaging")

    packages = split_packages(items, statements_by_local_id, args.max_uncompressed_mb * 1024 * 1024)
    summary_rows = [write_package(package, args.output_dir, args.prefix) for package in packages]
    summary = pd.DataFrame(summary_rows)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.summary, index=False)

    total_statements = sum(len(rows) for rows in statements_by_local_id.values())
    print(f"artifact items packaged: {len(items)}")
    print(f"ready statements packaged: {total_statements}")
    print(f"packages written: {len(summary)}")
    if len(plan):
        print("\nStatement plan summary:")
        print(
            plan.groupby(["field_name", "claim_status", "datatype"])
            .size()
            .reset_index(name="count")
            .to_string(index=False)
        )
    print("\nPackage summary:")
    print(summary.to_string(index=False))
    print(f"Wrote statement plan -> {args.plan}")
    print(f"Wrote package summary -> {args.summary}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, default=DEFAULT_ARTIFACTS)
    parser.add_argument("--statements", type=Path, default=DEFAULT_STATEMENTS)
    parser.add_argument("--reservations", type=Path, default=DEFAULT_RESERVATIONS)
    parser.add_argument("--authority-results", type=Path, default=DEFAULT_AUTHORITY_RESULTS)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--prior-results", type=Path, action="append", default=[])
    parser.add_argument("--retry-errors-from", type=Path)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--prefix", default="cdli_artifact_import")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--preview", type=int, default=10)
    parser.add_argument("--max-uncompressed-mb", type=int, default=4)
    parser.add_argument("--only-field-names", default="")
    args = parser.parse_args()
    build(args)


if __name__ == "__main__":
    main()
