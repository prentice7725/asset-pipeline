"""Pixel64 binary-alpha delivery copy; synthetic images only, no generation."""
import json

import numpy as np
import pytest
from PIL import Image

from assetpipe.pixel.transparent import make_transparent

WHITE, DARK, SHADOW = (255, 255, 255), (20, 10, 10), (140, 135, 146)


def _sprite(tmp_path, *, border=WHITE, name='in.png'):
    """64x64: ring outline enclosing a white pocket, white eye pixel, gray shadow, uniform border."""
    image = np.full((64, 64, 3), border, dtype=np.uint8)
    image[10:40, 10:40] = DARK
    image[20:30, 20:30] = border  # enclosed pocket (background-colored gap)
    image[12, 12] = border        # one-pixel highlight, also background-colored
    image[45:48, 12:38] = SHADOW
    path = tmp_path / name
    Image.fromarray(image, 'RGB').save(path)
    return path, image


def _rgba(path):
    return np.asarray(Image.open(path).convert('RGBA'))


def test_edge_background_cleared_enclosed_left_for_review(tmp_path):
    source, rgb = _sprite(tmp_path)
    before = source.read_bytes()
    report = make_transparent(source, tmp_path / 'out', created_by='test')
    out = _rgba(report['output'])
    assert source.read_bytes() == before
    assert out[0, 0, 3] == 0 and out[25, 25, 3] == 255 and out[12, 12, 3] == 255
    assert (out[46, 20] == (*SHADOW, 255)).all()
    opaque = out[..., 3] == 255
    assert (out[opaque][:, :3] == rgb[opaque]).all()
    assert set(np.unique(out[..., 3])) == {0, 255}
    assert report['status'] == 'ENCLOSED_BACKGROUND_REVIEW_REQUIRED'
    assert sorted(r['pixels'] for r in report['unresolved_enclosed_regions']) == [1, 100]
    assert report['review'] == 'HUMAN_REQUIRED'
    assert json.loads((tmp_path / 'out/transparent_report.json').read_text(encoding='utf-8'))['output_sha256'] == report['output_sha256']


def test_explicit_seed_clears_only_that_region(tmp_path):
    source, _ = _sprite(tmp_path)
    report = make_transparent(source, tmp_path / 'out', created_by='test', hole_seeds=[(25, 25)])
    out = _rgba(report['output'])
    assert out[25, 25, 3] == 0 and out[12, 12, 3] == 255
    assert [r['pixels'] for r in report['cleared_enclosed_regions']] == [100]
    assert [r['pixels'] for r in report['unresolved_enclosed_regions']] == [1]


def test_all_pockets_cleared_is_pass_review_required(tmp_path):
    source, _ = _sprite(tmp_path)
    report = make_transparent(source, tmp_path / 'out', created_by='test', hole_seeds=[(25, 25), (12, 12)])
    assert report['status'] == 'PASS_REVIEW_REQUIRED'
    assert report['gates']['background_residual_touching_transparency'] == 0


def test_seed_on_foreground_is_rejected_and_writes_nothing(tmp_path):
    source, _ = _sprite(tmp_path)
    with pytest.raises(ValueError, match='HOLE_SEED_NOT_ENCLOSED_BACKGROUND'):
        make_transparent(source, tmp_path / 'out', created_by='test', hole_seeds=[(15, 15)])
    assert not (tmp_path / 'out').exists()


def test_near_white_border_within_tolerance_is_used_exactly(tmp_path):
    source, _ = _sprite(tmp_path, border=(254, 254, 254))
    report = make_transparent(source, tmp_path / 'out', created_by='test')
    assert report['background_rgb_found'] == [254, 254, 254]


def test_border_far_from_declared_background_fails(tmp_path):
    source, _ = _sprite(tmp_path, border=(200, 200, 200))
    with pytest.raises(ValueError, match='BORDER_NOT_DECLARED_BACKGROUND'):
        make_transparent(source, tmp_path / 'out', created_by='test')


def test_mixed_border_is_not_guessed(tmp_path):
    source, rgb = _sprite(tmp_path)
    rgb[0, 5] = DARK
    Image.fromarray(rgb, 'RGB').save(source)
    with pytest.raises(ValueError, match='BORDER_NOT_UNIFORM'):
        make_transparent(source, tmp_path / 'out', created_by='test')


def test_wrong_size_and_existing_output_rejected(tmp_path):
    small = tmp_path / 'small.png'
    Image.new('RGB', (32, 32), WHITE).save(small)
    with pytest.raises(ValueError, match='SIZE_MISMATCH'):
        make_transparent(small, tmp_path / 'a', created_by='test')
    source, _ = _sprite(tmp_path)
    (tmp_path / 'b').mkdir()
    with pytest.raises(FileExistsError):
        make_transparent(source, tmp_path / 'b', created_by='test')


def test_non_opaque_source_rejected(tmp_path):
    path = tmp_path / 'rgba.png'
    Image.new('RGBA', (64, 64), (255, 255, 255, 0)).save(path)
    with pytest.raises(ValueError, match='SOURCE_NOT_OPAQUE'):
        make_transparent(path, tmp_path / 'out', created_by='test')


def test_enclosed_regions_get_display_only_hole_or_highlight_hints(tmp_path):
    import json
    from assetpipe.pixel.transparent import make_transparent
    image = np.full((64, 64, 3), 255, dtype=np.uint8)
    image[10:54, 10:54] = (20, 20, 20)          # dark body / outline
    image[14:18, 14:18] = 255                   # 16 px gap bordered by dark pixels -> possible hole
    image[30:40, 30:46] = (200, 200, 210)       # light robe area
    image[33:36, 34:38] = 255                   # 12 px white inside light robe -> likely highlight
    image[45, 45] = 255                         # 1 px eye glint in dark -> likely highlight (too small)
    path = tmp_path / 'in.png'
    Image.fromarray(image, 'RGB').save(path)
    report = make_transparent(path, tmp_path / 'out', created_by='test')
    hints = sorted((r['pixels'], r['hint']) for r in report['unresolved_enclosed_regions'])
    assert hints == [(1, 'LIKELY_HIGHLIGHT'), (12, 'LIKELY_HIGHLIGHT'), (16, 'POSSIBLE_HOLE')]
    assert report['possible_holes'] == 1
    preview = np.asarray(Image.open(tmp_path / 'out/review_preview.png').convert('RGB'))
    assert tuple(preview[15 * 8, 15 * 8]) == (255, 0, 255) and tuple(preview[34 * 8, 35 * 8]) == (0, 255, 255)
    out = np.asarray(Image.open(tmp_path / 'out/transparent.png').convert('RGBA'))
    assert out[15, 15, 3] == 255 and out[34, 35, 3] == 255  # hints never clear pixels
    assert json.loads((tmp_path / 'out/transparent_report.json').read_text(encoding='utf-8'))['hint_rule']['possible_hole_min_pixels'] == 6
