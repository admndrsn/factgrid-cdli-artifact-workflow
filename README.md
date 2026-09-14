# FactGrid CDLI Artifact Workflow

Utilities and staging data for preparing and writing CDLI cuneiform artifact
records to FactGrid.

This repository was split out from the TokenWorks Wikibase workflow so the CDLI
artifact import, duplicate-QID reuse, and FactGrid write safety logic can be
shared without exposing the larger private working tree.

## What Is Included

- `scripts/`: Python scripts for staging CDLI artifacts, preparing statements,
  checking existing FactGrid items, auditing duplicate CDLI IDs, and writing
  artifacts to FactGrid.
- `inputs/`: compact lookup tables for CDLI object types, periods, genres,
  languages, materials, proveniences, museum/collection mappings, and prior
  FactGrid/CDLI ID matches.
- `published/pilots/`: the active staged tranche and reviewed reuse-pool files
  needed to resume the current FactGrid write workflow.

The large local CDLI JSON export is not included. The scripts expect it to be
available locally when preparing new staging files.

## Excluded

The following are intentionally not tracked:

- passwords, tokens, and environment files;
- Python caches and local virtual environments;
- generated import packages and zip files;
- the oversized `factgrid_df_header_sample.csv` snapshot;
- older run outputs not needed to resume the current workflow.

## Setup

Use Python 3.12 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

For API writes, provide FactGrid credentials in the shell:

```bash
export FG_USER='Your FactGrid username'
read -s FG_PASS
export FG_PASS
```

Do not commit credentials.

## Current Safe Write Pattern

The FactGrid writer protects against timeout-after-success failures:

- `create` writes are single-attempt, because retrying can mint duplicate QIDs;
- `rewrite` writes are single-attempt, because retrying can repeatedly clear the
  same item;
- ordinary `update` writes may still retry.

The active tranche can be resumed with a small batch:

```bash
python scripts/write_factgrid_cdli_artifact_items.py \
  --artifacts published/pilots/cdli_artifact_staging_tranche_35001_60000.csv \
  --statements published/pilots/cdli_artifact_statement_staging_tranche_35001_60000.csv \
  --results published/pilots/factgrid_cdli_artifact_write_results_tranche_35001_60000.csv \
  --plan published/pilots/factgrid_cdli_artifact_write_plan_tranche_35001_60000.csv \
  --reuse-pool published/pilots/factgrid_cdli_artifact_duplicate_p692_reuse_pool_review_approved.csv \
  --only-missing-factgrid \
  --limit 10 \
  --preview 10 \
  --sleep 10 \
  --write \
  --clear-existing-reuse \
  --continue-on-row-error
```

If a create or rewrite times out, inspect FactGrid before rerunning. The script
records ambiguous writes as statuses such as `create_ambiguous` or
`rewrite_ambiguous` so they are not retried automatically.

## Important FactGrid Model Notes

- CDLI IDs are written with the leading `P` and six digits, for example
  `P001754`.
- `P329` present holding receives `P10` inventory number as a qualifier, not as
  a separate main statement.
- New or rewritten items receive `P131` research-project statements for
  TokenWorks and the CDLI-related research projects configured in the writer.
- Generic or uncertain finding spots should be skipped unless a reviewed
  FactGrid QID is available.

## Public Data Note

This repository contains staging and lookup CSVs derived from CDLI, FactGrid,
and local review work. It does not contain private credentials or the full local
CDLI JSON corpus.
