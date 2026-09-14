#!/usr/bin/env python3
"""Repair canonical FactGrid CDLI items after accidental duplicate creates.

For each duplicate pair, this script keeps the older/smaller canonical QID,
adds useful aliases from the duplicate/current CDLI row, and appends the ready
claims from the current statement plan to the canonical item.

It does not clear or repurpose the duplicate QID. Use the reuse-pool workflow
for that separate step.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import pandas as pd
from tqdm.auto import tqdm
from wikibaseintegrator.wbi_enums import ActionIfExists

from write_factgrid_cdli_artifact_items import (
    DEFAULT_ARTIFACTS,
    DEFAULT_COLLECTION_MATCHES,
    DEFAULT_FACTGRID_CDLI,
    DEFAULT_FACTGRID_UPLOAD_TABLE,
    DEFAULT_PLAN,
    DEFAULT_PRIOR_FACTGRID_QID_LOOKUPS,
    DEFAULT_STATEMENTS,
    FACTGRID_FINDING_SPOT_CONTEXT_FIELD,
    add_claims,
    api_login,
    build_workset as build_factgrid_workset,
    clean,
    format_cdli_id,
    parse_qid_list,
    robust_write,
)


WORKFLOW_ROOT = Path(__file__).resolve().parents[1]
PILOT_ROOT = WORKFLOW_ROOT / "published" / "pilots"
DEFAULT_RECONCILIATION = PILOT_ROOT / "factgrid_cdli_artifact_duplicate_reconciliation_staging.csv"
DEFAULT_RESULTS = PILOT_ROOT / "factgrid_cdli_artifact_duplicate_canonical_repair_results.csv"
DEFAULT_RESEARCH_PROJECT_QIDS = "Q1894741,Q389597,Q393513"


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, low_memory=False).fillna("")


def split_aliases(value: object) -> list[str]:
    aliases = []
    for part in clean(value).split("|"):
        text = clean(part)
        if text and text not in aliases:
            aliases.append(text[:250])
    return aliases


def build_workset(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame]:
    reconciliation = read_csv(args.reconciliation)
    results = read_csv(args.results)
    if reconciliation.empty:
        raise RuntimeError(f"No reconciliation rows found in {args.reconciliation}")
    done = set()
    if not results.empty and {"cdli_id", "repair_status"}.issubset(results.columns):
        done = set(results.loc[results["repair_status"].eq("written"), "cdli_id"].map(clean))
    work = reconciliation[~reconciliation["cdli_id"].map(clean).isin(done)].copy()
    if args.only_cdli_ids:
        allowed = {clean(v) for v in args.only_cdli_ids.replace(",", " ").split() if clean(v)}
        work = work[work["cdli_id"].map(clean).isin(allowed)].copy()
    if args.only_canonical_qids:
        allowed = {clean(v) for v in args.only_canonical_qids.replace(",", " ").split() if clean(v)}
        work = work[work["canonical_factgrid_qid"].map(clean).isin(allowed)].copy()
    if args.limit:
        work = work.head(args.limit).copy()
    writer_args = argparse.Namespace(
        artifacts=args.artifacts,
        statements=args.statements,
        factgrid_cdli=args.factgrid_cdli,
        prior_factgrid_qid_lookup=args.prior_factgrid_qid_lookup,
        factgrid_upload_table=args.factgrid_upload_table,
        collection_matches=args.collection_matches,
        results=Path("/tmp/factgrid_duplicate_canonical_repair_empty_results.csv"),
        limit=0,
        preview=args.preview,
        only_cdli_ids=" ".join(work["cdli_id"].map(clean)),
        only_missing_factgrid=False,
        only_existing_factgrid=True,
        only_field_names=args.only_field_names,
        reuse_pool=None,
        allow_unrepaired_reuse=False,
        allow_unapproved_reuse=False,
    )
    _, plan = build_factgrid_workset(writer_args)
    if not plan.empty:
        plan["_cdli_key"] = plan["cdli_id"].map(format_cdli_id)
        plan = plan[~plan["field_name"].eq(FACTGRID_FINDING_SPOT_CONTEXT_FIELD)].copy()
    return work, plan


def repair(args: argparse.Namespace) -> None:
    work, plan = build_workset(args)
    args.results.parent.mkdir(parents=True, exist_ok=True)
    print(f"canonical duplicate repairs selected: {len(work)}")
    if len(plan):
        print("\nStatement plan summary:")
        print(plan.groupby(["field_name", "fg_pid", "datatype"]).size().reset_index(name="count").to_string(index=False))
    if len(work):
        print("\nRepair preview:")
        print(
            work[
                [
                    "cdli_id",
                    "canonical_factgrid_qid",
                    "duplicate_factgrid_qid",
                    "canonical_label",
                    "duplicate_label",
                    "suggested_aliases_en",
                ]
            ]
            .head(args.preview)
            .to_string(index=False)
        )
    if not args.write:
        print("\nDRY_RUN: no canonical FactGrid items repaired. Pass --write to update canonical items.")
        return

    previous = read_csv(args.results)
    previous_written = previous[previous["repair_status"].eq("written")].copy() if not previous.empty else pd.DataFrame()
    out_rows = []
    wbi = api_login()
    research_project_qids = parse_qid_list(args.research_project_qids)
    for _, row in tqdm(work.iterrows(), total=len(work)):
        cdli_id = clean(row.get("cdli_id"))
        qid = clean(row.get("canonical_factgrid_qid"))
        item_plan = plan[plan["_cdli_key"].eq(format_cdli_id(cdli_id))].copy()
        try:
            item = wbi.item.get(qid)
            aliases = split_aliases(row.get("suggested_aliases_en"))
            if aliases:
                item.aliases.set(language="en", values=aliases, action_if_exists=ActionIfExists.APPEND_OR_REPLACE)
            claim_count, skipped_count = add_claims(item, item_plan, research_project_qids)
            robust_write(item, f"Repair canonical FactGrid CDLI duplicate {cdli_id}: {qid}")
            print(f"repaired canonical {qid} from duplicate {clean(row.get('duplicate_factgrid_qid'))} ({claim_count} claims; {skipped_count} skipped)", flush=True)
            out_rows.append(
                {
                    **row.to_dict(),
                    "claims_written": claim_count,
                    "claims_skipped": skipped_count,
                    "repair_status": "written",
                    "repair_error": "",
                }
            )
        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"[:500]
            print(f"canonical repair error: {qid} / {cdli_id} — {message}", flush=True)
            out_rows.append(
                {
                    **row.to_dict(),
                    "claims_written": 0,
                    "claims_skipped": len(item_plan),
                    "repair_status": "error",
                    "repair_error": message,
                }
            )
            if not args.continue_on_row_error:
                raise
        finally:
            pd.concat([previous_written, pd.DataFrame(out_rows)], ignore_index=True).drop_duplicates(["cdli_id"], keep="last").to_csv(args.results, index=False)
            time.sleep(args.sleep)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reconciliation", type=Path, default=DEFAULT_RECONCILIATION)
    parser.add_argument("--artifacts", type=Path, default=DEFAULT_ARTIFACTS)
    parser.add_argument("--statements", type=Path, default=DEFAULT_STATEMENTS)
    parser.add_argument("--factgrid-cdli", type=Path, default=DEFAULT_FACTGRID_CDLI)
    parser.add_argument("--prior-factgrid-qid-lookup", type=Path, action="append", default=[DEFAULT_PRIOR_FACTGRID_QID_LOOKUPS])
    parser.add_argument("--factgrid-upload-table", type=Path, default=DEFAULT_FACTGRID_UPLOAD_TABLE)
    parser.add_argument("--collection-matches", type=Path, default=DEFAULT_COLLECTION_MATCHES)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--research-project-qids", default=DEFAULT_RESEARCH_PROJECT_QIDS)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--preview", type=int, default=10)
    parser.add_argument("--sleep", type=float, default=2.0)
    parser.add_argument("--only-cdli-ids", default="")
    parser.add_argument("--only-canonical-qids", default="")
    parser.add_argument("--only-field-names", default="")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--continue-on-row-error", action="store_true")
    args = parser.parse_args()
    repair(args)


if __name__ == "__main__":
    main()
