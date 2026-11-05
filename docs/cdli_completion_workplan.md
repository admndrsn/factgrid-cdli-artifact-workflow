# CDLI completion sequence

User direction: complete CDLI text items and their statements in FactGrid first;
subsequently add ASCII Transliteration Format (ATF) texts as FactGrid Document
pages, linked from their items using P251.

## Phase 1: items and statements

- Continue fresh live reviews and resumable update batches, excluding all prior
  review manifests and canonical successful/held write outcomes.
- Exhaust each source range by identity, not by its offset label alone.
- Separately reconcile missing/mismatched CDLI identities, statement conflicts,
  and holding/inventory qualifier repairs. Reviewed holds are unfinished work.
- Identify unmatched source records, deduplicate against current live FactGrid
  identities, and prepare a separately reviewed new-item workflow. Existing-item
  update batches alone do not achieve full corpus coverage.
- Reconcile ambiguous historical outcomes before retrying. Preserve labels and
  descriptions; retain provenance and canonical results.
- Audit corpus coverage by CDLI ID and field before declaring phase 1 complete.

## Phase 2: ATF Document pages

- Inventory the ATF source files and map texts to verified CDLI IDs and FactGrid
  item IDs. Establish provenance, versioning, encoding and reuse permissions.
- Review the site's document-page naming and wikitext conventions with a small
  pilot; preserve ATF text faithfully, including special characters and lines.
- Check for existing pages and P251 links before creating anything; design
  resumable page creation and link reconciliation for partial successes.
- P251 was checked through the FactGrid API on 2026-11-03: English label
  "FactGrid document page", datatype URL; its description references a transcript
  URL such as https://database.factgrid.de/wiki/D-Q6641. It is a link to the page,
  not a property for storing the ATF file contents.
- Prepare the pilot after phase 1; no Document pages or P251 writes are part of
  the current batch preparation.

## User-provided ATF reference

Reference: https://database.factgrid.de/wiki/CDLI-ATF-L-Q894483
Read via MediaWiki API: revision 20109826, timestamp 2026-06-15T16:48:55Z.
The page is ordinary wikitext in namespace 0, not a separate Document namespace.

Structure to follow:

1. `{{Template:CuneiformInfoBox|894483}}` (numeric QID without Q).
2. A FactGrid ID link to `[[Item:Q894483]]`.
3. `<poem>` containing the ATF header, version/language directives, tablet-side
   and column directives, and numbered transliteration lines.
4. Four `<br/>` elements, followed by
   `{{Template:CuneiformImageFC|894483}}`.

The first ATF record identifies P020415 (TMH 5, 001). Live item Q894483 has
P692=P020415 and P251 pointing to this exact page URL. This provides a verified
example of the CDLI ID → FactGrid item → ATF page relationship. Preserve the
ATF content and test MediaWiki rendering with a pilot rather than treating ATF
as arbitrary wikitext. Page naming follows CDLI-ATF-L-Q{numeric_id} in this example.

## Agreed ATF publication sequence

Prepare a CDLI ID → FactGrid QID → planned ATF URL mapping first. Do not add
P251 links to nonexistent pages. During the ATF phase, create or verify each
page and its transliteration, then add the missing P251 link and record both
steps for resumability. User accepted this sequence on November 3, 2026.

## Latest completed checkpoint and standing workflow

Completed through 046: 28,360 updates, 54,816 claims, 47,877 cumulative written
IDs. Batch 046's CSRF interruption was retried successfully. Batch 047 is prepared/
running with the final 436 pending candidates. After reconciliation, next new
range is 310001–335000. Holds and unmatched records remain unfinished work.

On pasted terminal output, reconcile results, prepare the next freshly reviewed
batch, provide the tested launcher immediately, then publish an immutable
checkpoint while the user writes. Aim for 1,500 items, adjusting to finish small
remainders/ranges. Never publish active results as completed.
