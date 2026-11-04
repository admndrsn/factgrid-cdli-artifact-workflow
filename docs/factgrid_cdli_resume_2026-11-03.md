# Current FactGrid CDLI handoff — 2026-11-03 (through batch 039)

## Confirmed progress and pause point

The pilot and batches 002–039 contain **19,799 unique successful updates** and
**39,108 claims added**. All 39 canonical new-Mac result files have written status
with no remaining errors. The cumulative ledger includes **39,316 written IDs**,
one blocked_bad_sitelink and one rewrite_ambiguous; the held outcomes remain excluded.

- Batch 038: 291 updates, 564 claims added; zero rows on resume dry run.
- Batch 039: 500 updates, 1,046 claims added; zero rows on resume dry run.
- Both canonical CSVs match terminal output. Claim counts are additions recorded
  by the writer, not complete metadata coverage or a separate qualifier count.
- Batch 033's timeout was previously reconciled. Never merge historical
  before-retry files into the canonical ledger.

No batch 040 has been prepared. The immediate next work is **501 remaining
window-021 candidates**, saved in the checkpoint directory. They were eligible
at review time but need a fresh review before another write batch. Do not skip
this pending selection by excluding the entire window-021 manifest.

## Resume on this or another machine

Use Python 3.12+, requirements.txt, and private credentials. Read README.md and
this guide. API access was restored by administrator IP allowlisting; verify
JSON access from the current network. Keep the current login method by user
preference; its action=login deprecation warning is known.

```bash
python scripts/check_factgrid_api.py --timeout 15
python scripts/build_factgrid_resume_ledger.py
python scripts/review_factgrid_resume_window.py \
  --artifacts published/pilots/resume_2026_10_18/window_021_remaining_pending_recheck_artifacts.csv \
  --statements published/pilots/resume_2026_10_18/window_021_remaining_pending_recheck_statements.csv \
  --results published/pilots/resume_2026_10_18/cumulative_results.csv \
  --output-dir work/window_021_remaining_recheck_NEW_DATE \
  --read-batch-size 10 --limit 501
```

Require json=ok and FactGrid site information; an HTTP success or probe exit
code alone is insufficient. Choose a fresh output directory. The review helper
is read-only; inspect the resulting selection and dry run before writing.

Batches 038–039 froze the effective reviewed statement plan. Their header-only
batch-specific upload override CSV prevents a different machine's local upload
table from altering it. Three unknown inventory placeholders were omitted in
039 and two in 038. Future reviews must inspect the effective statement plan.
The pending statements are the previously effective plan; inspect any local
upload-table overrides applied by the review helper before preparing batch 040.

After the pending 501 are resolved, reconstruct current range 185001–210000
if needed and exclude all manifests 001–021 plus cumulative outcomes when
selecting *new* candidates. Do not advance ranges automatically. Retain holds
for separate review. After each write, reconcile canonical results and rebuild
the ledger. No creates or clear-rewrites are part of this update-only workflow.

## Overall workplan

See [CDLI completion workplan](cdli_completion_workplan.md). Complete items and
statements, including unmatched records and review holds, first. Prepare the
CDLI ID → QID → ATF URL mapping without publishing P251 links to missing pages.
Later create/verify each ATF page and then add its P251 link, recording both
steps. The verified reference is CDLI-ATF-L-Q894483 (CDLI P020415).

## Source ranges and next selection

Sorted source positions identify ranges, not historical completion boundaries.

| Sorted positions | Review windows | Current state |
| --- | --- | --- |
| 110001–135000 | 001–005 | Existing candidates reviewed; historical holds unresolved |
| 135001–160000 | 006–008 | Existing candidates reviewed; historical holds unresolved |
| 160001–185000 | 009–016 | No unreviewed existing candidates remained after batch 033 |
| 185001–210000 | 017–021 so far | Batches 038–039 complete; 501 window-021 candidates pending recheck |

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

Next, review remaining existing candidates in this current range,
excluding all window_001–window_021_reviewed_items.csv manifests plus cumulative
results. Do not advance automatically to the next 25,000 records.

## Identity holds and safeguards

Window 018 had 938 candidates missing a live CDLI ID claim; window 019 had 1,335.
These are held for identity review, not silently linked or enriched. The five
batch-037 items had matching live P692 identities and were written successfully. Conflict, identity and
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

This checkpoint extends GitHub commit 5f38c3843d907c8277854ab22a7d24f1314534fd.
It includes canonical results through 039, review windows 020–021, the 501
pending candidates, and updated handoff/workplan. Scratch API snapshots,
credentials, source ZIPs and machine-specific launchers are not committed.
Always fetch the current branch before subsequent publication; do not force-push.
