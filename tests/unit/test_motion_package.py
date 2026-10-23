"""Real local codec/packing tests with synthetic fixtures; zero model calls."""
import json
import shutil
import subprocess

import pytest
from PIL import Image, ImageDraw

from assetpipe.factory.provenance import fingerprint
from assetpipe.motion.package import package_video


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
