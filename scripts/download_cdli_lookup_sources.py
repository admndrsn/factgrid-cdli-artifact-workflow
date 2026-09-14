#!/usr/bin/env python3
"""Download public Google Sheet lookup tabs used by the CDLI artifact workflow.

The source sheets are maintained by the project team. This script only reads
their CSV exports and writes local CSV snapshots so staging and write scripts
can be deterministic.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import requests


WORKFLOW_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = WORKFLOW_ROOT / "inputs" / "cdli_lookup_sources"

LOD_TABLET_DICTIONARY_ID = "107ly4G5j3im6Hbifqw1HaB66zuqzf7ijN6q8A-WvH8s"
WORKING_FACTGRID_DF_ID = "13XuuZFbQy7uuE7TMsugV5kisrsrLts4b9cECN8JGjLw"
FG_CDLI_ID_FILE_ID = "1ev2kW40CmKwM_Zo3m4fN-EkobG7nwLpE"
PROVENIENCES_TO_ADD_ID = "1AecM85Mx9w3-zwMXoBANmxBsUzJT69zuG_O8OlGDVyQ"
ORACC_PROJECTS_ID = "1oQ3d-TVxcVHzwGiQmuHZKUUr9GNRmKqE3KgAnDdKkPM"

SHEET_EXPORTS = [
    ("museum_FG.csv", LOD_TABLET_DICTIONARY_ID, "16624952"),
    ("CDLI_Object.csv", LOD_TABLET_DICTIONARY_ID, "875244849"),
    ("CDLI_Period.csv", LOD_TABLET_DICTIONARY_ID, "1310814692"),
    ("CDLI_Genre.csv", LOD_TABLET_DICTIONARY_ID, "1361472048"),
    ("CDLI_Lang.csv", LOD_TABLET_DICTIONARY_ID, "708139167"),
    ("CDLI_Material.csv", LOD_TABLET_DICTIONARY_ID, "1899871341"),
    ("CDLI_provenience_2024.csv", LOD_TABLET_DICTIONARY_ID, "698847686"),
    ("factgrid_df_header_sample.csv", WORKING_FACTGRID_DF_ID, "772537659"),
    ("proveniences_CDLI_Proveniences.csv", PROVENIENCES_TO_ADD_ID, "0"),
    ("proveniences_FG_Proveniences.csv", PROVENIENCES_TO_ADD_ID, "570231479"),
    ("proveniences_FG_AncientSettlement.csv", PROVENIENCES_TO_ADD_ID, "1336146429"),
    ("proveniences_duplicates.csv", PROVENIENCES_TO_ADD_ID, "1613867844"),
    ("proveniences_safe_to_add.csv", PROVENIENCES_TO_ADD_ID, "1162635483"),
    ("oracc_project_list.csv", ORACC_PROJECTS_ID, "494351747"),
    ("oracc_project_all.csv", ORACC_PROJECTS_ID, "1579012248"),
]


def download(url: str, output: Path) -> None:
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    output.write_bytes(response.content)
    print(f"wrote {output} ({len(response.content):,} bytes)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--skip-fg-cdli-id", action="store_true")
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        help="Download only matching output filenames, e.g. --only oracc_project_list.csv. Can be repeated.",
    )
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    only = set(args.only)
    for filename, spreadsheet_id, gid in SHEET_EXPORTS:
        if only and filename not in only:
            continue
        url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={gid}"
        download(url, out_dir / filename)

    if not args.skip_fg_cdli_id and not only:
        url = f"https://drive.google.com/uc?export=download&id={FG_CDLI_ID_FILE_ID}"
        download(url, out_dir / "FG_CDLI_ID.csv")


if __name__ == "__main__":
    main()
