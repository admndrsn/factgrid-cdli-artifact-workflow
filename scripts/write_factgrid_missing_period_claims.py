#!/usr/bin/env python3
"""Write vetted missing FactGrid period claims from an audit-derived CSV."""

from __future__ import annotations

import argparse
import getpass
import os
import re
import time
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from tqdm.auto import tqdm


WORKFLOW_ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = WORKFLOW_ROOT / "published" / "period_audit"
DEFAULT_CANDIDATES = AUDIT_ROOT / "factgrid_missing_period_claim_candidates.csv"
DEFAULT_RESULTS = AUDIT_ROOT / "factgrid_missing_period_claim_results.csv"
FACTGRID_API = "https://database.factgrid.de/w/api.php"
PERIOD_PROPERTIES = ["P853", "P583"]


def clean(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none", "null"} else text


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, low_memory=False).fillna("")


def cdli_key(value: object) -> str:
    digits = re.sub(r"\D+", "", clean(value))
    return digits.lstrip("0") or ("0" if digits else "")


def env_or_prompt(name: str, prompt: str, secret: bool = False) -> str:
    value = os.environ.get(name, "")
    if value:
        return value
    return getpass.getpass(prompt) if secret else input(prompt)


def api_post(session: requests.Session, **data: str) -> dict[str, Any]:
    response = session.post(FACTGRID_API, data={"format": "json", **data}, timeout=60)
    response.raise_for_status()
    payload = response.json()
    if "error" in payload:
        raise RuntimeError(payload["error"])
    return payload


def login() -> requests.Session:
    username = env_or_prompt("FG_USER", "FactGrid username: ")
    password = env_or_prompt("FG_PASS", "FactGrid password: ", secret=True)
    session = requests.Session()
    token_payload = api_post(session, action="query", meta="tokens", type="login")
    login_token = token_payload["query"]["tokens"]["logintoken"]
    api_post(session, action="login", lgname=username, lgpassword=password, lgtoken=login_token)
    return session


def csrf_token(session: requests.Session) -> str:
    payload = api_post(session, action="query", meta="tokens")
    return payload["query"]["tokens"]["csrftoken"]


def qid_from_datavalue(value: object) -> str:
    if isinstance(value, dict):
        if value.get("id"):
            return clean(value.get("id"))
        if value.get("numeric-id"):
            return f"Q{clean(value.get('numeric-id'))}"
    return clean(value)


def fetch_entity(session: requests.Session, qid: str) -> dict[str, Any]:
    payload = api_post(session, action="wbgetentities", ids=qid)
    entity = payload.get("entities", {}).get(qid)
    if not entity or "missing" in entity:
        raise RuntimeError(f"{qid} not found")
    return entity


