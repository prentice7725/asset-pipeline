import json
from pathlib import Path

import pytest
import yaml

from assetpipe.prompts import compile_prompt
from assetpipe.prompts.spatial import compile_spatial_relationships
from assetpipe.prompts.synthetic_fixture import load_fixture_contract
from assetpipe.registry import load_registry
from assetpipe.styles.contracts import load_style_contract, style_contract_review_template
from assetpipe.styles.review import record_style_contract_review
from scripts import anima_family_pipeline as afp

ROOT = Path(__file__).resolve().parents[2]


def compile_cell(style_id, workflow_id):
    research = yaml.safe_load((ROOT / 'config/style_menu/nonpixel_prompt_research_v0.yaml').read_text(encoding='utf-8'))
    brief = afp._fixture(style_id, research['recipes'][style_id], workflow_id)
    return brief, compile_prompt(brief, load_registry(ROOT)[workflow_id], ROOT)


def test_style_contract_migration_keeps_krea_explorer_and_r2_evidence_links():
    research = yaml.safe_load((ROOT / 'config/style_menu/nonpixel_prompt_research_v0.yaml').read_text(encoding='utf-8'))
    candidates = yaml.safe_load((ROOT / 'config/style_menu/candidates_v0.yaml').read_text(encoding='utf-8'))
    cards = {item['menu_id']: item for item in candidates['cards']}
    for style_id in ('STYLE-001', 'STYLE-004'):
        row = research['recipes'][style_id]
        contract = load_style_contract(ROOT, style_id)
        source = contract['source']
        assert row['style_contract_id'] == style_id
        assert 'style_axes' not in row
        assert 'positive_tags' not in row['anima_base']
        assert 'natural_language_caption' not in row['anima_base']
        assert source['entry_id'] == cards[style_id]['source_id']
        assert source['preview_url'] == cards[style_id]['preview']
        assert source['revision'] == candidates['source']['revision']
        assert Path(ROOT / contract['evidence'][0]['path']).is_file()


@pytest.mark.parametrize('workflow_id,profile', [
    ('anima_base_rebuilt', 'anima-base-rebuilt'), ('anima_turbo', 'anima-turbo'),
])
@pytest.mark.parametrize('style_id', ['STYLE-001', 'STYLE-004'])
def test_each_anima_profile_compiles_contract_without_manual_style_prompt(style_id, workflow_id, profile):
    brief, compiled = compile_cell(style_id, workflow_id)
    assert compiled['profile_id'] == profile
    assert compiled['compiler_revision'] == 'anima_hybrid_v3'
    assert compiled['style_contract_compilation']['contract_id'] == style_id
    assert compiled['style_contract_compilation']['workflow_id'] == workflow_id
    assert compiled['style_contract_review']['status'] == 'NOT_REVIEWED'
    assert compiled['style_contract_review']['failure_codes'] == []
    assert 'style' not in brief['prompt_spec']
    assert 'CINEMATIC_STYLIZED' not in compiled['positive']
    assert 'RED_CHARCOAL' not in compiled['positive']
    assert 'WARM_BALANCED' not in compiled['positive']


def test_r2_style001_regressions_have_required_red_and_forbid_white_neutral():
    _, compiled = compile_cell('STYLE-001', 'anima_turbo')
    contract = load_style_contract(ROOT, 'STYLE-001')
    required_codes = {row['code'] for row in contract['required_style_features']}
    forbidden_codes = {row['code'] for row in contract['forbidden_style_features']}
    assert 'STYLE001_RED_LIGHT_MISSING' in required_codes
    assert 'red neon light visibly illuminates' in compiled['positive'].lower()
    assert 'STYLE001_WHITE_NEUTRAL_BACKGROUND_PRESENT' in forbidden_codes
    assert 'white or neutral studio background' in compiled['negative'].lower()
    assert 'simple subdued neutral environment' not in compiled['positive'].lower()


def test_r2_style004_regressions_keep_full_adult_fixture_and_gouache_requirements():
    brief, compiled = compile_cell('STYLE-004', 'anima_base_rebuilt')
    for trait in ('short dark brown hair', 'plain blue knee-length coat', 'dark trousers', 'dark closed shoes'):
        assert trait in compiled['positive']
    assert 'opaque gouache-like painted edges or brush texture' in compiled['positive']
    assert 'complete head-to-toe framing' in compiled['positive']
    assert 'whole character in frame from head to toe' in compiled['positive']
    assert 'both feet' in compiled['positive']
    assert 'white or neutral' not in compiled['positive'].lower()
    assert brief['prompt_spec']['subject_integrity']['whole_subject_required'] is True


