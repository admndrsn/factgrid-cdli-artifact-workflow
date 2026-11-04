# Batch 042 prepared — November 4, 2026

1,012 unique existing items passed fresh live review, with 1,798 expected main
statement additions and 8 P10 inventory qualifiers on new holding statements.
The tested dry run selects 1,012 updates; its effective plan matches the prepared
inputs exactly. No conflicting planned values for writer single-value properties
were found. No unknown inventory placeholders needed omission.

Window 024 reviewed all 1,877 remaining mapped candidates in source range
210001–235000 (1,876 distinct QIDs), excluding manifests 001–023 and canonical
outcomes through batch 041. It found 1,012 eligible, 565 already complete, 115
with live conflicts, and 255 missing live CDLI identity claims. Review categories
can overlap. Held and unmatched records are not completed by this batch.

Expected additions: 780 finding spots, 4 languages, 1 material, 1 period,
8 present holdings, 998 research-project memberships, and 6 genres. Actual
write counts may change if live data changes.

```bash
bash "/Users/aa/Documents/Codex/2026-11-01/i-q/outputs/factgrid-resume/run_batch_042.sh" --write
```

This is the machine-specific launcher; portable inputs are under
published/pilots/resume_2026_10_18/. The writer uses those batch_042_artifacts.csv
and batch_042_statements.csv files, batch_042_write_results.csv as the dedicated
result path, and the header-only batch_042_upload_overrides.csv with
--only-existing-factgrid --preserve-update-labels --limit 1012 --sleep 5.
Omit --write for a dry run; stop on errors. Retain the existing private login
method. Never include credentials in commits.

The batch was handed to the user for terminal execution. Publication includes
only its preparation; any in-progress batch_042_write_results.csv is excluded.
Reconcile its actual results before counting this batch as complete.

After successful completion there are no unreviewed mapped existing candidates
left in 210001–235000. Stage the next sorted range 235001–260000 with offset
235000 and limit 25000, exclude manifests 001–024 and cumulative outcomes,
and freshly review. Separately investigate historical holds and unmatched items.
