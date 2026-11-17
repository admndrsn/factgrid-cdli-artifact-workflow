# BDTNS batch 092 reconciled and batch 093 prepared

Batch 092 added 1,500 BDTNS IDs and skipped 6,000 existing statements.
All terminal success rows match the canonical results. The run took
3h29m55s, including service delays. The planned P959 on Q1989950
was verified at revision 21907763 after the service warnings.
The resume dry run selected zero items.

Batch 093 contains the 300 pending candidates from that review.
Fresh item API review confirmed all identities and missing P959 values.
The dry run reproduced the frozen plan, and offline construction
confirmed 300 P959 additions. Allow about 32 minutes at the typical
recent pace, with possible additional service delays.
