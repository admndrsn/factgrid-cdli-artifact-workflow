# Batch 073 combined CDLI, BDTNS and eBL pilot

Batch 073 is prepared for the user to run. It contains 120 existing-item
updates and 383 expected unique additions, including 120 P959 BDTNS IDs,
120 P1173 eBL IDs, 71 P695 finding spots and 72 P131 research projects.
Use the standard five-second pause and stop on error.

All 120 identities were confirmed in the MediaWiki API against P692. Each
item has one unique CDLI ID and one unique QID. None overlaps the cumulative
ledger or the prior window review manifests. The review found no conflicting
live values or missing inventory qualifiers on existing holdings. The
launcher reproduced the frozen plan, and an offline writer build against the
reviewed entity snapshots reproduced the expected claim counts.

## Identifier sources

The source crosswalk records the BDTNS JSONL row and record URL for each
pair. The join uses the explicit `cross_ids.cdli` and `cross_ids.ebl`
values. Both identifier properties take strings. Leading zeroes in BDTNS
IDs and the exact eBL spelling are preserved. This pilot uses single simple
fragment identifiers and excludes shared, compound or ambiguous source
references. It does not derive an eBL ID from a museum number.

FactGrid P959 is an external ID at revision 11622106. P1173 is the eBL ID
external-ID property at revision 9750944 and lists the Fragmentarium
formatter `https://www.ebl.lmu.de/fragmentarium/$1`. The direct-claim
index returned no P959 or P1173 assignments during preparation. The item
API confirmed both fields were empty on these 120 items. The writer reloads
each item, checks its P692 identity, skips exact identifier matches and stops
if it encounters a conflicting identifier value.

## Running and reconciling

Use the prepared update-only launcher with the explicit CDLI-to-QID
crosswalk, the frozen statements, label/description preservation and the
normal private login. Run without `--write` for a dry run. Only the user
runs the write. Reconcile the canonical result CSV against the terminal log
before moving to another batch.

For further CDLI batches, add each safely matched identifier to the same
reviewed update when available. Continue CDLI coverage work where an
external match is missing. Keep ambiguous external matches for review.
Backfill on previously completed items and corpus-wide eBL coverage are
outside this pilot.
