import copy
import hashlib
import json
from pathlib import Path
import shutil

import pytest
import yaml

from assetpipe.brief import make, validate
from assetpipe.registry import load_registry
from assetpipe.router import route
from assetpipe.api import route_brief
from assetpipe.prompts import compile_prompt
from assetpipe.styles import digest, style_digest
from assetpipe.manifests import write
from assetpipe.pipelines import create

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def root(tmp_path):
    shutil.copytree(ROOT / 'config', tmp_path / 'config')
    # Unit cases start with candidate knowledge; local real-run artifacts are separate evidence.
    path = tmp_path / 'config/styles/model_recipes.yaml'
    recipes = yaml.safe_load(path.read_text())
    for combinations in recipes['recipes'].values():
        for recipe in combinations.values():
            recipe['status'] = 'UNTESTED'
            recipe.pop('evidence', None)
    put(path, recipes)
    return tmp_path


def brief(style='graphic-risograph', workflow='anima_base'):
    value = make(asset_id='style_test', output_class='NONPIXEL_IMAGE', prompt='A fox scout')
    if style:
        value['style_id'] = style
    if workflow:
        value['workflow_preferences']['id'] = workflow
    return value


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding='utf-8')


def approved():
    return {'approved': True, 'reviewed_by': 'test human reviewer', 'reviewed_at': '2026-10-01', 'reason': 'test fixture only'}


