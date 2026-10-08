import asyncio
import json
from pathlib import Path
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

home = Path(__file__).resolve().parent

async def main():
    report = {'generation_calls': 0}
    params = StdioServerParameters(command=sys.executable, args=[str(home / 'launch.py')], cwd='C:/workspace/isekai')
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            report['server'] = init.serverInfo.model_dump()
            names = sorted(t.name for t in (await session.list_tools()).tools)
            assert names == sorted(['asset_capabilities', 'asset_build_brief', 'asset_route', 'asset_generate', 'asset_continue_animation', 'asset_inspect_run'])
            report['tools'] = names
            async def call(name, args):
                result = await session.call_tool(name, args)
                assert not result.isError, result
                return result.structuredContent or json.loads(result.content[0].text)
            brief = await call('asset_build_brief', {
                'request_text': 'Read-only MCP setup verification. No generation.',
                'requested_output_type': 'NONPIXEL_IMAGE',
                'asset_id': 'mcp_setup_check',
                'reference_image': 'C:/workspace/isekai/public/assets/golden-sample/PORTRAIT_app_0001_nakamura_neutral_v05.png',
            })
            report['brief'] = brief
            report['route'] = await call('asset_route', {'brief': brief['brief']})
            plain = await call('asset_build_brief', {'request_text': 'Read-only style routing verification', 'requested_output_type': 'NONPIXEL_IMAGE', 'workflow_id': 'krea2_base'})
            report['direct_route'] = await call('asset_route', {'brief': plain['brief']})
            assert report['direct_route']['selected_workflow'] == 'krea2_base'
            report['capabilities'] = await call('asset_capabilities', {})
    (home / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'handshake': 'PASS', 'tools': names, 'reference_access': 'PASS', 'reference_gate': report['route']['status'], 'direct_route': report['direct_route'], 'generation_calls': 0}, ensure_ascii=False))

asyncio.run(main())
