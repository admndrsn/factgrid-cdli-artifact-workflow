#!/usr/bin/env python3
"""Mark known FactGrid label-collision rows as resumable skips.

When WikibaseIntegrator wraps label collisions in a RetryError, older result
rows may have write_status=error without the collision QID. This utility reads a
terminal log/paste, extracts the collision target QIDs in order, and marks the
matching error rows as write_status=label_collision.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

from write_cdli_new_artifact_items import clean


WORKFLOW_ROOT = Path(__file__).resolve().parents[1]
PILOT_ROOT = WORKFLOW_ROOT / "published" / "pilots"
DEFAULT_RESULTS = PILOT_ROOT / "factgrid_cdli_artifact_write_results_tranche_10001_35000.csv"


def extract_collision_qids(log_path: Path) -> list[str]:
    text = log_path.read_text(errors="replace")
    qids = []
    for qid in re.findall(r"Item \[\[Item:(Q\d+)\|Q\d+\]\] already has label", text):
        if qid not in qids:
            qids.append(qid)
    return qids


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    df = pd.read_csv(args.results, dtype=str, low_memory=False).fillna("")
    if "label_collision_qid" not in df.columns:
        df["label_collision_qid"] = ""
    qids = extract_collision_qids(args.log)
    error_idx = list(df.index[df["write_status"].eq("error")])
    changed = []
    for idx, collision_qid in zip(error_idx, qids):
        df.at[idx, "write_status"] = "label_collision"
        df.at[idx, "label_collision_qid"] = collision_qid
        current_error = clean(df.at[idx, "write_error"])
        if collision_qid not in current_error:
            df.at[idx, "write_error"] = f"{current_error}; label collision with {collision_qid}".strip("; ")
        changed.append(
            {
                "cdli_id": clean(df.at[idx, "cdli_id"]),
                "attempted_reuse_qid": clean(df.at[idx, "factgrid_qid"]),
                "label_collision_qid": collision_qid,
            }
        )

    print(f"collision qids in log: {len(qids)}")
    print(f"error rows marked: {len(changed)}")
    if changed:
        print(pd.DataFrame(changed).to_string(index=False))
    if args.write:
        df.to_csv(args.results, index=False)
        print(f"Wrote updated results -> {args.results}")
    else:
        print("DRY_RUN: pass --write to update the results CSV.")


if __name__ == "__main__":
    main()
