# FactGrid CDLI Artifact Workflow

Scripts, lookup tables, reviewed staging data, and resumable checkpoints for
enriching CDLI cuneiform artifact records in FactGrid.

## Current handoff — 2026-11-03

Start with [the current resume guide](docs/factgrid_cdli_resume_2026-11-03.md).

- Batches through **039** are reconciled: **19,799 successful updates** and
  **39,108 claims added**, excluding older runs.
- The cumulative ledger contains **39,316 written CDLI IDs**, plus two historical
  held outcomes. All 39 canonical new-Mac result files have no remaining errors.
- **501 window-021 candidates** await fresh review before batch 040. These pending
  inputs are tracked; no new write batch is approved or prepared yet.
- Current sorted source range: **185001–210000**. After the pending selection,
  exclude manifests 001–021 and cumulative outcomes to find new candidates.
- Verify API JSON access on every resume. Reviewed holds and unmatched source
  records remain separate unfinished work.
- [Completion workplan](docs/cdli_completion_workplan.md): items and statements
  first, then ATF pages and P251 links together. Prepare URL mappings beforehand.

## Setup

Use Python 3.12 or newer:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

requirements-resume-2026-11-01.txt records the installed working environment.
The writer prompts privately for credentials or uses FG_USER and FG_PASS from
the current shell. Never commit credentials or place passwords in commands.
The current login is retained by user preference; its main-account deprecation
warning is documented in the resume guide.

## Safe resume workflow

1. Run `python scripts/check_factgrid_api.py --timeout 15`; require json=ok.
2. Run `python scripts/build_factgrid_resume_ledger.py` to reconstruct results.
3. Refresh the pending candidates using the current guide's read-only review
   command. Hold identity mismatches, claim conflicts, and qualifier repairs.
4. Inspect a dry run before writing. Use --only-existing-factgrid,
   --preserve-update-labels, --sleep 5, and stop on the first error. Do not pass
   --continue-on-row-error during the current workflow.
5. Reconcile the batch results, save the canonical CSV in this repository,
   rebuild the ledger, and checkpoint progress.

This example checks the completed last batch and should select zero rows:

```bash
python scripts/write_factgrid_cdli_artifact_items.py \
  --artifacts published/pilots/resume_2026_10_18/batch_039_artifacts.csv \
  --statements published/pilots/resume_2026_10_18/batch_039_statements.csv \
  --results published/pilots/resume_2026_10_18/batch_039_write_results.csv \
  --plan work/completed_batch_039_plan.csv \
  --only-existing-factgrid --preserve-update-labels --limit 10
```

The writer skips recorded successes. Creates and clear-rewrites have
timeout-after-success risks and are outside this update-only workflow.
Never automatically retry create_ambiguous or rewrite_ambiguous rows.

## Included files

- scripts/: original import tools plus portable ZIP staging, ledger
  reconstruction, and read-only live-review helpers.
- inputs/: tracked lookup tables and prior matches. Some tracked CSVs also match
  .gitignore rules; use `git ls-files` to inspect the actual repository contents.
- published/pilots/resume_2026_10_18/: canonical results, reviewed batch inputs,
  review manifests, cumulative results, held cases, and pending recheck inputs.
- docs/resume_2026-10-18.md: historical session log. Use the concise current guide.

The full CDLI JSON export is not in Git. Its source, checksum, and deterministic
range-selection instructions are in the current guide. Source offsets identify
ranges, not completed work.

## FactGrid model notes

- CDLI IDs retain the leading P and six digits, e.g. P001754.
- Inventory number P10 is a qualifier on present holding P329.
- Updates preserve existing labels and descriptions.
- Research-project memberships use P131; existing memberships are skipped.
- Unknown/uncertain finding spots require a reviewed QID.
- Raw finding-spot text is not sent as an item-valued P425 claim.
- Missing qualifiers on existing holding claims require a separate reviewed
  repair; the current writer does not add those qualifiers automatically.

The repository contains public staging and lookup data derived from CDLI and
FactGrid. Credentials, full corpus ZIPs, virtual environments, and scratch work
are excluded.
