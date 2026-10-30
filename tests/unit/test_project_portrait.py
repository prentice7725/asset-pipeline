import copy
from pathlib import Path

import pytest
from assetpipe.api import route_brief
from assetpipe.brief import make
from assetpipe.prompts import compile_prompt, from_brief
from assetpipe.prompts.subject_contract import subject_lead
from assetpipe.registry import load_registry
from assetpipe.styles import resolve_style, select_recipe, apply_style

ROOT = Path(__file__).resolve().parents[2]


def portrait():
    b = make(asset_id='portrait_test', output_class='NONPIXEL_IMAGE', prompt='Source-defined applicant')
    b.update(asset_type='character_portrait', project_id='isekai_examiner',
             project_contract_required=True, art_style='modern_flat_manga', style_id='STYLE-104')
    b['workflow_preferences'] = {'id': 'krea2_base', 'model_profile': 'krea2'}
    b['constraints'].update(resolution=[1212, 1300], transparency=True)
    b['forbidden_elements'] = ['watermark']
    b['prompt_spec'] = {'subject': 'Source-defined applicant', 'composition': 'Head-to-chest bust portrait',
                        'negative': ['watermark'], 'subject_integrity': {
                            'class': 'character_portrait', 'identity_source': 'test source',
                            'whole_subject_required': False, 'physically_connected_body': True,
                            'mandatory_parts': ['head', 'neck', 'shoulders', 'upper torso'],
                            'forbidden_substitutions': ['adult-looking face']}}
    return b


def environment_wall():
    b = make(asset_id='env_wall_test', output_class='NONPIXEL_IMAGE',
             prompt='Warm ivory wall plane in a maintained public-service office')
    b.update(asset_type='environment_background_layer', project_id='isekai_examiner',
             project_contract_required=True, art_style='watercolor_storybook', style_id='STYLE-111',
             purpose='Opaque wall-only candidate')
    b['source'] = {'type': 'DOCUMENTS', 'paths': ['source_extract.md'], 'references': []}
    b['identity']['canonical_traits'] = ['Warm ivory wall', 'Pale marble lower-wall treatment']
    b['identity']['visual_traits'] = ['Practical maintained public-service office architecture']
    b['constraints'].update(resolution=[1920, 1080], transparency=False,
                            palette=['Warm Ivory', 'Pale Marble'], style='STYLE-111 watercolor_storybook')
    b['workflow_preferences'] = {'id': 'krea2_base', 'model_profile': 'krea2'}
    b['forbidden_elements'] = ['characters, portraits, desks, counters, notice boards, number displays, printers, documents, readable signage, text, or UI',
                               'cathedral scale, grand altar staging, ornate fantasy excess, heavy impasto, cinematic lighting, dramatic spotlighting',
                               'uniform brown-gold palette, neon, magic-circle clutter, SaaS interface styling, RPG HUD styling',
                               'prominent invented architecture not fixed by the SOT']
    b['prompt_spec'] = {'subject': 'Day 01 wall plane of the celestial reincarnation administration office',
        'subject_integrity': {'class': 'environment', 'identity_source': 'source_extract.md',
                             'forbidden_substitutions': ['cathedral or celestial palace', 'modern SaaS office',
                                                         'sci-fi control room', 'merged foreground furniture and props']},
        'composition': 'Wide 16:9 wall-only layer; quiet planar architecture; avoid invented architecture.',
        'environment': 'Warm ivory wall, simple pale marble lower wall, practical construction, restrained wear.',
        'lighting': 'Bright, even, neutral office light.', 'mood': 'Dry bureaucratic black comedy in the premise only.',
        'appearance': ['Use STYLE-111 watercolor_storybook as rendering technique only.',
                       'Keep delicate watercolor texture readable at game scale.',
                       'Preserve warm ivory and pale marble color roles; do not impose sepia.'],
        'constraints': ['Preserve layer separation and gameplay hierarchy.', 'Do not create readable text or visual interaction cues.'],
        'negative': ['characters', 'furniture or foreground props', 'cathedral', 'ornate fantasy architecture',
                     'heavy impasto', 'cinematic light', 'neon', 'magic circles', 'SaaS UI', 'RPG HUD', 'readable text'],
        'aspectRatio': '16:9',
        'styleSources': [{'url': 'https://github.com/prentice7725/asset-pipeline/blob/5d6353ffa58a05e80a1821d402ca29fdf67da6cf/config/styles/style_menu_v1.yaml',
                          'description': 'STYLE MENU v1 STYLE-111'}]}
    return b


