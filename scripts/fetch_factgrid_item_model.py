#!/usr/bin/env python3
"""Fetch a FactGrid item statement model for comparison with TokenWorks.

This is a read-only helper. It queries the FactGrid SPARQL endpoint for one or
more item IDs and writes a flat CSV of statement/property/value/qualifier rows.
Use it to compare existing FactGrid cuneiform tablet modeling against the
TokenWorks artifact staging model before writing artifact data.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from textwrap import dedent

import pandas as pd
import requests


WORKFLOW_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = WORKFLOW_ROOT / "published" / "factgrid_model_samples" / "factgrid_item_model_claims.csv"
DEFAULT_SUMMARY = WORKFLOW_ROOT / "published" / "factgrid_model_samples" / "factgrid_item_model_summary.csv"
FACTGRID_SPARQL = "https://database.factgrid.de/sparql"
FACTGRID_API = "https://database.factgrid.de/w/api.php"
BROWSERISH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36 TokenWorks-CDLI-model-sampler/0.1"
    ),
    "Accept": "application/json, application/sparql-results+json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


def clean(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null"}:
        return ""
    return text


def normalize_qid(value: str) -> str:
    text = clean(value)
    if not text:
        return ""
    if text.startswith("http"):
        return text.rsplit("/", 1)[-1]
    if text.upper().startswith("Q"):
        return "Q" + text[1:]
    return text


def read_qids_from_file(path: Path) -> list[str]:
    if not path.exists():
        raise RuntimeError(f"QID file does not exist: {path}")
    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path, dtype=str).fillna("")
        if "factgrid_qid" in df.columns:
            values = df["factgrid_qid"].tolist()
        elif "item_id" in df.columns:
            values = df["item_id"].tolist()
        else:
            values = df.iloc[:, 0].tolist()
    else:
        values = path.read_text(encoding="utf-8").splitlines()
    qids = []
    seen = set()
    for value in values:
        qid = normalize_qid(value)
        if not qid or qid in seen:
            continue
        qids.append(qid)
        seen.add(qid)
    return qids


def build_query(qids: list[str]) -> str:
    values = " ".join(f"fg:{qid}" for qid in qids)
    return dedent(
        f"""
        PREFIX fg: <https://database.factgrid.de/entity/>
        PREFIX wikibase: <http://wikiba.se/ontology#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT
          ?item ?itemLabel
          ?property ?propertyLabel ?claimPredicate ?statementProperty
          ?value ?valueLabel
          ?qualifierProperty ?qualifierPropertyLabel ?qualifierPredicate ?qualifierValue ?qualifierValueLabel
        WHERE {{
          VALUES ?item {{ {values} }}
          ?item ?claimPredicate ?statement .
          ?property wikibase:claim ?claimPredicate ;
                    wikibase:statementProperty ?statementProperty .
          ?statement ?statementProperty ?value .

          OPTIONAL {{
            ?qualifierProperty wikibase:qualifier ?qualifierPredicate .
            ?statement ?qualifierPredicate ?qualifierValue .
          }}

          OPTIONAL {{ ?item rdfs:label ?itemLabel . FILTER(LANG(?itemLabel) = "en") }}
          OPTIONAL {{ ?property rdfs:label ?propertyLabel . FILTER(LANG(?propertyLabel) = "en") }}
          OPTIONAL {{ ?value rdfs:label ?valueLabel . FILTER(LANG(?valueLabel) = "en") }}
          OPTIONAL {{ ?qualifierProperty rdfs:label ?qualifierPropertyLabel . FILTER(LANG(?qualifierPropertyLabel) = "en") }}
          OPTIONAL {{ ?qualifierValue rdfs:label ?qualifierValueLabel . FILTER(LANG(?qualifierValueLabel) = "en") }}
        }}
        ORDER BY ?item ?property ?value ?qualifierProperty ?qualifierValue
        """
    ).strip()


def response_json(response: requests.Response, raw_output: str | Path = "") -> dict:
    try:
        return response.json()
    except requests.exceptions.JSONDecodeError as exc:
        if raw_output:
            raw_path = Path(raw_output)
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_text(response.text, encoding="utf-8", errors="replace")
            where = f" Raw response saved to {raw_path}."
        else:
            where = ""
        snippet = response.text[:500].replace("\n", " ")
        block_hint = ""
        if "mod_repudiator" in response.text:
            block_hint = (
                " FactGrid appears to be returning a mod_repudiator block page, "
                "so automated endpoint access is temporarily blocked or rate-limited."
            )
        raise RuntimeError(
            f"Expected JSON but received {response.headers.get('content-type', 'unknown content type')} "
            f"from {response.url}. Status={response.status_code}.{where}{block_hint} First 500 chars: {snippet}"
        ) from exc


def fetch_sparql(query: str, endpoint: str, raw_output: str | Path = "") -> pd.DataFrame:
    response = requests.post(
        endpoint,
        data={"query": query, "format": "json"},
        headers=BROWSERISH_HEADERS | {"Accept": "application/sparql-results+json, application/json"},
        timeout=180,
    )
    response.raise_for_status()
    data = response_json(response, raw_output)
    rows = []
    for binding in data.get("results", {}).get("bindings", []):
        row = {}
        for key, value in binding.items():
            row[key] = value.get("value", "")
        rows.append(row)
    return pd.DataFrame(rows)


def parse_datavalue(snak: dict) -> tuple[str, str, str]:
    datatype = clean(snak.get("datatype"))
    datavalue = snak.get("datavalue") or {}
    value = datavalue.get("value")
    if isinstance(value, dict):
        if "id" in value:
            return clean(value.get("id")), datatype, "wikibase-entity"
        if "text" in value:
            language = clean(value.get("language"))
            text = clean(value.get("text"))
            return f"{text} ({language})" if language else text, datatype, "monolingualtext"
        if "amount" in value:
            amount = clean(value.get("amount")).lstrip("+")
            unit = clean(value.get("unit"))
            return f"{amount} {unit}".strip(), datatype, "quantity"
        if "time" in value:
            return clean(value.get("time")), datatype, "time"
        return json.dumps(value, ensure_ascii=False, sort_keys=True), datatype, datavalue.get("type", "")
    return clean(value), datatype, datavalue.get("type", "")


def fetch_entity_json(qids: list[str], api_url: str) -> dict:
    response = requests.post(
        api_url,
        data={
            "action": "wbgetentities",
            "ids": "|".join(qids),
            "props": "labels|descriptions|aliases|claims",
            "languages": "en",
            "format": "json",
        },
        headers=BROWSERISH_HEADERS,
        timeout=180,
    )
    response.raise_for_status()
    return response_json(response)


def fetch_labels(entity_ids: set[str], api_url: str) -> dict[str, str]:
    ids = sorted(i for i in entity_ids if i and (i.startswith("Q") or i.startswith("P")))
    labels: dict[str, str] = {}
    for i in range(0, len(ids), 50):
        chunk = ids[i : i + 50]
        response = requests.post(
            api_url,
            data={
                "action": "wbgetentities",
                "ids": "|".join(chunk),
                "props": "labels",
                "languages": "en",
                "format": "json",
            },
            headers=BROWSERISH_HEADERS,
            timeout=180,
        )
        response.raise_for_status()
        data = response_json(response)
        for entity_id, entity in data.get("entities", {}).items():
            labels[entity_id] = clean(entity.get("labels", {}).get("en", {}).get("value"))
    return labels


def fetch_api_claims(qids: list[str], api_url: str) -> pd.DataFrame:
    data = fetch_entity_json(qids, api_url)
    rows = []
    entity_ids: set[str] = set(qids)
    for qid, entity in data.get("entities", {}).items():
        item_label = clean(entity.get("labels", {}).get("en", {}).get("value"))
        claims = entity.get("claims", {}) or {}
        for property_id, statements in claims.items():
            entity_ids.add(property_id)
            for statement in statements:
                mainsnak = statement.get("mainsnak", {})
                value, datatype, value_type = parse_datavalue(mainsnak)
                if value.startswith("Q") or value.startswith("P"):
                    entity_ids.add(value)
                qualifiers = statement.get("qualifiers", {}) or {}
                if not qualifiers:
                    rows.append(
                        {
                            "item_id": qid,
                            "itemLabel": item_label,
                            "property_id": property_id,
                            "propertyLabel": "",
                            "value": value,
                            "value_display": value,
                            "value_datatype": datatype,
                            "value_type": value_type,
                            "qualifier_property_id": "",
                            "qualifierPropertyLabel": "",
                            "qualifierValue": "",
                            "qualifier_value_display": "",
                            "rank": clean(statement.get("rank")),
                            "statement_id": clean(statement.get("id")),
                            "source": "mediawiki_api",
                        }
                    )
                    continue
                for qualifier_property_id, qualifier_snaks in qualifiers.items():
                    entity_ids.add(qualifier_property_id)
                    for qualifier_snak in qualifier_snaks:
                        qualifier_value, qualifier_datatype, qualifier_value_type = parse_datavalue(qualifier_snak)
                        if qualifier_value.startswith("Q") or qualifier_value.startswith("P"):
                            entity_ids.add(qualifier_value)
                        rows.append(
                            {
                                "item_id": qid,
                                "itemLabel": item_label,
                                "property_id": property_id,
                                "propertyLabel": "",
                                "value": value,
                                "value_display": value,
                                "value_datatype": datatype,
                                "value_type": value_type,
                                "qualifier_property_id": qualifier_property_id,
                                "qualifierPropertyLabel": "",
                                "qualifierValue": qualifier_value,
                                "qualifier_value_display": qualifier_value,
                                "qualifier_datatype": qualifier_datatype,
                                "qualifier_value_type": qualifier_value_type,
                                "rank": clean(statement.get("rank")),
                                "statement_id": clean(statement.get("id")),
                                "source": "mediawiki_api",
                            }
                        )
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    labels = fetch_labels(entity_ids, api_url)
    df["propertyLabel"] = df["property_id"].map(labels).fillna("")
    df["value_display"] = df["value"].map(lambda v: labels.get(v, v))
    df["qualifierPropertyLabel"] = df["qualifier_property_id"].map(labels).fillna("")
    df["qualifier_value_display"] = df["qualifierValue"].map(lambda v: labels.get(v, v))
    return df


def extract_id(uri: object) -> str:
    text = clean(uri)
    if "/entity/" in text:
        return text.rsplit("/", 1)[-1]
    if "/prop/" in text:
        return text.rsplit("/", 1)[-1]
    return text


def add_readable_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "property_id" in out.columns:
        return out
    for col in ["item", "property", "qualifierProperty"]:
        if col in out.columns:
            out[col.replace("Property", "_property") + "_id" if col != "item" else "item_id"] = out[col].map(extract_id)
    if "valueLabel" in out.columns and "value" in out.columns:
        out["value_display"] = out["valueLabel"].where(out["valueLabel"].map(clean).ne(""), out["value"])
    if "qualifierValueLabel" in out.columns and "qualifierValue" in out.columns:
        out["qualifier_value_display"] = out["qualifierValueLabel"].where(
            out["qualifierValueLabel"].map(clean).ne(""), out["qualifierValue"]
        )
    return out


def write_summary(df: pd.DataFrame, output: Path) -> None:
    if df.empty:
        summary = pd.DataFrame([("rows", 0)], columns=["metric", "value"])
    else:
        summary = (
            df.groupby(["property_id", "propertyLabel"], dropna=False)
            .agg(
                row_count=("property_id", "size"),
                distinct_values=("value", "nunique"),
                qualifier_rows=("qualifier_property_id", lambda s: int(s.map(clean).ne("").sum())),
            )
            .reset_index()
            .sort_values(["property_id", "propertyLabel"])
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(output, index=False)
    print(summary.to_string(index=False))
    print(f"Wrote summary -> {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--items", default="Q499899", help="Comma-separated FactGrid QIDs to sample.")
    parser.add_argument("--items-file", type=Path, help="CSV or text file of FactGrid QIDs. CSV prefers a factgrid_qid column.")
    parser.add_argument("--chunk-size", type=int, default=50)
    parser.add_argument("--sleep", type=float, default=0.0)
    parser.add_argument("--endpoint", default=FACTGRID_SPARQL)
    parser.add_argument("--api-url", default=FACTGRID_API)
    parser.add_argument("--source", choices=["auto", "sparql", "api"], default="auto")
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", default=DEFAULT_SUMMARY)
    parser.add_argument("--query-output", default="")
    parser.add_argument("--raw-output", default="")
    args = parser.parse_args()

    if args.items_file:
        qids = read_qids_from_file(args.items_file)
    else:
        qids = [normalize_qid(value) for value in args.items.split(",") if normalize_qid(value)]
    if not qids:
        raise RuntimeError("No FactGrid QIDs supplied.")

    query = build_query(qids[: args.chunk_size])
    if args.query_output:
        Path(args.query_output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.query_output).write_text(query + "\n", encoding="utf-8")
        print(f"Wrote SPARQL query -> {args.query_output}")

    frames = []
    for start in range(0, len(qids), args.chunk_size):
        chunk = qids[start : start + args.chunk_size]
        chunk_query = build_query(chunk)
        print(f"Fetching FactGrid items {start + 1}-{start + len(chunk)} of {len(qids)}")
        if args.source == "api":
            chunk_df = fetch_api_claims(chunk, args.api_url)
        else:
            try:
                chunk_df = add_readable_columns(fetch_sparql(chunk_query, args.endpoint, args.raw_output))
                if not chunk_df.empty:
                    chunk_df["source"] = "sparql"
            except Exception as exc:
                if args.source == "sparql":
                    raise
                print(f"SPARQL fetch failed; falling back to MediaWiki API: {type(exc).__name__}: {exc}")
                chunk_df = fetch_api_claims(chunk, args.api_url)
        frames.append(chunk_df)
        if args.sleep and start + len(chunk) < len(qids):
            time.sleep(args.sleep)
    df = pd.concat([frame for frame in frames if not frame.empty], ignore_index=True) if frames else pd.DataFrame()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, index=False)
    print(f"Wrote {len(df)} model rows -> {output}")
    write_summary(df, Path(args.summary))


if __name__ == "__main__":
    main()
