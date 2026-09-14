#!/usr/bin/env python3
"""Audit live FactGrid period claims against local CDLI-derived staging.

The script compares local staged period statements for CDLI artifact rows to the
period/style claims currently present on the corresponding FactGrid items. It
uses SPARQL by default, with a MediaWiki API fallback if the query service is
unavailable.
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
PILOT_ROOT = WORKFLOW_ROOT / "published" / "pilots"
AUDIT_ROOT = WORKFLOW_ROOT / "published" / "period_audit"
DEFAULT_STATEMENTS = PILOT_ROOT / "cdli_artifact_statement_staging_tranche_35001_60000.csv"
DEFAULT_RESULTS = PILOT_ROOT / "factgrid_cdli_artifact_write_results_tranche_35001_60000.csv"
DEFAULT_OUTPUT = AUDIT_ROOT / "factgrid_period_claim_audit.csv"
DEFAULT_MISMATCHES = AUDIT_ROOT / "factgrid_period_claim_mismatches.csv"
DEFAULT_SUMMARY = AUDIT_ROOT / "factgrid_period_claim_audit_summary.csv"
DEFAULT_QUERY_OUTPUT = AUDIT_ROOT / "factgrid_period_claim_audit_query.rq"
FACTGRID_SPARQL = "https://database.factgrid.de/sparql"
FACTGRID_API = "https://database.factgrid.de/w/api.php"
BROWSERISH_HEADERS = {
    "User-Agent": "TokenWorks-FactGrid-period-audit/0.1",
    "Accept": "application/sparql-results+json, application/json, */*",
}
PERIOD_PROPERTIES = ["P853", "P583"]
DEFAULT_REQUEST_RETRIES = 5
DEFAULT_REQUEST_RETRY_SLEEP = 15.0


def clean(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none", "null"} else text


def qid_from_uri(value: object) -> str:
    match = re.search(r"(Q\d+)$", clean(value))
    return match.group(1) if match else clean(value)


def cdli_key(value: object) -> str:
    digits = re.sub(r"\D+", "", clean(value))
    return digits.lstrip("0") or ("0" if digits else "")


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, low_memory=False).fillna("")


def staged_period_rows(statements: pd.DataFrame) -> pd.DataFrame:
    if statements.empty:
        return pd.DataFrame()
    rows = statements[
        statements["field_name"].eq("period")
        & statements["value"].map(clean).str.fullmatch(r"Q\d+", na=False)
    ].copy()
    return rows[["cdli_id", "artifact_label", "value", "value_label"]].rename(
        columns={"value": "expected_period_qid", "value_label": "expected_period_label"}
    )


def result_rows(results: pd.DataFrame) -> pd.DataFrame:
    if results.empty:
        return pd.DataFrame()
    rows = results[
        results["write_status"].eq("written")
        & results["factgrid_qid"].map(clean).str.fullmatch(r"Q\d+", na=False)
    ].copy()
    rows["cdli_key"] = rows["cdli_id"].map(cdli_key)
    return rows[["cdli_id", "cdli_key", "factgrid_qid", "artifact_label"]].drop_duplicates(
        ["cdli_key", "factgrid_qid"], keep="last"
    )


def build_query(qids: list[str]) -> str:
    values = " ".join(f"fg:{qid}" for qid in qids)
    return dedent(
        f"""
        PREFIX fg: <https://database.factgrid.de/entity/>
        PREFIX fgt: <https://database.factgrid.de/prop/direct/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX schema: <http://schema.org/>

        SELECT ?item ?itemLabel ?itemDescription ?cdliId ?periodProperty ?period ?periodLabel WHERE {{
          VALUES ?item {{ {values} }}
          OPTIONAL {{ ?item fgt:P692 ?cdliId . }}
          OPTIONAL {{
            {{
              ?item fgt:P853 ?period .
              BIND("P853" AS ?periodProperty)
            }}
            UNION
            {{
              ?item fgt:P583 ?period .
              BIND("P583" AS ?periodProperty)
            }}
          }}
          OPTIONAL {{
            ?period rdfs:label ?periodLabel .
            FILTER(LANG(?periodLabel) = "en")
          }}
          OPTIONAL {{
            ?item rdfs:label ?itemLabel .
            FILTER(LANG(?itemLabel) = "en")
          }}
          OPTIONAL {{
            ?item schema:description ?itemDescription .
            FILTER(LANG(?itemDescription) = "en")
          }}
        }}
        ORDER BY ?item ?periodProperty ?period
        """
    ).strip()


def fetch_sparql(query: str, endpoint: str, timeout: int) -> pd.DataFrame:
    response = requests.post(
        endpoint,
        data={"query": query, "format": "json"},
        headers=BROWSERISH_HEADERS,
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()
    rows: list[dict[str, str]] = []
    for binding in data.get("results", {}).get("bindings", []):
        row = {key: clean(value.get("value")) for key, value in binding.items()}
        row["factgrid_qid"] = qid_from_uri(row.get("item"))
        row["live_cdli_id"] = clean(row.get("cdliId"))
        row["live_period_qid"] = qid_from_uri(row.get("period"))
        row["live_period_label"] = clean(row.get("periodLabel"))
        row["live_period_property"] = clean(row.get("periodProperty"))
        row["live_label_en"] = clean(row.get("itemLabel"))
        row["live_description_en"] = clean(row.get("itemDescription"))
        rows.append(row)
    return pd.DataFrame(rows)


def parse_datavalue(snak: dict) -> str:
    value = (snak.get("datavalue") or {}).get("value")
    if isinstance(value, dict):
        if value.get("id"):
            return clean(value.get("id"))
        if value.get("numeric-id"):
            return f"Q{clean(value.get('numeric-id'))}"
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return clean(value)


def fetch_entities(qids: list[str], timeout: int, retries: int, retry_sleep: float) -> dict:
    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            response = requests.post(
                FACTGRID_API,
                data={
                    "action": "wbgetentities",
                    "ids": "|".join(qids),
                    "props": "labels|descriptions|claims",
                    "languages": "en",
                    "format": "json",
                },
                headers=BROWSERISH_HEADERS,
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            last_exc = exc
            if attempt >= retries:
                break
            print(
                f"  FactGrid API fetch failed for {qids[0]}-{qids[-1]} "
                f"({type(exc).__name__}: {exc}); retry {attempt}/{retries - 1} "
                f"in {retry_sleep:g}s",
                flush=True,
            )
            time.sleep(retry_sleep)
    assert last_exc is not None
    raise last_exc


def fetch_api_period_rows(qids: list[str], timeout: int, retries: int, retry_sleep: float) -> pd.DataFrame:
    rows: list[dict[str, str]] = []
    label_targets: set[str] = set()
    for start in range(0, len(qids), 50):
        chunk = qids[start : start + 50]
        entities = fetch_entities(chunk, timeout, retries, retry_sleep).get("entities", {})
        for qid in chunk:
            entity = entities.get(qid, {})
            cdli_values = []
            for claim in entity.get("claims", {}).get("P692", []):
                value = parse_datavalue(claim.get("mainsnak") or {})
                if value:
                    cdli_values.append(value)
            cdli_value = cdli_values[0] if cdli_values else ""
            live_label = clean(entity.get("labels", {}).get("en", {}).get("value"))
            live_description = clean(entity.get("descriptions", {}).get("en", {}).get("value"))
            found_period = False
            for prop in PERIOD_PROPERTIES:
                for claim in entity.get("claims", {}).get(prop, []):
                    period_qid = parse_datavalue(claim.get("mainsnak") or {})
                    if period_qid:
                        found_period = True
                        label_targets.add(period_qid)
                        rows.append(
                            {
                                "factgrid_qid": qid,
                                "live_cdli_id": cdli_value,
                                "live_period_property": prop,
                                "live_period_qid": period_qid,
                                "live_period_label": "",
                                "live_label_en": live_label,
                                "live_description_en": live_description,
                            }
                        )
            if not found_period:
                rows.append(
                    {
                        "factgrid_qid": qid,
                        "live_cdli_id": cdli_value,
                        "live_period_property": "",
                        "live_period_qid": "",
                        "live_period_label": "",
                        "live_label_en": live_label,
                        "live_description_en": live_description,
                    }
                )
    labels = fetch_labels(label_targets, timeout, retries, retry_sleep)
    for row in rows:
        row["live_period_label"] = labels.get(row["live_period_qid"], "")
    return pd.DataFrame(rows)


def fetch_labels(qids: set[str], timeout: int, retries: int, retry_sleep: float) -> dict[str, str]:
    labels: dict[str, str] = {}
    ids = sorted(qid for qid in qids if re.fullmatch(r"Q\d+", clean(qid)))
    for start in range(0, len(ids), 50):
        chunk = ids[start : start + 50]
        entities = fetch_entities(chunk, timeout, retries, retry_sleep).get("entities", {})
        for qid, entity in entities.items():
            labels[qid] = clean(entity.get("labels", {}).get("en", {}).get("value"))
    return labels


def fetch_live_period_rows(
    qids: list[str],
    chunk_size: int,
    source: str,
    endpoint: str,
    timeout: int,
    sleep: float,
    retries: int,
    retry_sleep: float,
    query_output: Path,
) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    if query_output:
        query_output.parent.mkdir(parents=True, exist_ok=True)
        query_output.write_text(build_query(qids[: min(len(qids), chunk_size)]), encoding="utf-8")
    for start in range(0, len(qids), chunk_size):
        chunk = qids[start : start + chunk_size]
        print(f"Fetching live period claims {start + 1}-{start + len(chunk)} of {len(qids)}", flush=True)
        frame = pd.DataFrame()
        if source in {"auto", "sparql"}:
            try:
                frame = fetch_sparql(build_query(chunk), endpoint, timeout)
            except Exception as exc:
                if source == "sparql":
                    raise
                print(f"  SPARQL failed; falling back to API: {type(exc).__name__}: {exc}", flush=True)
        if frame.empty and source in {"auto", "api"}:
            frame = fetch_api_period_rows(chunk, timeout, retries, retry_sleep)
        frames.append(frame)
        time.sleep(sleep)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True).fillna("")


def classify(row: pd.Series) -> str:
    expected = clean(row.get("expected_period_qid"))
    live = clean(row.get("live_period_qid"))
    if not expected and not live:
        return "no_expected_no_live"
    if expected and not live:
        return "missing_live_period"
    if live and not expected:
        return "unexpected_live_period"
    return "match" if expected == live else "mismatch"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--statements", type=Path, default=DEFAULT_STATEMENTS)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--mismatches", type=Path, default=DEFAULT_MISMATCHES)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--query-output", type=Path, default=DEFAULT_QUERY_OUTPUT)
    parser.add_argument("--source", choices=["auto", "sparql", "api"], default="auto")
    parser.add_argument("--endpoint", default=FACTGRID_SPARQL)
    parser.add_argument("--chunk-size", type=int, default=100)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--request-retries", type=int, default=DEFAULT_REQUEST_RETRIES)
    parser.add_argument("--request-retry-sleep", type=float, default=DEFAULT_REQUEST_RETRY_SLEEP)
    parser.add_argument("--sleep", type=float, default=1.0)
    args = parser.parse_args()

    statements = read_csv(args.statements)
    results = read_csv(args.results)
    staged = staged_period_rows(statements)
    result = result_rows(results)
    if result.empty:
        raise RuntimeError(f"No written FactGrid item rows found in {args.results}")
    if staged.empty:
        raise RuntimeError(f"No staged period rows found in {args.statements}")
    staged["cdli_key"] = staged["cdli_id"].map(cdli_key)
    qids = result["factgrid_qid"].drop_duplicates().tolist()
    if args.limit:
        qids = qids[: args.limit]
    live = fetch_live_period_rows(
        qids,
        args.chunk_size,
        args.source,
        args.endpoint,
        args.timeout,
        args.sleep,
        args.request_retries,
        args.request_retry_sleep,
        args.query_output,
    )
    if live.empty:
        live = pd.DataFrame(
            columns=[
                "factgrid_qid",
                "live_cdli_id",
                "live_period_property",
                "live_period_qid",
                "live_period_label",
                "live_label_en",
                "live_description_en",
            ]
        )
    live["live_cdli_key"] = live["live_cdli_id"].map(cdli_key)
    audit = live.merge(staged, left_on="live_cdli_key", right_on="cdli_key", how="left").fillna("")
    audit["cdli_id"] = audit["live_cdli_key"]
    audit["audit_status"] = audit.apply(classify, axis=1)
    columns = [
        "audit_status",
        "cdli_id",
        "factgrid_qid",
        "artifact_label",
        "live_label_en",
        "live_description_en",
        "expected_period_qid",
        "expected_period_label",
        "live_period_property",
        "live_period_qid",
        "live_period_label",
        "live_cdli_id",
    ]
    audit = audit[[col for col in columns if col in audit.columns]].sort_values(["audit_status", "cdli_id", "factgrid_qid"])
    mismatches = audit[audit["audit_status"].ne("match")].copy()
    summary = audit["audit_status"].value_counts(dropna=False).rename_axis("audit_status").reset_index(name="count")
    for path, frame in [(args.output, audit), (args.mismatches, mismatches), (args.summary, summary)]:
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(path, index=False)
    print(summary.to_string(index=False))
    print(f"Wrote audit -> {args.output}")
    print(f"Wrote mismatches -> {args.mismatches}")
    print(f"Wrote summary -> {args.summary}")
    print(f"Wrote sample SPARQL query -> {args.query_output}")


if __name__ == "__main__":
    main()
