from scripts.deploy_agent import documents
from scripts.agent.storage import CaseStore

if __name__=='__main__':
    docs=[d for d in documents() if d['id'].startswith('POLICY-')]
    s=CaseStore()
    r=s.request('POST',f'/restpp/graph/{s.graph}',json={'vertices':{'HHG_Document':{d['id']:{'kind':{'value':d['kind']}} for d in docs}}})
    print(r['results'])
