"""General (non-portrait) reference edits: per-class contracts and edit kinds; fake generation only."""
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator, ValidationError
from PIL import Image
import pytest
import yaml

from assetpipe.api import route_brief
from assetpipe.factory.variant import SCHEMA, plan_variant, run_variant, variant_brief
from assetpipe.pipelines import create
from assetpipe.prompts import compile_prompt
from assetpipe.registry import load_registry
from tests.unit.test_cli_providers import Sandbox
from tests.unit.test_project_portrait import environment_wall

ROOT = Path(__file__).resolve().parents[2]
SOT = 'config/styles/projects/isekai_examiner/visual_sot.yaml'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')
    return path


def cleanup_job(workflow_id, kind='CLEANUP', target='all baked-in text and lettering on the wall'):
    return {'asset_id': 'wall_clean', 'project_id': 'isekai_examiner',
            'provider': {'workflow_id': workflow_id}, 'variation': {'kind': kind, 'target': target}}


def edited_wall(workflow_id, kind='CLEANUP'):
    child, _ = variant_brief(environment_wall(), cleanup_job(workflow_id, kind), 'wall.png')
    return child


@pytest.mark.parametrize('editor', ['codex_imagegen', 'grok_imagine'])
def test_wall_cleanup_routes_to_explicit_editor_with_opaque_delivery(editor):
    decision = route_brief(edited_wall(editor), ROOT)
    assert decision['status'] == 'ROUTED' and decision['selected_workflow'] == editor
    assert decision['delivery_handling']['operation'] == 'LOCAL_RESIZE_SAME_ASPECT'
    assert decision['delivery_handling']['resolution'] == [1920, 1080]


def test_wall_cleanup_prompt_names_only_the_unwanted_elements_and_locks_the_rest():
    compiled = compile_prompt(edited_wall('codex_imagegen'), load_registry(ROOT)['codex_imagegen'], ROOT)
    text = compiled['positive']
    assert 'Remove only these unwanted elements: all baked-in text and lettering on the wall.' in text
    assert 'framing, canvas and aspect ratio' in text and 'same character' not in text
    assert 'Uniform solid white backdrop' not in text and 'portrait_source' not in compiled
    edit = compiled['delivery_profile']['project_reference_edit']
    assert edit['reference_input'] == 'EXACT_RGB' and edit['base_workflow_id'] == 'krea2_base'


def test_wall_cleanup_keeps_t2i_binding_for_other_workflows():
    b = edited_wall('anima_base')
    b['workflow_preferences']['allow_experimental'] = True
    decision = route_brief(b, ROOT)
    assert decision['status'] == 'BLOCKED' and 'style menu binding' in decision['reason']


def test_class_without_reference_edit_contract_still_blocks(tmp_path, monkeypatch):
    box = Sandbox(tmp_path, monkeypatch)
    path = box.root / SOT
    sot = yaml.safe_load(path.read_text(encoding='utf-8'))
    sot['asset_class_contracts']['environment_background_layer'].pop('reference_edit_contracts')
    path.write_text(yaml.safe_dump(sot, allow_unicode=True), encoding='utf-8')
    decision = route_brief(edited_wall('codex_imagegen'), box.root)
    assert decision['status'] == 'BLOCKED' and decision.get('selected_workflow') is None


@pytest.mark.parametrize('change', [{'resolution': [1212, 1300]}, {'transparency': True}])
def test_wall_edit_rejects_changed_final_contract(change):
    from assetpipe.router import route
    b = edited_wall('codex_imagegen')
    b['constraints'].update(change)
    with pytest.raises(ValueError, match='PROJECT_REFERENCE_EDIT_INPUT_CONFLICT'):
        route(b, load_registry(ROOT), ROOT)


@pytest.mark.parametrize('failure', ['rgb_without_delivery', 'rgba_with_delivery', 'rgb_with_neutral_backdrop',
                                     'unknown_input', 'bad_resolution'])
