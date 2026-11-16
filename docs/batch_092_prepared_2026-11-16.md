# BDTNS batch 091 reconciled and batch 092 prepared

Batch 091 completed 300 updates in 31m30s. The terminal log and canonical
CSV agree by item and claim count. The writer added 300 BDTNS IDs and skipped
1,200 existing claims. Resume selected zero. Batches 090 and 091 together
added 1,800 identifiers, reported separately from CDLI completion totals.

Batch 092 uses fresh P692 and P959 ownership checks, excludes prior BDTNS
review windows and requires live item review before selection.
The item API confirmed all 1,800 identities and missing P959 values.
The frozen plan has 1,500 P959 additions, leaving 300 eligible pending.
Dry run and offline construction both verified the plan. Allow about
2h38m at the batch 091 pace. The user runs the update-only launcher.
