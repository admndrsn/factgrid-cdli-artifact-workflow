> Historical preparation record. This batch is now complete; see the current resume guide for totals and next steps.

# Batch 039 prepared — not written

Fresh window 021 reviewed 1,500 candidates (1,496 distinct QIDs) from sorted source range 185001–210000, excluding manifests 001–020 and cumulative outcomes through completed batch 038. Live review found 1,001 eligible items. Batch 039 contains the first 500; both CDLI IDs and QIDs are unique. The remaining 501 are saved in window_021_remaining_pending_recheck_artifacts.csv and the corresponding statements file. Refresh those before selecting batch 040; do not lose them by simply excluding the whole reviewed manifest.

Expected additions for batch 039: 1,046 main statements and 52 inventory qualifiers on new holding statements. Breakdown: 457 finding spots, 12 languages, 5 materials, 4 periods, 52 present holdings, 500 research-project memberships, 16 genres. Three unknown inventory placeholders were omitted. Actual counts can differ if live claims change.

The final launcher dry run selected exactly 500 updates. Its effective statement plan matches the prepared inputs. All selected identities matched live P692 claims; conflict and missing-qualifier holds remain excluded. Window-level counts: 59 conflicting items, 49 missing CDLI IDs, one missing-qualifier case; categories may overlap. Full review evidence is retained locally.

Run on this machine:

```bash
bash "/Users/aa/Documents/Codex/2026-11-01/i-q/outputs/factgrid-resume/run_batch_039.sh" --write
```

Omit --write for a dry run. The launcher prompts privately for credentials if needed, preserves labels/descriptions, waits five seconds between writes, and stops on errors. It records results in the clean repository's canonical batch_039_write_results.csv. Frozen reviewed statements and a header-only upload override file prevent other local upload tables from changing the plan. No writes or GitHub publication were performed during preparation.

Next: reconcile batch 039 results and rebuild the ledger, then freshly check the 501 remaining window-021 candidates. Remain within the current source range until all remaining candidates are accounted for. Held and unmatched items require separate work.

Longer-term workplan: complete items and statements, including missing-item creation and review holds, before ATF pages. The user-provided ATF reference is https://database.factgrid.de/wiki/CDLI-ATF-L-Q894483, linked from Q894483 by P251 and matching CDLI P020415. See cdli_completion_workplan.md for the verified page structure.
