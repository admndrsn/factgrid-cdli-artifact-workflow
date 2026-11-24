# BDTNS batch 108 reconciled and batch 109 prepared

Batch 108 added all 1,500 BDTNS IDs and skipped 6,000 existing claims.
The first 655 successes match the saved recovery snapshot. The resumed
845 updates match the terminal log and took 1h29m14s. The resume dry run
selected zero.

Batch 109 includes all 300 pending tablets. Fresh item API checks
confirmed their P692 identities and missing P959 values. Dry run and
offline construction verified 300 additions. Allow about 32 minutes
at the resumed batch 108 pace.
