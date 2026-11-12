#!/usr/bin/env python3
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import sys
import time
from pathlib import Path
import pandas as pd
import requests

repo = Path(__file__).resolve().parents[1]
workdir = repo / 'work'
parser = argparse.ArgumentParser(description='Read-only live claim review for existing FactGrid items. Does not write to FactGrid.')
parser.add_argument('--output-dir', type=Path, required=True)
parser.add_argument('--exclude-items', type=Path, action='append', default=[])
parser.add_argument('--read-batch-size', type=int, default=50)
parser.add_argument('--read-workers', type=int, choices=range(1, 9), default=1)
parser.add_argument('--artifacts', type=Path, required=True)
parser.add_argument('--statements', type=Path, required=True)
parser.add_argument('--verified-existing-mapping', type=Path)
parser.add_argument('--results', type=Path, required=True)
parser.add_argument('--limit', type=int, default=1500)
options = parser.parse_args()
if not 1 <= options.read_batch_size <= 50 or options.limit < 1:
    parser.error('Use a read batch size of 1–50 and a positive limit.')
if not options.results.is_file():
    parser.error('Build the cumulative results ledger before reviewing.')
outputdir = options.output_dir
if (outputdir / 'candidate_live_review_1500.csv').exists():
    parser.error('Use a fresh output directory; do not overwrite a dated live review.')
outputdir.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(repo / 'scripts'))
import write_factgrid_cdli_artifact_items as writer

args = argparse.Namespace(
    artifacts=options.artifacts,
    statements=options.statements,
    results=options.results,
    verified_existing_mapping=options.verified_existing_mapping,
    factgrid_cdli=writer.DEFAULT_FACTGRID_CDLI,
    prior_factgrid_qid_lookup=list(writer.DEFAULT_PRIOR_FACTGRID_QID_LOOKUPS),
    factgrid_upload_table=writer.DEFAULT_FACTGRID_UPLOAD_TABLE,
    collection_matches=writer.DEFAULT_COLLECTION_MATCHES,
    only_cdli_ids='', only_missing_factgrid=False, only_existing_factgrid=True,
    only_field_names='', reuse_pool=None, limit=options.limit, preview=10,
)
if options.exclude_items:
    excluded = set()
    for path in options.exclude_items:
        excluded.update(pd.read_csv(path, dtype=str).fillna('').cdli_id)
    source = pd.read_csv(args.artifacts, dtype=str).fillna('')
    args.only_cdli_ids = ','.join(source.loc[~source.cdli_id.isin(excluded), 'cdli_id'])
    if not args.only_cdli_ids:
        raise RuntimeError('No unreviewed source IDs remain')
items, plan = writer.build_workset(args)
items.to_csv(outputdir/'candidate_items_1500.csv',index=False)
plan.to_csv(outputdir/'factgrid_candidate_update_plan_1500.csv',index=False)
if items.empty:
    print('No remaining existing-item candidates selected.')
    raise SystemExit(0)
qids = list(dict.fromkeys(items.factgrid_qid))
entities={}
batches = [qids[i:i + options.read_batch_size] for i in range(0, len(qids), options.read_batch_size)]

def read_entities(batch):
    for attempt in range(3):
        try:
            response = requests.get(
                writer.FACTGRID_API,
                params={'action': 'wbgetentities', 'ids': '|'.join(batch),
                        'props': 'claims|labels', 'languages': 'en', 'format': 'json'},
                headers={'User-Agent': 'CDLI-FactGrid-resume-read-review/1.0'},
                timeout=35,
            )
            if response.status_code in {429, 502, 503, 504} and attempt < 2:
                delay = response.headers.get('Retry-After', '')
                time.sleep(int(delay) if delay.isdigit() else 3 * (attempt + 1))
                continue
            response.raise_for_status()
            break
        except (requests.ConnectionError, requests.Timeout):
            if attempt == 2:
                raise
            time.sleep(3 * (attempt + 1))
    try:
        data = response.json()
    except ValueError:
        content_type = response.headers.get('content-type')
        raise RuntimeError(f'FactGrid did not return API JSON: status={response.status_code}, content-type={content_type}') from None
    if 'error' in data:
        raise RuntimeError(data['error'])
    received = data.get('entities', {})
    if not set(batch).issubset(received):
        raise RuntimeError('API response omitted requested entities; review is incomplete.')
    time.sleep(0.5)
    return received

