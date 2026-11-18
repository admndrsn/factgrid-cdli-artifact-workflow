# BDTNS batch 101 reconciled and batch 102 prepared

Batch 101 added all 299 BDTNS IDs and skipped 1,196 existing claims.
The first 26 successes match the saved snapshot. The resumed 273-row
run matches the terminal log and took 28m36s. The resume dry run selected
zero items. The BDTNS enrichment ledger reports these additions separately
from CDLI completion totals.

Fresh ownership checks and item API review verified 1,800 eligible
existing tablets. Batch 102 freezes 1,500 P959 additions and leaves
300 pending. The dry run and offline claim construction verified the
plan. Allow about 2h37m at the resumed batch 101 pace.
