"""Real local codec/packing tests with synthetic fixtures; zero model calls."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from assetpipe.factory.provenance import fingerprint
from assetpipe.motion.package import package_video


def test_published_factory_motion_schema_matches_validator():
    from assetpipe.factory.motion import SCHEMA
    root=Path(__file__).resolve().parents[2]
    assert json.loads((root/'schemas/factory_motion_job_v1.schema.json').read_text())==SCHEMA


@pytest.fixture
def case(tmp_path):
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        pytest.skip('Local FFmpeg/FFprobe required; no external-tool PASS inferred')
    frames = tmp_path / 'input'
    frames.mkdir()
    for index in range(6):
        image = Image.new('RGB', (64, 64), 'white')
        draw = ImageDraw.Draw(image)
        # Repeated poses deliberately retain their timeline slots.
        draw.rectangle((16 + index // 2, 12, 40 + index // 2, 56), fill='blue')
        draw.line((18, 14, 38, 54), fill='yellow', width=2)
        image.save(frames / f'{index:02d}.png')
    video = tmp_path / 'motion.avi'
    subprocess.run([shutil.which('ffmpeg'), '-v', 'error', '-framerate', '6',
                    '-i', str(frames / '%02d.png'), '-c:v', 'ffv1', str(video)],
                   capture_output=True, check=True, timeout=30)
    source = frames / '00.png'
    request = {'factory_contract_version': 1, 'factory_line': 'REFERENCE_MOTION',
               'output_mode': 'IMAGE_TO_SPRITE', 'project_id': 'test', 'asset_id': 'clip',
               'source': {'kind': 'EXTERNAL_IMAGES', 'images': [{
                   'path': str(source), 'sha256': fingerprint(source), 'role': 'IDENTITY_PRIMARY',
                   'ownership': 'SYNTHETIC_TEST_FIXTURE', 'license': 'SYNTHETIC_TEST_FIXTURE'}]},
               'motion': {'action': 'test', 'fps': 6, 'duration_seconds': 1, 'target_frames': 6,
                          'background_policy': 'PRESERVE_OR_REVIEW'}}
    path = tmp_path / 'request.json'
    path.write_text(json.dumps(request), encoding='utf-8')
    return tmp_path, path, video, tmp_path / 'workspace/child', request


def run(case):
    root, request, video, output, _ = case
    return package_video(request, video, fingerprint(video), output, root)


def factory_job(case):
    from assetpipe.brief import make
    from assetpipe.manifests import write
    root,request,video,_,data=case
    image=root/'input/00.png'
    brief=make(asset_id='parent',output_class='NONPIXEL_IMAGE',prompt='synthetic fixture')
    brief['project_id']='test'
    parent=root/'parent.json'
    write(parent,{'asset_id':'parent','project_id':'test','output_class':'NONPIXEL_IMAGE',
                  'asset_brief':brief,'outputs':[str(image)]})
    data['factory_line']='NONPIXEL'
    data['image']={'style_source':'SYNTHETIC_TEST_ONLY'}
    data['source']={'kind':'EXISTING_RUN','manifest_ref':str(parent),'manifest_sha256':fingerprint(parent),
                    'images':[{'path':str(image),'sha256':fingerprint(image),'role':'IDENTITY_PRIMARY'}]}
    write(request,data)
    history=root/'historical.json'
    write(history,{'seed':7,'status':'HISTORICAL_TEST_ONLY','models':[{'path':'Z:/retired-model.safetensors'}]})
    value={'schema_version':1,'kind':'FACTORY_MOTION_JOB','request_ref':str(request),
        'request_sha256':fingerprint(request),
        'input':{'kind':'EXISTING_VIDEO','path':str(video),'sha256':fingerprint(video),
                 'generation_record':{'path':str(history),'sha256':fingerprint(history)}},
        'recipe':{'schema_version':2,'selection':{'start_frame':2,'end_frame':5},
                  'alpha':{'method':'EDGE_CONNECTED_WHITE','background_rgb':[255,255,255],'tolerance':32}}}
    job=root/'job.json'
    write(job,value)
    return job,value


def test_nonpixel_create_cli_runs_existing_job_and_preserves_parent(case, monkeypatch, capsys):
    from assetpipe.cli import main
    from assetpipe.factory.motion import plan_job, inspect_job
    root, _, video, output, _ = case
    job, _ = factory_job(case)
    parent = root / 'parent.json'
    before = {p: fingerprint(p) for p in [parent, video, root/'input/00.png']}
    def forbidden(*args, **kwargs):
        raise AssertionError('Offline continuation must not generate a still or video')
    monkeypatch.setattr('assetpipe.pipelines.nonpixel_image.run', forbidden)
    monkeypatch.setattr('assetpipe.providers.video.executor.execute_prepared', forbidden)
    plan = plan_job(job, root)
    assert main(['--root', str(root), 'create', '--type', 'nonpixel-animation',
                 '--motion-job', str(job), '--motion-plan-sha256', plan['plan_sha256'],
                 '--output', str(output)]) == 0
    capsys.readouterr()
    receipt = output/'factory_motion.json'
    assert inspect_job(output, fingerprint(receipt), root)['generation_requests'] == 0
    assert (output/'exports/godot/walk.tres').exists() or (output/'exports/walk.tres').exists()
    assert before == {p: fingerprint(p) for p in before}


@pytest.mark.parametrize('failure', ['stale_plan', 'generation_flag', 'decode_failure'])
def test_nonpixel_create_failure_preserves_still_and_stops(case, monkeypatch, failure):
    from assetpipe.pipelines import create
    from assetpipe.factory.motion import plan_job
    root, _, video, output, _ = case
    job, _ = factory_job(case)
    plan = plan_job(job, root)
    parent = root/'parent.json'
    before = {p: fingerprint(p) for p in [parent, video, root/'input/00.png']}
    def fail(*args, **kwargs):
        raise ValueError('DECODE_FAILED_FOR_TEST')
    if failure == 'decode_failure':
        monkeypatch.setattr('assetpipe.motion.package.package_video', fail)
    expected = {'stale_plan': 'FACTORY_MOTION_PLAN_CHANGED',
                'generation_flag': 'FACTORY_MOTION_REPLAY_DISALLOWS_GENERATION',
                'decode_failure': 'DECODE_FAILED_FOR_TEST'}[failure]
    with pytest.raises(ValueError, match=expected):
        create(None, root, output, motion_job=job,
               motion_plan_sha256='0'*64 if failure == 'stale_plan' else plan['plan_sha256'],
               authorize_generation=failure == 'generation_flag')
    assert before == {p: fingerprint(p) for p in before}
    assert not (output/'exports').exists()
    if failure == 'decode_failure':
        assert json.loads((output/'factory_motion.json').read_text())['status'] == 'FAILED'
    else:
        assert not output.exists()


@pytest.mark.parametrize('options', [
    ['--type', 'nonpixel-image', '--motion-job', 'missing.json'],
    ['--type', 'nonpixel-animation', '--motion-job', 'missing.json', '--prompt', 'override'],
    ['--type', 'nonpixel-animation', '--motion-job', 'missing.json', '--seed', '0'],
    ['--type', 'nonpixel-animation', '--motion-job', 'missing.json', '--asset-id', 'override'],
    ['--type', 'nonpixel-image', '--authorize-generation'],
    ['--type', 'nonpixel-animation', '--motion-job', 'missing.json'],
])
def test_nonpixel_create_rejects_ambiguous_or_incomplete_inputs_before_output(tmp_path, options):
    from assetpipe.cli import main
    output = tmp_path/'workspace/child'
    assert main(['--root', str(tmp_path), 'create', '--output', str(output), *options]) == 1
    assert not output.exists()


def test_factory_motion_replay_real_codec_recipe_export_and_inspect(case,monkeypatch):
    from assetpipe.factory.motion import plan_job,run_job,inspect_job
    root,request,video,output,_=case
    job,value=factory_job(case)
    def no_provider(*args,**kwargs): raise AssertionError('Offline replay must never call a provider')
    monkeypatch.setattr('assetpipe.providers.video.executor.execute_prepared',no_provider)
    before={p:fingerprint(p) for p in [request,video,root/'parent.json',root/'historical.json']}
    plan=plan_job(job,root)
    assert plan['dispatches']==plan['budget_reservations']==0
    receipt=run_job(job,plan['plan_sha256'],output,root)
    result=inspect_job(output,fingerprint(receipt),root)
    assert result['status']=='FACTORY_MOTION_INTEGRITY_PASS_REVIEW_REQUIRED'
    assert result['generation_requests']==0 and result['game_ready'] is False
    atlas=json.loads((output/'candidate/atlas.json').read_text())
    assert [r['original_source_frame_index'] for r in atlas['frames']]==[2,3,4,5]
    native=json.loads((output/'exports/phaser-animation.json').read_text())
    assert native['frameRate']==6 and len(native['frames'])==4
    placement=json.loads((output/'exports/placement.json').read_text())
    assert placement['godot']['offset']==[-32,-62]
    assert placement['phaser']['origin']==[.5,62/64]
    assert (output/'historical-generation.json').read_bytes()==(root/'historical.json').read_bytes()
    assert before=={p:fingerprint(p) for p in before}
    assert not (root/'workspace/factory_budget').exists()
    with pytest.raises(FileExistsError): run_job(job,plan['plan_sha256'],output,root)


@pytest.mark.parametrize('failure',['stale_plan','generation_flag','outside_workspace','changed_video','bad_alpha'])
def test_factory_motion_replay_gates_before_output(case,failure):
    from jsonschema import ValidationError
    from assetpipe.factory.motion import plan_job,run_job
    from assetpipe.manifests import write
    root,_,video,output,_=case
    job,value=factory_job(case)
    plan=plan_job(job,root)
    options={}
    digest=plan['plan_sha256']
    if failure=='stale_plan': digest='0'*64
    elif failure=='generation_flag': options['authorize_generation']=True
    elif failure=='outside_workspace': output=root/'src/no_artifacts'
    elif failure=='changed_video': video.write_bytes(b'changed')
    else:
        value['recipe']['alpha']['tolerance']=61
        write(job,value)
    errors={'stale_plan':'FACTORY_MOTION_PLAN_CHANGED',
            'generation_flag':'FACTORY_MOTION_REPLAY_DISALLOWS_GENERATION',
            'outside_workspace':'FACTORY_MOTION_OUTPUT_INVALID',
            'changed_video':'FACTORY_MOTION_VIDEO_CHANGED'}
    expected=ValidationError if failure=='bad_alpha' else ValueError
    with pytest.raises(expected,match=errors.get(failure)):
        run_job(job,digest,output,root,**options)
    assert not output.exists()
    assert not (root/'workspace/factory_budget').exists()


@pytest.mark.parametrize('tamper',['export','extra','review'])
def test_factory_motion_inspect_detects_modified_inventory(case,tamper):
    from assetpipe.factory.motion import plan_job,run_job,inspect_job
    root,_,_,output,_=case
    job,_=factory_job(case)
    plan=plan_job(job,root)
    receipt=run_job(job,plan['plan_sha256'],output,root)
    sha=fingerprint(receipt)
    target={'export':'exports/placement.json','extra':'extra.txt','review':'candidate/review.json'}[tamper]
    (output/target).write_text('{}')
    with pytest.raises(ValueError,match='FACTORY_MOTION_OUTPUT_CHANGED'):
        inspect_job(output,sha,root)


def test_factory_motion_failure_is_terminal_and_retains_source(case,monkeypatch):
    from assetpipe.factory.motion import plan_job,run_job,inspect_job
    root,_,video,output,_=case
    job,_=factory_job(case)
    plan=plan_job(job,root)
    before=fingerprint(video)
    def fail(*args,**kwargs): raise ValueError('SYNTHETIC_DECODE_FAILURE')
    monkeypatch.setattr('assetpipe.motion.package.package_video',fail)
    with pytest.raises(ValueError,match='SYNTHETIC_DECODE_FAILURE'):
        run_job(job,plan['plan_sha256'],output,root)
    receipt=output/'factory_motion.json'
    assert json.loads(receipt.read_text())['status']=='FAILED'
    assert not (output/'candidate').exists() and fingerprint(video)==before
    with pytest.raises(ValueError,match='FACTORY_MOTION_RUN_BLOCKED'):
        inspect_job(output,fingerprint(receipt),root)


def test_factory_motion_inspect_rejects_foreign_output_before_read(case,monkeypatch):
    import assetpipe.factory.motion as coordinator
    from assetpipe.manifests import write
    root,_,_,output,_=case
    job,_=factory_job(case)
    plan=coordinator.plan_job(job,root)
    receipt=coordinator.run_job(job,plan['plan_sha256'],output,root)
    foreign=root.parent/'foreign-output.txt'
    foreign.write_text('not authorized for this data root')
    record=json.loads(receipt.read_text())
    record['outputs'][0]={'path':str(foreign),'sha256':fingerprint(foreign)}
    receipt.write_text(json.dumps(record),encoding='utf-8')
    expected=fingerprint(receipt)
    original=coordinator.fingerprint
    def bounded(path):
        assert path!=foreign,'Unauthorized file was read before root validation'
        return original(path)
    monkeypatch.setattr(coordinator,'fingerprint',bounded)
    with pytest.raises(ValueError,match='outside configured roots'):
        coordinator.inspect_job(output,expected,root)


def test_real_video_to_review_atlas_preserves_timing_and_sources(case):
    root, request, video, output, data = case
    before = {path: fingerprint(path) for path in [request, video, root / 'input/00.png']}
    receipt = json.loads(run(case).read_text(encoding='utf-8'))
    assert receipt['status'] == 'OFFLINE_PACKAGE_REVIEW_REQUIRED'
    assert receipt['provider_input_consumption'] == 'NOT_VERIFIED'
    assert receipt['generation_status'] == 'NOT_RUN'
    assert receipt['game_ready'] is False
    assert receipt['review_state'] == 'REVIEW_REQUIRED'
    assert before == {path: fingerprint(path) for path in before}
    assert fingerprint(output / 'original.avi') == fingerprint(video)
    atlas = json.loads((output / 'atlas.json').read_text())
    assert atlas['fps'] == '6'
    assert [frame['source_frame_index'] for frame in atlas['frames']] == list(range(1, 7))
    assert [frame['duration_ms'] for frame in atlas['frames']] == [1000 / 6] * 6
    with Image.open(output / 'sprites.png') as sheet:
        for frame in atlas['frames']:
            x, y, width, height = frame['rect']
            with Image.open(frame['path']) as aligned:
                assert sheet.crop((x, y, x + width, y + height)).tobytes() == aligned.convert('RGBA').tobytes()
    review = json.loads((output / 'review.json').read_text())
    assert all(value is None for value in review['checks'].values())
    with pytest.raises(FileExistsError):
        run(case)


@pytest.mark.parametrize('mutation,message', [
    ('hash', 'MOTION_SOURCE_CHANGED'), ('count', 'MOTION_FRAME_COUNT_MISMATCH'),
    ('fps', 'MOTION_CONTRACT_MISMATCH'), ('alpha', 'MOTION_ALPHA_UNAVAILABLE'),
    ('empty_roots', 'nonempty'), ('output', 'MOTION_OUTPUT_INVALID'),
    ('corrupt', None), ('source_drift', 'FACTORY_SOURCE_CHANGED')])
def test_invalid_inputs_fail_closed(case, mutation, message):
    root, request, video, output, data = case
    digest = fingerprint(video)
    roots = None
    if mutation == 'hash': digest = '0' * 64
    if mutation == 'count': data['motion']['target_frames'] = 5
    if mutation == 'fps': data['motion']['fps'] = 12
    if mutation == 'alpha': data['motion']['background_policy'] = 'EXPLICIT_ALPHA_REVIEW'
    if mutation == 'empty_roots': roots = []
    if mutation == 'output': output = root / 'src/forbidden'
    if mutation == 'corrupt':
        video.write_bytes(b'not a video')
        digest = fingerprint(video)
    if mutation == 'source_drift': (root / 'input/00.png').write_bytes(b'changed')
    request.write_text(json.dumps(data), encoding='utf-8')
    with pytest.raises(Exception, match=message):
        package_video(request, video, digest, output, root, allowed_roots=roots)
    if (output / 'run_manifest.json').exists():
        receipt = json.loads((output / 'run_manifest.json').read_text())
        assert receipt['status'] == 'FAILED'
        assert not (output / 'sprites.png').exists()


def test_child_failure_preserves_original_and_parent(case, monkeypatch):
    import assetpipe.motion.package as module
    from assetpipe.brief import make
    root, request, video, output, _ = case
    data = json.loads(request.read_text())
    brief = make(asset_id='parent', output_class='NONPIXEL_IMAGE', prompt='test fixture')
    brief['project_id'] = 'test'
    parent = root / 'parent.json'
    parent.write_text(json.dumps({'run_id': 'static-parent', 'asset_id': 'parent',
                                 'project_id': 'test', 'output_class': 'NONPIXEL_IMAGE',
                                 'asset_brief': brief, 'status': 'CANDIDATE_READY_REVIEW_REQUIRED',
                                 'outputs': [str(root / 'input/00.png')]}))
    data['source'].update(kind='EXISTING_RUN', manifest_ref=str(parent), manifest_sha256=fingerprint(parent))
    request.write_text(json.dumps(data))
    before = {path: fingerprint(path) for path in [request, video, parent, root / 'input/00.png']}
    def fail(*args, **kwargs):
        raise ValueError('forced extraction failure')
    monkeypatch.setattr(module, 'extract_motion', fail)
    with pytest.raises(ValueError, match='forced extraction'):
        run(case)
    assert before == {path: fingerprint(path) for path in before}
    assert fingerprint(output / 'original.avi') == before[video]
    assert (output / 'decoded/frame_0000.png').exists()
    receipt = json.loads((output / 'run_manifest.json').read_text())
    assert receipt['status'] == 'FAILED'
    assert 'outputs' not in receipt
    assert not (output / 'review.json').exists()


def test_empty_video_is_rejected(case):
    root, request, video, output, _ = case
    video.write_bytes(b'')
    with pytest.raises(subprocess.CalledProcessError):
        run(case)
    assert not output.exists()


def test_source_escape_is_rejected(case, tmp_path):
    root, request, video, output, data = case
    # Only the child directory is allowed, so request access itself must fail.
    with pytest.raises(ValueError, match='outside configured roots'):
        package_video(request, video, fingerprint(video), output, root, allowed_roots=[root / 'input'])


def test_missing_ffprobe_never_creates_child(case, monkeypatch):
    import assetpipe.motion.package as module
    monkeypatch.setattr(module.shutil, 'which', lambda name: None)
    with pytest.raises(ValueError, match='MOTION_FFPROBE_UNAVAILABLE'):
        run(case)
    assert not case[3].exists()


def test_corrupt_aligned_frame_does_not_export_atlas(case, monkeypatch):
    import assetpipe.motion.package as module
    original = module.extract_motion
    def corrupt(*args, **kwargs):
        report = original(*args, **kwargs)
        Image.new('RGB', (32, 32)).save(report['frames'][1]['aligned_path'])
        return report
    monkeypatch.setattr(module, 'extract_motion', corrupt)
    with pytest.raises(ValueError, match='MOTION_FRAME_SIZE_CHANGED'):
        run(case)
    output = case[3]
    assert not (output / 'sprites.png').exists()
    assert json.loads((output / 'run_manifest.json').read_text())['status'] == 'FAILED'


def test_parent_drift_after_extraction_cannot_report_success(case, monkeypatch):
    import assetpipe.motion.package as module
    original = module.extract_motion
    def drift(*args, **kwargs):
        report = original(*args, **kwargs)
        Image.new('RGB', (64, 64), 'red').save(case[0] / 'input/00.png')
        return report
    monkeypatch.setattr(module, 'extract_motion', drift)
    with pytest.raises(ValueError, match='FACTORY_SOURCE_CHANGED'):
        run(case)
    receipt = json.loads((case[3] / 'run_manifest.json').read_text())
    assert receipt['status'] == 'FAILED'
    assert 'outputs' not in receipt
    assert not (case[3] / 'review.json').exists()
