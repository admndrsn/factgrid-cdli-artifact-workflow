# Current FactGrid CDLI handoff — 2026-11-04 (through batch 044)

## Reconciled checkpoint

The pilot and batches 002–044 record **25,349 successful updates** and
**49,570 added claims**. All 44 canonical new-Mac result files are written with
no errors. The cumulative ledger has **44,866 written CDLI IDs**, plus one
blocked_bad_sitelink and one rewrite_ambiguous; held outcomes remain excluded.

- Batch 040: 1,500 updates, 2,950 claims; zero rows on resume dry run.
- Batch 041: 1,158 updates, 2,199 claims; zero rows on resume dry run.
- Batch 042: 1,012 updates, 1,798 claims; zero rows on resume dry run.
- Batch 044: 380 updates, 663 claims; zero rows on resume dry run.
- Batch 043: 1,500 updates, 2,852 claims after retry; zero rows on resume dry run.
  Its historical before-retry CSV must not be merged into the ledger.
- Terminal outputs agree with both canonical CSVs. Historical before-retry
  snapshots must never be counted again.
- Q2036070/P386408 proposed two languages in 041. The writer kept the first
  under its single-value rule. See batch_041_language_followup_Q2036070.csv;
  the second language needs a modeling review, not an automatic retry.

## Prepared/running batch 045

**1,511 items**, **2,477 expected main claims**, **25 inventory qualifiers**.
Fresh live review and dry run passed. All eligible items in the range are selected;
100 unknown inventory placeholders were omitted. User runs writes. This checkpoint
excludes active results; synchronize/reconcile the actual result file before
resuming, especially on another machine.

```bash
python scripts/write_factgrid_cdli_artifact_items.py \
  --artifacts published/pilots/resume_2026_10_18/batch_045_artifacts.csv \
  --statements published/pilots/resume_2026_10_18/batch_045_statements.csv \
  --results published/pilots/resume_2026_10_18/batch_045_write_results.csv \
  --plan work/batch_045_resume_plan.csv \
  --factgrid-upload-table published/pilots/resume_2026_10_18/batch_045_upload_overrides.csv \
  --only-existing-factgrid --preserve-update-labels --limit 1511 --sleep 5
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

Pending files from windows 021, 023 and 025 are historical/completed. Window 026
reviewed all 2,439 remaining mapped candidates in **260001–285000**; batch 045
contains all 1,511 eligible items. After reconciling it, advance to **285001–310000**
(offset 285000, limit 25000), excluding manifests **001–026** and cumulative
outcomes, with fresh review. No batch 046 is prepared. Historical holds and
unmatched source items remain unfinished work.

```bash
python scripts/check_factgrid_api.py --timeout 15
python scripts/build_factgrid_resume_ledger.py
```

Require JSON and FactGrid site information. Use Python 3.12+ and requirements.txt.
Credentials stay private; retain the current login method. Source ZIP details
and checksum remain in the November 1 handoff. API access may depend on the network.

## Overall objective

Complete CDLI items and statements first, including new unmatched items and
review holds. Then create/verify ATF Document pages and add P251 links together.
Prepare URL mappings first without adding links to missing pages. See
cdli_completion_workplan.md and the reference CDLI-ATF-L-Q894483.
