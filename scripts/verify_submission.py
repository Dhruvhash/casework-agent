"""Verify all answer semantics against source IDs, amounts and live graph readback."""
import csv
import json
from datetime import datetime, timezone
from scripts.agent.llm import ROOT
from scripts.agent.validation import validate_case_json
from scripts.agent.policy import exposure
from scripts.agent.storage import CaseStore

def main():
    pack=list(csv.DictReader((ROOT/'data/raw/case_pack.csv').open(encoding='utf-8-sig')))
    outputs={r['case_id']:json.loads((ROOT/'cases'/(r['case_id']+'.json')).read_text(encoding='utf-8')) for r in pack}
    wanted={tid for d in outputs.values() for tid in d['case']['affected_txn_ids']}
    tx={r['txn_id']:r for r in csv.DictReader((ROOT/'data/processed/transactions.csv').open(encoding='utf-8')) if r['txn_id'] in wanted}
    cards={r['card_id'] for r in csv.DictReader((ROOT/'data/processed/cards.csv').open())}
    history={r['case_id'] for r in csv.DictReader((ROOT/'data/raw/closed_cases_history.csv').open(encoding='utf-8-sig'))}
    store=CaseStore(); results=[]
    for row in pack:
        d=outputs[row['case_id']]; c=d['case']; errors=validate_case_json(d)
        ids=c['affected_txn_ids']
        if any(t not in tx for t in ids):errors.append('Unknown affected transaction')
        else:
            if exposure([tx[t] for t in ids])!=c['exposure_usd']:errors.append('Exposure does not match source')
            if any(tx[t]['ts']>row['opened_at'] for t in ids):errors.append('Future transaction leakage')
            if ids and c['first_suspicious_txn_id']!=min(ids,key=lambda t:(tx[t]['ts'],t)):errors.append('Incorrect episode start')
        if c['verdict']!='legitimate' and row['flagged_txn_id'] not in ids:errors.append('Flagged transaction missing')
        if any(x not in cards for x in c['connected_card_ids']):errors.append('Unknown connected card')
        if any(x not in history for x in c['similar_prior_cases']):errors.append('Unknown original historical case')
        trace=ROOT/'results/traces'/(row['case_id']+'.json')
        if not trace.exists():errors.append('Missing execution trace')
        else:
            t=json.loads(trace.read_text(encoding='utf-8'))
            if not all(x.get('success') for x in t['mcp_calls']):errors.append('Failed MCP call')
            if not t['facts'].get('network'):errors.append('Legacy engine trace')
        try:
            saved=store.request('GET',f"/restpp/graph/{store.graph}/vertices/HHG_InvestigationCase/{row['case_id']}")['results']
            if not saved or json.loads(saved[0]['attributes']['payload_json'])!=d:errors.append('Live graph payload differs')
        except Exception as exc:errors.append('Live readback failed: '+type(exc).__name__)
        results.append({'case_id':row['case_id'],'errors':errors,'verified':not errors})
        print(row['case_id'], 'PASS' if not errors else errors,flush=True)
    report={'checked_at':datetime.now(timezone.utc).isoformat(),'passed':sum(r['verified'] for r in results),'required':len(pack),'cases':results}
    (ROOT/'results/final_verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    if report['passed']!=len(pack):raise SystemExit(1)

if __name__=='__main__':main()
