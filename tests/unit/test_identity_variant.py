"""동일 인물 변형 작업 계약 테스트. 가짜 CLI만 쓰며 실제 생성이나 인물 유지 판정을 대신하지 않는다."""
import hashlib
import json
from pathlib import Path

import pytest

from assetpipe.factory.planner import plan as plan_request
from assetpipe.factory.variant import PRESERVE, plan_variant, run_variant, variant_brief
from assetpipe.paths import RootResolver
from assetpipe.pipelines import create
from tests.unit.test_cli_providers import Sandbox, brief


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')
    return path


@pytest.fixture
def lab(tmp_path, monkeypatch):
    box = Sandbox(tmp_path, monkeypatch)
    base = brief('codex_imagegen')
    base['project_id'] = 'game_a'
    run = box.root / 'workspace/game_a/runs/fox/base'
    manifest = create(base, box.root, run, None)
    data = json.loads(Path(manifest).read_text(encoding='utf-8'))
    assert data['status'] == 'CANDIDATE_READY_REVIEW_REQUIRED'
    box.base_manifest, box.base_image = Path(manifest), Path(data['outputs'][0])

    def job(**change):
        value = {'schema_version': 1, 'kind': 'FACTORY_IDENTITY_VARIANT_JOB',
                 'project_id': 'game_a', 'asset_id': 'fox_surprised',
                 'base': {'manifest_ref': str(box.base_manifest), 'manifest_sha256': digest(box.base_manifest),
                          'image': {'path': str(box.base_image), 'sha256': digest(box.base_image)},
                          'selected_by': 'tester', 'reason': 'clearest face'},
                 'variation': {'kind': 'EXPRESSION', 'target': 'surprised, eyes wide'},
                 'provider': {'workflow_id': 'grok_imagine'}}
        for key, item in change.items():
            value[key] = {**value[key], **item} if isinstance(item, dict) else item
        return save(box.root / 'workspace/jobs/job.json', value)

    def authorization(plan, identifier='a' * 32, **change):
        value = {'schema_version': 1, 'type': 'IDENTITY_VARIANT_AUTHORIZATION', 'authorization_id': identifier,
                 'project_id': 'game_a', 'asset_id': plan['brief']['asset_id'], 'plan_sha256': plan['plan_sha256'],
                 'workflow_id': plan['workflow']['id'], 'workflow_sha256': plan['workflow']['hash'],
                 'max_requests': 1, 'authorized_by': 'tester', 'reason': 'contract test', **change}
        return save(box.root / f'workspace/jobs/auth-{identifier}.json', value)

    # CLI provider 실행 기록은 provider의 원래 저장 위치를 출처로 남긴다. 부모로 쓰려면 그 위치를 명시 허용한다.
    (tmp_path / 'grok_home').mkdir(exist_ok=True)
    box.roots = [box.root, tmp_path / 'codex_home', tmp_path / 'grok_home']
    box.job, box.authorization = job, authorization
    return box


def test_plan_binds_base_and_routes_explicit_edit_provider_without_dispatch(lab):
    plan = plan_variant(lab.job(), lab.root, allowed_roots=lab.roots)
    assert plan['dispatches'] == 0 and plan['budget_reservations'] == 0 and lab.calls(lab.grok_dir) == []
    assert plan['workflow']['id'] == 'grok_imagine' and plan['base_image']['sha256'] == digest(lab.base_image)
    brief = plan['brief']
    assert brief['source'] == {'type': 'REFERENCE_IMAGE', 'paths': [str(lab.base_image)], 'references': []}
    assert brief['identity'] == {'canonical_traits': ['red scarf', 'one torn ear'], 'visual_traits': ['round glasses']}
    assert brief['forbidden_elements'] == ['weapons', 'text overlay']
    constraints = ' '.join(brief['prompt_spec']['constraints'])
    assert 'Change only the facial expression to: surprised, eyes wide.' in constraints and 'body pose' in constraints
    assert plan['identity_review'] == 'HUMAN_REQUIRED' and plan['game_ready'] is False
    assert plan['base_selection']['meaning'] == 'IDENTITY_BASE_CHOICE_NOT_ART_APPROVAL'
    assert plan_variant(lab.job(), lab.root, allowed_roots=lab.roots)['plan_sha256'] == plan['plan_sha256']


