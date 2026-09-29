#!/usr/bin/env python3
"""Compare planned CDLI artifact claims with freshly exported FactGrid claims."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

import pandas as pd

from prepare_factgrid_cdli_quickstatements import (
    live_claim_exists,
    load_live_claims,
    normalize_live_value,
    qs_value,
)
from prepare_factgrid_claim_sparql_chunks import apply_common_workset_args
from write_cdli_new_artifact_items import artifact_label_for, clean
from write_factgrid_cdli_artifact_items import (
    DEFAULT_PLAN,
    DEFAULT_RESULTS,
    DEFAULT_STATEMENTS,
    FACTGRID_INVENTORY_NUMBER_FIELD,
    FACTGRID_INVENTORY_NUMBER_QUALIFIER_PROPERTY,
    FACTGRID_PRESENT_HOLDING_PROPERTY,
    FACTGRID_RESEARCH_PROJECT_PROPERTY,
    build_workset,
    parse_qid_list,
)


WORKFLOW_ROOT = Path(__file__).resolve().parents[1]
PILOT_ROOT = WORKFLOW_ROOT / "published" / "pilots"
LIVE_CLAIM_ROOT = WORKFLOW_ROOT / "published" / "live_claim_audit"
DEFAULT_ARTIFACTS = PILOT_ROOT / "cdli_artifact_staging_tranche_60001_85000.csv"
DEFAULT_OUTPUT = LIVE_CLAIM_ROOT / "factgrid_cdli_artifact_live_claim_review.csv"
DEFAULT_SUMMARY = LIVE_CLAIM_ROOT / "factgrid_cdli_artifact_live_claim_review_summary.csv"
SINGLE_VALUE_PROPERTIES = {"P2", "P18", "P121", "P401", "P692", "P695", "P853"}


class LiveClaimIndex:
    def __init__(self, live_claims: set[tuple[str, str, str, str, str]]) -> None:
        self.claims = live_claims
        self.values_by_item_property: dict[tuple[str, str], set[str]] = {}
        self.qualifiers_by_claim: dict[tuple[str, str, str, str], set[str]] = {}
        for qid, prop, value, qualifier_prop, qualifier_value in live_claims:
            self.values_by_item_property.setdefault((qid, prop), set()).add(value)
            if qualifier_prop:
                self.qualifiers_by_claim.setdefault((qid, prop, value, qualifier_prop), set()).add(qualifier_value)

    def has_claim(
        self,
        qid: str,
        prop: str,
        value: str,
        qualifier_prop: str = "",
        qualifier_value: str = "",
    ) -> bool:
        return (
            qid,
            prop,
            normalize_live_value(value),
            qualifier_prop,
            normalize_live_value(qualifier_value),
        ) in self.claims

    def values_for(self, qid: str, prop: str) -> list[str]:
        return sorted(self.values_by_item_property.get((qid, prop), set()))

    def qualifier_values_for(self, qid: str, prop: str, value: str, qualifier_prop: str) -> list[str]:
        return sorted(self.qualifiers_by_claim.get((qid, prop, normalize_live_value(value), qualifier_prop), set()))


def live_values_for(
    live_claims: set[tuple[str, str, str, str, str]],
    qid: str,
    prop: str,
) -> list[str]:
    values = sorted({value for live_qid, live_prop, value, _, _ in live_claims if live_qid == qid and live_prop == prop})
    return values


def live_qualifier_values_for(
    live_claims: set[tuple[str, str, str, str, str]],
    qid: str,
    prop: str,
    value: str,
    qualifier_prop: str,
) -> list[str]:
    normalized = normalize_live_value(value)
    values = sorted(
        {
            qualifier_value
            for live_qid, live_prop, live_value, live_qualifier_prop, qualifier_value in live_claims
            if live_qid == qid
            and live_prop == prop
            and live_value == normalized
            and live_qualifier_prop == qualifier_prop
        }
    )
    return values


def planned_claim_status(
    live_index: LiveClaimIndex,
    qid: str,
    prop: str,
    value: str,
    qualifier_prop: str = "",
    qualifier_value: str = "",
) -> tuple[str, str, str]:
    live_values = live_index.values_for(qid, prop)
    if qualifier_prop or qualifier_value:
        if live_index.has_claim(qid, prop, value, qualifier_prop, qualifier_value):
            return "already_live", "exact qualifier claim already present", " | ".join(live_values)
        if live_index.has_claim(qid, prop, value):
            qualifiers = live_index.qualifier_values_for(qid, prop, value, qualifier_prop)
            note = "main claim present, planned qualifier missing"
            if qualifiers:
                note += f"; live {qualifier_prop}: {' | '.join(qualifiers)}"
            return "missing_qualifier", note, " | ".join(live_values)
        if prop in SINGLE_VALUE_PROPERTIES and live_values:
            return "conflict_same_property", "different live value exists for single-value property", " | ".join(live_values)
        return "missing", "planned claim absent from live export", " | ".join(live_values)
    if live_index.has_claim(qid, prop, value):
        return "already_live", "exact claim already present", " | ".join(live_values)
    if prop in SINGLE_VALUE_PROPERTIES and live_values:
        return "conflict_same_property", "different live value exists for single-value property", " | ".join(live_values)
    return "missing", "planned claim absent from live export", " | ".join(live_values)


def select_workset(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame]:
    apply_common_workset_args(args)
    requested_limit = args.limit
    args.limit = 0
    work, plan = build_workset(args)
    args.limit = requested_limit
    if args.start:
        work = work.iloc[args.start :].copy()
    if requested_limit:
        work = work.head(requested_limit).copy()
    if work.empty:
        raise RuntimeError("No existing FactGrid rows selected after applying --start/--limit.")
    selected = set(work["cdli_id"].map(clean))
    plan = plan[plan["cdli_id"].map(clean).isin(selected)].copy()
    return work, plan


def add_review_row(
    rows: list[dict[str, str]],
    live_index: LiveClaimIndex,
    artifact: pd.Series,
    field_name: str,
    prop: str,
    value: str,
    value_label: str = "",
    qualifier_prop: str = "",
    qualifier_value: str = "",
) -> None:
    qid = clean(artifact.get("factgrid_qid"))
    status, note, live_values = planned_claim_status(live_index, qid, prop, value, qualifier_prop, qualifier_value)
    rows.append(
        {
            "review_status": status,
            "cdli_id": clean(artifact.get("cdli_id")),
            "factgrid_qid": qid,
            "artifact_label": artifact_label_for(artifact),
            "field_name": field_name,
            "fg_pid": prop,
            "planned_value": value,
            "planned_value_label": value_label,
            "qualifier_property": qualifier_prop,
            "qualifier_value": qualifier_value,
            "live_values_for_property": live_values,
            "note": note,
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, default=DEFAULT_ARTIFACTS)
    parser.add_argument("--statements", type=Path, default=DEFAULT_STATEMENTS)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--live-claims-csv", type=Path, action="append", nargs="+", required=True)
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--preview", type=int, default=20)
    parser.add_argument("--only-cdli-ids", default="")
    parser.add_argument("--only-field-names", default="")
    parser.add_argument("--research-project-qids", default="Q1894741,Q389597,Q393513")
    args = parser.parse_args()

    live_claims = load_live_claims(args.live_claims_csv)
    if not live_claims:
        raise RuntimeError("No live claims loaded. Check --live-claims-csv path(s).")
    live_index = LiveClaimIndex(live_claims)
    work, plan = select_workset(args)
    research_project_qids = parse_qid_list(args.research_project_qids)

    rows: list[dict[str, str]] = []
    for _, artifact in work.iterrows():
        cdli_id = clean(artifact.get("cdli_id"))
        item_plan = plan[plan["cdli_id"].map(clean).eq(cdli_id)].copy()
        for research_project_qid in research_project_qids:
            add_review_row(
                rows,
                live_index,
                artifact,
                "research_project",
                FACTGRID_RESEARCH_PROJECT_PROPERTY,
                research_project_qid,
            )

        inventory_values = []
        for value in item_plan.loc[item_plan["field_name"].eq(FACTGRID_INVENTORY_NUMBER_FIELD), "value"].map(clean):
            if value and value not in inventory_values:
                inventory_values.append(value[:400])

        for _, plan_row in item_plan.iterrows():
            field_name = clean(plan_row.get("field_name"))
            if field_name == FACTGRID_INVENTORY_NUMBER_FIELD:
                continue
            prop = clean(plan_row.get("fg_pid"))
            value = qs_value(plan_row)
            if not prop or not value:
                continue
            value_label = clean(plan_row.get("value_label"))
            if prop == FACTGRID_PRESENT_HOLDING_PROPERTY and inventory_values:
                for inventory in inventory_values:
                    add_review_row(
                        rows,
                        live_index,
                        artifact,
                        field_name,
                        prop,
                        value,
                        value_label,
                        FACTGRID_INVENTORY_NUMBER_QUALIFIER_PROPERTY,
                        inventory,
                    )
            else:
                add_review_row(rows, live_index, artifact, field_name, prop, value, value_label)

    review = pd.DataFrame(rows)
    summary = (
        review.groupby(["fg_pid", "field_name", "review_status"], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(["review_status", "fg_pid", "field_name"])
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    review.to_csv(args.output, index=False, quoting=csv.QUOTE_MINIMAL)
    summary.to_csv(args.summary, index=False, quoting=csv.QUOTE_MINIMAL)

    print(f"Loaded live claims: {len(live_claims)}")
    print(f"Reviewed items: {len(work)}")
    print(f"Reviewed planned claims: {len(review)}")
    print(summary.to_string(index=False))
    print(f"Wrote review -> {args.output}")
    print(f"Wrote summary -> {args.summary}")
    if args.preview:
        print(review.loc[review["review_status"].ne("already_live")].head(args.preview).to_string(index=False))


if __name__ == "__main__":
    main()
