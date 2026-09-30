import json
from pathlib import Path
from PIL import Image
import pytest
from assetpipe.brief import make
from assetpipe.pipelines import create
from assetpipe.providers.comfyui import ComfyUIProvider
from assetpipe.pipelines.pixel_static import export_reviewed
from assetpipe._ported.config import load_config
from assetpipe._ported.pixel_gate.resolution import record_resolution_review
from assetpipe._ported.aseprite_bridge.runner import find_aseprite

ROOT = Path(__file__).resolve().parents[2]

def test_static_fixture_reaches_review_then_real_aseprite(monkeypatch, tmp_path):
    if not find_aseprite():
        pytest.skip('Real Aseprite unavailable')
    source = ROOT / 'tests/assets/true_pixel_art.png'
    monkeypatch.setattr(ComfyUIProvider, 'generate', lambda *args: [source])
    brief = make(asset_id='static_fixture', output_class='PIXEL_STATIC', prompt='fixture only, no generation')
    brief['constraints']['resolution'] = list(Image.open(source).size)
    run = tmp_path / 'run'
    path = create(brief, ROOT, run, seed=1)
    manifest = json.loads(path.read_text(encoding='utf-8'))
    assert manifest['status'] == 'RESOLUTION_REVIEW_REQUIRED'
    assert not (run / '060_aseprite').exists()
    review = record_resolution_review(run / '050_resolution/resolution_report.json', selected_height=brief['constraints']['resolution'][1], reason='Established analyzer test fixture; wiring-only benchmark', reviewed_by='automated fixture regression')
    export_reviewed(load_config(ROOT / 'config/pipeline.yaml'), run, review, manifest)
    assert manifest['status'] == 'EXPORT_READY_REVIEW_REQUIRED'
    assert manifest['qa_results'][-1]['pixel_integrity']['exact_rgba_match']
    assert not manifest['game_ready']

def test_pixel_failure_prevents_aseprite(monkeypatch, tmp_path):
    source = ROOT / 'tests/assets/downscaled_illustration.png'
    monkeypatch.setattr(ComfyUIProvider, 'generate', lambda *args: [source])
    brief = make(asset_id='failed_static', output_class='PIXEL_STATIC', prompt='fixture only')
    brief['constraints']['resolution'] = list(Image.open(source).size)
    run = tmp_path / 'run'
    with pytest.raises(ValueError, match='Pixel Gate failed'):
        create(brief, ROOT, run)
    assert not (run / '050_resolution').exists()
    assert not (run / '060_aseprite').exists()
    assert json.loads((run / 'run_manifest.json').read_text())['status'] == 'FAILED'
