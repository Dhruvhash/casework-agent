"""Add agent memory/vector schema, index supplied documents, install retrieval."""
import asyncio
import csv
import json
from pathlib import Path
from scripts.agent.mcp_client import TigerGraphMCP
from scripts.agent.graph_client import GraphClient
from scripts.agent.llm import embed, ROOT

SCHEMA = '''USE GRAPH FraudInvestigation
CREATE SCHEMA_CHANGE JOB HHG_AgentMemory_v2 FOR GRAPH FraudInvestigation {
 ADD VERTEX HHG_Document (PRIMARY_ID document_id STRING, text STRING, source STRING, kind STRING, closed_at STRING);
 ALTER VERTEX HHG_InvestigationCase ADD ATTRIBUTE (payload_json STRING);
 ADD DIRECTED EDGE HHG_CITES (FROM HHG_InvestigationCase, TO HHG_Document);
}
RUN SCHEMA_CHANGE JOB HHG_AgentMemory_v2
'''
SEARCH = '''USE GRAPH FraudInvestigation
CREATE QUERY HHG_VectorSearch(LIST<FLOAT> query_vec, INT k, STRING doc_kind) FOR GRAPH FraudInvestigation SYNTAX v3 {
 MapAccum<VERTEX, FLOAT> @@distances;
 all_docs = {HHG_Document.*};
 candidates = SELECT d FROM all_docs:d WHERE d.kind == doc_kind;
 matches = vectorSearch({HHG_Document.embedding}, query_vec, k, {candidate_set: candidates, distance_map: @@distances});
 PRINT matches, @@distances AS distances;
}
INSTALL QUERY HHG_VectorSearch
'''


def documents():
    import re
    text = (ROOT / 'data/raw/README.md').read_text(encoding='utf-8')
    sections = re.split(r'(?m)(?=^#{1,3} )', text)
    docs = [{'id': f'POLICY-{i:03}', 'text': s, 'source': 'dataset README: '+s.splitlines()[0], 'kind':'policy', 'closed_at':''}
            for i,s in enumerate(sections) if s.strip() and len(s) < 18000]
    allowed={'POLICY-010'}|{f'POLICY-{i:03}' for i in range(17,27)}
    for d in docs:
        if d['id'] not in allowed:d['kind']='reference'
    for row in csv.DictReader((ROOT / 'data/raw/closed_cases_history.csv').open(encoding='utf-8-sig')):
        docs.append({'id':row['case_id'], 'text':row['analyst_notes'], 'source':'closed_cases_history.csv', 'kind':'history', 'closed_at':row['closed_at']})
    docs.append({'id':'FFIEC-RED-FLAGS', 'text':'Regulatory context: a red flag warrants investigation but is not proof of criminal activity. Compare activity with the customer profile and investigate possible legitimate explanations. This context does not replace the hackathon policy or establish its dollar thresholds as law.', 'source':'https://bsaaml.ffiec.gov/manual/Appendices/07', 'kind':'policy','closed_at':''})
    return docs


async def main():
    client = GraphClient()
    async with TigerGraphMCP() as mcp:
        ls = await mcp.call('gsql', command='USE GRAPH FraudInvestigation\nLS')
        if 'HHG_Document' not in ls['result']:
            print('Deploying agent schema', flush=True)
            print((await mcp.call('gsql', command=SCHEMA))['result'], flush=True)
        ls = await mcp.call('gsql', command='USE GRAPH FraudInvestigation\nLS')
        if 'embedding' not in ls['result']:
            print('Adding native vector index', flush=True)
            await mcp.call('add_vector_attribute', vertex_type='HHG_Document', vector_name='embedding', dimension=768)
        cache = ROOT/'data/processed/document_vectors.jsonl'
        loaded = {d['id']:d for d in map(json.loads, cache.read_text(encoding='utf-8').splitlines())} if cache.exists() else {}
        docs = documents()
        for i in range(0, len(docs), 32):
            batch = docs[i:i+32]
            missing = [d for d in batch if d['id'] not in loaded]
            if missing:
                vectors = embed(['search_document: '+d['text'] for d in missing])
                with cache.open('a',encoding='utf-8') as out:
                    for d,v in zip(missing,vectors):
                        record = dict(d, embedding=v)
                        loaded[d['id']] = record
                        out.write(json.dumps(record)+'\n')
            for d in batch:loaded[d['id']]['kind']=d['kind']
            payload = {'vertices':{'HHG_Document':{d['id']:{k:{'value':v} for k,v in loaded[d['id']].items() if k!='id'} for d in batch}}}
            result = client._request('POST', '/restpp/graph/FraudInvestigation', json=payload)
            if result.get('error') or result.get('results',[{}])[0].get('accepted_vertices') != len(batch):
                raise RuntimeError('Document upsert failed: '+str(result)[:500])
            print(f'Indexed {min(i+32,len(docs))}/{len(docs)} documents', flush=True)
        print((await mcp.call('gsql', command=SEARCH))['result'], flush=True)
        check = await mcp.call('run_installed_query', query_name='HHG_VectorSearch', params={'query_vec':embed(['search_query: recurring legitimate customer confirms'])[0], 'k':3, 'doc_kind':'history'})
        (ROOT/'results/vector_verification.json').write_text(json.dumps({'documents':len(docs),'mcp_trace':mcp.trace,'search':check},indent=2),encoding='utf-8')
        print('Native vector retrieval verified', flush=True)


if __name__ == '__main__':
    asyncio.run(main())
