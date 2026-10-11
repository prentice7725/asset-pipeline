"""Synthetic adapter fixtures: no model call, paid request or review approval."""
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy

import pytest

from assetpipe.brief import make
from assetpipe.factory.executor import execute_file
from assetpipe.pipelines import create as original_create


def save(path, value):
    path.write_text(json.dumps(value), encoding='utf-8')
    return path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def box(tmp_path, monkeypatch):
    import assetpipe.api as api
    import assetpipe.registry as registry
    import assetpipe.pipelines as pipelines
    import assetpipe.prompts as prompts
    workflow = {'id': 'synthetic_workflow', 'hash': 'a'*64, 'version': 1, 'models': {}}
    route = {'status': 'ROUTED', 'selected_workflow': workflow['id'], 'execution_mode': 'SYNTHETIC',
             'missing_requirements': []}
    monkeypatch.setattr(api, 'route_brief', lambda *a, **k: deepcopy(route))
    monkeypatch.setattr(registry, 'load_registry', lambda root: {workflow['id']: workflow})
    monkeypatch.setattr(prompts, 'compile_prompt', lambda *a: {})
    calls = []
    def generate(brief, root, output, seed, **kwargs):
        calls.append((brief, seed, kwargs))
        output.mkdir()
        artifact = output/'synthetic.txt'
        artifact.write_text('Synthetic adapter output; not an actual generated asset')
        return save(output/'run_manifest.json', {'project_id': brief['project_id'],
            'asset_id': brief['asset_id'], 'output_class': brief['output_class'], 'game_ready': False,
            'status': 'SYNTHETIC_REVIEW_REQUIRED', 'outputs': [str(artifact)], 'qa_results': []})
    monkeypatch.setattr(pipelines, 'create', generate)
    def prepare(line='SFX', mode=None):
        output_class = {'SFX': 'SFX', 'NONPIXEL': 'NONPIXEL_IMAGE', 'PIXEL64': 'PIXEL_STATIC'}[line]
        brief = make(asset_id='fixture', output_class=output_class, prompt='synthetic contract only')
        brief['project_id'] = 'test_project'
        brief['workflow_preferences']['id'] = workflow['id']
        request = {'factory_contract_version': 1, 'factory_line': line,
                   'output_mode': mode or ('AUDIO_ONLY' if line == 'SFX' else 'IMAGE_ONLY'),
                   'project_id': 'test_project', 'asset_id': 'fixture',
                   'source': {'kind': 'GENERATE', 'brief_ref': 'brief.json'},
                   'authorization': {'generation_budget': 'authorization.json'}}
        if line == 'SFX':
            brief['audio'] = {'duration_seconds': 1}
            request['audio'] = {'duration_seconds': 1, 'category': 'UI_CUE', 'clip_name': 'fixture_cue'}
        else:
            request['image'] = {'style_source': 'SYNTHETIC_UNAPPROVED'}
            if line == 'PIXEL64':
                brief['constraints']['resolution'] = [64,64]
                request['image']['logical_size'] = [64,64]
        if mode == 'IMAGE_TO_SPRITE':
            request['motion'] = {'action': 'walk', 'fps': 12, 'duration_seconds': 1,
                'target_frames': 12, 'background_policy': 'PRESERVE_OR_REVIEW'}
        save(tmp_path/'brief.json', brief)
        path = save(tmp_path/'request.json', request)
        authorization = {'schema_version': 1, 'type': 'FACTORY_GENERATION_AUTHORIZATION',
            'authorization_id': 'b'*32, 'project_id': 'test_project', 'asset_id': 'fixture',
            'request_sha256': digest(path), 'workflow_id': workflow['id'], 'workflow_sha256': workflow['hash'],
            'seed': 7, 'max_requests': 1, 'authorized_by': 'SYNTHETIC_FIXTURE_ONLY', 'reason': 'No real approval'}
        save(tmp_path/'authorization.json', authorization)
        return path, request, authorization
    return tmp_path, prepare, calls, route, workflow, generate


