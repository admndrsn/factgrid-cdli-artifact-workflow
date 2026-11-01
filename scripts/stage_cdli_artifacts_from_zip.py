#!/usr/bin/env python3
"""Stage a sorted range directly from CDLI JSON ZIP without extracting the corpus."""

import argparse
from pathlib import Path
import zipfile

import pandas as pd

from prepare_cdli_artifact_staging import flatten_artifact

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--zip', type=Path, required=True)
parser.add_argument('--offset', type=int, required=True)
parser.add_argument('--limit', type=int, default=25000)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--summary', type=Path, required=True)
args = parser.parse_args()
if args.offset < 0 or args.limit < 1:
    parser.error('Offset must be nonnegative and limit positive.')
with zipfile.ZipFile(args.zip) as archive:
    names = sorted((n for n in archive.namelist() if n.endswith('.json') and '__MACOSX/' not in n and not Path(n).name.startswith('._')), key=lambda n: Path(n).name)
    if len({Path(n).name for n in names}) != len(names):
        raise SystemExit('Duplicate JSON basenames; cannot select a stable range.')
    selected = names[args.offset:args.offset + args.limit]
    if not selected:
        raise SystemExit('No JSON files selected.')
    rows = [flatten_artifact(zipfile.Path(archive, name)) for name in selected]
frame = pd.DataFrame(rows).sort_values('source_json', kind='stable')
if frame.cdli_id.duplicated().any():
    raise SystemExit('Duplicate artifact IDs; no staging file written.')
args.output.parent.mkdir(parents=True, exist_ok=True)
args.summary.parent.mkdir(parents=True, exist_ok=True)
frame.to_csv(args.output, index=False)
pd.DataFrame([{'metric': 'source_files', 'value': len(selected)}, {'metric': 'staging_rows', 'value': len(frame)}, {'metric': 'error_rows', 'value': 0}, {'metric': 'unique_cdli_ids', 'value': frame.cdli_id.nunique()}]).to_csv(args.summary, index=False)
print(f'Staged {len(frame):,} records -> {args.output}')
print('Sorted source positions are not historical completion boundaries.')
