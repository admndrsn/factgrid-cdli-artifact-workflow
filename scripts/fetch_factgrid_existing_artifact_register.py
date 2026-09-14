#!/usr/bin/env python3
"""Fetch a live FactGrid register of existing CDLI artifact items.

The main use case is duplicate prevention before adding more CDLI artifacts to
FactGrid. It uses a deliberately light two-stage fetch: SPARQL lists item IDs
for one or more `Instance of` QIDs, then the MediaWiki API enriches those QIDs
with labels, aliases, CDLI IDs, direct inventory numbers, and present-holding
inventory-number qualifiers.
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
OUTPUT_ROOT = WORKFLOW_ROOT / "published" / "factgrid_existing"
DEFAULT_OUTPUT = OUTPUT_ROOT / "factgrid_existing_clay_tablet_register.csv"
DEFAULT_SUMMARY = OUTPUT_ROOT / "factgrid_existing_clay_tablet_register_summary.csv"
DEFAULT_QUERY_OUTPUT = OUTPUT_ROOT / "factgrid_existing_clay_tablet_register.rq"
FACTGRID_SPARQL = "https://database.factgrid.de/sparql"
FACTGRID_API = "https://database.factgrid.de/w/api.php"
BROWSERISH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36 TokenWorks-FactGrid-existing-artifacts/0.1"
    ),
    "Accept": "application/sparql-results+json, application/json, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


def clean(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null"}:
        return ""
    return text


def qid_from_uri(value: object) -> str:
    match = re.search(r"(Q\d+)$", clean(value))
    return match.group(1) if match else clean(value)


def parse_qids(value: str) -> list[str]:
    out: list[str] = []
    for part in re.split(r"[,;\s]+", clean(value)):
        qid = qid_from_uri(part)
        if re.fullmatch(r"Q\d+", qid) and qid not in out:
            out.append(qid)
    return out


def build_query(instance_qids: list[str], limit: int, offset: int) -> str:
    values = " ".join(f"fg:{qid}" for qid in instance_qids)
    return dedent(
        f"""
        PREFIX fg: <https://database.factgrid.de/entity/>
        PREFIX fgt: <https://database.factgrid.de/prop/direct/>

        SELECT ?item ?instanceOf WHERE {{
          VALUES ?instanceOf {{ {values} }}
          ?item fgt:P2 ?instanceOf .
        }}
        ORDER BY ?item
        LIMIT {limit}
        OFFSET {offset}
        """
    ).strip()


def parse_datavalue(snak: dict) -> str:
    datavalue = snak.get("datavalue") or {}
    value = datavalue.get("value")
    if isinstance(value, dict):
        if "id" in value:
            return clean(value.get("id"))
        if "numeric-id" in value:
            return f"Q{clean(value.get('numeric-id'))}"
        if "text" in value:
            return clean(value.get("text"))
        if "amount" in value:
            return clean(value.get("amount")).lstrip("+")
        if "time" in value:
            return clean(value.get("time"))
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return clean(value)


def claim_values(entity: dict, prop: str) -> list[str]:
    out: list[str] = []
    for claim in entity.get("claims", {}).get(prop, []):
        value = parse_datavalue(claim.get("mainsnak") or {})
        if value and value not in out:
            out.append(value)
    return out


def present_holding_records(entity: dict) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for claim in entity.get("claims", {}).get("P329", []):
        holding = parse_datavalue(claim.get("mainsnak") or {})
        qualifiers = claim.get("qualifiers") or {}
        inventory_values = []
        for qualifier in qualifiers.get("P10", []):
            value = parse_datavalue(qualifier)
            if value and value not in inventory_values:
                inventory_values.append(value)
        if not inventory_values:
            inventory_values = [""]
        for inventory in inventory_values:
            records.append({"present_holding_qid": holding, "holdingInventoryNumber": inventory})
    return records or [{"present_holding_qid": "", "holdingInventoryNumber": ""}]


def fetch_qid_rows(query: str, endpoint: str, timeout: int) -> list[dict[str, str]]:
    response = requests.post(
        endpoint,
        data={"query": query, "format": "json"},
        headers=BROWSERISH_HEADERS,
        timeout=timeout,
    )
    response.raise_for_status()
    try:
        data = response.json()
    except requests.exceptions.JSONDecodeError as exc:
        snippet = response.text[:500].replace("\n", " ")
        raise RuntimeError(
            f"Expected FactGrid SPARQL JSON but received {response.headers.get('content-type', '')}; "
            f"status={response.status_code}; first 500 chars: {snippet}"
        ) from exc
    rows: list[dict[str, str]] = []
    for binding in data.get("results", {}).get("bindings", []):
        row = {key: value.get("value", "") for key, value in binding.items()}
        row["item_id"] = qid_from_uri(row.get("item"))
        row["instance_of_qid"] = qid_from_uri(row.get("instanceOf"))
        rows.append(row)
    return rows


def fetch_entities(qids: list[str], api_url: str, timeout: int) -> dict:
    response = requests.post(
        api_url,
        data={
            "action": "wbgetentities",
            "ids": "|".join(qids),
            "props": "labels|aliases|claims",
            "languages": "en",
            "format": "json",
        },
        headers=BROWSERISH_HEADERS,
        timeout=timeout,
    )
    response.raise_for_status()
    try:
        return response.json()
    except requests.exceptions.JSONDecodeError as exc:
        snippet = response.text[:500].replace("\n", " ")
        raise RuntimeError(
            f"Expected FactGrid API JSON but received {response.headers.get('content-type', '')}; "
            f"status={response.status_code}; first 500 chars: {snippet}"
        ) from exc


def fetch_labels(qids: set[str], api_url: str, timeout: int) -> dict[str, str]:
    labels: dict[str, str] = {}
    ids = sorted(qid for qid in qids if re.fullmatch(r"Q\d+", clean(qid)))
    for start in range(0, len(ids), 50):
        chunk = ids[start : start + 50]
        data = fetch_entities(chunk, api_url, timeout)
        for qid, entity in data.get("entities", {}).items():
            labels[qid] = clean(entity.get("labels", {}).get("en", {}).get("value"))
    return labels


def alias_text(entity: dict) -> str:
    aliases = []
    for alias in entity.get("aliases", {}).get("en", []):
        value = clean(alias.get("value"))
        if value and value not in aliases:
            aliases.append(value)
    return " | ".join(aliases)


def enrich_qid_rows(qid_rows: list[dict[str, str]], api_url: str, timeout: int) -> list[dict[str, str]]:
    if not qid_rows:
        return []
    qids = [row["item_id"] for row in qid_rows if row.get("item_id")]
    data = fetch_entities(qids, api_url, timeout)
    label_targets: set[str] = {row.get("instance_of_qid", "") for row in qid_rows}
    item_rows: list[dict[str, str]] = []
    for row in qid_rows:
        qid = row.get("item_id", "")
        entity = data.get("entities", {}).get(qid, {})
        cdli_values = claim_values(entity, "P692") or [""]
        direct_inventory_values = claim_values(entity, "P10") or [""]
        holdings = present_holding_records(entity)
        for holding in holdings:
            label_targets.add(holding.get("present_holding_qid", ""))
        for cdli_id in cdli_values:
            for direct_inventory in direct_inventory_values:
                for holding in holdings:
                    item_rows.append(
                        {
                            "item": f"https://database.factgrid.de/entity/{qid}",
                            "item_id": qid,
                            "itemLabel": clean(entity.get("labels", {}).get("en", {}).get("value")),
                            "itemAliases": alias_text(entity),
                            "instance_of_qid": row.get("instance_of_qid", ""),
                            "instanceOfLabel": "",
                            "cdliId": cdli_id,
                            "directInventoryNumber": direct_inventory,
                            "present_holding_qid": holding.get("present_holding_qid", ""),
                            "presentHoldingLabel": "",
                            "holdingInventoryNumber": holding.get("holdingInventoryNumber", ""),
                        }
                    )
    labels = fetch_labels(label_targets, api_url, timeout)
    for row in item_rows:
        row["instanceOfLabel"] = labels.get(row.get("instance_of_qid", ""), "")
        row["presentHoldingLabel"] = labels.get(row.get("present_holding_qid", ""), "")
    return item_rows


def enrich_qid_rows_with_retries(
    qid_rows: list[dict[str, str]],
    api_url: str,
    timeout: int,
    retries: int,
    sleep: float,
) -> list[dict[str, str]]:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            return enrich_qid_rows(qid_rows, api_url, timeout)
        except Exception as exc:
            last_error = exc
            print(
                f"  API enrichment attempt {attempt}/{retries} failed for "
                f"{qid_rows[0].get('item_id', '')}-{qid_rows[-1].get('item_id', '')}: "
                f"{type(exc).__name__}: {exc}",
                flush=True,
            )
            time.sleep(sleep * attempt)
    assert last_error is not None
    raise last_error


def read_existing(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, low_memory=False).fillna("")


def summarize(df: pd.DataFrame, instance_qids: list[str]) -> pd.DataFrame:
    if df.empty:
        rows = [
            {"metric": "register_rows", "value": 0},
            {"metric": "unique_items", "value": 0},
        ]
    else:
        rows = [
            {"metric": "register_rows", "value": len(df)},
            {"metric": "unique_items", "value": df["item_id"].nunique()},
            {"metric": "items_with_cdli_id", "value": df.loc[df["cdliId"].map(clean).ne(""), "item_id"].nunique()},
            {"metric": "items_with_aliases", "value": df.loc[df["itemAliases"].map(clean).ne(""), "item_id"].nunique()},
            {
                "metric": "items_with_holding_inventory_qualifier",
                "value": df.loc[df["holdingInventoryNumber"].map(clean).ne(""), "item_id"].nunique(),
            },
        ]
    rows.append({"metric": "instance_of_qids", "value": ",".join(instance_qids)})
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance-of-qids", default="Q512006", help="Comma/space-separated FactGrid instance QIDs.")
    parser.add_argument("--endpoint", default=FACTGRID_SPARQL)
    parser.add_argument("--api-url", default=FACTGRID_API)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--query-output", type=Path, default=DEFAULT_QUERY_OUTPUT)
    parser.add_argument("--chunk-size", type=int, default=5000)
    parser.add_argument("--api-chunk-size", type=int, default=50)
    parser.add_argument("--max-rows", type=int, default=0, help="Optional cap for testing; 0 means fetch until exhausted.")
    parser.add_argument("--sleep", type=float, default=1.0)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    instance_qids = parse_qids(args.instance_of_qids)
    if not instance_qids:
        raise RuntimeError("No valid --instance-of-qids were supplied.")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.query_output.parent.mkdir(parents=True, exist_ok=True)
    args.query_output.write_text(build_query(instance_qids, args.chunk_size, 0), encoding="utf-8")

    frames = []
    if args.resume:
        existing = read_existing(args.output)
        if not existing.empty:
            frames.append(existing)
            if "item_id" in existing.columns:
                offset = existing["item_id"].map(clean).replace("", pd.NA).dropna().nunique()
            else:
                offset = len(existing)
        else:
            offset = 0
    else:
        offset = 0

    total_new = 0
    while True:
        if args.max_rows and total_new >= args.max_rows:
            break
        limit = args.chunk_size
        if args.max_rows:
            limit = min(limit, args.max_rows - total_new)
        query = build_query(instance_qids, limit, offset)
        print(f"Fetching FactGrid artifact rows offset={offset} limit={limit}", flush=True)
        last_error: Exception | None = None
        qid_rows: list[dict[str, str]] = []
        for attempt in range(1, args.retries + 1):
            try:
                qid_rows = fetch_qid_rows(query, args.endpoint, args.timeout)
                last_error = None
                break
            except Exception as exc:
                last_error = exc
                print(f"  attempt {attempt}/{args.retries} failed: {type(exc).__name__}: {exc}", flush=True)
                time.sleep(args.sleep * attempt)
        if last_error is not None:
            raise last_error
        if not qid_rows:
            break
        rows: list[dict[str, str]] = []
        for start in range(0, len(qid_rows), args.api_chunk_size):
            rows.extend(
                enrich_qid_rows_with_retries(
                    qid_rows[start : start + args.api_chunk_size],
                    args.api_url,
                    args.timeout,
                    args.retries,
                    args.sleep,
                )
            )
        frames.append(pd.DataFrame(rows))
        total_new += len(qid_rows)
        offset += len(qid_rows)
        df = pd.concat(frames, ignore_index=True).drop_duplicates(
            ["item_id", "cdliId", "present_holding_qid", "holdingInventoryNumber", "directInventoryNumber"],
            keep="last",
        )
        df.to_csv(args.output, index=False)
        summarize(df, instance_qids).to_csv(args.summary, index=False)
        print(f"  saved {len(df)} rows; {df['item_id'].nunique()} unique items", flush=True)
        if len(qid_rows) < limit:
            break
        time.sleep(args.sleep)

    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if not df.empty:
        df = df.drop_duplicates(
            ["item_id", "cdliId", "present_holding_qid", "holdingInventoryNumber", "directInventoryNumber"],
            keep="last",
        )
    df.to_csv(args.output, index=False)
    summary = summarize(df, instance_qids)
    summary.to_csv(args.summary, index=False)
    print(summary.to_string(index=False))
    print(f"Wrote register -> {args.output}")
    print(f"Wrote summary -> {args.summary}")


if __name__ == "__main__":
    main()
