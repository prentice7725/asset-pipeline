import copy
from pathlib import Path

import pytest

from assetpipe.brief import make, validate
from assetpipe.art_direction import apply_intent
from assetpipe.prompts import compile_prompt, from_brief
from assetpipe.registry import load_registry

ROOT = Path(__file__).resolve().parents[2]


def brief():
    value = make(asset_id='scout', output_class='NONPIXEL_IMAGE', prompt='Fantasy scout')
    value['identity']['canonical_traits'] = ['blue tunic', 'six pouches', 'visible insignia']
    value['identity']['visual_traits'] = ['weathered wooden sign']
    return value


def intent():
    return {'version': 1, 'authority': 'EXPLICIT_BRIEF', 'source': 'user asset brief',
            'primary_focus': ['visible insignia']}


@pytest.mark.parametrize('workflow_id', ['anima_base', 'krea2_base', 'codex_imagegen', 'grok_imagine'])
def test_focus_preserves_canon_and_does_not_mutate_input(workflow_id):
    registry = load_registry(ROOT)
    if workflow_id not in registry:
        # Profile IDs are discovered from the actual registry, never invented as production bindings.
        workflow = next(v for v in registry.values() if v.get('engine') ==
                        ('codex_cli' if workflow_id == 'codex_imagegen' else 'grok_cli'))
    else:
        workflow = registry[workflow_id]
    value = brief()
    base = compile_prompt(value, workflow, ROOT)
    value['art_direction'] = intent()
    original = copy.deepcopy(value)
    result = compile_prompt(validate(value), workflow, ROOT)
    for trait in value['identity']['canonical_traits'] + value['identity']['visual_traits']:
        assert trait in result['positive']
    assert result['prompt_spec'].get('style') == base['prompt_spec'].get('style')
    assert result['negative_mode'] == base['negative_mode']
    assert result['art_direction']['status'] == 'INTENT_ONLY_REVIEW_REQUIRED'
    assert value == original
    del value['art_direction']
    assert compile_prompt(value, workflow, ROOT) == base


def test_invented_focus_composition_and_locked_sot_block():
    value = brief()
    value['art_direction'] = intent()
    spec = from_brief(value)
    with pytest.raises(ValueError, match='CONFLICT_REVIEW_REQUIRED'):
        apply_intent(value, spec, {'locked': True})
    spec['composition'] = 'Focus the background sign'
    with pytest.raises(ValueError, match='CONFLICT_REVIEW_REQUIRED'):
        apply_intent(value, spec, None)
    value['art_direction']['primary_focus'] = ['new sword']
    with pytest.raises(ValueError, match='CONFLICT_REVIEW_REQUIRED'):
        apply_intent(value, from_brief(value), None)


def test_route_blocks_conflict_before_generation():
    from assetpipe.api import route_brief
    value = brief()
    value['workflow_preferences']['id'] = 'anima_base'
    value['art_direction'] = intent()
    assert route_brief(value, ROOT)['status'] == 'ROUTED'
    value['constraints']['style'] = 'detailed background as focal subject'
    result = route_brief(value, ROOT)
    assert result['status'] == 'BLOCKED'
    assert 'ART_DIRECTION_CONFLICT_REVIEW_REQUIRED' in result['reason']


@pytest.mark.parametrize('kind', ['PIXEL_STATIC', 'PIXEL_ANIMATION', 'SFX'])
def test_other_output_classes_reject_intent(kind):
    value = brief()
    value['output_class'] = kind
    value['art_direction'] = intent()
    with pytest.raises(ValueError, match='NONPIXEL_IMAGE only'):
        validate(value)
