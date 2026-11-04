# Current FactGrid CDLI handoff — 2026-11-04 (through batch 042)

## Reconciled checkpoint

The pilot and batches 002–042 record **23,469 successful updates** and
**46,055 added claims**. All 42 canonical new-Mac result files are written with
no errors. The cumulative ledger has **42,986 written CDLI IDs**, plus one
blocked_bad_sitelink and one rewrite_ambiguous; held outcomes remain excluded.

- Batch 040: 1,500 updates, 2,950 claims; zero rows on resume dry run.
- Batch 041: 1,158 updates, 2,199 claims; zero rows on resume dry run.
- Batch 042: 1,012 updates, 1,798 claims; zero rows on resume dry run.
- Terminal outputs agree with both canonical CSVs. Historical before-retry
  snapshots must never be counted again.
- Q2036070/P386408 proposed two languages in 041. The writer kept the first
  under its single-value rule. See batch_041_language_followup_Q2036070.csv;
  the second language needs a modeling review, not an automatic retry.

## Prepared/running batch 043

**1,500 items**, **2,852 expected main claims**, **48 inventory qualifiers**.
Fresh live review and dry run passed. Two unknown inventory placeholders were
omitted. The user runs FactGrid writes in Terminal. This publication excludes
batch 043 write results, whether absent or in progress; do not count completion
without reconciling the actual canonical result file.

Portable dry run from the repository root:

```bash
python scripts/write_factgrid_cdli_artifact_items.py \
  --artifacts published/pilots/resume_2026_10_18/batch_043_artifacts.csv \
  --statements published/pilots/resume_2026_10_18/batch_043_statements.csv \
  --results published/pilots/resume_2026_10_18/batch_043_write_results.csv \
  --plan work/batch_043_resume_plan.csv \
  --factgrid-upload-table published/pilots/resume_2026_10_18/batch_043_upload_overrides.csv \
  --only-existing-factgrid --preserve-update-labels --limit 1500 --sleep 5
```

Only the user's write command adds --write. Omit --continue-on-row-error.
On another machine, synchronize actual running/completed results before resuming;
a missing result file in Git does not mean the batch was never run.

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

The pending window-021 and window-023 files are historical and completed.
Window 025 reviewed all 2,891 mapped candidates left in **235001–260000** and
found 1,880 eligible items. Batch 043 contains 1,500; **380 pending candidates**
are saved in window_025_remaining_pending_recheck_artifacts.csv and the matching
statements file. After reconciling 043, freshly review these pending inputs
against the rebuilt ledger before batch 044. Do not discard them by excluding
the whole window-025 manifest. No batch 044 is prepared.

After the pending group is resolved, advance new selection to **260001–285000**
(offset 260000, limit 25000), excluding manifests **001–025** and cumulative
outcomes. All mapped candidates in 235001–260000 have been reviewed, but holds
and unmatched records remain unfinished work.

```bash
python scripts/check_factgrid_api.py --timeout 15
python scripts/build_factgrid_resume_ledger.py
```

Require JSON and FactGrid site information. Use Python 3.12+ and requirements.txt.
Credentials stay private. Retain the current login method; API IP allowlisting
may depend on the network. Source ZIP details remain in the November 1 guide.

## Overall objective

Complete CDLI items and statements first, including new unmatched items and
review holds. Then create/verify ATF Document pages and add P251 links together.
Prepare URL mappings first without adding links to missing pages. See
cdli_completion_workplan.md and the reference CDLI-ATF-L-Q894483.
