"""Synthetic one-shot ComfyUI calls plus real local video decoding; zero model calls."""
import copy
import json
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock

import pytest
import yaml
from PIL import Image

from assetpipe.brief import make
from assetpipe.factory.provenance import fingerprint
from assetpipe.providers.video import prepare_file
from assetpipe.providers.video.executor import execution_plan, execute_prepared
from assetpipe.registry import load_registry
from assetpipe._ported.comfy_bridge.workflow_loader import load_workflow

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def case(tmp_path, monkeypatch):
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        pytest.skip('Real codec verification needs local FFmpeg/FFprobe')
    root = tmp_path / 'repo'
    root.mkdir()
    shutil.copytree(ROOT / 'config', root / 'config')
    model_root = root / 'workspace/models'
    workflow = load_registry(root)['nonpixel_motion_contract']
    models = []
    for folder, names in workflow['models'].items():
        for name in names:
            file = model_root / folder / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(b'SYNTHETIC MODEL; NEVER LOADED: ' + name.encode())
            models.append({'folder': folder, 'name': name, 'sha256': fingerprint(file)})
    config_path = root / 'config/pipeline.yaml'
    config = yaml.safe_load(config_path.read_text())
    config['video_research'] = {'enabled': True, 'model_roots': [str(model_root)]}
    config_path.write_text(yaml.safe_dump(config))
    parent = root / 'workspace/parent'
    parent.mkdir()
    image = parent / 'source.png'
    Image.new('RGB', (64, 64), 'blue').save(image)
    brief = make(asset_id='parent', output_class='NONPIXEL_IMAGE', prompt='A synthetic pilot fixture')
    brief['project_id'] = 'test'
    brief['identity']['canonical_traits'] = ['blue uniform', 'exactly one left shoulder badge']
    brief['forbidden_elements'] = ['extra equipment']
    manifest = parent / 'run_manifest.json'
    manifest.write_text(json.dumps({'run_id': 'static', 'project_id': 'test', 'asset_id': 'parent',
                                    'output_class': 'NONPIXEL_IMAGE', 'asset_brief': brief,
                                    'status': 'CANDIDATE_READY_REVIEW_REQUIRED', 'outputs': [str(image)]}))
    request = root / 'request.json'
    request.write_text(json.dumps({'factory_contract_version': 1, 'factory_line': 'NONPIXEL',
        'output_mode': 'IMAGE_TO_SPRITE', 'project_id': 'test', 'asset_id': 'motion_child',
        'source': {'kind': 'EXISTING_RUN', 'manifest_ref': str(manifest), 'manifest_sha256': fingerprint(manifest),
                   'images': [{'path': str(image), 'sha256': fingerprint(image), 'role': 'IDENTITY_PRIMARY'}]},
        'image': {'style_source': 'SYNTHETIC_TEST_NO_ART_APPROVAL'},
        'motion': {'action': 'walk', 'fps': 24, 'duration_seconds': 5 / 24, 'target_frames': 5,
                   'background_policy': 'PRESERVE_OR_REVIEW', 'workflow_id': 'nonpixel_motion_contract'}}))
    run = prepare_file(request, 'workspace/prepared', root).parent
    video = tmp_path / 'synthetic.mp4'
    subprocess.run([shutil.which('ffmpeg'), '-v', 'error', '-f', 'lavfi', '-i',
                    'color=c=blue:s=64x64:r=24', '-frames:v', '5', '-c:v', 'libx264',
                    '-pix_fmt', 'yuv420p', str(video)], check=True, capture_output=True, timeout=30)
    source_graph = load_workflow('deno_minimax_h3_r2v_8step', root / 'config/workflows')
    info = {}
    for node in source_graph.api_prompt.values():
        slots = {}
        for key, value in node['inputs'].items():
            kind = 'BOOLEAN' if type(value) is bool else 'INT' if type(value) is int else 'FLOAT' if type(value) is float else 'STRING' if isinstance(value, str) else 'ANY'
            slots[key] = [kind, {}]
        info[node['class_type']] = {'input': {'required': slots}}
    length = source_graph.bindings['length']
    info[source_graph.api_prompt[length['node']]['class_type']]['input']['required'][length['input']] = ['INT', {'min': 5, 'max': 240, 'step': 17}]
    state = {'uploads': 0, 'queues': 0, 'downloads': 0, 'mode': None, 'graph': None, 'lock': Lock()}

    class FakeClient:
        def __init__(self, *args, **kwargs): pass
        def check_connection(self):
            if state['mode'] == 'offline': raise ConnectionError('SYNTHETIC unavailable')
            return {'system': {'comfyui_version': 'SYNTHETIC_TEST_ONLY'}}
        def list_models(self, folder): return workflow['models'][folder]
        def _json(self, path):
            if path.startswith('/object_info/'):
                name = path.split('/')[-1]
                return {name: info[name]} if name in info else {}
            if path == '/object_info': raise AssertionError('Global catalog must not be queried')
            graph = copy.deepcopy(state['graph'])
            if state['mode'] == 'history_mismatch': graph['142']['inputs']['image_paths'] = 'wrong.png'
            return {'synthetic-prompt': {'prompt': [0, 'synthetic-prompt', graph, {}, ['144']]}}
        def upload_image(self, path):
            with state['lock']: state['uploads'] += 1
            if state['mode'] == 'upload': raise ValueError('SYNTHETIC upload failure')
            return 'synthetic_unique_reference.png'
        def queue_prompt(self, graph, client_id):
            with state['lock']: state['queues'] += 1
            state['graph'] = copy.deepcopy(graph)
            if state['mode'] == 'queue': raise TimeoutError('SYNTHETIC queue response lost')
            return 'synthetic-prompt'
        def wait_for_outputs(self, prompt_id, output_nodes):
            if state['mode'] == 'poll': raise TimeoutError('SYNTHETIC generation timeout')
            identifier = state['graph']['144']['inputs']['filename_prefix'].split('/')[-1]
            asset = {'filename': identifier + '_00001.mp4', 'subfolder': 'assetpipe_motion', 'type': 'output'}
            if state['mode'] == 'stale_output': asset['filename'] = 'another_run_00001.mp4'
            return [asset, asset] if state['mode'] == 'ambiguous' else [asset]
        def download_asset(self, asset, destination):
            state['downloads'] += 1
            shutil.copyfile(video, destination)
            if state['mode'] == 'corrupt': destination.write_bytes(b'corrupt video')
    monkeypatch.setattr('assetpipe.providers.video.ComfyClient', FakeClient)
    monkeypatch.setattr('assetpipe.providers.video.executor.ComfyClient', FakeClient)
    plan = execution_plan(run, root, seed=7, width=64, height=64)
    auth = root / 'authorization.json'
    value = {'schema_version': 1, 'kind': 'MOTION_ONE_REQUEST_AUTHORIZATION',
             'authorization_id': 'a' * 32, 'execution_plan_sha256': plan['execution_plan_sha256'],
             'project_id': 'test', 'asset_id': 'motion_child', 'purpose': plan['purpose'],
             'max_requests': 1, 'authorized_by': 'SYNTHETIC_TEST_ONLY',
             'reason': 'SYNTHETIC FIXTURE; NOT HUMAN CONSENT', 'models': models}
    auth.write_text(json.dumps(value))
    return dict(root=root, run=run, request=request, parent=manifest, image=image, auth=auth,
                authorization=value, plan=plan, state=state, info=info, model_root=model_root)


