"""Krea2 Pixel64 registry entry and static pipeline intermediate handling; no generation."""
import hashlib
from pathlib import Path

import pytest
from PIL import Image

from assetpipe._ported.comfy_bridge.runner import patch_workflow
from assetpipe._ported.comfy_bridge.workflow_loader import load_workflow
from assetpipe.pipelines import pixel_static
from assetpipe.registry import load_registry

ROOT = Path(__file__).resolve().parents[2]


def test_entry_is_validated_explicit_only_pixel_static():
    entry = load_registry(ROOT)['krea2_pixel64']
    assert entry['status'] == 'VALIDATED' and entry['selection'] == 'explicit_only'
    assert entry['output_class'] == 'PIXEL_STATIC' and entry['preserved_intermediate_outputs'] == 1


def test_logical_size_binds_to_refiner_not_latent():
    workflow = load_workflow('krea2_pixel64_api', ROOT / 'config/workflows')
    graph = patch_workflow(workflow, prompt='archer', seed=5, filename_prefix='assetpipe/x',
                           workflow_inputs={'width': 64, 'height': 64, 'colors': 24, 'lora_strength': 1.0})
    assert (graph['30']['inputs']['width'], graph['30']['inputs']['height']) == (64, 64)
    assert (graph['5']['inputs']['width'], graph['5']['inputs']['height']) == (1024, 1024)
    assert graph['15']['inputs']['lora_name'] == 'k2-pixel64.safetensors'
    assert workflow.output_nodes == ('9', '31')


def test_default_graph_uses_dora_node_and_stock_graph_is_kept_unchanged():
    registry = load_registry(ROOT)
    assert registry['krea2_pixel64_stock']['status'] == 'EXPERIMENTAL'
    assert registry['krea2_pixel64_stock']['selection'] == 'explicit_only'
    dora = patch_workflow(load_workflow('krea2_pixel64_api', ROOT / 'config/workflows'), prompt='a', seed=1,
                          filename_prefix='assetpipe/x', workflow_inputs={'lora_strength': 0.5})
    assert dora['15']['class_type'] == 'AssetpipeAIToolkitDoRALoader'
    assert dora['15']['inputs']['strength'] == 0.5 and dora['15']['inputs']['alpha_over_rank'] == 1.0
    stock_path = ROOT / 'config/workflows/krea2_pixel64_stock_api.json'
    # Identical bytes to the graph used by the 2026-11-07 batch runs (their recorded workflow_sha256).
    assert hashlib.sha256(stock_path.read_bytes()).hexdigest().startswith('1ea5ee227549f34e')
    stock = patch_workflow(load_workflow('krea2_pixel64_stock_api', ROOT / 'config/workflows'), prompt='a', seed=1,
                           filename_prefix='assetpipe/x', workflow_inputs={'lora_strength': 1.0})
    assert stock['15']['class_type'] == 'LoraLoaderModelOnly'


def _fake(monkeypatch, paths):
    seen = {}
    monkeypatch.setattr(pixel_static.ComfyUIProvider, 'generate', lambda self, *a: paths)
    monkeypatch.setattr(pixel_static, 'process_candidate',
                        lambda candidate, *a, **k: seen.update(candidate=candidate, kwargs=k) or a[-1])
    return seen


def test_declared_intermediate_is_hashed_and_last_output_is_the_candidate(monkeypatch, tmp_path):
    raw, refined = tmp_path / 'raw.png', tmp_path / 'refined.png'
    Image.new('RGB', (8, 8)).save(raw)
    Image.new('RGB', (4, 4)).save(refined)
    seen = _fake(monkeypatch, [raw, refined])
    manifest = {'pipeline_steps': []}
    pixel_static.run({}, {'preserved_intermediate_outputs': 1}, None, tmp_path, manifest, 1)
    assert seen['candidate'] == refined and seen['kwargs'] == {'transparent': None}
    step = manifest['pipeline_steps'][0]
    assert step['outputs'] == [{'path': str(raw), 'sha256': hashlib.sha256(raw.read_bytes()).hexdigest()}]


