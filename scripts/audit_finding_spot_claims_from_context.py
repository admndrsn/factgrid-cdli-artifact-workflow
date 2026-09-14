#!/usr/bin/env python3
"""Audit artifact finding-spot claims against their CDLI context strings.

The item-valued finding spot claim (TokenWorks P224) can be wrong when a lookup
row maps a CDLI provenience label to the wrong authority item. The paired
finding-spot context string (TokenWorks P394) preserves the original CDLI
provenience label, so this script uses that string as the source key and
compares written P224 claims with the expected authority QID.

This script does not edit TokenWorks.
"""

from __future__ import annotations

import argparse
import glob
import re
from pathlib import Path

import pandas as pd


WORKFLOW_ROOT = Path(__file__).resolve().parents[1]
PILOT_ROOT = WORKFLOW_ROOT / "published" / "pilots"
DEFAULT_STATEMENTS = PILOT_ROOT / "cdli_artifact_statement_staging_pilot_10000_with_lookups.csv"
DEFAULT_AUTHORITY_RESULTS = PILOT_ROOT / "cdli_authority_item_results_pilot_10000.csv"
DEFAULT_AUTHORITY_RESULTS_GLOB = str(PILOT_ROOT / "finding_spot_missing_authority_item_results*.csv")
DEFAULT_AUTHORITY_OVERRIDES = WORKFLOW_ROOT / "inputs" / "authority_qid_overrides.csv"
DEFAULT_RESULTS_GLOB = str(PILOT_ROOT / "cdli_artifact_authority_claim*results*.csv")
DEFAULT_REPAIR_RESULTS_GLOB = str(PILOT_ROOT / "*finding_spot*repair_results.csv")
DEFAULT_PROVENIENCE_LOOKUP = WORKFLOW_ROOT / "inputs" / "cdli_lookup_sources" / "proveniences_FG_AncientSettlement.csv"
DEFAULT_PROVENIENCE_FG_LOOKUP = WORKFLOW_ROOT / "inputs" / "cdli_lookup_sources" / "proveniences_FG_Proveniences.csv"
DEFAULT_PROVENIENCE_ALIASES = WORKFLOW_ROOT / "inputs" / "provenience_aliases_reviewed.csv"
DEFAULT_OUTPUT = PILOT_ROOT / "finding_spot_context_audit.csv"
DEFAULT_SUMMARY = PILOT_ROOT / "finding_spot_context_audit_summary.csv"
FINDING_SPOT_PID = "P224"


def clean(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null"}:
        return ""
    if text.endswith(".0") and text[:-2].isdigit():
        return text[:-2]
    return text


def norm(value: object) -> str:
    return re.sub(r"\s+", " ", clean(value).casefold())


def qid_from_uri(value: object) -> str:
    text = clean(value)
    match = re.search(r"(Q\d+)(?:$|[/?#])", text)
    if match:
        return match.group(1)
    match = re.search(r"(Q\d+)$", text)
    return match.group(1) if match else text


def is_qid(value: object) -> bool:
    return bool(re.fullmatch(r"Q\d+", clean(value)))


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, low_memory=False).fillna("")


def load_glob(pattern: str) -> pd.DataFrame:
    frames = []
    for filename in sorted(glob.glob(pattern)):
        df = load_csv(Path(filename))
        if df.empty:
            continue
        df["source_results_file"] = filename
        frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def first_existing(df: pd.DataFrame, names: list[str]) -> str:
    lowered = {c.casefold(): c for c in df.columns}
    for name in names:
        if name.casefold() in lowered:
            return lowered[name.casefold()]
    return ""


def existing_columns(df: pd.DataFrame, names: list[str]) -> list[str]:
    lowered = {c.casefold(): c for c in df.columns}
    return [lowered[name.casefold()] for name in names if name.casefold() in lowered]


def promote_header_row_if_needed(df: pd.DataFrame, expected_columns: list[str]) -> pd.DataFrame:
    if df.empty:
        return df
    current = {c.casefold() for c in df.columns}
    if any(col.casefold() in current for col in expected_columns):
        return df
    first_row = [clean(v) for v in df.iloc[0].tolist()]
    first = {v.casefold() for v in first_row if v}
    if not any(col.casefold() in first for col in expected_columns):
        return df
    out = df.iloc[1:].copy()
    out.columns = [value if value else f"unnamed_{i}" for i, value in enumerate(first_row)]
    return out.fillna("")


def make_lookup(path: Path, key_columns: list[str], qid_columns: list[str], label_columns: list[str]) -> dict[str, dict[str, str]]:
    df = load_csv(path)
    if df.empty:
        return {}
    df = promote_header_row_if_needed(df, key_columns + qid_columns + label_columns)
    key_cols = existing_columns(df, key_columns)
    qid_col = first_existing(df, qid_columns)
    label_col = first_existing(df, label_columns)
    if not key_cols or not qid_col:
        return {}
    out: dict[str, dict[str, str]] = {}
    for _, row in df.iterrows():
        qid = qid_from_uri(row.get(qid_col))
        if not is_qid(qid):
            continue
        for key_col in key_cols:
            key = norm(row.get(key_col))
            if not key:
                continue
            out[key] = {
                "factgrid_qid": qid,
                "label": clean(row.get(label_col)) if label_col else clean(row.get(key_col)),
                "source_key": clean(row.get(key_col)),
                "lookup_source": str(path),
            }
    return out


