#!/usr/bin/env python3
"""Repair TokenWorks CDLI ID external IDs to six-digit P-numbers.

CDLI formatter URLs expect values like `P001754`, not `P1754`. This script
targets already-written artifact result CSVs, removes existing TokenWorks
`P223` claims, and adds the normalized six-digit CDLI ID.
"""

from __future__ import annotations

import argparse
import getpass
import os
import re
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
DEFAULT_RESULTS = WORKFLOW_ROOT / "published" / "pilots" / "cdli_id_repair_results.csv"
TW_API = "https://wikibase.tk-wiki-kg.com/w/api.php"
CDLI_ID_PROPERTY = "P223"


def clean(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null"}:
        return ""
    if text.endswith(".0") and text[:-2].isdigit():
        return text[:-2]
    return text


def format_cdli_id(value: object) -> str:
    text = clean(value)
    match = re.search(r"(\d+)", text)
    if not match:
        return text
    return f"P{int(match.group(1)):06d}"


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


def load_result_rows(paths: list[Path]) -> pd.DataFrame:
    frames = []
    for path in paths:
        if path.exists():
            frames.append(pd.read_csv(path, dtype=str, low_memory=False).fillna(""))
    if not frames:
        raise RuntimeError("No input result CSV rows found.")
    rows = pd.concat(frames, ignore_index=True).fillna("")
    rows = rows[rows["write_status"].eq("written")].copy()
    rows = rows[rows["cdli_id"].map(clean).ne("") & rows["tw_qid"].map(clean).ne("")]
    return rows.drop_duplicates(["cdli_id", "tw_qid"], keep="last")


def already_repaired(results_path: Path) -> set[tuple[str, str]]:
    if not results_path.exists():
        return set()
    df = pd.read_csv(results_path, dtype=str).fillna("")
    if "repair_status" not in df.columns:
        return set()
    return set(
        zip(
            df.loc[df["repair_status"].eq("written"), "cdli_id"].map(clean),
            df.loc[df["repair_status"].eq("written"), "tw_qid"].map(clean),
        )
    )


def repair(args: argparse.Namespace) -> pd.DataFrame:
    rows = load_result_rows(args.input_results)
    done = already_repaired(args.results)
    if done:
        rows = rows[~rows.apply(lambda row: (clean(row["cdli_id"]), clean(row["tw_qid"])) in done, axis=1)].copy()
    if args.limit:
        rows = rows.head(args.limit).copy()
    rows["normalized_cdli_id"] = rows["cdli_id"].map(format_cdli_id)

    print(f"CDLI ID claims to repair: {len(rows)}")
    preview_cols = ["cdli_id", "normalized_cdli_id", "tw_qid", "artifact_label"]
    if len(rows):
        print(rows[[col for col in preview_cols if col in rows.columns]].head(args.preview).to_string(index=False))
    args.results.parent.mkdir(parents=True, exist_ok=True)

    if args.dry_run:
        print("DRY_RUN: no CDLI ID claims repaired.")
        return rows

    prior = pd.read_csv(args.results, dtype=str).fillna("") if args.results.exists() else pd.DataFrame()
    out_rows = []
    wbi = api_login()
    for _, row in tqdm(rows.iterrows(), total=len(rows)):
        qid = clean(row.get("tw_qid"))
        cdli_id = clean(row.get("cdli_id"))
        normalized = clean(row.get("normalized_cdli_id"))
        try:
            item = wbi.item.get(entity_id=qid)
            item.claims.remove(CDLI_ID_PROPERTY)
            item.claims.add(
                datatypes.ExternalID(prop_nr=CDLI_ID_PROPERTY, value=normalized),
                action_if_exists=ActionIfExists.APPEND_OR_REPLACE,
            )
            robust_write(item, f"Normalize CDLI ID on {qid} to {normalized}")
            out_rows.append(
                {
                    "cdli_id": cdli_id,
                    "normalized_cdli_id": normalized,
                    "tw_qid": qid,
                    "artifact_label": clean(row.get("artifact_label")),
                    "repair_status": "written",
                    "repair_error": "",
                }
            )
            print(f"repaired {qid}: {normalized}", flush=True)
            time.sleep(args.sleep)
        except Exception as exc:
            out_rows.append(
                {
                    "cdli_id": cdli_id,
                    "normalized_cdli_id": normalized,
                    "tw_qid": qid,
                    "artifact_label": clean(row.get("artifact_label")),
                    "repair_status": "error",
                    "repair_error": f"{type(exc).__name__}: {exc}"[:500],
                }
            )
            print(f"repair error {qid}: {type(exc).__name__}: {exc}", flush=True)
            if not args.continue_on_row_error:
                pd.concat([prior, pd.DataFrame(out_rows)], ignore_index=True).drop_duplicates(["cdli_id", "tw_qid"], keep="last").to_csv(
                    args.results, index=False
                )
                raise
            time.sleep(args.sleep)
        finally:
            pd.concat([prior, pd.DataFrame(out_rows)], ignore_index=True).drop_duplicates(["cdli_id", "tw_qid"], keep="last").to_csv(
                args.results, index=False
            )
    return pd.concat([prior, pd.DataFrame(out_rows)], ignore_index=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-results", type=Path, action="append", required=True)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--preview", type=int, default=20)
    parser.add_argument("--sleep", type=float, default=1.5)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--continue-on-row-error", action="store_true")
    args = parser.parse_args()
    repair(args)


if __name__ == "__main__":
    main()
