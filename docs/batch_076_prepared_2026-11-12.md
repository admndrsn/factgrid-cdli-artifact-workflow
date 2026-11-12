# Batch 075 reconciled and batch 076 prepared

Batch 075 completed 492 updates in 50m44s, adding 656 claims and skipping
5,286. Each terminal success matched its canonical CSV row. All planned
CDLI ID and QID pairs were written and the resume dry run selected zero.
The rebuilt ledger contains 96,773 written IDs plus two historical holds.
New-Mac totals are 77,256 updates and 150,305 claims added.

Batch 076 is prepared for the user to run. The refreshed P692/P959/P1173
index yielded 735 new candidates after exclusion of prior window manifests,
the cumulative ledger and the batch 074 dispositions. The MediaWiki item
API confirmed their identities and reviewed the proposed claims. All 735
were eligible, and the dry run reproduced the frozen statement plan.

The batch has 797 expected main additions: 696 eBL IDs, 41 BDTNS IDs,
33 research-project claims and 27 finding spots. Two items receive both
external IDs. The eBL join uses the explicit `externalNumbers.cdliNumber`
and `_id` fields in the local eBL Fragmentarium `10018951/fragments.json`
export. The BDTNS join uses the explicit `cross_ids.cdli` field in the
BDTNS JSONL export. The crosswalk preserves identifier spelling and source
URLs. Shared identifiers, source disagreements and live conflicts are
excluded from enrichment. This pass uses the available explicit source
references and leaves corpus-wide identity and field coverage open.

Run the update-only launcher with five-second pauses and stop on error.
At the batch 075 measured pace, allow approximately 76 minutes. Reconcile
the canonical results before advancing.