def make_reviewed_alias_lookup(path: Path) -> dict[str, dict[str, str]]:
    df = load_csv(path)
    if df.empty:
        return {}
    source_col = first_existing(df, ["source_value", "alias", "provenience", "value_label"])
    qid_col = first_existing(df, ["factgrid_qid", "FG_qid", "FG-Q", "qid"])
    label_col = first_existing(df, ["factgrid_label", "label", "Len"])
    status_col = first_existing(df, ["review_status", "status"])
    if not source_col or not qid_col:
        return {}
    out: dict[str, dict[str, str]] = {}
    for _, row in df.iterrows():
        status = clean(row.get(status_col)).casefold() if status_col else "approved"
        if status not in {"approved", "yes", "y", "ready"}:
            continue
        key = norm(row.get(source_col))
        qid = qid_from_uri(row.get(qid_col))
        if not key or not is_qid(qid):
            continue
        out[key] = {
            "factgrid_qid": qid,
            "label": clean(row.get(label_col)) if label_col else clean(row.get(source_col)),
            "source_key": clean(row.get(source_col)),
            "lookup_source": str(path),
        }
    return out


def build_provenience_lookup(args: argparse.Namespace) -> dict[str, dict[str, str]]:
    lookup = make_lookup(
        args.provenience_lookup,
        ["provenience", "Len", "Aen", "Aen (update)", "Aen2"],
        ["FG_qid", "FG-Q", "qid"],
        ["Len", "provenience", "Aen", "Aen2"],
    )
    lookup.update(
        make_lookup(
            args.provenience_fg_lookup,
            ["Len", "Aen", "cdli_legacy_'Len'", "transciption_name", "transcription_name", "provenience"],
            ["FG_qid", "ancientplace", "FG_Qid", "FG-Q", "qid"],
            ["Len", "Aen", "cdli_legacy_'Len'", "transciption_name", "transcription_name"],
        )
    )
    lookup.update(make_reviewed_alias_lookup(args.provenience_aliases))
    return lookup


def build_authority_map(authority: pd.DataFrame, overrides: pd.DataFrame) -> dict[str, str]:
    out = {
        clean(row.factgrid_qid): clean(row.tw_qid)
        for row in authority.itertuples(index=False)
        if clean(getattr(row, "factgrid_qid", "")) and clean(getattr(row, "tw_qid", ""))
    }
    if not overrides.empty:
        for row in overrides.itertuples(index=False):
            status = clean(getattr(row, "review_status", "approved")).casefold()
            if status not in {"approved", "yes", "y", "ready"}:
                continue
            factgrid_qid = clean(getattr(row, "factgrid_qid", ""))
            tokenworks_qid = clean(getattr(row, "tokenworks_qid", ""))
            if factgrid_qid and tokenworks_qid:
                out[factgrid_qid] = tokenworks_qid
    return out


def load_authority_results(primary: Path, extra_pattern: str) -> pd.DataFrame:
    frames = []
    primary_df = load_csv(primary)
    if not primary_df.empty:
        frames.append(primary_df)
    extra = load_glob(extra_pattern) if extra_pattern else pd.DataFrame()
    if not extra.empty:
        frames.append(extra)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True).drop_duplicates("factgrid_qid", keep="last")


def build_context_map(statements: pd.DataFrame) -> dict[tuple[str, str], str]:
    if statements.empty or "field_name" not in statements.columns:
        return {}
    context = statements[statements["field_name"].eq("finding_spot_context")].copy()
    return {
        (clean(row.get("cdli_id")), clean(row.get("tw_qid"))): clean(row.get("value"))
        for _, row in context.iterrows()
        if clean(row.get("cdli_id")) and clean(row.get("tw_qid"))
    }


def current_finding_spot_rows(results: pd.DataFrame, repair_results: pd.DataFrame) -> pd.DataFrame:
    if results.empty:
        return pd.DataFrame()
    rows = results[
        results["write_status"].eq("written")
        & results["field_name"].eq("finding_spot")
        & results["tw_pid"].eq(FINDING_SPOT_PID)
    ].copy()
    if rows.empty:
        return rows
    rows["current_tokenworks_value_qid"] = rows["tokenworks_value_qid"].map(clean)
    rows["repair_source_file"] = ""
    if not repair_results.empty and {"tw_qid", "repair_status", "new_tokenworks_value_qid"}.issubset(repair_results.columns):
        written_repairs = repair_results[repair_results["repair_status"].eq("written")].copy()
        repair_by_qid = {
            clean(row.get("tw_qid")): (clean(row.get("new_tokenworks_value_qid")), clean(row.get("source_results_file")))
            for _, row in written_repairs.iterrows()
            if clean(row.get("tw_qid")) and clean(row.get("new_tokenworks_value_qid"))
        }
        for idx, row in rows.iterrows():
            qid = clean(row.get("tw_qid"))
            if qid in repair_by_qid:
                rows.at[idx, "current_tokenworks_value_qid"] = repair_by_qid[qid][0]
                rows.at[idx, "repair_source_file"] = repair_by_qid[qid][1]
    return rows.drop_duplicates(["cdli_id", "tw_qid", "current_tokenworks_value_qid"], keep="last")


