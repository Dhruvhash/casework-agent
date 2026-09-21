"""Generate benchmark answers atomically; any failed case makes the command fail."""
import argparse
import csv
import json
from scripts.agent.engine import CaseInvestigator, CASE_PACK_PATH
from scripts.agent.llm import ROOT
from scripts.agent.validation import validate_case_json


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--case', help='Run one supplied benchmark ID')
    parser.add_argument('--response',choices=['pending','confirmed','denied','no_reply_24h'],default='pending')
    parser.add_argument('--no-persist',action='store_true')
    args=parser.parse_args()
    rows=list(csv.DictReader(CASE_PACK_PATH.open(encoding='utf-8-sig')))
    rows.sort(key=lambda r:(r['opened_at'],r['case_id']))
    if args.case:
        rows=[r for r in rows if r['case_id']==args.case]
        if not rows: raise SystemExit('Unknown benchmark ID')
    agent=CaseInvestigator()
    output=ROOT/'cases'
    output.mkdir(exist_ok=True)
    failures=[]
    summary=[]
    for row in rows:
        cid=row['case_id']
        print('Investigating '+cid,flush=True)
        try:
            data=agent.investigate_case(row,response=args.response,persist=not args.no_persist)
            errors=validate_case_json(data)
            if errors: raise ValueError('; '.join(errors))
            tmp=output/(cid+'.tmp')
            tmp.write_text(json.dumps(data,indent=2,allow_nan=False),encoding='utf-8')
            tmp.replace(output/(cid+'.json'))
            summary.append({'case_id':cid,'verdict':data['case']['verdict'],'written_to_graph':data['case']['written_to_graph'],'tokens':data['tokens'],'tool_calls':data['tool_calls']})
            print(summary[-1],flush=True)
        except Exception as e:
            failures.append({'case_id':cid,'error':str(e)[:1000]})
            print('FAILED '+cid+': '+str(e)[:400],flush=True)
    report_name=('scenario_'+args.case+'_'+args.response+'.json') if args.case else 'benchmark_validation.json'
    (ROOT/'results'/report_name).write_text(json.dumps({'response_scenario':args.response,'completed':summary,'failures':failures},indent=2),encoding='utf-8')
    if failures: raise SystemExit(1)


if __name__=='__main__':
    main()
