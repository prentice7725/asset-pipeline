import copy
import json
from pathlib import Path

import pytest

from assetpipe.api import route_brief
from assetpipe.brief import make, validate
from assetpipe.prompts import compile_prompt, compile_spec, from_brief
from assetpipe.prompt_mining import compile_candidate
from assetpipe.registry import load_registry
from assetpipe.styles import resolve_style

ROOT = Path(__file__).resolve().parents[2]


def fixture():
    value = make(asset_id='subject_test', output_class='NONPIXEL_IMAGE', prompt='Fantasy scout')
    value['identity']['canonical_traits'] = ['blue tunic', 'six front belt pouches']
    value['identity']['visual_traits'] = ['red warning flag']
    value['constraints']['silhouette'] = 'upright complete character'
    value['forbidden_elements'] = ['extra weapons']
    value['workflow_preferences'] = {'id': 'anima_base'}
    value['prompt_spec'] = {'subject': 'Fantasy scout', 'pose': 'standing near wooden gate',
        'composition': 'front view', 'environment': 'forest gate with red warning flag',
        'subject_integrity': {'class': 'full_character', 'identity_source': 'synthetic source brief',
            'whole_subject_required': True, 'physically_connected_body': True,
            'mandatory_parts': ['head', 'torso', 'left arm', 'right arm', 'left leg', 'right leg'],
            'camera_view': 'from_source',
            'equipment': [{'source_trait': 'six front belt pouches', 'relationship': 'worn',
                           'visible_count': 6, 'location': 'front'}],
            'forbidden_substitutions': ['floating clothes', 'mannequin']}}
    return value


def direction(style=None):
    result = {'focal_target': 'full_character', 'source': 'explicit fixture direction',
              'value_grouping': 'large_coherent_masses', 'shadow_grouping': 'broad_connected_shadows',
              'background_texture': 'subordinate', 'preserve_scene_landmarks': True}
    if style:
        result['style_sha256'] = style['style_sha256']
    return result


def test_m26_source_first_style_and_canon_are_preserved():
    value = fixture()
    style = resolve_style({**value, 'style_id': 'clean_anime_cel'}, ROOT)
    value['prompt_spec']['art_direction'] = direction(style)
    before = copy.deepcopy(value)
    result = compile_candidate(ROOT, 'mined_clean_anime_cel', value, 'anima_base')
    assert result['positive'].startswith('Depict the complete character')
    for phrase in ['six front belt pouches', 'blue tunic', 'red warning flag',
                   'upright complete character', 'standing near wooden gate', 'front view']:
        assert phrase in result['positive']
    assert result['positive'].index('standing near wooden gate') < result['positive'].index('forest gate')
    assert result['positive'].index('2D cel illustration') < result['positive'].index('Subordinate incidental')
    assert 'floating clothes' not in result['positive']
    assert 'floating clothes' in result['negative'] and 'extra weapons' in result['negative']
    assert result['negative_mode'] == 'NATIVE'
    assert result['subject_contract_review']['semantic'] == 'NOT_VALIDATED'
    assert result['mining']['golden_approved'] is False
    assert value == before


@pytest.mark.parametrize('adapter_id', ['anima_base', 'krea2_base', 'codex_imagegen'])
def test_model_adapters_keep_subject_first_without_inventing_native_negative(adapter_id):
    value = fixture()
    value['forbidden_elements'] = []
    value['prompt_spec']['subject_integrity']['forbidden_substitutions'] = []
    value['workflow_preferences'] = {}
    value['prompt_spec']['art_direction'] = direction()
    result = compile_prompt(value, load_registry(ROOT)[adapter_id], ROOT)
    assert result['positive'].startswith('Depict the complete character')
    assert 'six front belt pouches' in result['positive']
    if adapter_id != 'anima_base':
        assert 'Full body, complete character.' not in result['positive']
    assert result['negative_mode'] == 'NONE'


def test_native_negative_is_not_replaced_with_instruction():
    value = fixture()
    value['forbidden_elements'] = []
    workflow = load_registry(ROOT)['codex_imagegen']
    with pytest.raises(ValueError, match='native negative'):
        compile_prompt(value, workflow, ROOT)
    value['workflow_preferences'] = {'id': 'codex_imagegen', 'allow_experimental': True}
    assert route_brief(value, ROOT)['status'] == 'BLOCKED'


@pytest.mark.parametrize('mutation', ['camera', 'count', 'equipment', 'focal_target', 'class'])
def test_source_and_visibility_conflicts_block(mutation):
    value = fixture()
    lock = value['prompt_spec']['subject_integrity']
    if mutation == 'camera':
        value['prompt_spec']['composition'] = 'rear view'
    elif mutation == 'count':
        lock['equipment'][0]['visible_count'] = 5
    elif mutation == 'equipment':
        lock['equipment'][0]['source_trait'] = 'new sword'
    elif mutation == 'focal_target':
        value['prompt_spec']['art_direction'] = {**direction(), 'focal_target': 'costume_item'}
    else:
        lock['class'] = 'costume_item'
    with pytest.raises(ValueError):
        validate(value)


