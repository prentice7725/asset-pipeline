import hashlib
import json
from pathlib import Path

import pytest
from PIL import Image

from assetpipe.manifests import write
from assetpipe.visual_review import build_review
from assetpipe.styles.contracts import load_style_contract, style_contract_review_template


def candidate(tmp_path, kind='PIXEL_STATIC'):
    image = tmp_path / 'candidate.png'
    Image.new('RGBA', (32, 64), (255, 0, 0, 0)).save(image)
    write(tmp_path / 'run_manifest.json', {
        'output_class': kind, 'status': 'EXPORT_READY_REVIEW_REQUIRED',
        'outputs': [str(image)], 'qa_results': [{'status': 'PASS'}],
        'pipeline_steps': [], 'game_ready': False})
    return image


def test_review_preserves_original_manifest_and_unreviewed_state(tmp_path):
    image = candidate(tmp_path)
    source_bytes = image.read_bytes()
    manifest_bytes = (tmp_path / 'run_manifest.json').read_bytes()
    path = build_review(tmp_path, display_size=(64, 128), matte=(10, 20, 30))
    report = json.loads(path.read_text())
    assert image.read_bytes() == source_bytes
    assert (tmp_path / 'run_manifest.json').read_bytes() == manifest_bytes
    assert (path.parent / 'original.png').read_bytes() == source_bytes
    assert report['source_sha256'] == hashlib.sha256(source_bytes).hexdigest()
    assert report['approval_effect'] == 'NONE' and report['status'] == 'REVIEW_REQUIRED'
    assert all(v['decision'] == 'NOT_REVIEWED' for v in report['checks'].values())
    assert Image.open(path.parent / 'native_matte.png').getpixel((0, 0)) == (10, 20, 30)
    assert Image.open(path.parent / 'display_scale.png').size == (64, 128)
    assert report['settings']['resampling'] == 'NEAREST'
    assert build_review(tmp_path).parent != path.parent


@pytest.mark.parametrize('status', ['FAILED', 'RUNNING', 'RESOLUTION_REVIEW_REQUIRED'])
def test_failed_or_incomplete_run_cannot_get_review(tmp_path, status):
    candidate(tmp_path)
    path = tmp_path / 'run_manifest.json'
    data = json.loads(path.read_text())
    data['status'] = status
    write(path, data)
    with pytest.raises(ValueError, match='technical gates'):
        build_review(tmp_path)
    assert not (tmp_path / 'review_artifacts').exists()


def test_selection_and_failed_qa_cannot_be_bypassed(tmp_path):
    candidate(tmp_path)
    with pytest.raises(ValueError, match='manifest output'):
        build_review(tmp_path, image=tmp_path / 'other.png')
    path = tmp_path / 'run_manifest.json'
    data = json.loads(path.read_text())
    data['qa_results'] = [{'status': 'FAIL'}]
    write(path, data)
    with pytest.raises(ValueError, match='failed technical gate'):
        build_review(tmp_path)


def test_nonpixel_review_has_no_inferred_display_rules(tmp_path):
    candidate(tmp_path, 'NONPIXEL_IMAGE')
    path = build_review(tmp_path)
    report = json.loads(path.read_text())
    assert report['settings']['resampling'] == 'LANCZOS'
    assert report['context_review'] == 'NOT_AVAILABLE_DISPLAY_RULES_MISSING'
    assert 'display_scale.png' not in report['artifacts']


def test_saved_review_manifest_uses_explicit_brief_output_class(tmp_path):
    candidate(tmp_path)
    path = tmp_path / 'run_manifest.json'
    value = json.loads(path.read_text())
    value['asset_brief'] = {'output_class': value.pop('output_class')}
    value['qa_results'].extend([{'status': 'REVIEW_REQUIRED'}, {'status': 'ANALYSIS_COMPLETE_REVIEW_REQUIRED'}])
    write(path, value)
    report = json.loads(build_review(tmp_path).read_text())
    assert report['output_class'] == 'PIXEL_STATIC'


def test_subject_contract_review_never_invents_semantic_or_art_pass(tmp_path):
    candidate(tmp_path, 'NONPIXEL_IMAGE')
    manifest = tmp_path / 'run_manifest.json'
    value = json.loads(manifest.read_text())
    value['asset_brief'] = {'prompt_spec': {'subject_integrity': {
        'class': 'full_character', 'identity_source': 'test fixture',
        'whole_subject_required': True, 'physically_connected_body': True}}}
    write(manifest, value)
    report = json.loads(build_review(tmp_path).read_text())
    assert set(report['review_domains']) == {'SEMANTIC', 'COMPOSITION', 'ART'}
    assert all(domain['status'] == 'NOT_VALIDATED' for domain in report['review_domains'].values())
    assert report['approval_effect'] == 'NONE'


def test_visual_review_exposes_style_contract_failure_code_checklist(tmp_path):
    candidate(tmp_path, 'NONPIXEL_IMAGE')
    manifest = tmp_path / 'run_manifest.json'
    value = json.loads(manifest.read_text())
    contract = load_style_contract(Path(__file__).resolve().parents[2], 'STYLE-001')
    value['generation'] = {'compiled_prompt': {
        'style_contract_review': style_contract_review_template(contract),
    }}
    write(manifest, value)
    report = json.loads(build_review(tmp_path).read_text())
    checklist = report['style_contract_review']
    assert checklist['status'] == 'NOT_REVIEWED'
    assert checklist['failure_codes'] == []
    assert 'STYLE001_RED_LIGHT_MISSING' in {item['code'] for item in checklist['required_features']}
    assert 'STYLE001_WHITE_NEUTRAL_BACKGROUND_PRESENT' in {item['code'] for item in checklist['forbidden_features']}
    assert report['approval_effect'] == 'NONE'
