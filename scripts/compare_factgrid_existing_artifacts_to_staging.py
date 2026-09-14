#!/usr/bin/env python3
"""Compare live FactGrid artifact register rows to local CDLI staging.

Outputs both a review table and a writer-compatible lookup CSV. The lookup CSV
has `match_key_type`, `match_key`, and `factgrid_qid`, so it can be supplied to
`write_factgrid_cdli_artifact_items.py --prior-factgrid-qid-lookup`.
"""

from __future__ import annotations

import argparse
import re
import unicodedata
from pathlib import Path

import pandas as pd

from write_cdli_new_artifact_items import clean, format_cdli_id


WORKFLOW_ROOT = Path(__file__).resolve().parents[1]
PILOT_ROOT = WORKFLOW_ROOT / "published" / "pilots"
EXISTING_ROOT = WORKFLOW_ROOT / "published" / "factgrid_existing"
DEFAULT_REGISTER = EXISTING_ROOT / "factgrid_existing_clay_tablet_register.csv"
DEFAULT_ARTIFACTS = PILOT_ROOT / "cdli_artifact_staging_tranche_10001_35000.csv"
DEFAULT_RESULTS = PILOT_ROOT / "factgrid_cdli_artifact_write_results_tranche_10001_35000.csv"
DEFAULT_OUTPUT = EXISTING_ROOT / "factgrid_existing_artifact_matches_to_staging.csv"
DEFAULT_LOOKUP = WORKFLOW_ROOT / "inputs" / "factgrid_tablet_sources" / "factgrid_existing_live_cdli_lookup.csv"
DEFAULT_SUMMARY = EXISTING_ROOT / "factgrid_existing_artifact_matches_to_staging_summary.csv"


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, low_memory=False).fillna("")


def qid_number(qid: object) -> int:
    match = re.fullmatch(r"Q(\d+)", clean(qid))
    return int(match.group(1)) if match else 10**18


def cdli_keys(value: object) -> set[str]:
    text = clean(value)
    if not text:
        return set()
    formatted = format_cdli_id(text)
    digits = re.sub(r"\D+", "", text)
    return {v for v in {text, formatted, digits} if v}


def normalize_text(value: object) -> str:
    text = unicodedata.normalize("NFKD", clean(value))
    text = text.encode("ascii", "ignore").decode("ascii").casefold()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def split_values(value: object) -> list[str]:
    parts = re.split(r"\s*\|\s*|\s*;\s*", clean(value))
    return [part for part in (clean(p) for p in parts) if part]


def staging_inventory_values(row: pd.Series) -> list[str]:
    values: list[str] = []
    for col in ["designation", "museum_no", "accession_no", "exact_references"]:
        if col not in row.index:
            continue
        for value in split_values(row.get(col)):
            if value and value not in values:
                values.append(value)
    return values


def safe_label_alias_key(value: object) -> str:
    key = normalize_text(value)
    if not key:
        return ""
    if len(key) < 6:
        return ""
    generic = {
        "unknown",
        "unassigned",
        "unpublished unassigned",
        "nmsi",
        "nmsd",
        "va",
        "sb",
        "bm",
        "amm",
        "im",
    }
    if key in generic:
        return ""
    if re.fullmatch(r"[a-z]{1,4}", key):
        return ""
    if "unknown" in key or "unassigned" in key:
        return ""
    return key


