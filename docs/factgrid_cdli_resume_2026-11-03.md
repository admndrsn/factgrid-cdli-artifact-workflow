# Current FactGrid CDLI handoff — 2026-11-03

## Confirmed progress and pause point

The pilot and batches 002–036 contain **19,003 unique successful updates** and
**37,492 claims added** on the new Mac. All 36 canonical result CSVs have written
status, with no remaining errors. The cumulative ledger, including the older
runs, contains **38,520 written IDs**, one blocked_bad_sitelink and one
rewrite_ambiguous. These two held outcomes remain excluded.

Batch 033 stopped after 79 successes when loading Q2063416 timed out, before
writing that item. The retry completed the remaining 116. Its canonical result
has 195 successes and 338 added claims. Historical before-retry snapshots must
not be combined with canonical results.

**Batch 037 is prepared but has NOT been written.** Its five items passed live
identity and claim review on 2026-11-03, and its dry run selected five updates.
Refresh that review after a pause; do not treat an old review as current approval.

The administrator allowlisted the user's outbound IP. Read-only API checks and
reviews subsequently returned JSON. No challenge bypass was used. Access can
depend on the current network; require API JSON on each resume. Keep the current
login method by user preference. Its action=login deprecation warning is known.

## Resume on this or another machine

Read README.md and this guide first. Install Python 3.12+ and requirements.txt;
requirements-resume-2026-11-01.txt records the working environment. Never commit
credentials. The writer prompts privately or uses the current shell environment.

Run these read-only preparation commands from the repository:

```bash
python scripts/check_factgrid_api.py --timeout 15
python scripts/build_factgrid_resume_ledger.py
python scripts/review_factgrid_resume_window.py \
  --artifacts published/pilots/resume_2026_10_18/batch_037_artifacts.csv \
  --statements published/pilots/resume_2026_10_18/batch_037_statements.csv \
  --results published/pilots/resume_2026_10_18/cumulative_results.csv \
  --output-dir work/batch_037_fresh_review --limit 5 --read-batch-size 10
```

Use a new dated output directory for each review. Require json=ok and expected
FactGrid site information; the API probe may exit normally even when returning
HTML. All five pending identities must remain verified and eligible before
using the original batch. If eligibility changes, prepare reviewed subsets.

Inspect the dry run before adding --write:

```bash
python scripts/write_factgrid_cdli_artifact_items.py \
  --artifacts published/pilots/resume_2026_10_18/batch_037_artifacts.csv \
  --statements published/pilots/resume_2026_10_18/batch_037_statements.csv \
  --results published/pilots/resume_2026_10_18/batch_037_write_results.csv \
  --plan work/batch_037_write_plan.csv \
  --only-existing-factgrid --preserve-update-labels --sleep 5 --limit 5
```

The local Terminal wrapper is outputs/factgrid-resume/run_batch_037.sh, outside
the checkout. It accepts --write and has not been run with that flag.

There is deliberately no empty batch_037_write_results.csv: the ledger builder
reads result files for completed/attempted batches only. Once written, reconcile
results, save the canonical CSV here, and rebuild the ledger.

## Source ranges and next selection

Sorted source positions identify ranges, not historical completion boundaries.

| Sorted positions | Review windows | Current state |
| --- | --- | --- |
| 110001–135000 | 001–005 | Existing candidates reviewed; historical holds unresolved |
| 135001–160000 | 006–008 | Existing candidates reviewed; historical holds unresolved |
| 160001–185000 | 009–016 | No unreviewed existing candidates remained after batch 033 |
| 185001–210000 | 017–019 so far | Batch 037 pending; further unreviewed candidates may remain |

Current staging files are in the workspace's work/ directory, outside Git:
cdli_artifact_staging_candidate_sorted_185001_210000.csv and
cdli_artifact_statement_staging_candidate_sorted_185001_210000.csv.
The 25,000 source IDs were unique. To reconstruct the range from the original ZIP:

```bash
python scripts/stage_cdli_artifacts_from_zip.py \
  --zip /path/to/artifacts_json.zip --offset 185000 --limit 25000 \
  --output work/artifacts_185001_210000.csv \
  --summary work/artifacts_185001_210000_summary.csv
```

Use the statement-staging lookup command in the September guide with these new
paths, tracked lookup tables, --reservations '' and the reviewed provenience
aliases. The original ZIP details, hash and provenance are recorded in
docs/factgrid_cdli_resume_2026-11-01.md. No source ZIP is included in Git.

After batch 037, review remaining existing candidates in this current range,
excluding all window_001–window_019_reviewed_items.csv manifests plus cumulative
results. Do not advance automatically to the next 25,000 records.

## Identity holds and safeguards

Window 018 had 938 candidates missing a live CDLI ID claim; window 019 had 1,335.
These are held for identity review, not silently linked or enriched. The five
batch-037 items have matching live P692 identities. Conflict, identity and
qualifier-hold counts can overlap. An update count is not complete metadata
coverage and does not include unmatched source records.

all_review_holds.csv is historical evidence, not a freshly validated repair
list. Per-window holds, summaries and reviewed-item manifests are also retained.
All held items require separate investigation before changes.

Preserve labels/descriptions. P10 belongs as a qualifier under P329. Missing
qualifiers on an existing main statement require a separate repair; the writer
currently skips that main statement. Unknown fields remain omitted. No creates,
clear-rewrites, or automatic ambiguous-outcome retries are authorized here.
Use --only-existing-factgrid and --preserve-update-labels, keep the five-second
delay, omit --continue-on-row-error, and stop on errors. Update-only retries skip
recorded successes; inspect timeout stage before retrying.

## Publication and local history

The previous GitHub checkpoint was cb26f1c9829fd870f9993465e3b262a8eaf41fde
(through batch 028). This handoff accompanies the subsequent progress upload.
GitHub publication uses the authorized connector. The old local main contains
the original 29 commits and its remote-tracking ref may be stale; do not
force-push it. Fetch and merge the published main before future Terminal pushes.
The original full-history bundle remains in workspace outputs/.
