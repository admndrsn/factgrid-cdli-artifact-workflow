# Batch 074 reconciled and batch 075 prepared

Batch 074 completed 4,400 existing-item updates in 7h54m35s, adding 8,603
main claims and skipping 51,539 plan entries. Every successful terminal row
matched the canonical CSV by QID and both claim counts. Two write timeouts
preceded successful rows for Q2179926 and Q2180815. The live item API
confirmed both planned main claims on each item at revisions 21852917 and
21854208, respectively. The completed launcher's dry run selected zero.

Cumulative new-Mac totals are 76,764 updates and 149,649 claims added.
The rebuilt ledger contains 96,281 written CDLI IDs and two held outcomes.

## Batch 075

A fresh live review of the 492 eligible pending candidates from the batch
074 window confirmed every P692 identity and found no holds. The frozen plan
contains 656 expected main additions: 492 BDTNS identifiers, 76 finding
spots and 88 research-project claims. These pending records have no eligible
eBL cross-reference under the source matching rules. The earlier eight
period conflicts remain held. The dry run reproduced the frozen statement
CSV byte for byte. At the batch 074 measured pace, allow about 53 minutes.

The user runs the update-only launcher with the private login, a five-second
pause and stop-on-error behavior. Reconcile the canonical result CSV against
the terminal log before proceeding to more candidates. After this batch, look
for independently verified CDLI and external-ID matches across the remaining
indexed source candidates and continue holding ambiguous identities.
