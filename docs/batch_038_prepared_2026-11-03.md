> Historical preparation record. This batch is now complete; see the current resume guide for totals and next steps.

# Batch 038 — prepared, not written

Prepared November 3, 2026 against GitHub checkpoint 5f38c38.

291 existing FactGrid items passed fresh live identity and claim review. Expected additions: 564 main statements (291 P131 research-project memberships, 271 P695 finding spots, 2 P329 present holdings), plus one P10 qualifier on a new holding. Actual write counts may differ if live data changes.

Source: sorted positions 185001–210000 in the verified original ZIP (SHA256 7c12ab12a76de4bf7efd4c2c7d5642320dd8d00f220a3662dc00cdef30387e3c). All manifests 001–019 and all cumulative outcomes were excluded. Window 020 reviewed 1,500 unique IDs/QIDs. 1,009 lacked a live CDLI identity, 110 had conflicts, and one had a missing-qualifier repair; categories overlap. Held cases are saved separately. Two unknown inventory placeholders were omitted from batch statement inputs.

API probe returned JSON and FactGrid site information. The canonical ledger still contains 38,525 written IDs; new-Mac totals remain 19,008 updates and 37,498 claims. No writes, commits, or GitHub publication were performed.

## Files and portability

The ZIP paths are relative to the repository root. The clean working checkout is:
/Users/aa/Documents/Codex/2026-11-01/i-q/work/factgrid-cdli-artifact-workflow

Batch statements freeze the effective reviewed plan, including this machine's legacy upload-table overrides. The header-only batch_038_upload_overrides.csv prevents a different machine's local upload table from changing that reviewed plan. The final dry-run plan matches the prepared statement values exactly. Full raw live entity evidence remains under work/window_020_review_2026_11_03/ in the clean checkout.

## Validated dry-run command

Run from the repository root with Python 3.12+ and its dependencies:

```bash
python scripts/write_factgrid_cdli_artifact_items.py \
  --artifacts published/pilots/resume_2026_10_18/batch_038_artifacts.csv \
  --statements published/pilots/resume_2026_10_18/batch_038_statements.csv \
  --results published/pilots/resume_2026_10_18/batch_038_write_results.csv \
  --plan published/pilots/resume_2026_10_18/batch_038_dry_run_plan.csv \
  --factgrid-upload-table published/pilots/resume_2026_10_18/batch_038_upload_overrides.csv \
  --only-existing-factgrid --preserve-update-labels --limit 291 --sleep 5
```

This command was run without --write and selected exactly 291 updates. The results CSV deliberately does not exist yet. Writing requires a separate instruction; the same command would use --write, with private credentials and no --continue-on-row-error. Recheck API health and refresh the review if resuming later. Preserve labels/descriptions and stop on errors.

After execution, reconcile canonical results and rebuild the ledger. Batch 038 remains pending until then. Include window_020_reviewed_items.csv in future range exclusions, while retaining this batch's pending selection. Do not automatically advance to the next source range. Review holds remain separate.
