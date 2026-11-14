# Current FactGrid CDLI handoff — 2026-11-11 (through batch 078)

## Reconciled checkpoint

Completed through 078: **79,891 successful updates**, **154,903 claims added**.
Cumulative ledger: **99,408 written IDs**, one blocked_bad_sitelink and one
rewrite_ambiguous. Batch 072 completed in 10h00m11s on the final progress meter
with 4,267 updates, 7,985 claims added and 40,613 skipped. The result CSV matches
the terminal success lines and the resume dry run selected zero.

Batch 049 recovery evidence confirms its delayed one-claim write. Historical
retry snapshots must never be counted again. The batch-041 Q2036070/P386408
language modeling hold remains unresolved.

See [the reconciliation and live coverage audit](batch_072_completed_2026-11-11.md).

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

After 072, no pending eligible candidates remain from windows 044–047. The local-mapping coverage audit across source positions 1–421387 found no further unreviewed mapped candidates after these windows. This does not prove that unmatched source records lack live FactGrid items. Use the refreshed P692 audit to validate newly mapped items and investigate missing identities before a separately reviewed new-item pilot. Reconcile existing holds independently. The user has resequenced BDTNS and eBL enrichment to accompany reviewed CDLI updates. [Batch 073](batch_073_prepared_2026-11-11.md) completed with 120 successful updates, 383 claims added and zero remaining on resume. Batch 074 completed with 4,400 updates and 8,603 claims in 7h54m35s. Batch 075 completed the 492 remaining eligible candidates from that review. Batch 076 completed 735 explicit eBL and BDTNS updates. Batch 077 completed all 1,500 updates after a CSRF-token restart. Batch 078 completed the 400 pending updates. [Batch 079](batch_079_prepared_2026-11-12.md) is prepared for 1,500 further finding-spot updates, with 400 pending fresh recheck. Do not create another batch by replaying reviewed or completed IDs.

See batch_072_prepared_2026-11-11.md, windows_044_047_summary.json and coverage_audit_2026_11_11.json. Source ZIP has 421,387 records; offsets are not completion markers. Retain historical holds, including Q2036070/P386408.

## Overall objective

Complete CDLI items and statements first, including new unmatched items and
review holds. Then create/verify ATF Document pages and add P251 links together.
Prepare URL mappings first without adding links to missing pages. See
cdli_completion_workplan.md and the reference CDLI-ATF-L-Q894483.

## November 13 checkpoint

[Batch 079 reconciled and Old Assyrian batch 080 prepared](batch_080_oa_prepared_2026-11-13.md).

[Batch 082 reconciled and batch 083 prepared](batch_083_prepared_2026-11-13.md).
