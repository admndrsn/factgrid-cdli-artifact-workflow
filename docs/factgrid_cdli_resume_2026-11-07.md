# Current FactGrid CDLI handoff — 2026-11-07 (through batch 055)

## Reconciled checkpoint

Completed through 055: **40,950 successful updates**, **78,859 claims added**.
Cumulative ledger: **60,467 written IDs**, one blocked_bad_sitelink and one
rewrite_ambiguous. All 55 canonical new-Mac result files have written outcomes.
Batch 055: 1,500 updates, 2,929 claims, 2h41m54s, no errors; zero remaining on resume.
Batch 049 recovery evidence confirms its delayed one-claim write; skipped count
unknown. Historical retry/recovery snapshots must never be counted again.
The batch-041 Q2036070/P386408 language modeling hold remains unresolved.

## Prepared/running batch 056

**728 items**, **1,434 expected unique main claims**, **0 qualifiers**.
All window-033 pending candidates passed fresh review and a verified dry run.
Allow about 1h19m. Active results are excluded; synchronize actual results before
another-machine resume.

```bash
python scripts/write_factgrid_cdli_artifact_items.py \
  --artifacts published/pilots/resume_2026_10_18/batch_056_artifacts.csv \
  --statements published/pilots/resume_2026_10_18/batch_056_statements.csv \
  --results published/pilots/resume_2026_10_18/batch_056_write_results.csv \
  --plan work/batch_056_resume_plan.csv \
  --factgrid-upload-table published/pilots/resume_2026_10_18/batch_056_upload_overrides.csv \
  --only-existing-factgrid --preserve-update-labels --limit 728 --sleep 5
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

After reconciling 056, continue within **1–110000**, excluding manifests
**001–033** and cumulative outcomes. Window 033 was capped at 2,500 candidates;
the range is not exhausted. Its pending files belong to 056. Earlier pending
files are historical/completed; never replay independently.
Window 031 reviewed the final source range 385001–421387: 803 complete, 500
conflicts, zero eligible additions. Earlier offset handoffs were inaccurate;
continue the coverage audit by explicit CDLI identities and exclusions.
Holds and unmatched records remain unfinished work.
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
