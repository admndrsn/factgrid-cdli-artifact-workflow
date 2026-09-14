#!/usr/bin/env python3
"""Write ready staged claims onto TokenWorks ORACC project items."""

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
DEFAULT_STAGING = WORKFLOW_ROOT / "published" / "factgrid_model_samples" / "oracc_project_claim_staging.csv"
DEFAULT_PLAN = WORKFLOW_ROOT / "published" / "factgrid_model_samples" / "oracc_project_claim_write_plan.csv"
DEFAULT_RESULTS = WORKFLOW_ROOT / "published" / "factgrid_model_samples" / "oracc_project_claim_write_results.csv"
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


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, low_memory=False).fillna("")


def claim_from_row(row: pd.Series):
    prop = clean(row.get("tokenworks_property_id"))
    datatype = clean(row.get("datatype"))
    if not prop:
        return None
    if datatype == "wikibase-item":
        value = clean(row.get("value_tokenworks_qid"))
        if not value:
            return None
        return datatypes.Item(prop_nr=prop, value=value)
    if datatype == "url":
        value = clean(row.get("value"))
        if not value:
            return None
        return datatypes.URL(prop_nr=prop, value=value)
    if datatype == "time":
        value = clean(row.get("value"))
        if not value:
            return None
        return datatypes.Time(prop_nr=prop, time=f"+{value}-00-00T00:00:00Z", precision=9)
    raise ValueError(f"Unsupported ready ORACC datatype: {datatype}")


def build_plan(args: argparse.Namespace) -> pd.DataFrame:
    staging = load_csv(args.staging)
    previous = load_csv(args.results)
    if staging.empty:
        raise RuntimeError(f"No ORACC claim staging rows found in {args.staging}")

    plan = staging[
        staging["claim_status"].eq("ready")
        & staging["project_tokenworks_qid"].map(clean).ne("")
        & staging["tokenworks_property_id"].map(clean).ne("")
    ].copy()
    if args.only_source_columns:
        allowed = {clean(part) for part in args.only_source_columns.split(",") if clean(part)}
        plan = plan[plan["source_column"].isin(allowed)].copy()

    if not previous.empty and {"project_tokenworks_qid", "source_column", "tokenworks_property_id", "value", "value_tokenworks_qid", "write_status"}.issubset(previous.columns):
        written_keys = set(
            zip(
                previous.loc[previous["write_status"].eq("written"), "project_tokenworks_qid"].map(clean),
                previous.loc[previous["write_status"].eq("written"), "source_column"].map(clean),
                previous.loc[previous["write_status"].eq("written"), "tokenworks_property_id"].map(clean),
                previous.loc[previous["write_status"].eq("written"), "value"].map(clean),
                previous.loc[previous["write_status"].eq("written"), "value_tokenworks_qid"].map(clean),
            )
        )
        plan = plan[
            ~plan.apply(
                lambda row: (
                    clean(row.get("project_tokenworks_qid")),
                    clean(row.get("source_column")),
                    clean(row.get("tokenworks_property_id")),
                    clean(row.get("value")),
                    clean(row.get("value_tokenworks_qid")),
                )
                in written_keys,
                axis=1,
            )
        ].copy()

    if args.limit_claims:
        plan = plan.head(args.limit_claims).copy()

    args.plan.parent.mkdir(parents=True, exist_ok=True)
    plan.to_csv(args.plan, index=False)
    return plan


def add_claims_to_item(wbi: WikibaseIntegrator, qid: str, rows: pd.DataFrame) -> int:
    item = wbi.item.get(entity_id=qid)
    count = 0
    for _, row in rows.iterrows():
        claim = claim_from_row(row)
        if claim is None:
            continue
        item.claims.add(claim, action_if_exists=ActionIfExists.APPEND_OR_REPLACE)
        count += 1
    if count:
        robust_write(item, f"Add ORACC project claims to {qid}")
    return count


def write_claims(args: argparse.Namespace) -> pd.DataFrame:
    plan = build_plan(args)
    print(f"ORACC project claims ready to write: {len(plan)}")
    if len(plan):
        print("\nPlan summary:")
        print(plan.groupby(["source_column", "tokenworks_property_id", "datatype"]).size().reset_index(name="count").to_string(index=False))
        preview_cols = [
            "project_tokenworks_qid",
            "project_label",
            "source_column",
            "tokenworks_property_id",
            "tokenworks_property_label",
            "datatype",
            "value",
            "value_tokenworks_qid",
        ]
        print("\nPreview:")
        print(plan[[col for col in preview_cols if col in plan.columns]].head(args.preview).to_string(index=False))

    if args.dry_run:
        print("\nDRY_RUN: no ORACC project claims written.")
        return plan

    results = load_csv(args.results)
    rows = []
    wbi = api_login()
    for qid, group in tqdm(list(plan.groupby("project_tokenworks_qid", sort=False))):
        try:
            count = add_claims_to_item(wbi, clean(qid), group)
            for _, row in group.iterrows():
                result = row.to_dict()
                result["write_status"] = "written"
                result["write_error"] = ""
                rows.append(result)
            print(f"updated {qid} — {count} ORACC project claims", flush=True)
            time.sleep(args.sleep)
        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"[:500]
            for _, row in group.iterrows():
                result = row.to_dict()
                result["write_status"] = "error"
                result["write_error"] = message
                rows.append(result)
            print(f"row error: {qid} — {message}", flush=True)
            if not args.continue_on_row_error:
                pd.concat([results, pd.DataFrame(rows)], ignore_index=True).drop_duplicates(
                    ["project_tokenworks_qid", "source_column", "tokenworks_property_id", "value", "value_tokenworks_qid"],
                    keep="last",
                ).to_csv(args.results, index=False)
                raise
            time.sleep(args.sleep)
        finally:
            pd.concat([results, pd.DataFrame(rows)], ignore_index=True).drop_duplicates(
                ["project_tokenworks_qid", "source_column", "tokenworks_property_id", "value", "value_tokenworks_qid"],
                keep="last",
            ).to_csv(args.results, index=False)
    return pd.concat([results, pd.DataFrame(rows)], ignore_index=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staging", type=Path, default=DEFAULT_STAGING)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--limit-claims", type=int, default=0)
    parser.add_argument("--preview", type=int, default=40)
    parser.add_argument("--sleep", type=float, default=2.0)
    parser.add_argument("--only-source-columns", default="")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--continue-on-row-error", action="store_true")
    args = parser.parse_args()
    write_claims(args)


if __name__ == "__main__":
    main()
