import asyncio
import os
import certifi
from dotenv import load_dotenv
from pyTigerGraph import AsyncTigerGraphConnection


async def main():
    load_dotenv()
    c = AsyncTigerGraphConnection(host=os.getenv('TG_HOST'), graphname=os.getenv('TG_GRAPHNAME'),
        gsqlSecret=os.getenv('TG_SECRET'), restppPort=443, gsPort=443, certPath=certifi.where(), version='4.2.5')
    print('SDK created', flush=True)
    try:
        result = await asyncio.wait_for(c.runInterpretedQuery('INTERPRET QUERY () FOR GRAPH FraudInvestigation { PRINT 1; }'), 20)
        print(result, flush=True)
    finally:
        await c.aclose()


if __name__ == '__main__':
    asyncio.run(main())