def execute(case, **kwargs):
    return execute_prepared(case['run'], case['auth'], case['root'], seed=7, width=64, height=64,
                            authorize_generation=True, **kwargs)


def factory_motion_job(case):
    from assetpipe.manifests import write
    path=case['root']/'job.json'
    write(path,{'schema_version':1,'kind':'FACTORY_MOTION_JOB',
        'request_ref':str(case['request']),'request_sha256':fingerprint(case['request']),
        'input':{'kind':'PREPARED_GENERATION','run_ref':str(case['run']),'seed':7,'width':64,'height':64},
        'recipe':{'schema_version':1,'selection':{'start_frame':1,'end_frame':5},
                  'alpha':{'method':'PRESERVE'}}})
    return path


@pytest.mark.parametrize('entrypoint', ['factory', 'create'])
def test_factory_motion_generation_delegates_single_budget_and_exports(case, entrypoint):
    from assetpipe.factory.motion import plan_job,run_job,inspect_job
    job=factory_motion_job(case)
    root=case['root']
    plan=plan_job(job,root)
    assert plan['generation_plan']==case['plan']
    output=root/'workspace/factory_child'
    def execute(target):
        if entrypoint == 'create':
            from assetpipe.pipelines import create
            return create(None,root,target,motion_job=job,motion_plan_sha256=plan['plan_sha256'],
                          authorization=case['auth'],authorize_generation=True)
        return run_job(job,plan['plan_sha256'],target,root,authorization=case['auth'],authorize_generation=True)
    receipt=execute(output)
    assert inspect_job(output,fingerprint(receipt),root)['generation_requests']==1
    assert case['state']['uploads']==case['state']['queues']==1
    with pytest.raises(ValueError,match='MOTION_BUDGET_ALREADY_RESERVED'):
        execute(root/'workspace/another_child')
    assert case['state']['uploads']==case['state']['queues']==1


