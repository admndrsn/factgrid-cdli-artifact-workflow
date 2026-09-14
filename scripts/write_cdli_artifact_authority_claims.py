#!/usr/bin/env python3
"""Write item-valued CDLI artifact claims after authority Q-items exist.

The first artifact pilot writes only scalar/external-id claims. This script
adds the authority-backed item claims such as instance of, material, period,
language, finding spot, present holding, and type of work.
"""

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
DEFAULT_STATEMENTS = WORKFLOW_ROOT / "published" / "pilots" / "cdli_artifact_statement_staging_pilot_10000_with_lookups.csv"
DEFAULT_AUTHORITY_RESULTS = WORKFLOW_ROOT / "published" / "pilots" / "cdli_authority_item_results_pilot_10000.csv"
DEFAULT_ARTIFACT_RESULTS = WORKFLOW_ROOT / "published" / "pilots" / "cdli_artifact_write_pilot_results.csv"
DEFAULT_PLAN = WORKFLOW_ROOT / "published" / "pilots" / "cdli_artifact_authority_claim_plan_pilot_10000.csv"
DEFAULT_RESULTS = WORKFLOW_ROOT / "published" / "pilots" / "cdli_artifact_authority_claim_results_pilot_10000.csv"
DEFAULT_AUTHORITY_OVERRIDES = WORKFLOW_ROOT / "inputs" / "authority_qid_overrides.csv"
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


def authority_map(authority: pd.DataFrame, overrides: pd.DataFrame | None = None) -> dict[str, str]:
    out = {
        clean(row.factgrid_qid): clean(row.tw_qid)
        for row in authority.itertuples(index=False)
        if clean(getattr(row, "factgrid_qid", "")) and clean(getattr(row, "tw_qid", ""))
    }
    if overrides is not None and not overrides.empty:
        for row in overrides.itertuples(index=False):
            status = clean(getattr(row, "review_status", "approved")).casefold()
            if status not in {"approved", "yes", "y", "ready"}:
                continue
            factgrid_qid = clean(getattr(row, "factgrid_qid", ""))
            tokenworks_qid = clean(getattr(row, "tokenworks_qid", ""))
            if factgrid_qid and tokenworks_qid:
                out[factgrid_qid] = tokenworks_qid
    return out


def build_plan(args: argparse.Namespace) -> pd.DataFrame:
    statements = load_csv(args.statements)
    authority = load_csv(args.authority_results)
    authority_overrides = load_csv(args.authority_overrides)
    artifacts = load_csv(args.artifact_results)
    previous = load_csv(args.results)
    if statements.empty:
        raise RuntimeError(f"No statement rows found in {args.statements}")
    if authority.empty:
        raise RuntimeError(f"No authority rows found in {args.authority_results}")
    if artifacts.empty:
        raise RuntimeError(f"No artifact write results found in {args.artifact_results}")

    fg_to_tw = authority_map(authority, authority_overrides)
    if not fg_to_tw:
        raise RuntimeError(
            f"No authority TokenWorks QIDs found in {args.authority_results}. "
            "Run write_cdli_authority_items.py first."
        )

    written_artifacts = artifacts[artifacts["write_status"].eq("written")].copy()
    if args.limit_artifacts:
        written_artifacts = written_artifacts.head(args.limit_artifacts).copy()
    artifact_qids = set(written_artifacts["tw_qid"].map(clean))
    artifact_labels = {
        clean(row.tw_qid): clean(row.artifact_label)
        for row in written_artifacts.itertuples(index=False)
        if clean(getattr(row, "tw_qid", ""))
    }

    plan = statements[
        statements["tw_qid"].map(clean).isin(artifact_qids)
        & statements["datatype"].eq("wikibase-item")
        & statements["plan_status"].eq("ready")
    ].copy()
    if args.only_field_names:
        fields = {clean(part) for part in args.only_field_names.split(",") if clean(part)}
        plan = plan[plan["field_name"].isin(fields)].copy()

    plan["factgrid_value_qid"] = plan["value"].map(clean)
    plan["tokenworks_value_qid"] = plan["factgrid_value_qid"].map(fg_to_tw).fillna("")
    plan["artifact_label"] = plan["tw_qid"].map(artifact_labels).fillna(plan.get("artifact_label", ""))
    plan["claim_status"] = plan["tokenworks_value_qid"].map(lambda value: "ready" if clean(value) else "missing_authority_tw_qid")
    if not previous.empty and {"tw_qid", "field_name", "tokenworks_value_qid", "write_status"}.issubset(previous.columns):
        written_keys = set(
            zip(
                previous.loc[previous["write_status"].eq("written"), "tw_qid"].map(clean),
                previous.loc[previous["write_status"].eq("written"), "field_name"].map(clean),
                previous.loc[previous["write_status"].eq("written"), "tokenworks_value_qid"].map(clean),
            )
        )
        plan = plan[
            ~plan.apply(
                lambda row: (clean(row["tw_qid"]), clean(row["field_name"]), clean(row["tokenworks_value_qid"])) in written_keys,
                axis=1,
            )
        ].copy()

    args.plan.parent.mkdir(parents=True, exist_ok=True)
    plan.to_csv(args.plan, index=False)
    return plan


