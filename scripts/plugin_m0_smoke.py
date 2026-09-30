"""Exactly four M0 smokes through a real MCP stdio client/server session."""
import asyncio
import hashlib
import json
from pathlib import Path
import sys
import time
import yaml
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from PIL import Image
from assetpipe.brief import load
from assetpipe.registry import load_registry
from assetpipe.manifests import write

ROOT = Path(__file__).resolve().parents[1]

async def main():
    directory = ROOT / 'workspace/plugin_m0' / str(int(time.time()))
    directory.mkdir(parents=True, exist_ok=False)
    legacy = ROOT.parent / 'pixel-pipeline'
    config = directory / 'config.yaml'
    config.write_text(yaml.safe_dump({'core_root': str(ROOT), 'source_roots': [str(ROOT / 'examples'), str(ROOT / 'tests/fixtures'), str(legacy / 'workspace/runs/sword_warrior_001')], 'output_root': str(directory / 'runs')}), encoding='utf-8')
    parameters = StdioServerParameters(command=sys.executable, args=['-m', 'integrations.mcp.server', '--config', str(config)], cwd=str(ROOT))
    evidence = {'smokes': {}, 'package_gate': 'MCP_SMOKES_ONLY'}
    async with stdio_client(parameters) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            tools = (await session.list_tools()).tools
            assert len(tools) == 6
            schemas = ROOT / 'integrations/mcp/schemas'
            schemas.mkdir(parents=True, exist_ok=True)
            for tool in tools:
                write(schemas / f'{tool.name}.json', tool.inputSchema)
            async def call(name, arguments):
                result = await session.call_tool(name, arguments)
                if result.isError:
                    raise RuntimeError(str(result.content))
                return result.structuredContent or json.loads(result.content[0].text)
            async def finish(run):
                assert run['run_id'], run
                for _ in range(900):
                    result = await call('asset_inspect_run', {'run_id': run['run_id']})
                    if result['status'] not in {'STARTING', 'RUNNING'}:
                        assert result['status'] == 'REVIEW_REQUIRED', result
                        return result
                    await asyncio.sleep(2)
                raise TimeoutError(run['run_id'])

            # A: exact registry-backed capabilities and actual readiness.
            caps = await call('asset_capabilities', {})
            assert set(caps['active_workflows']) == {k for k, v in load_registry(ROOT).items() if v['status'] == 'ACTIVE'}
            assert all(v['ready'] for v in caps['environment_readiness'].values())
            evidence['smokes']['A'] = {'status': 'PASS', 'result': caps}
            print('Smoke A PASS', flush=True)

            # B: one ACTIVE nonpixel generation, no quality competition.
            built = await call('asset_build_brief', {'request_text': 'fantasy scout, short brown hair, blue cloak, light armor, dagger, white background', 'requested_output_type': 'NONPIXEL_IMAGE', 'asset_id': 'plugin_nonpixel_smoke', 'workflow_id': 'anima_base'})
            brief = built['brief']
            brief['workflow_preferences']['preset'] = 'smoke'
            decision = await call('asset_route', {'brief': brief})
            assert decision['status'] == 'ROUTED'
            nonpixel = await finish(await call('asset_generate', {'brief': brief, 'seed': 20260930}))
            evidence['smokes']['B'] = {'status': 'PASS', 'result': nonpixel}
            print('Smoke B PASS', flush=True)

            # C: existing approved fixture + motion through continuation; no new motion.
            pixel = await finish(await call('asset_continue_animation', {'asset_reference': 'examples/pixel_animation_smoke.yaml', 'action': 'walk', 'output_class': 'PIXEL_ANIMATION'}))
            reference = legacy / 'workspace/runs/sword_warrior_001/phase13_step3_direct_walk/attempt_05/040_direct_pixel_frames'
            paths = [Path(p) for p in pixel['outputs'] if Path(p).parent.name == '040_direct_pixel_frames']
            assert len(paths) == 8
            exact = []
            for path in paths:
                with Image.open(path) as a, Image.open(reference / path.name) as b:
                    assert a.convert('RGBA').tobytes() == b.convert('RGBA').tobytes()
                exact.append({'frame': path.name, 'exact_rgba_match': True, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
            evidence['smokes']['C'] = {'status': 'PASS', 'result': pixel, 'regression': exact}
            print('Smoke C PASS: 8/8 exact RGBA', flush=True)

            # D: source-extracted prepared document brief; routing only.
            prepared = load(ROOT / 'examples/character_test_brief.yaml')
            built = await call('asset_build_brief', {'request_text': 'Create the scout described in the fixture design document', 'requested_output_type': 'NONPIXEL_IMAGE', 'source_document_paths': ['tests/fixtures/character_test.md'], 'prepared_brief': prepared})
            decision = await call('asset_route', {'brief': built['brief']})
            assert decision['status'] == 'ROUTED' and decision['selected_workflow'] == 'anima_base'
            evidence['smokes']['D'] = {'status': 'PASS', 'brief': built['brief'], 'route': decision}
            print('Smoke D PASS', flush=True)
    write(directory / 'smoke_report.json', evidence)
    write(ROOT / 'workspace/plugin_m0/latest.json', {'report': str(directory / 'smoke_report.json')})
    print(directory / 'smoke_report.json')

if __name__ == '__main__':
    asyncio.run(main())
