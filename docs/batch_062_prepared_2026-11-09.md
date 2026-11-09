Historical: batch 062 completed. See batch_062_completed_2026-11-09.md.

# Batch 062 prepared — 2026-11-09

All 678 window-037 pending candidates passed fresh live review. Expected additions:
1,355 unique main claims and 0 inventory qualifiers. No internal single-value
conflicts; 0 unknown inventory rows omitted. IDs/QIDs are unique,
live CDLI identities match, and no cumulative outcomes overlap. The dry run selects
678 updates and exactly reproduces the frozen plan. Allow about 1h12m.

After reconciling 062, continue within source positions 1–110000 excluding manifests
001–037 and cumulative outcomes. Window 037's 4,000-candidate limit did not exhaust
the range. Its pending files now belong to 062; never replay independently.
Historical holds and unmatched records remain unfinished work.

User runs run_batch_062.sh --write. Preserve labels/descriptions, five-second pauses,
and stop-on-error. Active results are excluded; synchronize actual results before
another-machine resume. Assistant made no FactGrid writes.
