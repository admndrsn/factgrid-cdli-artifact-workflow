# Codex Handoff Prompt: FactGrid CDLI Artifact Workflow

Use this prompt to start a new Codex task on another machine.

```text
I am continuing the FactGrid CDLI cuneiform artifact/tablet workflow from this repository:

https://github.com/admndrsn/factgrid-cdli-artifact-workflow

Please work carefully and collaboratively in the same style as the prior Codex task. The goal is to keep adding CDLI cuneiform artifact/tablet statements to existing FactGrid items, in resumable batches, while avoiding duplicates and avoiding unsafe rewrites.

Start by reading these files in the repo:

1. docs/factgrid_cdli_resume_2026-09-28.md
2. README.md
3. scripts/write_factgrid_cdli_artifact_items.py
4. scripts/prepare_cdli_artifact_staging.py
5. scripts/prepare_cdli_artifact_statement_staging.py

Current state at handoff:

- Tranche 85001_110000 is complete for existing-FactGrid updates.
- Result file: published/pilots/factgrid_cdli_artifact_write_results_tranche_85001_110000.csv
- Status at handoff: 6420 written rows, 0 current errors, 0 remaining existing-FactGrid rows in that tranche.
- Next tranche to prepare: 110001_135000, using CDLI JSON offset 110000 and limit 25000.
- The full CDLI artifact JSON export is not in Git. It must exist locally, ideally at:
  /Users/aa/Documents/FactGrid/FactgridCuneiform/Datasets/CDLI/2026_GET/artifacts_json
  If it is elsewhere, adjust --json-dir in the staging command.

Important workflow principles:

- Do not write to FactGrid until a dry run has been inspected.
- Use update-only batches first: pass --only-existing-factgrid.
- Preserve existing labels on updates: pass --preserve-update-labels.
- Inventory number P10 belongs as a qualifier on Present holding P329, not as a separate main statement.
- CDLI IDs should keep the leading P and six digits, e.g. P214517.
- For update-only batches, if a batch is interrupted, it is usually OK to rerun the same command because written rows in the results CSV are skipped.
- Avoid create/rewrite workflows unless explicitly discussed; those have timeout-after-success risks.
- When FactGrid SPARQL/live-claim export works, prefer live-claim review before writing. If FactGrid read endpoints are slow, the writer has loaded-item fallback safeguards for update-only batches.
- After each successful batch, reconcile the result CSV, prepare the next dry run, and commit/push progress so another machine can resume.

Setup commands:

```bash
git clone https://github.com/admndrsn/factgrid-cdli-artifact-workflow.git
cd factgrid-cdli-artifact-workflow

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

FactGrid credentials should be provided only in the shell and never committed:

```bash
export FG_USER='Adam Anderson'
read -s FG_PASS
export FG_PASS
```

Prepare the next tranche:

```bash
python scripts/prepare_cdli_artifact_staging.py \
  --sort \
  --offset 110000 \
  --limit 25000 \
  --workers 8 \
  --output published/pilots/cdli_artifact_staging_tranche_110001_135000.csv \
  --summary published/pilots/cdli_artifact_staging_tranche_110001_135000_summary.csv
```

Then prepare statement staging:

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

Dry run the next existing-FactGrid update window:

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

If the dry run looks clean, provide this write command for me to run:

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

After I paste a batch output back to you:

1. Inspect the output for errors, ambiguous writes, conflicts, duplicate creates, or server errors.
2. Reconcile the result CSV with a concise count of write_status values.
3. Dry-run the next window.
4. Give me the next write command if clean.
5. When a tranche or substantial batch is complete, prepare a git commit and push it.

Tone and collaboration preference:

- Be concise but proactive.
- Explain what you are checking and why.
- Prefer concrete commands I can run.
- Keep the workflow safe and resumable.
- Do not assume FactGrid is healthy; if endpoints slow down, reduce batch size or use fallback safeguards.
```
