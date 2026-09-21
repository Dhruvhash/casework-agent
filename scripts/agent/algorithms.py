"""Connected components and shared-origin motifs on the retrieved graph.

Components demonstrate relationships, not culpability. Confirmed historical labels
are accepted only from the supplied closed-case file and before the as-of time.
"""
from collections import defaultdict
import csv
from functools import lru_cache
from .llm import ROOT


@lru_cache(maxsize=1)
def historical_labels():
    return {r['case_id']:r for r in csv.DictReader((ROOT/'data/raw/closed_cases_history.csv').open(encoding='utf-8-sig'))}


def relationships(context, row):
    adjacency=defaultdict(set)
    for e in context.get('links',[]):
        a,b=e['from_id'],e['to_id']; adjacency[a].add(b); adjacency[b].add(a)
    remaining=set(adjacency); components=[]
    while remaining:
        seed=min(remaining); seen={seed}; stack=[seed]
        while stack:
            for nxt in adjacency[stack.pop()]-seen:
                seen.add(nxt);stack.append(nxt)
        remaining-=seen;components.append(sorted(seen))
    labels=historical_labels()
    confirmed=[v['v_id'] for v in context.get('neighbor_prior',[]) if v['v_id'] in labels
               and labels[v['v_id']]['closed_at']<=row['opened_at'] and labels[v['v_id']]['outcome']=='confirmed_fraud']
    cards=sorted({labels[c]['card_id'] for c in confirmed})
    candidates=sorted({v['v_id'] for v in context.get('connected',[]) if v['v_id']!=row['card_id']})
    # R6 needs evidence of fraud on several cards, not only a shared generic profile.
    shared=len(cards)>=2
    suspicious_txns={e['to_id'] for e in context.get('links',[]) if e['e_type']=='HHG_DEVICE_USED_FOR'
                     and e.get('attributes',{}).get('device_new','').lower()=='new'
                     and e.get('attributes',{}).get('proxy_type','').lower() in {'ip_proxy:anonymous','ip_proxy:hidden','anonymous','hidden'}}
    customers={e['to_id'] for e in context.get('links',[]) if e['e_type']=='HHG_TRANSACTION_OF' and e['from_id'] in suspicious_txns}
    coordinated=len(customers)>=3 and len(suspicious_txns)>=3 and len(suspicious_txns)>=.8*len(context.get('neighbors',[]))
    return {'components':components,'node_count':len(adjacency),'edge_count':len(context.get('links',[])),
            'candidate_cards':candidates,'confirmed_prior_ids':confirmed,'shared_fraud':shared,
            'coordinated':coordinated,'coordinated_txns':sorted(suspicious_txns) if coordinated else [],'coordinated_customers':sorted(customers) if coordinated else [],
            'connected_cards':sorted(set(cards+candidates)-{row['card_id']}) if shared or coordinated else [],
            'profiles':[v['attributes']['profile'] for v in context.get('devices',[])] if shared or coordinated else [],
            'degree':{k:len(v) for k,v in adjacency.items()},
            'explanation':'Connected components and degree describe the evidence neighborhood; profile sharing alone is not proof of fraud.'}
