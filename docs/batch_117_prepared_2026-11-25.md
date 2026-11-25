# BDTNS batch 116 reconciled and batch 117 prepared

Batch 116 added 1,500 BDTNS IDs and skipped 6,000 existing claims in
2h37m39s. Every terminal success matches the canonical results.
After the connection reset, the item API confirmed the planned P959
on Q2040751 at revision 21988365. The resume dry run selected zero.

Batch 117 includes all 300 pending tablets from the batch 116 review.
Fresh item API checks confirmed their P692 identities and missing P959
values. Dry run and offline claim construction verified 300 additions.
Allow about 32 minutes at batch 116's pace.
