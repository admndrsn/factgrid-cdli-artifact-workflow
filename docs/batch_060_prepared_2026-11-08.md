Historical: batch 060 completed. See batch_060_completed_2026-11-08.md.

# Batch 060 prepared — 2026-11-08

1,500 freshly reviewed existing items, 2,964 expected unique main claims,
3 inventory qualifiers. Selected IDs/QIDs are unique, identities match live
P692 claims, and no cumulative outcomes or earlier manifests overlap. Conflicting
single-value plans are held separately. Omitted inventory placeholders: 0.
Dry run selects 1,500 updates and exactly reproduces the frozen statement plan.
Allow roughly 2h40m–3h20m based on recent batches; runtime is not guaranteed.

Window 036 reviewed 2,500 candidates in source positions 1–110000, excluding
manifests 001–035 and cumulative outcomes. 740 eligible candidates remain
in pending-recheck files. Freshly review those after reconciling 060, then continue
within 1–110000 excluding manifests 001–036 and cumulative outcomes. This review
limit did not exhaust the range. Holds and unmatched records remain unfinished.

User runs run_batch_060.sh --write. Preserve labels/descriptions, five-second pauses,
and stop-on-error. Active results are excluded; synchronize actual results before
another-machine resume. Assistant made no FactGrid writes.