def test_factory_motion_no_consent_never_dispatches(case):
    from assetpipe.factory.motion import plan_job,run_job
    job=factory_motion_job(case)
    root=case['root']
    plan=plan_job(job,root)
    with pytest.raises(ValueError,match='FACTORY_MOTION_GENERATION_NOT_AUTHORIZED'):
        run_job(job,plan['plan_sha256'],root/'workspace/no_consent',root)
    assert not (root/'workspace/no_consent').exists()
    assert case['state']['uploads']==case['state']['queues']==0


def test_factory_motion_disabled_research_cannot_be_enabled_by_job(case):
    from assetpipe.factory.motion import plan_job,run_job
    root=case['root']
    settings=root/'config/pipeline.yaml'
    config=yaml.safe_load(settings.read_text())
    config['video_research']['enabled']=False
    settings.write_text(yaml.safe_dump(config))
    case['run']=prepare_file(case['request'],'workspace/disabled_prepared',root).parent
    job=factory_motion_job(case)
    plan=plan_job(job,root)
    auth=case['authorization']
    auth['execution_plan_sha256']=plan['generation_plan']['execution_plan_sha256']
    case['auth'].write_text(json.dumps(auth))
    with pytest.raises(ValueError,match='MOTION_RESEARCH_DISABLED'):
        run_job(job,plan['plan_sha256'],root/'workspace/blocked',root,
                authorization=case['auth'],authorize_generation=True)
    assert case['state']['uploads']==case['state']['queues']==0
    assert not (root/'workspace/factory_budget').exists()


def test_factory_motion_rejects_prepared_input_for_another_request(case):
    from assetpipe.factory.motion import plan_job
    root=case['root']
    request=json.loads(case['request'].read_text())
    request['asset_id']='different_child'
    path=root/'another_request.json'
    path.write_text(json.dumps(request))
    job=factory_motion_job(case)
    value=json.loads(job.read_text())
    value.update(request_ref=str(path),request_sha256=fingerprint(path))
    job.write_text(json.dumps(value))
    with pytest.raises(ValueError,match='FACTORY_MOTION_PREPARED_REQUEST_MISMATCH'):
        plan_job(job,root)
    assert case['state']['uploads']==case['state']['queues']==0


