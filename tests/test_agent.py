"""Offline regression tests; never contact cloud or write a live case."""
import pytest
from scripts.agent.queries import context_query
from scripts.agent.storage import CaseStore
from scripts.agent.signals import analyze
from scripts.agent.llm import InferenceClient

def test_query_rejects_injection():
    with pytest.raises(ValueError):
        context_query({'customer_id':'bad"; DROP GRAPH','card_id':'C1-K1','flagged_txn_id':'1','opened_at':'2016-12-01 00:00:00'})

def test_query_has_asof_filters():
    q=context_query({'customer_id':'C1','card_id':'C1-K1','flagged_txn_id':'1','opened_at':'2016-12-01 00:00:00'})
    assert 't.ts <=' in q
    assert 'HHG_KNOWN_ON_CARD' in q
    assert 'HHG_CARD_IN_CLOSED_CASE' in q

def test_cloud_requires_key(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    client=InferenceClient(provider='openai')
    with pytest.raises(RuntimeError,match='OPENAI_API_KEY'):
        client.json('test',{},{})

def test_unknown_provider_is_not_silently_replaced():
    with pytest.raises(ValueError):
        InferenceClient(provider='nonexistent')

def test_html_start_page_is_not_success():
    class Response:
        headers={'Content-Type':'text/html'}
        def raise_for_status(self): pass
    class Session:
        def request(self,*a,**k): return Response()
    store=CaseStore()
    store.session=Session()
    assert store.ready() is False
