Historical: batch 057 completed. See batch_057_completed_2026-11-08.md.

# Batch 057 prepared — 2026-11-08

All 582 window-034 pending candidates passed fresh live review. Expected additions:
1,157 unique main claims and 0 inventory qualifiers. No internal single-value
conflicts; 1 unknown inventory rows omitted. IDs/QIDs are unique,
live CDLI identities match, and no cumulative outcomes overlap. The dry run selects
582 updates and exactly reproduces the frozen plan. Allow about 1h02m.

After reconciling 057, continue within source positions 1–110000 excluding manifests
001–034 and cumulative outcomes. Window 034's 3,200-candidate limit did not exhaust
the range. Its pending files now belong to 057; never replay independently.
Historical holds and unmatched records remain unfinished work.

User runs run_batch_057.sh --write. Preserve labels/descriptions, five-second pauses,
and stop-on-error. Active results are excluded; synchronize actual results before
another-machine resume. Assistant made no FactGrid writes.
