# Current FactGrid CDLI handoff — 2026-11-09 (through batch 062)

## Reconciled checkpoint

Completed through 062: **52,522 successful updates**, **101,814 claims added**.
Cumulative ledger: **72,039 written IDs**, one blocked_bad_sitelink and one
rewrite_ambiguous. All 62 canonical new-Mac result files have written outcomes.
Batch 062: 678 updates, 1,355 claims, 1h11m06s, no errors; zero remaining on resume.
Batch 049 recovery evidence confirms its delayed one-claim write; skipped count
unknown. Never count historical retry/recovery snapshots again. The batch-041
Q2036070/P386408 language modeling hold remains unresolved.

## Prepared/running batch 063

1,500 items, 2,983 expected unique main claims, 0 inventory qualifiers.
Fresh review and verified dry run passed. Active results are excluded; synchronize
actual results before another-machine resume.

```bash
python scripts/write_factgrid_cdli_artifact_items.py \
  --artifacts published/pilots/resume_2026_10_18/batch_063_artifacts.csv \
  --statements published/pilots/resume_2026_10_18/batch_063_statements.csv \
  --results published/pilots/resume_2026_10_18/batch_063_write_results.csv \
  --plan work/batch_063_resume_plan.csv \
  --factgrid-upload-table published/pilots/resume_2026_10_18/batch_063_upload_overrides.csv \
  --only-existing-factgrid --preserve-update-labels --limit 1500 --sleep 5
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

After reconciling 063, freshly review 678 window-038 pending candidates.
Then continue within **1–110000**, excluding manifests **001–038** and cumulative
outcomes. The 2,500-candidate review did not exhaust this range. Earlier pending
files are historical/completed; never replay independently.
Window 031 reviewed the ZIP's final source range: 803 complete, 500 conflicts,
zero eligible additions. Earlier offset handoffs were inaccurate; use explicit
CDLI identities/exclusions. Holds and unmatched records remain unfinished work.
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
