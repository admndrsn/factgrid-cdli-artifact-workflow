# Current FactGrid CDLI handoff — 2026-11-05 (through batch 046)

## Reconciled checkpoint

The pilot and batches 002–046 record **28,360 successful updates** and
**54,816 added claims**. All 46 canonical new-Mac result files are written with
no errors. The cumulative ledger has **47,877 written CDLI IDs**, plus one
blocked_bad_sitelink and one rewrite_ambiguous; held outcomes remain excluded.

- Batch 040: 1,500 updates, 2,950 claims; zero rows on resume dry run.
- Batch 041: 1,158 updates, 2,199 claims; zero rows on resume dry run.
- Batch 042: 1,012 updates, 1,798 claims; zero rows on resume dry run.
- Batch 044: 380 updates, 663 claims; zero rows on resume dry run.
- Batch 046: 1,500 updates, 2,769 claims after CSRF retry; zero remaining rows.
  Its historical before-retry snapshot must never be counted again.
- Batch 045: 1,511 updates, 2,477 claims; zero rows on resume dry run.
  Includes one result recovered from live revision evidence after an empty CSV.
  Recovery evidence is historical, never additional canonical successes.
- Batch 043: 1,500 updates, 2,852 claims after retry; zero rows on resume dry run.
  Its historical before-retry CSV must not be merged into the ledger.
- Terminal outputs agree with both canonical CSVs. Historical before-retry
  snapshots must never be counted again.
- Q2036070/P386408 proposed two languages in 041. The writer kept the first
  under its single-value rule. See batch_041_language_followup_Q2036070.csv;
  the second language needs a modeling review, not an automatic retry.

## Prepared/running batch 047

**436 items**, **763 expected main claims**, **no inventory qualifiers**.
All window-027 pending candidates passed fresh review and dry run. Two unknown
inventory placeholders were omitted. User runs writes; active results are
excluded. Reconcile/synchronize actual results before resuming on another machine.

```bash
python scripts/write_factgrid_cdli_artifact_items.py \
  --artifacts published/pilots/resume_2026_10_18/batch_047_artifacts.csv \
  --statements published/pilots/resume_2026_10_18/batch_047_statements.csv \
  --results published/pilots/resume_2026_10_18/batch_047_write_results.csv \
  --plan work/batch_047_resume_plan.csv \
  --factgrid-upload-table published/pilots/resume_2026_10_18/batch_047_upload_overrides.csv \
  --only-existing-factgrid --preserve-update-labels --limit 436 --sleep 5
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

Window-027 pending files now belong to batch 047; do not replay independently.
Earlier pending files from windows 021, 023 and 025 are historical/completed.
After reconciling 047, advance to **310001–335000** (offset 310000, limit 25000),
excluding manifests **001–027** and cumulative outcomes, with fresh live review.
All mapped candidates in 285001–310000 were reviewed; historical holds and
unmatched source records remain unfinished work. No batch 048 is prepared.

```bash
python scripts/check_factgrid_api.py --timeout 15
python scripts/build_factgrid_resume_ledger.py
```

Require JSON and FactGrid site information. Use Python 3.12+ and requirements.txt.
Credentials stay private; retain the current login method. Source ZIP provenance
and checksum remain in the November 1 handoff. API access may depend on network.

## Overall objective

Complete CDLI items and statements first, including new unmatched items and
review holds. Then create/verify ATF Document pages and add P251 links together.
Prepare URL mappings first without adding links to missing pages. See
cdli_completion_workplan.md and the reference CDLI-ATF-L-Q894483.