def entity_cdli_keys(entity: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    for claim in entity.get("claims", {}).get("P692", []):
        value = qid_from_datavalue(claim.get("mainsnak", {}).get("datavalue", {}).get("value"))
        key = cdli_key(value)
        if key:
            keys.add(key)
    return keys


def existing_period_claims(entity: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for prop in PERIOD_PROPERTIES:
        for claim in entity.get("claims", {}).get(prop, []):
            value = qid_from_datavalue(claim.get("mainsnak", {}).get("datavalue", {}).get("value"))
            if value:
                out.append(f"{prop}:{value}")
    return out


def create_item_claim(session: requests.Session, token: str, item_qid: str, prop: str, value_qid: str, summary: str) -> str:
    payload = api_post(
        session,
        action="wbcreateclaim",
        entity=item_qid,
        snaktype="value",
        property=prop,
        value='{"entity-type":"item","numeric-id":%s}' % value_qid.removeprefix("Q"),
        token=token,
        summary=summary,
    )
    return clean(payload.get("claim", {}).get("id"))


def prepare_work(candidates: pd.DataFrame, results: pd.DataFrame, limit: int) -> pd.DataFrame:
    required = {"cdli_id", "factgrid_qid", "period_property", "period_qid"}
    missing = required - set(candidates.columns)
    if missing:
        raise RuntimeError(f"Candidate CSV missing columns: {sorted(missing)}")
    work = candidates[
        candidates["write_status"].eq("ready")
        & candidates["factgrid_qid"].map(clean).str.fullmatch(r"Q\d+", na=False)
        & candidates["period_property"].map(clean).str.fullmatch(r"P\d+", na=False)
        & candidates["period_qid"].map(clean).str.fullmatch(r"Q\d+", na=False)
    ].copy()
    key_cols = ["cdli_id", "factgrid_qid", "period_property", "period_qid"]
    if not results.empty and {*key_cols, "write_status"}.issubset(results.columns):
        done_keys = set(
            results.loc[results["write_status"].isin(["written", "skipped_existing_period"])]
            .apply(lambda r: "|".join([clean(r.get(c)) for c in key_cols]), axis=1)
        )
        work["_write_key"] = work.apply(lambda r: "|".join([clean(r.get(c)) for c in key_cols]), axis=1)
        work = work[~work["_write_key"].isin(done_keys)].copy()
    if limit:
        work = work.head(limit).copy()
    return work


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--preview", type=int, default=10)
    parser.add_argument("--sleep", type=float, default=2.0)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--continue-on-row-error", action="store_true")
    args = parser.parse_args()

    candidates = read_csv(args.candidates)
    results = read_csv(args.results)
    work = prepare_work(candidates, results, args.limit)

    print(f"missing period claims selected: {len(work)}")
    if len(work):
        print(
            work[
                [
                    "cdli_id",
                    "factgrid_qid",
                    "live_label_en",
                    "period_property",
                    "period_qid",
                    "expected_period_label",
                ]
            ]
            .head(args.preview)
            .to_string(index=False)
        )
    if not args.write:
        print("\nDRY_RUN: no FactGrid period claims added. Pass --write to add claims.")
        return

    session = login()
    token = csrf_token(session)
    out_rows: list[dict[str, object]] = []
    for _, row in tqdm(work.iterrows(), total=len(work)):
        qid = clean(row.get("factgrid_qid"))
        prop = clean(row.get("period_property"))
        period_qid = clean(row.get("period_qid"))
        summary = f"Add missing CDLI period for {clean(row.get('cdli_id'))}: {period_qid}"
        try:
            entity = fetch_entity(session, qid)
            expected_cdli_key = cdli_key(row.get("cdli_id"))
            live_cdli_keys = entity_cdli_keys(entity)
            if expected_cdli_key and live_cdli_keys and expected_cdli_key not in live_cdli_keys:
                raise RuntimeError(f"Live P692 on {qid} is {sorted(live_cdli_keys)}, not {expected_cdli_key}")
            existing = existing_period_claims(entity)
            if existing:
                status = "skipped_existing_period"
                error = f"Existing period claim(s): {' | '.join(existing)}"
                claim_id = ""
                print(f"skipped {qid}: {error}", flush=True)
            else:
                claim_id = create_item_claim(session, token, qid, prop, period_qid, summary)
                status = "written"
                error = ""
                print(f"added {qid}: {prop} {period_qid}", flush=True)
        except Exception as exc:
            status = "error"
            error = f"{type(exc).__name__}: {exc}"[:500]
            claim_id = ""
            print(f"row error {qid}: {error}", flush=True)
            if not args.continue_on_row_error:
                raise
        out_rows.append(
            {
                **{col: clean(row.get(col)) for col in candidates.columns},
                "new_claim_id": claim_id,
                "write_status": status,
                "write_error": error,
            }
        )
        args.results.parent.mkdir(parents=True, exist_ok=True)
        pd.concat([results, pd.DataFrame(out_rows)], ignore_index=True).to_csv(args.results, index=False)
        time.sleep(args.sleep)


if __name__ == "__main__":
    main()
