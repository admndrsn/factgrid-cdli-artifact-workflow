# Batch 066 prepared — 2026-11-10

All 565 window-040 pending candidates passed fresh live review. Expected additions:
1,121 unique main claims and 0 inventory qualifiers. No internal single-value
conflicts; 1 unknown inventory rows omitted. IDs/QIDs are unique,
live CDLI identities match, and no cumulative outcomes overlap. The dry run selects
565 updates and exactly reproduces the frozen plan. Estimated runtime: about
1h at batch 065's pace. This batch finishes the pending group.

User runs run_batch_066.sh --write. Preserve labels/descriptions, five-second pauses,
and stop-on-error. Active results are excluded. Synchronize actual results before
another-machine resume. No FactGrid writes were made by the assistant.

After reconciling 066, continue within source positions 1–110000, excluding
manifests 001–040 and cumulative outcomes. Window 040's 2,500-candidate limit
did not exhaust the range. Its pending files now belong to 066 and must not be
replayed independently. Window 031 found 803 complete and 500 conflicting items
at the ZIP end, with no eligible additions. Holds and unmatched records remain work.
