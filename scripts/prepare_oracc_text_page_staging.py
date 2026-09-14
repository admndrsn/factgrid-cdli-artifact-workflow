#!/usr/bin/env python3
"""Prepare ORACC text wiki-page staging from word-level ORACC CSV data.

``finaldf.csv`` is word-level text data keyed by ``id_text``. This script
streams it text-by-text, assembles a simple MediaWiki transcript page, and
stages a future ``P196`` URL claim for matching TokenWorks artifact Q-items.
"""

from __future__ import annotations

import argparse
import csv
import glob
import re
from collections import defaultdict
from pathlib import Path

import pandas as pd


WORKFLOW_ROOT = Path(__file__).resolve().parents[1]
PILOT_ROOT = WORKFLOW_ROOT / "published" / "pilots"
DEFAULT_FINALDF = Path("/Users/aa/Documents/FactGrid/FactgridCuneiform/Datasets/ORACC/finaldf.csv")
DEFAULT_FACTGRID_DF = Path("/Users/aa/Documents/FactGrid/FactgridCuneiform/Datasets/ORACC/factgrid_df.csv")
DEFAULT_OUTPUT = WORKFLOW_ROOT / "published" / "oracc_text_pages" / "oracc_text_page_staging.csv"
DEFAULT_SUMMARY = WORKFLOW_ROOT / "published" / "oracc_text_pages" / "oracc_text_page_staging_summary.csv"
DEFAULT_PAGES_DIR = WORKFLOW_ROOT / "published" / "oracc_text_pages" / "wikitext"
DEFAULT_TW_BASE_URL = "https://wikibase.tk-wiki-kg.com/wiki"


