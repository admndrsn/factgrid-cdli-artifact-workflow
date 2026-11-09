# Current FactGrid CDLI handoff — 2026-11-09 (through batch 061)

## Reconciled checkpoint

Completed through 061: **51,844 successful updates**, **100,459 claims added**.
Cumulative ledger: **71,361 written IDs**, one blocked_bad_sitelink and one
rewrite_ambiguous. All 61 canonical new-Mac result files have written outcomes.
Batch 061: 3,600 updates, 7,117 claims after read-timeout retry; zero remaining on
resume dry run. Historical before-retry snapshots must never be counted again.
Batch 049 recovery evidence confirms its delayed one-claim write; skipped count
unknown. The batch-041 Q2036070/P386408 language modeling hold remains unresolved.

## Prepared/running batch 062

678 items, 1,355 expected unique main claims, 0 inventory qualifiers.
Fresh review and verified dry run passed. Allow about 1h12m. Active results are
excluded; synchronize actual results before another-machine resume.

```bash
python scripts/write_factgrid_cdli_artifact_items.py \
  --artifacts published/pilots/resume_2026_10_18/batch_062_artifacts.csv \
  --statements published/pilots/resume_2026_10_18/batch_062_statements.csv \
  --results published/pilots/resume_2026_10_18/batch_062_write_results.csv \
  --plan work/batch_062_resume_plan.csv \
  --factgrid-upload-table published/pilots/resume_2026_10_18/batch_062_upload_overrides.csv \
  --only-existing-factgrid --preserve-update-labels --limit 678 --sleep 5
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

After reconciling 062, continue within **1–110000**, excluding manifests
**001–037** and cumulative outcomes. Window 037 was capped at 4,000 candidates;
the range is not exhausted. Its pending files belong to 062. Earlier pending
files are historical/completed; never replay independently. Historical conflict
holds and unmatched records remain unfinished work.
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
