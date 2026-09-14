#!/usr/bin/env python3
"""Prepare TokenWorks statement staging rows for CDLI artifact items.

This script does not write to TokenWorks. It joins flattened CDLI artifact JSON
rows, optional QID reuse reservations, optional FactGrid CDLI coverage, and
CSV exports from the CDLI/FactGrid lookup sheets into a reviewable statement
plan.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd


WORKFLOW_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACTS = WORKFLOW_ROOT / "published" / "pilots" / "cdli_artifact_staging_pilot_100.csv"
DEFAULT_RESERVATIONS = WORKFLOW_ROOT / "published" / "pilots" / "cdli_artifact_qid_reuse_reservations_pilot_10.csv"
DEFAULT_OUTPUT = WORKFLOW_ROOT / "published" / "pilots" / "cdli_artifact_statement_staging_pilot.csv"
DEFAULT_SUMMARY = WORKFLOW_ROOT / "published" / "pilots" / "cdli_artifact_statement_staging_pilot_summary.csv"


TW_PROPS = {
    "instance_of": "P2",
    "language": "P18",
    "present_holding": "P203",
    "inventory_number": "P10",
    "material": "P391",
    "bdtns_id": "P392",
    "oracc_id": "P393",
    "finding_spot_context": "P394",
    "type_of_work": "P126",
    "cdli_id": "P223",
    "finding_spot": "P224",
    "script_style": "P228",
    "period": "P245",
    "factgrid_item_id": "P378",
}

FG_PROPS = {
    "instance_of": "P2",
    "language": "P18",
    "present_holding": "P329",
    "inventory_number": "P10",
    "material": "P401",
    "bdtns_id": "P959",
    "oracc_id": "P960",
    "finding_spot_context": "P425",
    "type_of_work": "P121",
    "cdli_id": "P692",
    "finding_spot": "P695",
    "script_style": "P747",
    "period": "P853",
}


def clean(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null"}:
        return ""
    return text


def format_cdli_id(value: object) -> str:
    text = clean(value)
    match = re.search(r"(\d+)", text)
    if not match:
        return text
    return f"P{int(match.group(1)):06d}"


def norm(value: object) -> str:
    return re.sub(r"\s+", " ", clean(value).casefold())


def qid_from_uri(value: object) -> str:
    text = clean(value)
    match = re.search(r"(Q\d+)$", text)
    return match.group(1) if match else text


def is_qid(value: object) -> bool:
    return bool(re.fullmatch(r"Q\d+", clean(value)))


def first_existing(df: pd.DataFrame, names: list[str]) -> str:
    lowered = {c.casefold(): c for c in df.columns}
    for name in names:
        if name.casefold() in lowered:
            return lowered[name.casefold()]
    return ""


def existing_columns(df: pd.DataFrame, names: list[str]) -> list[str]:
    lowered = {c.casefold(): c for c in df.columns}
    return [lowered[name.casefold()] for name in names if name.casefold() in lowered]


def read_csv(path: str | Path) -> pd.DataFrame:
    if not path:
        return pd.DataFrame()
    p = Path(path)
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p, dtype=str).fillna("")


def promote_header_row_if_needed(df: pd.DataFrame, expected_columns: list[str]) -> pd.DataFrame:
    if df.empty:
        return df
    current = {c.casefold() for c in df.columns}
    if any(col.casefold() in current for col in expected_columns):
        return df
    first_row = [clean(v) for v in df.iloc[0].tolist()]
    first = {v.casefold() for v in first_row if v}
    if not any(col.casefold() in first for col in expected_columns):
        return df
    out = df.iloc[1:].copy()
    out.columns = [value if value else f"unnamed_{i}" for i, value in enumerate(first_row)]
    return out.fillna("")


def make_lookup(
    path: str | Path,
    key_columns: list[str],
    qid_columns: list[str],
    label_columns: list[str] | None = None,
    skip_blank_qid: bool = True,
) -> dict[str, dict[str, str]]:
    df = read_csv(path)
    if df.empty:
        return {}
    df = promote_header_row_if_needed(df, key_columns + qid_columns + (label_columns or []))
    key_cols = existing_columns(df, key_columns)
    qid_col = first_existing(df, qid_columns)
    label_col = first_existing(df, label_columns or [])
    if not key_cols or not qid_col:
        return {}
    out: dict[str, dict[str, str]] = {}
    for _, row in df.iterrows():
        qid = qid_from_uri(row.get(qid_col))
        if skip_blank_qid and not qid:
            continue
        if skip_blank_qid and not is_qid(qid):
            continue
        for key_col in key_cols:
            key = norm(row.get(key_col))
            if not key:
                continue
            out.setdefault(
                key,
                {
                    "qid": qid,
                    "label": clean(row.get(label_col)) if label_col else clean(row.get(key_col)),
                    "source_key": clean(row.get(key_col)),
                },
            )
            if key.endswith(" period"):
                out.setdefault(
                    key.removesuffix(" period").strip(),
                    {
                        "qid": qid,
                        "label": clean(row.get(label_col)) if label_col else clean(row.get(key_col)),
                        "source_key": clean(row.get(key_col)),
                    },
                )
    return out


def make_reviewed_alias_lookup(path: str | Path) -> dict[str, dict[str, str]]:
    df = read_csv(path)
    if df.empty:
        return {}
    source_col = first_existing(df, ["source_value", "alias", "provenience", "value_label"])
    qid_col = first_existing(df, ["factgrid_qid", "FG_qid", "FG-Q", "qid"])
    label_col = first_existing(df, ["factgrid_label", "label", "Len"])
    status_col = first_existing(df, ["review_status", "status"])
    if not source_col or not qid_col:
        return {}
    out: dict[str, dict[str, str]] = {}
    for _, row in df.iterrows():
        status = clean(row.get(status_col)).casefold() if status_col else "approved"
        if status not in {"approved", "yes", "y", "ready"}:
            continue
        key = norm(row.get(source_col))
        qid = qid_from_uri(row.get(qid_col))
        if not key or not qid:
            continue
        out[key] = {
            "qid": qid,
            "label": clean(row.get(label_col)) if label_col else clean(row.get(source_col)),
            "source_key": clean(row.get(source_col)),
        }
    return out


def split_values(value: object) -> list[str]:
    return [clean(v) for v in clean(value).split("|") if clean(v)]


def external_ids_from_resources(names: object, urls: object, needle: str) -> list[str]:
    out: list[str] = []
    for name, url in zip(split_values(names), split_values(urls)):
        haystack = f"{name} {url}".casefold()
        if needle.casefold() not in haystack:
            continue
        if needle.casefold() == "oracc":
            match = re.search(r"oracc\\.museum\\.upenn\\.edu/([^\\s?#]+)", url)
            value = match.group(1).strip("/") if match else clean(url)
        elif needle.casefold() == "bdtns":
            match = re.search(r"(?:id_texto=|/)(\\d{2,})", url)
            value = match.group(1) if match else clean(url)
        else:
            value = clean(url)
        if value and value not in out:
            out.append(value)
    return out


def add_statement(
    rows: list[dict[str, str]],
    artifact: pd.Series,
    tw_qid: str,
    field_name: str,
    tw_pid: str,
    datatype: str,
    value: str,
    value_label: str = "",
    source: str = "cdli_json",
    status: str = "ready",
    note: str = "",
    fg_pid: str = "",
) -> None:
    if not clean(value) and not clean(value_label) and not clean(note):
        return
    rows.append(
        {
            "cdli_id": clean(artifact.get("cdli_id")),
            "tw_qid": tw_qid,
            "artifact_label": clean(artifact.get("label")),
            "artifact_type": clean(artifact.get("type")),
            "field_name": field_name,
            "tw_pid": tw_pid,
            "fg_pid": fg_pid,
            "datatype": datatype,
            "value": clean(value),
            "value_label": clean(value_label),
            "plan_status": status,
            "source": source,
            "note": note,
        }
    )


def build_statement_rows(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame]:
    artifacts = read_csv(args.artifacts)
    if artifacts.empty:
        raise RuntimeError(f"No artifact rows found in {args.artifacts}")
    reservations = read_csv(args.reservations)
    fg_cdli = read_csv(args.factgrid_cdli)

    qid_by_cdli: dict[str, str] = {}
    if not reservations.empty and {"incoming_source_id", "reserved_qid"}.issubset(reservations.columns):
        qid_by_cdli.update(
            {
                clean(r["incoming_source_id"]): clean(r["reserved_qid"])
                for _, r in reservations.iterrows()
                if clean(r.get("incoming_source_id")) and clean(r.get("reserved_qid"))
            }
        )

    fg_by_cdli: dict[str, dict[str, str]] = {}
    if not fg_cdli.empty:
        cdli_col = first_existing(fg_cdli, ["CDLI_ID", "cdli_id", "P692"])
        qid_col = first_existing(fg_cdli, ["Clay_tablet", "factgrid_qid", "qid"])
        label_col = first_existing(fg_cdli, ["Clay_tabletLabel", "label", "Len"])
        if cdli_col and qid_col:
            for _, row in fg_cdli.iterrows():
                cdli = clean(row.get(cdli_col))
                if cdli:
                    fg_by_cdli[cdli] = {"qid": qid_from_uri(row.get(qid_col)), "label": clean(row.get(label_col))}

    object_lookup = make_lookup(args.object_lookup, ["object_type", "artifact_type", "type"], ["FG_qid", "qid"], ["FG_Label", "label"])
    period_lookup = make_lookup(args.period_lookup, ["Len", "period", "name"], ["qid", "FG_qid"], ["Len", "period", "name"])
    genre_lookup = make_lookup(args.genre_lookup, ["cdli_genre", "genre"], ["P121", "FG_qid_2", "FG_qid", "qid"], ["cdli_genre", "Label"])
    language_lookup = make_lookup(args.language_lookup, ["Language", "language"], ["FG_item", "FG_qid", "qid"], ["Language"])
    material_lookup = make_lookup(args.material_lookup, ["Material", "material"], ["FactGrid_Q", "Specific_FG-Q", "FG_qid"], ["FactGrid_Label", "Material"])
    provenience_lookup = make_lookup(
        args.provenience_lookup,
        ["provenience", "Len", "Aen", "Aen (update)", "Aen2"],
        ["FG_qid", "FG-Q", "qid"],
        ["Len", "provenience", "Aen", "Aen2"],
    )
    provenience_lookup.update(
        make_lookup(
            args.provenience_fg_lookup,
            ["P694", "CDLI_ID2", "cdli_id2", "Len", "Aen", "cdli_legacy_'Len'", "transciption_name", "transcription_name", "provenience"],
            ["FG_qid", "ancientplace", "FG_Qid", "FG-Q", "qid"],
            ["Len", "Aen", "cdli_legacy_'Len'", "transciption_name", "transcription_name"],
        )
    )
    provenience_lookup.update(make_reviewed_alias_lookup(args.provenience_aliases))
    collection_lookup = make_lookup(
        args.collection_lookup,
        ["Den", "Len", "collection_name Collection", "Aen", "abb", "collection_name_native"],
        ["qid", "factgrid_id"],
        ["Len", "collection_name Collection", "Den"],
    )

    rows: list[dict[str, str]] = []
    considered = artifacts.head(args.limit) if args.limit else artifacts
    for _, artifact in considered.iterrows():
        cdli_id = clean(artifact.get("cdli_id"))
        tw_qid = qid_by_cdli.get(cdli_id, "")
        if not tw_qid:
            tw_qid = clean(artifact.get("tw_qid"))
        if not tw_qid:
            tw_qid = "NEEDS_QID"

        add_statement(rows, artifact, tw_qid, "cdli_id", TW_PROPS["cdli_id"], "external-id", format_cdli_id(cdli_id), fg_pid=FG_PROPS["cdli_id"])

        fg_match = fg_by_cdli.get(f"P{cdli_id}") or fg_by_cdli.get(cdli_id)
        if fg_match:
            add_statement(
                rows,
                artifact,
                tw_qid,
                "factgrid_item_id",
                TW_PROPS["factgrid_item_id"],
                "external-id",
                fg_match["qid"],
                fg_match.get("label", ""),
                source="FG_CDLI_ID.csv",
            )

        type_key = norm(artifact.get("artifact_type") or artifact.get("type"))
        obj = object_lookup.get(type_key)
        if obj:
            add_statement(rows, artifact, tw_qid, "instance_of", TW_PROPS["instance_of"], "wikibase-item", obj["qid"], obj["label"], "CDLI_Object", fg_pid=FG_PROPS["instance_of"])
        else:
            add_statement(rows, artifact, tw_qid, "instance_of", TW_PROPS["instance_of"], "wikibase-item", "", "", "CDLI_Object", "needs_lookup_qid", clean(artifact.get("artifact_type")), FG_PROPS["instance_of"])

        period = period_lookup.get(norm(artifact.get("period")))
        if period:
            add_statement(rows, artifact, tw_qid, "period", TW_PROPS["period"], "wikibase-item", period["qid"], period["label"], "CDLI_Period", fg_pid=FG_PROPS["period"])
        elif clean(artifact.get("period")):
            add_statement(rows, artifact, tw_qid, "period", TW_PROPS["period"], "wikibase-item", "", clean(artifact.get("period")), "CDLI_Period", "needs_lookup_qid", "", FG_PROPS["period"])

        for language in split_values(artifact.get("languages")):
            hit = language_lookup.get(norm(language))
            add_statement(
                rows,
                artifact,
                tw_qid,
                "language",
                TW_PROPS["language"],
                "wikibase-item",
                hit["qid"] if hit else "",
                hit["label"] if hit else language,
                "CDLI_Lang",
                "ready" if hit else "needs_lookup_qid",
                fg_pid=FG_PROPS["language"],
            )

        for genre in split_values(artifact.get("genres")):
            hit = genre_lookup.get(norm(genre))
            add_statement(
                rows,
                artifact,
                tw_qid,
                "type_of_work",
                TW_PROPS["type_of_work"],
                "wikibase-item",
                hit["qid"] if hit else "",
                hit["label"] if hit else genre,
                "CDLI_Genre",
                "ready" if hit else "needs_lookup_qid",
                fg_pid=FG_PROPS["type_of_work"],
            )

        for material in split_values(artifact.get("materials")):
            hit = material_lookup.get(norm(material))
            add_statement(
                rows,
                artifact,
                tw_qid,
                "material",
                TW_PROPS["material"],
                "wikibase-item",
                hit["qid"] if hit else "",
                hit["label"] if hit else material,
                "CDLI_Material",
                "ready" if hit else "needs_lookup_qid",
                "",
                FG_PROPS["material"],
            )

        for collection in split_values(artifact.get("collections")):
            hit = collection_lookup.get(norm(collection))
            add_statement(
                rows,
                artifact,
                tw_qid,
                "present_holding",
                TW_PROPS["present_holding"],
                "wikibase-item",
                hit["qid"] if hit else "",
                hit["label"] if hit else collection,
                "museum_FG",
                "ready" if hit else "needs_lookup_qid",
                fg_pid=FG_PROPS["present_holding"],
            )

        if clean(artifact.get("museum_no")):
            add_statement(rows, artifact, tw_qid, "inventory_number", TW_PROPS["inventory_number"], "string", clean(artifact.get("museum_no")), fg_pid=FG_PROPS["inventory_number"])
        if clean(artifact.get("provenience")):
            hit = provenience_lookup.get(norm(artifact.get("provenience_id"))) or provenience_lookup.get(norm(artifact.get("provenience")))
            add_statement(
                rows,
                artifact,
                tw_qid,
                "finding_spot",
                TW_PROPS["finding_spot"],
                "wikibase-item",
                hit["qid"] if hit else "",
                hit["label"] if hit else clean(artifact.get("provenience")),
                "provenience_lookup",
                "ready" if hit else "needs_lookup_qid",
                fg_pid=FG_PROPS["finding_spot"],
            )
            add_statement(
                rows,
                artifact,
                tw_qid,
                "finding_spot_context",
                TW_PROPS["finding_spot_context"],
                "string",
                clean(artifact.get("provenience")),
                source="cdli_json",
                fg_pid=FG_PROPS["finding_spot_context"],
            )

        for value in external_ids_from_resources(artifact.get("external_resource_names"), artifact.get("external_resource_urls"), "bdtns"):
            add_statement(rows, artifact, tw_qid, "bdtns_id", TW_PROPS["bdtns_id"], "external-id", value, source="cdli_json", fg_pid=FG_PROPS["bdtns_id"])
        for value in external_ids_from_resources(artifact.get("external_resource_names"), artifact.get("external_resource_urls"), "oracc"):
            add_statement(rows, artifact, tw_qid, "oracc_id", TW_PROPS["oracc_id"], "external-id", value, source="cdli_json", fg_pid=FG_PROPS["oracc_id"])

    out = pd.DataFrame(rows)
    summary = (
        out.groupby(["field_name", "plan_status"], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(["field_name", "plan_status"])
        if not out.empty
        else pd.DataFrame(columns=["field_name", "plan_status", "count"])
    )
    return out, summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", default=DEFAULT_ARTIFACTS)
    parser.add_argument("--reservations", default=DEFAULT_RESERVATIONS)
    parser.add_argument("--factgrid-cdli", default="")
    parser.add_argument("--object-lookup", default="")
    parser.add_argument("--period-lookup", default="")
    parser.add_argument("--genre-lookup", default="")
    parser.add_argument("--language-lookup", default="")
    parser.add_argument("--material-lookup", default="")
    parser.add_argument("--provenience-lookup", default="")
    parser.add_argument("--provenience-fg-lookup", default="")
    parser.add_argument("--provenience-aliases", default=WORKFLOW_ROOT / "inputs" / "provenience_aliases_reviewed.csv")
    parser.add_argument("--collection-lookup", default="")
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", default=DEFAULT_SUMMARY)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    out, summary = build_statement_rows(args)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output, index=False)
    summary.to_csv(args.summary, index=False)
    print(summary.to_string(index=False))
    print(f"Wrote statement staging -> {args.output}")
    print(f"Wrote summary -> {args.summary}")


if __name__ == "__main__":
    main()