def test_compass_is_single_source_trait_and_front_left_maps_to_image_right():
    brief, compiled = compile_cell('STYLE-004', 'anima_turbo')
    assert compiled['positive'].lower().count('compass') == 1
    assert 'duplicate required equipment' in compiled['negative']
    assert compiled['spatial_relationships'] == [{
        'source_trait': "exactly one brass compass held in the subject's left hand",
        'camera_view': 'FRONT', 'subject_side': 'SUBJECT_LEFT', 'image_side': 'IMAGE_RIGHT',
        'relationship': 'carried', 'visible_count': 1,
    }]
    assert 'maps SUBJECT_LEFT to IMAGE_RIGHT' in compiled['positive']
    assert brief['prompt_spec']['subject_integrity']['equipment'][0]['visible_count'] == 1


@pytest.mark.parametrize(('view', 'side', 'expected'), [
    ('front', 'SUBJECT_LEFT', 'IMAGE_RIGHT'), ('front', 'SUBJECT_RIGHT', 'IMAGE_LEFT'),
    ('rear', 'SUBJECT_LEFT', 'IMAGE_LEFT'), ('rear', 'SUBJECT_RIGHT', 'IMAGE_RIGHT'),
])
def test_spatial_front_and_rear_mappings(view, side, expected):
    spec = {'pose': f'{view} view', 'subject_integrity': {
        'camera_view': view, 'equipment': [{'source_trait': 'a carried item', 'relationship': 'carried',
                                             'visible_count': 1, 'subject_side': side}]}}
    result = compile_spatial_relationships(spec)
    assert result['mappings'][0]['image_side'] == expected


def test_spatial_three_quarter_fails_closed():
    spec = {'pose': 'three-quarter view', 'subject_integrity': {
        'camera_view': 'three_quarter', 'equipment': [{'source_trait': 'a carried item',
            'relationship': 'carried', 'visible_count': 1, 'subject_side': 'SUBJECT_LEFT'}]}}
    with pytest.raises(ValueError, match='SPATIAL_VIEW_UNRESOLVED'):
        compile_spatial_relationships(spec)


def test_synthetic_fixture_contract_has_exact_r3_facts_and_no_project_canon():
    fixture = load_fixture_contract(ROOT)
    assert fixture['state'] == 'SYNTHETIC_NOT_CANON'
    assert fixture['output_class'] == 'NONPIXEL_IMAGE'
    assert fixture['subject']['canonical_traits'] == [
        'adult traveler', 'short dark brown hair', 'plain blue knee-length coat',
        'dark trousers', 'dark closed shoes', "exactly one brass compass held in the subject's left hand",
    ]
    assert fixture['equipment'][0]['subject_side'] == 'SUBJECT_LEFT'
    assert fixture['camera']['view'] == 'FRONT'


def test_style_review_records_human_failure_codes_without_approval(tmp_path):
    contract = load_style_contract(ROOT, 'STYLE-001')
    review = {'style_contract_review': style_contract_review_template(contract),
              'status': 'REVIEW_REQUIRED', 'approval_effect': 'NONE'}
    path = tmp_path / 'visual_review.json'
    path.write_text(json.dumps(review), encoding='utf-8')
    observed = {
        **{row['code']: False for row in contract['required_style_features']},
        **{row['code']: row['code'] == 'STYLE001_WHITE_NEUTRAL_BACKGROUND_PRESENT'
           for row in contract['forbidden_style_features']},
    }
    updated = record_style_contract_review(path, observed, reviewed_by='human', reason='R3 visual inspection')
    assert 'STYLE001_RED_LIGHT_MISSING' in updated['style_contract_review']['failure_codes']
    assert 'STYLE001_WHITE_NEUTRAL_BACKGROUND_PRESENT' in updated['style_contract_review']['failure_codes']
    assert updated['status'] == 'REVIEW_REQUIRED'
    assert updated['approval_effect'] == 'NONE'
    assert updated['style_contract_review']['approval_effect'] == 'NONE'


def test_review_rejects_missing_outcomes_and_unknown_failure_codes(tmp_path):
    contract = load_style_contract(ROOT, 'STYLE-004')
    path = tmp_path / 'visual_review.json'
    path.write_text(json.dumps({'style_contract_review': style_contract_review_template(contract)}), encoding='utf-8')
    with pytest.raises(ValueError, match='COVER_EVERY_CONTRACT_FEATURE'):
        record_style_contract_review(path, {}, reviewed_by='human', reason='incomplete')
    with pytest.raises(ValueError, match='COVER_EVERY_CONTRACT_FEATURE'):
        record_style_contract_review(path, {'UNKNOWN_CODE': True}, reviewed_by='human', reason='invalid')
