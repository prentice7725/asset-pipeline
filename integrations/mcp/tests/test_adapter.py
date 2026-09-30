import asyncio
import copy
import json
from pathlib import Path
import subprocess
import pytest
import yaml
from assetpipe import api
from assetpipe.brief import make, load
from integrations.mcp.tools.adapter import Adapter
from integrations.mcp.server import create_server

ROOT = Path(__file__).resolve().parents[3]

@pytest.fixture
def adapter(tmp_path):
    config = tmp_path / 'adapter.yaml'
    config.write_text(yaml.safe_dump({'core_root': str(ROOT), 'source_roots': [str(ROOT / 'examples'), str(ROOT / 'tests/fixtures')], 'output_root': str(tmp_path / 'outputs')}))
    return Adapter(config)

def brief():
    return make(asset_id='test', output_class='NONPIXEL_IMAGE', prompt='fantasy scout')

def test_capabilities_delegate_to_core(adapter, monkeypatch):
    monkeypatch.setattr(api, 'capabilities', lambda root: {'same_registry': str(root)})
    assert adapter.capabilities() == {'same_registry': str(ROOT)}

def test_path_rejection_includes_traversal_and_file_references(adapter, tmp_path):
    outside = tmp_path / 'private.json'
    outside.write_text('{}')
    with pytest.raises(ValueError, match='outside'):
        adapter.source(str(outside))
    value = brief()
    value['production'] = {'static_master': str(outside)}
    with pytest.raises(ValueError, match='outside'):
        adapter.route(value)
    with pytest.raises(ValueError):
        adapter.inspect('../../private')
    with pytest.raises(ValueError):
        adapter.generate(brief_file=str(outside))

def test_schema_and_tool_exclusivity(adapter):
    with pytest.raises(ValueError):
        adapter.route({'asset_id': 'x'})
    with pytest.raises(ValueError):
        adapter.generate()
    with pytest.raises(ValueError):
        adapter.generate(brief=brief(), seed=-1)
    with pytest.raises(ValueError):
        adapter.generate(brief=brief(), seed=True)

def test_unknown_workflow_and_explicit_override(adapter):
    value = brief()
    value['workflow_preferences']['id'] = 'unknown'
    assert adapter.route(value)['status'] == 'BLOCKED'
    value['workflow_preferences']['id'] = 'anima_base'
    result = adapter.route(value)
    assert result['selected_workflow'] == 'anima_base'
    assert {'selected_pipeline', 'selected_workflow', 'reason', 'required_capabilities', 'missing_requirements', 'fallback_candidates'} <= result.keys()

def test_experimental_never_auto_selected(adapter):
    value = brief()
    assert adapter.route(value)['selected_workflow'] != 'tomohi_character'
    value['workflow_preferences']['id'] = 'tomohi_character'
    assert adapter.route(value)['status'] == 'BLOCKED'

def test_missing_approved_master_blocks_launch(adapter, monkeypatch):
    value = make(asset_id='walk', output_class='PIXEL_ANIMATION', prompt='walk', action='walk')
    value['workflow_preferences']['id'] = 'minimax_character_motion_reference'
    monkeypatch.setattr(subprocess, 'Popen', lambda *a, **k: pytest.fail('must not launch'))
    result = adapter.generate(brief=value)
    assert result['status'] == 'BLOCKED'
    assert result['run_id'] is None

def test_document_builder_does_not_invent_canon(adapter):
    result = adapter.build_brief(request_text='Create the protagonist', output_class='NONPIXEL_IMAGE', source_documents=['tests/fixtures/character_test.md'])
    assert result['brief']['identity']['canonical_traits'] == []
    assert result['brief']['source_notes'][0]['classification'] == 'UNSPECIFIED'
    assert adapter.route(result['brief'])['status'] == 'BLOCKED'

def test_optional_output_type_is_never_guessed(adapter):
    result = adapter.build_brief(request_text='Create a character', output_class=None)
    assert result['status'] == 'BLOCKED' and result['brief'] is None