@pytest.mark.parametrize('declared, count', [(0, 2), (1, 1), (1, 3)])
def test_output_count_must_match_declaration(monkeypatch, tmp_path, declared, count):
    _fake(monkeypatch, [tmp_path / f'{i}.png' for i in range(count)])
    with pytest.raises(ValueError, match='expects one image candidate'):
        pixel_static.run({}, {'preserved_intermediate_outputs': declared}, None, tmp_path, {'pipeline_steps': []}, 1)


def test_registry_declares_transparent_delivery_and_run_passes_it(monkeypatch, tmp_path):
    registry = load_registry(ROOT)
    for key in ('krea2_pixel64', 'krea2_pixel64_stock'):
        assert registry[key]['transparent_delivery'] == {'background_rgb': [255, 255, 255], 'tolerance': 10}
    raw, refined = tmp_path / 'raw.png', tmp_path / 'refined.png'
    Image.new('RGB', (8, 8)).save(raw)
    Image.new('RGB', (4, 4)).save(refined)
    seen = _fake(monkeypatch, [raw, refined])
    pixel_static.run({}, registry['krea2_pixel64'], None, tmp_path, {'pipeline_steps': []}, 1)
    assert seen['kwargs'] == {'transparent': {'background_rgb': [255, 255, 255], 'tolerance': 10}}


class _FakeAseprite:
    calls = []

    def __init__(self, config):
        pass

    def export(self, images, directory, name):
        self.calls.append((list(images), directory, name))
        return {'status': 'PASS', 'master': str(directory / 'master.aseprite')}


def _sprite(tmp_path, bars=False):
    image = Image.new('RGB', (64, 64), (252, 252, 252))
    for x in range(20, 44):
        for y in range(10, 54):
            image.putpixel((x, y), (40, 60, 120))
    if bars:
        for x in list(range(0, 9)) + list(range(55, 64)):
            for y in range(64):
                image.putpixel((x, y), (0, 0, 0))
    path = tmp_path / 'quantized.png'
    image.save(path)
    return path


SETTINGS = {'background_rgb': [255, 255, 255], 'tolerance': 10}


def test_transparent_delivery_writes_copy_and_aseprite_round_trip(monkeypatch, tmp_path):
    import assetpipe.providers.aseprite as aseprite
    monkeypatch.setattr(aseprite, 'AsepriteProvider', _FakeAseprite)
    manifest = {'pipeline_steps': [], 'asset_id': 'knight'}
    pixel_static.transparent_delivery(_sprite(tmp_path), SETTINGS, None, tmp_path, manifest, [64, 64])
    out = Image.open(tmp_path / '070_transparent/transparent.png').convert('RGBA')
    assert out.getpixel((0, 0))[3] == 0 and out.getpixel((30, 30)) == (40, 60, 120, 255)
    assert manifest['transparent_delivery']['status'] == 'PASS_REVIEW_REQUIRED'
    assert manifest['transparent_delivery']['aseprite_roundtrip'] == 'PASS'
    assert manifest['pipeline_steps'][-1]['step'] == 'transparent_delivery'
    assert (tmp_path / '070_transparent/aseprite_roundtrip.json').is_file()


def test_generated_side_bars_block_delivery_without_failing_the_run(monkeypatch, tmp_path):
    import assetpipe.providers.aseprite as aseprite
    _FakeAseprite.calls = []
    monkeypatch.setattr(aseprite, 'AsepriteProvider', _FakeAseprite)
    manifest = {'pipeline_steps': [], 'asset_id': 'knight', 'status': 'RESOLUTION_REVIEW_REQUIRED'}
    pixel_static.transparent_delivery(_sprite(tmp_path, bars=True), SETTINGS, None, tmp_path, manifest, [64, 64])
    assert manifest['transparent_delivery']['status'] == 'BLOCKED_REVIEW_REQUIRED'
    assert 'BORDER_NOT_UNIFORM' in manifest['transparent_delivery']['reason']
    assert manifest['status'] == 'RESOLUTION_REVIEW_REQUIRED' and _FakeAseprite.calls == []
