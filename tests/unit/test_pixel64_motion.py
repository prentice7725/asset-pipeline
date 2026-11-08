"""Pixel64 walk animation offline: reference, selection, pixelization, measurements and delivery (synthetic only)."""
import json

import numpy as np
import pytest
from PIL import Image

from assetpipe.pixel import motion64

COLORS = [(200, 30, 30), (30, 30, 200), (240, 200, 160)]


def _master(tmp_path):
    image = np.full((64, 64, 3), 252, dtype=np.uint8)
    image[12:30, 24:40] = COLORS[0]      # body
    image[30:52, 24:32] = COLORS[1]      # left leg
    image[30:52, 32:40] = COLORS[1]      # right leg
    image[6:12, 28:36] = COLORS[2]       # head
    path = tmp_path / 'master.png'
    Image.fromarray(image, 'RGB').save(path)
    return path


def _video_frame(tmp_path, index, leg_shift, s=12):
    """The master drawn at s-times on white, with the legs moved as a crude walk."""
    frame = np.full((768, 768, 3), 255, dtype=np.uint8)
    frame[12 * s:30 * s, 24 * s:40 * s] = COLORS[0]
    frame[30 * s:52 * s, (24 + leg_shift) * s:(32 + leg_shift) * s] = COLORS[1]
    frame[30 * s:52 * s, (32 - leg_shift) * s:(40 - leg_shift) * s] = COLORS[1]
    frame[6 * s:12 * s, 28 * s:36 * s] = COLORS[2]
    frame[12 * s, 24 * s:40 * s] = (215, 120, 120)   # anti-aliased edge colour not in the palette
    path = tmp_path / 'frames' / f'frame_{index:04d}.png'
    path.parent.mkdir(exist_ok=True)
    Image.fromarray(frame, 'RGB').save(path)
    return path


def test_reference_is_integer_nearest_upscale(tmp_path):
    record = motion64.build_reference(_master(tmp_path), tmp_path / 'ref')
    assert record['scale'] == 12 and record['size'] == [768, 768]
    with Image.open(record['reference']) as image:
        assert image.getpixel((26 * 12 + 5, 20 * 12 + 5)) == COLORS[0]


def test_selection_rules(tmp_path):
    path = tmp_path / 'selection.json'
    good = {'action': 'walk', 'reviewed_by': 'me', 'source_video_sha256': 'v', 'frames': [1, 4, 7, 10], 'fps': 8}
    path.write_text(json.dumps(good), encoding='utf-8')
    assert motion64.validate_selection(path, 'v')['fps'] == 8
    for change, code in [({'frames': [1, 2, 3]}, 'COUNT'), ({'frames': [4, 1, 7, 10]}, 'ORDER'),
                         ({'reviewed_by': ''}, 'UNREVIEWED'), ({'action': 'idle'}, 'ACTION')]:
        path.write_text(json.dumps({**good, **change}), encoding='utf-8')
        with pytest.raises(ValueError, match=code):
            motion64.validate_selection(path, 'v')
    path.write_text(json.dumps(good), encoding='utf-8')
    with pytest.raises(ValueError, match='VIDEO_MISMATCH'):
        motion64.validate_selection(path, 'other')


def test_pixelize_locks_palette_size_and_baseline(tmp_path):
    master = _master(tmp_path)
    frames = [_video_frame(tmp_path, i, shift) for i, shift in enumerate([0, 2, 0, -2])]
    report = motion64.pixelize(frames, master, tmp_path / 'out')
    palette = set(report['master_geometry']['palette'])
    assert len(report['frames']) == 4 and not any(f['clipped'] for f in report['frames'])
    for row in report['frames']:
        rgba = np.asarray(Image.open(row['path']).convert('RGBA'))
        assert rgba.shape == (64, 64, 4) and set(np.unique(rgba[..., 3])) <= {0, 255}
        opaque = rgba[rgba[..., 3] == 255][:, :3]
        assert {'#%02X%02X%02X' % tuple(c) for c in np.unique(opaque, axis=0)} <= palette
    rows = report['measurements']['frames']
    assert all(r['baseline_shift'] == 0 and r['height'] == 46 for r in rows)
    assert rows[0]['palette_usage_l1'] < 0.05 and rows[1]['changed_fraction_vs_previous'] > 0
    assert report['measurements']['rule'] == 'REPORT_ONLY_THRESHOLDS_NOT_SET'


