# Batch 083 reconciled and batch 084 prepared

Batch 083 completed all 4,480 updates, adding 9,005 claims and skipping
36,783 plan entries. The final 2,743 rows match the resumed terminal
log and took 4h46m19s. The first 1,737 match the saved snapshot.
The earlier write timeout on Q1921882 was reconciled against revision
21884697, which contains both planned claims. The resume dry run
selected zero. The rebuilt CDLI ledger contains 106,888 written IDs.
New-Mac totals are 87,371 updates and 169,915 claims added.

Batch 084 includes all 520 remaining candidates from the prior review.
Fresh item API review confirmed identity and no conflicts. The dry run
reproduced the frozen plan and offline construction verified 520 P695
finding spots and 520 P131 projects. Expect about 54 minutes at the
recent pace, with five-second pauses and stop on error.
