#!/usr/bin/env python3
"""Export recent FactGrid provenience items from a user's contributions.

This is a read-only helper for cases where provenience/finding-spot items were
created manually in FactGrid and need to be folded back into the local CDLI
lookup files. It uses the MediaWiki API contributions list to collect recent
item QIDs, fetches their labels/aliases/claims, and keeps likely provenience
items: rows with FactGrid `P2 = Q389596` and/or a `P694` CDLI provenience ID.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

import pandas as pd
import requests


WORKFLOW_ROOT = Path(__file__).resolve().parents[1]
INPUT_ROOT = WORKFLOW_ROOT / "inputs" / "cdli_lookup_sources"
OUTPUT_ROOT = WORKFLOW_ROOT / "published" / "factgrid_model_samples"
DEFAULT_EXISTING = INPUT_ROOT / "proveniences_FG_Proveniences.csv"
DEFAULT_REVIEW_OUTPUT = OUTPUT_ROOT / "recent_factgrid_provenience_contributions.csv"
DEFAULT_LOOKUP_OUTPUT = INPUT_ROOT / "proveniences_FG_recent_contributions.csv"
DEFAULT_MERGED_OUTPUT = INPUT_ROOT / "proveniences_FG_all_with_recent.csv"
DEFAULT_SUMMARY = OUTPUT_ROOT / "recent_factgrid_provenience_contributions_summary.csv"
FACTGRID_API = "https://database.factgrid.de/w/api.php"
PROVENIENCE_INSTANCE_QID = "Q389596"
BROWSERISH_HEADERS = {
    "User-Agent": "TokenWorks-FactGrid-provenience-contribution-export/0.1",
    "Accept": "application/json, */*",
}


def clean(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null"}:
        return ""
    return text


def qid_from_title(value: object) -> str:
    match = re.search(r"(Q\d+)", clean(value))
    return match.group(1) if match else ""


def unique(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = clean(value)
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def api_get(params: dict, api_url: str, timeout: int) -> dict:
    response = requests.get(api_url, params=params | {"format": "json"}, headers=BROWSERISH_HEADERS, timeout=timeout)
    response.raise_for_status()
    try:
        return response.json()
    except requests.exceptions.JSONDecodeError as exc:
        snippet = response.text[:500].replace("\n", " ")
        raise RuntimeError(
            f"Expected JSON from FactGrid API but received {response.headers.get('content-type', '')}; "
            f"status={response.status_code}; first 500 chars: {snippet}"
        ) from exc


def fetch_contribution_qids(args: argparse.Namespace) -> tuple[list[str], dict[str, dict[str, str]]]:
    qids: list[str] = []
    meta: dict[str, dict[str, str]] = {}
    cont: dict[str, str] = {}
    while len(qids) < args.limit:
        params = {
            "action": "query",
            "list": "usercontribs",
            "ucuser": args.user,
            "ucnamespace": "120",
            "uclimit": str(min(500, args.limit - len(qids))),
            "ucprop": "title|timestamp|comment|ids|flags",
        }
        if args.start:
            params["ucstart"] = args.start
        if args.end:
            params["ucend"] = args.end
        params.update(cont)
        data = api_get(params, args.api_url, args.timeout)
        contribs = data.get("query", {}).get("usercontribs", [])
        if not contribs:
            break
        for contrib in contribs:
            qid = qid_from_title(contrib.get("title"))
            if not qid:
                continue
            if qid not in meta:
                qids.append(qid)
                meta[qid] = {
                    "last_contribution_timestamp": clean(contrib.get("timestamp")),
                    "last_contribution_comment": clean(contrib.get("comment")),
                }
        if len(qids) >= args.limit or "continue" not in data:
            break
        cont = {k: v for k, v in data.get("continue", {}).items() if k != "continue"}
        time.sleep(args.sleep)
    return qids, meta


def parse_datavalue(snak: dict) -> str:
    datavalue = snak.get("datavalue") or {}
    value = datavalue.get("value")
    if isinstance(value, dict):
        if "id" in value:
            return clean(value.get("id"))
        if "numeric-id" in value:
            return f"Q{clean(value.get('numeric-id'))}"
        if "latitude" in value and "longitude" in value:
            return f"Point({clean(value.get('longitude'))} {clean(value.get('latitude'))})"
        if "text" in value:
            return clean(value.get("text"))
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return clean(value)


def claim_values(entity: dict, prop: str) -> list[str]:
    return unique([parse_datavalue(claim.get("mainsnak") or {}) for claim in entity.get("claims", {}).get(prop, [])])


def fetch_entities(qids: list[str], args: argparse.Namespace) -> dict[str, dict]:
    entities: dict[str, dict] = {}
    for start in range(0, len(qids), 50):
        chunk = qids[start : start + 50]
        data = api_get(
            {
                "action": "wbgetentities",
                "ids": "|".join(chunk),
                "props": "labels|aliases|descriptions|claims",
                "languages": "en",
            },
            args.api_url,
            args.timeout,
        )
        entities.update(data.get("entities", {}))
        time.sleep(args.sleep)
    return entities


def aliases_for(entity: dict) -> str:
    return " | ".join(unique([clean(alias.get("value")) for alias in entity.get("aliases", {}).get("en", [])]))


def build_rows(qids: list[str], meta: dict[str, dict[str, str]], entities: dict[str, dict]) -> pd.DataFrame:
    rows: list[dict[str, str]] = []
    for qid in qids:
        entity = entities.get(qid, {})
        p2_qids = claim_values(entity, "P2")
        p694_values = claim_values(entity, "P694")
        if PROVENIENCE_INSTANCE_QID not in p2_qids and not p694_values:
            continue
        label = clean(entity.get("labels", {}).get("en", {}).get("value"))
        aliases = aliases_for(entity)
        rows.append(
            {
                "FG_qid": qid,
                "FG_qid_url": f"https://database.factgrid.de/entity/{qid}",
                "Len": label,
                "Aen": aliases,
                "P694": " | ".join(p694_values),
                "P48": " | ".join(claim_values(entity, "P48")),
                "P2": " | ".join(p2_qids),
                "description_en": clean(entity.get("descriptions", {}).get("en", {}).get("value")),
                "last_contribution_timestamp": meta.get(qid, {}).get("last_contribution_timestamp", ""),
                "last_contribution_comment": meta.get(qid, {}).get("last_contribution_comment", ""),
            }
        )
    columns = [
        "FG_qid",
        "FG_qid_url",
        "Len",
        "Aen",
        "P694",
        "P48",
        "P2",
        "description_en",
        "last_contribution_timestamp",
        "last_contribution_comment",
    ]
    if not rows:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(rows, columns=columns).sort_values(["FG_qid"]).reset_index(drop=True)


def read_existing(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, low_memory=False).fillna("")


def lookup_rows(review: pd.DataFrame) -> pd.DataFrame:
    if review.empty:
        return pd.DataFrame(columns=["FG_qid", "Len", "Aen", "P694", "P48"])
    return review[["FG_qid", "Len", "Aen", "P694", "P48"]].copy()


def merged_lookup(existing_path: Path, recent_lookup: pd.DataFrame) -> pd.DataFrame:
    existing = read_existing(existing_path)
    if existing.empty:
        return recent_lookup
    frames = [existing, recent_lookup]
    out = pd.concat(frames, ignore_index=True).fillna("")
    if "FG_qid" in out.columns:
        out["_qid_key"] = out["FG_qid"].map(lambda value: qid_from_title(value) or clean(value))
        out = out.drop_duplicates("_qid_key", keep="last").drop(columns=["_qid_key"])
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user", default="Adam Anderson")
    parser.add_argument("--api-url", default=FACTGRID_API)
    parser.add_argument("--limit", type=int, default=5000)
    parser.add_argument("--start", default="", help="Optional ucstart timestamp, e.g. 2026-09-09T23:59:59Z")
    parser.add_argument("--end", default="", help="Optional ucend timestamp, e.g. 2026-09-08T00:00:00Z")
    parser.add_argument("--sleep", type=float, default=0.2)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--existing", type=Path, default=DEFAULT_EXISTING)
    parser.add_argument("--review-output", type=Path, default=DEFAULT_REVIEW_OUTPUT)
    parser.add_argument("--lookup-output", type=Path, default=DEFAULT_LOOKUP_OUTPUT)
    parser.add_argument("--merged-output", type=Path, default=DEFAULT_MERGED_OUTPUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--preview", type=int, default=20)
    args = parser.parse_args()

    qids, meta = fetch_contribution_qids(args)
    entities = fetch_entities(qids, args)
    review = build_rows(qids, meta, entities)
    lookup = lookup_rows(review)
    merged = merged_lookup(args.existing, lookup)

    for path in [args.review_output, args.lookup_output, args.merged_output, args.summary]:
        path.parent.mkdir(parents=True, exist_ok=True)
    review.to_csv(args.review_output, index=False)
    lookup.to_csv(args.lookup_output, index=False)
    merged.to_csv(args.merged_output, index=False)
    summary = pd.DataFrame(
        [
            {"metric": "contribution_qids_seen", "value": len(qids)},
            {"metric": "likely_provenience_items", "value": len(review)},
            {"metric": "lookup_rows", "value": len(lookup)},
            {"metric": "merged_lookup_rows", "value": len(merged)},
        ]
    )
    summary.to_csv(args.summary, index=False)
    print(summary.to_string(index=False))
    if args.preview and not review.empty:
        print(review.head(args.preview).to_string(index=False))
    print(f"Wrote review -> {args.review_output}")
    print(f"Wrote recent lookup -> {args.lookup_output}")
    print(f"Wrote merged lookup -> {args.merged_output}")
    print(f"Wrote summary -> {args.summary}")


if __name__ == "__main__":
    main()
