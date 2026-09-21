"""Validate the benchmark contract and cross-field policy consistency."""
import math
from .policy import route

PATTERNS={'card_testing','card_not_present_fraud','card_not_present_new_device','out_of_region_use','account_takeover','undocumented','none'}
ACTIONS={'ALLOW_TRANSACTION','DECLINE_TRANSACTION','MONITOR_CARD','MONITOR_CONNECTED_CARDS','WARN_CUSTOMER','VERIFY_WITH_CUSTOMER','STEP_UP_AUTH','BLOCK_CARD','BLOCK_ALL_CARDS','GENERATE_REPORT','CREATE_CASE','FILE_REPORT','ESCALATE_TO_ANALYST','CLOSE_NO_FRAUD'}


def validate_case_json(data):
    errors=[]
    required={'case_id','case','evidence_requests','next_best_actions','sar','stop_reason','tool_calls','tokens','latency_s'}
    if set(data)!=required: errors.append('Top-level contract mismatch')
    c=data.get('case',{}); sar=data.get('sar',{}); nba=data.get('next_best_actions',{})
    fields={'status','verdict','fraud_probability','pattern','pattern_description','affected_txn_ids','first_suspicious_txn_id','connected_card_ids','connected_device_profiles','exposure_usd','evidence','similar_prior_cases','summary','written_to_graph','graph_case_id'}
    if set(c)!=fields: errors.append('Case contract mismatch')
    if c.get('status') not in {'open','closed_fraud','closed_legitimate','escalated'}: errors.append('Invalid status')
    if c.get('verdict') not in {'fraud','legitimate','uncertain'}: errors.append('Invalid verdict')
    p=c.get('fraud_probability',-1)
    if not isinstance(p,(int,float)) or not math.isfinite(p) or not 0<=p<=1: errors.append('Invalid probability')
    if c.get('pattern') not in PATTERNS: errors.append('Invalid pattern')
    if c.get('pattern')=='undocumented' and len(c.get('pattern_description',''))<80: errors.append('Undocumented pattern lacks explanation')
    if type(c.get('written_to_graph')) is not bool: errors.append('Graph flag must be boolean')
    if not isinstance(c.get('exposure_usd'),(int,float)) or not math.isfinite(c.get('exposure_usd',float('nan'))) or c.get('exposure_usd',-1)<0: errors.append('Invalid exposure')
    if c.get('pattern')!='undocumented' and c.get('pattern_description'): errors.append('Unexpected pattern description')
    if c.get('written_to_graph') != bool(c.get('graph_case_id')): errors.append('Graph write claim mismatch')
    affected=c.get('affected_txn_ids',[])
    if len(affected)!=len(set(affected)): errors.append('Duplicate affected transactions')
    if c.get('verdict')=='legitimate' and (affected or c.get('exposure_usd') or c.get('first_suspicious_txn_id') or sar.get('file')): errors.append('Legitimate case retains fraud exposure')
    if affected and c.get('first_suspicious_txn_id') not in affected: errors.append('First suspicious transaction missing')
    for e in c.get('evidence',[]):
        if set(e)!={'claim','source','ref','entity_ids'} or e.get('source') not in {'graph','document','customer','external'}: errors.append('Invalid evidence')
    for group in ('initial','final'):
        for action in nba.get(group,[]):
            if set(action)!={'action','route','reason'}: errors.append('Invalid action contract')
            if action.get('action') not in ACTIONS or not action.get('reason'): errors.append('Unknown action or missing reason')
            if action.get('route')!=route(action.get('action'),c.get('exposure_usd',0)): errors.append('Approval route mismatch')
    names={a['action'] for a in nba.get('final',[])}
    if set(sar)!={'file','reason','narrative','subjects','total_amount_usd','activity_dates'}: errors.append('SAR contract mismatch')
    if set(nba)!={'initial','final','what_changed'}: errors.append('Action groups mismatch')
    if sar.get('file') and (not sar.get('narrative') or len(sar.get('activity_dates',[]))!=2 or not sar.get('subjects')): errors.append('Incomplete SAR')
    for request in data.get('evidence_requests',[]):
        if set(request)!={'type','asked_after_step','assumed_response'} or request.get('type') not in {'customer_validation','step_up_auth','analyst_info'} or not request.get('assumed_response'): errors.append('Invalid evidence request')
    if sar.get('file')!=('FILE_REPORT' in names): errors.append('SAR/action mismatch')
    if 'ESCALATE_TO_ANALYST' in names and c.get('status')!='escalated': errors.append('Escalation/status mismatch')
    if not sar.get('file') and (sar.get('narrative') or sar.get('subjects') or sar.get('total_amount_usd') or sar.get('activity_dates')): errors.append('Non-filed SAR must be empty')
    if sar.get('file') and sar.get('total_amount_usd')!=c.get('exposure_usd'): errors.append('SAR exposure mismatch')
    if not data.get('evidence_requests') and (nba.get('initial')!=nba.get('final') or nba.get('what_changed')!='nothing'): errors.append('Actions changed without new evidence')
    for name in ('tool_calls','tokens'):
        if type(data.get(name)) is not int or data[name]<0: errors.append('Invalid telemetry '+name)
    return errors
