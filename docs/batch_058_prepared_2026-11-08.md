Historical: batch 058 completed. See batch_058_completed_2026-11-08.md.

# Batch 058 prepared — 2026-11-08

1,500 freshly reviewed existing items, 2,989 expected unique main claims,
24 inventory qualifiers. Selected IDs/QIDs are unique, identities match live
P692 claims, and no cumulative outcomes or earlier manifests overlap. Conflicting
single-value plans are held separately. Omitted inventory placeholders: 3.
Dry run selects 1,500 updates and exactly reproduces the frozen statement plan.
Allow roughly 2h40m–3h20m based on recent batches; runtime is not guaranteed.

Window 035 reviewed 2,500 candidates in source positions 1–110000, excluding
manifests 001–034 and cumulative outcomes. 712 eligible candidates remain
in pending-recheck files. Freshly review those after reconciling 058, then continue
within 1–110000 excluding manifests 001–035 and cumulative outcomes. This review
limit did not exhaust the range. Holds and unmatched records remain unfinished.

User runs run_batch_058.sh --write. Preserve labels/descriptions, five-second pauses,
and stop-on-error. Active results are excluded; synchronize actual results before
another-machine resume. Assistant made no FactGrid writes.
