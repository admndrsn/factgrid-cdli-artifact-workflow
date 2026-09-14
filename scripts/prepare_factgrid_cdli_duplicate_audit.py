#!/usr/bin/env python3
"""Audit duplicate FactGrid CDLI artifact items by CDLI ID.

This script is intentionally read-only. It consumes a live FactGrid artifact
register produced by `fetch_factgrid_existing_artifact_register.py` plus an
optional manually curated timeout-recovery CSV. It then stages:

- one row per duplicate CDLI-ID group;
- one reuse-pool row per surplus duplicate QID.

The reuse-pool output is not automatically approved. It preserves enough old
identity information to let us deliberately reuse accidental duplicate QIDs in
a later write.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

from write_cdli_new_artifact_items import clean, format_cdli_id


WORKFLOW_ROOT = Path(__file__).resolve().parents[1]
PILOT_ROOT = WORKFLOW_ROOT / "published" / "pilots"
EXISTING_ROOT = WORKFLOW_ROOT / "published" / "factgrid_existing"
DEFAULT_REGISTER = EXISTING_ROOT / "factgrid_existing_cdli_artifact_register.csv"
DEFAULT_TIMEOUT_RECOVERY = PILOT_ROOT / "factgrid_cdli_artifact_timeout_duplicate_recovery.csv"
DEFAULT_OUTPUT = PILOT_ROOT / "factgrid_cdli_artifact_duplicate_p692_audit.csv"
DEFAULT_REUSE_POOL = PILOT_ROOT / "factgrid_cdli_artifact_duplicate_p692_reuse_pool.csv"
DEFAULT_SUMMARY = PILOT_ROOT / "factgrid_cdli_artifact_duplicate_p692_audit_summary.csv"


def read_csv(path: Path) -> pd.DataFrame:
    if not path or not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, low_memory=False).fillna("")


def qid_number(qid: object) -> int:
    match = re.fullmatch(r"Q(\d+)", clean(qid))
    return int(match.group(1)) if match else 10**18


def split_qids(value: object) -> list[str]:
    qids: list[str] = []
    for part in re.split(r"[|,;\\s]+", clean(value)):
        if re.fullmatch(r"Q\d+", part) and part not in qids:
            qids.append(part)
    return qids


def build_live_duplicate_rows(register: pd.DataFrame) -> list[dict[str, str]]:
    if register.empty:
        return []
    required = {"item_id", "cdliId"}
    if not required.issubset(register.columns):
        raise RuntimeError(f"Live register is missing columns: {sorted(required - set(register.columns))}")

    rows: list[dict[str, str]] = []
    work = register.copy()
    work["_formatted_cdli_id"] = work["cdliId"].map(format_cdli_id)
    work = work[work["_formatted_cdli_id"].map(clean).ne("")]
    label_by_qid = (
        work.assign(_item_id=work["item_id"].map(clean), _label=work["itemLabel"].map(clean))
        .drop_duplicates("_item_id", keep="first")
        .set_index("_item_id")["_label"]
        .to_dict()
    )
    for cdli_id, group in work.groupby("_formatted_cdli_id", dropna=False):
        qids = sorted(set(group["item_id"].map(clean)), key=qid_number)
        qids = [qid for qid in qids if re.fullmatch(r"Q\d+", qid)]
        if len(qids) < 2:
            continue
        canonical = qids[0]
        duplicates = qids[1:]
        labels = []
        for qid in qids:
            label = clean(label_by_qid.get(qid))
            if label and label not in labels:
                labels.append(label)
        rows.append(
            {
                "cdli_id": cdli_id,
                "canonical_factgrid_qid": canonical,
                "duplicate_factgrid_qids": "|".join(duplicates),
                "canonical_label": clean(label_by_qid.get(canonical)) or (labels[0] if labels else ""),
                "all_labels_seen": " | ".join(labels),
                "duplicate_count": str(len(duplicates)),
                "source": "live_factgrid_register_p692",
            }
        )
    return rows


def build_timeout_rows(timeout_recovery: pd.DataFrame) -> list[dict[str, str]]:
    if timeout_recovery.empty:
        return []
    rows: list[dict[str, str]] = []
    required = {"cdli_id", "canonical_factgrid_qid", "duplicate_factgrid_qids"}
    if not required.issubset(timeout_recovery.columns):
        raise RuntimeError(f"Timeout recovery CSV is missing columns: {sorted(required - set(timeout_recovery.columns))}")
    for _, row in timeout_recovery.iterrows():
        duplicates = split_qids(row.get("duplicate_factgrid_qids"))
        if not duplicates:
            continue
        rows.append(
            {
                "cdli_id": format_cdli_id(row.get("cdli_id")),
                "canonical_factgrid_qid": clean(row.get("canonical_factgrid_qid")),
                "duplicate_factgrid_qids": "|".join(duplicates),
                "canonical_label": clean(row.get("canonical_label")),
                "all_labels_seen": clean(row.get("canonical_label")),
                "duplicate_count": str(len(duplicates)),
                "source": "manual_timeout_recovery",
            }
        )
    return rows


def merge_duplicate_rows(rows: list[dict[str, str]]) -> pd.DataFrame:
    merged: dict[str, dict[str, str]] = {}
    for row in rows:
        cdli_id = format_cdli_id(row.get("cdli_id"))
        if not cdli_id:
            continue
        qids = [clean(row.get("canonical_factgrid_qid")), *split_qids(row.get("duplicate_factgrid_qids"))]
        qids = sorted({qid for qid in qids if re.fullmatch(r"Q\d+", qid)}, key=qid_number)
        if len(qids) < 2:
            continue
        current = merged.setdefault(
            cdli_id,
            {
                "cdli_id": cdli_id,
                "canonical_factgrid_qid": qids[0],
                "duplicate_factgrid_qids": "",
                "canonical_label": clean(row.get("canonical_label")),
                "all_labels_seen": "",
                "duplicate_count": "0",
                "sources": "",
            },
        )
        all_qids = sorted(
            {
                current["canonical_factgrid_qid"],
                *split_qids(current.get("duplicate_factgrid_qids")),
                *qids,
            },
            key=qid_number,
        )
        current["canonical_factgrid_qid"] = all_qids[0]
        current["duplicate_factgrid_qids"] = "|".join(all_qids[1:])
        current["duplicate_count"] = str(len(all_qids) - 1)
        labels = [clean(v) for v in current.get("all_labels_seen", "").split(" | ") if clean(v)]
        for label in [row.get("canonical_label"), *clean(row.get("all_labels_seen")).split(" | ")]:
            label = clean(label)
            if label and label not in labels:
                labels.append(label)
        current["all_labels_seen"] = " | ".join(labels)
        if not current.get("canonical_label") and labels:
            current["canonical_label"] = labels[0]
        sources = [clean(v) for v in current.get("sources", "").split("|") if clean(v)]
        source = clean(row.get("source"))
        if source and source not in sources:
            sources.append(source)
        current["sources"] = "|".join(sources)
    out = pd.DataFrame(merged.values())
    if out.empty:
        return pd.DataFrame(
            columns=[
                "cdli_id",
                "canonical_factgrid_qid",
                "duplicate_factgrid_qids",
                "canonical_label",
                "all_labels_seen",
                "duplicate_count",
                "sources",
            ]
        )
    out["_canonical_num"] = out["canonical_factgrid_qid"].map(qid_number)
    return out.sort_values(["_canonical_num", "cdli_id"], kind="stable").drop(columns=["_canonical_num"])


def build_reuse_pool(audit: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, str]] = []
    for _, row in audit.iterrows():
        cdli_id = clean(row.get("cdli_id"))
        canonical_qid = clean(row.get("canonical_factgrid_qid"))
        canonical_label = clean(row.get("canonical_label"))
        aliases = clean(row.get("all_labels_seen"))
        for duplicate_qid in split_qids(row.get("duplicate_factgrid_qids")):
            rows.append(
                {
                    "reuse_pool_status": "hold_until_canonical_repair",
                    "reuse_candidate_class": "duplicate_p692_cdli_artifact",
                    "qid_available_for_future_entity": duplicate_qid,
                    "canonical_factgrid_qid": canonical_qid,
                    "old_cdli_id": cdli_id,
                    "old_duplicate_label_to_preserve": canonical_label,
                    "canonical_label": canonical_label,
                    "old_aliases_to_preserve": aliases,
                    "reuse_precondition_1": "canonical_factgrid_qid has been checked for complete CDLI claims",
                    "reuse_precondition_2": "old duplicate identity is preserved in this CSV before the item is repurposed",
                    "reuse_precondition_3": "manual approval or future_reuse_status=approved before clear=True rewrite",
                    "future_entity_type": "",
                    "future_entity_label": "",
                    "future_reuse_status": "",
                    "source_duplicate_audit": clean(row.get("sources")),
                }
            )
    out = pd.DataFrame(rows)
    if out.empty:
        return pd.DataFrame(
            columns=[
                "reuse_pool_status",
                "reuse_candidate_class",
                "qid_available_for_future_entity",
                "canonical_factgrid_qid",
                "old_cdli_id",
                "old_duplicate_label_to_preserve",
                "canonical_label",
                "old_aliases_to_preserve",
                "reuse_precondition_1",
                "reuse_precondition_2",
                "reuse_precondition_3",
                "future_entity_type",
                "future_entity_label",
                "future_reuse_status",
                "source_duplicate_audit",
            ]
        )
    out["_qid_number"] = out["qid_available_for_future_entity"].map(qid_number)
    return out.sort_values("_qid_number", kind="stable").drop(columns=["_qid_number"])


def write_summary(audit: pd.DataFrame, reuse_pool: pd.DataFrame, summary_path: Path) -> None:
    rows = [
        {"metric": "duplicate_cdli_groups", "value": len(audit)},
        {"metric": "duplicate_qids_available_for_review", "value": len(reuse_pool)},
        {"metric": "canonical_qids", "value": audit["canonical_factgrid_qid"].nunique() if not audit.empty else 0},
    ]
    if not audit.empty:
        for source, count in audit["sources"].value_counts().items():
            rows.append({"metric": f"groups_source_{source}", "value": count})
    pd.DataFrame(rows).to_csv(summary_path, index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--register", type=Path, default=DEFAULT_REGISTER)
    parser.add_argument("--timeout-recovery", type=Path, default=DEFAULT_TIMEOUT_RECOVERY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--reuse-pool", type=Path, default=DEFAULT_REUSE_POOL)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--preview", type=int, default=20)
    args = parser.parse_args()

    register = read_csv(args.register)
    timeout_recovery = read_csv(args.timeout_recovery)
    rows = [*build_live_duplicate_rows(register), *build_timeout_rows(timeout_recovery)]
    audit = merge_duplicate_rows(rows)
    reuse_pool = build_reuse_pool(audit)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.reuse_pool.parent.mkdir(parents=True, exist_ok=True)
    audit.to_csv(args.output, index=False)
    reuse_pool.to_csv(args.reuse_pool, index=False)
    write_summary(audit, reuse_pool, args.summary)

    print(pd.read_csv(args.summary).to_string(index=False))
    print(f"Wrote duplicate audit -> {args.output}")
    print(f"Wrote reuse pool -> {args.reuse_pool}")
    print(f"Wrote summary -> {args.summary}")
    if len(audit):
        print("\nAudit preview:")
        print(audit.head(args.preview).to_string(index=False))
    if len(reuse_pool):
        print("\nReuse pool preview:")
        print(reuse_pool.head(args.preview).to_string(index=False))


if __name__ == "__main__":
    main()
