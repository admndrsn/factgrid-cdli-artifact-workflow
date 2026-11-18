# BDTNS batch 100 reconciled and batch 101 prepared

Batch 100 added 1,500 BDTNS IDs and skipped 6,000 existing claims in
2h39m50s. Every success matched the canonical results. After the write
timeout the item API confirmed P959 013435 on Q1926303 at revision
21929854. The resume dry run selected zero.

Batch 101 contains all 299 pending candidates from the prior review.
Fresh checks confirmed their P692 identities and missing P959 values.
Dry run and offline construction verified 299 P959 additions. Allow
about 32 minutes with the usual five-second pause and stop on error.