def test_recipe_cannot_delete_canon_or_lock():
    value = fixture()
    spec = from_brief(value)
    spec['appearance'].remove('blue tunic')
    with pytest.raises(ValueError, match='removed canonical'):
        compile_spec(value, load_registry(ROOT)['anima_base'], ROOT, spec)
    spec = from_brief(value)
    spec['subject_integrity']['mandatory_parts'] = []
    with pytest.raises(ValueError, match='cannot rewrite'):
        compile_spec(value, load_registry(ROOT)['anima_base'], ROOT, spec)


def test_camera_conflict_returns_blocked_route_without_dispatch():
    value = fixture()
    value['prompt_spec']['composition'] = 'rear view'
    decision = route_brief(value, ROOT)
    assert decision['status'] == 'BLOCKED'
    assert decision['selected_workflow'] is None
    assert 'BRIEF_COMPOSITION_CONFLICT' in decision['reason']


def test_style_binding_and_locked_sot_do_not_get_overridden():
    value = fixture()
    style = resolve_style({**value, 'style_id': 'clean_anime_cel'}, ROOT)
    value['prompt_spec']['art_direction'] = direction(style)
    spec = from_brief(value)
    with pytest.raises(ValueError, match='locked Visual SOT'):
        compile_spec(value, load_registry(ROOT)['anima_base'], ROOT, spec,
                     style_context={**style, 'locked': True})
    value['prompt_spec']['art_direction']['style_sha256'] = '0' * 64
    with pytest.raises(ValueError, match='fingerprint'):
        compile_candidate(ROOT, 'mined_clean_anime_cel', value, 'anima_base')


@pytest.mark.parametrize('kind', ['PIXEL_STATIC', 'SFX'])
def test_pixel_and_sfx_contracts_are_not_changed(kind):
    value = fixture()
    value['output_class'] = kind
    with pytest.raises(ValueError, match='NONPIXEL_IMAGE only'):
        validate(value)


def test_costume_item_remains_an_item():
    value = make(asset_id='coat', output_class='NONPIXEL_IMAGE', prompt='Blue coat')
    value['asset_type'] = 'costume_item'
    value['prompt_spec'] = {'subject': 'Blue coat', 'subject_integrity': {
        'class': 'costume_item', 'identity_source': 'item source', 'whole_subject_required': True}}
    result = compile_prompt(value, load_registry(ROOT)['anima_base'], ROOT)
    assert result['positive'].startswith('Depict the costume item')
    assert 'physically connected' not in result['positive']


def test_published_prompt_schema_matches_runtime():
    from assetpipe.prompts import SCHEMA
    assert json.loads((ROOT / 'schemas/prompt-spec.schema.json').read_text()) == SCHEMA


@pytest.mark.parametrize('field', ['whole_subject_required', 'physically_connected_body'])
def test_missing_full_character_lock_is_rejected(field):
    value = fixture()
    del value['prompt_spec']['subject_integrity'][field]
    with pytest.raises(ValueError, match='explicit whole-subject'):
        validate(value)


@pytest.mark.parametrize('trait,location', [('six or seven belt pouches', 'unspecified'), ('six belt pouches', 'rear')])
def test_ambiguous_count_and_unsourced_location_are_rejected(trait, location):
    value = fixture()
    value['identity']['canonical_traits'][1] = trait
    value['prompt_spec']['subject_integrity']['equipment'][0].update(source_trait=trait, location=location)
    with pytest.raises(ValueError, match='SUBJECT_SOURCE_CONFLICT'):
        validate(value)


@pytest.mark.parametrize('camera', ['rear view', 'three-quarter perspective'])
def test_unspecified_equipment_location_requires_visibility_review(camera):
    value = fixture()
    value['identity']['canonical_traits'][1] = 'six belt pouches'
    value['prompt_spec']['composition'] = camera
    value['prompt_spec']['subject_integrity']['equipment'][0].update(source_trait='six belt pouches', location='unspecified')
    result = compile_prompt(value, load_registry(ROOT)['anima_base'], ROOT)
    limits = result['subject_contract_review']['assessment_limits']
    assert limits['view_visibility'] == 'VIEW_VISIBILITY_REVIEW_REQUIRED'
    assert limits['certifies_conflict_absence'] is False
    assert limits['prose_conflicts'] == 'UNASSESSED_OUTSIDE_EXPLICIT_PATTERNS'
    assert camera in result['positive']


@pytest.mark.parametrize('scene', ['forest_gate', 'market_street'])
def test_c_d_fixtures_change_only_background_direction(scene):
    from assetpipe.brief import load
    c = load(ROOT / f'examples/m27/{scene}_C_subject_lock.json')
    d = load(ROOT / f'examples/m27/{scene}_D_background_subordinate.json')
    stripped = copy.deepcopy(d)
    del stripped['prompt_spec']['art_direction']['background_texture']
    assert stripped == c
    results = [compile_candidate(ROOT, 'mined_clean_anime_cel', value, 'anima_base') for value in (c, d)]
    assert results[0]['workflow_inputs'] == results[1]['workflow_inputs']
    assert results[0]['negative'] == results[1]['negative']
    assert results[0]['mining']['recipe_sha256'] == results[1]['mining']['recipe_sha256']
    for result in results:
        assert result['positive'].startswith('Depict the complete character')
        assert 'six belt pouches' in result['positive']
        assert result['mining']['generation_requests'] == 0
