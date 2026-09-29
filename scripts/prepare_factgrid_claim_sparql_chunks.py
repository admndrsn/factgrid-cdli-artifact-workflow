#!/usr/bin/env python3
"""Write exact-QID SPARQL files for live FactGrid claim comparison."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from textwrap import dedent

import pandas as pd

from write_cdli_new_artifact_items import clean
from write_factgrid_cdli_artifact_items import build_workset


WORKFLOW_ROOT = Path(__file__).resolve().parents[1]
PILOT_ROOT = WORKFLOW_ROOT / "published" / "pilots"
AUDIT_ROOT = WORKFLOW_ROOT / "published" / "live_claim_audit"
DEFAULT_ARTIFACTS = PILOT_ROOT / "cdli_artifact_staging_tranche_60001_85000.csv"
DEFAULT_STATEMENTS = PILOT_ROOT / "cdli_artifact_statement_staging_tranche_60001_85000.csv"
DEFAULT_RESULTS = PILOT_ROOT / "factgrid_cdli_artifact_write_results_tranche_60001_85000.csv"
DEFAULT_PLAN = PILOT_ROOT / "factgrid_cdli_artifact_live_claim_plan.csv"
DEFAULT_OUTPUT_DIR = AUDIT_ROOT / "manual_sparql_chunks"
DEFAULT_PROPERTIES = "P131,P692,P2,P853,P121,P401,P329,P695,P18"


def property_query_block(pid: str) -> str:
    return dedent(
        f"""
        {{
          ?item p:{pid} ?statement .
          ?statement ps:{pid} ?value .
          BIND("{pid}" AS ?property)
        }}
        """
    ).strip()


def build_query(qids: list[str], properties: list[str]) -> str:
    values = "\n    ".join(f"fg:{qid}" for qid in qids)
    union = "\n        UNION\n        ".join(property_query_block(pid) for pid in properties)
    return dedent(
        f"""
        PREFIX fg: <https://database.factgrid.de/entity/>
        PREFIX p: <https://database.factgrid.de/prop/>
        PREFIX ps: <https://database.factgrid.de/prop/statement/>
        PREFIX pq: <https://database.factgrid.de/prop/qualifier/>

        SELECT ?item ?property ?value ?qualifierProperty ?qualifierValue WHERE {{
          VALUES ?item {{
            {values}
          }}

          {{
            {union}
          }}

          OPTIONAL {{
            ?statement pq:P10 ?qualifierValue .
            BIND("P10" AS ?qualifierProperty)
          }}
        }}
        ORDER BY ?item ?property ?value ?qualifierProperty ?qualifierValue
        """
    ).strip()


def apply_common_workset_args(args: argparse.Namespace) -> None:
    args.factgrid_cdli = WORKFLOW_ROOT / "inputs" / "factgrid_tablet_sources" / "FG_CDLI_ID.csv"
    args.prior_factgrid_qid_lookup = [
        WORKFLOW_ROOT / "inputs" / "factgrid_tablet_sources" / "FG_OA_Published_prior_qid_lookup.csv",
        WORKFLOW_ROOT / "inputs" / "factgrid_tablet_sources" / "factgrid_existing_live_cdli_lookup.csv",
    ]
    args.factgrid_upload_table = Path("/Users/aa/Documents/FactGrid/FactgridCuneiform/_upload2FG/working_factgrid_df.csv")
    args.collection_matches = WORKFLOW_ROOT / "published" / "factgrid_museum_staging" / "cdli_missing_museums_factgrid_match_review.csv"
    args.only_missing_factgrid = False
    args.only_existing_factgrid = True
    args.reuse_pool = None
    args.allow_unrepaired_reuse = False
    args.allow_unapproved_reuse = False
    args.clear_existing_reuse = False


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, default=DEFAULT_ARTIFACTS)
    parser.add_argument("--statements", type=Path, default=DEFAULT_STATEMENTS)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--chunk-size", type=int, default=500)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--only-cdli-ids", default="")
    parser.add_argument("--only-field-names", default="")
    parser.add_argument("--properties", default=DEFAULT_PROPERTIES)
    parser.add_argument("--preview", type=int, default=10)
    args = parser.parse_args()

    apply_common_workset_args(args)
    requested_limit = args.limit
    args.limit = 0
    work, plan = build_workset(args)
    args.limit = requested_limit
    if work.empty:
        raise RuntimeError("No existing FactGrid rows selected for live-claim SPARQL export.")

    qids = [qid for qid in work["factgrid_qid"].map(clean).drop_duplicates().tolist() if re.fullmatch(r"Q\d+", qid)]
    if args.start:
        qids = qids[args.start :]
    if args.limit:
        qids = qids[: args.limit]
    properties = [pid for pid in re.split(r"[,;\s]+", clean(args.properties)) if re.fullmatch(r"P\d+", pid)]
    if not properties:
        raise RuntimeError("No valid properties supplied.")

    args.plan.parent.mkdir(parents=True, exist_ok=True)
    plan.to_csv(args.plan, index=False)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for chunk_number, start in enumerate(range(0, len(qids), args.chunk_size), start=1):
        chunk = qids[start : start + args.chunk_size]
        path = args.output_dir / f"factgrid_live_claims_chunk_{chunk_number:04d}.rq"
        path.write_text(build_query(chunk, properties) + "\n", encoding="utf-8")
        rows.append(
            {
                "chunk_number": chunk_number,
                "query_file": str(path),
                "qids": len(chunk),
                "first_qid": chunk[0] if chunk else "",
                "last_qid": chunk[-1] if chunk else "",
                "expected_export_csv": str(args.output_dir / f"factgrid_live_claims_chunk_{chunk_number:04d}.csv"),
            }
        )

    manifest = pd.DataFrame(rows)
    manifest_path = args.output_dir / "manifest.csv"
    manifest.to_csv(manifest_path, index=False)
    print(f"Live-claim QIDs selected: {len(qids)}")
    print(f"Properties: {', '.join(properties)}")
    print(f"Wrote {len(rows)} SPARQL chunks -> {args.output_dir}")
    print(f"Wrote manifest -> {manifest_path}")
    if rows:
        print(f"First query -> {rows[0]['query_file']}")


if __name__ == "__main__":
    main()
