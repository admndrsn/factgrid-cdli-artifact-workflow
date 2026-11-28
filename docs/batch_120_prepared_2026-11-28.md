# BDTNS batch 119 reconciled and batch 120 prepared

Batch 119 completed all 9,938 planned P959 additions, with 39,752
existing claims skipped. Terminal successes across the resumed runs
match the canonical results, with unique CDLI/QID identities and no
remaining errors. The resume dry run selects zero. The final run added
122 IDs in 12m55s.

The next batch retains the 10,000-item ceiling, five-second write interval,
serial writes, preserved labels, identity/conflict checks, and resumable
per-item results. No FactGrid writer was started by the assistant.

Batch 120 reviewed 10,000 candidates and selected 9,998 tablets for
9,998 P959 additions. Fresh ownership and item API checks confirmed their
P692 identities and missing P959 values. The other two need project claims
and are deferred from this ID-only batch. Dry run and offline claim
construction passed. At the final batch 119 run's measured pace, allow
about 17h39m, plus API delays and interruptions.

Use the preparation workspace launcher `outputs/run_batch_120.sh --write`.