def build_live_maps(register: pd.DataFrame) -> tuple[dict[str, list[dict[str, str]]], dict[str, list[dict[str, str]]]]:
    by_cdli: dict[str, list[dict[str, str]]] = {}
    by_inventory: dict[str, list[dict[str, str]]] = {}
    by_label_alias: dict[str, list[dict[str, str]]] = {}
    if register.empty:
        return by_cdli, by_inventory
    for _, row in register.iterrows():
        record = {
            "factgrid_qid": clean(row.get("item_id")),
            "factgrid_label": clean(row.get("itemLabel")),
            "factgrid_aliases": clean(row.get("itemAliases")),
            "factgrid_cdli_id": clean(row.get("cdliId")),
            "factgrid_instance_of_qid": clean(row.get("instance_of_qid")),
            "factgrid_instance_of_label": clean(row.get("instanceOfLabel")),
            "factgrid_present_holding_qid": clean(row.get("present_holding_qid")),
            "factgrid_present_holding_label": clean(row.get("presentHoldingLabel")),
            "factgrid_direct_inventory_number": clean(row.get("directInventoryNumber")),
            "factgrid_holding_inventory_number": clean(row.get("holdingInventoryNumber")),
        }
        for key in cdli_keys(row.get("cdliId")):
            by_cdli.setdefault(key, []).append(record)
        for value in [row.get("itemLabel"), *split_values(row.get("itemAliases"))]:
            key = safe_label_alias_key(value)
            if key:
                by_label_alias.setdefault(key, []).append(record)
        for col in ["directInventoryNumber", "holdingInventoryNumber"]:
            key = normalize_text(row.get(col))
            if key:
                by_inventory.setdefault(key, []).append(record)
    return by_cdli, by_inventory, by_label_alias


def pick_lowest(records: list[dict[str, str]]) -> dict[str, str]:
    if not records:
        return {}
    return sorted(records, key=lambda r: qid_number(r.get("factgrid_qid")))[0]


def build_matches(
    artifacts: pd.DataFrame,
    register: pd.DataFrame,
    results: pd.DataFrame,
    include_inventory_candidates: bool,
) -> pd.DataFrame:
    by_cdli, by_inventory, by_label_alias = build_live_maps(register)
    written_cdli = set()
    if not results.empty and {"cdli_id", "write_status"}.issubset(results.columns):
        written_cdli = set(results.loc[results["write_status"].eq("written"), "cdli_id"].map(clean))

    rows: list[dict[str, str]] = []
    for _, artifact in artifacts.iterrows():
        cdli_id = clean(artifact.get("cdli_id"))
        cdli_matches: list[dict[str, str]] = []
        for key in cdli_keys(cdli_id):
            cdli_matches.extend(by_cdli.get(key, []))
        matches = cdli_matches
        match_type = "cdli_id" if matches else ""
        if not matches:
            label_key = safe_label_alias_key(artifact.get("label"))
            if label_key:
                matches = by_label_alias.get(label_key, [])
                match_type = "label_or_alias" if matches else ""
        if not matches and include_inventory_candidates:
            for inventory in staging_inventory_values(artifact):
                if len(normalize_text(inventory)) < 5:
                    continue
                inv_matches = by_inventory.get(normalize_text(inventory), [])
                if inv_matches:
                    matches.extend(inv_matches)
                    match_type = "inventory_number"
        canonical = pick_lowest(matches)
        if not canonical:
            continue
        rows.append(
            {
                "cdli_id": cdli_id,
                "formatted_cdli_id": format_cdli_id(cdli_id),
                "staging_label": clean(artifact.get("label")),
                "staging_artifact_type": clean(artifact.get("artifact_type")),
                "staging_period": clean(artifact.get("period")),
                "staging_provenience": clean(artifact.get("provenience")),
                "staging_primary_collection": clean(artifact.get("primary_collection")),
                "staging_inventory_values": " | ".join(staging_inventory_values(artifact)),
                "match_type": match_type,
                "factgrid_qid": canonical.get("factgrid_qid", ""),
                "factgrid_label": canonical.get("factgrid_label", ""),
                "factgrid_aliases": canonical.get("factgrid_aliases", ""),
                "factgrid_cdli_id": canonical.get("factgrid_cdli_id", ""),
                "factgrid_instance_of_qid": canonical.get("factgrid_instance_of_qid", ""),
                "factgrid_instance_of_label": canonical.get("factgrid_instance_of_label", ""),
                "factgrid_present_holding_qid": canonical.get("factgrid_present_holding_qid", ""),
                "factgrid_present_holding_label": canonical.get("factgrid_present_holding_label", ""),
                "factgrid_inventory_number": canonical.get("factgrid_holding_inventory_number")
                or canonical.get("factgrid_direct_inventory_number", ""),
                "candidate_count": len({r.get("factgrid_qid", "") for r in matches if r.get("factgrid_qid")}),
                "already_written_in_results": "yes" if cdli_id in written_cdli else "no",
            }
        )
    return pd.DataFrame(rows)


