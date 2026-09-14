#!/usr/bin/env python3
"""Replace noisy FactGrid CDLI artifact aliases with complete aliases only.

Earlier artifact writes used `publication_designations` and `exact_references`
as independent aliases. That produced noisy fragments such as `UET 2` and `70`
instead of a complete alias like `UET 2, 70`. This repair recomputes aliases
from the CDLI artifact staging and replaces the English alias list on already
created FactGrid items.
"""

from __future__ import annotations

import argparse
import getpass
import logging
import os
import re
import time
from pathlib import Path

import pandas as pd
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from tqdm.auto import tqdm
from wikibaseintegrator import WikibaseIntegrator
from wikibaseintegrator.wbi_config import config
from wikibaseintegrator.wbi_enums import ActionIfExists
from wikibaseintegrator.wbi_login import Login

from write_cdli_new_artifact_items import alias_values, artifact_label_for, clean


WORKFLOW_ROOT = Path(__file__).resolve().parents[1]
PILOT_ROOT = WORKFLOW_ROOT / "published" / "pilots"
DEFAULT_ARTIFACTS = PILOT_ROOT / "cdli_artifact_staging_tranche_10001_35000.csv"
DEFAULT_RESULTS = PILOT_ROOT / "factgrid_cdli_artifact_write_results_tranche_10001_35000.csv"
DEFAULT_OUTPUT = PILOT_ROOT / "factgrid_cdli_artifact_alias_repair_results_tranche_10001_35000.csv"
FACTGRID_API = "https://database.factgrid.de/w/api.php"


def read_csv(path: str | Path) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p, dtype=str, low_memory=False).fillna("")


def api_login() -> WikibaseIntegrator:
    username = os.environ.get("FG_USER") or input("FactGrid username: ")
    password = os.environ.get("FG_PASS") or getpass.getpass("FactGrid password: ")
    config["MEDIAWIKI_API_URL"] = FACTGRID_API
    config["PROPERTY_CONSTRAINTS_CHECK"] = False
    logging.getLogger("backoff").setLevel(logging.ERROR)
    login = Login(user=username, password=password, mediawiki_api_url=FACTGRID_API)
    return WikibaseIntegrator(login=login)


@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=2, min=5, max=60), retry=retry_if_exception_type(Exception))
def robust_write(entity, summary: str):
    return entity.write(summary=summary)


def is_fragment_alias(value: object) -> bool:
    text = clean(value)
    if not text:
        return False
    if re.fullmatch(r"\d+[a-z]?", text, flags=re.IGNORECASE):
        return True
    # Series-only publication references such as "UET 2" or "KUB 34".
    if re.fullmatch(r"[A-Z][A-Z0-9./-]{1,12}\s+\d+[A-Z]?", text):
        return True
    return False


def prepare(args: argparse.Namespace) -> pd.DataFrame:
    artifacts = read_csv(args.artifacts)
    results = read_csv(args.results)
    if artifacts.empty:
        raise RuntimeError(f"No artifact rows found in {args.artifacts}")
    if results.empty:
        raise RuntimeError(f"No write result rows found in {args.results}")
    if not {"cdli_id", "factgrid_qid", "write_status"}.issubset(results.columns):
        raise RuntimeError(f"Results must include cdli_id, factgrid_qid, and write_status: {args.results}")

    artifacts["_cdli_id_clean"] = artifacts["cdli_id"].map(clean)
    artifact_by_cdli = {clean(row.get("cdli_id")): row for _, row in artifacts.iterrows()}
    prior = read_csv(args.output)
    done = set()
    if not prior.empty and {"cdli_id", "repair_status"}.issubset(prior.columns):
        done = set(prior.loc[prior["repair_status"].eq("written"), "cdli_id"].map(clean))

    rows = []
    only_cdli_ids = {clean(part) for part in re.split(r"[,;|\s]+", clean(args.only_cdli_ids)) if clean(part)}
    only_factgrid_qids = {clean(part) for part in re.split(r"[,;|\s]+", clean(args.only_factgrid_qids)) if clean(part)}
    for _, result in results.iterrows():
        if clean(result.get("write_status")) != "written":
            continue
        cdli_id = clean(result.get("cdli_id"))
        if only_cdli_ids and cdli_id not in only_cdli_ids:
            continue
        if cdli_id in done:
            continue
        factgrid_qid = clean(result.get("factgrid_qid"))
        if only_factgrid_qids and factgrid_qid not in only_factgrid_qids:
            continue
        if not re.fullmatch(r"Q\d+", factgrid_qid):
            continue
        artifact = artifact_by_cdli.get(cdli_id)
        if artifact is None:
            continue
        aliases = alias_values(artifact)
        removed_preview = [
            value
            for value in str(artifact.get("publication_designations", "")).split("|") + str(artifact.get("exact_references", "")).split("|")
            if is_fragment_alias(value) and clean(value) not in aliases
        ]
        rows.append(
            {
                "cdli_id": cdli_id,
                "factgrid_qid": factgrid_qid,
                "artifact_label": clean(result.get("artifact_label")) or artifact_label_for(artifact),
                "clean_aliases_en": " | ".join(aliases),
                "fragment_aliases_removed_preview": " | ".join(dict.fromkeys(clean(v) for v in removed_preview if clean(v))),
                "repair_status": "",
                "repair_error": "",
            }
        )

    out = pd.DataFrame(rows)
    if args.only_with_fragment_preview and not out.empty:
        out = out[out["fragment_aliases_removed_preview"].map(clean).ne("")].copy()
    if args.limit:
        out = out.head(args.limit).copy()
    return out


