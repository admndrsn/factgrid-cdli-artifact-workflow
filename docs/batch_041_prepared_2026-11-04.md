> Historical preparation record; this batch is complete. See the current November 4 resume guide.

# Batch 041 prepared — November 4, 2026

All 1,158 pending window-023 candidates passed fresh live review: matching CDLI identities, no conflicts, no missing-qualifier holds. Each CDLI ID and QID is unique; none overlap cumulative results through completed batch 040.

Expected additions: 2,200 main statements (1,021 finding spots, 5 languages, 5 periods, 1,158 research-project memberships, 11 genres). No new inventory qualifiers expected. One unknown inventory placeholder was omitted. Actual counts can differ if live data changes.

The tested launcher selects exactly 1,158 updates. Its dry-run plan matches the prepared inputs. No writes have been made.

```bash
bash "/Users/aa/Documents/Codex/2026-11-01/i-q/outputs/factgrid-resume/run_batch_041.sh" --write
```

Allow roughly two hours. The launcher prompts privately for credentials if needed, preserves labels/descriptions, pauses five seconds between writes, stops on errors, and records canonical batch_041_write_results.csv. Omit --write for a dry run. Frozen reviewed statements use a header-only upload override file to prevent local override drift.

After completion: reconcile results and rebuild the ledger. The old window_023_remaining_pending_recheck files are now represented by batch 041; do not select them independently. Continue new candidate review within range 210001–235000, excluding manifests 001–023 and cumulative outcomes. This does not imply the range is complete. Historical holds and unmatched source items remain separate work.

GitHub checkpoint f499f77 covers completed batches through 039. Batch 040 completion and batch 041 preparation remain local until the next publication.
