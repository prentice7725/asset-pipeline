"""MCP/API inspection of runs whose CLI provider saved the original image outside configured roots."""
import json
from pathlib import Path

import pytest

from assetpipe.api import inspect_manifest
from assetpipe.paths import RootResolver


def codex_run(root, outside):
    """Shape of a real codex_imagegen run (merc-guild 194c4c1b...): delivered output in the run,
    Codex's own copy under ~/.codex/generated_images recorded as provider provenance."""
    run = root / 'merc-guild/runs/merc-ash-angry/194c4c1b12fc424c9997c7fc0f6f6f05'
    raw = run / '010_generation/codex_cli/raw/exec-1.png'
    portrait = run / '020_delivery/0/portrait.png'
    manifest = {
        'schema_version': 1, 'asset_id': 'merc-ash-angry', 'output_class': 'NONPIXEL_IMAGE',
        'status': 'CANDIDATE_READY_REVIEW_REQUIRED', 'game_ready': False, 'delivery_ready': False,
        'workflow': {'id': 'codex_imagegen'}, 'qa_results': [{'step': 'basic_image_qa', 'status': 'PASS', 'path': str(portrait)}],
        'outputs': [str(portrait)],
        'generation': {'raw_outputs': [str(raw)], 'provider': {
            'provider_id': 'codex_imagegen', 'engine': 'codex_cli', 'status': 'COMPLETED',
            'outputs': [{'path': str(raw), 'sha256': '0' * 64, 'source_path': outside}]}},
    }
    run.mkdir(parents=True)
    path = run / 'run_manifest.json'
    path.write_text(json.dumps(manifest), encoding='utf-8')
    return path, manifest


@pytest.fixture
def roots(tmp_path):
    root = tmp_path / 'plugin_runs'
    root.mkdir()
    outside = str(tmp_path / 'home/.codex/generated_images/01a1/exec-37944b65.png')
    return root, RootResolver([root], base=root), outside


def test_inspect_reads_codex_run_with_external_source_and_keeps_review_gate(roots):
    root, resolver, outside = roots
    path, _ = codex_run(root, outside)
    result = inspect_manifest(path, resolver)
    assert result['status'] == 'REVIEW_REQUIRED'
    assert result['review_items'] == ['CANDIDATE_READY_REVIEW_REQUIRED']
    assert result['game_ready'] is False
    assert result['outputs'][0].endswith('portrait.png')
    # The manifest on disk is not rewritten; provenance stays as recorded.
    assert json.loads(path.read_text(encoding='utf-8'))['generation']['provider']['outputs'][0]['source_path'] == outside


@pytest.mark.parametrize('break_it', [
    lambda m, o: m['outputs'].append(o),
    lambda m, o: m['generation']['provider']['outputs'][0].update(path=o),
    lambda m, o: m['qa_results'][0].update(path=o),
    lambda m, o: m.update(source_manifest=o),
])
def test_inspect_still_rejects_every_other_outside_reference(roots, break_it):
    root, resolver, outside = roots
    path, manifest = codex_run(root, outside)
    break_it(manifest, outside)
    path.write_text(json.dumps(manifest), encoding='utf-8')
    with pytest.raises(ValueError, match='outside configured roots'):
        inspect_manifest(path, resolver)


def test_factory_and_inspect_share_one_exemption():
    from assetpipe.factory import provenance
    from assetpipe import paths
    assert provenance.validate_run_manifest is paths.validate_run_manifest


def test_mcp_adapter_inspect_returns_review_state_for_codex_run(tmp_path):
    """End to end through the MCP adapter, which is what hf-game-studio calls."""
    from integrations.mcp.tools.adapter import Adapter
    core = Path(__file__).resolve().parents[2]
    source = tmp_path / 'sources'
    source.mkdir()
    output = tmp_path / 'plugin_runs'
    config = tmp_path / 'adapter.yaml'
    config.write_text(f'core_root: {core.as_posix()}\nsource_roots:\n- {source.as_posix()}\noutput_root: {output.as_posix()}\n',
                      encoding='utf-8')
    adapter = Adapter(config)
    outside = str(tmp_path / 'home/.codex/generated_images/01a1/exec-37944b65.png')
    path, manifest = codex_run(output, outside)
    run_id = '194c4c1b12fc424c9997c7fc0f6f6f05'
    requests = output / 'merc-guild/requests'
    requests.mkdir(parents=True)
    (requests / f'{run_id}.json').write_text(json.dumps({'run_id': run_id, 'project_id': 'merc-guild', 'status': 'STARTING',
                                                        'manifest': str(path)}), encoding='utf-8')
    result = adapter.inspect(run_id)
    assert result['status'] == 'REVIEW_REQUIRED' and result['game_ready'] is False
    assert result['project_id'] == 'merc-guild'
    assert Path(result['outputs'][0]).name == 'portrait.png'
