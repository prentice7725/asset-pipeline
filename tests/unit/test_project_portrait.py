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
