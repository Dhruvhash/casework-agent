# GSQL deployment status

The dataset-backed graph schema in [`tigergraph/schema/schema.gsql`](../tigergraph/schema/schema.gsql) has been deployed to Savanna's `FraudInvestigation` graph. The live schema API confirms all eight vertex types and eleven forward edge types, each with its reverse edge. Do not rerun the schema change job.

The repeatable GSQL loading job is generated at `tigergraph/loading/load_prepared.gsql` by `python scripts/ingest/load_tigergraph.py`. See [automated loading](DATA_LOADING.md) for verification evidence and resume behavior. The live investigator uses the bounded as-of traversal in `scripts/agent/queries.py`. `scripts/deploy_agent.py` adds document/vector memory and installs `HHG_VectorSearch`; `scripts/deploy_memory.py` installs `HHG_MemorySearch` for generated investigations. Both retrieval queries have been installed successfully on the development workspace.
