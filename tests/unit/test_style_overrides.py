"""Offline routing/authorization regression. No image/provider dispatch."""
import copy
import hashlib
import json
from pathlib import Path
import shutil

import pytest
import yaml

from assetpipe.brief import make, validate, SCHEMA
from assetpipe.registry import load_registry
from assetpipe.router import route
from assetpipe.styles.menu import bind_menu
from assetpipe.styles.overrides import propose_rescue, reserve_generation
from assetpipe.prompts import compile_prompt

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def root(tmp_path):
    shutil.copytree(ROOT / 'config', tmp_path / 'config')
    return tmp_path


def brief():
    result = make(asset_id='assault', output_class='NONPIXEL_IMAGE', prompt='One canon Assault aircraft')
    result.update(art_style='retro_sci_fi_anime', subject_domain='aircraft', project_id='sky')
    return result


def save(root, name, value):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')
    return name


def human():
    return {'approved': True, 'reviewed_by': 'test human', 'reviewed_at': '2026-10-08', 'reason': 'test only'}


def approve(root, b):
    record = {key: b.get(key) for key in ('model_override', 'workflow_override', 'executor_override',
                                         'override_mode', 'override_reason')}
    record.update(project_id='sky', asset_id=b['asset_id'], style_id='STYLE-103', human_approval=human())
    b['override_approval'] = save(root, 'workspace/approval.json', record)
    return record


def manual(root):
    b = brief()
    b.update(model_override='krea2', workflow_override='krea2_base',
             override_mode='USER_MANUAL', override_reason='Repeated aircraft geometry failure')
    approve(root, b)
    return b


def failure_evidence(root, b):
    refs = []
    for index in range(2):
        # Synthetic review artifacts exercise hash validation, not actual images
        # or real generation evidence. These exist only in pytest's temporary dir.
        raw = f'test-only review source {index}'.encode()
        original = f'workspace/original{index}.txt'
        (root / original).parent.mkdir(parents=True, exist_ok=True)
        (root / original).write_bytes(raw)
        refs.append(save(root, f'workspace/failure{index}.json', {
            'project_id': 'sky', 'asset_id': b['asset_id'], 'style_id': 'STYLE-103',
            'state': 'PRIMARY_ROUTE_SUBJECT_FAILURE', 'workflow_id': 'anima_base_rebuilt',
            'subject_domain': 'aircraft', 'failure_type': 'ROLE_IDENTITY_FAILURE',
            'conditions': {'seed': index, 'prompt_sha256': hashlib.sha256(b['prompt'].encode()).hexdigest()},
            'original_path': original, 'original_sha256': hashlib.sha256(raw).hexdigest(),
            'review_source': 'test-only human review', 'uncertainty': 'test fixture, no artwork assessment',
            'human_approval': human()}))
    b['failure_evidence'] = refs


def test_24_styles_keep_full_baseline_route_decisions():
    baseline = json.loads((ROOT / 'tests/fixtures/style_menu_routes_v1.json').read_text(encoding='utf-8'))
    registry = load_registry(ROOT)
    assert len({r['brief']['art_style'] for r in baseline}) == 24
    for row in baseline:
        assert route(row['brief'], registry) == row['decision']


def test_manual_krea_preserves_style_identity_fingerprint_and_primary(root):
    b = manual(root)
    original = copy.deepcopy(b)
    registry = load_registry(root)
    decision = route(b, registry)
    compiled = compile_prompt(b, registry['krea2_base'], root)
    assert b == original
    assert decision['selected_workflow'] == 'krea2_base'
    audit = decision['override']
    assert audit['route_decision'] == 'USER_OVERRIDE'
    assert audit['original']['workflow_id'] == 'anima_base_rebuilt'
    assert audit['primary_model'] == 'anima_base_rebuilt'
    assert audit['selected']['model_profile'] == 'krea2'
    assert audit['selected']['provider'] == 'comfyui'
    assert compiled['style_selection']['style_sha256'] == audit['style_sha256']
    assert 'Assault aircraft' in compiled['positive']
    assert compiled['style_contract_compilation']['contract_id'] == 'STYLE-103'
    assert audit['generation_state'] == 'GENERATION_NOT_RUN'
    assert audit['review_state'] == 'REVIEW_REQUIRED'
    assert not decision['fallback_candidates']


def test_grok_missing_recipe_fails_closed(root):
    registry = load_registry(root)
    wf = next(v for v in registry.values() if v.get('engine') == 'grok_cli')
    b = manual(root)
    b.update(model_override=wf['model_profile'], workflow_override=wf['id'])
    b['workflow_preferences']['allow_experimental'] = True
    approve(root, b)
    with pytest.raises(ValueError, match='No style-compatible recipe'):
        route(b, registry)


