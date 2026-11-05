> Historical preparation record. Batch 046 is complete after its CSRF retry.

# Batch 046 prepared — November 5, 2026

1,500 unique CDLI IDs and QIDs passed fresh identity and claim review, with
2,769 expected main claims and 16 inventory qualifiers on new holdings.
Dry run passed; effective statement values exactly match the prepared inputs.
114 unknown inventory placeholders were omitted. Two conflicting-plan IDs in
the window are held separately; neither is selected.

Window 027 reviewed all 2,497 remaining mapped candidates (2,455 QIDs) in sorted
source range 285001–310000, excluding manifests 001–026 and canonical outcomes
through 045. After planned-value checks, 1,936 were eligible. The first 1,500
form batch 046; 436 are saved in window_027_remaining_pending_recheck_artifacts.csv
and its matching statements file. Freshly recheck those before batch 047.

Expected additions: 1,243 finding spots, 3 languages, 9 periods, 18 present
holdings, 1,496 research-project memberships, plus 16 P10 qualifiers. Actual
write counts may change if live data changes.

```bash
bash "/Users/aa/Documents/Codex/2026-11-01/i-q/outputs/factgrid-resume/run_batch_046.sh" --write
```

Only-existing-factgrid, preserved labels/descriptions, five-second pauses, private
credentials and stop-on-error remain. Use frozen reviewed statements and the
header-only batch_046_upload_overrides.csv. The user runs writes; publication
excludes active batch_046_write_results.csv. Synchronize actual results before
resuming on another machine or counting completion.

After 046 and the 436 pending candidates are resolved, no unreviewed mapped
candidates remain in this range. Next new range: 310001–335000 (offset 310000),
excluding manifests 001–027 and cumulative outcomes. Historical holds and
unmatched source records remain unfinished. No batch 047 is prepared yet.