def repair_aliases(args: argparse.Namespace) -> pd.DataFrame:
    work = prepare(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    print(f"FactGrid alias repairs selected: {len(work)}")
    if len(work):
        print(
            work[["cdli_id", "factgrid_qid", "artifact_label", "clean_aliases_en", "fragment_aliases_removed_preview"]]
            .head(args.preview)
            .to_string(index=False)
        )
    if not args.write:
        print("DRY_RUN: no FactGrid aliases changed. Pass --write to repair aliases.")
        work.to_csv(args.output, index=False)
        return work

    prior = read_csv(args.output)
    if not prior.empty:
        prior = prior[prior["repair_status"].eq("written")].copy()
    wbi = api_login()
    written_rows = []
    for _, row in tqdm(work.iterrows(), total=len(work)):
        try:
            qid = clean(row.get("factgrid_qid"))
            aliases = [clean(part)[:250] for part in clean(row.get("clean_aliases_en")).split("|") if clean(part)]
            item = wbi.item.get(qid)
            item.aliases.set(language="en", values=aliases, action_if_exists=ActionIfExists.REPLACE_ALL)
            robust_write(item, f"Repair CDLI artifact aliases: {qid}")
            row = row.copy()
            row["repair_status"] = "written"
            row["repair_error"] = ""
            print(f"repaired aliases: {qid} — {clean(row.get('artifact_label'))}", flush=True)
        except Exception as exc:
            row = row.copy()
            row["repair_status"] = "error"
            row["repair_error"] = f"{type(exc).__name__}: {exc}"[:500]
            print(f"alias repair error: {clean(row.get('factgrid_qid'))} — {type(exc).__name__}: {exc}", flush=True)
            if not args.continue_on_row_error:
                written_rows.append(dict(row))
                pd.concat([prior, pd.DataFrame(written_rows)], ignore_index=True).drop_duplicates(["cdli_id"], keep="last").to_csv(args.output, index=False)
                raise
        finally:
            written_rows.append(dict(row))
            pd.concat([prior, pd.DataFrame(written_rows)], ignore_index=True).drop_duplicates(["cdli_id"], keep="last").to_csv(args.output, index=False)
            time.sleep(args.sleep)
    return pd.concat([prior, pd.DataFrame(written_rows)], ignore_index=True).drop_duplicates(["cdli_id"], keep="last")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, default=DEFAULT_ARTIFACTS)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--preview", type=int, default=20)
    parser.add_argument("--sleep", type=float, default=1.5)
    parser.add_argument("--only-cdli-ids", default="")
    parser.add_argument("--only-factgrid-qids", default="")
    parser.add_argument("--only-with-fragment-preview", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--continue-on-row-error", action="store_true")
    args = parser.parse_args()
    repair_aliases(args)


if __name__ == "__main__":
    main()
