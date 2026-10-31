"""Brief-only transparent delivery (resolution + transparency + max_file_kb) for NONPIXEL_IMAGE."""
import copy
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from assetpipe.api import route_brief
from assetpipe.brief import make, validate
from assetpipe.prompts import compile_prompt, workflow_values
from assetpipe.qa import basic_image_qa
from assetpipe.registry import load_registry

ROOT = Path(__file__).resolve().parents[2]


def manifest_brief(**constraints):
    """What hf-game-studio's asset manifest asks for: 256x256, alpha, <=512 KB."""
    b = make(asset_id='merc_ash', output_class='NONPIXEL_IMAGE', prompt='Bust portrait of a mercenary, plain background')
    b['project_id'] = 'merc-guild'
    b['workflow_preferences']['id'] = 'krea2_base'
    b['constraints'].update({'resolution': [256, 256], 'transparency': True, 'max_file_kb': 512, **constraints})
    return validate(b)


@pytest.fixture
def no_model_check(monkeypatch):
    import assetpipe.portrait_delivery as delivery
    monkeypatch.setattr(delivery, 'preflight', lambda value: None)


def test_brief_constraints_alone_enable_local_delivery_without_project_sot():
    from assetpipe.portrait_delivery import profile
    b = manifest_brief()
    value = profile(b, ROOT, 'krea2_base')
    assert value['operation'] == 'LOCAL_MASK_UNIFORM_CONTAIN'
    assert value['source'] == 'PIPELINE_DEFAULT' and value['trigger'] == 'BRIEF_RESOLUTION_AND_TRANSPARENCY'
    assert value['human_review_required'] is True and value['max_file_kb'] == 512
    assert value['workflow_id'] == 'krea2_base'
    assert Path(value['model_path']).is_relative_to(Path(value['model_roots'][0]))


@pytest.mark.parametrize('change', [{'transparency': None}, {'transparency': False}, {'resolution': None}])
def test_delivery_needs_both_explicit_dimensions_and_transparency(change):
    from assetpipe.portrait_delivery import profile
    assert profile(manifest_brief(**change), ROOT, 'krea2_base') is None


def test_native_transparent_workflow_and_other_classes_are_untouched():
    from assetpipe.portrait_delivery import default_profile
    b = manifest_brief()
    assert default_profile(b, ROOT, 'x', {'capabilities': {'transparent_output': True}}) is None
    pixel = copy.deepcopy(b)
    pixel['output_class'] = 'PIXEL_STATIC'
    pixel['constraints']['max_file_kb'] = None
    assert default_profile(pixel, ROOT, 'krea2_base') is None


def test_project_sot_delivery_profile_keeps_authority():
    """isekai_examiner binds delivery to krea2_base; the default never replaces that contract."""
    from assetpipe.portrait_delivery import profile
    b = manifest_brief()
    b['project_id'] = 'isekai_examiner'
    b['asset_type'] = 'environment_background_layer'
    assert profile(b, ROOT, 'krea2_base') is None


def test_route_accepts_transparency_and_small_exact_size_through_delivery(no_model_check):
    b = manifest_brief()
    r = route_brief(b, ROOT)
    assert r['status'] == 'ROUTED', r
    assert r['selected_workflow'] == 'krea2_base'
    assert r['delivery_handling']['native_transparency_supported'] is False
    assert r['delivery_handling']['human_review'] == 'REVIEW_REQUIRED'


def test_route_blocks_when_delivery_model_is_unavailable(monkeypatch):
    import assetpipe.portrait_delivery as delivery
    monkeypatch.setattr(delivery, 'preflight', lambda value: (_ for _ in ()).throw(ValueError('model missing')))
    r = route_brief(manifest_brief(), ROOT)
    assert r['status'] == 'BLOCKED'
    assert 'PORTRAIT_DELIVERY_UNAVAILABLE' in r['rejected_candidates']['krea2_base']


def test_source_is_generated_at_preset_size_on_white_and_scaled_down_locally(no_model_check):
    b = manifest_brief()
    wf = load_registry(ROOT)['krea2_base']
    compiled = compile_prompt(b, wf, ROOT)
    assert 'Uniform solid white backdrop' in compiled['positive']
    assert 'visible white margin on every side' in compiled['positive']
    assert compiled['portrait_source']['final_transparency'] is True
    values = workflow_values(compiled, wf, b)
    assert [values['width'], values['height']] == [1024, 1024]
    wide = manifest_brief(resolution=[320, 180])
    values = workflow_values(compile_prompt(wide, wf, ROOT), wf, wide)
    assert [values['width'], values['height']] == [1024, 576]


def test_contain_writes_exact_canvas_and_records_file_limit(tmp_path):
    from assetpipe.portrait_delivery import contain
    source = Image.new('RGBA', (1024, 768), (0, 0, 0, 0))
    ImageDraw.Draw(source).ellipse((200, 100, 800, 700), fill=(120, 80, 40, 255))
    output, placement = contain(source, [256, 256], tmp_path / 'out.png', 512)
    with Image.open(output) as image:
        assert image.size == (256, 256) and image.mode == 'RGBA'
        assert image.getpixel((0, 0))[3] == 0 and image.getpixel((128, 128))[3] == 255
    assert placement['resized_size'] == [256, 192] and placement['offset'] == [0, 32]
    assert placement['within_file_limit'] is True
    assert placement['file_size_bytes'] == output.stat().st_size


