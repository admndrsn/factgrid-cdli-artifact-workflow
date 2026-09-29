# FactGrid CDLI Artifact Resume Notes

Last updated: 2026-09-28.

This repo can be used to continue the CDLI cuneiform artifact/tablet statement
write to FactGrid from another machine.

## Current Status

- Remote repo: `https://github.com/admndrsn/factgrid-cdli-artifact-workflow`
- Active completed tranche: `85001_110000`
- Current result file:
  `published/pilots/factgrid_cdli_artifact_write_results_tranche_85001_110000.csv`
- Current `85001_110000` result status: `6420` written rows, `0` current errors.
- A dry-run resume check against `85001_110000` selected `0` remaining existing-FactGrid rows.
- Next work should start by preparing tranche `110001_135000`.

The local safety fallback in `scripts/write_factgrid_cdli_artifact_items.py`
now skips already-present research project (`P131`) values and skips conflicting
single-value claims already loaded on the item. This matters when FactGrid
SPARQL/live-claim export is too slow and we write using the loaded-item
fallback path.

## Required Local Data

The full CDLI artifact JSON export is not tracked in Git. The staging script
expects this local directory by default:

```bash
/Users/aa/Documents/FactGrid/FactgridCuneiform/Datasets/CDLI/2026_GET/artifacts_json
```

If the travel machine uses a different path, pass it with `--json-dir`.

## Setup On Another Machine

```bash
git clone https://github.com/admndrsn/factgrid-cdli-artifact-workflow.git
cd factgrid-cdli-artifact-workflow

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Set FactGrid credentials only in the terminal session. Do not commit them.

```bash
export FG_USER='Adam Anderson'
read -s FG_PASS
export FG_PASS
```

## Prepare Next Tranche

The next tranche should be `110001_135000`, using offset `110000` and limit
`25000`.

```bash
python scripts/prepare_cdli_artifact_staging.py \
  --sort \
  --offset 110000 \
  --limit 25000 \
  --workers 8 \
  --output published/pilots/cdli_artifact_staging_tranche_110001_135000.csv \
  --summary published/pilots/cdli_artifact_staging_tranche_110001_135000_summary.csv
```

Then prepare FactGrid statement staging:

```bash
python scripts/prepare_cdli_artifact_statement_staging.py \
  --artifacts published/pilots/cdli_artifact_staging_tranche_110001_135000.csv \
  --factgrid-cdli inputs/factgrid_tablet_sources/FG_CDLI_ID.csv \
  --object-lookup inputs/cdli_lookup_sources/CDLI_Object.csv \
  --period-lookup inputs/cdli_lookup_sources/CDLI_Period.csv \
  --genre-lookup inputs/cdli_lookup_sources/CDLI_Genre.csv \
  --language-lookup inputs/cdli_lookup_sources/CDLI_Lang.csv \
  --material-lookup inputs/cdli_lookup_sources/CDLI_Material.csv \
  --provenience-lookup inputs/cdli_lookup_sources/proveniences_FG_Proveniences.csv \
  --provenience-fg-lookup inputs/cdli_lookup_sources/proveniences_FG_all_with_p694_live.csv \
  --provenience-aliases inputs/provenience_aliases_reviewed.csv \
  --collection-lookup inputs/cdli_lookup_sources/museum_FG.csv \
  --output published/pilots/cdli_artifact_statement_staging_tranche_110001_135000.csv \
  --summary published/pilots/cdli_artifact_statement_staging_tranche_110001_135000_summary.csv
```

## Dry Run Existing FactGrid Updates

Start with a dry run before writing:

```bash
python scripts/write_factgrid_cdli_artifact_items.py \
  --artifacts published/pilots/cdli_artifact_staging_tranche_110001_135000.csv \
  --statements published/pilots/cdli_artifact_statement_staging_tranche_110001_135000.csv \
  --results published/pilots/factgrid_cdli_artifact_write_results_tranche_110001_135000.csv \
  --plan published/pilots/factgrid_cdli_artifact_write_plan_tranche_110001_135000.csv \
  --only-existing-factgrid \
  --limit 1500 \
  --preserve-update-labels
```

If the dry run looks clean, write with a gentle sleep:

```bash
python scripts/write_factgrid_cdli_artifact_items.py \
  --artifacts published/pilots/cdli_artifact_staging_tranche_110001_135000.csv \
  --statements published/pilots/cdli_artifact_statement_staging_tranche_110001_135000.csv \
  --results published/pilots/factgrid_cdli_artifact_write_results_tranche_110001_135000.csv \
  --plan published/pilots/factgrid_cdli_artifact_write_plan_tranche_110001_135000.csv \
  --only-existing-factgrid \
  --limit 1500 \
  --sleep 5 \
  --preserve-update-labels \
  --write \
  --continue-on-row-error
```

Repeat the same write command until the dry run selects `0` rows. Commit and
push the updated result CSV after each travel-session batch so another machine
can resume from Git.

## Optional Live-Claim Review

When FactGrid SPARQL is responsive, use the live-claim review path before a
write window. When FactGrid SPARQL or anonymous API reads are timing out, the
loaded-item fallback in the writer is the practical route for update-only
batches.

## Notes

- Inventory numbers are written as `P10` qualifiers on `P329` present holding,
  not as standalone main statements.
- CDLI IDs should keep the leading `P` and six digits, for example `P214517`.
- For update-only batches, keep `--preserve-update-labels`.
- If a batch is interrupted, rerun the same command. Rows already recorded as
  `written` in the result CSV are skipped.
