"""Repository custom-node preflight and installer; no ComfyUI or torch needed."""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from assetpipe.providers.comfyui import custom_nodes

ROOT = Path(__file__).resolve().parents[2]
NODE = 'AssetpipeAIToolkitDoRALoader'
SOURCE = 'integrations/comfyui_dora/__init__.py'
EXPECTED = hashlib.sha256((ROOT / SOURCE).read_bytes()).hexdigest()
DECLARED = [{'class': NODE, 'source': SOURCE}]


def _fetch(description=None, missing=False, error=None):
    def fetch(path):
        assert path == '/object_info/' + NODE
        if error:
            raise error
        return {} if missing else {NODE: {'description': description}}
    return fetch


def test_loaded_node_matching_repository_passes():
    assert custom_nodes.check(_fetch(f'EXPERIMENTAL ... source_sha256={EXPECTED}'), ROOT, DECLARED) == []


@pytest.mark.parametrize('fetch, code', [
    (_fetch(missing=True), 'COMFYUI_CUSTOM_NODE_MISSING'),
    (_fetch('source_sha256=' + '0' * 64), 'COMFYUI_CUSTOM_NODE_STALE'),
    (_fetch('old node without a hash'), 'COMFYUI_CUSTOM_NODE_STALE'),
    (_fetch(error=OSError('refused')), 'COMFYUI_CUSTOM_NODE_QUERY_FAILED'),
])
def test_missing_stale_or_unreachable_node_is_reported(fetch, code):
    assert custom_nodes.check(fetch, ROOT, DECLARED)[0]['code'] == code


def test_require_blocks_krea2_pixel64_and_ignores_graphs_without_declarations():
    assert custom_nodes.requirements(ROOT, 'krea2_pixel64_api') == DECLARED
    assert custom_nodes.requirements(ROOT, 'krea2_pixel64_stock_api') == []
    with pytest.raises(RuntimeError, match='COMFYUI_CUSTOM_NODE_MISSING'):
        custom_nodes.require(_fetch(missing=True), ROOT, 'krea2_pixel64_api')
    custom_nodes.require(_fetch(missing=True), ROOT, 'krea2_pixel64_stock_api')


def test_source_outside_repository_is_rejected(tmp_path):
    problems = custom_nodes.check(_fetch(missing=True), ROOT, [{'class': NODE, 'source': '../outside.py'}])
    assert problems[0]['code'] == 'COMFYUI_CUSTOM_NODE_SOURCE_MISSING'


def test_node_publishes_hash_of_its_own_source():
    from integrations import comfyui_dora
    assert comfyui_dora.SOURCE_SHA256 == EXPECTED
    assert f'source_sha256={EXPECTED}' in comfyui_dora.AssetpipeAIToolkitDoRALoader.DESCRIPTION


def test_generate_checks_nodes_before_submitting(monkeypatch, tmp_path):
    from assetpipe.providers import comfyui
    import assetpipe.prompts as prompts
    calls = []
    monkeypatch.setattr(prompts, 'compile_prompt', lambda *a: {'positive': 'p', 'negative': ''})
    monkeypatch.setattr(prompts, 'workflow_values', lambda *a: {})
    monkeypatch.setattr(custom_nodes, 'require', lambda fetch, root, name: calls.append(('require', name)) or
                        (_ for _ in ()).throw(RuntimeError('COMFYUI_CUSTOM_NODE_STALE')))
    monkeypatch.setattr(comfyui, 'run_workflow', lambda *a, **k: calls.append('submitted'))

    class Config:
        root = ROOT

        def section(self, name):
            return {}

    brief = {'source': {'type': 'TEXT', 'paths': []}, 'asset_id': 'x'}
    with pytest.raises(RuntimeError, match='STALE'):
        comfyui.ComfyUIProvider(Config()).generate(brief, {'workflow_name': 'krea2_pixel64_api'}, tmp_path, 1)
    assert calls == [('require', 'krea2_pixel64_api')]


def _installer():
    spec = importlib.util.spec_from_file_location('install_comfyui_dora', ROOT / 'scripts/install_comfyui_dora.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_installer_copies_bytes_and_refuses_silent_overwrite(tmp_path):
    installer = _installer()
    (tmp_path / 'custom_nodes').mkdir()
    assert installer.install(tmp_path, update=False)['install'] == 'INSTALLED'
    target = tmp_path / 'custom_nodes/assetpipe_aitoolkit_dora/__init__.py'
    assert target.read_bytes() == (ROOT / SOURCE).read_bytes()
    assert installer.install(tmp_path, update=False)['install'] == 'UP_TO_DATE'
    target.write_text('old', encoding='utf-8')
    with pytest.raises(SystemExit, match='DIFFERS'):
        installer.install(tmp_path, update=False)
    result = installer.install(tmp_path, update=True)
    assert result['install'] == 'UPDATED' and Path(result['backup']).read_text(encoding='utf-8') == 'old'
    assert target.read_bytes() == (ROOT / SOURCE).read_bytes()
    with pytest.raises(SystemExit, match='CUSTOM_NODES_NOT_FOUND'):
        installer.install(tmp_path / 'nope', update=False)
    json.dumps(result)
