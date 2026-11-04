# Batch 043 interrupted — retry checkpoint

713 updates succeeded, with 1,464 added claims. 787 of 1,500 planned items remain.
The error on P407529 / Q2065065 occurred in build_item -> wbi.item.get(qid),
before robust_write was called for that item. The traceback shows a connection/
TLS timeout during the read, not an ambiguous write. A fresh read returned the
expected P692=P407529. The retry dry run selects 787 items, includes P407529,
and excludes every recorded success.

The pre-retry CSV is preserved as batch_043_results_before_retry.csv; never merge
that historical snapshot into the canonical ledger. Keep batch_043_write_results.csv
as the live results file. Rerun the same run_batch_043.sh --write launcher. It
skips successes and stops on errors. Do not advance to 044 until 043 is reconciled.
No writes or GitHub publication were performed during this retry preparation.
