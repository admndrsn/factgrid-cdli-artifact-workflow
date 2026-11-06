# Current FactGrid CDLI handoff — 2026-11-05 (through batch 049)

## Reconciled checkpoint

Completed through 049: **30,552 successful updates**, **58,781 claims added**.
Cumulative ledger: **50,069 written IDs**, one blocked_bad_sitelink and one
rewrite_ambiguous. All 49 canonical new-Mac result files have written outcomes.
Batch 049: 256 updates, 533 claims, zero remaining on resume dry run. It completed
after CSRF/504 interruptions. Revision 21782647 confirms the recovered one-claim
write to Q1994815; its skipped count remains unknown. See the completion note,
recovery evidence and historical snapshots. Never count snapshots as new successes.
Batch 048's one-claim forecast difference was a duplicate language source row.
The batch-041 Q2036070/P386408 language modeling hold remains unresolved.

## Prepared/running batch 050

512 items, 936 expected unique main claims and 46 inventory qualifiers.
All selected items passed fresh review and a verified launcher dry run.
Active results are excluded. Synchronize actual results before another-machine resume.

```bash
python scripts/write_factgrid_cdli_artifact_items.py \
  --artifacts published/pilots/resume_2026_10_18/batch_050_artifacts.csv \
  --statements published/pilots/resume_2026_10_18/batch_050_statements.csv \
  --results published/pilots/resume_2026_10_18/batch_050_write_results.csv \
  --plan work/batch_050_resume_plan.csv \
  --factgrid-upload-table published/pilots/resume_2026_10_18/batch_050_upload_overrides.csv \
  --only-existing-factgrid --preserve-update-labels --limit 512 --sleep 5
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

After reconciling 050, advance to **335001–360000** (offset 335000, limit 25000),
excluding review manifests **001–029** and cumulative outcomes. All mapped
candidates in 310001–335000 have been reviewed. No eligible pending remainder;
historical conflict holds and unmatched records remain unfinished work.
Earlier pending files belong to completed batches; never replay independently.
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