def test_invalid_per_class_contracts_fail_closed(failure):
    from assetpipe.styles.project import _reference_edits
    data = yaml.safe_load((ROOT / SOT).read_text(encoding='utf-8'))
    scope = data['asset_class_contracts']['environment_background_layer']
    edit = scope['reference_edit_contracts']['codex_imagegen']
    if failure == 'rgb_without_delivery':
        edit.pop('delivery')
    elif failure == 'rgba_with_delivery':
        edit.update(reference_input='EXACT_RGBA', source_background='UNIFORM_NEUTRAL')
    elif failure == 'rgb_with_neutral_backdrop':
        edit['source_background'] = 'UNIFORM_NEUTRAL'
    elif failure == 'unknown_input':
        edit['reference_input'] = 'ANY'
    else:
        edit['resolution'] = [1920]
    with pytest.raises(ValueError, match='PROJECT_REFERENCE_EDIT_CONTRACT_INVALID'):
        _reference_edits(scope)


def test_rgba_edit_contract_on_a_class_without_mask_delivery_conflicts(tmp_path, monkeypatch):
    box = Sandbox(tmp_path, monkeypatch)
    path = box.root / SOT
    sot = yaml.safe_load(path.read_text(encoding='utf-8'))
    edit = sot['asset_class_contracts']['environment_background_layer']['reference_edit_contracts']['codex_imagegen']
    edit.pop('delivery')
    edit.update(reference_input='EXACT_RGBA', source_background='UNIFORM_NEUTRAL')
    path.write_text(yaml.safe_dump(sot, allow_unicode=True), encoding='utf-8')
    b = edited_wall('codex_imagegen')
    b['constraints']['transparency'] = True
    assert 'PROJECT_REFERENCE_EDIT_INPUT_CONFLICT' in route_brief(b, box.root)['reason']


@pytest.mark.parametrize('kind', ['RECOLOR', 'cleanup', 'STYLE_TRANSFER'])
def test_unknown_edit_kinds_are_rejected(kind):
    job = {'schema_version': 1, 'kind': 'FACTORY_IDENTITY_VARIANT_JOB', 'project_id': 'p', 'asset_id': 'a',
           'base': {'manifest_ref': 'm.json', 'manifest_sha256': '0' * 64,
                    'image': {'path': 'i.png', 'sha256': '0' * 64}, 'selected_by': 'x', 'reason': 'y'},
           'variation': {'kind': kind, 'target': 'text'}, 'provider': {'workflow_id': 'codex_imagegen'}}
    with pytest.raises(ValidationError):
        Draft202012Validator(SCHEMA).validate(job)
    job['variation']['kind'] = 'CLEANUP'
    Draft202012Validator(SCHEMA).validate(job)


def test_detail_edit_changes_one_named_detail_and_keeps_pose_untouched():
    b = environment_wall()
    child, _ = variant_brief(b, cleanup_job('codex_imagegen', 'DETAIL_EDIT', 'one hairline crack near the skirting'), 'wall.png')
    assert 'pose' not in child['prompt_spec']
    assert 'Change only the one named local detail to: one hairline crack near the skirting.' in child['prompt_spec']['constraints']
    assert child['identity'] == b['identity'] and child['forbidden_elements'] == b['forbidden_elements']


def test_resize_delivery_never_crops_pads_or_stretches(tmp_path):
    from assetpipe.portrait_delivery import process
    value = {'operation': 'LOCAL_RESIZE_SAME_ASPECT', 'human_review_required': True}
    wrong = tmp_path / 'wrong.png'
    Image.new('RGB', (1536, 1024), 'white').save(wrong)
    with pytest.raises(ValueError, match='DELIVERY_ASPECT_MISMATCH'):
        process(wrong, [1920, 1080], value, tmp_path / 'a')
    record = json.loads((tmp_path / 'a/delivery_record.json').read_text())
    assert record['status'] == 'FAILED' and record['crop'] is False and record['stretch'] is False
    right = tmp_path / 'right.png'
    Image.new('RGB', (1280, 720), 'white').save(right)
    output, record = process(right, [1920, 1080], value, tmp_path / 'b')
    with Image.open(output) as image:
        assert image.size == (1920, 1080) and image.mode == 'RGB'
    assert record['human_review'] == 'REVIEW_REQUIRED' and record['output_sha256'] == digest(output)