def test_actual_capability_diagnostics_and_project_provenance(monkeypatch):
    import assetpipe.portrait_delivery as delivery
    monkeypatch.setattr(delivery, 'preflight', lambda value: (_ for _ in ()).throw(ValueError('missing model')))
    b = portrait()
    original = copy.deepcopy(b)
    r = route_brief(b, ROOT)
    assert r['status'] == 'BLOCKED'
    assert r['missing_capabilities'] == ['transparent_output']
    assert 'text_to_image' in r['required_capabilities']
    assert 'text_to_image' not in r['reason']
    assert r['style_selection']['selection_source'] == 'PROJECT_VISUAL_SOT'
    assert not any(k.startswith('_') for k in r['style_selection'])
    assert r['constraint_issues'][0]['code'] == 'DELIVERY_RESOLUTION_UNSUPPORTED'
    assert b == original


def test_project_recipe_and_portrait_lead_without_generation():
    b = portrait()
    selection = resolve_style(b, ROOT)
    wf = load_registry(ROOT)['krea2_base']
    selection = select_recipe(selection, wf, ROOT, explicit=True)
    spec = apply_style(from_brief(b), selection)
    assert selection['recipe_file'].endswith('isekai_examiner/visual_sot.yaml')
    assert selection['recipe_status'] == 'UNTESTED'
    assert any('Thin clean dark' in x for x in spec['style'])
    assert not any('bold ink contours' in x for x in spec['style'])
    lead = subject_lead(spec, 'krea2')
    assert 'source crop' in lead
    assert 'whole character in frame' not in lead
    assert 'watermark' in spec['negative']
    compiled = compile_prompt(b, wf, ROOT)
    assert compiled['negative_mode'] == 'POSITIVE_TEXT_INSTRUCTION_REVIEW_REQUIRED'
    assert compiled['negative'] == ''
    assert 'watermark' in compiled['positive']
    assert 'adult-looking face' in compiled['positive']
    assert compiled['exclusion_review']['delivery_ready'] is False
    assert all(c['decision'] == 'NOT_REVIEWED' for c in compiled['exclusion_review']['checks'])


def test_instruction_policy_requires_registered_project_and_workflow():
    b = portrait()
    b['project_contract_required'] = False
    wf = load_registry(ROOT)['krea2_base']
    with pytest.raises(ValueError, match='native negative'):
        compile_prompt(b, wf, ROOT)


def test_delivery_dimensions_and_explicit_route_handling(monkeypatch):
    import assetpipe.portrait_delivery as delivery
    from assetpipe.prompts import workflow_values
    monkeypatch.setattr(delivery, 'preflight', lambda value: None)
    b = portrait()
    wf = load_registry(ROOT)['krea2_base']
    compiled = compile_prompt(b, wf, ROOT)
    values = workflow_values(compiled, wf, b)
    assert [values['width'], values['height']] == [1216, 1304]
    assert b['constraints']['resolution'] == [1212, 1300]
    result = route_brief(b, ROOT)
    assert result['status'] == 'ROUTED'
    assert result['exclusion_handling']['native_negative_supported'] is False
    assert result['delivery_handling']['native_transparency_supported'] is False
    assert result['fallback_candidates'] == []


def test_delivery_model_failure_prevents_generation(monkeypatch, tmp_path):
    import assetpipe.portrait_delivery as delivery
    from assetpipe.pipelines.nonpixel_image import run
    from assetpipe._ported.config import load_config
    monkeypatch.setattr(delivery, 'preflight', lambda value: (_ for _ in ()).throw(ValueError('bad model hash')))
    from assetpipe.providers.comfyui import ComfyUIProvider
    monkeypatch.setattr(ComfyUIProvider, 'generate', lambda *args: pytest.fail('generation must not run'))
    with pytest.raises(ValueError, match='bad model hash'):
        run(portrait(), load_registry(ROOT)['krea2_base'], load_config(ROOT / 'config/pipeline.yaml'),
            tmp_path, {'generation': {}}, 1)


def test_required_project_contract_missing_never_uses_catalog():
    b = portrait()
    b['project_id'] = 'not_registered'
    assert 'PROJECT_SOT_UNREGISTERED' in route_brief(b, ROOT)['reason']


