"""Bounded, as-of GSQL traversals; no model-generated executable GSQL."""
import json
import re
from datetime import datetime, timedelta


def context_query(row):
    for field in ('customer_id', 'card_id', 'flagged_txn_id'):
        if not re.fullmatch(r'[A-Za-z0-9_-]+', row[field]):
            raise ValueError('Invalid graph identifier')
    at = datetime.fromisoformat(row['opened_at'])
    since = (at - timedelta(hours=48)).strftime('%Y-%m-%d %H:%M:%S')
    q = json.dumps
    return f'''INTERPRET QUERY () FOR GRAPH FraudInvestigation {{
      SetAccum<EDGE> @@links;
      customers = {{HHG_Customer.*}};
      customer = SELECT c FROM customers:c WHERE c == to_vertex({q(row['customer_id'])}, "HHG_Customer");
      history = SELECT t FROM customer:c -(HHG_HAS_TRANSACTION:e)-> HHG_Transaction:t
        WHERE t.ts <= {q(row['opened_at'])};
      cards = {{HHG_Card.*}};
      card = SELECT c FROM cards:c WHERE c == to_vertex({q(row['card_id'])}, "HHG_Card");
      known = SELECT t FROM card:c -(HHG_KNOWN_CARD_TRANSACTION:e)-> HHG_Transaction:t
        WHERE t.ts <= {q(row['opened_at'])} ACCUM @@links += e;
      trigger = SELECT t FROM history:t WHERE t == to_vertex({q(row['flagged_txn_id'])}, "HHG_Transaction");
      devices = SELECT d FROM trigger:t -(HHG_FROM_DEVICE:e)-> HHG_DeviceProfile:d ACCUM @@links += e;
      neighbors = SELECT t FROM devices:d -(HHG_DEVICE_USED_FOR:e)-> HHG_Transaction:t
        WHERE t.ts >= {q(since)} AND t.ts <= {q(row['opened_at'])} ACCUM @@links += e;
      connected = SELECT c FROM neighbors:t -(HHG_KNOWN_ON_CARD:e)-> HHG_Card:c ACCUM @@links += e;
      neighbor_customers = SELECT c FROM neighbors:t -(HHG_TRANSACTION_OF:e)-> HHG_Customer:c ACCUM @@links += e;
      neighbor_prior = SELECT p FROM neighbors:t -(HHG_TRANSACTION_IN_CLOSED_CASE:e)-> HHG_ClosedCase:p ACCUM @@links += e;
      prior = SELECT p FROM card:c -(HHG_CARD_IN_CLOSED_CASE:e)-> HHG_ClosedCase:p;
      PRINT history, known, trigger, devices, neighbors, connected, prior, neighbor_prior, neighbor_customers, @@links AS links;
    }}'''


def unpack(results):
    merged = {}
    for item in results:
        merged.update(item)
    return merged


def attrs(vertices):
    return [dict(v.get('attributes', {}), id=v['v_id']) for v in vertices]
