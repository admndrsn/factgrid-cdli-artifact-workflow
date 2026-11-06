# Batch 052 prepared — 2026-11-06

All 732 window-030 pending candidates passed fresh live review. Expected additions:
921 unique main claims and 0 inventory qualifiers. Internal single-value
conflicts: none. Unknown inventory rows omitted: 0. IDs/QIDs
are unique, live CDLI identities match, and no cumulative outcomes overlap.
The launcher dry run selects 732 updates and exactly reproduces the frozen plan.
Estimated runtime: about 1h17m at batch 051's average pace.

User runs run_batch_052.sh --write. Preserve labels/descriptions, five-second pauses,
and stop-on-error. Active batch_052_write_results.csv is excluded from this checkpoint.
Synchronize actual results before another-machine resume.

After reconciling 052, advance to source positions 385001–410000 (offset 385000,
limit 25000), excluding manifests 001–030 and cumulative outcomes. All mapped
candidates in 335001–385000 were reviewed; pending files now belong to 052 and
must not be replayed independently. Historical holds and unmatched records remain work.
