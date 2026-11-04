# Batch 043 prepared — November 4, 2026

1,500 unique CDLI IDs and FactGrid QIDs passed fresh live review, with 2,852
expected main claims and 48 inventory qualifiers on new holding statements.
The tested launcher selects 1,500 updates; the effective plan matches the prepared
inputs. Two unknown inventory placeholders were omitted. Planned values were
checked for conflicts under the writer's single-value rules; no such items are
in the batch. One conflicting-plan ID in the whole window is held separately.

Window 025 reviewed all 2,891 remaining mapped candidates in sorted source range
235001–260000, excluding manifests 001–024 and cumulative outcomes through 042.
It found 1,880 eligible items; the first 1,500 form batch 043. The other 380 are
saved in window_025_remaining_pending_recheck_artifacts.csv and the corresponding
statements file. Recheck those first before selecting another batch.

Expected additions: 1,341 finding spots, 4 languages, 48 present holdings,
1,459 research-project memberships, plus 48 P10 qualifiers. Actual write counts
may change if live data changes. Review-window hold categories can overlap.

```bash
bash "/Users/aa/Documents/Codex/2026-11-01/i-q/outputs/factgrid-resume/run_batch_043.sh" --write
```

The user runs writes in Terminal. Private credentials, five-second pauses,
preserve-update-labels, only-existing-factgrid, and stop-on-error behavior remain.
Portable batch inputs and the header-only upload override file are in
published/pilots/resume_2026_10_18/. Batch 043 write results are explicitly
excluded from this publication while it may be running. Reconcile the real
result file before counting completion or resuming on another machine.

After 043 and the 380 pending candidates are resolved, this range has no
unreviewed mapped candidates remaining. Historical holds and unmatched source
records remain separate unfinished work. Next new range after that is
260001–285000 (offset 260000); exclude manifests 001–025 and cumulative outcomes.
