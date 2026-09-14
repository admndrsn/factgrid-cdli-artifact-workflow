#!/usr/bin/env python3
"""Create TokenWorks authority Q-items for CDLI artifact statement values."""

from __future__ import annotations

import argparse
import getpass
import os
import time
from pathlib import Path

import pandas as pd
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from tqdm.auto import tqdm
from wikibaseintegrator import WikibaseIntegrator, datatypes
from wikibaseintegrator.wbi_config import config
from wikibaseintegrator.wbi_enums import ActionIfExists
from wikibaseintegrator.wbi_login import Login


WORKFLOW_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ITEMS = WORKFLOW_ROOT / "published" / "pilots" / "cdli_authority_item_staging_pilot_10000.csv"
DEFAULT_RESULTS = WORKFLOW_ROOT / "published" / "pilots" / "cdli_authority_item_results_pilot_10000.csv"
TW_API = "https://wikibase.tk-wiki-kg.com/w/api.php"
FACTGRID_ITEM_ID_PROPERTY = "P378"


def clean(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null"}:
        return ""
    if text.endswith(".0") and text[:-2].isdigit():
        return text[:-2]
    return text


def split_aliases(value: object) -> list[str]:
    seen = set()
    out = []
    for part in clean(value).split("|"):
        text = clean(part)
        if not text or text in seen:
            continue
        out.append(text[:250])
        seen.add(text)
    return out


def api_login() -> WikibaseIntegrator:
    username = os.environ.get("TW_USER") or input("TokenWorks username: ")
    password = os.environ.get("TW_PASS") or getpass.getpass("TokenWorks password: ")
    config["MEDIAWIKI_API_URL"] = TW_API
    config["PROPERTY_CONSTRAINTS_CHECK"] = False
    login = Login(user=username, password=password)
    return WikibaseIntegrator(login=login)


@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=2, min=5, max=60), retry=retry_if_exception_type(Exception))
def robust_write(entity, summary: str):
    return entity.write(summary=summary)


def load_items(args: argparse.Namespace) -> pd.DataFrame:
    items = pd.read_csv(args.items, dtype=str).fillna("")
    if args.results.exists():
        previous = pd.read_csv(args.results, dtype=str).fillna("")
        if "factgrid_qid" not in previous.columns:
            raise RuntimeError(f"Authority results missing factgrid_qid column: {args.results}")
        for col in previous.columns:
            if col not in items.columns:
                items[col] = ""
        previous_by_qid = {clean(row.get("factgrid_qid")): row for _, row in previous.iterrows()}
        for idx, row in items.iterrows():
            factgrid_qid = clean(row.get("factgrid_qid"))
            prior = previous_by_qid.get(factgrid_qid)
            if prior is None:
                continue
            for col in ["tw_qid", "create_status", "create_error"]:
                if col in prior.index and clean(prior.get(col)):
                    items.at[idx, col] = clean(prior.get(col))
    for col in ["tw_qid", "create_status", "create_error"]:
        if col not in items.columns:
            items[col] = ""
    return items


def create_item(wbi: WikibaseIntegrator, row: pd.Series, include_factgrid_id: bool = True):
    item = wbi.item.new()
    label = clean(row.get("label_en"))
    description = clean(row.get("description_en"))
    if not label:
        raise ValueError(f"Missing label for {clean(row.get('factgrid_qid'))}")
    item.labels.set(language="en", value=label[:250])
    if description:
        item.descriptions.set(language="en", value=description[:250])
    aliases = split_aliases(row.get("aliases_en"))
    if aliases:
        item.aliases.set(language="en", values=aliases, action_if_exists=ActionIfExists.APPEND_OR_REPLACE)
    factgrid_qid = clean(row.get("factgrid_qid"))
    if factgrid_qid and include_factgrid_id:
        item.claims.add(
            datatypes.ExternalID(prop_nr=FACTGRID_ITEM_ID_PROPERTY, value=factgrid_qid),
            action_if_exists=ActionIfExists.APPEND_OR_REPLACE,
        )
    return robust_write(item, f"Create TokenWorks CDLI authority value: {label}")


def write_items(args: argparse.Namespace) -> pd.DataFrame:
    items = load_items(args)
    candidates = items[items["tw_qid"].map(clean).eq("") & items["create_status"].isin(["", "not_started", "error"])].copy()
    if args.limit:
        candidates = candidates.head(args.limit).copy()

    print(f"authority items to create: {len(candidates)}")
    preview_cols = ["factgrid_qid", "label_en", "description_en", "source_fields", "source_count", "source_cdli_count"]
    if len(candidates):
        print(candidates[[col for col in preview_cols if col in candidates.columns]].head(args.preview).to_string(index=False))

    args.results.parent.mkdir(parents=True, exist_ok=True)
    if args.dry_run:
        print("DRY_RUN: no authority items created.")
        items.to_csv(args.results, index=False)
        return items

    wbi = api_login()
    for idx, row in tqdm(candidates.iterrows(), total=len(candidates)):
        try:
            print(f"creating authority item: {clean(row.get('factgrid_qid'))} — {clean(row.get('label_en'))}", flush=True)
            written = create_item(wbi, row, include_factgrid_id=not args.skip_factgrid_id_claim)
            items.at[idx, "tw_qid"] = written.id
            items.at[idx, "create_status"] = "created"
            items.at[idx, "create_error"] = ""
            print(f"created {written.id} — {clean(row.get('label_en'))}", flush=True)
            time.sleep(args.sleep)
        except Exception as exc:
            items.at[idx, "create_status"] = "error"
            items.at[idx, "create_error"] = f"{type(exc).__name__}: {exc}"[:500]
            items.to_csv(args.results, index=False)
            print(f"create error: {clean(row.get('factgrid_qid'))} — {type(exc).__name__}: {exc}", flush=True)
            if not args.continue_on_row_error:
                raise
            time.sleep(args.sleep)
        finally:
            items.to_csv(args.results, index=False)
    return items


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--items", type=Path, default=DEFAULT_ITEMS)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--preview", type=int, default=20)
    parser.add_argument("--sleep", type=float, default=1.5)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--continue-on-row-error", action="store_true")
    parser.add_argument(
        "--skip-factgrid-id-claim",
        action="store_true",
        help="Create the item without its P378 FactGrid Item ID claim. Useful for diagnosing generic save failures.",
    )
    args = parser.parse_args()
    write_items(args)


if __name__ == "__main__":
    main()