def test_executor_is_independent_and_unconnected_agent_blocks(root):
    b = manual(root)
    b['executor_override'] = 'grok'
    approve(root, b)
    with pytest.raises(ValueError, match='EXECUTOR_UNAVAILABLE'):
        route(b, load_registry(root))
    b['executor_override'] = 'local_python'
    approve(root, b)
    decision = route(b, load_registry(root))
    assert decision['override']['selected']['provider'] == 'comfyui'
    assert decision['override']['executor']['actual'] == 'local_python'


@pytest.mark.parametrize('change, error', [
    ({'model_override': 'krea2_base'}, 'MODEL_OVERRIDE_IS_WORKFLOW_ALIAS'),
    ({'model_override': 'anima-base-rebuilt'}, 'workflow/model profile mismatch'),
    ({'style_id': 'STYLE-104'}, 'conflicts'),
    ({'style_lock': False}, 'STYLE_LOCK_CONFLICT'),
    ({'override_approval': 'workspace/missing.json'}, 'evidence unavailable'),
])
def test_override_conflicts(root, change, error):
    b = manual(root)
    b.update(change)
    if 'override_approval' not in change:
        approve(root, b)
    with pytest.raises(ValueError, match=error):
        route(b, load_registry(root))


def test_hard_sot_binding_requires_approved_exception(root):
    b = manual(root)
    sot = {'source': 'drive://sky/active', 'art_style': b['art_style'],
           'model_profile': 'anima-base-rebuilt', 'workflow_id': 'anima_base_rebuilt',
           'hard_model_prohibition': True}
    path = root / 'config/styles/projects/sky/visual_sot.yaml'
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump(sot), encoding='utf-8')
    with pytest.raises(ValueError, match='SOT_BINDING_CONFLICT'):
        route(b, load_registry(root))
    record = approve(root, b)
    record.update(sot_exception_approved=True, sot_exception_source=sot['source'])
    save(root, b['override_approval'], record)
    assert route(b, load_registry(root))['selected_workflow'] == 'krea2_base'
    assert yaml.safe_load(path.read_text()) == sot
    # Without an override the asset-specific SOT binding precedes the menu.
    no_override = brief()
    no_override['workflow_preferences']['allow_experimental'] = True
    assert route(no_override, load_registry(root))['selected_workflow'] == 'anima_base_rebuilt'


def test_capability_blocked_before_generation(root):
    b = manual(root)
    b['constraints']['transparency'] = True
    with pytest.raises(ValueError, match='required capabilities unavailable'):
        route(b, load_registry(root))


def test_rescue_missing_evidence_and_duplicate_originals_block(root):
    b = brief()
    with pytest.raises(ValueError, match='two distinct'):
        propose_rescue(b, root)
    failure_evidence(root, b)
    record = json.loads((root / b['failure_evidence'][1]).read_text())
    first = json.loads((root / b['failure_evidence'][0]).read_text())
    record.update(original_path=first['original_path'], original_sha256=first['original_sha256'])
    save(root, b['failure_evidence'][1], record)
    with pytest.raises(ValueError, match='duplicate artifact'):
        propose_rescue(b, root)


def test_proposal_does_not_generate_or_authorize(root, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('proposal attempted generation')
    from assetpipe.providers.comfyui import ComfyUIProvider
    monkeypatch.setattr(ComfyUIProvider, 'generate', forbidden)
    b = brief()
    failure_evidence(root, b)
    proposal = propose_rescue(b, root)
    assert 1 <= len(proposal['candidates']) <= 3
    assert proposal['generation_requests'] == 0
    assert not proposal['generation_authorized']
    assert all(c['installation'] == 'NOT_VERIFIED' for c in proposal['candidates'])
    assert not (root / 'workspace/override_budget').exists()


def test_proposal_preserves_sot_style_lock_without_executing_model_exception(root):
    b = brief()
    failure_evidence(root, b)
    path = root / 'config/styles/projects/sky/visual_sot.yaml'
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump({'source': 'drive://sky/active', 'art_style': b['art_style'],
                                   'style_id': 'STYLE-103', 'model_profile': 'anima-base-rebuilt',
                                   'workflow_id': 'anima_base_rebuilt'}), encoding='utf-8')
    proposal = propose_rescue(b, root)
    assert any(c['workflow_id'] == 'krea2_base' for c in proposal['candidates'])
    assert all(c['recipe']['style_id'] == 'STYLE-103' for c in proposal['candidates'])
    assert not proposal['generation_authorized']


