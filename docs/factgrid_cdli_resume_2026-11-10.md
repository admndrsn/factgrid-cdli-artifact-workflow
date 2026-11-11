# Current FactGrid CDLI handoff — 2026-11-10 (through batch 068)

## Reconciled checkpoint

Completed through 068: **61,106 successful updates**, **118,998 claims added**.
Cumulative ledger: **80,623 written IDs**, one blocked_bad_sitelink and one
rewrite_ambiguous. All 68 canonical new-Mac result files have written outcomes.
Batch 068: 741 updates, 1,482 claims, 1h17m40s, no errors; zero remaining on resume.
Batch 049 recovery evidence confirms its delayed one-claim write; skipped count
unknown. Historical retry/recovery snapshots must never be counted again.
The batch-041 Q2036070/P386408 language modeling hold remains unresolved.

## Prepared/running batch 069

**5,000 items**, **9,942 expected unique main claims**, **10 qualifiers**.
Fresh window-042 review and dry run verified. Estimated runtime: 8¾–10h.
Active results excluded; synchronize actual results before another-machine resume.

```bash
python scripts/write_factgrid_cdli_artifact_items.py \
  --artifacts published/pilots/resume_2026_10_18/batch_069_artifacts.csv \
  --statements published/pilots/resume_2026_10_18/batch_069_statements.csv \
  --results published/pilots/resume_2026_10_18/batch_069_write_results.csv \
  --plan published/pilots/resume_2026_10_18/batch_069_dry_run_plan.csv \
  --factgrid-upload-table published/pilots/resume_2026_10_18/batch_069_upload_overrides.csv \
  --only-existing-factgrid \
  --preserve-update-labels \
  --limit 5000 \
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

After reconciling 069, freshly review **714 window-042 pending candidates**.
Then continue within **1–110000**, excluding manifests **001–042** and cumulative
outcomes. The range is not exhausted. Earlier pending files are historical/completed.
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
