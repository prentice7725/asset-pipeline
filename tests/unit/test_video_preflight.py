"""Synthetic source/install contracts; never model generation or real approvals."""
import json
import shutil
from pathlib import Path

import pytest
import yaml
from PIL import Image

from assetpipe.factory.provenance import fingerprint
from assetpipe.providers.video import preflight_file, prepare_file, inspect_prepared

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def case(tmp_path, monkeypatch):
    root = tmp_path / 'project'
    root.mkdir()
    shutil.copytree(ROOT / 'config', root / 'config')
    images = []
    for index, role in enumerate(['IDENTITY_PRIMARY', 'ALTERNATE_VIEW', 'POSE_ANCHOR']):
        path = root / f'input{index}.png'
        Image.new('RGB', (64, 64), (50 * index, 20, 70)).save(path)
        images.append({'path': path.name, 'sha256': fingerprint(path), 'role': role,
                       'ownership': 'SYNTHETIC_TEST_ONLY', 'license': 'SYNTHETIC_TEST_ONLY'})
    request = {'factory_contract_version': 1, 'factory_line': 'REFERENCE_MOTION',
               'output_mode': 'IMAGE_TO_SPRITE', 'project_id': 'fixture', 'asset_id': 'subject',
               'source': {'kind': 'EXTERNAL_IMAGES', 'images': images[:1]},
               'motion': {'action': 'walk', 'fps': 24, 'duration_seconds': 56 / 24,
                          'target_frames': 56, 'background_policy': 'PRESERVE_OR_REVIEW',
                          'workflow_id': 'nonpixel_motion_contract'}}
    path = root / 'request.json'

    def save(value=request):
        path.write_text(json.dumps(value), encoding='utf-8')
        return path

    # Any accidental upload, queue, download, poll or connection is a test failure.
    def forbidden(*args, **kwargs):
        raise AssertionError('Offline preflight reached provider execution')
    from assetpipe._ported.comfy_bridge.client import ComfyClient
    for method in ['upload_image', 'queue_prompt', 'wait_for_outputs', 'download_asset', 'check_connection']:
        monkeypatch.setattr(ComfyClient, method, forbidden)
    save()
    return root, path, request, images, save


@pytest.mark.parametrize('count', [1, 2, 3])
def test_counts_are_bound_without_claiming_supported_consumption(case, count):
    root, path, request, images, save = case
    request['source']['images'] = images[:count]
    save()
    result = preflight_file(path, root)
    assert result['status'] == 'BLOCKED'
    assert result['generation_allowed'] is False
    assert result['dispatches'] == result['budget_reservations'] == result['uploads'] == 0
    assert result['reference_consumption'] == 'NOT_VERIFIED'
    assert [item['role'] for item in result['references']] == [item['role'] for item in images[:count]]
    assert [item['order'] for item in result['references']] == list(range(count))
    assert 'REFERENCE_CAPABILITY_NOT_VERIFIED' in {item['code'] for item in result['issues']}
    assert 'MOTION_PROMPT_PROFILE_MISSING' in {item['code'] for item in result['issues']}
    assert not (root / 'workspace').exists()


def test_prepare_and_inspect_preserve_exact_inputs_and_cannot_be_approved(case):
    root, path, request, images, save = case
    request['source']['images'] = images
    save()
    original = {p: fingerprint(p) for p in [path, *[root / i['path'] for i in images]]}
    manifest = prepare_file(path, 'workspace/motion', root)
    result = inspect_prepared(manifest.parent, root)
    assert result['status'] == 'PREPARED_BLOCKED'
    assert result['review_state'] == 'REVIEW_REQUIRED'
    assert result['generation_allowed'] is result['game_ready'] is False
    assert len(result['copied_references']) == 3
    for item in result['copied_references']:
        assert fingerprint(Path(item['preserved_path'])) == item['sha256']
    assert original == {p: fingerprint(p) for p in original}
    assert not (root / 'workspace/factory_budget').exists()
    assert not (manifest.parent / 'workflow.json').exists()
    with pytest.raises(FileExistsError):
        prepare_file(path, 'workspace/motion', root)