@pytest.mark.parametrize('line', ['SFX','NONPIXEL','PIXEL64'])
def test_terminal_adapter_preserves_candidate_and_receipt(box, line):
    root, prepare, calls, *_ = box
    path, _, _ = prepare(line)
    from assetpipe.factory.planner import plan_file
    assert plan_file(path,root)['execution_status'] == 'NOT_RUN_REQUIRES_EXPLICIT_AUTHORIZATION'
    receipt = json.loads(execute_file(path, root, authorize_generation=True, seed=7).read_text())
    assert len(calls) == 1 and calls[0][1] == 7
    assert receipt['status'] == 'CANDIDATE_REVIEW_REQUIRED'
    assert receipt['attempts'] == 1 and receipt['retry'] == receipt['fallback'] == 'NONE'
    assert receipt['game_ready'] is False and receipt['review_state'] == 'REVIEW_REQUIRED'
    assert receipt['artifacts'][0]['sha256'] == digest(root/'workspace/factory_budget'/('b'*32)/'run/synthetic.txt')
    assert calls[0][0]['workflow_preferences']['id'] == 'synthetic_workflow'
    assert calls[0][2]['clip'] == ({'duration_seconds':1,'category':'UI_CUE','clip_name':'fixture_cue',
                                   'no_music':True,'no_voice':True} if line == 'SFX' else None)


@pytest.mark.parametrize('key,value', [('max_requests',2),('max_requests',True),('seed',True),
    ('request_sha256','c'*64),('workflow_id','other'),('workflow_sha256','c'*64),
    ('project_id','other'),('asset_id','other'),('authorized_by',''),('reason',''),
    ('authorization_id','../escape'),('type','ART_APPROVAL'),('schema_version',True)])
def test_invalid_authorization_blocks_before_reservation(box, key, value):
    root, prepare, calls, *_ = box
    path, _, auth = prepare()
    auth[key] = value
    save(root/'authorization.json', auth)
    with pytest.raises(ValueError): execute_file(path, root, authorize_generation=True, seed=7)
    assert calls == [] and not (root/'workspace/factory_budget').exists()


@pytest.mark.parametrize('kwargs', [{}, {'authorize_generation':True}, {'authorize_generation':True,'seed':True},
    {'authorize_generation':True,'seed':-1}, {'authorize_generation':True,'seed':2**32}])
def test_consent_and_seed_are_required(box, kwargs):
    root, prepare, calls, *_ = box
    path, *_ = prepare()
    with pytest.raises(ValueError): execute_file(path, root, **kwargs)
    assert calls == [] and not (root/'workspace').exists()


def test_motion_blocks_before_still_generation(box):
    root, prepare, calls, *_ = box
    path, *_ = prepare('NONPIXEL', 'IMAGE_TO_SPRITE')
    with pytest.raises(ValueError, match='BLOCKED_BACKEND_NOT_VERIFIED'):
        execute_file(path, root, authorize_generation=True, seed=7)
    assert calls == [] and not (root/'workspace').exists()


def test_failure_consumes_budget_without_retry(box, monkeypatch):
    import assetpipe.pipelines as pipelines
    root, prepare, calls, *_ = box
    path, *_ = prepare()
    def fail(*a, **k):
        calls.append('failed_attempt')
        raise RuntimeError('synthetic ambiguous generation failure')
    monkeypatch.setattr(pipelines, 'create', fail)
    with pytest.raises(RuntimeError): execute_file(path, root, authorize_generation=True, seed=7)
    receipt = json.loads((root/'workspace/factory_budget'/('b'*32)/'execution.json').read_text())
    assert receipt['status'] == 'FAILED'
    with pytest.raises(ValueError, match='ALREADY_RESERVED'):
        execute_file(path, root, authorize_generation=True, seed=7)
    assert calls == ['failed_attempt']


