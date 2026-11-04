# Batch 043 completed after retry

Canonical result: 1,500 written updates, 2,852 added claims, no errors. Resume
dry run selects zero rows. The first run wrote 713 items and 1,464 claims,
then timed out reading P407529/Q2065065 before its write. The retry wrote the
remaining 787 items and 1,388 claims in 1h 22m 19s. Terminal QIDs match the
canonical results. The historical batch_043_results_before_retry.csv is preserved
but must never be counted with the canonical result file.

New-Mac totals: 24,969 updates and 48,907 claims. Cumulative ledger: 44,486 written
CDLI IDs plus two historical held outcomes. Batch 044 covers the final 380
pending eligible candidates in this range, subject to fresh review.
