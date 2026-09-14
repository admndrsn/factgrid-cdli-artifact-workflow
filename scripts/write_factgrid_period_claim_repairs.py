#!/usr/bin/env python3
"""Write vetted FactGrid period-claim repairs from an audit CSV."""

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
DEFAULT_REPAIRS = AUDIT_ROOT / "factgrid_period_claim_repair_candidates_verified.csv"
DEFAULT_RESULTS = AUDIT_ROOT / "factgrid_period_claim_repair_results.csv"
FACTGRID_API = "https://database.factgrid.de/w/api.php"


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


def matching_claim_ids(entity: dict[str, Any], prop: str, old_qid: str) -> list[str]:
    out: list[str] = []
    for claim in entity.get("claims", {}).get(prop, []):
        claim_id = clean(claim.get("id"))
        value = qid_from_datavalue(claim.get("mainsnak", {}).get("datavalue", {}).get("value"))
        if claim_id and value == old_qid:
            out.append(claim_id)
    return out


def entity_cdli_keys(entity: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    for claim in entity.get("claims", {}).get("P692", []):
        value = qid_from_datavalue(claim.get("mainsnak", {}).get("datavalue", {}).get("value"))
        key = cdli_key(value)
        if key:
            keys.add(key)
    return keys


def remove_claims(session: requests.Session, token: str, claim_ids: list[str], summary: str) -> None:
    api_post(session, action="wbremoveclaims", claim="|".join(claim_ids), token=token, summary=summary)


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


def prepare_work(repairs: pd.DataFrame, results: pd.DataFrame, limit: int) -> pd.DataFrame:
    required = {"cdli_id", "factgrid_qid", "live_period_property", "live_period_qid", "correct_period_qid"}
    missing = required - set(repairs.columns)
    if missing:
        raise RuntimeError(f"Repair CSV missing columns: {sorted(missing)}")
    work = repairs[
        repairs["repair_status"].eq("ready")
        & repairs["factgrid_qid"].map(clean).str.fullmatch(r"Q\d+", na=False)
        & repairs["live_period_property"].map(clean).str.fullmatch(r"P\d+", na=False)
        & repairs["live_period_qid"].map(clean).str.fullmatch(r"Q\d+", na=False)
        & repairs["correct_period_qid"].map(clean).str.fullmatch(r"Q\d+", na=False)
    ].copy()
    key_cols = ["cdli_id", "factgrid_qid", "live_period_property", "live_period_qid", "correct_period_qid"]
    if not results.empty and {*key_cols, "write_status"}.issubset(results.columns):
        done_keys = set(
            results.loc[results["write_status"].eq("written")]
            .apply(lambda r: "|".join([clean(r.get(c)) for c in key_cols]), axis=1)
        )
        work["_repair_key"] = work.apply(lambda r: "|".join([clean(r.get(c)) for c in key_cols]), axis=1)
        work = work[~work["_repair_key"].isin(done_keys)].copy()
    if limit:
        work = work.head(limit).copy()
    return work


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repairs", type=Path, default=DEFAULT_REPAIRS)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--preview", type=int, default=10)
    parser.add_argument("--sleep", type=float, default=2.0)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--continue-on-row-error", action="store_true")
    args = parser.parse_args()

    repairs = read_csv(args.repairs)
    results = read_csv(args.results)
    work = prepare_work(repairs, results, args.limit)

    print(f"period repairs selected: {len(work)}")
    if len(work):
        print(
            work[
                [
                    "cdli_id",
                    "factgrid_qid",
                    "artifact_label",
                    "live_period_property",
                    "live_period_label",
                    "live_period_qid",
                    "expected_period_label",
                    "correct_period_qid",
                ]
            ]
            .head(args.preview)
            .to_string(index=False)
        )
    if not args.write:
        print("\nDRY_RUN: no FactGrid period claims changed. Pass --write to repair claims.")
        return

    session = login()
    token = csrf_token(session)
    out_rows: list[dict[str, object]] = []
    for _, row in tqdm(work.iterrows(), total=len(work)):
        qid = clean(row.get("factgrid_qid"))
        prop = clean(row.get("live_period_property"))
        old_qid = clean(row.get("live_period_qid"))
        new_qid = clean(row.get("correct_period_qid"))
        summary = f"Repair CDLI period for {clean(row.get('cdli_id'))}: {old_qid} -> {new_qid}"
        try:
            entity = fetch_entity(session, qid)
            expected_cdli_key = cdli_key(row.get("cdli_id"))
            live_cdli_keys = entity_cdli_keys(entity)
            if expected_cdli_key and live_cdli_keys and expected_cdli_key not in live_cdli_keys:
                raise RuntimeError(f"Live P692 on {qid} is {sorted(live_cdli_keys)}, not {expected_cdli_key}")
            claim_ids = matching_claim_ids(entity, prop, old_qid)
            if not claim_ids:
                raise RuntimeError(f"No matching {prop} {old_qid} claim found on {qid}")
            remove_claims(session, token, claim_ids, summary)
            new_claim_id = create_item_claim(session, token, qid, prop, new_qid, summary)
            status = "written"
            error = ""
            print(f"repaired {qid}: {prop} {old_qid} -> {new_qid}", flush=True)
        except Exception as exc:
            status = "error"
            error = f"{type(exc).__name__}: {exc}"[:500]
            new_claim_id = ""
            claim_ids = []
            print(f"row error {qid}: {error}", flush=True)
            if not args.continue_on_row_error:
                raise
        out_rows.append(
            {
                **{col: clean(row.get(col)) for col in repairs.columns},
                "removed_claim_ids": " | ".join(claim_ids),
                "new_claim_id": new_claim_id,
                "write_status": status,
                "write_error": error,
            }
        )
        args.results.parent.mkdir(parents=True, exist_ok=True)
        pd.concat([results, pd.DataFrame(out_rows)], ignore_index=True).to_csv(args.results, index=False)
        time.sleep(args.sleep)


if __name__ == "__main__":
    main()
