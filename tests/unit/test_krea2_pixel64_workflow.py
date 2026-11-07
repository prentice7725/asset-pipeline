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


def test_entry_is_experimental_explicit_only_pixel_static():
    entry = load_registry(ROOT)['krea2_pixel64']
    assert entry['status'] == 'EXPERIMENTAL' and entry['selection'] == 'explicit_only'
    assert entry['output_class'] == 'PIXEL_STATIC' and entry['preserved_intermediate_outputs'] == 1


def test_logical_size_binds_to_refiner_not_latent():
    workflow = load_workflow('krea2_pixel64_api', ROOT / 'config/workflows')
    graph = patch_workflow(workflow, prompt='archer', seed=5, filename_prefix='assetpipe/x',
                           workflow_inputs={'width': 64, 'height': 64, 'colors': 24, 'lora_strength': 1.0})
    assert (graph['30']['inputs']['width'], graph['30']['inputs']['height']) == (64, 64)
    assert (graph['5']['inputs']['width'], graph['5']['inputs']['height']) == (1024, 1024)
    assert graph['15']['inputs']['lora_name'] == 'k2-pixel64.safetensors'
    assert workflow.output_nodes == ('9', '31')


def _fake(monkeypatch, paths):
    seen = {}
    monkeypatch.setattr(pixel_static.ComfyUIProvider, 'generate', lambda self, *a: paths)
    monkeypatch.setattr(pixel_static, 'process_candidate',
                        lambda candidate, *a: seen.setdefault('candidate', candidate) and a[-1])
    return seen


def test_declared_intermediate_is_hashed_and_last_output_is_the_candidate(monkeypatch, tmp_path):
    raw, refined = tmp_path / 'raw.png', tmp_path / 'refined.png'
    Image.new('RGB', (8, 8)).save(raw)
    Image.new('RGB', (4, 4)).save(refined)
    seen = _fake(monkeypatch, [raw, refined])
    manifest = {'pipeline_steps': []}
    pixel_static.run({}, {'preserved_intermediate_outputs': 1}, None, tmp_path, manifest, 1)
    assert seen['candidate'] == refined
    step = manifest['pipeline_steps'][0]
    assert step['outputs'] == [{'path': str(raw), 'sha256': hashlib.sha256(raw.read_bytes()).hexdigest()}]


@pytest.mark.parametrize('declared, count', [(0, 2), (1, 1), (1, 3)])
def test_output_count_must_match_declaration(monkeypatch, tmp_path, declared, count):
    _fake(monkeypatch, [tmp_path / f'{i}.png' for i in range(count)])
    with pytest.raises(ValueError, match='expects one image candidate'):
        pixel_static.run({}, {'preserved_intermediate_outputs': declared}, None, tmp_path, {'pipeline_steps': []}, 1)
