"""Install time-filtered retrieval for versioned generated investigations."""
import asyncio
from scripts.agent.mcp_client import TigerGraphMCP

QUERY='''USE GRAPH FraudInvestigation
CREATE QUERY HHG_MemorySearch(LIST<FLOAT> query_vec, INT k, STRING as_of, STRING exclude_source) FOR GRAPH FraudInvestigation SYNTAX v3 {
 MapAccum<VERTEX, FLOAT> @@distances;
 all_docs = {HHG_Document.*};
 candidates = SELECT d FROM all_docs:d WHERE d.kind == "investigation" AND d.closed_at < as_of AND d.source != exclude_source;
 matches = vectorSearch({HHG_Document.embedding}, query_vec, k, {candidate_set: candidates, distance_map: @@distances});
 PRINT matches, @@distances AS distances;
}
INSTALL QUERY HHG_MemorySearch
'''

async def main():
    async with TigerGraphMCP() as m:
        print((await m.call('gsql',command=QUERY))['result'],flush=True)

if __name__=='__main__':asyncio.run(main())
