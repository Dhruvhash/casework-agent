# TigerGraph Savanna setup for a beginner

TigerGraph is the graph database: it stores customers, cards, transactions, relationships, and case memory. Savanna is TigerGraph's hosted service, so you do not need to install a database server. The challenge requires TigerGraph, GSQL, graph algorithms, MCP, and GraphRAG.

1. Open [TigerGraph Savanna](https://savanna.tgcloud.io). Create an account or sign in. Create a workgroup and a read-write workspace using the free hackathon option available in your account. Enable auto-stop and auto-start, as the challenge PDF directs. The exact button names and available tiers may differ by account; follow the current Savanna wizard.
2. On the workspace card, select **Connect**, then the API connection details. Copy the TigerGraph database endpoint URL, including `https://`, into `TG_HOST` in a new `.env` file copied from `.env.example`. In **Design Schema**, use **Create New Graph** to create an empty graph named `FraudInvestigation`. The local schema change job in `tigergraph/schema/schema.gsql` adds its types after that.
3. Select **Database Secrets** from Savanna's left navigation, click **Create Secret**, name it `hhgoa-agent`, select `MyWorkspace` (or your actual workspace), and create it. Copy the generated secret into `TG_SECRET` in `.env`; it is shown only once. Keep it private. The Savanna organization **API Key** under Admin → Settings is for the Savanna management API and is not this database secret. [TigerGraph's current database secret guide](https://www.tigergraph.com/docs/savanna/main/administration/settings/how2-create-database-secret)
4. Set `TG_GRAPHNAME=FraudInvestigation`. The official MCP server uses the `TG_*` variable names, not `TIGERGRAPH_*`.
5. Install the local Python dependencies: `python -m pip install -r requirements.txt`. Install the official MCP server separately: `python -m pip install tigergraph-mcp`.
6. Run `python scripts/check_tigergraph.py`. It reports configuration, TigerGraph HTTP, graph endpoints, and the presence of the MCP executable separately. An executable being present does not prove a live MCP tool call.
7. Download the five official dataset files to `data/raw/` as described in [DATASET.md](DATASET.md), then run `python scripts/ingest/inspect.py`.

8. For this workspace, the schema is already deployed. Load the validated prepared data with `python scripts/ingest/load_tigergraph.py`. See [automated loading](DATA_LOADING.md) for the verification report. Explicit card anchors are loaded; transactions without an established card remain linked to their known customer.

A `401` or `403` from the check script points to a token/permission issue. A connection error suggests an incorrect URL, a stopped workspace, or a network issue. A graph endpoints `404` suggests the graph name or endpoint is wrong.
