"""Read-only submission audit. Presence is not equivalent to verified completion."""
import csv
import json
from pathlib import Path
from scripts.agent.llm import ROOT
from scripts.agent.validation import validate_case_json


def main():
    rows=list(csv.DictReader((ROOT/'data/raw/case_pack.csv').open(encoding='utf-8-sig')))
    cases=[]
    for row in rows:
        path=ROOT/'cases'/(row['case_id']+'.json')
        if not path.exists():
            cases.append({'case_id':row['case_id'],'errors':['missing output']});continue
        data=json.loads(path.read_text(encoding='utf-8'))
        errs=validate_case_json(data)
        trace=ROOT/'results/traces'/(row['case_id']+'.json')
        if not trace.exists(): errs.append('No verified engine trace; legacy output not accepted')
        cases.append({'case_id':row['case_id'],'errors':errs,'graph_write_claim':data['case'].get('written_to_graph',False)})
    report={'case_files':len(list((ROOT/'cases').glob('HHG-*.json'))),
            'validated_with_trace':sum(not c['errors'] for c in cases),'required':len(rows),'cases':cases,
            'video_files':[str(p.relative_to(ROOT)) for p in (ROOT/'docs').rglob('*') if p.suffix.lower() in {'.mp4','.webm','.mov'}],
            'blog_draft_exists':(ROOT/'docs/BLOG_POST.md').exists(),
            'git_repository_exists':(ROOT/'.git').exists(),
            'note':'Live graph readback, publication links, hidden-label accuracy and complete UI progression require separate verification.'}
    (ROOT/'results/submission_audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__': main()
