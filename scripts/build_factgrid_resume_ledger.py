#!/usr/bin/env python3
"""Reconcile canonical result CSVs; never read historical before-retry snapshots."""

import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, default=ROOT / 'published/pilots/resume_2026_10_18/cumulative_results.csv')
args = parser.parse_args()
checkpoint = ROOT / 'published/pilots/resume_2026_10_18'
paths = sorted((ROOT / 'published/pilots').glob('factgrid_cdli_artifact_write_results*.csv'))
old_count = len(paths)
paths += [checkpoint / 'pilot_write_results.csv']
paths += sorted(checkpoint.glob('batch_*_write_results.csv'))
frames = []
for path in paths:
    if not path.is_file():
        raise SystemExit(f'Missing canonical result file: {path}')
    frame = pd.read_csv(path, dtype=str).fillna('')
    required = {'cdli_id', 'factgrid_qid', 'write_status', 'claims_written'}
    if not required.issubset(frame):
        raise SystemExit(f'Invalid result columns: {path}')
    if frame.cdli_id.duplicated().any():
        raise SystemExit(f'Duplicate IDs within canonical result file: {path}')
    frames.append(frame)
all_rows = pd.concat(frames, ignore_index=True)
all_rows = all_rows.drop_duplicates('cdli_id', keep='last')
new_rows = pd.concat(frames[old_count:], ignore_index=True)
if new_rows.cdli_id.duplicated().any():
    raise SystemExit('Duplicate CDLI IDs across new-Mac batches; inspect before resuming.')
written = new_rows[new_rows.write_status.eq('written')]
args.output.parent.mkdir(parents=True, exist_ok=True)
all_rows.to_csv(args.output, index=False)
print(f'Canonical result files: {len(paths)}')
print(all_rows.write_status.value_counts().to_string())
print(f'New-Mac successful updates: {len(written):,}')
print(f'New-Mac claims added: {written.claims_written.astype(int).sum():,}')
print(f'Wrote {args.output}')