def test_portrait_contract_not_applied_to_environment():
    b = portrait()
    b['asset_type'] = 'environment'
    assert 'PROJECT_ASSET_CONTRACT_UNREGISTERED' in route_brief(b, ROOT)['reason']


def test_portrait_cannot_request_whole_body():
    b = portrait()
    b['prompt_spec']['subject_integrity']['whole_subject_required'] = True
    assert 'BRIEF_COMPOSITION_CONFLICT' in route_brief(b, ROOT)['reason']


def test_existing_nonpixel_without_project_remains_compatible():
    b = make(asset_id='old_brief', output_class='NONPIXEL_IMAGE', prompt='A fox')
    b['workflow_preferences']['id'] = 'krea2_base'
    assert route_brief(b, ROOT)['status'] == 'ROUTED'


def test_project_nonpixel_default_does_not_affect_pixel_or_sfx():
    from assetpipe.styles.project import project_sot
    b = make(asset_id='pixel', output_class='PIXEL_STATIC', prompt='A fox')
    b['project_id'] = 'isekai_examiner'
    assert project_sot(b, ROOT)[0] == {}


def test_environment_style_menu_binding_and_project_negative_review():
    b = environment_wall()
    from assetpipe.brief import validate
    b = validate(b)
    decision = route_brief(b, ROOT)
    assert decision['status'] == 'ROUTED'
    assert decision['selected_workflow'] == 'krea2_base'
    assert decision['style_selection']['style_id'] == 'STYLE-111'
    assert decision['style_selection']['selection_source'] == 'PROJECT_VISUAL_SOT'
    assert decision['style_selection']['recipe_file'].endswith('isekai_examiner/visual_sot.yaml')
    assert decision['style_menu']['source_file'] == 'config/styles/style_menu_v1.yaml'
    assert decision['style_menu']['style_id'] == 'STYLE-111'
    assert decision['style_menu']['menu_candidate_id'] == 'CAND-011'
    assert decision['exclusion_handling']['native_negative_supported'] is False
    compiled = compile_prompt(b, load_registry(ROOT)['krea2_base'], ROOT)
    assert compiled['negative_mode'] == 'POSITIVE_TEXT_INSTRUCTION_REVIEW_REQUIRED'
    assert compiled['negative'] == ''
    for text in b['forbidden_elements'] + b['prompt_spec']['negative'] + b['prompt_spec']['subject_integrity']['forbidden_substitutions']:
        assert text in compiled['positive']
        assert any(row['requirement'] == text for row in compiled['exclusion_review']['checks'])
    assert compiled['exclusion_review']['delivery_ready'] is False


def test_blocked_style_menu_route_keeps_the_menu_selection():
    b = environment_wall()
    b['constraints']['transparency'] = True
    decision = route_brief(b, ROOT)
    assert decision['status'] == 'BLOCKED'
    assert decision['missing_capabilities'] == ['transparent_output']
    assert decision['style_menu']['style_id'] == 'STYLE-111'
    assert decision['style_selection']['selection_source'] == 'PROJECT_VISUAL_SOT'


def test_unsupported_delivery_size_blocks_even_without_alpha_or_negatives():
    b = make(asset_id='size', output_class='NONPIXEL_IMAGE', prompt='A fox')
    b['workflow_preferences']['id'] = 'krea2_base'
    b['constraints']['resolution'] = [1212, 1300]
    r = route_brief(b, ROOT)
    assert r['status'] == 'BLOCKED'
    assert r['missing_capabilities'] == []
    assert 'DELIVERY_RESOLUTION_UNSUPPORTED' in r['reason']
    b['constraints']['resolution'] = [1216, 1304]
    assert route_brief(b, ROOT)['status'] == 'ROUTED'


def test_portrait_source_backdrop_is_distinct_from_transparent_delivery():
    b = portrait()
    b['prompt_spec']['environment'] = 'transparent alpha; no baked background'
    original = copy.deepcopy(b)
    compiled = compile_prompt(b, load_registry(ROOT)['krea2_base'], ROOT)
    assert 'Uniform solid white backdrop' in compiled['positive']
    assert 'transparent alpha; no baked background' not in compiled['positive']
    assert 'Keep the complete hairstyle inside the source canvas with visible white headroom' in compiled['positive']
    assert compiled['portrait_source']['requested_composition'] == b['prompt_spec']['composition']
    assert compiled['portrait_source']['requested_environment'] == b['prompt_spec']['environment']
    assert compiled['delivery_profile']['operation'] == 'LOCAL_MASK_UNIFORM_CONTAIN'
    assert b == original and b['constraints']['transparency'] is True