def promote(root, workflow='anima_base', human=True):
    catalog_path = root / 'config/styles/catalog.yaml'
    catalog = yaml.safe_load(catalog_path.read_text())
    style = catalog['styles']['graphic-risograph']
    style.update(status='APPROVED', human_approval=approved())
    put(catalog_path, catalog)
    recipes_path = root / 'config/styles/model_recipes.yaml'
    recipes = yaml.safe_load(recipes_path.read_text())
    recipe = recipes['recipes']['graphic-risograph'][workflow]
    recipe.update(status='APPROVED', style_sha256=style_digest(style), evidence='workspace/test/evidence.json')
    if human:
        recipe['human_approval'] = approved()
    output = root / 'workspace/test/output.png'
    output.parent.mkdir(parents=True, exist_ok=True)
    from PIL import Image
    Image.new('RGB', (8, 8), 'red').save(output)
    manifest = {'workflow': {'id': workflow}, 'status': 'CANDIDATE_READY_REVIEW_REQUIRED',
                'style_selection': {'style_id': 'graphic-risograph', 'recipe_version': '1.0.0', 'style_sha256': style_digest(style), 'recipe_sha256': digest(recipe)},
                'qa_results': [{'status': 'PASS'}], 'outputs': [str(output)]}
    path = root / 'workspace/test/run_manifest.json'
    write(path, manifest)
    write(root / 'workspace/test/evidence.json', {'result': 'STYLE_COMBINATION_TESTED', 'style_id': 'graphic-risograph',
        'workflow_id': workflow, 'recipe_version': '1.0.0', 'run_manifest': 'workspace/test/run_manifest.json',
        'style_sha256': style_digest(style),
        'run_manifest_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'outputs': [{'path': 'workspace/test/output.png', 'sha256': hashlib.sha256(output.read_bytes()).hexdigest()}]})
    put(recipes_path, recipes)


def test_legacy_no_style_unchanged(root):
    value = brief(None, None)
    first = route(value, load_registry(root))
    shutil.rmtree(root / 'config/styles')
    assert route(value, load_registry(root)) == first
    assert 'style_selection' not in first


def test_unknown_style_blocked_all_entrypoints(root):
    value = brief('missing-style')
    assert route_brief(value, root)['status'] == 'BLOCKED'
    with pytest.raises(ValueError, match='Unknown style_id'):
        compile_prompt(value, load_registry(root)['anima_base'], root)
    with pytest.raises(ValueError, match='Unknown style_id'):
        create(value, root, root / 'workspace/blocked')
    manifest = json.loads((root / 'workspace/blocked/run_manifest.json').read_text())
    assert manifest['status'] == 'FAILED' and manifest['outputs'] == []


def test_visual_sot_lock_and_pack_precedence(root):
    project = root / 'config/styles/projects/game'
    put(project / 'visual_sot.yaml', {'style_id': 'anime-cel', 'source': 'project art direction'})
    put(project / 'style_pack.yaml', {'status': 'APPROVED', 'human_approval': approved(),
        'default_style_id': 'graphic-risograph', 'styles': {}})
    value = brief('graphic-risograph')
    value['project_id'] = 'game'
    assert 'lock conflicts' in route_brief(value, root)['reason']
    del value['style_id']
    selection = route(value, load_registry(root))['style_selection']
    assert selection['style_id'] == 'anime-cel' and selection['locked']
    assert selection['selection_source'] == 'PROJECT_VISUAL_SOT'
    (project / 'visual_sot.yaml').unlink()
    assert route(value, load_registry(root))['style_selection']['style_id'] == 'graphic-risograph'
    assert route(value, load_registry(root))['style_selection']['selection_source'] == 'PROJECT_STYLE_PACK'


def test_unapproved_default_and_fake_promotion_blocked(root):
    value = brief(workflow=None)
    assert route_brief(value, root)['status'] == 'BLOCKED'
    promote(root, human=False)
    assert 'human_approval' in route_brief(value, root)['reason']
    promote(root)
    assert route_brief(value, root)['selected_workflow'] == 'anima_base'
    (root / 'workspace/test/output.png').write_bytes(b'tampered')
    assert route_brief(value, root)['status'] == 'BLOCKED'


def test_style_capabilities_block_before_generation(root):
    path = root / 'config/styles/catalog.yaml'
    data = yaml.safe_load(path.read_text())
    data['styles']['graphic-risograph']['required_capabilities'] = ['transparent_output']
    put(path, data)
    recipe_path = root / 'config/styles/model_recipes.yaml'
    recipes = yaml.safe_load(recipe_path.read_text())
    recipes['recipes']['graphic-risograph']['anima_base']['style_sha256'] = style_digest(data['styles']['graphic-risograph'])
    put(recipe_path, recipes)
    assert 'transparent_output' in route_brief(brief(), root)['reason']


@pytest.mark.parametrize('workflow', ['anima_base', 'krea2_base', 'tomohi_character', 'codex_imagegen', 'grok_imagine'])
def test_all_model_compilers_preserve_canon(root, workflow):
    value = brief(workflow=workflow)
    value['workflow_preferences']['allow_experimental'] = True
    value['identity']['canonical_traits'] = ['RED scarf', 'Mira the Fox']
    value['identity']['visual_traits'] = ['green backpack']
    value['constraints']['silhouette'] = 'large triangular ears'
    value['prompt_spec'] = {'subject': 'A fox scout', 'appearance': []}
    original = copy.deepcopy(value)
    registry = load_registry(root)
    decision = route(value, registry)
    result = compile_prompt(value, registry[workflow], root)
    for text in ('RED scarf', 'Mira the Fox', 'green backpack', 'large triangular ears', 'risograph'):
        assert text in result['positive']
    assert result['style_selection'] == decision['style_selection']
    assert result['style_selection']['recipe_status'] == 'UNTESTED'
    assert value == original


def test_explicit_model_and_workflow_priority(root):
    value = brief(workflow=None)
    value['workflow_preferences']['model_profile'] = 'krea2'
    assert route(value, load_registry(root))['selected_workflow'] == 'krea2_base'
    value['workflow_preferences']['id'] = 'anima_base'
    assert route_brief(value, root)['status'] == 'BLOCKED'


def test_pixel_sfx_not_changed(root):
    put(root / 'config/styles/projects/default/visual_sot.yaml', {'style_id': 'anime-cel', 'source': 'test project SOT'})
    for kind in ('PIXEL_STATIC', 'SFX'):
        value = make(asset_id='old', output_class=kind, prompt='sample')
        assert 'style_selection' not in route(value, load_registry(root))
        value['style_id'] = 'graphic-risograph'
        with pytest.raises(ValueError, match='NONPIXEL_IMAGE only'):
            route(value, load_registry(root))


def test_changed_recipe_invalidates_generation_evidence(root):
    promote(root)
    path = root / 'config/styles/model_recipes.yaml'
    recipes = yaml.safe_load(path.read_text())
    recipes['recipes']['graphic-risograph']['anima_base']['positive'] = ['unverified changed prompt']
    put(path, recipes)
    assert 'recipe content differs' in route_brief(brief(), root)['reason']


def test_style_id_schema():
    with pytest.raises(ValueError):
        validate(brief('../unsafe'))


def test_project_pack_overrides_catalog_and_requires_human(root):
    value = brief()
    value['project_id'] = 'game'
    catalog = yaml.safe_load((root / 'config/styles/catalog.yaml').read_text())
    local = copy.deepcopy(catalog['styles']['graphic-risograph'])
    local['texture'] = ['project paper grain']
    recipes_path = root / 'config/styles/model_recipes.yaml'
    recipes = yaml.safe_load(recipes_path.read_text())
    recipe = copy.deepcopy(recipes['recipes']['graphic-risograph']['anima_base'])
    recipe['style_sha256'] = style_digest(local)
    pack = {'status': 'APPROVED', 'styles': {'graphic-risograph': local}, 'human_approval': approved(),
            'recipes': {'graphic-risograph': {'anima_base': recipe}}}
    path = root / 'config/styles/projects/game/style_pack.yaml'
    put(path, pack)
    result = compile_prompt(value, load_registry(root)['anima_base'], root)
    assert 'project paper grain' in result['positive']
    assert 'subtle risograph print grain' not in result['positive']
    assert result['style_selection']['selection_source'] == 'PROJECT_STYLE_PACK'
    assert result['style_selection']['recipe_file'].endswith('game/style_pack.yaml')
    assert route_brief(brief(), root)['status'] == 'ROUTED'  # Shared catalog stays usable.
    pack.pop('human_approval')
    put(path, pack)
    assert 'human_approval' in route_brief(value, root)['reason']


def test_missing_real_evidence_blocks_tested_recipe(root):
    path = root / 'config/styles/model_recipes.yaml'
    recipes = yaml.safe_load(path.read_text())
    recipes['recipes']['graphic-risograph']['anima_base'].update(status='TESTED', evidence='workspace/absent.json')
    put(path, recipes)
    assert 'evidence unavailable' in route_brief(brief(), root)['reason']


def test_route_manifest_and_compiler_share_selection(root, monkeypatch):
    def generate(value, workflow, config, directory, manifest, seed):
        compiled = compile_prompt(value, workflow, root)
        write(directory / '010_generation/compiled_prompt.json', compiled)
        manifest['status'] = 'CANDIDATE_READY_REVIEW_REQUIRED'
    monkeypatch.setattr('assetpipe.pipelines.nonpixel_image.run', generate)
    path = create(brief(), root, root / 'workspace/contract')
    manifest = json.loads(path.read_text())
    decision = json.loads((path.parent / 'route_decision.json').read_text())
    assert manifest['style_selection'] == decision['style_selection']
    assert manifest['generation']['compiled_prompt']['style_selection'] == decision['style_selection']


def test_rejected_style_and_recipe_and_stale_fingerprint(root):
    catalog_path = root / 'config/styles/catalog.yaml'
    catalog = yaml.safe_load(catalog_path.read_text())
    catalog['styles']['graphic-risograph']['status'] = 'REJECTED'
    put(catalog_path, catalog)
    assert 'REJECTED style' in route_brief(brief(), root)['reason']
    catalog['styles']['graphic-risograph']['status'] = 'UNTESTED'
    put(catalog_path, catalog)
    recipe_path = root / 'config/styles/model_recipes.yaml'
    recipes = yaml.safe_load(recipe_path.read_text())
    recipes['recipes']['graphic-risograph']['anima_base']['status'] = 'REJECTED'
    put(recipe_path, recipes)
    assert 'REJECTED style/model' in route_brief(brief(), root)['reason']
    recipes['recipes']['graphic-risograph']['anima_base']['status'] = 'UNTESTED'
    recipes['recipes']['graphic-risograph']['anima_base']['style_sha256'] = 'stale'
    put(recipe_path, recipes)
    assert 'fingerprint mismatch' in route_brief(brief(), root)['reason']
