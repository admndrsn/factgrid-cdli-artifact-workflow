# BDTNS batch 104 reconciled and batch 105 prepared

Batch 104 added 1,500 BDTNS IDs and skipped 6,000 existing claims in
2h36m19s. The terminal log matches the canonical results row for row.
The resume dry run selected zero items.

Batch 105 includes all 300 pending tablets from the batch 104 review.
Fresh item API checks confirmed matching P692 and missing P959 values.
Dry run and offline claim construction verified 300 additions. Allow
about 31 minutes at batch 104's pace. Use five-second pauses and stop
on error.