def test_launch_uses_only_fixed_cli_and_manifest_model(adapter, monkeypatch):
    calls = []
    class Child:
        pid = 123
    def popen(args, **kwargs):
        calls.append((args, kwargs))
        return Child()
    monkeypatch.setattr(subprocess, 'Popen', popen)
    result = adapter.generate(brief=brief(), seed=5)
    assert len(result['run_id']) == 32
    assert calls[0][0][1:3] == ['-m', 'assetpipe']
    assert calls[0][1]['shell'] is False
    assert adapter.inspect(result['run_id'])['status'] == 'STARTING'


def test_projects_partition_runs_requests_and_inspection(adapter, monkeypatch):
    class Child:
        pid = 123
    monkeypatch.setattr(subprocess, 'Popen', lambda *args, **kwargs: Child())
    for project in ('game-a', 'game-b'):
        value = brief()
        value['project_id'] = project
        result = adapter.generate(brief=value)
        assert Path(result['manifest']).relative_to(adapter.output).parts == (project, 'runs', 'test', result['run_id'], 'run_manifest.json')
        receipt = adapter.output / project / 'requests' / (result['run_id'] + '.json')
        assert receipt.is_file()
        assert adapter.inspect(result['run_id'])['project_id'] == project
        assert json.loads(receipt.read_text())['project_id'] == project
    assert not (adapter.output / 'requests').exists()


@pytest.mark.parametrize('project', ['../escape', 'a/b', 'a\\b', 'C:escape', 'CON', 'NUL', 'game.', '', 'a' * 65])
def test_invalid_project_cannot_launch(adapter, monkeypatch, project):
    monkeypatch.setattr(subprocess, 'Popen', lambda *args, **kwargs: pytest.fail('Invalid project must not launch'))
    value = brief()
    value['project_id'] = project
    with pytest.raises(ValueError):
        adapter.generate(brief=value)


def test_builder_records_explicit_project(adapter):
    result = adapter.build_brief(request_text='scout', output_class='NONPIXEL_IMAGE', project_id='game-a')
    assert result['brief']['project_id'] == 'game-a'

def test_read_only_inspection_preserves_review_state_and_blocks_output_escape(adapter):
    result = adapter.generate
    run_id = 'a' * 32
    manifest_path = adapter.output / 'runs/test' / run_id / 'run_manifest.json'
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(json.dumps({'status': 'EXPORT_READY_REVIEW_REQUIRED', 'asset_id': 'test', 'output_class': 'PIXEL_STATIC', 'outputs': [], 'qa_results': []}))
    receipt = adapter.output / 'requests' / f'{run_id}.json'
    receipt.parent.mkdir()
    receipt.write_text(json.dumps({'manifest': str(manifest_path)}))
    before = manifest_path.read_bytes()
    assert adapter.inspect(run_id)['status'] == 'REVIEW_REQUIRED'
    assert manifest_path.read_bytes() == before
    document = json.loads(before)
    document['outputs'] = [str(ROOT / 'README.md')]
    manifest_path.write_text(json.dumps(document))
    with pytest.raises(ValueError, match='outside'):
        adapter.inspect(run_id)

def test_six_tools_and_strict_arguments(adapter):
    config = adapter.output.parent / 'adapter.yaml'
    server = create_server(config)
    tools = asyncio.run(server.list_tools())
    assert {tool.name for tool in tools} == {'asset_capabilities', 'asset_build_brief', 'asset_route', 'asset_generate', 'asset_continue_animation', 'asset_inspect_run'}
    assert all(tool.inputSchema['additionalProperties'] is False for tool in tools)
    with pytest.raises(Exception):
        asyncio.run(server.call_tool('asset_generate', {'command': 'arbitrary shell'}))
    with pytest.raises(Exception):
        asyncio.run(server.call_tool('asset_inspect_run', {'run_id': 3}))

def test_unsupported_animation_constraints_are_rejected(adapter):
    with pytest.raises(ValueError):
        adapter.continue_animation('examples/character_test_brief.yaml', 'walk', 'PIXEL_ANIMATION', {'executable': 'cmd.exe'})
