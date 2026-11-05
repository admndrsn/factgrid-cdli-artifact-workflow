# Batch 049 prepared — 2026-11-05

Fresh read-only review verified all 256 window-028 pending candidates. Batch 049
expects 533 unique main claims and 13 inventory qualifiers. No live conflicts,
missing-qualifier holds, internal single-value conflicts, or inventory placeholders
occur in the selected set. IDs and QIDs are unique; no cumulative outcome overlaps.
The dry run selects 256 updates and exactly reproduces the frozen statement plan.

Use the local run_batch_049.sh launcher with --write. It preserves labels and
descriptions, pauses five seconds, and stops on error. User performs writes.
Active batch_049_write_results.csv is excluded from this checkpoint.

After reconciling 049, continue fresh selection within source positions
310001–335000, excluding manifests 001–028 and cumulative outcomes. Window 028
was capped at 3,000 candidates, so this range is not exhausted. Its pending files
are now represented by batch 049 and must not be replayed independently.
Historical holds and unmatched source records remain unfinished work.
