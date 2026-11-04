> Historical preparation record; this batch is complete. See the current November 4 resume guide.

# Batch 040 — prepared, not written

1,500 unique identity-verified existing items, with 2,950 expected main statement additions and no expected inventory-qualifier additions. The selected CDLI IDs and QIDs are unique. The final launcher dry run selects exactly 1,500 updates and its effective plan matches the prepared statement inputs. Two unknown inventory placeholders were omitted.

Composition: 760 eligible items from window 022 (sorted source range 185001–210000), including all 501 previously pending window-021 candidates, plus 740 items from window 023 (range 210001–235000). All cumulative outcomes and previous reviewed holds were excluded. Window 022 reviewed all 811 remaining mapped candidates in its range: 760 eligible, 49 already complete, 2 blocked. This exhausts unreviewed mapped candidates in that range, not all unmatched source items or held metadata.

Window 023 reviewed 2,500 candidates and found 1,898 eligible. Its remaining 1,158 are saved in window_023_remaining_pending_recheck_artifacts.csv and the corresponding statements file. Recheck these first before a subsequent batch. The old window-021 pending files are historical: their IDs are now included in batch 040. Do not replay them independently.

Expected additions: 1,373 finding spots, 1 language, 9 periods, 1,493 research-project memberships, 74 genres. Actual counts may differ if live data changes.

## Terminal command (this machine)

```bash
bash "/Users/aa/Documents/Codex/2026-11-01/i-q/outputs/factgrid-resume/run_batch_040.sh" --write
```

Omit --write to dry run. Credentials are prompted privately if not already in the shell. The launcher preserves labels and descriptions, waits five seconds between writes, stops on errors, and records canonical results under published/pilots/resume_2026_10_18/batch_040_write_results.csv. Frozen reviewed statements use a header-only upload override CSV for portability. At the recent observed pace, allow approximately 2.5–3 hours. On interruption, inspect the error/timeout stage and reconcile results before retrying; recorded successes are skipped.

## Checkpoint and next steps

Completed batches through 039 were published on main as f499f773084a5785282aa15587854ba81750674f. GitHub and the local checkout were reconciled with an identical tree. That checkpoint records 19,799 updates and 39,108 added claims; cumulative written IDs: 39,316.

This batch 040 preparation and review windows 022–023 are currently local. No FactGrid writes were made during preparation. After the run, reconcile results, rebuild the ledger, update the handoff and publish the next checkpoint. Handle the 1,158 pending candidates before selecting new candidates in 210001–235000 with manifests 001–023 and cumulative outcomes excluded. Retain unresolved holds separately. ATF pages and P251 remain a later phase.
