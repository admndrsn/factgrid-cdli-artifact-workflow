# BDTNS batch 112 reconciled and batch 113 prepared

Batch 112 added all 1,500 BDTNS IDs and skipped 6,000 existing claims.
The first 729 successes match the recovery snapshot. The resumed 771
updates match the terminal log and took 1h20m06s. The resume dry run
selected zero items.

Batch 113 includes all 300 pending tablets from the batch 112 review.
Fresh item API checks confirmed their P692 identities and missing P959
values. Dry run and offline claim construction verified 300 additions.
Allow about 31 minutes at the resumed batch 112 pace.
