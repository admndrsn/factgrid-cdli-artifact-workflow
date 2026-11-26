# BDTNS batch 118 reconciled and batch 119 prepared

Batch 118 completed all 9,778 planned P959 additions, with 39,112
existing claims skipped. All terminal successes across the resumed runs
match the canonical results, with unique CDLI/QID identities and no
remaining errors. The resume dry run selects zero. The final run added
2,635 IDs in 5h08m06s. Eight items affected by recovered connection
errors were independently checked through the item API and have the
expected P959 values.

The next batch retains the 10,000-item ceiling, five-second write interval,
serial writes, preserved labels, identity/conflict checks, and resumable
per-item results. No FactGrid writer was started by the assistant.

Batch 119 reviewed 10,000 candidates and selected 9,938 tablets for
9,938 P959 additions. Fresh ownership and item API checks confirmed their
P692 identities and missing P959 values. The other 62 need project claims
and are deferred from this ID-only batch. Dry run and offline claim
construction passed. At the final batch 118 run's measured pace, allow
about 19h22m, with actual runtime dependent on API delays and interruptions.

Use the preparation workspace launcher `outputs/run_batch_119.sh --write`.
