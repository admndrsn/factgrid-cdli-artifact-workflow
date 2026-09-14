#!/usr/bin/env python3
"""Remove redundant bare FactGrid finding-spot claims.

This is for canonical duplicate repairs where a canonical item already had a
qualified P695 finding-spot statement and the repair appended the same P695
value as a bare statement. It removes only the bare duplicate when a qualified
claim with the same main value remains.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import pandas as pd
from tqdm.auto import tqdm

from write_factgrid_cdli_artifact_items import (
    FACTGRID_API,
    api_login,
    claim_main_value,
    clean,
    robust_write,
)


WORKFLOW_ROOT = Path(__file__).resolve().parents[1]
PILOT_ROOT = WORKFLOW_ROOT / "published" / "pilots"
DEFAULT_CANONICAL_REPAIRS = PILOT_ROOT / "factgrid_cdli_artifact_duplicate_canonical_repair_results.csv"
DEFAULT_OUTPUT = PILOT_ROOT / "factgrid_duplicate_finding_spot_repair_results.csv"
FINDING_SPOT_PID = "P695"


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, low_memory=False).fillna("")


def has_qualifiers(claim) -> bool:
    try:
        return bool(claim.qualifiers and claim.qualifiers.get_json())
    except Exception:
        try:
            return bool(claim.get_json().get("qualifiers"))
        except Exception:
            return False


def build_workset(args: argparse.Namespace) -> pd.DataFrame:
    repairs = read_csv(args.canonical_repairs)
    if repairs.empty:
        raise RuntimeError(f"No canonical repair rows found in {args.canonical_repairs}")
    if not {"canonical_factgrid_qid", "repair_status"}.issubset(repairs.columns):
        raise RuntimeError("Canonical repair results must include canonical_factgrid_qid and repair_status")
    work = repairs[repairs["repair_status"].eq("written")].copy()
    if args.only_qids:
        allowed = {clean(v) for v in args.only_qids.replace(",", " ").split() if clean(v)}
        work = work[work["canonical_factgrid_qid"].map(clean).isin(allowed)].copy()
    work = work.drop_duplicates("canonical_factgrid_qid", keep="last")
    previous = read_csv(args.output)
    if not previous.empty and {"factgrid_qid", "cleanup_status"}.issubset(previous.columns):
        done = set(previous.loc[previous["cleanup_status"].eq("written"), "factgrid_qid"].map(clean))
        work = work[~work["canonical_factgrid_qid"].map(clean).isin(done)].copy()
    if args.limit:
        work = work.head(args.limit).copy()
    return work


def find_bare_duplicate_claims(item) -> list:
    claims = list(item.claims.get(FINDING_SPOT_PID))
    qualified_values = {claim_main_value(claim) for claim in claims if has_qualifiers(claim)}
    to_remove = []
    seen_bare_values = set()
    for claim in claims:
        value = claim_main_value(claim)
        if not value or has_qualifiers(claim):
            continue
        if value in qualified_values or value in seen_bare_values:
            to_remove.append(claim)
        seen_bare_values.add(value)
    return to_remove


def repair(args: argparse.Namespace) -> None:
    work = build_workset(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    print(f"FactGrid duplicate finding-spot cleanup selected: {len(work)}")
    if len(work):
        print(work[["cdli_id", "canonical_factgrid_qid", "canonical_label"]].head(args.preview).to_string(index=False))
    if args.dry_run:
        preview = work.copy()
        preview["factgrid_qid"] = preview["canonical_factgrid_qid"].map(clean)
        preview["cleanup_status"] = "dry_run_preview"
        preview["cleanup_error"] = ""
        preview.to_csv(args.output, index=False)
        print("DRY_RUN: no FactGrid finding-spot claims removed.")
        print(f"Wrote cleanup preview -> {args.output}")
        return

    previous = read_csv(args.output)
    rows = []
    wbi = api_login()
    for _, row in tqdm(work.iterrows(), total=len(work)):
        result = row.to_dict()
        qid = clean(row.get("canonical_factgrid_qid"))
        try:
            item = wbi.item.get(qid)
            to_remove = find_bare_duplicate_claims(item)
            for claim in to_remove:
                claim.remove()
            if to_remove:
                robust_write(item, f"Remove redundant bare finding-spot claims from {qid}")
            result["factgrid_qid"] = qid
            result["removed_bare_duplicate_p695_count"] = str(len(to_remove))
            result["cleanup_status"] = "written"
            result["cleanup_error"] = ""
            print(f"cleaned {qid}: removed {len(to_remove)} bare duplicate {FINDING_SPOT_PID} claims", flush=True)
        except Exception as exc:
            result["factgrid_qid"] = qid
            result["removed_bare_duplicate_p695_count"] = "0"
            result["cleanup_status"] = "error"
            result["cleanup_error"] = f"{type(exc).__name__}: {exc}"[:500]
            print(f"finding-spot cleanup error {qid}: {result['cleanup_error']}", flush=True)
            if not args.continue_on_row_error:
                rows.append(result)
                pd.concat([previous, pd.DataFrame(rows)], ignore_index=True).drop_duplicates("factgrid_qid", keep="last").to_csv(args.output, index=False)
                raise
        rows.append(result)
        pd.concat([previous, pd.DataFrame(rows)], ignore_index=True).drop_duplicates("factgrid_qid", keep="last").to_csv(args.output, index=False)
        time.sleep(args.sleep)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical-repairs", type=Path, default=DEFAULT_CANONICAL_REPAIRS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--preview", type=int, default=20)
    parser.add_argument("--sleep", type=float, default=2.0)
    parser.add_argument("--only-qids", default="")
    parser.add_argument("--dry-run", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--continue-on-row-error", action="store_true")
    args = parser.parse_args()
    repair(args)


if __name__ == "__main__":
    main()