with ThreadPoolExecutor(max_workers=options.read_workers) as executor:
    for received in executor.map(read_entities, batches):
        entities.update(received)
        print(f'Read {len(entities)}/{len(qids)} FactGrid items', flush=True)
(outputdir/'candidate_live_entities.json').write_text(json.dumps(entities,ensure_ascii=False))

def value(snak):
    return writer.normalize_claim_datavalue(snak.get('datavalue',{}).get('value',''))

rows=[]
plans_by_cdli = dict(tuple(plan.groupby("cdli_id", sort=False)))
for _,artifact in items.iterrows():
    cdli=artifact.cdli_id
    qid=artifact.factgrid_qid
    entity=entities.get(qid,{})
    claims=entity.get('claims',{})
    item_plan=plans_by_cdli.get(cdli, plan.iloc[:0])
    checks=[(r.field_name,r.fg_pid,r.value,'','') for _,r in item_plan.iterrows() if r.field_name!='inventory_number']
    checks.extend(('research_project','P131',project,'','') for project in writer.parse_qid_list(writer.DEFAULT_RESEARCH_PROJECT_QIDS))
    inventories=list(item_plan.loc[item_plan.field_name.eq('inventory_number'),'value'])
    for _,r in item_plan[item_plan.fg_pid.eq('P329')].iterrows():
        checks.extend(('inventory_number','P329',r.value,'P10',inv[:400]) for inv in inventories)
    for field,prop,expected,qualprop,qualvalue in checks:
        existing=claims.get(prop,[])
        matching=[c for c in existing if value(c.get('mainsnak',{}))==expected]
        values=[value(c.get('mainsnak',{})) for c in existing]
        if 'missing' in entity or not entity:
            status='missing_entity'
        elif options.verified_existing_mapping and prop == writer.FACTGRID_CDLI_ID_PROPERTY and (
            set(values) != {expected} or not any(c.get('rank') != 'deprecated' for c in matching)
        ):
            status='conflict_same_property'
        elif prop in writer.EXTERNAL_ENRICHMENT_PROPERTIES and any(v != expected for v in values):
            status='conflict_same_property'
        elif prop in writer.SINGLE_VALUE_PROPERTIES and any(v and v != expected for v in values):
            status='conflict_same_property'
        elif matching:
            status='already_live'
            if qualprop and not any(value(s)==qualvalue for c in matching for s in c.get('qualifiers',{}).get(qualprop,[])):
                status='missing_qualifier'
        elif prop in writer.SINGLE_VALUE_PROPERTIES and any(values):
            status='conflict_same_property'
        else:
            status='missing'
        rows.append(dict(cdli_id=cdli,factgrid_qid=qid,field_name=field,property=prop,value=expected,qualifier_property=qualprop,qualifier_value=qualvalue,review_status=status,live_values=' | '.join(values)))
review=pd.DataFrame(rows)
review.to_csv(outputdir/'candidate_live_review_1500.csv',index=False)
summary=review.groupby(['field_name','review_status']).size().rename('count').reset_index()
summary.to_csv(outputdir/'candidate_live_review_summary.csv',index=False)
print(summary.to_string(index=False),flush=True)
blocked=set(review.loc[review.review_status.isin(['conflict_same_property','missing_entity']),'cdli_id'])
needs=set(review.loc[review.review_status.isin(['missing','missing_qualifier']),'cdli_id'])-blocked
verified=set(review.loc[review.field_name.eq('cdli_id') & review.review_status.eq('already_live'), 'cdli_id'])
qualifier_holds=set(review.loc[review.review_status.eq('missing_qualifier'), 'cdli_id'])
safe=items[items.cdli_id.isin(needs & verified - qualifier_holds)].copy()
safe.to_csv(outputdir/'candidate_items_reviewed.csv',index=False)
print(json.dumps({'selected_items':len(items),'blocked_items':len(blocked),'items_needing_additions_without_conflicts':len(safe),'items_already_complete':len(set(items.cdli_id)-blocked-set(review.loc[review.review_status.isin(['missing','missing_qualifier']), 'cdli_id']))}),flush=True)
