#!/usr/bin/env python3
"""Prepare FactGrid tablet QID lists from a CDLI/FactGrid alignment CSV.

The input is the user's reviewed FactGrid tablet sheet export with columns:

- Clay_tablet: FactGrid item URL or QID
- Clay_tabletLabel: FactGrid label
- CDLI_ID: optional CDLI external ID

Outputs are read-only staging files used by the FactGrid model fetch/import
workflow. No Wikibase writes happen here.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd


WORKFLOW_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = WORKFLOW_ROOT / "inputs" / "factgrid_tablet_sources" / "FG_CDLI_ID.csv"
DEFAULT_OUTPUT_DIR = WORKFLOW_ROOT / "published" / "factgrid_model_samples"


def clean(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null"}:
        return ""
    return text


def extract_qid(value: object) -> str:
    match = re.search(r"\bQ\d+\b", clean(value))
    return match.group(0) if match else ""


def format_cdli_id(value: object) -> str:
    text = clean(value)
    match = re.search(r"(\d+)", text)
    if not match:
        return text
    return f"P{int(match.group(1)):06d}"


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise RuntimeError(f"Missing input CSV: {path}")
    return pd.read_csv(path, dtype=str, low_memory=False).fillna("")


def prepare(args: argparse.Namespace) -> None:
    source = load_csv(args.input)
    required = {"Clay_tablet", "Clay_tabletLabel", "CDLI_ID"}
    missing = required - set(source.columns)
    if missing:
        raise RuntimeError(f"{args.input} is missing required columns: {sorted(missing)}")

    out = pd.DataFrame(
        {
            "factgrid_qid": source["Clay_tablet"].map(extract_qid),
            "factgrid_label": source["Clay_tabletLabel"].map(clean),
            "cdli_id": source["CDLI_ID"].map(format_cdli_id),
            "source_url": source["Clay_tablet"].map(clean),
        }
    )
    out = out[out["factgrid_qid"].ne("")].copy()
    out["has_cdli_id"] = out["cdli_id"].ne("").map({True: "yes", False: "no"})
    out = out.drop_duplicates(["factgrid_qid", "cdli_id"], keep="first").sort_values(["factgrid_qid", "cdli_id"])

    tranche_out = pd.DataFrame()
    if args.artifacts:
        artifacts = load_csv(args.artifacts)
        if "cdli_id" not in artifacts.columns:
            raise RuntimeError(f"{args.artifacts} is missing cdli_id")
        artifact_ids = set(artifacts["cdli_id"].map(format_cdli_id))
        tranche_out = out[out["cdli_id"].isin(artifact_ids) & out["cdli_id"].ne("")].copy()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    all_path = args.output_dir / args.output
    text_path = args.output_dir / args.text_output
    summary_path = args.output_dir / args.summary
    out.to_csv(all_path, index=False)
    text_path.write_text("\n".join(out["factgrid_qid"].drop_duplicates().tolist()) + "\n", encoding="utf-8")

    rows = [
        ("source_rows", len(source)),
        ("prepared_rows", len(out)),
        ("unique_factgrid_qids", out["factgrid_qid"].nunique()),
        ("rows_with_cdli_id", int(out["cdli_id"].ne("").sum())),
        ("unique_cdli_ids", out.loc[out["cdli_id"].ne(""), "cdli_id"].nunique()),
    ]
    if args.artifacts:
        tranche_path = args.output_dir / args.tranche_output
        tranche_text_path = args.output_dir / args.tranche_text_output
        tranche_out.to_csv(tranche_path, index=False)
        tranche_text_path.write_text(
            "\n".join(tranche_out["factgrid_qid"].drop_duplicates().tolist()) + "\n",
            encoding="utf-8",
        )
        rows.extend(
            [
                ("tranche_rows", len(tranche_out)),
                ("tranche_unique_factgrid_qids", tranche_out["factgrid_qid"].nunique() if not tranche_out.empty else 0),
                ("tranche_unique_cdli_ids", tranche_out["cdli_id"].nunique() if not tranche_out.empty else 0),
            ]
        )
        print(f"Wrote tranche QIDs -> {tranche_path}")
        print(f"Wrote tranche QID text list -> {tranche_text_path}")

    summary = pd.DataFrame(rows, columns=["metric", "value"])
    summary.to_csv(summary_path, index=False)
    print(summary.to_string(index=False))
    print(f"Wrote all tablet QIDs -> {all_path}")
    print(f"Wrote all tablet QID text list -> {text_path}")
    print(f"Wrote summary -> {summary_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--artifacts", type=Path, help="Optional CDLI artifact staging CSV to create a tranche overlap list.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--output", default="factgrid_tablet_all_qids.csv")
    parser.add_argument("--text-output", default="factgrid_tablet_all_qids.txt")
    parser.add_argument("--tranche-output", default="factgrid_tablet_tranche_qids.csv")
    parser.add_argument("--tranche-text-output", default="factgrid_tablet_tranche_qids.txt")
    parser.add_argument("--summary", default="factgrid_tablet_qid_list_summary.csv")
    args = parser.parse_args()
    prepare(args)


if __name__ == "__main__":
    main()