def test_full_synthetic_probe_connects_to_real_video_packaging(case):
    before = {p: fingerprint(p) for p in [case['parent'], case['image'], case['request']]}
    plan = case['plan']
    assert all(text in plan['compiled_prompt']['positive'] for text in ['blue uniform', 'left shoulder badge', 'extra equipment', 'walk'])
    assert plan['compiled_prompt']['negative_mode'] == 'NATURAL_LANGUAGE_INSTRUCTION'
    result = execute(case)
    receipt = json.loads(result.read_text())
    assert receipt['status'] == 'CANDIDATE_REVIEW_REQUIRED'
    assert receipt['review_state'] == 'REVIEW_REQUIRED' and receipt['game_ready'] is False
    assert receipt['reference_role_semantics'] == 'NOT_VERIFIED'
    assert receipt['reference_binding'] == 'HISTORY_GRAPH_MATCHED'
    assert receipt['queue_attempts'] == 1
    package = json.loads(Path(receipt['package_manifest_path']).read_text())
    assert package['qa']['frame_count'] == 5
    assert package['review_state'] == 'REVIEW_REQUIRED'
    assert package['provider_input_consumption'] == 'NOT_VERIFIED'
    assert before == {p: fingerprint(p) for p in before}
    with pytest.raises(ValueError, match='MOTION_BUDGET_ALREADY_RESERVED'):
        execute(case)
    assert case['state']['uploads'] == case['state']['queues'] == case['state']['downloads'] == 1


@pytest.mark.parametrize('field,value', [('max_requests', 2), ('max_requests', True),
    ('project_id', 'another'), ('purpose', 'PRODUCTION'), ('execution_plan_sha256', '0' * 64),
    ('authorization_id', '../outside')])
def test_invalid_budget_never_uploads_or_reserves(case, field, value):
    record = case['authorization']
    record[field] = value
    case['auth'].write_text(json.dumps(record))
    with pytest.raises(ValueError, match='MOTION_AUTHORIZATION_'):
        execute(case)
    assert case['state']['uploads'] == case['state']['queues'] == 0
    assert not (case['root'] / 'workspace/factory_budget').exists()


def test_explicit_execution_consent_is_required(case):
    with pytest.raises(ValueError, match='MOTION_GENERATION_NOT_AUTHORIZED'):
        execute_prepared(case['run'], case['auth'], case['root'], seed=7, width=64, height=64)
    assert case['state']['uploads'] == case['state']['queues'] == 0


@pytest.mark.parametrize('mode', ['upload', 'queue', 'poll', 'history_mismatch', 'stale_output', 'ambiguous', 'corrupt'])
def test_attempt_failure_consumes_budget_and_preserves_parent(case, mode):
    before = fingerprint(case['parent'])
    case['state']['mode'] = mode
    with pytest.raises(Exception): execute(case)
    receipt_path = case['root'] / ('workspace/factory_budget/' + 'a' * 32 + '/motion_execution.json')
    receipt = json.loads(receipt_path.read_text())
    assert receipt['status'] == 'FAILED'
    assert receipt['game_ready'] is False
    assert fingerprint(case['parent']) == before
    if mode == 'corrupt': assert (receipt_path.parent / 'original.mp4').exists()
    case['state']['mode'] = None
    counts = case['state']['uploads'], case['state']['queues']
    with pytest.raises(ValueError, match='MOTION_BUDGET_ALREADY_RESERVED'): execute(case)
    assert counts == (case['state']['uploads'], case['state']['queues'])


@pytest.mark.parametrize('mode', ['hash', 'missing', 'empty', 'extra', 'duplicate'])
def test_model_contract_blocks_before_budget(case, mode):
    auth = case['authorization']
    if mode == 'hash': auth['models'][0]['sha256'] = '0' * 64
    if mode == 'missing': (case['model_root'] / auth['models'][0]['folder'] / auth['models'][0]['name']).unlink()
    if mode == 'empty': auth['models'] = []
    if mode == 'extra': auth['models'].append({'folder': 'vae', 'name': 'wrong', 'sha256': '0' * 64})
    if mode == 'duplicate': auth['models'][1] = auth['models'][0]
    case['auth'].write_text(json.dumps(auth))
    with pytest.raises(ValueError, match='MOTION_MODEL_'): execute(case)
    assert not (case['root'] / 'workspace/factory_budget').exists()
    assert case['state']['uploads'] == case['state']['queues'] == 0


def test_backend_unavailable_does_not_reserve_budget(case):
    case['state']['mode'] = 'offline'
    with pytest.raises(ValueError, match='MOTION_PREFLIGHT_BLOCKED'): execute(case)
    assert not (case['root'] / 'workspace/factory_budget').exists()


