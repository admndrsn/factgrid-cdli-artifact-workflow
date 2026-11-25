# BDTNS batch 117 reconciled and batch 118 prepared

Batch 117 added 300 BDTNS IDs and skipped 1,200 existing claims in
35m45s. Every terminal success matches the canonical results.
After the write timeout, the item API confirmed the planned P959 on
Q2041872 at revision 21990099. The resume dry run selected zero.

Following the user's report of the FactGrid administrator's recommendation,
future batches may contain at most 10,000 items. This changes the item
ceiling while retaining the five-second write interval, serial writes,
stop-on-error behavior and resumable per-item results. Only verified
matches qualify. Archibab batches may use the same ceiling after identity
matching and live review, rather than treating unlinked source IDs as
ready additions.

Batch 118 reviewed 10,000 candidate items and selected 9,778 tablets for
9,778 P959 additions. All have the expected live P692 and no conflicting
P959. The other 222 also need research-project claims and are deferred
from this ID-only batch. Dry run and offline claim construction passed.
At batch 117's measured pace, allow about 19h25m, with actual runtime
dependent on API response times. The launcher selects at most 10,000 items.

Run `outputs/run_batch_118.sh --write` from the preparation workspace.
The assistant has not started a FactGrid writer.