def test_concurrent_jobs_cannot_share_authorization(box):
    root, prepare, calls, *_ = box
    path, *_ = prepare()
    def invoke():
        try: return execute_file(path, root, authorize_generation=True, seed=7)
        except ValueError as exc: return str(exc)
    with ThreadPoolExecutor(max_workers=2) as pool: results = list(pool.map(lambda _: invoke(), range(2)))
    assert len(calls) == 1
    assert sum('ALREADY_RESERVED' in str(result) for result in results) == 1


@pytest.mark.parametrize('gate', ['route','compiler','source_drift'])
def test_failed_preflight_does_not_consume_budget(box, monkeypatch, gate):
    import assetpipe.prompts as prompts
    root, prepare, calls, route, *_ = box
    path, *_ = prepare('NONPIXEL')
    if gate == 'route': route.update(status='BLOCKED', missing_requirements=['synthetic blocked'])
    else:
        def compiler(*a):
            if gate == 'compiler': raise ValueError('synthetic compiler gate')
            brief = json.loads((root/'brief.json').read_text()); brief['prompt'] = 'changed fixture'
            save(root/'brief.json', brief)
        monkeypatch.setattr(prompts,'compile_prompt',compiler)
    with pytest.raises(ValueError): execute_file(path,root,authorize_generation=True,seed=7)
    assert not calls and not (root/'workspace').exists()


@pytest.mark.parametrize('mutation', ['qa','approved','wrong_project','outside_output','missing_outputs'])
def test_bad_result_cannot_advance(box, monkeypatch, mutation):
    import assetpipe.pipelines as pipelines
    root, prepare, calls, _, _, generate = box
    path, *_ = prepare()
    def result(*a, **k):
        manifest_path = generate(*a, **k)
        manifest = json.loads(manifest_path.read_text())
        if mutation == 'qa': manifest['qa_results'] = [{'status':'FAIL'}]
        if mutation == 'approved': manifest['game_ready'] = True
        if mutation == 'wrong_project': manifest['project_id'] = 'other'
        if mutation == 'outside_output': manifest['outputs'] = [str(path)]
        if mutation == 'missing_outputs': manifest['outputs'] = []
        return save(manifest_path, manifest)
    monkeypatch.setattr(pipelines,'create',result)
    with pytest.raises(ValueError): execute_file(path,root,authorize_generation=True,seed=7)
    receipt = json.loads((root/'workspace/factory_budget'/('b'*32)/'execution.json').read_text())
    assert receipt['status'] == 'FAILED' and receipt['game_ready'] is False


def test_existing_create_receives_audio_metadata(box, monkeypatch):
    import assetpipe.pipelines as pipelines
    import assetpipe.pipelines.sfx as sfx
    import assetpipe.registry as registry
    # Preserve module identity so monkeypatch restores every shared function.
    root, prepare, calls, _, workflow, _ = box
    monkeypatch.setattr(pipelines,'load_registry',registry.load_registry)
    monkeypatch.setattr(pipelines,'load_config',lambda path: None)
    def run(brief, workflow, config, directory, manifest, seed, *, clip):
        calls.append(clip)
        manifest['status'] = 'AUDIO_CANDIDATE_READY_REVIEW_REQUIRED'
        artifact = directory/'synthetic_pipeline_adapter.txt'
        artifact.write_text('Synthetic adapter fixture only')
        manifest['outputs'] = [str(artifact)]
    monkeypatch.setattr(sfx,'run',run)
    monkeypatch.setattr(pipelines,'create',original_create)
    path, *_ = prepare()
    execute_file(path,root,authorize_generation=True,seed=7)
    assert len(calls) == 1 and calls[0]['clip_name'] == 'fixture_cue'


