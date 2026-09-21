"""Meaningful policy/state transitions and graph-motif guardrails."""
from scripts.agent.policy import decide
from scripts.agent.algorithms import relationships

def names(d): return {a['action'] for a in d['actions']}

def test_verification_progression_requires_human_block_approval():
    initial=decide(.42,1500)
    final=decide(.42,1500,response='denied')
    assert 'BLOCK_CARD' not in names(initial)
    assert {'BLOCK_CARD','FILE_REPORT','CREATE_CASE'}<=names(final)
    assert next(a['route'] for a in final['actions'] if a['action']=='FILE_REPORT')=='L2'

def test_no_reply_escalates_without_confirming_fraud():
    result=decide(.5,600,response='no_reply_24h')
    assert result['verdict']=='uncertain' and result['status']=='escalated'
    assert {'MONITOR_CARD','DECLINE_TRANSACTION'}<=names(result)
    assert 'BLOCK_CARD' not in names(result)

def test_block_all_is_never_inferred_from_single_denial():
    assert 'BLOCK_ALL_CARDS' not in names(decide(.5,50,response='denied'))
    r=decide(.5,50,response='denied',confirmed_cards=2)
    assert next(a['route'] for a in r['actions'] if a['action']=='BLOCK_ALL_CARDS')=='L2'

def test_recurring_dispute_requires_verified_merchant():
    a=decide(.4,49,dispute=True)
    b=decide(.4,49,dispute=True,recurring_verified=True)
    assert 'WARN_CUSTOMER' not in names(a)
    assert {'WARN_CUSTOMER','VERIFY_WITH_CUSTOMER','CREATE_CASE'}<=names(b)

def test_generic_shared_profile_does_not_make_a_ring():
    c={'links':[{'from_id':'D1','to_id':str(i),'e_type':'HHG_DEVICE_USED_FOR','attributes':{}} for i in range(5)]}
    r=relationships(c,{'card_id':'C1-K1','opened_at':'2016-12-01'})
    assert not r['coordinated'] and not r['shared_fraud']
    assert len(r['components'])==1 and r['degree']['D1']==5

def test_coordinated_motif_needs_separate_customers():
    edges=[]
    for i in range(3):
        edges.extend([{'from_id':'D1','to_id':str(i),'e_type':'HHG_DEVICE_USED_FOR','attributes':{'device_new':'New','proxy_type':'IP_PROXY:ANONYMOUS'}},
                      {'from_id':str(i),'to_id':'C'+str(i),'e_type':'HHG_TRANSACTION_OF'}])
    r=relationships({'links':edges,'neighbors':[{}, {}, {}]}, {'card_id':'C1-K1','opened_at':'2016-12-01'})
    assert r['coordinated'] and len(r['coordinated_customers'])==3
