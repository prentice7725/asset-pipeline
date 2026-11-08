"""Transparent delivery joining a static approval, and the resolution review helper; synthetic files only."""
import json

import numpy as np
import pytest
from PIL import Image

from assetpipe.pipelines.pixel_static.approval import validate_delivery, write_resolution_review
from assetpipe.pixel.transparent import make_transparent


def _master(tmp_path, hole=False):
    image = np.full((64, 64, 3), 252, dtype=np.uint8)
    image[10:54, 10:54] = (20, 20, 20)
    if hole:
        image[14:18, 14:18] = 252
    path = tmp_path / 'sheet.png'
    Image.fromarray(image, 'RGB').convert('RGBA').save(path)
    return path


def _delivery(tmp_path, master, name='t', seeds=(), roundtrip='PASS'):
    report = make_transparent(master, tmp_path / name, created_by='test', hole_seeds=seeds)
    if roundtrip:
        (tmp_path / name / 'aseprite_roundtrip.json').write_text(json.dumps({'status': roundtrip}), encoding='utf-8')
    return report['output']


def test_delivery_matching_master_is_recorded(tmp_path):
    master = _master(tmp_path)
    record = validate_delivery(master, _delivery(tmp_path, master))
    assert record['possible_holes'] == 0 and record['unresolved_enclosed_regions'] == 0
    assert len(record['transparent_sha256']) == 64 and record['accepted_possible_holes'] is False


def test_possible_holes_need_explicit_acceptance_or_a_hole_seed(tmp_path):
    master = _master(tmp_path, hole=True)
    delivered = _delivery(tmp_path, master)
    with pytest.raises(ValueError, match='look like holes'):
        validate_delivery(master, delivered)
    assert validate_delivery(master, delivered, accept_possible_holes=True)['accepted_possible_holes'] is True
    cleared = _delivery(tmp_path, master, name='holes', seeds=[(15, 15)])
    assert validate_delivery(master, cleared)['hole_seeds'] == [[15, 15]]


def test_delivery_from_a_different_or_edited_image_is_rejected(tmp_path):
    master = _master(tmp_path)
    other = np.asarray(Image.open(master).convert('RGB')).copy()
    other[30, 30] = (200, 0, 0)
    other_path = tmp_path / 'other.png'
    Image.fromarray(other, 'RGB').save(other_path)
    with pytest.raises(ValueError, match='only its background removed'):
        validate_delivery(master, _delivery(tmp_path, other_path))


def test_delivery_needs_aseprite_round_trip_and_unchanged_file(tmp_path):
    master = _master(tmp_path)
    with pytest.raises(ValueError, match='Aseprite round trip'):
        validate_delivery(master, _delivery(tmp_path, master, roundtrip=None))
    delivered = _delivery(tmp_path, master, name='t2')
    Image.new('RGBA', (64, 64)).save(delivered)
    with pytest.raises(ValueError, match='changed since'):
        validate_delivery(master, delivered)


def test_resolution_review_records_selection_with_report_hash(tmp_path):
    run = tmp_path / 'run'
    (run / '050_resolution').mkdir(parents=True)
    report = {'candidates': [{'logical_height': 64, 'status': 'AUTO_PASS_REVIEW_REQUIRED'}]}
    (run / '050_resolution/resolution_report.json').write_text(json.dumps(report), encoding='utf-8')
    (run / 'run_manifest.json').write_text(json.dumps({'output_class': 'PIXEL_STATIC', 'status': 'RESOLUTION_REVIEW_REQUIRED'}), encoding='utf-8')
    with pytest.raises(ValueError, match='not a passing candidate'):
        write_resolution_review(run, resolution=32, reviewed_by='me', reason='r')
    path = write_resolution_review(run, resolution=64, reviewed_by='me', reason='native size')
    review = json.loads(path.read_text(encoding='utf-8'))
    assert review['status'] == 'SELECTED' and review['selected_resolution'] == 64 and len(review['source_report_sha256']) == 64
    with pytest.raises(FileExistsError):
        write_resolution_review(run, resolution=64, reviewed_by='me', reason='again')


def test_report_without_hints_counts_every_enclosed_region_as_possible_hole(tmp_path):
    master = _master(tmp_path, hole=True)
    delivered = _delivery(tmp_path, master)
    report_path = tmp_path / 't/transparent_report.json'
    report = json.loads(report_path.read_text(encoding='utf-8'))
    del report['possible_holes']
    report_path.write_text(json.dumps(report), encoding='utf-8')
    with pytest.raises(ValueError, match='1 enclosed region'):
        validate_delivery(master, delivered)