@pytest.mark.parametrize('target', ['authorization','budget'])
def test_alias_escape_is_rejected_before_dispatch(box, tmp_path, target):
    import os
    import subprocess
    root, prepare, calls, *_ = box
    path, request, _ = prepare()
    outside = root.parent/(root.name + '_outside')
    outside.mkdir()
    if target == 'authorization':
        saved = root/'authorization.json'
        (outside/'authorization.json').write_bytes(saved.read_bytes())
        saved.unlink()
        try: saved.symlink_to(outside/'authorization.json')
        except OSError as exc: pytest.skip('Symlink creation unavailable: ' + str(exc))
    else:
        workspace = root/'workspace'
        workspace.mkdir()
        alias = workspace/'factory_budget'
        if os.name == 'nt':
            subprocess.run(['cmd','/c','mklink','/J',str(alias),str(outside)],check=True,capture_output=True)
        else: alias.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError): execute_file(path,root,authorize_generation=True,seed=7)
    assert calls == [] and not (outside/('b'*32)).exists()


def test_missing_budget_document_is_not_authorization(box):
    root, prepare, calls, *_ = box
    path, request, _ = prepare()
    request.pop('authorization')
    save(path, request)
    with pytest.raises(ValueError,match='NOT_AUTHORIZED'):
        execute_file(path,root,authorize_generation=True,seed=7)
    assert not calls and not (root/'workspace').exists()


def test_reroute_cannot_change_authorized_workflow_at_dispatch(box, monkeypatch):
    import assetpipe.pipelines as pipelines
    import assetpipe.pipelines.sfx as sfx
    root, prepare, calls, _, workflow, _ = box
    path, *_ = prepare()
    changed = {**workflow, 'hash': 'c'*64}
    monkeypatch.setattr(pipelines,'create',original_create)
    monkeypatch.setattr(pipelines,'load_registry',lambda root: {workflow['id']: changed})
    monkeypatch.setattr(sfx,'run',lambda *a, **k: pytest.fail('changed workflow dispatched'))
    with pytest.raises(ValueError,match='dispatch workflow changed'):
        execute_file(path,root,authorize_generation=True,seed=7)
    assert not calls


@pytest.mark.parametrize('target', ['budget_root','reservation'])
def test_same_root_budget_alias_does_not_bypass_lock(box, target):
    import os
    import subprocess
    root, prepare, calls, *_ = box
    path, *_ = prepare()
    destination = root/'other_directory'
    destination.mkdir()
    workspace = root/'workspace'
    workspace.mkdir()
    if target == 'budget_root': alias = workspace/'factory_budget'
    else:
        (workspace/'factory_budget').mkdir()
        alias = workspace/'factory_budget'/('b'*32)
    if os.name == 'nt':
        subprocess.run(['cmd','/c','mklink','/J',str(alias),str(destination)],check=True,capture_output=True)
    else: alias.symlink_to(destination,target_is_directory=True)
    with pytest.raises(ValueError,match='aliased'):
        execute_file(path,root,authorize_generation=True,seed=7)
    assert not calls and list(destination.iterdir()) == []


def test_existing_still_is_never_regenerated(box):
    from PIL import Image
    root, prepare, calls, *_ = box
    path, request, _ = prepare('NONPIXEL')
    image = root/'existing.png'
    Image.new('RGB',(64,64),(10,30,50)).save(image)
    brief = json.loads((root/'brief.json').read_text())
    parent = save(root/'parent.json', {'project_id':'test_project','output_class':'NONPIXEL_IMAGE',
        'asset_brief':brief,'outputs':[str(image)],'status':'CANDIDATE_READY_REVIEW_REQUIRED'})
    request['source'] = {'kind':'EXISTING_RUN','manifest_ref':str(parent),'manifest_sha256':digest(parent),
        'images':[{'path':str(image),'sha256':digest(image),'role':'IDENTITY_PRIMARY'}]}
    save(path, request)
    before = digest(parent)
    with pytest.raises(ValueError,match='SOURCE_READ_ONLY'):
        execute_file(path,root,authorize_generation=True,seed=7)
    assert not calls and not (root/'workspace').exists() and digest(parent) == before


def test_explicit_empty_roots_fail_closed(box):
    root, prepare, calls, *_ = box
    path, *_ = prepare()
    with pytest.raises(ValueError,match='Configured roots'):
        execute_file(path,root,authorize_generation=True,seed=7,allowed_roots=[])
    assert not calls and not (root/'workspace').exists()
