# Automated Savanna loading

The deployed `FraudInvestigation` schema is populated by:

```powershell
python scripts/ingest/load_tigergraph.py
```

Credentials come from `.env` (`TG_HOST`, `TG_GRAPHNAME`, `TG_SECRET`). The script
creates or updates its own `HHG_LoadPrepared_v1` GSQL loading job, then streams
prepared CSV records as JSON batches through the REST loading endpoint. JSON
preserves commas, quotes, and other characters in historical analyst notes.

Before uploading, it checks unique IDs, every edge endpoint, finite numeric
values, and the customer/time ordering of transaction sequence edges. Every
batch must report the expected accepted line/object counts and zero parsing or
attribute errors. Primary IDs make retries idempotent. Completed files have
content hashes recorded in `results/tigergraph_load_checkpoint.json`.

After loading, the script compares exact vertex and edge counts, including
reverse edges, against the local files and reads stored sample records back to
check their attributes. Evidence is saved in
`results/tigergraph_load_report.json`. A successful upload alone is not a
successful verification; check that this report has `verified: true`.

To check an existing load without uploading again:

```powershell
python scripts/ingest/load_tigergraph.py --verify-only
```

API streaming uploads may not appear as individual uploaded CSV jobs in
Savanna's Load Data screen. Use Explore Graph or the saved verification report
to inspect the resulting data.

## Modeling details

- `HHG_KNOWN_CARD_TRANSACTION` contains only explicit card/transaction anchors.
  The source data cannot establish a card for every transaction.
- One transaction/domain pair has one email edge. When purchaser and recipient
  domains match, `email_role` is `purchaser|recipient`. There are 531,106 unique
  edges from 633,715 original role observations; both roles are preserved.
- `closed_case_transaction_edges.csv` links each historical case to its listed
  transactions. There are 14,955 such links.
- `HHG_InvestigationCase` is intentionally empty until the investigation agent
  writes actual results.

Local preparation statistics in `data/processed/ingestion_stats.json` describe
the preparation step only. Live deployment evidence is in the separate load
report.

Sources: [GSQL loading APIs](https://www.tigergraph.com/docs/tigergraph-server/4.2/api/gsql-endpoints),
[JSON loading](https://www.tigergraph.com/docs/gsql-ref/4.2/ddl-and-loading/creating-a-loading-job).
