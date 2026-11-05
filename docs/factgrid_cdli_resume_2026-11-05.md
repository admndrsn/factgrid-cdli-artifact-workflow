# Current FactGrid CDLI handoff — 2026-11-05 (through batch 047)

## Reconciled checkpoint

The pilot and batches 002–047 record **28,796 successful updates** and
**55,579 added claims**. All 47 canonical new-Mac result files are written with
no errors. The cumulative ledger has **48,313 written CDLI IDs**, plus one
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

## Prepared/running batch 048

Batch 047 completed: 436 updates and 763 claims, no errors; resume dry run selects zero.
Totals through 047: 28,796 updates and 55,579 claims. Cumulative ledger: 48,313 written IDs plus two historical held outcomes.

Batch 048 contains 1,500 freshly reviewed existing items from source positions 310001–335000, with 2,670 expected main claims and seven inventory qualifiers. Four unknown inventory placeholders were omitted. No internal single-value plan conflicts were found. The launcher dry run selects 1,500 updates and reproduces the frozen statement plan exactly. Labels/descriptions are preserved; five-second pauses and stop-on-error remain enabled.

Window 028 reviewed 3,000 candidates: 283 blocked, 790 already complete, 1,756 eligible for additions. These categories can overlap for already-complete/conflicted items. The first 1,500 eligible items form batch 048; 256 remain in pending-recheck files. Freshly review that remainder after reconciling 048, then continue within 310001–335000 excluding manifests 001–028 and cumulative outcomes. The 3,000-candidate limit means this range is not exhausted. Historical holds and unmatched records remain unfinished work.

User runs writes; batch_048_write_results.csv is excluded from this preparation checkpoint. Reconcile actual results before resuming on another machine. Never replay pending files independently of completed batches.

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

After reconciling 048, freshly review window-028's 256 pending items first.
Then continue within **310001–335000**, excluding manifests **001–028** and
cumulative outcomes. The 3,000-candidate review limit did not exhaust this range.
Window-027 and earlier pending files are historical/completed. Holds and
unmatched records remain unfinished work.

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