def build_lookup(matches: pd.DataFrame) -> pd.DataFrame:
    if matches.empty:
        return pd.DataFrame(columns=["match_key_type", "match_key", "factgrid_qid", "factgrid_label", "source"])
    rows: list[dict[str, str]] = []
    automatic = matches[matches["match_type"].isin(["cdli_id", "label_or_alias"])]
    for _, row in automatic.iterrows():
        for key in cdli_keys(row.get("cdli_id")):
            rows.append(
                {
                    "match_key_type": "cdli_id",
                    "match_key": key,
                    "factgrid_qid": clean(row.get("factgrid_qid")),
                    "factgrid_label": clean(row.get("factgrid_label")),
                    "source": "factgrid_live_existing_artifact_register",
                }
            )
        if clean(row.get("match_type")) == "label_or_alias" and str(row.get("candidate_count")) == "1":
            label_key = safe_label_alias_key(row.get("staging_label"))
            if label_key:
                rows.append(
                    {
                        "match_key_type": "label_or_alias",
                        "match_key": label_key,
                        "factgrid_qid": clean(row.get("factgrid_qid")),
                        "factgrid_label": clean(row.get("factgrid_label")),
                        "source": "factgrid_live_existing_artifact_register",
                    }
                )
    return pd.DataFrame(rows).drop_duplicates(["match_key_type", "match_key", "factgrid_qid"], keep="last")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--register", type=Path, default=DEFAULT_REGISTER)
    parser.add_argument("--artifacts", type=Path, default=DEFAULT_ARTIFACTS)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--lookup-output", type=Path, default=DEFAULT_LOOKUP)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument(
        "--include-inventory-candidates",
        action="store_true",
        help="Include inventory-number candidates in the review output. These are never written to the automatic lookup.",
    )
    args = parser.parse_args()

    register = read_csv(args.register)
    artifacts = read_csv(args.artifacts)
    results = read_csv(args.results)
    if register.empty:
        raise RuntimeError(f"No live FactGrid register rows found in {args.register}")
    if artifacts.empty:
        raise RuntimeError(f"No artifact staging rows found in {args.artifacts}")

    matches = build_matches(artifacts, register, results, args.include_inventory_candidates)
    lookup = build_lookup(matches)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.lookup_output.parent.mkdir(parents=True, exist_ok=True)
    matches.to_csv(args.output, index=False)
    lookup.to_csv(args.lookup_output, index=False)

    summary = pd.DataFrame(
        [
            {"metric": "live_register_rows", "value": len(register)},
            {"metric": "live_unique_items", "value": register["item_id"].nunique() if "item_id" in register.columns else 0},
            {"metric": "staging_rows", "value": len(artifacts)},
            {"metric": "matched_staging_rows", "value": matches["cdli_id"].nunique() if not matches.empty else 0},
            {"metric": "matched_by_cdli_id", "value": int(matches["match_type"].eq("cdli_id").sum()) if not matches.empty else 0},
            {"metric": "matched_by_label_or_alias", "value": int(matches["match_type"].eq("label_or_alias").sum()) if not matches.empty else 0},
            {"metric": "matched_by_inventory_number_review_only", "value": int(matches["match_type"].eq("inventory_number").sum()) if not matches.empty else 0},
            {"metric": "lookup_rows", "value": len(lookup)},
        ]
    )
    summary.to_csv(args.summary, index=False)
    print(summary.to_string(index=False))
    if not matches.empty:
        print("\nMatch preview:")
        print(matches.head(20).to_string(index=False))
    print(f"Wrote matches -> {args.output}")
    print(f"Wrote writer lookup -> {args.lookup_output}")
    print(f"Wrote summary -> {args.summary}")


if __name__ == "__main__":
    main()
