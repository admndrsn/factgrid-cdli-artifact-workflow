# Current FactGrid CDLI handoff — 2026-11-06 (through batch 052)

## Reconciled checkpoint

Completed through 052: **35,396 successful updates**, **67,842 claims added**.
Cumulative ledger: **54,913 written IDs**, one blocked_bad_sitelink and one
rewrite_ambiguous. All 52 canonical new-Mac result files have written outcomes.
Batch 052: 732 updates, 921 claims, 1h16m42s, no errors; zero remaining on resume.
Batch 049 recovery evidence confirms its delayed one-claim write; skipped count
unknown. Historical retry/recovery snapshots must never be counted again.
The batch-041 Q2036070/P386408 language modeling hold remains unresolved.

## Prepared/running batch 053

**2,300 items**, **4,616 expected unique main claims**, **11 qualifiers**.
Fresh review and verified dry run passed. Approximately four hours at recent pace.
Active results are excluded; synchronize actual results before another-machine resume.

```bash
python scripts/write_factgrid_cdli_artifact_items.py \
  --artifacts published/pilots/resume_2026_10_18/batch_053_artifacts.csv \
  --statements published/pilots/resume_2026_10_18/batch_053_statements.csv \
  --results published/pilots/resume_2026_10_18/batch_053_write_results.csv \
  --plan work/batch_053_resume_plan.csv \
  --factgrid-upload-table published/pilots/resume_2026_10_18/batch_053_upload_overrides.csv \
  --only-existing-factgrid --preserve-update-labels --limit 2300 --sleep 5
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

After reconciling 053, freshly review **1754 window-032 pending candidates**.
Window 032 reviewed 5,000 mapped source candidates in **1–110000**.
After the pending group is resolved, continue within 1–110000 excluding manifests 001–032 and cumulative outcomes. The 5,000-candidate review limit did not exhaust the range.
Exclude manifests **001–032** and cumulative outcomes when selecting new work.
Earlier pending files belong to completed batches; never replay independently.
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