def test_asset_sot_binding_does_not_leak_to_other_assets(root):
    b = brief()
    path = root / 'config/styles/projects/sky/visual_sot.yaml'
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump({'source': 'drive://sky/active', 'art_style': b['art_style'],
                                   'asset_model_bindings': {'assault': {'model_profile': 'krea2',
                                                                       'workflow_id': 'krea2_base'}}}), encoding='utf-8')
    assert route(b, load_registry(root))['selected_workflow'] == 'krea2_base'
    b['asset_id'] = 'buster'
    assert route(b, load_registry(root))['selected_workflow'] == 'anima_base_rebuilt'


def test_original_without_override_records_sot_and_menu_separately(root):
    b = manual(root)
    b.update(model_override='anima-base-rebuilt', workflow_override='anima_base_rebuilt')
    b['workflow_preferences']['allow_experimental'] = True
    approve(root, b)
    path = root / 'config/styles/projects/sky/visual_sot.yaml'
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump({'source': 'drive://sky/active', 'art_style': b['art_style'],
                                   'model_profile': 'krea2', 'workflow_id': 'krea2_base'}), encoding='utf-8')
    audit = route(b, load_registry(root))['override']
    assert audit['original']['workflow_id'] == 'krea2_base'
    assert audit['menu_original_binding']['workflow_id'] == 'anima_base_rebuilt'
    assert audit['selected']['workflow_id'] == 'anima_base_rebuilt'


def test_approval_cannot_leak_to_another_asset(root):
    b = manual(root)
    b['asset_id'] = 'buster'
    with pytest.raises(ValueError, match='scope mismatch: asset_id'):
        route(b, load_registry(root))


def test_experimental_consent_is_not_inherited_from_primary(root):
    b = manual(root)
    b.update(model_override='anima-turbo', workflow_override='anima_turbo')
    approve(root, b)
    with pytest.raises(ValueError, match='EXPERIMENTAL requires explicit opt-in'):
        route(b, load_registry(root))


def test_rescue_cannot_supersede_project_model_binding(root):
    b = manual(root)
    b['override_mode'] = 'SUBJECT_RESCUE'
    failure_evidence(root, b)
    record = approve(root, b)
    record.update(rescue_exploration_approved=True,
                  failure_evidence_sha256s=[hashlib.sha256((root / r).read_bytes()).hexdigest() for r in b['failure_evidence']])
    save(root, b['override_approval'], record)
    path = root / 'config/styles/projects/sky/visual_sot.yaml'
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump({'source': 'drive://sky/active', 'art_style': b['art_style'],
                                   'model_profile': 'anima-base-rebuilt', 'workflow_id': 'anima_base_rebuilt'}), encoding='utf-8')
    with pytest.raises(ValueError, match='SOT_BINDING_CONFLICT'):
        route(b, load_registry(root))


def test_rescue_route_requires_bound_failure_hashes_and_exploration(root):
    b = manual(root)
    b['override_mode'] = 'SUBJECT_RESCUE'
    failure_evidence(root, b)
    record = approve(root, b)
    with pytest.raises(ValueError, match='exploration approval'):
        route(b, load_registry(root))
    record.update(rescue_exploration_approved=True,
                  failure_evidence_sha256s=[hashlib.sha256((root / r).read_bytes()).hexdigest() for r in b['failure_evidence']])
    save(root, b['override_approval'], record)
    assert route(b, load_registry(root))['override']['route_decision'] == 'APPROVED_SUBJECT_RESCUE'


def test_persistent_single_dispatch_budget_and_no_retry(root):
    b = manual(root)
    decision = route(b, load_registry(root))
    with pytest.raises(ValueError, match='budget required'):
        reserve_generation(b, root, decision)
    auth = {'project_id': 'sky', 'asset_id': b['asset_id'], 'style_id': 'STYLE-103',
            'human_approval': human(), 'generation_approved': True, 'max_requests': 1,
            'override_approval_sha256': decision['override']['approval']['sha256'],
            'workflow_id': 'krea2_base', 'model_profile': 'krea2', 'request_id': 'one',
            'cost_acknowledgement': 'test only, no paid request authorized'}
    b['generation_authorization'] = save(root, 'workspace/generation.json', auth)
    assert reserve_generation(b, root, decision)['reserved_requests'] == 1
    with pytest.raises(ValueError, match='BUDGET_CONSUMED'):
        reserve_generation(b, root, decision)