def test_pose_variant_sets_pose_and_keeps_identity_list():
    parent = brief('grok_imagine')
    parent.update(project_id='game_a', style_id='STYLE-111', art_style='watercolor_storybook')
    job = {'project_id': 'game_a', 'asset_id': 'fox_run', 'provider': {'workflow_id': 'grok_imagine'},
           'variation': {'kind': 'POSE', 'target': 'mid-stride running, side view'}}
    value, removed = variant_brief(parent, job, '/base.png')
    assert removed == ['style_id', 'art_style'] and 'style_id' not in value and 'art_style' not in value
    assert value['prompt_spec']['pose'] == 'mid-stride running, side view'
    assert 'body pose' not in PRESERVE['POSE'] and 'rendering style' in PRESERVE['POSE']
    assert 'Change only the body pose to: mid-stride running, side view.' in value['prompt_spec']['constraints']


def test_run_requires_consent_and_matching_single_attempt_authorization(lab):
    job = lab.job()
    plan = plan_variant(job, lab.root, allowed_roots=lab.roots)
    with pytest.raises(ValueError, match='NOT_AUTHORIZED'):
        run_variant(job, plan['plan_sha256'], lab.authorization(plan), lab.root, allowed_roots=lab.roots)
    for change, code in [({'max_requests': 2}, 'AUTHORIZATION_INVALID'), ({'plan_sha256': 'b' * 64}, 'MISMATCH: plan_sha256'),
                         ({'workflow_id': 'codex_imagegen'}, 'MISMATCH: workflow_id')]:
        with pytest.raises(ValueError, match=code):
            run_variant(job, plan['plan_sha256'], lab.authorization(plan, 'c' * 32, **change), lab.root, authorize_generation=True, allowed_roots=lab.roots)
    with pytest.raises(ValueError, match='PLAN_CHANGED'):
        run_variant(job, 'd' * 64, lab.authorization(plan), lab.root, authorize_generation=True, allowed_roots=lab.roots)
    assert lab.calls(lab.grok_dir) == [] and not (lab.root / 'workspace/factory_budget').exists()


def test_authorized_run_sends_base_image_once_and_never_reuses_budget(lab):
    job = lab.job()
    plan = plan_variant(job, lab.root, allowed_roots=lab.roots)
    auth = lab.authorization(plan)
    receipt_path = run_variant(job, plan['plan_sha256'], auth, lab.root, authorize_generation=True, allowed_roots=lab.roots)
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    assert receipt['status'] == 'CANDIDATE_REVIEW_REQUIRED' and receipt['reference_input'] == 'COPIED_TO_PROVIDER_INPUT'
    assert receipt['attempts'] == 1 and receipt['retry'] == receipt['fallback'] == 'NONE'
    assert receipt['identity_review'] == 'HUMAN_REQUIRED' and receipt['game_ready'] is False
    calls = lab.calls(lab.grok_dir)
    assert len(calls) == 1 and calls[0]['argv'][calls[0]['argv'].index('--tools') + 1] == 'image_edit'
    assert 'Change only the facial expression to: surprised, eyes wide.' in calls[0]['prompt']
    manifest = json.loads(Path(receipt['manifest_path']).read_text(encoding='utf-8'))
    assert manifest['asset_id'] == 'fox_surprised' and manifest['generation']['provider']['reference']['sha256'] == digest(lab.base_image)
    assert digest(receipt_path.parent / 'job-input.json') == digest(job)
    with pytest.raises(ValueError, match='ALREADY_RESERVED'):
        run_variant(job, plan['plan_sha256'], auth, lab.root, authorize_generation=True, allowed_roots=lab.roots)
    assert len(lab.calls(lab.grok_dir)) == 1


