# Batch 061 expanded preparation — 2026-11-08

Batch 061 retry (November 9): 1,020 updates / 2,008 claims saved; 2,580 items remain after a read timeout before writing. See batch_061_retry_2026-11-09.md. Synchronize active results before another-machine resume.

Expanded before writing at the user's request for roughly six to eight hours away.
3,600 existing items: the original 740 window-036 candidates plus 2,860 freshly
reviewed window-037 candidates. Expected additions: 7,117 unique main claims
and 1 inventory qualifiers. At recent pace allow roughly 6¼–8 hours;
server/session errors can still stop the run early. Five-second pacing retained.

Selected CDLI IDs and QIDs are unique, identities match live, and no cumulative
outcomes overlap. New candidates exclude review manifests 001–036. Planned
single-value conflicts held: 0 IDs; inventory placeholders omitted:
0. Dry run selects 3,600 updates and exactly reproduces the frozen
statement plan. No result file existed when the preparation was expanded.

Window 037 reviewed 4,000 candidates in source positions 1–110000. 678 eligible
candidates remain in pending-recheck files. After reconciling 061, freshly review
those first, then continue in 1–110000 excluding manifests 001–037 and cumulative
outcomes. The range is not exhausted. Window-036 pending files belong to 061.
Historical holds and unmatched records remain unfinished work.

The same run_batch_061.sh --write command now selects 3,600 items. Preserve labels,
descriptions and stop-on-error. Active results are excluded from publication;
synchronize actual results before resuming on another machine. No assistant writes.
