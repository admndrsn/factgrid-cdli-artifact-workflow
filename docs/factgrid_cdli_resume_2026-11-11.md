# Current FactGrid CDLI handoff — 2026-11-11 (through batch 071)

## Reconciled checkpoint

Completed through 071: **67,977 successful updates**, **132,678 claims added**.
Cumulative ledger: **87,494 written IDs**, one blocked_bad_sitelink and one
rewrite_ambiguous. All 71 canonical new-Mac result files have written outcomes.
Batch 071: 1,157 updates, 2,314 claims, 2h00m54s, no errors; zero remaining on resume.
Batch 049 recovery evidence confirms its delayed one-claim write; skipped count
unknown. Historical retry/recovery snapshots must never be counted again.
The batch-042 Q2036070/P386408 language modeling hold remains unresolved.

## Prepared/running batch 072

**4,267 items**, **7,985 expected unique main claims**, **9 qualifiers**.
Fresh review and dry run passed. Approximately 8½–10 hours with a six-second pause
for this batch only; default remains five seconds. Active results excluded.

```bash
python scripts/write_factgrid_cdli_artifact_items.py \
  --artifacts published/pilots/resume_2026_10_18/batch_072_artifacts.csv \
  --statements published/pilots/resume_2026_10_18/batch_072_statements.csv \
  --results published/pilots/resume_2026_10_18/batch_072_write_results.csv \
  --plan published/pilots/resume_2026_10_18/batch_072_dry_run_plan.csv \
  --factgrid-upload-table published/pilots/resume_2026_10_18/batch_072_upload_overrides.csv \
  --only-existing-factgrid \
  --preserve-update-labels \
  --limit 4267 \
  --sleep 6
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

After reconciling 072, no pending eligible candidates remain from windows 044–047. The local-mapping coverage audit across source positions 1–421387 found no further unreviewed mapped candidates after these windows. This does not prove that unmatched source records lack live FactGrid items. Refresh live CDLI mappings and deduplicate unmatched records before a separately reviewed new-item pilot; reconcile existing holds independently. Do not create another batch by replaying reviewed or completed IDs.

See batch_072_prepared_2026-11-11.md, windows_044_047_summary.json and coverage_audit_2026_11_11.json. Source ZIP has 421,387 records; offsets are not completion markers. Retain historical holds, including Q2036070/P386408.

## Overall objective

Complete CDLI items and statements first, including new unmatched items and
review holds. Then create/verify ATF Document pages and add P251 links together.
Prepare URL mappings first without adding links to missing pages. See
cdli_completion_workplan.md and the reference CDLI-ATF-L-Q894483.
