#!/usr/bin/env python3
"""Stage FactGrid research-project authority items for TokenWorks."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


WORKFLOW_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IMPORT_STAGING = WORKFLOW_ROOT / "published" / "factgrid_model_samples" / "factgrid_pilot_all_import_staging.csv"
DEFAULT_ORACC_PROJECTS = WORKFLOW_ROOT / "inputs" / "cdli_lookup_sources" / "oracc_project_list.csv"
DEFAULT_OUTPUT = WORKFLOW_ROOT / "published" / "factgrid_model_samples" / "cdli_research_project_authority_staging.csv"
DEFAULT_SUMMARY = WORKFLOW_ROOT / "published" / "factgrid_model_samples" / "cdli_research_project_authority_staging_summary.csv"

TOKENWORKS_FACTGRID_QID = "Q1894741"
LABEL_OVERRIDES = {
    "Q1190559": {
        "label_en": "Glottolog",
        "description_en": "global catalog of languages, language families and dialects",
        "aliases_en": "Global catalog of the world's languages, language families and dialects | Glottolog language catalog",
    },
}


def clean(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null"}:
        return ""
    return text


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise RuntimeError(f"Missing CSV: {path}")
    return pd.read_csv(path, dtype=str, low_memory=False).fillna("")


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


def combine_aliases(values: list[object]) -> str:
    seen = set()
    out = []
    for value in values:
        for part in clean(value).split("|"):
            alias = clean(part)
            if alias and alias not in seen:
                out.append(alias)
                seen.add(alias)
    return " | ".join(out)


def merge_rows(rows: list[dict[str, object]]) -> pd.DataFrame:
    grouped: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        qid = clean(row.get("factgrid_qid"))
        if qid:
            grouped.setdefault(qid, []).append(row)

    out = []
    for qid, group in grouped.items():
        labels = [clean(row.get("label_en")) for row in group if clean(row.get("label_en")) and clean(row.get("label_en")) != qid]
        descriptions = [clean(row.get("description_en")) for row in group if clean(row.get("description_en"))]
        source_fields = combine_aliases([row.get("source_fields") for row in group])
        source_count = sum(int(clean(row.get("source_count")) or 0) for row in group)
        source_cdli_count = sum(int(clean(row.get("source_cdli_count")) or 0) for row in group)
        out.append(
            {
                "factgrid_qid": qid,
                "label_en": (labels[0] if labels else qid)[:250],
                "description_en": (descriptions[0] if descriptions else "research project that contributed to the artifact data set")[:250],
                "aliases_en": combine_aliases([row.get("aliases_en") for row in group]),
                "source_fields": source_fields,
                "source_count": source_count,
                "source_cdli_count": source_cdli_count,
            }
        )
    return pd.DataFrame(out)


def oracc_rows(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    raw = pd.read_csv(path, dtype=str, header=None, low_memory=False).fillna("")
    if len(raw) < 3:
        return []
    headers = [clean(value) for value in raw.iloc[0].tolist()]
    data = raw.iloc[2:].copy()
    data.columns = headers[: len(data.columns)]

    rows = []
    for _, row in data.iterrows():
        qid = factgrid_qid(row.get("FactGrid_ID"))
        label = clean(row.get("Label"))
        if not qid or not label:
            continue
        rows.append(
            {
                "factgrid_qid": qid,
                "label_en": label,
                "description_en": clean(row.get("Description")) or "ORACC research project",
                "aliases_en": clean(row.get("Alias")),
                "source_fields": "oracc_project",
                "source_count": 1,
                "source_cdli_count": 0,
            }
        )
    return rows


def prepare(args: argparse.Namespace) -> None:
    staging = load_csv(args.import_staging)
    projects = staging[
        staging["factgrid_property_id"].eq("P131")
        & staging["factgrid_value"].map(clean).str.startswith("Q", na=False)
    ].copy()

    rows = []
    for factgrid_qid, group in projects.groupby("factgrid_value", dropna=False):
        label = clean(group["factgrid_value_label"].iloc[0])
        if not label:
            label = factgrid_qid
        rows.append(
            {
                "factgrid_qid": clean(factgrid_qid),
                "label_en": label[:250],
                "description_en": "research project that contributed to the artifact data set",
                "aliases_en": "",
                "source_fields": "research_project",
                "source_count": len(group),
                "source_cdli_count": group["factgrid_item_id"].map(clean).nunique(),
            }
        )

    rows.extend(oracc_rows(args.oracc_projects))

    rows.append(
        {
            "factgrid_qid": TOKENWORKS_FACTGRID_QID,
            "label_en": "TokenWorks",
            "description_en": "research project contributing data to the TokenWorks Wikibase",
            "aliases_en": "TokenWorks Wikibase | TokenWorks LLC",
            "source_fields": "research_project",
            "source_count": 0,
            "source_cdli_count": 0,
        }
    )

    out = merge_rows(rows)
    for idx, row in out.iterrows():
        override = LABEL_OVERRIDES.get(clean(row.get("factgrid_qid")))
        if not override:
            continue
        for col, value in override.items():
            out.at[idx, col] = value
    out = out.sort_values(["source_count", "label_en"], ascending=[False, True])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output, index=False)

    summary = pd.DataFrame(
        [
            {"metric": "research_project_rows", "value": len(out)},
            {"metric": "factgrid_p131_project_rows", "value": len(projects)},
            {"metric": "factgrid_p131_project_qids", "value": projects["factgrid_value"].map(clean).nunique()},
            {"metric": "oracc_project_rows", "value": len(oracc_rows(args.oracc_projects))},
            {"metric": "includes_tokenworks_factgrid_qid", "value": int(TOKENWORKS_FACTGRID_QID in set(out["factgrid_qid"]))},
        ]
    )
    summary.to_csv(args.summary, index=False)
    print(out.head(args.preview).to_string(index=False))
    print(summary.to_string(index=False))
    print(f"Wrote research project authority staging -> {args.output}")
    print(f"Wrote summary -> {args.summary}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--import-staging", type=Path, default=DEFAULT_IMPORT_STAGING)
    parser.add_argument("--oracc-projects", type=Path, default=DEFAULT_ORACC_PROJECTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--preview", type=int, default=30)
    args = parser.parse_args()
    prepare(args)


if __name__ == "__main__":
    main()
