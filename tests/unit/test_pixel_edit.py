"""Pixel64 masked edit; synthetic images only, no generation."""
import json

import numpy as np
import pytest
from PIL import Image

from assetpipe.pixel.edit import SPEC_KIND, apply_edit

BODY, OUTLINE, SHADOW, EYE = (68, 88, 52), (15, 22, 15), (140, 135, 146), (219, 219, 219)


def _sprite(tmp_path):
    image = np.zeros((64, 64, 4), dtype=np.uint8)
    image[10:50, 20:44] = (*BODY, 255)
    image[49, 20:44] = (*OUTLINE, 255)
    image[20, 30] = (*EYE, 255)
    image[50:54, 14:50] = (*SHADOW, 255)
    image[51, 31] = (*OUTLINE, 255)  # foot pixel inside the shadow band
    path = tmp_path / 'in.png'
    Image.fromarray(image, 'RGBA').save(path)
    return path, image


def _spec(tmp_path, operations, name='spec.json', **extra):
    path = tmp_path / name
    path.write_text(json.dumps({'kind': SPEC_KIND, 'schema_version': 1, 'reason': 'test',
                                'operations': operations, **extra}), encoding='utf-8')
    return path


def _rgba(path):
    return np.asarray(Image.open(path).convert('RGBA'))


def test_erase_colors_removes_only_named_colors_inside_rect(tmp_path):
    source, before = _sprite(tmp_path)
    original = source.read_bytes()
    spec = _spec(tmp_path, [{'op': 'erase_colors', 'rect': [0, 50, 64, 64], 'colors': [list(SHADOW)]}])
    report = apply_edit(source, spec, tmp_path / 'out', created_by='test')
    after = _rgba(report['output'])
    assert source.read_bytes() == original
    assert (after[50:54, 14:50][..., 3] == 0).sum() == 4 * 36 - 1
    assert (after[51, 31] == (*OUTLINE, 255)).all()
    changed = (after != before).any(axis=2)
    assert not changed[:50].any()
    assert report['status'] == 'PASS_REVIEW_REQUIRED' and report['gates']['changed_outside_mask'] == 0
    assert report['operations'] == [{'index': 0, 'op': 'erase_colors', 'changed_pixels': 143}]
    assert report['review'] == 'HUMAN_REQUIRED'


def test_replace_and_set_pixels_stay_in_source_palette(tmp_path):
    source, _ = _sprite(tmp_path)
    spec = _spec(tmp_path, [{'op': 'replace_color', 'rect': [20, 10, 44, 30], 'from': list(EYE), 'to': list(OUTLINE)},
                            {'op': 'set_pixels', 'pixels': [[25, 25, list(OUTLINE)], [26, 25, None]]}])
    report = apply_edit(source, spec, tmp_path / 'out', created_by='test')
    after = _rgba(report['output'])
    assert (after[20, 30] == (*OUTLINE, 255)).all() and (after[25, 25] == (*OUTLINE, 255)).all()
    assert after[25, 26, 3] == 0
    assert report['changed_pixels'] == 3


def test_color_outside_locked_palette_fails_gate(tmp_path):
    source, _ = _sprite(tmp_path)
    spec = _spec(tmp_path, [{'op': 'set_pixels', 'pixels': [[25, 25, [1, 2, 3]]]}])
    with pytest.raises(ValueError, match='GATE_FAILED'):
        apply_edit(source, spec, tmp_path / 'out', created_by='test')
    report = json.loads((tmp_path / 'out/edit_report.json').read_text(encoding='utf-8'))
    assert report['status'] == 'FAIL' and report['gates']['colors_outside_palette'] == 1


def test_explicit_palette_allows_declared_new_color(tmp_path):
    source, _ = _sprite(tmp_path)
    spec = _spec(tmp_path, [{'op': 'set_pixels', 'pixels': [[25, 25, [1, 2, 3]]]}],
                 palette=[list(BODY), list(OUTLINE), list(SHADOW), list(EYE), [1, 2, 3]])
    assert apply_edit(source, spec, tmp_path / 'out', created_by='test')['palette_mode'] == 'EXPLICIT'


def test_protected_region_rejects_before_writing(tmp_path):
    source, _ = _sprite(tmp_path)
    spec = _spec(tmp_path, [{'op': 'erase_colors', 'rect': [0, 50, 64, 64], 'colors': [list(SHADOW)]}],
                 protected=[[14, 52, 20, 54]])
    with pytest.raises(ValueError, match='PROTECTED_REGION'):
        apply_edit(source, spec, tmp_path / 'out', created_by='test')
    assert not (tmp_path / 'out').exists()


def test_operation_without_effect_is_rejected(tmp_path):
    source, _ = _sprite(tmp_path)
    spec = _spec(tmp_path, [{'op': 'erase_colors', 'rect': [0, 0, 10, 10], 'colors': [list(SHADOW)]}])
    with pytest.raises(ValueError, match='OP_NO_EFFECT'):
        apply_edit(source, spec, tmp_path / 'out', created_by='test')


@pytest.mark.parametrize('operations, extra, match', [
    ([{'op': 'blur', 'rect': [0, 0, 4, 4]}], {}, 'op must be one of'),
    ([{'op': 'erase_colors', 'rect': [0, 0, 70, 4], 'colors': [[0, 0, 0]]}], {}, 'outside'),
    ([{'op': 'erase_colors', 'rect': [0, 0, 4, 4], 'colors': [[0, 0, 300]]}], {}, 'integers 0-255'),
    ([], {}, 'non-empty'),
    ([{'op': 'set_pixels', 'pixels': [[1, 1, None]]}], {'extra_field': 1}, 'unknown fields'),
])
def test_invalid_specs_rejected(tmp_path, operations, extra, match):
    source, _ = _sprite(tmp_path)
    spec = _spec(tmp_path, operations, **extra)
    with pytest.raises(ValueError, match=match):
        apply_edit(source, spec, tmp_path / 'out', created_by='test')


def test_semi_transparent_source_and_existing_output_rejected(tmp_path):
    path = tmp_path / 'soft.png'
    Image.new('RGBA', (64, 64), (10, 10, 10, 128)).save(path)
    spec = _spec(tmp_path, [{'op': 'set_pixels', 'pixels': [[1, 1, None]]}])
    with pytest.raises(ValueError, match='ALPHA_NOT_BINARY'):
        apply_edit(path, spec, tmp_path / 'out', created_by='test')
    source, _ = _sprite(tmp_path)
    (tmp_path / 'exists').mkdir()
    with pytest.raises(FileExistsError):
        apply_edit(source, spec, tmp_path / 'exists', created_by='test')