def clean(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null"}:
        return ""
    if text.endswith(".0") and text[:-2].isdigit():
        return text[:-2]
    return text


def format_cdli_id(value: object) -> str:
    text = clean(value)
    match = re.search(r"(\d+)", text)
    if not match:
        return text
    return f"P{int(match.group(1)):06d}"


def qid_number(qid: str) -> str:
    return clean(qid).lstrip("Q")


def page_title_for(qid: str) -> str:
    return f"D-Q{qid_number(qid)}"


def load_artifact_qid_map(patterns: list[str]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for pattern in patterns:
        for filename in glob.glob(pattern):
            path = Path(filename)
            if not path.exists():
                continue
            df = pd.read_csv(path, dtype=str, low_memory=False).fillna("")
            if not {"cdli_id", "tw_qid"}.issubset(df.columns):
                continue
            status_col = "write_status" if "write_status" in df.columns else ""
            for _, row in df.iterrows():
                if status_col and clean(row.get(status_col)) not in {"written", ""}:
                    continue
                cdli_id = format_cdli_id(row.get("cdli_id"))
                tw_qid = clean(row.get("tw_qid"))
                if not cdli_id or not tw_qid:
                    continue
                out[cdli_id] = {
                    "tw_qid": tw_qid,
                    "artifact_label": clean(row.get("artifact_label")),
                    "source_results_file": str(path),
                }
    return out


def load_catalog(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    usecols = ["P692", "Len", "Den", "P18", "P121_y", "P853"]
    df = pd.read_csv(path, dtype=str, low_memory=False, usecols=lambda col: col in usecols).fillna("")
    out = {}
    for _, row in df.iterrows():
        cdli_id = format_cdli_id(row.get("P692"))
        if not cdli_id:
            continue
        out[cdli_id] = {
            "catalog_label": clean(row.get("Len")),
            "catalog_description": clean(row.get("Den")),
            "language_factgrid_qid": clean(row.get("P18")),
            "genre_factgrid_qid": clean(row.get("P121_y")),
            "period_factgrid_qid": clean(row.get("P853")),
        }
    return out


def token_from_row(row: dict[str, str]) -> str:
    for col in ["form", "norm", "cf", "gw", "base"]:
        value = clean(row.get(col))
        if value:
            return value
    return ""


def nowiki(text: str) -> str:
    return clean(text).replace("</nowiki>", "&lt;/nowiki&gt;")


def append_text_row(lines: dict[str, list[str]], row: dict[str, str]) -> None:
    label = clean(row.get("label")) or "unlabeled"
    token = token_from_row(row)
    if token:
        lines[label].append(token)


def page_body_for_text(cdli_id: str, qid: str, catalog: dict[str, str], lines: dict[str, list[str]]) -> str:
    title = catalog.get("catalog_label") or f"ORACC text {cdli_id}"
    parts = [
        f"= {title} =",
        "",
        f"* TokenWorks item: [[Item:{qid}|{qid}]]",
        f"* CDLI ID: {cdli_id}",
        "* Source: ORACC word-level export",
    ]
    if catalog.get("catalog_description"):
        parts.extend(["", "== Catalog Description ==", "", catalog["catalog_description"]])
    parts.extend(["", "== Transliteration ==", ""])
    for label, tokens in lines.items():
        if not tokens:
            continue
        parts.append(f"; <nowiki>{nowiki(label)}</nowiki>")
        parts.append(f"<nowiki>{nowiki(' '.join(tokens))}</nowiki>")
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def flush_text(
    text_id: str,
    lines: dict[str, list[str]],
    qid_map: dict[str, dict[str, str]],
    catalog: dict[str, dict[str, str]],
    pages_dir: Path,
    tw_base_url: str,
) -> dict[str, str] | None:
    cdli_id = format_cdli_id(text_id)
    artifact = qid_map.get(cdli_id)
    if not artifact:
        return None
    tw_qid = artifact["tw_qid"]
    title = page_title_for(tw_qid)
    page_url = f"{tw_base_url.rstrip('/')}/{title}"
    page_path = pages_dir / f"{title}.wiki"
    cat = catalog.get(cdli_id, {})
    page_body = page_body_for_text(cdli_id, tw_qid, cat, lines)
    page_path.write_text(page_body, encoding="utf-8")
    token_count = sum(len(tokens) for tokens in lines.values())
    line_count = sum(1 for tokens in lines.values() if tokens)
    return {
        "cdli_id": cdli_id,
        "tw_qid": tw_qid,
        "artifact_label": artifact.get("artifact_label", ""),
        "page_title": title,
        "page_url": page_url,
        "page_path": str(page_path),
        "p196_property": "P196",
        "token_count": str(token_count),
        "line_count": str(line_count),
        "catalog_label": cat.get("catalog_label", ""),
        "source_results_file": artifact.get("source_results_file", ""),
        "write_status": "not_started",
        "write_error": "",
    }


def prepare(args: argparse.Namespace) -> None:
    qid_map = load_artifact_qid_map(args.artifact_results_glob)
    if not qid_map:
        raise RuntimeError("No TokenWorks artifact QID map loaded from --artifact-results-glob")
    catalog = load_catalog(args.factgrid_df)
    args.pages_dir.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    staged = []
    current_text = ""
    lines: dict[str, list[str]] = defaultdict(list)
    seen_texts = 0
    matched_texts = 0

    with args.finaldf.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            text_id = clean(row.get("id_text"))
            if not text_id:
                continue
            if current_text and text_id != current_text:
                seen_texts += 1
                result = flush_text(current_text, lines, qid_map, catalog, args.pages_dir, args.tw_base_url)
                if result:
                    staged.append(result)
                    matched_texts += 1
                    if args.limit_texts and matched_texts >= args.limit_texts:
                        break
                if args.max_texts_scanned and seen_texts >= args.max_texts_scanned:
                    break
                lines = defaultdict(list)
            current_text = text_id
            append_text_row(lines, row)
        else:
            if current_text:
                seen_texts += 1
                result = flush_text(current_text, lines, qid_map, catalog, args.pages_dir, args.tw_base_url)
                if result:
                    staged.append(result)
                    matched_texts += 1

    out = pd.DataFrame(staged)
    out.to_csv(args.output, index=False)
    summary = pd.DataFrame(
        [
            {"metric": "artifact_qids_loaded", "value": len(qid_map)},
            {"metric": "catalog_rows_loaded", "value": len(catalog)},
            {"metric": "oracc_texts_seen", "value": seen_texts},
            {"metric": "oracc_text_pages_staged", "value": len(out)},
            {"metric": "page_text_dir", "value": str(args.pages_dir)},
        ]
    )
    summary.to_csv(args.summary, index=False)
    print(summary.to_string(index=False))
    if len(out):
        print(out.head(args.preview).to_string(index=False))
    print(f"Wrote ORACC text page staging -> {args.output}")
    print(f"Wrote summary -> {args.summary}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--finaldf", type=Path, default=DEFAULT_FINALDF)
    parser.add_argument("--factgrid-df", type=Path, default=DEFAULT_FACTGRID_DF)
    parser.add_argument(
        "--artifact-results-glob",
        action="append",
        default=[
            str(PILOT_ROOT / "cdli_artifact_write*_results*.csv"),
            str(PILOT_ROOT / "cdli_artifact_new_item_results*.csv"),
        ],
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--pages-dir", type=Path, default=DEFAULT_PAGES_DIR)
    parser.add_argument("--tw-base-url", default=DEFAULT_TW_BASE_URL)
    parser.add_argument("--limit-texts", type=int, default=20)
    parser.add_argument(
        "--max-texts-scanned",
        type=int,
        default=0,
        help="Optional safety cap on distinct ORACC id_text values scanned; 0 means no cap.",
    )
    parser.add_argument("--preview", type=int, default=10)
    args = parser.parse_args()
    prepare(args)


if __name__ == "__main__":
    main()