def test_subject_leaving_the_window_is_reported_as_clipped(tmp_path):
    master = _master(tmp_path)
    # Subject at half the reference scale, so the 64px window covers only the middle of the frame.
    frames = [_video_frame(tmp_path, i, 0, s=6) for i in range(3)]
    wide = np.asarray(Image.open(frames[2]).convert('RGB')).copy()
    wide[200:220, 700:760] = COLORS[0]   # something far to the right of the subject
    Image.fromarray(wide, 'RGB').save(frames[2])
    report = motion64.pixelize(frames, master, tmp_path / 'out')
    assert [f['clipped'] for f in report['frames']] == [False, False, True]


def test_build_animation_stops_at_review_with_engine_files(tmp_path, monkeypatch):
    import assetpipe.motion.extractor as extractor
    import assetpipe.pipelines.pixel_static.approval as approval
    import assetpipe.providers.aseprite as aseprite
    master = _master(tmp_path)
    video = tmp_path / 'walk.mp4'
    video.write_bytes(b'video')
    selection = tmp_path / 'selection.json'
    selection.write_text(json.dumps({'action': 'walk', 'reviewed_by': 'me', 'frames': [0, 1, 2, 3], 'fps': 8,
                                     'source_video_sha256': motion64._sha(video)}), encoding='utf-8')
    record = tmp_path / 'approval_record.json'
    record.write_text('{}', encoding='utf-8')

    def decode(_video, output, last):
        output.mkdir(parents=True)
        for i, shift in enumerate([0, 2, 0, -2][:last + 1]):
            path = _video_frame(tmp_path, i, shift)
            path.replace(output / path.name)
        return {'decoded_count': last + 1}

    class Provider:
        def __init__(self, config): pass
        def export(self, frames, output, asset_id, action, duration):
            assert action == 'walk' and duration == 125 and len(frames) == 4
            return {'status': 'PASS', 'master': str(output / 'master.aseprite'), 'pixel_integrity': {'exact_rgba_match': True}}
    monkeypatch.setattr(extractor, 'decode_direct_reference', decode)
    monkeypatch.setattr(approval, 'validate_approval', lambda *a, **k: {})
    monkeypatch.setattr(aseprite, 'AsepriteProvider', Provider)
    manifest = motion64.build_animation(master=master, approval_record=record, video=video, selection_path=selection,
                                        output=tmp_path / 'run', config=None, asset_id='knight64')
    assert manifest['status'] == 'EXPORT_READY_REVIEW_REQUIRED' and manifest['game_ready'] is False
    engine = tmp_path / 'run/050_engine'
    assert {p.name for p in engine.iterdir()} == {'sprites.png', 'walk.tres', 'phaser-atlas.json', 'phaser-animation.json', 'placement.json'}
    placement = json.loads((engine / 'placement.json').read_text(encoding='utf-8'))
    assert placement['source_frame_indices'] == [0, 1, 2, 3] and placement['review_state'] == 'REVIEW_REQUIRED'
    with Image.open(engine / 'sprites.png') as sheet:
        assert sheet.size == (256, 64)
    # A second build into the same folder is refused rather than overwritten.
    with pytest.raises(FileExistsError):
        motion64.build_animation(master=master, approval_record=record, video=video, selection_path=selection,
                                 output=tmp_path / 'run', config=None, asset_id='knight64')


def test_video_submit_records_one_attempt_and_refuses_reuse(tmp_path, monkeypatch):
    import assetpipe._ported.comfy_bridge.runner as runner
    from pathlib import Path as P
    reference = motion64.build_reference(_master(tmp_path), tmp_path / 'ref')
    calls = []

    def fake_run(config, **kwargs):
        calls.append(kwargs)
        kwargs['output_dir'].mkdir(parents=True)
        video = kwargs['output_dir'] / 'walk.mp4'
        video.write_bytes(b'mp4')
        return [video]
    monkeypatch.setattr(runner, 'run_workflow', fake_run)

    class Config:
        root = P(__file__).resolve().parents[2]
    record = motion64.submit_video(tmp_path / 'ref', tmp_path / 'v1', seed=7, config=Config())
    assert record['status'] == 'COMPLETED' and record['retry'] == 'NONE' and record['seed'] == 7
    assert calls[0]['input_image'] == P(reference['reference']) and calls[0]['workflow_name'] == motion64.VIDEO_WORKFLOW
    with pytest.raises(FileExistsError):
        motion64.submit_video(tmp_path / 'ref', tmp_path / 'v1', seed=7, config=Config())
    monkeypatch.setattr(runner, 'run_workflow', lambda config, **k: (_ for _ in ()).throw(RuntimeError('comfy down')))
    with pytest.raises(RuntimeError):
        motion64.submit_video(tmp_path / 'ref', tmp_path / 'v2', seed=7, config=Config())
    assert json.loads((tmp_path / 'v2/video_run.json').read_text(encoding='utf-8'))['status'] == 'FAILED'
    assert len(calls) == 1
