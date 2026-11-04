# Batch 041 completion — November 4, 2026

1,158 successful updates; 2,199 recorded claims added; zero errors or duplicate
result IDs. All planned IDs are recorded. Terminal output matches the canonical
CSV. Resume dry run selects zero items. Run duration: 2h 00m 49s.

The preview predicted 2,200 claims. Q2036070 / CDLI P386408 planned both
P18=Q471146 and P18=Q471149, while the writer treats P18 as single-valued.
The writer added the first language and the research-project membership, then
skipped the second language. A read-only API check on November 4 confirmed
Q471146 present and Q471149 absent. Preserve the second language as a separate
modeling/review case; do not automatically retry it. Evidence is in
batch_041_language_followup_Q2036070.csv. Future batch selection must also
exclude conflicting values proposed within the same plan for writer single-value
properties, even when the live item has no value yet.

Canonical new-Mac totals: 22,457 updates and 44,257 claims.
Cumulative written IDs including older runs: 41,974; two historical outcomes held.

The 1,158 window-023 pending candidates are now completed. Next select new
candidates within sorted source range 210001–235000, excluding review manifests
001–023 and cumulative outcomes; batch 042 is not yet prepared. Historical
review holds and unmatched source items remain separate unfinished work.
GitHub f499f77 covers through 039; completed 040–041 remain local.
