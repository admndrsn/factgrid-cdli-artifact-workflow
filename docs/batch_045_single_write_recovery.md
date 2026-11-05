> Historical recovery record. Batch 045 is now complete; the recovered row remains in its canonical CSV.

# Batch 045 single-write recovery

The user reported one successful update: Q2046186 / P427590 / CUSAS 13, 174.
The local results CSV contained only one newline. Revision 21773161 (parent
20002965) confirms the batch write and exactly one added claim: P131=Q1894741.
All expected reviewed claims are present. Restored one written result row with
claims_written=1. claims_skipped is blank because the terminal count was not
provided. The empty file is preserved separately. No FactGrid write was made
while recovering this local record. Do not infer the reason the CSV was empty.

Resume batch 045 using the same launcher. The recovered first item is skipped;
1,510 planned items remain. Never combine recovery evidence with canonical
results as additional successes.
