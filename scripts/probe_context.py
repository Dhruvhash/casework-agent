import csv
import json
from pathlib import Path
from scripts.agent.graph_client import GraphClient
from scripts.agent.queries import context_query, unpack


if __name__ == '__main__':
    row = next(csv.DictReader(open('data/raw/case_pack.csv', encoding='utf-8-sig')))
    client = GraphClient()
    result = client._request('POST', '/gsql/v1/queries/interpret', data=context_query(row), headers={'Content-Type':'text/plain'})
    if result.get('error'):
        print(result)
        raise SystemExit(1)
    data = unpack(result['results'])
    print({k:len(v) for k,v in data.items()})
    Path('results/context_probe.json').write_text(json.dumps(data), encoding='utf-8')
