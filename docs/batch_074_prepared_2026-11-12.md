# Batch 074 overnight CDLI update

Batch 073 completed in 12m34s with 120 successful updates, 383 claims added
and 1,250 skipped. Every terminal success matched the canonical result CSV,
and the resume dry run selected zero. The rebuilt ledger contains 91,881
written CDLI IDs and two historical held outcomes. New-Mac totals are 72,364
successful updates and 141,046 claims added.

Batch 074 is prepared for user execution. It contains 4,400 existing-item
updates and 8,603 expected unique main additions, including 4,400 BDTNS IDs
(P959) and 3,732 eBL IDs (P1173). The remaining 668 items have an eligible
BDTNS match without an eligible eBL match under the pilot's source rules.
At the 073 pace, expect about 7h41m. Keep five-second pauses, stop on error,
and use the private login from the launcher.

Fresh MediaWiki review covered 4,900 distinct candidates outside the ledger
and prior manifests, using only explicit CDLI/QID mappings. Eight live period
conflicts were held. All 3,732 eligible dual-ID candidates are in the batch.
The 492 eligible candidates beyond the 4,400 limit can be considered after
a fresh review. The external ID index was refreshed after 073, and claims
and identity on the selected items were checked in the item API. The source
crosswalk preserves exact identifier strings and records the source URL and
JSONL row. The dry run reproduced the frozen statement CSV byte for byte.

After execution, compare terminal outcomes to the canonical result CSV,
resolve any interruption before retrying, rebuild the ledger and check for
zero remaining. The checkpoint contains the reviewed preparation and the
completed 073 results. Treat 074 as pending until reconciled.