def test_source_backdrop_policy_does_not_override_ordinary_images():
    b = make(asset_id='scene', output_class='NONPIXEL_IMAGE', prompt='A person in a garden')
    b['workflow_preferences']['id'] = 'krea2_base'
    b['prompt_spec'] = {'subject': 'person', 'environment': 'garden'}
    compiled = compile_prompt(b, load_registry(ROOT)['krea2_base'], ROOT)
    assert compiled['prompt_spec']['environment'] == 'garden'
    assert 'portrait_source' not in compiled and 'Uniform solid white backdrop' not in compiled['positive']


@pytest.mark.parametrize('failure', ['exception', 'opaque', 'wrong_size'])
def test_matting_failure_preserves_segmentation_without_silent_fallback(tmp_path, monkeypatch, failure):
    import sys
    from types import ModuleType
    from PIL import Image, ImageOps
    import assetpipe.portrait_delivery as delivery
    fake_rembg, fake_bg = ModuleType('rembg'), ModuleType('rembg.bg')
    fake_rembg.new_session = lambda *args, **kwargs: object()
    mask = Image.new('L', (32,32), 0)
    for x in range(8,24):
        for y in range(8,24):
            mask.putpixel((x,y),255)
    fake_rembg.remove = lambda image, **kwargs: ImageOps.expand(mask, border=3, fill=0)
    def fail(*args, **kwargs):
        if failure == 'opaque':
            return Image.new('RGBA',(32,32),(255,255,255,255))
        if failure == 'wrong_size':
            return Image.new('RGBA',(8,8),(0,0,0,0))
        raise ValueError('matting failed')
    fake_bg.alpha_matting_cutout = fail
    monkeypatch.setitem(sys.modules, 'rembg', fake_rembg)
    monkeypatch.setitem(sys.modules, 'rembg.bg', fake_bg)
    monkeypatch.setattr(delivery, 'preflight', lambda value: tmp_path/'pinned-model.onnx')
    monkeypatch.setattr(delivery, '_source_background',
                        lambda image, mask: (mask, Image.new('1', image.size, 0),
                                             {'verified_white_fraction': 1.0,'verified_background_fraction':1.0}))
    monkeypatch.setattr(delivery.importlib.metadata, 'version', lambda name: 'test-version')
    source = tmp_path/'source.png'
    Image.new('RGB',(32,32),'white').save(source)
    output = tmp_path/'delivery'
    with pytest.raises(ValueError, match='matting failed|matting returned an invalid|matte has no'):
        delivery.process(source, [32,32], {'operation':'LOCAL_MASK_UNIFORM_CONTAIN'}, output)
    assert (output/'segmentation_mask.png').is_file()
    assert not (output/'portrait.png').exists() and not (output/'masked_original.png').exists()
    import json
    audit = json.loads((output/'alpha_processing.json').read_text())
    assert audit['status'] == 'FAILED' and audit['fallback'] == 'NONE'


def test_real_matting_keeps_white_clothing_inside_subject(tmp_path, monkeypatch):
    rembg = pytest.importorskip('rembg')
    from PIL import Image, ImageDraw, ImageOps
    import hashlib
    import assetpipe.portrait_delivery as delivery
    image = Image.new('RGB', (64,64), 'white')
    draw = ImageDraw.Draw(image)
    draw.rectangle((12,8,52,63), fill='black')
    draw.rectangle((23,29,41,47), fill='white')
    mask = Image.new('L',(64,64),0)
    ImageDraw.Draw(mask).rectangle((12,8,52,63),fill=255)
    source = tmp_path/'source.png'
    image.save(source)
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    monkeypatch.setattr(delivery, 'preflight', lambda value: tmp_path/'pinned-model.onnx')
    monkeypatch.setattr(rembg, 'new_session', lambda *args, **kwargs: object())
    def segment(padded, **kwargs):
        assert padded.size == (76,76)
        assert padded.crop((6,6,70,70)).tobytes() == image.tobytes()
        assert padded.getpixel((0,0)) == (255,255,255)
        return ImageOps.expand(mask, border=6, fill=0)
    monkeypatch.setattr(rembg, 'remove', segment)
    output, record = delivery.process(source,[64,64],{'operation':'LOCAL_MASK_UNIFORM_CONTAIN'},tmp_path/'delivery')
    actual = Image.open(output)
    assert actual.getpixel((32,38)) == (255,255,255,255)
    assert actual.getpixel((2,2))[3] == 0 and actual.getpixel((32,20))[3] == 255
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
    assert Image.open(tmp_path/'delivery/masked_original.png').convert('RGB').tobytes() == image.tobytes()
    assert record['crop'] is False and record['approval_effect'] == 'NONE'
    assert record['alpha_processing']['status'] == 'COMPLETED_REVIEW_REQUIRED'
    assert record['alpha_processing']['rgb_policy'] == 'PRESERVE_OPAQUE_RGB_UNMATTE_WHITE_EDGES'
    assert record['alpha_processing']['segmentation_context']['mask_source_box'] == [6,6,70,70]
    assert Image.open(tmp_path/'delivery/segmentation_mask.png').tobytes() == mask.tobytes()


