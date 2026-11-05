# Batch 046 CSRF retry checkpoint

361 written updates, 725 added claims; 1,139 items remain. P454023/Q1986042
was rejected with Invalid CSRF token. Live read confirms the expected CDLI
identity; both proposed additions (P695=Q390161 and P131=Q1894741) remain absent.
The pre-retry CSV is preserved as batch_046_results_before_retry.csv; never
count this historical snapshot alongside canonical results.

Retry dry run selects 1,139 unique IDs, excludes all successes, and includes
the rejected item. Rerun run_batch_046.sh --write to establish a fresh login;
keep the same canonical result file and stop-on-error behavior. No writes were
made during retry preparation. Do not advance to batch 047 until reconciled.
