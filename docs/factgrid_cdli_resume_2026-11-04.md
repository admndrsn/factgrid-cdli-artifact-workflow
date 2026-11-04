# Current FactGrid CDLI handoff — 2026-11-04 (through batch 041)

## Reconciled checkpoint

The pilot and batches 002–041 record **22,457 successful updates** and
**44,257 added claims**. All 41 canonical new-Mac result files are written with
no errors. The cumulative ledger has **41,974 written CDLI IDs**, plus one
blocked_bad_sitelink and one rewrite_ambiguous; held outcomes remain excluded.

- Batch 040: 1,500 updates, 2,950 claims; zero rows on resume dry run.
- Batch 041: 1,158 updates, 2,199 claims; zero rows on resume dry run.
- Terminal outputs agree with both canonical CSVs. Historical before-retry
  snapshots must never be counted again.
- Q2036070/P386408 proposed two languages in 041. The writer kept the first
  under its single-value rule. See batch_041_language_followup_Q2036070.csv;
  the second language needs a modeling review, not an automatic retry.

## Prepared/running batch 042

**1,012 items**, **1,798 expected main claims**, **8 inventory qualifiers**.
Preparation is complete and the dry run passed. The user runs FactGrid writes
in Terminal. This publication deliberately excludes its write results, whether
absent or in progress. Do not count it complete without result reconciliation.

Portable dry-run command (repository root):

```bash
python scripts/write_factgrid_cdli_artifact_items.py \
  --artifacts published/pilots/resume_2026_10_18/batch_042_artifacts.csv \
  --statements published/pilots/resume_2026_10_18/batch_042_statements.csv \
  --results published/pilots/resume_2026_10_18/batch_042_write_results.csv \
  --plan work/batch_042_resume_plan.csv \
  --factgrid-upload-table published/pilots/resume_2026_10_18/batch_042_upload_overrides.csv \
  --only-existing-factgrid --preserve-update-labels --limit 1012 --sleep 5
```

Only the user's write command adds --write. Omit --continue-on-row-error.
On another machine, first synchronize any actual running/completed result file
before resuming; a missing result file in Git does not mean it was never run.

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

The pending window-021 and window-023 files are historical: they were completed
in batches 040 and 041. Window 024 exhausted the remaining mapped candidates in
210001–235000; batch 042 contains all its eligible rows. After reconciling 042,
stage **235001–260000** from the verified source ZIP (offset 235000, limit 25000),
then exclude manifests **001–024** and cumulative outcomes and freshly review.
No batch 043 is prepared. Held and unmatched records remain unfinished work.

```bash
python scripts/check_factgrid_api.py --timeout 15
python scripts/build_factgrid_resume_ledger.py
```

Require API JSON and FactGrid site information. Use Python 3.12+ and
requirements.txt. Keep credentials private and retain the user's current login
method. API IP allowlisting may depend on the network. Source ZIP provenance
and checksum remain in docs/factgrid_cdli_resume_2026-11-01.md.

## Overall objective

Complete CDLI items and statements first, including new unmatched items and
review holds. Then create/verify ATF Document pages and add P251 links together.
Prepare URL mappings first without adding links to missing pages. See
cdli_completion_workplan.md and the reference CDLI-ATF-L-Q894483.