def test_create_no_budget_preserves_manifest_and_never_calls_provider(root, monkeypatch):
    from assetpipe.pipelines import create
    from assetpipe.providers.comfyui import ComfyUIProvider
    def forbidden(*args, **kwargs):
        pytest.fail('unauthorized provider dispatch')
    monkeypatch.setattr(ComfyUIProvider, 'generate', forbidden)
    b = manual(root)
    output = root / 'workspace/run'
    with pytest.raises(ValueError, match='budget required'):
        create(b, root, output)
    manifest = json.loads((output / 'run_manifest.json').read_text())
    assert manifest['asset_brief'] == b
    assert manifest['status'] == 'FAILED'
    assert manifest['override']['generation_state'] == 'GENERATION_NOT_RUN'
    assert manifest['override']['recipe']['style_sha256']
    assert manifest['generation']['compiled_prompt']['style_contract_review']
    assert manifest['qa_results'] == []
    assert (output / 'route_decision.json').is_file()


def test_existing_image_mock_preserves_qa_provenance_and_review_state(root, monkeypatch):
    from assetpipe.pipelines import create
    from assetpipe.providers.comfyui import ComfyUIProvider
    b = manual(root)
    decision = route(b, load_registry(root))
    auth = {'project_id': 'sky', 'asset_id': b['asset_id'], 'style_id': 'STYLE-103',
            'human_approval': human(), 'generation_approved': True, 'max_requests': 1,
            'override_approval_sha256': decision['override']['approval']['sha256'],
            'workflow_id': 'krea2_base', 'model_profile': 'krea2', 'request_id': 'mock-one',
            'cost_acknowledgement': 'unit test only'}
    b['generation_authorization'] = save(root, 'workspace/mock_budget.json', auth)
    # Return an existing regression image. No generation or fabricated output.
    original = ROOT / 'tests/assets/downscaled_illustration.png'
    calls = []
    def existing(self, brief, workflow, output, seed):
        calls.append(workflow['id'])
        return [original]
    monkeypatch.setattr(ComfyUIProvider, 'generate', existing)
    path = create(b, root, root / 'workspace/mock_run', seed=7725)
    manifest = json.loads(path.read_text())
    assert calls == ['krea2_base']
    assert manifest['asset_brief'] == b
    assert manifest['status'] == 'CANDIDATE_READY_REVIEW_REQUIRED'
    assert manifest['qa_results'] and all(q['status'] == 'PASS' for q in manifest['qa_results'])
    assert manifest['override']['original_outputs'][0]['sha256'] == hashlib.sha256(original.read_bytes()).hexdigest()
    assert manifest['override']['style_review'] == 'NOT_VALIDATED'
    assert manifest['override']['review_state'] == 'REVIEW_REQUIRED'
    assert manifest['generation']['seed'] == 7725


def test_recipe_fingerprint_cannot_be_bypassed(root):
    b = manual(root)
    path = root / 'config/styles/model_recipes.yaml'
    data = yaml.safe_load(path.read_text())
    data['recipes']['STYLE-103']['krea2_base']['style_sha256'] = '0' * 64
    path.write_text(yaml.safe_dump(data), encoding='utf-8')
    with pytest.raises(ValueError, match='fingerprint mismatch'):
        route(b, load_registry(root))


@pytest.mark.parametrize('kind', ['PIXEL_STATIC', 'PIXEL_ANIMATION', 'SFX'])
def test_subject_domain_does_not_change_legacy_routes(kind):
    b = make(asset_id='regression', output_class=kind, prompt='One asset',
             action='walk' if kind.endswith('ANIMATION') else None,
             reference=ROOT / 'tests/assets/downscaled_illustration.png' if kind.endswith('ANIMATION') else None)
    registry = load_registry(ROOT)
    before = route(b, registry)
    b['subject_domain'] = 'aircraft'
    assert route(b, registry) == before


@pytest.mark.parametrize('kind', ['PIXEL_STATIC', 'PIXEL_ANIMATION', 'SFX'])
def test_nonpixel_override_cannot_modify_other_paths(root, kind):
    b = manual(root)
    b['output_class'] = kind
    with pytest.raises(ValueError, match='NONPIXEL_IMAGE'):
        validate(b)


def test_subject_domain_not_inferred_and_schema_matches():
    b = make(asset_id='legacy', output_class='NONPIXEL_IMAGE', prompt='One item')
    assert 'subject_domain' not in validate(b)
    assert json.loads((ROOT / 'schemas/asset_brief.schema.json').read_text()) == SCHEMA