def test_variant_output_can_be_a_motion_parent(lab):
    job = lab.job()
    plan = plan_variant(job, lab.root, allowed_roots=lab.roots)
    receipt = json.loads(run_variant(job, plan['plan_sha256'], lab.authorization(plan), lab.root,
                                     authorize_generation=True, allowed_roots=lab.roots).read_text(encoding='utf-8'))
    request = {'factory_contract_version': 1, 'factory_line': 'NONPIXEL', 'output_mode': 'IMAGE_TO_SPRITE',
               'project_id': 'game_a', 'asset_id': 'fox_surprised', 'image': {'style_source': 'variant'},
               'source': {'kind': 'EXISTING_RUN', 'manifest_ref': receipt['manifest_path'],
                          'manifest_sha256': receipt['manifest_sha256'],
                          'images': [{'path': receipt['artifacts'][0]['path'], 'sha256': receipt['artifacts'][0]['sha256'],
                                      'role': 'IDENTITY_PRIMARY'}]},
               'motion': {'action': 'idle', 'fps': 12, 'duration_seconds': 1, 'target_frames': 12,
                          'background_policy': 'EXPLICIT_ALPHA_REVIEW'}}
    planned = plan_request(request, lab.root, resolver=RootResolver(lab.roots, base=lab.root))
    assert planned['status'] == 'OFFLINE_CONTRACT_PASS' and planned['parent']['asset_id'] == 'fox_surprised'


def test_unsupported_provider_changed_base_and_invalid_sources_block_before_dispatch(lab):
    with pytest.raises(ValueError, match='ROUTE_BLOCKED.*character_reference'):
        plan_variant(lab.job(provider={'workflow_id': 'codex_imagegen'}), lab.root, allowed_roots=lab.roots)
    with pytest.raises(ValueError, match='ASSET_ID'):
        plan_variant(lab.job(asset_id='fox'), lab.root, allowed_roots=lab.roots)
    with pytest.raises(ValueError, match='hash mismatch'):
        plan_variant(lab.job(base={'image': {'path': str(lab.base_image), 'sha256': 'e' * 64}}), lab.root, allowed_roots=lab.roots)
    data = json.loads(lab.base_manifest.read_text(encoding='utf-8'))
    data['status'] = 'FAILED'
    lab.base_manifest.write_text(json.dumps(data), encoding='utf-8')
    with pytest.raises(ValueError, match='BASE_INVALID'):
        plan_variant(lab.job(), lab.root, allowed_roots=lab.roots)
    assert lab.calls(lab.grok_dir) == []


def test_cli_provider_base_needs_its_output_location_explicitly_allowed(lab):
    # 출처 경로를 조용히 무시하지 않는다. 허용 루트를 명시하지 않으면 계획 단계에서 막힌다.
    with pytest.raises(ValueError, match='outside configured roots'):
        plan_variant(lab.job(), lab.root)
    assert lab.calls(lab.grok_dir) == []


def test_cli_plan_and_run_use_the_same_contract(lab, capsys):
    from assetpipe.cli import main
    roots = [arg for root in lab.roots for arg in ('--allowed-root', str(root))]
    job = lab.job()
    main(['--root', str(lab.root), 'factory', 'variant-plan', '--job', str(job), *roots])
    plan = json.loads(capsys.readouterr().out)
    auth = lab.authorization(plan)
    main(['--root', str(lab.root), 'factory', 'variant-run', '--job', str(job), '--plan-sha256', plan['plan_sha256'],
          '--authorization', str(auth), '--authorize-generation', *roots])
    result = json.loads(capsys.readouterr().out)
    assert result['identity_review'] == 'HUMAN_REQUIRED' and result['receipt_sha256'] == digest(result['receipt_path'])
    assert len(lab.calls(lab.grok_dir)) == 1


def test_published_schema_and_example_match_the_contract():
    from jsonschema import Draft202012Validator
    from assetpipe.factory.variant import SCHEMA
    root = Path(__file__).resolve().parents[2]
    assert json.loads((root / 'schemas/factory_identity_variant_job_v1.schema.json').read_text(encoding='utf-8')) == SCHEMA
    Draft202012Validator(SCHEMA).validate(json.loads((root / 'examples/factory_identity_variant_job.json').read_text(encoding='utf-8')))
