#!/usr/bin/env python3
"""Fetch live FactGrid CDLI provenience/locality lookup rows from P694.

FactGrid `P694` is the CDLI ID2 / provenience identifier property. This helper
uses a light SPARQL query to list all items with `P694`, then enriches those
QIDs through the MediaWiki API for labels, aliases, coordinates, and instance
claims. The resulting CSV can be passed as `--provenience-fg-lookup` when
building CDLI artifact statement staging.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from textwrap import dedent

import pandas as pd
import requests


WORKFLOW_ROOT = Path(__file__).resolve().parents[1]
INPUT_ROOT = WORKFLOW_ROOT / "inputs" / "cdli_lookup_sources"
OUTPUT_ROOT = WORKFLOW_ROOT / "published" / "factgrid_model_samples"
DEFAULT_EXISTING = INPUT_ROOT / "proveniences_FG_Proveniences.csv"
DEFAULT_OUTPUT = INPUT_ROOT / "proveniences_FG_P694_live.csv"
DEFAULT_MERGED_OUTPUT = INPUT_ROOT / "proveniences_FG_all_with_p694_live.csv"
DEFAULT_SUMMARY = OUTPUT_ROOT / "factgrid_p694_provenience_lookup_summary.csv"
DEFAULT_QUERY_OUTPUT = OUTPUT_ROOT / "factgrid_p694_provenience_lookup.rq"
FACTGRID_SPARQL = "https://database.factgrid.de/sparql"
FACTGRID_API = "https://database.factgrid.de/w/api.php"
BROWSERISH_HEADERS = {
    "User-Agent": "TokenWorks-FactGrid-P694-provenience-lookup/0.1",
    "Accept": "application/sparql-results+json, application/json, */*",
}


def clean(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null"}:
        return ""
    return text


def qid_from_uri(value: object) -> str:
    match = re.search(r"(Q\d+)(?:$|[/?#])", clean(value))
    return match.group(1) if match else clean(value)


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


def build_query(limit: int, offset: int) -> str:
    return dedent(
        f"""
        PREFIX fgt: <https://database.factgrid.de/prop/direct/>

        SELECT ?item ?cdliId WHERE {{
          ?item fgt:P694 ?cdliId .
        }}
        ORDER BY ?cdliId ?item
        LIMIT {limit}
        OFFSET {offset}
        """
    ).strip()


def response_json(response: requests.Response) -> dict:
    try:
        return response.json()
    except requests.exceptions.JSONDecodeError as exc:
        snippet = response.text[:500].replace("\n", " ")
        raise RuntimeError(
            f"Expected JSON from {response.url} but received {response.headers.get('content-type', '')}; "
            f"status={response.status_code}; first 500 chars: {snippet}"
        ) from exc


def fetch_sparql_rows(query: str, endpoint: str, timeout: int) -> list[dict[str, str]]:
    response = requests.post(
        endpoint,
        data={"query": query, "format": "json"},
        headers=BROWSERISH_HEADERS,
        timeout=timeout,
    )
    response.raise_for_status()
    data = response_json(response)
    rows: list[dict[str, str]] = []
    for binding in data.get("results", {}).get("bindings", []):
        item = clean(binding.get("item", {}).get("value"))
        rows.append(
            {
                "FG_qid": qid_from_uri(item),
                "FG_qid_url": item,
                "P694": clean(binding.get("cdliId", {}).get("value")),
            }
        )
    return rows


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


def fetch_entities(qids: list[str], api_url: str, timeout: int, sleep: float) -> dict[str, dict]:
    entities: dict[str, dict] = {}
    for start in range(0, len(qids), 50):
        chunk = qids[start : start + 50]
        response = requests.post(
            api_url,
            data={
                "action": "wbgetentities",
                "ids": "|".join(chunk),
                "props": "labels|aliases|descriptions|claims",
                "languages": "en",
                "format": "json",
            },
            headers=BROWSERISH_HEADERS,
            timeout=timeout,
        )
        response.raise_for_status()
        entities.update(response_json(response).get("entities", {}))
        time.sleep(sleep)
    return entities


def alias_text(entity: dict) -> str:
    return " | ".join(unique([clean(alias.get("value")) for alias in entity.get("aliases", {}).get("en", [])]))


def enrich(rows: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    if rows.empty:
        return pd.DataFrame(columns=["FG_qid", "FG_qid_url", "Len", "Aen", "P694", "P48", "P2", "description_en"])
    qids = unique(rows["FG_qid"].tolist())
    entities = fetch_entities(qids, args.api_url, args.timeout, args.sleep)
    enriched: list[dict[str, str]] = []
    for _, row in rows.iterrows():
        qid = clean(row.get("FG_qid"))
        entity = entities.get(qid, {})
        p694_values = claim_values(entity, "P694") or [clean(row.get("P694"))]
        enriched.append(
            {
                "FG_qid": qid,
                "FG_qid_url": clean(row.get("FG_qid_url")) or f"https://database.factgrid.de/entity/{qid}",
                "Len": clean(entity.get("labels", {}).get("en", {}).get("value")),
                "Aen": alias_text(entity),
                "P694": " | ".join(p694_values),
                "P48": " | ".join(claim_values(entity, "P48")),
                "P2": " | ".join(claim_values(entity, "P2")),
                "description_en": clean(entity.get("descriptions", {}).get("en", {}).get("value")),
            }
        )
    return pd.DataFrame(enriched).drop_duplicates(["FG_qid", "P694"], keep="last")


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, low_memory=False).fillna("")


def merge_existing(existing_path: Path, live: pd.DataFrame) -> pd.DataFrame:
    existing = read_csv(existing_path)
    if existing.empty:
        return live
    out = pd.concat([existing, live], ignore_index=True).fillna("")
    if "FG_qid" in out.columns:
        out["_qid_key"] = out["FG_qid"].map(lambda value: qid_from_uri(value) or clean(value))
        out = out.drop_duplicates("_qid_key", keep="last").drop(columns=["_qid_key"])
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default=FACTGRID_SPARQL)
    parser.add_argument("--api-url", default=FACTGRID_API)
    parser.add_argument("--existing", type=Path, default=DEFAULT_EXISTING)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--merged-output", type=Path, default=DEFAULT_MERGED_OUTPUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--query-output", type=Path, default=DEFAULT_QUERY_OUTPUT)
    parser.add_argument("--chunk-size", type=int, default=1000)
    parser.add_argument("--max-rows", type=int, default=0)
    parser.add_argument("--sleep", type=float, default=0.2)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--preview", type=int, default=20)
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.query_output.parent.mkdir(parents=True, exist_ok=True)
    args.query_output.write_text(build_query(args.chunk_size, 0), encoding="utf-8")

    frames = []
    offset = 0
    if args.resume:
        existing_live = read_csv(args.output)
        if not existing_live.empty:
            frames.append(existing_live)
            offset = len(existing_live)

    total_new = 0
    while True:
        if args.max_rows and total_new >= args.max_rows:
            break
        limit = args.chunk_size if not args.max_rows else min(args.chunk_size, args.max_rows - total_new)
        query = build_query(limit, offset)
        print(f"Fetching FactGrid P694 rows offset={offset} limit={limit}", flush=True)
        last_error: Exception | None = None
        rows: list[dict[str, str]] = []
        for attempt in range(1, args.retries + 1):
            try:
                rows = fetch_sparql_rows(query, args.endpoint, args.timeout)
                last_error = None
                break
            except Exception as exc:
                last_error = exc
                print(f"  attempt {attempt}/{args.retries} failed: {type(exc).__name__}: {exc}", flush=True)
                time.sleep(args.sleep * attempt)
        if last_error is not None:
            raise last_error
        if not rows:
            break
        live_chunk = enrich(pd.DataFrame(rows), args)
        frames.append(live_chunk)
        total_new += len(rows)
        offset += len(rows)
        live = pd.concat(frames, ignore_index=True).drop_duplicates(["FG_qid", "P694"], keep="last")
        live.to_csv(args.output, index=False)
        merge_existing(args.existing, live).to_csv(args.merged_output, index=False)
        print(f"  saved {len(live)} live rows", flush=True)
        if len(rows) < limit:
            break
        time.sleep(args.sleep)

    live = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if not live.empty:
        live = live.drop_duplicates(["FG_qid", "P694"], keep="last")
    merged = merge_existing(args.existing, live)
    live.to_csv(args.output, index=False)
    merged.to_csv(args.merged_output, index=False)
    summary = pd.DataFrame(
        [
            {"metric": "live_p694_rows", "value": len(live)},
            {"metric": "live_unique_qids", "value": live["FG_qid"].nunique() if not live.empty else 0},
            {"metric": "merged_lookup_rows", "value": len(merged)},
        ]
    )
    summary.to_csv(args.summary, index=False)
    print(summary.to_string(index=False))
    if args.preview and not live.empty:
        print(live.head(args.preview).to_string(index=False))
    print(f"Wrote live P694 lookup -> {args.output}")
    print(f"Wrote merged lookup -> {args.merged_output}")
    print(f"Wrote summary -> {args.summary}")


if __name__ == "__main__":
    main()