def test_white_source_refinement_requires_source_seed_and_preserves_border_clothing():
    pytest.importorskip('scipy')
    from PIL import Image, ImageDraw
    from assetpipe.portrait_delivery import _source_background
    image = Image.new('RGB',(20,20),'black')
    draw = ImageDraw.Draw(image)
    draw.rectangle((0,0,4,19),fill='white')
    draw.rectangle((8,12,14,19),fill='white')  # white shirt touches bottom
    draw.point((5,19),fill=(244,244,244))
    mask = Image.new('L',image.size,255)
    mask.putpixel((0,0),0)
    refined,background,record = _source_background(image,mask)
    assert refined.getpixel((4,19)) == 0
    assert refined.getpixel((5,19)) == 255  # outside fixed white tolerance
    assert refined.getpixel((10,19)) == 255  # no seed from canvas/padding
    assert not background.getpixel((10,19))
    assert record['padding_or_edge_seeds'] is False


def test_invalid_context_mask_stops_before_matting(tmp_path, monkeypatch):
    import sys
    from types import ModuleType
    from PIL import Image
    import assetpipe.portrait_delivery as delivery
    fake_rembg, fake_bg = ModuleType('rembg'), ModuleType('rembg.bg')
    fake_rembg.new_session = lambda *args, **kwargs: object()
    fake_rembg.remove = lambda *args, **kwargs: Image.new('L', (32,32), 0)
    fake_bg.alpha_matting_cutout = lambda *args, **kwargs: pytest.fail('invalid mask must stop')
    monkeypatch.setitem(sys.modules, 'rembg', fake_rembg)
    monkeypatch.setitem(sys.modules, 'rembg.bg', fake_bg)
    monkeypatch.setattr(delivery, 'preflight', lambda value: tmp_path/'pinned-model.onnx')
    source = tmp_path/'source.png'
    Image.new('RGB',(32,32),'white').save(source)
    output = tmp_path/'delivery'
    with pytest.raises(ValueError, match='segmentation returned invalid dimensions'):
        delivery.process(source,[32,32],{'operation':'LOCAL_MASK_UNIFORM_CONTAIN'},output)
    assert (output/'segmentation_input.png').is_file()
    assert not (output/'portrait.png').exists()


def test_source_background_gap_misclassified_as_foreground_is_removed_without_erasing_white_details(tmp_path, monkeypatch):
    rembg = pytest.importorskip('rembg')
    from PIL import Image, ImageDraw, ImageOps
    import assetpipe.portrait_delivery as delivery
    image = Image.new('RGB', (80,80), 'white')
    draw = ImageDraw.Draw(image)
    draw.rectangle((8,0,72,79), fill='black')
    # Background channel between strands reaches a falsely confident foreground.
    draw.rectangle((25,0,40,40), fill='white')
    # An enclosed eye/shirt detail must survive the same white color.
    draw.rectangle((45,48,58,61), fill='white')
    mask = Image.new('L',image.size,0)
    ImageDraw.Draw(mask).rectangle((8,0,72,79),fill=255)
    ImageDraw.Draw(mask).rectangle((25,0,40,4),fill=0)
    source = tmp_path/'source.png'
    image.save(source)
    monkeypatch.setattr(delivery,'preflight',lambda value: tmp_path/'pinned-model.onnx')
    monkeypatch.setattr(rembg,'new_session',lambda *args,**kwargs: object())
    monkeypatch.setattr(rembg,'remove',lambda *args,**kwargs: ImageOps.expand(mask,border=8,fill=0))
    output,record = delivery.process(source,[80,80],{'operation':'LOCAL_MASK_UNIFORM_CONTAIN'},tmp_path/'delivery')
    actual = Image.open(output)
    assert actual.getpixel((32,25))[3] == 0, 'open white background gap must not remain opaque'
    assert actual.getpixel((51,54)) == (255,255,255,255), 'enclosed white detail must remain'
    assert actual.getpixel((20,50)) == (0,0,0,255), 'dark silhouette must remain'
    assert Image.open(tmp_path/'delivery/masked_original.png').convert('RGB').tobytes() == image.tobytes()