@pytest.fixture(params=['codex_imagegen', 'grok_imagine'])
def wall_lab(tmp_path, monkeypatch, request):
    from assetpipe.providers.comfyui import ComfyUIProvider
    box = Sandbox(tmp_path, monkeypatch)

    def generated(self, brief, workflow, directory, seed):
        directory.mkdir(parents=True)
        source = directory / 'wall.png'
        Image.new('RGB', (1920, 1080), (240, 232, 214)).save(source)
        return [source]
    monkeypatch.setattr(ComfyUIProvider, 'generate', generated)
    base = create(environment_wall(), box.root, box.root / 'workspace/base', None)
    image = Path(json.loads(Path(base).read_text())['outputs'][0])
    job = {'schema_version': 1, 'kind': 'FACTORY_IDENTITY_VARIANT_JOB', 'project_id': 'isekai_examiner',
           'asset_id': 'wall_clean', 'base': {'manifest_ref': str(base), 'manifest_sha256': digest(base),
               'image': {'path': str(image), 'sha256': digest(image)}, 'selected_by': 'unit-test human choice',
               'reason': 'synthetic contract fixture; no real art approval'},
           'variation': {'kind': 'CLEANUP', 'target': 'baked-in text'}, 'provider': {'workflow_id': request.param}}
    box.job, box.base_image, box.editor = save(box.root / 'workspace/job.json', job), image, request.param
    for folder in ('grok_home', 'codex_home'):
        (tmp_path / folder).mkdir(exist_ok=True)
    box.allowed = [box.root, tmp_path / 'grok_home', tmp_path / 'codex_home']
    return box


def authorize(box, plan, authorization_id):
    return save(box.root / f'workspace/auth-{authorization_id[:4]}.json', {
        'schema_version': 1, 'type': 'IDENTITY_VARIANT_AUTHORIZATION', 'authorization_id': authorization_id,
        'project_id': 'isekai_examiner', 'asset_id': 'wall_clean', 'plan_sha256': plan['plan_sha256'],
        'workflow_id': plan['workflow']['id'], 'workflow_sha256': plan['workflow']['hash'],
        'max_requests': 1, 'authorized_by': 'test', 'reason': 'fake E2E'})


def test_wall_cleanup_runs_once_with_exact_rgb_reference_and_review_required(wall_lab):
    box = wall_lab
    (box.codex if box.editor == 'codex_imagegen' else box.grok)(size=(1536, 864))
    editor_dir = box.codex_dir if box.editor == 'codex_imagegen' else box.grok_dir
    plan = plan_variant(box.job, box.root, allowed_roots=box.allowed)
    assert plan['variation']['kind'] == 'CLEANUP' and 'framing, canvas and aspect ratio' in plan['variation']['preserve']
    assert plan['project_reference_edit']['reference_input'] == 'EXACT_RGB'
    assert plan['identity_review'] == 'HUMAN_REQUIRED' and plan['retry'] == plan['fallback'] == 'NONE'
    receipt = run_variant(box.job, plan['plan_sha256'], authorize(box, plan, 'c' * 32), box.root,
                          authorize_generation=True, allowed_roots=box.allowed)
    result = json.loads(receipt.read_text())
    assert result['status'] == 'CANDIDATE_REVIEW_REQUIRED' and result['game_ready'] is False
    manifest = json.loads(Path(result['manifest_path']).read_text())
    provider = manifest['generation']['provider']
    assert provider['reference'] == {**provider['reference'], 'sha256': digest(box.base_image),
                                     'contract': 'EXACT_RGB_UNCHANGED'}
    assert len(box.calls(editor_dir)) == 1
    assert manifest['qa_results'][0]['resolution'] == [1920, 1080]
    assert manifest['portrait_delivery'][0]['operation'] == 'LOCAL_RESIZE_SAME_ASPECT'


def test_wall_cleanup_with_mismatched_editor_aspect_fails_without_retry(wall_lab):
    box = wall_lab
    (box.codex if box.editor == 'codex_imagegen' else box.grok)(size=(1536, 1024))
    editor_dir = box.codex_dir if box.editor == 'codex_imagegen' else box.grok_dir
    plan = plan_variant(box.job, box.root, allowed_roots=box.allowed)
    auth = authorize(box, plan, 'd' * 32)
    with pytest.raises(ValueError, match='DELIVERY_ASPECT_MISMATCH'):
        run_variant(box.job, plan['plan_sha256'], auth, box.root, authorize_generation=True, allowed_roots=box.allowed)
    assert len(box.calls(editor_dir)) == 1
    receipt = json.loads((box.root / 'workspace/factory_budget' / ('d' * 32) / 'variant.json').read_text())
    assert receipt['status'] == 'FAILED' and receipt['attempts'] == 1
