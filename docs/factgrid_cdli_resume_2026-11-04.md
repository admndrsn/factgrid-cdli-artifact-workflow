# Current FactGrid CDLI handoff — 2026-11-04 (through batch 043)

## Reconciled checkpoint

The pilot and batches 002–043 record **24,969 successful updates** and
**48,907 added claims**. All 43 canonical new-Mac result files are written with
no errors. The cumulative ledger has **44,486 written CDLI IDs**, plus one
blocked_bad_sitelink and one rewrite_ambiguous; held outcomes remain excluded.

- Batch 040: 1,500 updates, 2,950 claims; zero rows on resume dry run.
- Batch 041: 1,158 updates, 2,199 claims; zero rows on resume dry run.
- Batch 042: 1,012 updates, 1,798 claims; zero rows on resume dry run.
- Batch 043: 1,500 updates, 2,852 claims after retry; zero rows on resume dry run.
  Its historical before-retry CSV must not be merged into the ledger.
- Terminal outputs agree with both canonical CSVs. Historical before-retry
  snapshots must never be counted again.
- Q2036070/P386408 proposed two languages in 041. The writer kept the first
  under its single-value rule. See batch_041_language_followup_Q2036070.csv;
  the second language needs a modeling review, not an automatic retry.

## Prepared/running batch 044

**380 items**, **663 expected main claims**, **6 inventory qualifiers**.
All remaining window-025 pending candidates passed fresh review. Four unknown
inventory placeholders were omitted. The dry run passed. The user runs writes;
this publication excludes active results. Synchronize and reconcile the actual
result file before any resume, especially on another machine.

```bash
python scripts/write_factgrid_cdli_artifact_items.py \
  --artifacts published/pilots/resume_2026_10_18/batch_044_artifacts.csv \
  --statements published/pilots/resume_2026_10_18/batch_044_statements.csv \
  --results published/pilots/resume_2026_10_18/batch_044_write_results.csv \
  --plan work/batch_044_resume_plan.csv \
  --factgrid-upload-table published/pilots/resume_2026_10_18/batch_044_upload_overrides.csv \
  --only-existing-factgrid --preserve-update-labels --limit 380 --sleep 5
```

Only the user's write command adds --write. Omit --continue-on-row-error.

## Standing workflow

When the user pastes terminal output: reconcile the canonical CSV and cumulative
ledger, inspect failures or ambiguous outcomes before advancing, freshly review
and prepare the next batch, provide the tested terminal command immediately,
then publish completed results and next-batch preparation while the user writes.
Aim for 1,500 verified items, using fewer to finish a range or pending group.
Publish immutable snapshots; exclude active-batch result files. Preserve labels
and descriptions, five-second pauses, and stop-on-error behavior.

Check live identities, live conflicts, missing-qualifier holds, and multiple
proposed values within one plan for writer single-value properties. Such planned
conflicts must be held even when the live property is empty. Skip unknown
inventory placeholders. P10 is a qualifier on P329, not a main statement.

## Next selection

Batch 044 contains the final 380 eligible pending candidates from window 025.
The old window-025 pending files are now represented by this batch; do not replay
them independently. Previous pending files from windows 021 and 023 are completed.

After reconciling 044, begin new range **260001–285000** (offset 260000, limit
25000), excluding manifests **001–025** and cumulative outcomes. All mapped
candidates in 235001–260000 were reviewed, but holds and unmatched records
remain unfinished work. No batch 045 is prepared.

```bash
python scripts/check_factgrid_api.py --timeout 15
python scripts/build_factgrid_resume_ledger.py
```

Require JSON and FactGrid site information. Use Python 3.12+ and requirements.txt.
Credentials stay private; retain the current login method. Source ZIP details
and checksum remain in the November 1 handoff. API access may depend on the network.

## Overall objective

Complete CDLI items and statements first, including new unmatched items and
review holds. Then create/verify ATF Document pages and add P251 links together.
Prepare URL mappings first without adding links to missing pages. See
cdli_completion_workplan.md and the reference CDLI-ATF-L-Q894483.
