#!/usr/bin/env python3
"""Create small missing FactGrid-equivalent properties in TokenWorks."""

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
DEFAULT_RESULTS = WORKFLOW_ROOT / "published" / "factgrid_model_samples" / "tw_missing_factgrid_property_results.csv"
TW_API = "https://wikibase.tk-wiki-kg.com/w/api.php"
FACTGRID_PROPERTY_QID = "Q2"
FACTGRID_PROPERTY_PID = "P5"
INSTANCE_OF_PID = "P2"

PROPERTIES = [
    {
        "property_label": "Naming",
        "property_aliases": "Name | Named as | Local name",
        "property_description": "name recorded for an entity in a particular language or script; equivalent to FactGrid P34",
        "datatype": "monolingualtext",
        "factgrid_pid": "P34",
    },
    {
        "property_label": "CDLI ID2",
        "property_aliases": "CDLI place ID | CDLI geography ID | CDLI locality ID",
        "property_description": "CDLI identifier used for localities or proveniences; equivalent to FactGrid P694",
        "datatype": "external-id",
        "factgrid_pid": "P694",
    },
]


def clean(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null"}:
        return ""
    return text


def split_aliases(value: object) -> list[str]:
    seen = set()
    out = []
    for part in clean(value).split("|"):
        alias = clean(part)
        if alias and alias not in seen:
            out.append(alias[:250])
            seen.add(alias)
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


def seed_rows(results_path: Path) -> pd.DataFrame:
    if results_path.exists():
        existing = pd.read_csv(results_path, dtype=str).fillna("")
    else:
        existing = pd.DataFrame()

    by_fg_pid = {}
    if not existing.empty and "factgrid_pid" in existing.columns:
        by_fg_pid = {clean(row.get("factgrid_pid")): row.to_dict() for _, row in existing.iterrows()}

    rows = []
    for prop in PROPERTIES:
        row = dict(prop)
        row.update(
            {
                "created_tw_pid": "",
                "create_status": "",
                "create_error": "",
                "statement_status": "",
                "statement_error": "",
            }
        )
        row.update(by_fg_pid.get(prop["factgrid_pid"], {}))
        rows.append(row)
    return pd.DataFrame(rows)


def create_property(wbi: WikibaseIntegrator, row: pd.Series):
    prop = wbi.property.new(datatype=clean(row.get("datatype")))
    label = clean(row.get("property_label"))
    description = clean(row.get("property_description"))
    prop.labels.set(language="en", value=label[:250])
    if description:
        prop.descriptions.set(language="en", value=description[:250])
    aliases = split_aliases(row.get("property_aliases"))
    if aliases:
        prop.aliases.set(language="en", values=aliases, action_if_exists=ActionIfExists.APPEND_OR_REPLACE)
    prop.claims.add(
        datatypes.Item(prop_nr=INSTANCE_OF_PID, value=FACTGRID_PROPERTY_QID),
        action_if_exists=ActionIfExists.APPEND_OR_REPLACE,
    )
    prop.claims.add(
        datatypes.ExternalID(prop_nr=FACTGRID_PROPERTY_PID, value=clean(row.get("factgrid_pid"))),
        action_if_exists=ActionIfExists.APPEND_OR_REPLACE,
    )
    return robust_write(prop, f"Create TokenWorks FactGrid-equivalent property: {label}")


def write_properties(args: argparse.Namespace) -> pd.DataFrame:
    rows = seed_rows(args.results)
    candidates = rows[rows["created_tw_pid"].map(clean).eq("")].copy()
    if args.limit:
        candidates = candidates.head(args.limit).copy()

    print(f"missing FactGrid-equivalent properties to create: {len(candidates)}")
    print(candidates[["factgrid_pid", "property_label", "datatype", "property_description"]].to_string(index=False))
    args.results.parent.mkdir(parents=True, exist_ok=True)

    if args.dry_run:
        rows.to_csv(args.results, index=False)
        print("DRY_RUN: no TokenWorks properties created.")
        return rows

    wbi = api_login()
    for idx, row in tqdm(candidates.iterrows(), total=len(candidates)):
        try:
            written = create_property(wbi, row)
            rows.at[idx, "created_tw_pid"] = written.id
            rows.at[idx, "create_status"] = "created"
            rows.at[idx, "create_error"] = ""
            rows.at[idx, "statement_status"] = "written"
            rows.at[idx, "statement_error"] = ""
            print(f"created {written.id} — {clean(row.get('property_label'))}", flush=True)
            time.sleep(args.sleep)
        except Exception as exc:
            rows.at[idx, "create_status"] = "error"
            rows.at[idx, "create_error"] = f"{type(exc).__name__}: {exc}"[:500]
            print(f"create error: {clean(row.get('factgrid_pid'))} — {type(exc).__name__}: {exc}", flush=True)
            if not args.continue_on_row_error:
                raise
            time.sleep(args.sleep)
        finally:
            rows.to_csv(args.results, index=False)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--sleep", type=float, default=2.0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--continue-on-row-error", action="store_true")
    args = parser.parse_args()
    write_properties(args)


if __name__ == "__main__":
    main()