@pytest.mark.parametrize('background,edge_rgb', [((255,255,255),(140,165,190)), ((240,242,241),(132,158,183))])
def test_translucent_portrait_edge_composites_without_white_backdrop_contamination(tmp_path, monkeypatch,background,edge_rgb):
    pytest.importorskip('scipy')
    import sys
    from types import ModuleType
    from PIL import Image, ImageDraw, ImageOps
    import assetpipe.portrait_delivery as delivery
    image=Image.new('RGB',(32,32),background)
    ImageDraw.Draw(image).rectangle((10,8,23,31),fill=(25,75,125))
    # The known 50%-alpha edge of that color composited onto white.
    ImageDraw.Draw(image).line((9,8,9,31),fill=edge_rgb)
    alpha=Image.new('L',image.size,0)
    ImageDraw.Draw(alpha).rectangle((10,8,23,31),fill=255)
    ImageDraw.Draw(alpha).line((9,8,9,31),fill=128)
    fake_rembg,fake_bg=ModuleType('rembg'),ModuleType('rembg.bg')
    fake_rembg.new_session=lambda *a,**kw: object()
    fake_rembg.remove=lambda *a,**kw: ImageOps.expand(alpha,border=3,fill=0)
    estimate=image.convert('RGBA'); estimate.putalpha(alpha)
    fake_bg.alpha_matting_cutout=lambda *a,**kw: estimate
    monkeypatch.setitem(sys.modules,'rembg',fake_rembg)
    monkeypatch.setitem(sys.modules,'rembg.bg',fake_bg)
    monkeypatch.setattr(delivery,'preflight',lambda value: tmp_path/'pinned.onnx')
    monkeypatch.setattr(delivery.importlib.metadata,'version',lambda name:'test')
    source=tmp_path/'source.png'; image.save(source)
    policy={'operation':'LOCAL_MASK_UNIFORM_CONTAIN'}
    if background!=(255,255,255):
        policy.update(reference_input='EXACT_RGBA',source_background_policy='UNIFORM_NEUTRAL')
    output,record=delivery.process(source,[32,32],policy,tmp_path/'delivery')
    actual=Image.open(output)
    # Composite over black: expected source color * alpha, within 8-bit rounding.
    composite=Image.alpha_composite(Image.new('RGBA',image.size,'black'),actual)
    assert all(abs(c-e)<=1 for c,e in zip(composite.getpixel((9,16))[:3],(13,38,63)))
    assert actual.getpixel((15,16)) == (25,75,125,255)
    assert actual.getchannel('A').tobytes() == alpha.tobytes()
    assert actual.getpixel((0,0)) == (*background,0)


