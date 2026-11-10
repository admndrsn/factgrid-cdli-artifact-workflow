# Current FactGrid CDLI handoff — 2026-11-09 (through batch 064)

## Reconciled checkpoint

Completed through 064: **54,700 successful updates**, **106,140 claims added**.
Cumulative ledger: **74,217 written IDs**, one blocked_bad_sitelink and one
rewrite_ambiguous. All 64 canonical new-Mac result files have written outcomes.
Batch 064: 678 updates, 1,343 claims, 1h20m11s, no errors; zero remaining on resume.
Batch 049 recovery evidence confirms its delayed one-claim write; skipped count
unknown. Historical retry/recovery snapshots must never be counted again.
The batch-041 Q2036070/P386408 language modeling hold remains unresolved.

## Prepared/running batch 065

**3,600 items**, **7,256 expected unique main claims**, **59 qualifiers**.
Fresh reviews cover windows 039–040; dry run verified. Allow roughly 6¼–8 hours,
subject to server speed and stop-on-error. Active results excluded.

```bash
python scripts/write_factgrid_cdli_artifact_items.py \
  --artifacts published/pilots/resume_2026_10_18/batch_065_artifacts.csv \
  --statements published/pilots/resume_2026_10_18/batch_065_statements.csv \
  --results published/pilots/resume_2026_10_18/batch_065_write_results.csv \
  --plan published/pilots/resume_2026_10_18/batch_065_dry_run_plan.csv \
  --factgrid-upload-table published/pilots/resume_2026_10_18/batch_065_upload_overrides.csv \
  --only-existing-factgrid \
  --preserve-update-labels \
  --limit 3600 \
  --sleep 5
```

Only the user adds --write. Omit --continue-on-row-error.

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

After reconciling 065, freshly review remaining pending candidates: {'039': 0, '040': 565}.
Then continue within **1–110000**, excluding manifests **001–040** and cumulative
outcomes. The range is not exhausted. Older pending files are historical/completed;
never replay independently.
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