@pytest.mark.parametrize('drift', ['request', 'image', 'configuration', 'copy', 'role', 'review'])
def test_prepared_drift_never_passes_inspection(case, drift):
    root, path, request, images, save = case
    manifest = prepare_file(path, 'workspace/motion', root)
    record = json.loads(manifest.read_text())
    if drift == 'request':
        request['motion']['action'] = 'idle'
        save()
    if drift == 'image':
        (root / images[0]['path']).write_bytes(b'changed')
    if drift == 'configuration':
        with (root / 'config/pipeline.yaml').open('a') as stream:
            stream.write('\n# configuration changed\n')
    if drift == 'copy':
        Path(record['copied_references'][0]['preserved_path']).write_bytes(b'changed')
    if drift == 'role':
        record['copied_references'][0]['role'] = 'START_FRAME'
        manifest.write_text(json.dumps(record))
    if drift == 'review':
        record['generation_allowed'] = True
        manifest.write_text(json.dumps(record))
    with pytest.raises(ValueError):
        inspect_prepared(manifest.parent, root)


def test_stale_source_before_prepare_does_not_create_run(case):
    root, path, request, images, save = case
    (root / images[0]['path']).write_bytes(b'changed')
    with pytest.raises(ValueError, match='FACTORY_SOURCE_CHANGED'):
        prepare_file(path, 'workspace/motion', root)
    assert not (root / 'workspace').exists()


@pytest.mark.parametrize('workflow_id', [None, 'missing', 'minimax_character_motion_reference', 'krea2_base'])
def test_explicit_video_workflow_is_required(case, workflow_id):
    root, path, request, images, save = case
    request['motion'].pop('workflow_id')
    if workflow_id:
        request['motion']['workflow_id'] = workflow_id
    save()
    with pytest.raises(ValueError, match='MOTION_WORKFLOW_'):
        preflight_file(path, root)


@pytest.mark.parametrize('output', ['src/run', 'config/run', 'workspace', '../outside'])
def test_output_boundary_blocks_before_creation(case, output):
    root, path, request, images, save = case
    with pytest.raises(ValueError):
        prepare_file(path, output, root)
    assert not (root / 'src/run').exists()


def test_empty_roots_are_not_defaulted(case):
    root, path, *_ = case
    with pytest.raises(ValueError, match='nonempty'):
        preflight_file(path, root, allowed_roots=[])


def test_installation_inventory_never_becomes_capability_verification(case, monkeypatch):
    from assetpipe._ported.comfy_bridge.client import ComfyClient
    from assetpipe._ported.comfy_bridge.workflow_loader import load_workflow
    root, path, *_ = case
    graph = load_workflow('deno_minimax_h3_r2v_8step', root / 'config/workflows')
    # Exact node names and all model filenames are present; consumption is still unverified.
    monkeypatch.setattr(ComfyClient, 'check_connection', lambda self: {'system': {'comfyui_version': 'SYNTHETIC'}})
    monkeypatch.setattr(ComfyClient, '_json', lambda self, path: {n['class_type']: {'input': {}} for n in graph.api_prompt.values()})
    from assetpipe.registry import load_registry
    models = load_registry(root)['nonpixel_motion_contract']['models']
    monkeypatch.setattr(ComfyClient, 'list_models', lambda self, folder: models[folder])
    report = preflight_file(path, root, inspect_installation=True)
    assert report['installation']['status'] == 'INVENTORY_ONLY'
    assert report['generation_allowed'] is False
    assert report['reference_consumption'] == 'NOT_VERIFIED'
    assert report['status'] == 'BLOCKED'


def test_unavailable_installation_reports_block_without_reservations(case, monkeypatch):
    from assetpipe._ported.comfy_bridge.client import ComfyClient
    root, path, *_ = case
    def unavailable(self):
        raise ConnectionError('SYNTHETIC unavailable backend')
    monkeypatch.setattr(ComfyClient, 'check_connection', unavailable)
    report = preflight_file(path, root, inspect_installation=True)
    assert report['installation']['status'] == 'UNAVAILABLE'
    assert 'COMFYUI_UNAVAILABLE' in {issue['code'] for issue in report['issues']}
    assert not (root / 'workspace').exists()


