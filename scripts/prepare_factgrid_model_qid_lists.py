#!/usr/bin/env python3
"""Prepare FactGrid QID lists for CDLI pilot model comparison.

The lists produced here are read-only inputs for ``fetch_factgrid_item_model.py``.
They let us retrieve FactGrid statements for both directly matched CDLI artifact
items and TokenWorks authority items aligned to FactGrid QIDs.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


WORKFLOW_ROOT = Path(__file__).resolve().parents[1]
PILOT_ROOT = WORKFLOW_ROOT / "published" / "pilots"
DEFAULT_STATEMENTS = PILOT_ROOT / "cdli_artifact_statement_staging_pilot_10000_with_lookups.csv"
DEFAULT_AUTHORITY_RESULTS = PILOT_ROOT / "cdli_authority_item_results_pilot_10000.csv"
DEFAULT_OUTPUT_DIR = WORKFLOW_ROOT / "published" / "factgrid_model_samples"


def clean(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null"}:
        return ""
    return text


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise RuntimeError(f"Missing input CSV: {path}")
    return pd.read_csv(path, dtype=str, low_memory=False).fillna("")


def prepare_lists(args: argparse.Namespace) -> None:
    statements = load_csv(args.statements)
    authority = load_csv(args.authority_results)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    artifact_rows = statements[statements["field_name"].eq("factgrid_item_id")].copy()
    artifact_rows = artifact_rows[artifact_rows["value"].map(clean).ne("")]
    artifact_out = (
        artifact_rows.rename(columns={"value": "factgrid_qid", "value_label": "factgrid_label", "tw_qid": "tokenworks_qid"})
        [["factgrid_qid", "factgrid_label", "tokenworks_qid", "cdli_id", "artifact_label", "artifact_type"]]
        .drop_duplicates("factgrid_qid", keep="first")
        .sort_values("factgrid_qid")
    )

    authority_out = authority[authority["factgrid_qid"].map(clean).ne("") & authority["tw_qid"].map(clean).ne("")].copy()
    authority_out = authority_out.rename(columns={"tw_qid": "tokenworks_qid"})
    authority_out = authority_out[
        [
            "factgrid_qid",
            "label_en",
            "tokenworks_qid",
            "source_fields",
            "source_count",
            "source_cdli_count",
            "description_en",
            "aliases_en",
        ]
    ].drop_duplicates("factgrid_qid", keep="first")
    authority_out = authority_out.sort_values(["source_fields", "factgrid_qid"])

    all_out = pd.concat(
        [
            artifact_out.assign(qid_source="artifact_factgrid_item_id"),
            authority_out.rename(columns={"label_en": "factgrid_label"}).assign(qid_source="authority_alignment"),
        ],
        ignore_index=True,
        sort=False,
    ).drop_duplicates("factgrid_qid", keep="first")
    all_out = all_out.sort_values(["qid_source", "factgrid_qid"])

    artifact_path = args.output_dir / "factgrid_pilot_artifact_qids.csv"
    authority_path = args.output_dir / "factgrid_pilot_authority_qids.csv"
    all_path = args.output_dir / "factgrid_pilot_all_qids.csv"
    all_txt_path = args.output_dir / "factgrid_pilot_all_qids.txt"
    summary_path = args.output_dir / "factgrid_pilot_qid_list_summary.csv"

    artifact_out.to_csv(artifact_path, index=False)
    authority_out.to_csv(authority_path, index=False)
    all_out.to_csv(all_path, index=False)
    all_txt_path.write_text("\n".join(all_out["factgrid_qid"].tolist()) + "\n", encoding="utf-8")

    summary = pd.DataFrame(
        [
            ("artifact_factgrid_qids", len(artifact_out)),
            ("authority_factgrid_qids", len(authority_out)),
            ("all_unique_factgrid_qids", len(all_out)),
            ("authority_q132027_factgrid_qid", authority_out.loc[authority_out["tokenworks_qid"].eq("Q132027"), "factgrid_qid"].iloc[0] if authority_out["tokenworks_qid"].eq("Q132027").any() else ""),
            ("authority_q132027_label", authority_out.loc[authority_out["tokenworks_qid"].eq("Q132027"), "label_en"].iloc[0] if authority_out["tokenworks_qid"].eq("Q132027").any() else ""),
        ],
        columns=["metric", "value"],
    )
    summary.to_csv(summary_path, index=False)

    print(summary.to_string(index=False))
    print(f"Wrote artifact QIDs -> {artifact_path}")
    print(f"Wrote authority QIDs -> {authority_path}")
    print(f"Wrote all QIDs -> {all_path}")
    print(f"Wrote all QID text list -> {all_txt_path}")
    print(f"Wrote summary -> {summary_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--statements", type=Path, default=DEFAULT_STATEMENTS)
    parser.add_argument("--authority-results", type=Path, default=DEFAULT_AUTHORITY_RESULTS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    prepare_lists(args)


if __name__ == "__main__":
    main()