def test_basic_qa_fails_file_over_max_file_kb(tmp_path):
    import numpy as np
    path = tmp_path / 'noise.png'
    rng = np.random.default_rng(1)
    Image.fromarray(rng.integers(0, 256, (256, 256, 4), dtype=np.uint8), 'RGBA').save(path)
    b = manifest_brief(max_file_kb=1)
    report = basic_image_qa(path, b)
    assert report['status'] == 'FAIL'
    assert any('max_file_kb' in reason for reason in report['reasons'])
    assert basic_image_qa(path, manifest_brief(max_file_kb=4096))['status'] == 'PASS'


def test_pipeline_delivers_rgba_candidate_and_keeps_review_gate(no_model_check, tmp_path, monkeypatch):
    import assetpipe.portrait_delivery as delivery
    from assetpipe._ported.config import load_config
    from assetpipe.pipelines.nonpixel_image import run
    from assetpipe.providers.comfyui import ComfyUIProvider

    def fake_generate(self, brief, workflow, output, seed):
        output.mkdir(parents=True)
        compiled = compile_prompt(brief, workflow, ROOT)
        (output / 'compiled_prompt.json').write_text(__import__('json').dumps(compiled), encoding='utf-8')
        path = output / 'source.png'
        image = Image.new('RGB', (1024, 1024), 'white')
        ImageDraw.Draw(image).rectangle((300, 200, 700, 1000), fill=(90, 60, 40))
        image.save(path)
        return [path]

    def fake_process(source, resolution, value, directory, max_file_kb=None):
        directory.mkdir(parents=True)
        rgb = Image.open(source).convert('RGBA')
        alpha = Image.eval(rgb.convert('L'), lambda v: 0 if v > 250 else 255)
        rgb.putalpha(alpha)
        output, placement = delivery.contain(rgb, resolution, directory / 'portrait.png', max_file_kb)
        return output, {'operation': value['operation'], **placement, 'human_review': 'REVIEW_REQUIRED'}

    monkeypatch.setattr(ComfyUIProvider, 'generate', fake_generate)
    monkeypatch.setattr(delivery, 'process', fake_process)
    manifest = {'generation': {}, 'qa_results': [], 'pipeline_steps': []}
    result = run(manifest_brief(), load_registry(ROOT)['krea2_base'], load_config(ROOT / 'config/pipeline.yaml'),
                 tmp_path, manifest, 7)
    assert result['status'] == 'CANDIDATE_READY_REVIEW_REQUIRED'
    assert result['delivery_ready'] is False
    with Image.open(result['outputs'][0]) as image:
        assert image.size == (256, 256) and image.mode == 'RGBA'
        assert image.getchannel('A').getextrema() == (0, 255)
    assert result['generation']['raw_outputs'][0].endswith('source.png')
    assert result['portrait_delivery'][0]['within_file_limit'] is True
    assert result['qa_results'][0]['status'] == 'PASS'


@pytest.mark.parametrize('policy, passes', [('UNIFORM_NEUTRAL', True), (None, False)])
def test_default_profile_accepts_light_neutral_t2i_backdrop(tmp_path, monkeypatch, policy, passes):
    """Krea2 emitted ~RGB(238,234,234) for a 'white' backdrop in the 2026-11-01 real run."""
    rembg = pytest.importorskip('rembg')
    from PIL import ImageOps
    import assetpipe.portrait_delivery as delivery
    image = Image.new('RGB', (64, 64), (238, 234, 234))
    ImageDraw.Draw(image).rectangle((16, 10, 48, 63), fill=(70, 50, 40))
    mask = Image.new('L', (64, 64), 0)
    ImageDraw.Draw(mask).rectangle((16, 10, 48, 63), fill=255)
    source = tmp_path / 'source.png'
    image.save(source)
    monkeypatch.setattr(delivery, 'preflight', lambda value: tmp_path / 'pinned.onnx')
    monkeypatch.setattr(rembg, 'new_session', lambda *a, **kw: object())
    monkeypatch.setattr(rembg, 'remove', lambda padded, **kw: ImageOps.expand(mask, border=6, fill=0))
    value = {'operation': 'LOCAL_MASK_UNIFORM_CONTAIN', 'source': 'PIPELINE_DEFAULT'}
    if policy:
        value['source_background_policy'] = policy
    if not passes:
        with pytest.raises(ValueError, match='not verified uniform white'):
            delivery.process(source, [32, 32], value, tmp_path / 'out')
        return
    output, record = delivery.process(source, [32, 32], value, tmp_path / 'out', max_file_kb=512)
    with Image.open(output) as result:
        assert result.size == (32, 32) and result.mode == 'RGBA'
        assert result.getpixel((1, 1))[3] == 0 and result.getpixel((16, 20))[3] == 255
    assert record['alpha_processing']['source_background_refinement']['background_rgb'] == [238, 234, 234]
    assert record['profile_source'] == 'PIPELINE_DEFAULT' and record['within_file_limit'] is True
    assert record['human_review'] == 'REVIEW_REQUIRED'
