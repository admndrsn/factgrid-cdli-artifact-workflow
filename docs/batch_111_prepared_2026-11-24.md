# BDTNS batch 110 reconciled and batch 111 prepared

Batch 110 added 1,500 BDTNS IDs and skipped 6,000 existing claims in
2h39m38s. Every terminal success matches the canonical results.
The item API confirmed P959 046432 on Q1996915 at revision 21976248
after the write warning. The resume dry run selected zero.

Batch 111 includes all 300 pending tablets. Fresh item API checks
confirmed matching P692 and missing P959 values. Dry run and offline
claim construction verified 300 additions. Allow about 32 minutes
at batch 110's pace.
