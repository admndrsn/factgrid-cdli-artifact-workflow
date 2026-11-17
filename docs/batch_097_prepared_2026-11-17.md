# BDTNS batch 096 reconciled and batch 097 prepared

Batch 096 added 1,500 BDTNS IDs and skipped 6,000 existing claims in
2h40m37s. Every successful row matches the canonical results. After the
write timeout, the item API confirmed P959 032260 on Q2007318 at revision
21914300. The resume dry run selected zero. Batches 090–096 added 6,900
BDTNS IDs, reported separately from the CDLI completion ledger.

Batch 097 contains all 300 pending tablets from the batch 096 review.
Fresh item API review confirmed their CDLI identities and missing P959
values. Dry run and offline construction verified 300 P959 additions.
Allow about 32 minutes at batch 096's pace.