def audit(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame]:
    statements = load_csv(args.statements)
    authority = load_authority_results(args.authority_results, args.authority_results_glob)
    overrides = load_csv(args.authority_overrides)
    results = load_glob(args.results_glob)
    repair_results = load_glob(args.repair_results_glob)
    if statements.empty:
        raise RuntimeError(f"No statement staging found in {args.statements}")
    if authority.empty and overrides.empty:
        raise RuntimeError("No authority results or authority overrides found.")
    if results.empty:
        raise RuntimeError(f"No prior finding-spot result rows matched {args.results_glob}")

    context_by_key = build_context_map(statements)
    lookup = build_provenience_lookup(args)
    fg_to_tw = build_authority_map(authority, overrides)
    rows = current_finding_spot_rows(results, repair_results)

    out_rows: list[dict[str, str]] = []
    for _, row in rows.iterrows():
        cdli_id = clean(row.get("cdli_id"))
        tw_qid = clean(row.get("tw_qid"))
        context = context_by_key.get((cdli_id, tw_qid), "")
        expected = lookup.get(norm(context), {}) if context else {}
        expected_fg_qid = clean(expected.get("factgrid_qid"))
        expected_tw_qid = fg_to_tw.get(expected_fg_qid, "")
        current_tw_qid = clean(row.get("current_tokenworks_value_qid"))
        if not context:
            status = "missing_context"
        elif not expected_fg_qid:
            status = "missing_lookup"
        elif not expected_tw_qid:
            status = "missing_expected_tw_qid"
        elif current_tw_qid == expected_tw_qid:
            status = "ok"
        else:
            status = "mismatch"
        out_rows.append(
            {
                "cdli_id": cdli_id,
                "tw_qid": tw_qid,
                "artifact_label": clean(row.get("artifact_label")),
                "finding_spot_context": context,
                "current_tokenworks_value_qid": current_tw_qid,
                "written_value_label": clean(row.get("value_label")),
                "expected_factgrid_qid": expected_fg_qid,
                "expected_tokenworks_qid": expected_tw_qid,
                "expected_label": clean(expected.get("label")),
                "lookup_source": clean(expected.get("lookup_source")),
                "audit_status": status,
                "source_results_file": clean(row.get("source_results_file")),
                "repair_source_file": clean(row.get("repair_source_file")),
            }
        )
    out = pd.DataFrame(out_rows)
    if args.only_status:
        statuses = {clean(part) for part in args.only_status.split(",") if clean(part)}
        out = out[out["audit_status"].isin(statuses)].copy()
    summary = (
        out.groupby("audit_status", dropna=False).size().reset_index(name="count").sort_values(["audit_status"])
        if not out.empty
        else pd.DataFrame(columns=["audit_status", "count"])
    )
    return out, summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--statements", type=Path, default=DEFAULT_STATEMENTS)
    parser.add_argument("--authority-results", type=Path, default=DEFAULT_AUTHORITY_RESULTS)
    parser.add_argument("--authority-results-glob", default=DEFAULT_AUTHORITY_RESULTS_GLOB)
    parser.add_argument("--authority-overrides", type=Path, default=DEFAULT_AUTHORITY_OVERRIDES)
    parser.add_argument("--results-glob", default=DEFAULT_RESULTS_GLOB)
    parser.add_argument("--repair-results-glob", default=DEFAULT_REPAIR_RESULTS_GLOB)
    parser.add_argument("--provenience-lookup", type=Path, default=DEFAULT_PROVENIENCE_LOOKUP)
    parser.add_argument("--provenience-fg-lookup", type=Path, default=DEFAULT_PROVENIENCE_FG_LOOKUP)
    parser.add_argument("--provenience-aliases", type=Path, default=DEFAULT_PROVENIENCE_ALIASES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--only-status", default="")
    parser.add_argument("--preview", type=int, default=30)
    args = parser.parse_args()

    out, summary = audit(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output, index=False)
    summary.to_csv(args.summary, index=False)
    print(summary.to_string(index=False))
    if args.preview and not out.empty:
        print(out.head(args.preview).to_string(index=False))
    print(f"Wrote finding-spot audit -> {args.output}")
    print(f"Wrote summary -> {args.summary}")


if __name__ == "__main__":
    main()