def add_claims_to_item(wbi: WikibaseIntegrator, qid: str, rows: pd.DataFrame) -> int:
    item = wbi.item.get(entity_id=qid)
    count = 0
    for _, row in rows.iterrows():
        prop = clean(row.get("tw_pid"))
        value = clean(row.get("tokenworks_value_qid"))
        if not prop or not value:
            continue
        item.claims.add(datatypes.Item(prop_nr=prop, value=value), action_if_exists=ActionIfExists.APPEND_OR_REPLACE)
        count += 1
    if count:
        robust_write(item, f"Add CDLI authority claims to {qid}")
    return count


def write_claims(args: argparse.Namespace) -> pd.DataFrame:
    plan = build_plan(args)
    ready = plan[plan["claim_status"].eq("ready")].copy()
    if args.limit_claims:
        ready = ready.head(args.limit_claims).copy()
    print(f"authority claims ready to write: {len(ready)}")
    if len(plan):
        print("\nPlan summary:")
        print(plan.groupby(["field_name", "claim_status"]).size().reset_index(name="count").to_string(index=False))
    preview_cols = ["cdli_id", "tw_qid", "artifact_label", "field_name", "tw_pid", "value_label", "tokenworks_value_qid"]
    if len(ready):
        print("\nPreview:")
        print(ready[[col for col in preview_cols if col in ready.columns]].head(args.preview).to_string(index=False))

    args.results.parent.mkdir(parents=True, exist_ok=True)
    if args.dry_run:
        print("\nDRY_RUN: no artifact authority claims written.")
        return plan

    results = load_csv(args.results)
    rows = []
    wbi = api_login()
    for qid, group in tqdm(list(ready.groupby("tw_qid", sort=False))):
        try:
            count = add_claims_to_item(wbi, clean(qid), group)
            for _, row in group.iterrows():
                rows.append(
                    {
                        "cdli_id": clean(row.get("cdli_id")),
                        "tw_qid": clean(row.get("tw_qid")),
                        "artifact_label": clean(row.get("artifact_label")),
                        "field_name": clean(row.get("field_name")),
                        "tw_pid": clean(row.get("tw_pid")),
                        "factgrid_value_qid": clean(row.get("factgrid_value_qid")),
                        "tokenworks_value_qid": clean(row.get("tokenworks_value_qid")),
                        "value_label": clean(row.get("value_label")),
                        "write_status": "written",
                        "write_error": "",
                    }
                )
            print(f"updated {qid} — {count} authority claims", flush=True)
            time.sleep(args.sleep)
        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"[:500]
            for _, row in group.iterrows():
                rows.append(
                    {
                        "cdli_id": clean(row.get("cdli_id")),
                        "tw_qid": clean(row.get("tw_qid")),
                        "artifact_label": clean(row.get("artifact_label")),
                        "field_name": clean(row.get("field_name")),
                        "tw_pid": clean(row.get("tw_pid")),
                        "factgrid_value_qid": clean(row.get("factgrid_value_qid")),
                        "tokenworks_value_qid": clean(row.get("tokenworks_value_qid")),
                        "value_label": clean(row.get("value_label")),
                        "write_status": "error",
                        "write_error": message,
                    }
                )
            print(f"row error: {qid} — {message}", flush=True)
            if not args.continue_on_row_error:
                pd.concat([results, pd.DataFrame(rows)], ignore_index=True).drop_duplicates(
                    ["tw_qid", "field_name", "tokenworks_value_qid"], keep="last"
                ).to_csv(args.results, index=False)
                raise
            time.sleep(args.sleep)
        finally:
            pd.concat([results, pd.DataFrame(rows)], ignore_index=True).drop_duplicates(
                ["tw_qid", "field_name", "tokenworks_value_qid"], keep="last"
            ).to_csv(args.results, index=False)
    return pd.concat([results, pd.DataFrame(rows)], ignore_index=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--statements", type=Path, default=DEFAULT_STATEMENTS)
    parser.add_argument("--authority-results", type=Path, default=DEFAULT_AUTHORITY_RESULTS)
    parser.add_argument("--authority-overrides", type=Path, default=DEFAULT_AUTHORITY_OVERRIDES)
    parser.add_argument("--artifact-results", type=Path, default=DEFAULT_ARTIFACT_RESULTS)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--limit-artifacts", type=int, default=10)
    parser.add_argument("--limit-claims", type=int, default=0)
    parser.add_argument("--preview", type=int, default=40)
    parser.add_argument("--sleep", type=float, default=2.0)
    parser.add_argument("--only-field-names", default="")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--continue-on-row-error", action="store_true")
    args = parser.parse_args()
    write_claims(args)


if __name__ == "__main__":
    main()
