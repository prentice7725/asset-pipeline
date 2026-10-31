"""PIXEL_STATIC palette quantization before Pixel Gate."""
import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from assetpipe.pixel.quantize import quantize_candidate
from assetpipe._ported.pixel_gate.analyzer import analyze_image

ROOT = Path(__file__).resolve().parents[2]


def noisy_sprite(path, blocks=6, size=96, seed=3):
    """Flat color blocks plus per-pixel noise: thousands of colors, like a diffusion output."""
    rng = np.random.default_rng(seed)
    base = rng.integers(30, 225, (blocks, blocks, 3))
    cell = size // blocks
    rgb = np.kron(base, np.ones((cell, cell, 1))).astype(np.int16)
    rgb += rng.integers(-6, 7, rgb.shape)
    alpha = np.full((size, size), 255, dtype=np.uint8)
    alpha[:cell, :] = 0
    rgba = np.dstack([np.clip(rgb, 0, 255).astype(np.uint8), alpha])
    Image.fromarray(rgba, 'RGBA').save(path)
    return rgba


def test_median_cut_reduces_to_budget_and_preserves_alpha(tmp_path):
    source = tmp_path / 'source.png'
    original = noisy_sprite(source)
    assert analyze_image(source)['palette']['unique_color_count'] > 32
    output, report = quantize_candidate(source, tmp_path / 'q', max_colors=32)
    result = np.asarray(Image.open(output).convert('RGBA'))
    assert report['status'] == 'APPLIED' and report['method'] == 'MEDIAN_CUT'
    assert report['unique_colors_before'] > 1000 and report['unique_colors_after'] <= 32
    assert analyze_image(output)['palette']['unique_color_count'] <= 32
    assert np.array_equal(result[..., 3], original[..., 3])
    assert result.shape == original.shape
    assert report['human_review'] == 'REVIEW_REQUIRED' and report['approval_effect'] == 'NONE'
    saved = json.loads((tmp_path / 'q/quantize_report.json').read_text(encoding='utf-8'))
    assert saved['output_sha256'] == report['output_sha256']


def test_transparent_pixels_do_not_consume_palette_slots(tmp_path):
    rgba = np.zeros((8, 8, 4), dtype=np.uint8)
    rgba[..., :3] = np.arange(64, dtype=np.uint8).reshape(8, 8, 1) * 3
    rgba[:4, :, 3] = 255
    path = tmp_path / 'half.png'
    Image.fromarray(rgba, 'RGBA').save(path)
    _, report = quantize_candidate(path, tmp_path / 'q', max_colors=40)
    assert report['status'] == 'NOT_NEEDED' and report['unique_colors_before'] == 32


def test_brief_palette_snaps_every_opaque_pixel(tmp_path):
    source = tmp_path / 'source.png'
    noisy_sprite(source)
    palette = ['#000000', '#FFFFFF', '#FF0000', '#00FF00', '#0000FF']
    output, report = quantize_candidate(source, tmp_path / 'q', allowed_palette=palette)
    assert report['method'] == 'NEAREST_ALLOWED_PALETTE'
    assert set(report['result_palette']) <= set(palette)
    gate = analyze_image(output, allowed_palette=palette)
    assert gate['palette']['off_palette_pixel_count'] == 0
    assert not any('outside the configured palette' in r for r in gate['reasons']['failure'] + gate['reasons']['fix'])


def test_candidate_within_budget_is_copied_unchanged(tmp_path):
    path = tmp_path / 'flat.png'
    Image.new('RGBA', (16, 16), (10, 20, 30, 255)).save(path)
    output, report = quantize_candidate(path, tmp_path / 'q')
    assert report['status'] == 'NOT_NEEDED' and report['changed_pixels'] == 0
    assert output.read_bytes() == path.read_bytes()


def test_existing_output_directory_is_never_overwritten(tmp_path):
    path = tmp_path / 'flat.png'
    Image.new('RGBA', (4, 4), (1, 2, 3, 255)).save(path)
    (tmp_path / 'q').mkdir()
    with pytest.raises(FileExistsError):
        quantize_candidate(path, tmp_path / 'q')


def test_static_pipeline_quantizes_before_pixel_gate(tmp_path):
    from assetpipe._ported.config import load_config
    from assetpipe.brief import make
    from assetpipe.pipelines.pixel_static import process_candidate
    source = tmp_path / 'candidate.png'
    noisy_sprite(source)
    brief = make(asset_id='sprite', output_class='PIXEL_STATIC', prompt='sprite')
    manifest = {'qa_results': [], 'pipeline_steps': [], 'outputs': []}
    try:
        process_candidate(source, brief, load_config(ROOT / 'config/pipeline.yaml'), tmp_path / 'run', manifest)
    except ValueError as exc:
        # A gate failure for other reasons is allowed; the color budget must not be one of them.
        assert 'Pixel Gate failed' in str(exc)
    steps = [row['step'] for row in manifest['pipeline_steps']]
    assert steps.index('palette_quantize') < steps.index('pixel_gate')
    gate = next(r for r in manifest['qa_results'] if r.get('image', '').endswith('quantized.png'))
    assert gate['palette']['unique_color_count'] <= 32
    assert not any('unique colors exceed' in r for r in gate['reasons']['failure'] + gate['reasons']['fix'])
    assert Path(manifest['outputs'][0]).parent.name == '035_quantize'
    step = next(row for row in manifest['pipeline_steps'] if row['step'] == 'palette_quantize')
    assert step['unique_colors_before'] > 32 and 'source_failure_reasons' in step


def test_quantization_keeps_unquantized_evidence_and_review_state(tmp_path):
    """A smoothed illustration no longer fails on color count, but it is never auto-approved."""
    from assetpipe._ported.config import load_config
    from assetpipe.brief import make
    from assetpipe.pipelines.pixel_static import process_candidate
    source = ROOT / 'tests/assets/downscaled_illustration.png'
    brief = make(asset_id='smooth', output_class='PIXEL_STATIC', prompt='fixture only')
    brief['constraints']['resolution'] = list(Image.open(source).size)
    manifest = {'qa_results': [], 'pipeline_steps': [], 'outputs': []}
    process_candidate(source, brief, load_config(ROOT / 'config/pipeline.yaml'), tmp_path / 'run', manifest)
    step = next(row for row in manifest['pipeline_steps'] if row['step'] == 'palette_quantize')
    assert step['source_analysis_status'] == 'FAIL'
    assert any('gradient' in reason for reason in step['source_failure_reasons'])
    assert manifest['status'].endswith('REVIEW_REQUIRED')
    assert manifest.get('game_ready', False) is False