def test_concurrent_jobs_share_atomic_reservation(case):
    def attempt():
        try: return execute(case)
        except ValueError as error: return str(error)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))
    assert sum(isinstance(result, Path) for result in results) == 1
    assert any('MOTION_BUDGET_ALREADY_RESERVED' in str(result) for result in results)
    assert case['state']['queues'] == 1


@pytest.mark.parametrize('width,height', [(63, 64), (64, True), (768, 768)])
def test_bad_or_oversized_atlas_dimensions_are_rejected(case, width, height):
    # For the atlas limit case increase the bound request before fresh preparation.
    if width == 768:
        value = json.loads(case['request'].read_text())
        value['motion'].update(target_frames=56, duration_seconds=56 / 24)
        case['request'].write_text(json.dumps(value))
        run = prepare_file(case['request'], 'workspace/larger', case['root']).parent
    else: run = case['run']
    with pytest.raises(ValueError, match='MOTION_(DIMENSIONS_INVALID|ATLAS_LIMIT)'):
        execution_plan(run, case['root'], seed=7, width=width, height=height)


def test_source_change_during_upload_cannot_queue(case, monkeypatch):
    import assetpipe.providers.video.executor as module
    original = module.ComfyClient.upload_image
    def changed(self, path):
        uploaded = original(self, path)
        case['image'].write_bytes(b'changed')
        return uploaded
    monkeypatch.setattr(module.ComfyClient, 'upload_image', changed)
    with pytest.raises(ValueError, match='FACTORY_SOURCE_CHANGED'): execute(case)
    assert case['state']['uploads'] == 1 and case['state']['queues'] == 0


def test_execution_is_disabled_by_default_in_repository():
    config = yaml.safe_load((ROOT / 'config/pipeline.yaml').read_text())
    assert config['video_research'] == {'enabled': False, 'model_roots': []}
    assert load_registry(ROOT)['nonpixel_motion_contract']['status'] == 'EXPERIMENTAL'


def test_valid_budget_does_not_enable_disabled_executor(case):
    config_path = case['root'] / 'config/pipeline.yaml'
    config = yaml.safe_load(config_path.read_text())
    config['video_research']['enabled'] = False
    config_path.write_text(yaml.safe_dump(config))
    case['run'] = prepare_file(case['request'], 'workspace/disabled', case['root']).parent
    plan = execution_plan(case['run'], case['root'], seed=7, width=64, height=64)
    case['authorization']['execution_plan_sha256'] = plan['execution_plan_sha256']
    case['auth'].write_text(json.dumps(case['authorization']))
    with pytest.raises(ValueError, match='MOTION_RESEARCH_DISABLED'): execute(case)
    assert case['state']['uploads'] == case['state']['queues'] == 0
    assert not (case['root'] / 'workspace/factory_budget').exists()


def test_compiler_preserves_required_project_contract_gate(case):
    parent = json.loads(case['parent'].read_text())
    parent['asset_brief']['project_contract_required'] = True
    case['parent'].write_text(json.dumps(parent))
    request = json.loads(case['request'].read_text())
    request['source']['manifest_sha256'] = fingerprint(case['parent'])
    case['request'].write_text(json.dumps(request))
    run = prepare_file(case['request'], 'workspace/locked', case['root']).parent
    with pytest.raises(ValueError, match='PROJECT_SOT_UNREGISTERED'):
        execution_plan(run, case['root'], seed=7, width=64, height=64)
    assert case['state']['uploads'] == case['state']['queues'] == 0


def test_changed_seed_cannot_reuse_bound_budget(case):
    with pytest.raises(ValueError, match='MOTION_AUTHORIZATION_MISMATCH'):
        execute_prepared(case['run'], case['auth'], case['root'], seed=8, width=64, height=64,
                         authorize_generation=True)
    assert not (case['root'] / 'workspace/factory_budget').exists()


