# Batch 089 reconciled and BDTNS batch 090 prepared

Batch 089 completed all 130 period updates in 13m33s. Terminal and
canonical results agree, with 130 additions and 1,083 skipped plan entries.
Resume selected zero. The CDLI ledger has 112,203 written IDs and two
historical holds. New-Mac CDLI totals are 92,686 updates and 178,073 claims.

Batch 090 uses one-to-one BDTNS source links and refreshed P692/P959
ownership checks. Item API review verified 1,800 existing tablet identities
and missing P959 values. The first 1,500 are frozen, with 300 eligible
pending. Dry run and offline construction confirmed exactly 1,500 P959
additions. The launcher retains five-second spacing and stop on error.
Allow about 2h36m at the batch 089 pace. The ledger builder reports BDTNS
enrichment separately because it can revisit previously written items.
