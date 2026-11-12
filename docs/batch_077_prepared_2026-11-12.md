Historical preparation: batch077 completed; see batch_077_completed_2026-11-12.md.

# Batch 076 reconciled and batch 077 prepared

Batch 076 completed 735 updates in 1h21m19s, adding 797 main claims and
skipping 8,073 plan entries. Every terminal success matched the canonical
CSV by QID and both claim counts. The log recorded connection resets before
the successful Q2156463 row. Its planned eBL ID K.6882 was confirmed in the
item API at revision 21861049. The resume dry run selected zero items.
Cumulative new-Mac totals are 77,991 updates and 151,102 added claims. The
rebuilt ledger contains 97,508 written CDLI IDs and two historical holds.

## Batch 077

The current pass prioritizes CDLI records with a supported staged finding
spot and no P695 value in the direct-claim index. This is a candidate
filter. The MediaWiki item API verified the exact P692 identity and all
planned values for each of the 1,900 reviewed candidates. The review found
1,900 eligible and zero held. The frozen batch includes 1,500 selected
items and keeps 400 eligible pending for a fresh review before use. Use the
review disposition to exclude this window from future broad selections.

Expected main additions are 1,500 P695 finding spots, 1,500 P131 project
claims and one P329 holding. The new holding also carries its inventory
qualifier. This window has no newly verified BDTNS or eBL additions under
the existing source matching rules. It continues CDLI field coverage
after the explicit identifier passes in batches 073–076.

The update-only launcher reproduced the frozen statement CSV byte for byte.
At batch 076's measured pace, allow about 2h46m. Keep five-second pauses,
stop on error, and reconcile the canonical results before advancing.
