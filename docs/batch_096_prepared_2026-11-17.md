# BDTNS batch 095 reconciled and batch 096 prepared

Batch 095 added 300 BDTNS IDs and skipped 1,200 existing claims in
31m30s. The initial attempt was rejected at login before any writes.
Every successful row matches the canonical CSV. The resume dry run
selected zero. Batches 090–095 added 5,400 identifiers, reported
separately from the CDLI completion ledger.

Fresh P692/P959 index checks and item API review identified 1,800
eligible tablets. Batch 096 freezes 1,500 P959 additions and leaves
300 pending. Dry run and offline construction verified the plan.
Allow about 2h38m at batch 095's pace.
