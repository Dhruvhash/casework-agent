"""Official TigerGraph MCP over stdio, with bounded calls and an audit trace."""
import asyncio
import json
import os
import shutil
import sys
import certifi
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv
from .llm import ROOT


class TigerGraphMCP:
    async def __aenter__(self):
        load_dotenv(ROOT / '.env')
        env = dict(os.environ)
        for name in list(env):
            if name.upper() in {'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY'}:
                del env[name]
        env.update(TG_RESTPP_PORT='443', TG_GS_PORT='443', TG_TGCLOUD='true', TG_CERT_PATH=certifi.where())
        self.stack = AsyncExitStack()
        command = shutil.which('tigergraph-mcp')
        if not command:
            raise RuntimeError('Install requirements.txt: official tigergraph-mcp is missing')
        streams = await self.stack.enter_async_context(stdio_client(StdioServerParameters(command=sys.executable, args=['-m', 'tigergraph_mcp.main', '--transport', 'stdio'], env=env)))
        self.session = await self.stack.enter_async_context(ClientSession(*streams))
        await asyncio.wait_for(self.session.initialize(), 30)
        self.trace = []
        return self

    async def __aexit__(self, *args):
        await self.stack.aclose()

    async def call(self, tool, **arguments):
        result = await asyncio.wait_for(self.session.call_tool('tigergraph__' + tool, arguments=arguments), 180)
        contents = list(result.content)
        for content in contents:
            if getattr(content, 'type', '') == 'text':
                try:
                    raw = content.text
                    if raw.startswith('```json\n'):
                        # Documents can themselves contain Markdown code fences.
                        # Decode the first JSON value instead of splitting on ```.
                        body = json.JSONDecoder().raw_decode(raw[len('```json\n'):].lstrip())[0]
                    else:
                        body = json.loads(raw)
                except ValueError:
                    continue
                if isinstance(body, list):
                    from mcp.types import TextContent
                    contents.extend(TextContent(type='text', text=x['text']) for x in body if isinstance(x, dict) and 'text' in x)
                if isinstance(body, dict) and 'success' in body:
                    self.trace.append({'tool': tool, 'success': body['success']})
                    if not body['success']:
                        raise RuntimeError(f"MCP {tool}: {body.get('error', body.get('summary'))}")
                    return body['data']
        message = ' '.join(getattr(c,'text','') for c in result.content)[:1200]
        for key in ('TG_SECRET','TG_API_TOKEN','OPENAI_API_KEY'):
            if os.getenv(key): message=message.replace(os.getenv(key),'[redacted]')
        raise RuntimeError(f'MCP {tool} returned no structured success response: '+message)


async def probe():
    print('Opening official MCP connection', flush=True)
    async with TigerGraphMCP() as client:
        print('MCP handshake OK', flush=True)
        tools = await asyncio.wait_for(client.session.list_tools(), 20)
        print(len(tools.tools), 'tools', flush=True)
        result = await client.call('run_query', query_text='INTERPRET QUERY () FOR GRAPH FraudInvestigation { PRINT "ready" AS status; }')
        print(json.dumps(result))


if __name__ == '__main__':
    asyncio.run(probe())
