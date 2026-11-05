# Current FactGrid CDLI handoff — 2026-11-05 (through batch 048)

Batch 049 retry: 130 updates / 291 claims saved; 126 items remain after a CSRF rejection. See batch_049_retry_2026-11-05.md. Active results must be synchronized before another-machine resume.

## Reconciled checkpoint

Completed through 048: **30,296 successful updates**, **58,248 claims added**.
Cumulative ledger: **49,813 written IDs**, one blocked_bad_sitelink and one
rewrite_ambiguous. All 48 canonical new-Mac result files have written outcomes.
Batch 048: 1,500 updates, 2,669 claims, zero remaining on resume dry run.
The one-claim forecast difference was a duplicate language row, confirmed live.
See batch_048_completed_2026-11-05.md and its completion-check evidence.
Historical retry snapshots and revision-recovery evidence must never be counted
as additional canonical results. The batch-041 Q2036070/P386408 language modeling
hold remains unresolved; do not automatically retry its second language.

## Prepared/running batch 049

256 items, 533 expected unique main claims and 13 inventory qualifiers.
All window-028 pending candidates passed fresh review and the launcher dry run.
Active results are excluded. Reconcile actual results before another-machine resume.

```bash
python scripts/write_factgrid_cdli_artifact_items.py \
  --artifacts published/pilots/resume_2026_10_18/batch_049_artifacts.csv \
  --statements published/pilots/resume_2026_10_18/batch_049_statements.csv \
  --results published/pilots/resume_2026_10_18/batch_049_write_results.csv \
  --plan work/batch_049_resume_plan.csv \
  --factgrid-upload-table published/pilots/resume_2026_10_18/batch_049_upload_overrides.csv \
  --only-existing-factgrid --preserve-update-labels --limit 256 --sleep 5
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

After reconciling 049, continue within **310001–335000**, excluding review
manifests **001–028** and cumulative outcomes. This range is not exhausted.
Window-028 pending files belong to 049; earlier pending files are historical.
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
