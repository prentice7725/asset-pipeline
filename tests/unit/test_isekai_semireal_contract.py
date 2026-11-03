from pathlib import Path

from assetpipe.brief import validate
from assetpipe.api import route_brief
from assetpipe.prompts import compile_prompt
from assetpipe.registry import load_registry
from test_project_portrait import environment_wall

ROOT = Path(__file__).resolve().parents[2]

def test_environment_routes_and_compiles_project_semireal_contract():
    brief = validate(environment_wall())
    decision = route_brief(brief, ROOT)
    assert decision['status'] == 'ROUTED'
    assert decision['style_selection']['style_id'] == 'ISEKAI-ENV-SEMIREAL-001'
    assert decision['style_selection']['selection_source'] == 'PROJECT_VISUAL_SOT'
    compiled = compile_prompt(brief, load_registry(ROOT)['krea2_base'], ROOT)
    assert 'semi-realistic' in compiled['positive'].lower()
    assert 'watercolor_storybook' not in compiled['positive'].lower()
    assert compiled['exclusion_review']['delivery_ready'] is False

def test_old_watercolor_request_does_not_override_new_environment_lock():
    brief = environment_wall()
    brief['style_id'] = 'STYLE-111'
    assert route_brief(validate(brief), ROOT)['status'] == 'BLOCKED'

def test_project_workflow_binding_rejects_other_model_without_menu_slug():
    brief = environment_wall()
    brief['workflow_preferences'] = {'id': 'anima_base', 'model_profile': 'anima-base'}
    decision = route_brief(validate(brief), ROOT)
    assert decision['status'] == 'BLOCKED'
    assert 'project binding' in decision['reason']