def test_remote_server_is_rejected_before_connection(case):
    root, path, *_ = case
    settings = root / 'config/pipeline.yaml'
    data = yaml.safe_load(settings.read_text())
    data['comfyui']['base_url'] = 'http://example.com:8188'
    settings.write_text(yaml.safe_dump(data))
    with pytest.raises(ValueError, match='MOTION_LOCAL_SERVER_REQUIRED'):
        preflight_file(path, root, inspect_installation=True)


def test_failed_copy_preserves_partial_run_with_failed_state(case, monkeypatch):
    root, path, *_ = case
    def fail(*args):
        raise OSError('SYNTHETIC copy failure')
    monkeypatch.setattr('assetpipe.providers.video.shutil.copyfile', fail)
    with pytest.raises(OSError, match='copy failure'):
        prepare_file(path, 'workspace/motion', root)
    manifest = root / 'workspace/motion/prepared_motion.json'
    result = json.loads(manifest.read_text())
    assert result['status'] == 'FAILED'
    with pytest.raises(ValueError, match='MOTION_PREPARATION_INVALID'):
        inspect_prepared(manifest.parent, root)


def test_cli_preflight_never_sends_generation(case, capsys):
    from assetpipe.cli import main
    root, path, *_ = case
    assert main(['--root', str(root), 'motion-preflight', '--request', str(path)]) == 0
    assert json.loads(capsys.readouterr().out)['generation_allowed'] is False


def test_live_binding_and_length_constraints_are_reported(case, monkeypatch):
    from assetpipe._ported.comfy_bridge.client import ComfyClient
    from assetpipe._ported.comfy_bridge.workflow_loader import load_workflow
    root, path, request, images, save = case
    request['motion'].update(target_frames=53, duration_seconds=53 / 24)
    save()
    graph = load_workflow('deno_minimax_h3_r2v_8step', root / 'config/workflows')
    info = {}
    for node in graph.api_prompt.values():
        info[node['class_type']] = {'input': {'required': {name: ['ANY', {}] for name in node['inputs']}}}
    binding = graph.bindings['length']
    node_class = graph.api_prompt[binding['node']]['class_type']
    info[node_class]['input']['required'][binding['input']] = ['INT', {'min': 5, 'max': 240, 'step': 17}]
    image_binding = graph.bindings['input_image']
    info[graph.api_prompt[image_binding['node']]['class_type']]['input']['required'].pop(image_binding['input'])
    monkeypatch.setattr(ComfyClient, 'check_connection', lambda self: {'system': {}})
    monkeypatch.setattr(ComfyClient, '_json', lambda self, path: info)
    monkeypatch.setattr(ComfyClient, 'list_models', lambda self, folder: [])
    report = preflight_file(path, root, inspect_installation=True)
    codes = {issue['code'] for issue in report['issues']}
    assert {'MOTION_BINDING_UNAVAILABLE', 'MOTION_FRAME_COUNT_UNSUPPORTED', 'MOTION_MODEL_MISSING'} <= codes
    assert report['generation_allowed'] is False


def test_source_outside_allowed_roots_is_rejected(case, tmp_path):
    root, path, request, images, save = case
    outside = tmp_path / 'outside.png'
    Image.new('RGB', (64, 64), 'green').save(outside)
    request['source']['images'][0].update(path=str(outside), sha256=fingerprint(outside))
    save()
    with pytest.raises(ValueError, match='outside configured roots'):
        preflight_file(path, root)


def test_prepared_copy_cannot_redirect_to_a_source_image(case):
    root, path, request, images, save = case
    manifest = prepare_file(path, 'workspace/motion', root)
    record = json.loads(manifest.read_text())
    record['copied_references'][0]['preserved_path'] = str(root / images[0]['path'])
    manifest.write_text(json.dumps(record))
    with pytest.raises(ValueError, match='MOTION_REFERENCE_BINDING_INVALID'):
        inspect_prepared(manifest.parent, root)
