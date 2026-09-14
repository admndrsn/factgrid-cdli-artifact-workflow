#!/usr/bin/env python3
"""Stage TokenWorks claims for ORACC project authority items.

The ORACC source sheet has human-readable column headers in row 1 and FactGrid
property IDs in row 2. This script treats row 2 as authoritative, maps those
FactGrid properties through the TokenWorks property map, and reports whether
each value is ready to write or needs a TokenWorks QID/property decision.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


WORKFLOW_ROOT = Path(__file__).resolve().parents[1]
TOKENWORKS_ROOT = WORKFLOW_ROOT.parents[0]
DEFAULT_ORACC_PROJECTS = WORKFLOW_ROOT / "inputs" / "cdli_lookup_sources" / "oracc_project_list.csv"
DEFAULT_PROPERTY_MAP = TOKENWORKS_ROOT / "tw_property_completion_results.csv"
DEFAULT_PROJECT_QIDS = WORKFLOW_ROOT / "published" / "factgrid_model_samples" / "cdli_research_project_authority_results.csv"
DEFAULT_AUTHORITY_QIDS = WORKFLOW_ROOT / "published" / "pilots" / "cdli_authority_item_results_pilot_10000.csv"
DEFAULT_OUTPUT = WORKFLOW_ROOT / "published" / "factgrid_model_samples" / "oracc_project_claim_staging.csv"
DEFAULT_SUMMARY = WORKFLOW_ROOT / "published" / "factgrid_model_samples" / "oracc_project_claim_staging_summary.csv"

TERM_COLUMNS = {"FG_Qid", "Len", "Aen", "Den"}


def clean(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null"}:
        return ""
    return text


def factgrid_qid(value: object) -> str:
    text = clean(value)
    if not text:
        return ""
    if "/Item:" in text:
        return text.rsplit("/Item:", 1)[-1].strip()
    if "/entity/" in text:
        return text.rsplit("/entity/", 1)[-1].strip()
    if text.startswith("Q"):
        return text
    return ""


def load_property_map(path: Path) -> dict[str, dict[str, str]]:
    df = pd.read_csv(path, dtype=str, low_memory=False).fillna("")
    fg_col = "factgrid_pid" if "factgrid_pid" in df.columns else "factgridPid"
    tw_col = "final_tw_pid" if "final_tw_pid" in df.columns else "twPid"
    label_col = "property_label" if "property_label" in df.columns else "propertyLabel"
    out = {}
    for _, row in df.iterrows():
        fg_pid = clean(row.get(fg_col))
        tw_pid = clean(row.get(tw_col))
        if fg_pid and tw_pid:
            out[fg_pid] = {
                "tw_pid": tw_pid,
                "tw_property_label": clean(row.get(label_col)),
                "datatype": clean(row.get("datatype")),
            }
    return out


def load_qid_map(paths: list[Path]) -> dict[str, str]:
    out = {}
    for path in paths:
        if not path.exists():
            continue
        df = pd.read_csv(path, dtype=str, low_memory=False).fillna("")
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


def load_oracc_sheet(path: Path) -> tuple[list[str], list[str], pd.DataFrame]:
    if not path.exists():
        raise RuntimeError(f"Missing ORACC project CSV: {path}. Run download_cdli_lookup_sources.py first.")
    raw = pd.read_csv(path, dtype=str, header=None, low_memory=False).fillna("")
    if len(raw) < 3:
        raise RuntimeError(f"ORACC project CSV needs two header rows and data rows: {path}")
    labels = [clean(value) for value in raw.iloc[0].tolist()]
    fg_pids = [clean(value) for value in raw.iloc[1].tolist()]
    data = raw.iloc[2:].copy()
    data.columns = labels[: len(data.columns)]
    return labels, fg_pids, data


def classify_value(datatype: str, value: str, qid_map: dict[str, str]) -> tuple[str, str, str]:
    qid = factgrid_qid(value)
    if datatype == "wikibase-item":
        if qid and qid in qid_map:
            return "ready", qid_map[qid], "Mapped FactGrid item value to TokenWorks QID"
        if qid:
            return "needs_value_qid", "", f"Need TokenWorks QID for FactGrid value {qid}"
        return "needs_datatype_review", "", "Expected FactGrid QID for wikibase-item value"
    if datatype == "url":
        if value.startswith(("http://", "https://")):
            return "ready", "", "URL value can be copied"
        return "needs_datatype_review", "", "URL property has non-URL value"
    if datatype in {"string", "external-id", "quantity", "time", "monolingualtext"}:
        return "ready", "", f"{datatype} value can be copied"
    return "needs_datatype_review", "", f"Review unsupported or missing datatype {datatype}"


def prepare(args: argparse.Namespace) -> None:
    labels, fg_pids, data = load_oracc_sheet(args.oracc_projects)
    property_map = load_property_map(args.property_map)
    qid_map = load_qid_map([args.project_qids, args.authority_qids])

    rows = []
    for _, source in data.iterrows():
        project_fg_qid = factgrid_qid(source.get("FactGrid_ID"))
        project_label = clean(source.get("Label"))
        project_tw_qid = qid_map.get(project_fg_qid, "")
        if not project_fg_qid:
            continue
        for col_idx, column in enumerate(labels):
            if not column or column in TERM_COLUMNS:
                continue
            fg_pid = fg_pids[col_idx] if col_idx < len(fg_pids) else ""
            value = clean(source.get(column))
            if not value or not fg_pid or not fg_pid.startswith("P"):
                continue
            mapping = property_map.get(fg_pid, {})
            if not mapping:
                status, tw_value_qid, note = "unmapped_property", "", f"No TokenWorks property mapped for FactGrid {fg_pid}"
            else:
                status, tw_value_qid, note = classify_value(clean(mapping.get("datatype")), value, qid_map)
            rows.append(
                {
                    "source_column": column,
                    "factgrid_property_id": fg_pid,
                    "tokenworks_property_id": clean(mapping.get("tw_pid")),
                    "tokenworks_property_label": clean(mapping.get("tw_property_label")),
                    "datatype": clean(mapping.get("datatype")),
                    "project_factgrid_qid": project_fg_qid,
                    "project_tokenworks_qid": project_tw_qid,
                    "project_label": project_label,
                    "value": value,
                    "value_factgrid_qid": factgrid_qid(value),
                    "value_tokenworks_qid": tw_value_qid,
                    "claim_status": status,
                    "claim_note": note,
                }
            )

    out = pd.DataFrame(rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output, index=False)
    summary = (
        out.groupby(["source_column", "factgrid_property_id", "tokenworks_property_id", "claim_status"], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(["claim_status", "source_column"])
    )
    summary.to_csv(args.summary, index=False)
    print(summary.to_string(index=False))
    print(f"Wrote ORACC project claim staging -> {args.output}")
    print(f"Wrote summary -> {args.summary}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--oracc-projects", type=Path, default=DEFAULT_ORACC_PROJECTS)
    parser.add_argument("--property-map", type=Path, default=DEFAULT_PROPERTY_MAP)
    parser.add_argument("--project-qids", type=Path, default=DEFAULT_PROJECT_QIDS)
    parser.add_argument("--authority-qids", type=Path, default=DEFAULT_AUTHORITY_QIDS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    args = parser.parse_args()
    prepare(args)


if __name__ == "__main__":
    main()
