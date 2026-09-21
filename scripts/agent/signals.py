"""Explainable features computed from as-of graph evidence, never risk-score verdicts."""
from collections import Counter
from datetime import datetime, timedelta
from statistics import median
from .queries import attrs
from .algorithms import relationships


def analyze(context, row):
    trigger = attrs(context['trigger'])[0]
    ts = datetime.fromisoformat(trigger['ts'])
    history = sorted(attrs(context['history']), key=lambda t:(t['ts'],t['id']))
    baseline = [t for t in history if t['ts'] < (ts-timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S')]
    known = sorted(attrs(context['known']), key=lambda t:(t['ts'],t['id']))
    window = [t for t in known if ts-timedelta(hours=1) <= datetime.fromisoformat(t['ts']) <= ts]
    tiny = [t for t in window if t['channel']=='online' and 0 < abs(t['amount_usd']) < 5 and t['ts'] < trigger['ts']]
    testing = len(tiny)>=3 and trigger['channel']=='online' and abs(trigger['amount_usd'])>max(abs(t['amount_usd']) for t in tiny)
    normal_amount = median([abs(t['amount_usd']) for t in baseline]) if baseline else None
    regions = Counter(t['billing_region'] for t in baseline if t['billing_region'])
    new_region = bool(regions and trigger['billing_region'] and trigger['billing_region'] not in regions)
    unusual_amount = normal_amount is not None and abs(trigger['amount_usd'])>max(100,normal_amount*3)
    new_product = bool(baseline and trigger['product_code'] not in {t['product_code'] for t in baseline})
    device_edges = [e for e in context.get('links',[]) if e['e_type']=='HHG_FROM_DEVICE']
    new_device = any(e.get('attributes',{}).get('device_new','').lower()=='new' for e in device_edges)
    proxy = any(e.get('attributes',{}).get('proxy_type','').lower() in {'anonymous','hidden','ip_proxy:anonymous','ip_proxy:hidden'} for e in device_edges)
    amount_matches = [t for t in baseline if abs(t['amount_usd']-trigger['amount_usd']) < .05 and t['product_code']==trigger['product_code']]
    # Merchant identity is absent. This is a cadence hint, never proof of R7.
    monthly = any(27 <= (ts-datetime.fromisoformat(t['ts'])).total_seconds()/86400 <= 33 for t in amount_matches)
    signal_count = sum([new_region,unusual_amount,new_product,new_device,proxy,testing])
    network=relationships(context,row)
    recent=[t for t in known if ts-timedelta(hours=48)<=datetime.fromisoformat(t['ts'])<=ts]
    mixed=len({t['channel'] for t in recent})>1
    takeover=mixed and new_device and proxy and (unusual_amount or new_region)
    if testing:
        pattern='card_testing'
    elif takeover:
        pattern='account_takeover'
    elif trigger['channel']=='online' and new_device and (unusual_amount or new_product or proxy):
        pattern='card_not_present_new_device'
    elif trigger['channel']=='online' and (unusual_amount or new_product):
        pattern='card_not_present_fraud'
    elif trigger['channel']=='in_person' and new_region:
        pattern='out_of_region_use'
    else:
        pattern='none'
    coordinated=network['coordinated'] or (network['shared_fraud'] and pattern=='none')
    if coordinated: pattern='undocumented'
    probability = .15 if len(baseline)>=10 and signal_count==0 else min(.80,.30+.12*signal_count)
    if testing:
        probability=.86
    if takeover or network['shared_fraud'] or coordinated: probability=max(probability,.86)
    affected = tiny+[trigger] if testing else [trigger]
    if coordinated:
        affected=sorted({t['id']:t for t in affected+attrs(context.get('neighbors',[])) if t['id']==trigger['id'] or t['id'] in network['coordinated_txns']}.values(),key=lambda t:(t['ts'],t['id']))
    return {'trigger':trigger,'baseline_count':len(baseline),'median_amount':normal_amount,
            'home_region':regions.most_common(1)[0][0] if regions else None,
            'new_region':new_region,'unusual_amount':unusual_amount,'new_product':new_product,
            'new_device':new_device,'proxy':proxy,'testing':testing,'monthly_amount_hint':monthly,
            'signal_count':signal_count,'pattern':pattern,'probability':probability,'affected':affected,
            'network':network,'takeover':takeover,'coordinated':coordinated,
            'history_tail':history[-15:], 'neighbor_count':len(context.get('neighbors',[])),
            'candidate_connected_cards':[v['v_id'] for v in context.get('connected',[]) if v['v_id']!=row['card_id']],
            'limitations':['Customer history is not proven card history.','Shared device profiles are not unique physical devices.',
                          'No merchant identifier or settlement status is supplied.','Probability is a heuristic, not a calibrated model.']}
