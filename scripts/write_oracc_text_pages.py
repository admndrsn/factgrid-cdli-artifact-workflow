#!/usr/bin/env python3
"""Write staged ORACC transcript pages and P196 URL claims to TokenWorks."""

from __future__ import annotations

import argparse
import getpass
import os
import time
from pathlib import Path

import pandas as pd
import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from tqdm.auto import tqdm
from wikibaseintegrator import WikibaseIntegrator, datatypes
from wikibaseintegrator.wbi_config import config
from wikibaseintegrator.wbi_enums import ActionIfExists
from wikibaseintegrator.wbi_login import Login


WORKFLOW_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STAGING = WORKFLOW_ROOT / "published" / "oracc_text_pages" / "oracc_text_page_staging.csv"
DEFAULT_RESULTS = WORKFLOW_ROOT / "published" / "oracc_text_pages" / "oracc_text_page_write_results.csv"
TW_API = "https://wikibase.tk-wiki-kg.com/w/api.php"


def clean(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null"}:
        return ""
    if text.endswith(".0") and text[:-2].isdigit():
        return text[:-2]
    return text


def api_login() -> tuple[Login, WikibaseIntegrator]:
    username = os.environ.get("TW_USER") or input("TokenWorks username: ")
    password = os.environ.get("TW_PASS") or getpass.getpass("TokenWorks password: ")
    config["MEDIAWIKI_API_URL"] = TW_API
    config["PROPERTY_CONSTRAINTS_CHECK"] = False
    login = Login(user=username, password=password)
    return login, WikibaseIntegrator(login=login)


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, low_memory=False).fillna("")


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=5, max=60),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def robust_entity_write(entity, summary: str):
    return entity.write(summary=summary)


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=5, max=60),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def edit_page(login: Login, title: str, text: str, summary: str) -> None:
    session = login.get_session()
    response = session.post(
        TW_API,
        data={
            "action": "edit",
            "title": title,
            "text": text,
            "summary": summary,
            "token": login.get_edit_token(),
            "format": "json",
            "utf8": "1",
        },
        timeout=120,
    )
    response.raise_for_status()
    payload = response.json()
    if "error" in payload:
        raise RuntimeError(payload["error"])
    if payload.get("edit", {}).get("result") != "Success":
        raise RuntimeError(payload)


def add_p196_claim(wbi: WikibaseIntegrator, qid: str, prop: str, page_url: str) -> None:
    item = wbi.item.get(entity_id=qid)
    item.claims.add(
        datatypes.URL(prop_nr=prop, value=page_url),
        action_if_exists=ActionIfExists.APPEND_OR_REPLACE,
    )
    robust_entity_write(item, f"Add ORACC transcript page link to {qid}")


def build_plan(args: argparse.Namespace) -> pd.DataFrame:
    staging = load_csv(args.staging)
    if staging.empty:
        raise RuntimeError(f"No ORACC text page staging rows found in {args.staging}")

    required = {"tw_qid", "page_title", "page_url", "page_path", "p196_property"}
    missing = required - set(staging.columns)
    if missing:
        raise RuntimeError(f"Staging file is missing columns: {', '.join(sorted(missing))}")

    plan = staging.copy()
    previous = load_csv(args.results)
    if not previous.empty and {"tw_qid", "page_url", "write_status"}.issubset(previous.columns):
        written_keys = set(
            zip(
                previous.loc[previous["write_status"].eq("written"), "tw_qid"].map(clean),
                previous.loc[previous["write_status"].eq("written"), "page_url"].map(clean),
            )
        )
        plan = plan[
            ~plan.apply(lambda row: (clean(row.get("tw_qid")), clean(row.get("page_url"))) in written_keys, axis=1)
        ].copy()

    if args.limit:
        plan = plan.head(args.limit).copy()
    return plan


def write_pages(args: argparse.Namespace) -> pd.DataFrame:
    plan = build_plan(args)
    print(f"ORACC text pages to write: {len(plan)}")
    if len(plan):
        print(
            plan[
                ["cdli_id", "tw_qid", "artifact_label", "page_title", "page_url", "token_count", "line_count"]
            ]
            .head(args.preview)
            .to_string(index=False)
        )

    if args.dry_run:
        print("\nDRY_RUN: no wiki pages or P196 claims written.")
        return plan

    args.results.parent.mkdir(parents=True, exist_ok=True)
    previous = load_csv(args.results)
    rows = []
    login, wbi = api_login()

    for _, row in tqdm(plan.iterrows(), total=len(plan)):
        result = row.to_dict()
        qid = clean(row.get("tw_qid"))
        page_title = clean(row.get("page_title"))
        page_url = clean(row.get("page_url"))
        page_path = Path(clean(row.get("page_path")))
        prop = clean(row.get("p196_property")) or "P196"
        try:
            if not args.skip_page_write:
                text = page_path.read_text(encoding="utf-8")
                edit_page(login, page_title, text, f"Create ORACC transcript page for {qid}")
                result["page_write_status"] = "written"
            else:
                result["page_write_status"] = "skipped"

            if not args.skip_p196_claim:
                add_p196_claim(wbi, qid, prop, page_url)
                result["p196_write_status"] = "written"
            else:
                result["p196_write_status"] = "skipped"

            result["write_status"] = "written"
            result["write_error"] = ""
            print(f"written: {page_title} -> {qid} {prop}", flush=True)
        except Exception as exc:
            result["write_status"] = "error"
            result["write_error"] = f"{type(exc).__name__}: {exc}"[:500]
            print(f"row error: {page_title} / {qid} — {result['write_error']}", flush=True)
            rows.append(result)
            combined = pd.concat([previous, pd.DataFrame(rows)], ignore_index=True)
            combined.to_csv(args.results, index=False)
            if not args.continue_on_row_error:
                raise
            time.sleep(args.sleep)
            continue

        rows.append(result)
        combined = pd.concat([previous, pd.DataFrame(rows)], ignore_index=True)
        combined.to_csv(args.results, index=False)
        time.sleep(args.sleep)

    return pd.concat([previous, pd.DataFrame(rows)], ignore_index=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staging", type=Path, default=DEFAULT_STAGING)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--preview", type=int, default=10)
    parser.add_argument("--sleep", type=float, default=2.0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-page-write", action="store_true")
    parser.add_argument("--skip-p196-claim", action="store_true")
    parser.add_argument("--continue-on-row-error", action="store_true")
    args = parser.parse_args()
    write_pages(args)


if __name__ == "__main__":
    main()
