"""Versioned graph memory. Generated outcomes remain explicitly simulated/unverified."""
import hashlib
import json
from datetime import datetime, timezone
from .llm import ROOT, embed


def persist_memory(store, data, row, vector):
    cid=data['case_id']
    digest=hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()[:16]
    snapshot={'recorded_at':datetime.now(timezone.utc).isoformat(),'as_of':row['opened_at'],
              'revision':digest,'case':data,'evidence_status':'Generated investigation; verification responses are simulations, not ground truth.'}
    text=json.dumps(snapshot,ensure_ascii=False)
    docid='INV-'+cid+'-'+digest
    attrs={'text':text,'source':'generated investigation '+cid,'kind':'investigation','closed_at':row['opened_at'],'embedding':vector}
    store.request('POST',f'/restpp/graph/{store.graph}',json={
        'vertices':{'HHG_Document':{docid:{k:{'value':v} for k,v in attrs.items()}}},
        'edges':{'HHG_InvestigationCase':{cid:{'HHG_CITES':{'HHG_Document':{docid:{}}}}}}})
    folder=ROOT/'results/history'/cid
    folder.mkdir(parents=True,exist_ok=True)
    target=folder/(digest+'.json')
    if not target.exists(): target.write_text(json.dumps(snapshot,indent=2),encoding='utf-8')
    return docid


def memory_text(data):
    c=data['case']
    return 'search_document: '+c['summary']+' Pattern: '+c['pattern']+' '+data['next_best_actions']['what_changed']
