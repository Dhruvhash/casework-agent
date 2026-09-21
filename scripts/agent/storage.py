"""Verified case persistence. Never pollute historical ground-truth vertices."""
import json
import os
from urllib.parse import quote
import requests
from dotenv import load_dotenv
from .llm import ROOT


class CaseStore:
    def __init__(self):
        load_dotenv(ROOT/'.env')
        self.host = os.getenv('TG_HOST','').rstrip('/')
        self.graph = os.getenv('TG_GRAPHNAME','FraudInvestigation')
        self.session = requests.Session()
        self.session.trust_env = False
        secret = os.getenv('TG_SECRET')
        self.session.headers['Authorization'] = 'GSQL-Secret '+secret if secret else 'Bearer '+os.getenv('TG_API_TOKEN','')
        self.calls = 0

    def request(self, method, path, **kwargs):
        self.calls += 1
        r = self.session.request(method,self.host+path,timeout=(10,60),**kwargs)
        r.raise_for_status()
        if 'json' not in r.headers.get('Content-Type','').lower():
            raise RuntimeError('Workspace is starting or returned non-JSON; retry when ready')
        body = r.json()
        if body.get('error'):
            raise RuntimeError(body.get('message','TigerGraph request failed'))
        return body

    def ready(self):
        try:
            self.request('GET','/restpp/echo')
            return True
        except (requests.RequestException,ValueError,RuntimeError):
            return False

    def save(self, data, row, document_ids):
        c = data['case']
        cid = data['case_id']
        attrs = {k:{'value':c[k]} for k in ('status','verdict','fraud_probability','summary')}
        attrs.update(updated_at={'value':row['opened_at']},payload_json={'value':json.dumps(data)})
        edges = {'HHG_INVESTIGATION_FOR_CUSTOMER':{'HHG_Customer':{row['customer_id']:{}}},
                 'HHG_INVESTIGATION_OF':{'HHG_Transaction':{tid:{} for tid in set(c['affected_txn_ids']+[row['flagged_txn_id']])}}}
        if document_ids:
            edges['HHG_CITES'] = {'HHG_Document':{d:{} for d in document_ids}}
        body = {'vertices':{'HHG_InvestigationCase':{cid:attrs}},'edges':{'HHG_InvestigationCase':{cid:edges}}}
        result = self.request('POST',f'/restpp/graph/{self.graph}',json=body)
        if result.get('results',[{}])[0].get('accepted_vertices') != 1:
            raise RuntimeError('Case vertex was not acknowledged')
        saved = self.request('GET',f'/restpp/graph/{self.graph}/vertices/HHG_InvestigationCase/{quote(cid,safe="")}')['results']
        if not saved or saved[0]['attributes'].get('payload_json') != attrs['payload_json']['value']:
            raise RuntimeError('Case readback did not match the submitted payload')
        c['written_to_graph'], c['graph_case_id'] = True, cid
        # Persist the verified flag only after successful readback.
        self.request('POST', f'/restpp/graph/{self.graph}',json={'vertices':{'HHG_InvestigationCase':{cid:{'payload_json':{'value':json.dumps(data)}}}}})
        return cid
