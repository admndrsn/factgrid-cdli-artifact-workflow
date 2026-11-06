# Current FactGrid CDLI handoff — 2026-11-06 (through batch 051)

## Reconciled checkpoint

Completed through 051: **34,664 successful updates**, **66,921 claims added**.
Cumulative ledger: **54,181 written IDs**, one blocked_bad_sitelink and one
rewrite_ambiguous. All 51 canonical new-Mac result files have written outcomes.
Batch 051: 3,600 updates, 7,204 claims, 6h16m14s, no errors; zero remaining on resume.
Batch 049 recovery evidence confirms its delayed one-claim write; skipped count
unknown. Historical retry/recovery snapshots must never be counted again.
The batch-041 Q2036070/P386408 language modeling hold remains unresolved.

## Prepared/running batch 052

**732 items**, **921 expected unique main claims**, **0 qualifiers**.
Fresh review and verified dry run passed. Active results are excluded;
synchronize actual results before another-machine resume.

```bash
python scripts/write_factgrid_cdli_artifact_items.py \
  --artifacts published/pilots/resume_2026_10_18/batch_052_artifacts.csv \
  --statements published/pilots/resume_2026_10_18/batch_052_statements.csv \
  --results published/pilots/resume_2026_10_18/batch_052_write_results.csv \
  --plan work/batch_052_resume_plan.csv \
  --factgrid-upload-table published/pilots/resume_2026_10_18/batch_052_upload_overrides.csv \
  --only-existing-factgrid --preserve-update-labels --limit 732 --sleep 5
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

After reconciling 052, advance to **385001–410000** (offset 385000, limit 25000),
excluding review manifests **001–030** and cumulative outcomes. All mapped
candidates in 335001–385000 were reviewed. Window-030 pending files are represented
by 052; earlier pending files belong to completed batches. Never replay independently.
Historical holds/unmatched records remain work; source positions are not completion boundaries.
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
