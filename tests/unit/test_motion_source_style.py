"""Source style transfer is a research instruction, never a quality approval."""
import copy
import json
import shutil
from pathlib import Path

import pytest
import yaml

from assetpipe.brief import make
from assetpipe.prompts import compile_prompt
from assetpipe.providers.video.prompt import compile_reference_prompt
from assetpipe.registry import load_registry

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def styled(tmp_path):
    shutil.copytree(ROOT / 'config', tmp_path / 'config')
    brief = make(asset_id='fixture', output_class='NONPIXEL_IMAGE', prompt='one rabbit courier')
    brief['project_id'] = 'test'
    brief['art_style'] = 'flat_western_action_cartoon'
    brief['identity']['visual_traits'] = ['blue vest', 'one white satchel']
    brief['prompt_spec'] = {'subject': 'one rabbit courier', 'pose': 'standing, three-quarter view facing right'}
    registry = load_registry(tmp_path)
    source = registry['krea2_base']
    compiled = compile_prompt(brief, source, tmp_path)
    parent = tmp_path / 'parent.json'
    parent.write_text(json.dumps({'workflow': {'id': source['id'], 'hash': source['hash']},
                                 'generation': {'compiled_prompt': compiled}}), encoding='utf-8')
    return tmp_path, brief, registry['nonpixel_motion_contract'], parent, compiled


def test_source_contract_is_preserved_without_still_model_dialect(styled):
    root, brief, motion, parent, compiled = styled
    original = copy.deepcopy(brief)
    result = compile_reference_prompt(brief, motion, root, parent, 'walk in place')
    assert brief == original
    assert result['source_compilation'] == compiled
    assert result['source_style_contract']['id'] == 'STYLE-107'
    assert result['prompt_spec']['pose'] == 'walk in place'
    assert compiled['prompt_spec']['pose'] == 'standing, three-quarter view facing right'
    assert 'three-quarter view facing right' in result['positive']
    assert 'blue vest' in result['positive'] and 'one white satchel' in result['positive']
    assert 'photorealistic skin' in result['positive']
    for key, values in result['source_style_contract'].items():
        if key in {'medium', 'palette', 'linework', 'shading', 'lighting', 'background', 'texture', 'value_structure'}:
            assert all(value in result['positive'] for value in values)
    assert result['negative'] == ''
    assert result['style_transfer_quality'] == 'NOT_VERIFIED'
    assert result['review_state'] == 'REVIEW_REQUIRED'


@pytest.mark.parametrize('mutation, error', [
    ('workflow', 'MOTION_SOURCE_WORKFLOW_UNVERIFIED'),
    ('history', 'MOTION_SOURCE_COMPILATION_CHANGED'),
    ('source_traits', 'MOTION_SOURCE_COMPILATION_CHANGED'),
    ('mode', 'MOTION_SOURCE_STYLE_MODE_UNSUPPORTED'),
    ('exclusions', 'MOTION_SOURCE_EXCLUSIONS_UNSUPPORTED'),
])
def test_source_drift_or_missing_capability_blocks(styled, mutation, error):
    root, brief, motion, parent, _ = styled
    data = json.loads(parent.read_text())
    if mutation == 'workflow':
        data['workflow']['hash'] = '0' * 64
    elif mutation == 'history':
        data['generation']['compiled_prompt']['positive'] += ' changed'
    elif mutation == 'source_traits':
        brief['identity']['visual_traits'].append('red hat')
    elif mutation == 'mode':
        path = root / 'config/model_profiles.yaml'
        config = yaml.safe_load(path.read_text())
        del config['profiles'][motion['model_profile']]['reference_style_mode']
        path.write_text(yaml.safe_dump(config))
    else:
        motion['capabilities']['negative_prompt_instruction'] = False
        motion['capabilities']['negative_prompt'] = False
    parent.write_text(json.dumps(data))
    with pytest.raises(ValueError, match=error):
        compile_reference_prompt(brief, motion, root, parent, 'walk')


def test_source_menu_lock_still_blocks(styled):
    root, brief, motion, parent, _ = styled
    brief['workflow_preferences']['id'] = 'nonpixel_motion_contract'
    with pytest.raises(ValueError, match='conflict'):
        compile_reference_prompt(brief, motion, root, parent, 'walk')