@pytest.mark.parametrize('neutral_pattern',[False,True])
def test_nonwhite_backdrop_stops_before_white_edge_recovery(tmp_path,monkeypatch,neutral_pattern):
    pytest.importorskip('scipy')
    import sys
    import json
    from types import ModuleType
    from PIL import Image,ImageDraw,ImageOps
    import assetpipe.portrait_delivery as delivery
    image=Image.new('RGB',(32,32),(220,210,200))
    if neutral_pattern:
        image=Image.new('RGB',(32,32),(225,225,225))
        ImageDraw.Draw(image).rectangle((16,0,31,31),fill=(250,250,250))
    ImageDraw.Draw(image).rectangle((10,8,23,31),fill='black')
    mask=Image.new('L',image.size,0)
    ImageDraw.Draw(mask).rectangle((10,8,23,31),fill=255)
    fake_rembg,fake_bg=ModuleType('rembg'),ModuleType('rembg.bg')
    fake_rembg.new_session=lambda *a,**kw: object()
    fake_rembg.remove=lambda *a,**kw: ImageOps.expand(mask,border=3,fill=0)
    fake_bg.alpha_matting_cutout=lambda *a,**kw: pytest.fail('unverified backdrop must stop')
    monkeypatch.setitem(sys.modules,'rembg',fake_rembg)
    monkeypatch.setitem(sys.modules,'rembg.bg',fake_bg)
    monkeypatch.setattr(delivery,'preflight',lambda value: tmp_path/'pinned.onnx')
    monkeypatch.setattr(delivery.importlib.metadata,'version',lambda name:'test')
    source=tmp_path/'source.png'; image.save(source)
    out=tmp_path/'delivery'
    policy={'operation':'LOCAL_MASK_UNIFORM_CONTAIN'}
    if neutral_pattern:
        policy.update(reference_input='EXACT_RGBA',source_background_policy='UNIFORM_NEUTRAL')
    with pytest.raises(ValueError,match='not verified uniform'):
        delivery.process(source,[32,32],policy,out)
    audit=json.loads((out/'alpha_processing.json').read_text())
    assert audit['status']=='FAILED' and audit['fallback']=='NONE'
    assert (out/'segmentation_mask.png').is_file() and not (out/'portrait.png').exists()


def reference_portrait():
    b=portrait()
    b['source']={'type':'REFERENCE_IMAGE','paths':['selected.png'],'references':[]}
    b['workflow_preferences']={'id':'grok_imagine','allow_experimental':True}
    return b


def test_explicit_project_reference_edit_retains_style_and_uses_local_delivery(monkeypatch):
    import assetpipe.portrait_delivery as delivery
    from assetpipe.router import route
    monkeypatch.setattr(delivery,'preflight',lambda value: None)
    b=reference_portrait(); original=copy.deepcopy(b)
    decision=route(b,load_registry(ROOT),ROOT)
    assert decision['selected_workflow']=='grok_imagine'
    assert decision['style_selection']['style_id']=='STYLE-104'
    assert decision['delivery_handling']['native_transparency_supported'] is False
    assert decision['delivery_handling']['resolution']==[1212,1300]
    assert decision['fallback_candidates']==[]
    compiled=compile_prompt(b,load_registry(ROOT)['grok_imagine'],ROOT)
    contract=compiled['delivery_profile']['project_reference_edit']
    assert contract['base_workflow_id']=='krea2_base' and len(contract['sot_sha256'])==64
    assert compiled['delivery_profile']['reference_input']=='EXACT_RGBA'
    assert 'Preserve the reference framing and canvas exactly' in compiled['positive']
    assert 'visible white headroom' not in compiled['positive']
    assert 'Match the supplied reference rendering style exactly' in compiled['positive']
    assert b==original and b['project_contract_required'] is True


def test_expression_target_replaces_parent_neutral_expression_without_unlocking_body_pose():
    from assetpipe.factory.variant import variant_brief
    b=portrait(); b['prompt_spec']['pose']='neutral expression'
    job={'asset_id':'surprised','project_id':'isekai_examiner',
         'provider':{'workflow_id':'grok_imagine'},'variation':{'kind':'EXPRESSION','target':'surprised'}}
    child,_=variant_brief(b,job,'selected.png')
    assert 'neutral expression' not in child['prompt_spec']['pose']
    assert 'Keep the body pose exactly as in the reference' in child['prompt_spec']['pose']
    assert child['identity']==b['identity']


@pytest.mark.parametrize('change',[{'resolution':[1024,1024]},{'transparency':False}])
def test_project_edit_rejects_changed_final_contract(change):
    from assetpipe.router import route
    b=reference_portrait(); b['constraints'].update(change)
    with pytest.raises(ValueError,match='PROJECT_REFERENCE_EDIT_INPUT_CONFLICT'):
        route(b,load_registry(ROOT),ROOT)


def test_project_edit_does_not_unlock_t2i_or_other_editors():
    from assetpipe.router import route
    for b in [portrait(),reference_portrait()]:
        b['workflow_preferences']={'id':'grok_imagine' if b['source']['type']!='REFERENCE_IMAGE' else 'codex_imagegen','allow_experimental':True}
        with pytest.raises(ValueError,match='conflicts with style menu binding'):
            route(b,load_registry(ROOT),ROOT)
