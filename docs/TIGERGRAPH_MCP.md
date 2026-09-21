# Official TigerGraph MCP

MCP is the tool protocol through which the investigation agent will call TigerGraph. This project uses the [official `tigergraph-mcp` server](https://github.com/tigergraph/tigergraph-mcp), whose current README documents `pip install tigergraph-mcp`, `TG_HOST`, optional `TG_GRAPHNAME`, and `TG_SECRET`, with stdio or Streamable HTTP transport. Install it with `python -m pip install tigergraph-mcp` after the Savanna workspace exists. [TigerGraph's Savanna MCP guide](https://www.tigergraph.com/docs/savanna/main/get-started/connect-agent-mcp) specifically recommends a database secret.

The implemented client in `scripts/agent/mcp_client.py` initializes the official server over stdio and invokes real `run_query` and `run_installed_query` tools. Execution traces record successful calls. The model never supplies executable GSQL; the investigator uses fixed, validated templates. Native `HHG_VectorSearch` retrieves original history and policy, while `HHG_MemorySearch` retrieves earlier generated investigations with time and same-case exclusions.

If the server is missing, install the package above. If it starts but cannot reach the graph, verify the `TG_*` values and that Savanna is running. If graph queries fail, verify the GSQL query is installed and permissions permit execution.