@pytest.mark.parametrize('count', [2, 3])
def test_probe_never_drops_extra_references(case, count):
    parent = json.loads(case['parent'].read_text())
    request = json.loads(case['request'].read_text())
    for index in range(1, count):
        image = case['parent'].parent / f'view{index}.png'
        Image.new('RGB', (64, 64), (index * 50, 100, 20)).save(image)
        parent['outputs'].append(str(image))
        request['source']['images'].append({'path': str(image), 'sha256': fingerprint(image),
                                           'role': ['ALTERNATE_VIEW', 'POSE_ANCHOR'][index - 1]})
    case['parent'].write_text(json.dumps(parent))
    request.update(factory_line='REFERENCE_MOTION')
    request.pop('image')
    request['source']['manifest_sha256'] = fingerprint(case['parent'])
    case['request'].write_text(json.dumps(request))
    run = prepare_file(case['request'], 'workspace/multiple', case['root']).parent
    with pytest.raises(ValueError, match='MOTION_PROBE_SCOPE'):
        execution_plan(run, case['root'], seed=7, width=64, height=64)
    record = json.loads((run / 'prepared_motion.json').read_text())
    assert len(record['copied_references']) == count
    assert case['state']['uploads'] == case['state']['queues'] == 0


def test_coherent_request_edit_during_generation_cannot_rebind_video(case, monkeypatch):
    import assetpipe.providers.video.executor as module
    download = module.ComfyClient.download_asset
    def changed(self, asset, destination):
        download(self, asset, destination)
        Image.new('RGB', (64, 64), 'green').save(case['image'])
        value = json.loads(case['request'].read_text())
        value['source']['images'][0]['sha256'] = fingerprint(case['image'])
        case['request'].write_text(json.dumps(value))
    monkeypatch.setattr(module.ComfyClient, 'download_asset', changed)
    with pytest.raises(ValueError, match='MOTION_SOURCE_CHANGED'): execute(case)
    folder = case['root'] / ('workspace/factory_budget/' + 'a' * 32)
    assert (folder / 'original.mp4').exists()
    assert not (folder / 'package').exists()
    assert json.loads((folder / 'motion_execution.json').read_text())['status'] == 'FAILED'


def test_registry_cannot_omit_model_hash_coverage(case):
    file = case['root'] / 'config/workflow_registry.yaml'
    registry = yaml.safe_load(file.read_text())
    registry['workflows']['nonpixel_motion_contract']['models']['loras'] = []
    file.write_text(yaml.safe_dump(registry))
    run = prepare_file(case['request'], 'workspace/missing-model', case['root']).parent
    with pytest.raises(ValueError, match='MOTION_MODEL_DECLARATION_MISMATCH'):
        execution_plan(run, case['root'], seed=7, width=64, height=64)
    assert case['state']['uploads'] == case['state']['queues'] == 0


@pytest.mark.parametrize('mutation,valid', [('none', True), ('pixel_format', False), ('unknown', False), ('crf', False)])
def test_vhs_dynamic_codec_widgets_are_strictly_validated(mutation, valid):
    from assetpipe.providers.video.executor import _validate_graph
    graph = {'1': {'class_type': 'VHS_VideoCombine', 'inputs': {
        'format': 'video/h264-mp4', 'pix_fmt': 'yuv420p', 'crf': 15, 'save_metadata': True}}}
    info = {'VHS_VideoCombine': {'input': {'required': {
        'format': [['video/h264-mp4'], {'formats': {'video/h264-mp4': [
            ['pix_fmt', ['yuv420p', 'yuv420p10le']],
            ['crf', 'INT', {'min': 0, 'max': 100, 'step': 1}],
            ['save_metadata', 'BOOLEAN', {'default': True}]]}}]}}}}
    if mutation == 'pixel_format': graph['1']['inputs']['pix_fmt'] = 'unsupported'
    if mutation == 'unknown': graph['1']['inputs']['undeclared_widget'] = True
    if mutation == 'crf': graph['1']['inputs']['crf'] = 101
    if valid:
        _validate_graph(graph, info)
    else:
        with pytest.raises(ValueError): _validate_graph(graph, info)
