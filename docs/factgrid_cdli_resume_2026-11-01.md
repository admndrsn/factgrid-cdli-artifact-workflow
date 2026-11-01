# Current FactGrid CDLI handoff — 2026-11-01

## Confirmed checkpoint

The canonical new-Mac pilot and batches 002–028 contain **15,008 unique successful
update rows** and **29,665 claims added**. These exclude the older runs.
Batch 016's 122 CSRF failures were retried; its current result file has 500
successes. batch_016_results_before_retry.csv is historical and must never be
merged into the current ledger.

Checkpoint files are under published/pilots/resume_2026_10_18/. The cumulative
ledger also incorporates the two older top-level result files: **34,525 written
IDs**, one blocked_bad_sitelink and one rewrite_ambiguous. Those held statuses
remain excluded by the writer. Claims-added counts are recorded additions,
not every pre-existing claim or a measure of complete metadata coverage.

## Current blocker and next action

Fresh API checks on 2026-11-01 followed redirects from /w/api.php to
/rep-pow-challenge and returned HTTP 200 text/html labelled mod_repudiator.
An anonymous siteinfo probe confirmed the same behavior. No fresh claim review
was accepted. Obtain supported API access or an administrator-approved
exception; do not bypass the challenge or infer API health from HTTP 200.

There are **699 remaining candidates** from review window 014. Their old review
is stale and they are not approved as batch 029. The pending inputs are:

- window_014_remaining_pending_recheck_artifacts.csv
- window_014_remaining_pending_recheck_statements.csv

These files are for fresh review, not a write command.

## Portable recovery on another machine

Clone the repository, install requirements, and run:

```bash
python scripts/check_factgrid_api.py --timeout 15
python scripts/build_factgrid_resume_ledger.py
```

The probe must report json=ok with the expected FactGrid sitename. The probe's
exit code alone is not sufficient: it currently exits normally on HTML, too.
Once API JSON access is restored:

```bash
python scripts/review_factgrid_resume_window.py \
  --artifacts published/pilots/resume_2026_10_18/window_014_remaining_pending_recheck_artifacts.csv \
  --statements published/pilots/resume_2026_10_18/window_014_remaining_pending_recheck_statements.csv \
  --results published/pilots/resume_2026_10_18/cumulative_results.csv \
  --output-dir work/window_014_remaining_recheck \
  --read-batch-size 10 --limit 699
```

This helper reads only. It fails on non-JSON or incomplete entity responses.
candidate_items_reviewed.csv includes only matching live CDLI identities with
no detected single-value conflicts, supported missing additions, and no
missing-qualifier repair cases. Treat every review as a dated snapshot.
Inspect it and prepare subset artifact/statement files before issuing a write.

Old source_json path strings are provenance. The writer does not dereference
them; the commands above do not depend on another machine's filesystem.

For subsequent writes, use --only-existing-factgrid, --preserve-update-labels,
--sleep 5 and a dedicated batch results file. Leave out --continue-on-row-error
to stop on new authentication errors. Rerunning the same batch/result file skips
successes. Copy updated canonical results into this checkpoint directory and
rebuild the cumulative ledger before selecting another batch.

## Source export and range history

Original source: [artifacts_json.zip on Google Drive](https://drive.google.com/file/d/1ASmm28jrlZpp2C3Cfje0SWHbmSptvaEZ/view).

- Size: 780,323,470 bytes.
- SHA256: 7c12ab12a76de4bf7efd4c2c7d5642320dd8d00f220a3662dc00cdef30387e3c.
- 421,387 JSON files; the full ZIP CRC check passed during migration.
- Thirty sampled records matched the previous staging data in every field
  except the local source path.

Ranges are sorted by JSON basename:

| Sorted positions | Review windows | State |
| --- | --- | --- |
| 110001–135000 | 001–005 | Existing-item candidates reviewed; historical holds unresolved |
| 135001–160000 | 006–008 | Existing-item candidates reviewed; historical holds unresolved |
| 160001–185000 | 009–014 so far | 699 window 014 candidates await recheck; later candidates may remain |

Do not automatically move to the next source range after the pending 699:
first review all remaining existing-item candidates in the current range,
excluding every reviewed-items manifest for windows 009–014 and cumulative
successes. No claim is made that every source record has been written.
Unmatched items, conflicts, uncertain identities, and qualifier repairs remain
separate from successful updates.

The September instruction to sort and resume at offset 110000 does not
reproduce earlier tranche membership. Only 1,528 of the 25,000 saved
85001–110000 files belong to that sorted range. Eligibility depends on CDLI
identity, current results, and live claims.

Stage a range directly from the ZIP without extracting the corpus:

```bash
python scripts/stage_cdli_artifacts_from_zip.py \
  --zip /path/to/artifacts_json.zip --offset 160000 --limit 25000 \
  --output work/artifacts_160001_185000.csv \
  --summary work/artifacts_160001_185000_summary.csv
```

Prepare statements with scripts/prepare_cdli_artifact_statement_staging.py
using the tracked lookup tables, following the September guide's statement
staging command with the new artifact/output paths. A source offset is not
a completion marker. Compare IDs with the ledger and review manifests.

## Retained safeguards and limits

- Preserve labels/descriptions. Existing main claims and project memberships
  have loaded-item fallback checks; never overwrite newer conflicts.
- P10 belongs under P329. Missing qualifiers on an existing main claim require
  separate reviewed repair; the writer currently skips the existing main claim.
- Unmapped fields are omitted. A written result does not mean complete coverage
  of all source metadata.
- all_review_holds.csv preserves historical flags by review window. It is not
  a freshly validated repair list.
- Creates and clear-rewrites remain outside this workflow. Ambiguous outcomes
  require live reconciliation, never automatic retry.
- Keep credentials in private prompts or the current shell. The user prefers
  retaining the current login unless repeated failures warrant changing it.
  Its main-account action=login deprecation warning is known.
- requirements-resume-2026-11-01.txt records the installed package environment.

The long session log is docs/resume_2026-10-18.md. Its statements that progress
was local refer to the time of each entry; verify publication against GitHub's
current branch when handing off.
