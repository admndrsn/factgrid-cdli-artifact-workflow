#!/usr/bin/env python3
"""Stage FactGrid model claims for possible TokenWorks import.

This is a conservative classifier, not a writer. It maps FactGrid properties to
TokenWorks properties when a property map exists, maps FactGrid item values to
TokenWorks QIDs when an authority/artifact alignment exists, and marks the rest
for review.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


WORKFLOW_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = WORKFLOW_ROOT / "published" / "factgrid_model_samples" / "factgrid_item_model_Q389713_claims.csv"
DEFAULT_PROPERTY_MAP = WORKFLOW_ROOT.parents[0] / "tw_property_map_restored.csv"
DEFAULT_MISSING_PROPERTY_RESULTS = (
    WORKFLOW_ROOT / "published" / "factgrid_model_samples" / "tw_missing_factgrid_property_results.csv"
)
DEFAULT_AUTHORITY_QIDS = WORKFLOW_ROOT / "published" / "factgrid_model_samples" / "factgrid_pilot_authority_qids.csv"
DEFAULT_ARTIFACT_QIDS = WORKFLOW_ROOT / "published" / "factgrid_model_samples" / "factgrid_pilot_artifact_qids.csv"
DEFAULT_RESEARCH_PROJECT_QIDS = (
    WORKFLOW_ROOT / "published" / "factgrid_model_samples" / "cdli_research_project_authority_results.csv"
)
DEFAULT_OUTPUT = WORKFLOW_ROOT / "published" / "factgrid_model_samples" / "factgrid_item_model_Q389713_import_staging.csv"
DEFAULT_SUMMARY = WORKFLOW_ROOT / "published" / "factgrid_model_samples" / "factgrid_item_model_Q389713_import_summary.csv"


def clean(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null"}:
        return ""
    return text


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise RuntimeError(f"Missing CSV: {path}")
    return pd.read_csv(path, dtype=str, low_memory=False).fillna("")


def add_property_map_rows(out: dict[str, dict[str, str]], path: Path) -> None:
    if not path.exists():
        return
    df = load_csv(path)
    fg_col = "factgridPid" if "factgridPid" in df.columns else "factgrid_pid"
    tw_col = "twPid" if "twPid" in df.columns else "final_tw_pid"
    if tw_col not in df.columns and "created_tw_pid" in df.columns:
        tw_col = "created_tw_pid"
    label_col = "propertyLabel" if "propertyLabel" in df.columns else "property_label"
    for _, row in df.iterrows():
        fg_pid = clean(row.get(fg_col))
        tw_pid = clean(row.get(tw_col))
        if not fg_pid or not tw_pid:
            continue
        out[fg_pid] = {"tw_pid": tw_pid, "tw_property_label": clean(row.get(label_col))}


def load_property_map(path: Path, extra_paths: list[Path]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    add_property_map_rows(out, path)
    for extra_path in extra_paths:
        add_property_map_rows(out, extra_path)
    return out


def load_qid_map(paths: list[Path]) -> dict[str, str]:
    out = {}
    for path in paths:
        if not path.exists():
            continue
        df = load_csv(path)
        if "tokenworks_qid" not in df.columns and "tw_qid" in df.columns:
            df = df.rename(columns={"tw_qid": "tokenworks_qid"})
        if not {"factgrid_qid", "tokenworks_qid"}.issubset(df.columns):
            continue
        for _, row in df.iterrows():
            fg_qid = clean(row.get("factgrid_qid"))
            tw_qid = clean(row.get("tokenworks_qid"))
            if fg_qid and tw_qid:
                out[fg_qid] = tw_qid
    return out


def classify(row: pd.Series, property_map: dict[str, dict[str, str]], qid_map: dict[str, str]) -> tuple[str, str]:
    fg_pid = clean(row.get("property_id"))
    if fg_pid not in property_map:
        return "unmapped_property", f"No TokenWorks property mapped for FactGrid {fg_pid}"
    value_type = clean(row.get("value_type"))
    value = clean(row.get("value"))
    datatype = clean(row.get("value_datatype"))
    if value_type == "wikibase-entity" or value.startswith("Q"):
        if value in qid_map:
            return "ready", "Mapped FactGrid item value to TokenWorks QID"
        return "needs_value_qid", f"Need TokenWorks QID for FactGrid value {value}"
    if datatype in {"external-id", "string", "monolingualtext", "globe-coordinate", "quantity", "time"}:
        return "ready", "Literal/coordinate value can be copied to mapped TokenWorks property"
    return "needs_datatype_review", f"Review unsupported or unexpected datatype {datatype}"


def prepare(args: argparse.Namespace) -> None:
    claims = load_csv(args.model_claims)
    property_map = load_property_map(args.property_map, args.extra_property_map)
    qid_map = load_qid_map([args.authority_qids, args.artifact_qids, *args.extra_qid_map])

    rows = []
    for _, row in claims.iterrows():
        fg_pid = clean(row.get("property_id"))
        mapping = property_map.get(fg_pid, {})
        status, note = classify(row, property_map, qid_map)
        fg_value = clean(row.get("value"))
        rows.append(
            {
                "factgrid_item_id": clean(row.get("item_id")),
                "factgrid_item_label": clean(row.get("itemLabel")),
                "factgrid_property_id": fg_pid,
                "factgrid_property_label": clean(row.get("propertyLabel")),
                "tokenworks_property_id": mapping.get("tw_pid", ""),
                "tokenworks_property_label": mapping.get("tw_property_label", ""),
                "factgrid_value": fg_value,
                "factgrid_value_label": clean(row.get("value_display")),
                "tokenworks_value_qid": qid_map.get(fg_value, ""),
                "value_datatype": clean(row.get("value_datatype")),
                "value_type": clean(row.get("value_type")),
                "qualifier_property_id": clean(row.get("qualifier_property_id")),
                "qualifier_property_label": clean(row.get("qualifierPropertyLabel")),
                "qualifier_value": clean(row.get("qualifierValue")),
                "qualifier_value_label": clean(row.get("qualifier_value_display")),
                "import_status": status,
                "import_note": note,
            }
        )

    out = pd.DataFrame(rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output, index=False)
    summary = (
        out.groupby(["factgrid_property_id", "factgrid_property_label", "tokenworks_property_id", "import_status"], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(["factgrid_property_id", "import_status"])
    )
    summary.to_csv(args.summary, index=False)
    print(summary.to_string(index=False))
    print(f"Wrote staging -> {args.output}")
    print(f"Wrote summary -> {args.summary}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-claims", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--property-map", type=Path, default=DEFAULT_PROPERTY_MAP)
    parser.add_argument("--extra-property-map", type=Path, action="append", default=[DEFAULT_MISSING_PROPERTY_RESULTS])
    parser.add_argument("--authority-qids", type=Path, default=DEFAULT_AUTHORITY_QIDS)
    parser.add_argument("--artifact-qids", type=Path, default=DEFAULT_ARTIFACT_QIDS)
    parser.add_argument("--extra-qid-map", type=Path, action="append", default=[DEFAULT_RESEARCH_PROJECT_QIDS])
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    args = parser.parse_args()
    prepare(args)


if __name__ == "__main__":
    main()
