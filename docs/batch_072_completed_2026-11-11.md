# Batch 072 completed and CDLI identity audit

The canonical result CSV contains 4,267 unique planned CDLI ID/QID pairs, all
successful updates, with 7,985 claims added and 40,613 skipped. All terminal
success lines agree row for row. The log contains transient transport failures
and finishes at 4,267/4,267 in 10h00m11s on its progress meter. The rebuilt
ledger contains 91,761 written IDs and two historical held outcomes. Running
the launcher without `--write` selected zero items. The writer does not count
inventory qualifiers separately.

## CDLI coverage

The ten staged source ranges contain 421,387 valid unique CDLI IDs. A fresh
FactGrid SPARQL export of direct P692 values returned 158,902 rows, matching a
separate COUNT query. Eight non-CDLI values were excluded. The remaining rows
indexed 158,216 normalized CDLI IDs, including IDs outside the staged source.

| Source identity status | IDs |
|---|---:|
| One indexed QID with one CDLI ID | 156,558 |
| No indexed P692 match | 264,119 |
| More than one indexed QID | 678 |
| One indexed QID carrying multiple CDLI IDs | 32 |

An absent direct P692 match leaves item existence unresolved. The counts use
the SPARQL truthy index and do not account for indexing delays, deprecated
claims or items without P692. Use the MediaWiki API to confirm identities
before any write preparation. Windows 044–047 left 186 held candidates.
Their reviewed fields include type-of-work conflicts and identity gaps, with
holding/inventory and other claim repairs still requiring review. These window
reviews cover only the selected records. Corpus-wide field coverage remains
open. Batch 041 remains the source of the Q2036070/P386408 language hold.

## BDTNS read-only profile

All 105,187 JSONL records parsed and had unique string BDTNS IDs. Matching used
the explicit `cross_ids.cdli` field, preserving BDTNS leading zeroes. The CSV
was unnecessary for this join and neither source was modified.

| Match status | Records |
|---|---:|
| One-to-one against the P692 index | 66,253 |
| Explicit CDLI ID absent from the index | 34,964 |
| No explicit CDLI ID | 3,806 |
| Shared CDLI ID across BDTNS records | 82 |
| CDLI ID maps to multiple indexed QIDs | 80 |
| Indexed QID carries multiple CDLI IDs | 2 |

MediaWiki API revision 11622106 confirms P959 is the external-ID property
“BDTNS ID”. Its P236 formatter is
`http://bdtns.cesga.es/catalogo_directo_new.php?numBDTS=$1`. The property
entity returned no explicit constraint statements. A direct P959 SPARQL
query returned zero indexed statements. Recheck P692 and P959 in the item API
before staging any pilot, including existing values, provenance and collisions.
CDLI completion remains open and the BDTNS write phase remains conditional.
