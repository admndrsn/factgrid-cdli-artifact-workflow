# Current FactGrid CDLI handoff — 2026-11-08 (through batch 060)

## Reconciled checkpoint

Completed through 060: **48,244 successful updates**, **93,342 claims added**.
Cumulative ledger: **67,761 written IDs**, one blocked_bad_sitelink and one
rewrite_ambiguous. All 60 canonical new-Mac result files have written outcomes.
Batch 060: 1,500 updates, 2,964 claims, 3h22m52s, no errors; zero remaining on resume.
Batch 049 recovery evidence confirms its delayed one-claim write; skipped count
unknown. Historical retry/recovery snapshots must never be counted again.
The batch-041 Q2036070/P386408 language modeling hold remains unresolved.

## Prepared/running batch 061 — expanded

**3,600 items**, **7,117 expected unique main claims**, **1 qualifiers**.
Includes 740 window-036 items and 2,860 freshly reviewed window-037 items.
Expanded before writing for the user's six-to-eight-hour absence. Allow about 6¼–8 hours.
Dry run passed; active results excluded. Synchronize results before another-machine resume.

```bash
python scripts/write_factgrid_cdli_artifact_items.py \
  --artifacts published/pilots/resume_2026_10_18/batch_061_artifacts.csv \
  --statements published/pilots/resume_2026_10_18/batch_061_statements.csv \
  --results published/pilots/resume_2026_10_18/batch_061_write_results.csv \
  --plan work/batch_061_resume_plan.csv \
  --factgrid-upload-table published/pilots/resume_2026_10_18/batch_061_upload_overrides.csv \
  --only-existing-factgrid --preserve-update-labels --limit 3600 --sleep 5
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

After reconciling 061, freshly review 678 window-037 pending candidates.
Then continue within **1–110000**, excluding manifests **001–037** and cumulative
outcomes. The 4,000-candidate review did not exhaust the range. Window-036 pending
files are represented by 061; earlier pending files are historical/completed.
Historical conflict holds and unmatched records remain unfinished work.

Use Python 3.12+ and requirements.txt; retain private credentials/current login.
Source ZIP provenance remains in the November 1 handoff.

```bash
python scripts/check_factgrid_api.py --timeout 15
python scripts/build_factgrid_resume_ledger.py
```

## Overall objective

Complete CDLI items and statements first, including new unmatched items and
review holds. Then create/verify ATF Document pages and add P251 links together.
Prepare URL mappings first without adding links to missing pages. See
cdli_completion_workplan.md and the reference CDLI-ATF-L-Q894483.
