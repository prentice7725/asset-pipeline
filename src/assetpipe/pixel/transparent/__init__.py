"""Pixel64 투명 납품본 (P1).

불투명 생성본은 그대로 두고 별도의 이진 알파 납품본을 만든다.

- 배경색은 선언한 값(기본 흰색)과 허용 거리 안에 있어야 하고, 이미지 테두리 전체가 그 한 색이어야
  한다. 테두리가 섞여 있으면 배경을 추측하지 않고 실패한다.
- 테두리에 이어진 배경색 픽셀만 투명하게 한다(기존 검증된 edge_connected 사용).
- 캐릭터 안에 갇힌 배경색 영역(지팡이와 몸 사이 틈, 눈 하이라이트 등)은 자동으로 지우지 않는다.
  명시한 seed 좌표가 가리키는 영역만 지우고, 나머지는 검토 항목으로 보고한다.
- 검토를 돕기 위해 남은 영역마다 힌트를 붙인다(표시 전용, 아무것도 지우지 않는다): 6픽셀 이상이고
  둘레의 70% 이상이 어두우면(밝기 < 100) 구멍 가능성(자홍색), 아니면 하이라이트 가능성(청록색).
- 불투명 픽셀의 RGB와 위치는 바꾸지 않는다. 바닥 그림자 같은 비배경색은 그대로 남는다.
- 결과는 후보이며 사람 검토가 필요하다.
"""
import hashlib
import math
from pathlib import Path

import numpy as np
from PIL import Image

from ...manifests import now, write_new
from ..direct.ported import edge_connected

KIND = 'PIXEL64_TRANSPARENT_DELIVERY'
DEFAULT_BACKGROUND = (255, 255, 255)
DEFAULT_TOLERANCE = 10
PREVIEW_SCALE = 8
# Display-only hint thresholds, measured on the 2026-11-07 Pixel64 samples: cleared holes had >= 71%
# dark 4-neighbours, kept highlights (glints, white robe, blade shine) <= 50%; eye glints are tiny.
HOLE_HINT_MIN_PIXELS = 6
HOLE_HINT_MIN_DARK_RING = 0.7
DARK_LUMA = 100
HOLE_COLOR, HIGHLIGHT_COLOR = (255, 0, 255), (0, 255, 255)


def _sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _label4(mask):
    """4-connected component labels for a small boolean mask (0 = none)."""
    labels = np.zeros(mask.shape, dtype=np.int32)
    count = 0
    height, width = mask.shape
    for y, x in zip(*np.nonzero(mask)):
        if labels[y, x]:
            continue
        count += 1
        stack = [(y, x)]
        labels[y, x] = count
        while stack:
            cy, cx = stack.pop()
            for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                if 0 <= ny < height and 0 <= nx < width and mask[ny, nx] and not labels[ny, nx]:
                    labels[ny, nx] = count
                    stack.append((ny, nx))
    return labels, count


def _region(labels, index, rgb=None):
    ys, xs = np.nonzero(labels == index)
    region = {'pixels': int(len(xs)), 'bbox_xyxy': [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1],
              'seed_xy': [int(xs[0]), int(ys[0])]}
    if rgb is not None:
        region.update(_hint(rgb, labels == index))
    return region


def _hint(rgb, mask):
    """Display-only guess: a real hole is bordered by outline/dark pixels, a highlight by light ones."""
    pad = np.pad(mask, 1)
    ring = (pad[:-2, 1:-1] | pad[2:, 1:-1] | pad[1:-1, :-2] | pad[1:-1, 2:]) & ~mask
    luma = rgb[ring].astype(np.float64) @ np.array([0.299, 0.587, 0.114])
    dark = float((luma < DARK_LUMA).mean()) if len(luma) else 0.0
    hole = int(mask.sum()) >= HOLE_HINT_MIN_PIXELS and dark >= HOLE_HINT_MIN_DARK_RING
    return {'dark_ring_fraction': round(dark, 3), 'hint': 'POSSIBLE_HOLE' if hole else 'LIKELY_HIGHLIGHT'}


def _preview(rgba, unresolved, path, highlight=None):
    """Checkerboard behind transparency; unresolved enclosed background: magenta = possible hole,
    cyan = likely highlight (``highlight`` mask)."""
    height, width = unresolved.shape
    yy, xx = np.mgrid[0:height, 0:width]
    checker = np.where(((yy // 2 + xx // 2) % 2)[..., None] == 0, [200, 200, 200], [150, 150, 150]).astype(np.uint8)
    opaque = rgba[..., 3:4] == 255
    view = np.where(opaque, rgba[..., :3], checker)
    view[unresolved] = HOLE_COLOR
    if highlight is not None:
        view[unresolved & highlight] = HIGHLIGHT_COLOR
    Image.fromarray(view.astype(np.uint8), 'RGB').resize((width * PREVIEW_SCALE, height * PREVIEW_SCALE),
                                                         Image.NEAREST).save(path)


def make_transparent(source, output_dir, *, background_rgb=DEFAULT_BACKGROUND, tolerance=DEFAULT_TOLERANCE,
                     hole_seeds=(), expected_size=(64, 64), created_by):
    source, output_dir = Path(source), Path(output_dir)
    if output_dir.exists():
        raise FileExistsError(f'PIXEL64_TRANSPARENT_OUTPUT_EXISTS: {output_dir}')
    if not created_by or not str(created_by).strip():
        raise ValueError('PIXEL64_TRANSPARENT_CREATED_BY_REQUIRED')
    background_rgb = tuple(int(v) for v in background_rgb)
    if len(background_rgb) != 3 or not all(0 <= v <= 255 for v in background_rgb):
        raise ValueError('PIXEL64_TRANSPARENT_BACKGROUND_INVALID')
    if not (isinstance(tolerance, (int, float)) and math.isfinite(tolerance) and tolerance >= 0):
        raise ValueError('PIXEL64_TRANSPARENT_TOLERANCE_INVALID')

    with Image.open(source) as opened:
        size = opened.size
        rgba = np.asarray(opened.convert('RGBA'), dtype=np.uint8)
    if size != tuple(expected_size):
        raise ValueError(f'PIXEL64_TRANSPARENT_SIZE_MISMATCH: {size} != {tuple(expected_size)}')
    if not (rgba[..., 3] == 255).all():
        raise ValueError('PIXEL64_TRANSPARENT_SOURCE_NOT_OPAQUE: input must be the opaque generated candidate')
    rgb = rgba[..., :3]

    border = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
    border_colors = {tuple(int(v) for v in color) for color in border}
    if len(border_colors) != 1:
        raise ValueError(f'PIXEL64_TRANSPARENT_BORDER_NOT_UNIFORM: {len(border_colors)} border colors')
    found = border_colors.pop()
    distance = math.dist(found, background_rgb)
    if distance > tolerance:
        raise ValueError(f'PIXEL64_TRANSPARENT_BORDER_NOT_DECLARED_BACKGROUND: {list(found)} is {distance:.1f} from {list(background_rgb)}')

    same = (rgb == np.array(found, dtype=np.uint8)).all(axis=2)
    outside = edge_connected(same)
    labels, count = _label4(same & ~outside)
    cleared = set()
    for seed in hole_seeds:
        x, y = (int(v) for v in seed)
        if not (0 <= x < size[0] and 0 <= y < size[1]) or not labels[y, x]:
            raise ValueError(f'PIXEL64_TRANSPARENT_HOLE_SEED_NOT_ENCLOSED_BACKGROUND: {[x, y]}')
        cleared.add(int(labels[y, x]))
    transparent = outside | np.isin(labels, sorted(cleared))
    unresolved = (labels > 0) & ~transparent

    out = np.dstack((rgb, np.full(rgb.shape[:2], 255, dtype=np.uint8)))
    out[transparent] = 0
    output_dir.mkdir(parents=True)
    image_path = output_dir / 'transparent.png'
    preview_path = output_dir / 'review_preview.png'
    Image.fromarray(out, 'RGBA').save(image_path)
    unresolved_labels = sorted(set(int(v) for v in np.unique(labels[unresolved])) - {0})
    unresolved_regions = [_region(labels, i, rgb) for i in unresolved_labels]
    highlight = np.isin(labels, [i for i, r in zip(unresolved_labels, unresolved_regions) if r['hint'] == 'LIKELY_HIGHLIGHT'])
    _preview(out, unresolved, preview_path, highlight)

    with Image.open(image_path) as written:
        check = np.asarray(written.convert('RGBA'), dtype=np.uint8)
    opaque = check[..., 3] == 255
    pad = np.pad(check[..., 3] == 0, 1)
    touches = pad[:-2, 1:-1] | pad[2:, 1:-1] | pad[1:-1, :-2] | pad[1:-1, 2:]
    gates = {
        'size': list(size) == list(expected_size),
        'alpha_binary': bool(np.isin(check[..., 3], (0, 255)).all()),
        'opaque_rgb_unchanged': bool((check[opaque][:, :3] == rgb[opaque]).all()),
        'transparent_only_background_color': bool(same[~opaque].all()),
        'background_residual_touching_transparency': int((opaque & same & touches).sum()),
        'foreground_present': bool(opaque.any()),
    }
    passed = (gates['size'] and gates['alpha_binary'] and gates['opaque_rgb_unchanged']
              and gates['transparent_only_background_color'] and gates['foreground_present']
              and gates['background_residual_touching_transparency'] == 0)
    if passed:
        status = 'PASS_REVIEW_REQUIRED' if not unresolved.any() else 'ENCLOSED_BACKGROUND_REVIEW_REQUIRED'
    else:
        status = 'FAIL'
    colors = {tuple(int(v) for v in pixel) for pixel in check[opaque][:, :3]}
    report = {
        'kind': KIND,
        'schema_version': 1,
        'status': status,
        'created_by': str(created_by).strip(),
        'created_at': now(),
        'source': str(source.resolve()),
        'source_sha256': _sha(source),
        'output': str(image_path.resolve()),
        'output_sha256': _sha(image_path),
        'review_preview': str(preview_path.resolve()),
        'review_preview_legend': ('checkerboard = transparent; enclosed background color left opaque: magenta = possible hole, '
                                  'cyan = likely highlight (display-only hint, nothing is cleared without --hole)'),
        'hint_rule': {'possible_hole_min_pixels': HOLE_HINT_MIN_PIXELS, 'possible_hole_min_dark_ring_fraction': HOLE_HINT_MIN_DARK_RING,
                      'dark_luma_below': DARK_LUMA, 'neighbourhood': '4-connected ring'},
        'method': 'uniform border color within tolerance of declared background; 4-connected edge fill of that exact color; enclosed regions only at explicit seeds',
        'declared_background_rgb': list(background_rgb),
        'tolerance_rgb_distance': tolerance,
        'background_rgb_found': list(found),
        'hole_seeds': [[int(v) for v in seed] for seed in hole_seeds],
        'cleared_enclosed_regions': [_region(labels, i) for i in sorted(cleared)],
        'unresolved_enclosed_regions': unresolved_regions,
        'possible_holes': sum(r['hint'] == 'POSSIBLE_HOLE' for r in unresolved_regions),
        'transparent_pixels': int((~opaque).sum()),
        'opaque_pixels': int(opaque.sum()),
        'opaque_colors': len(colors),
        'gates': gates,
        'review': 'HUMAN_REQUIRED',
    }
    write_new(output_dir / 'transparent_report.json', report)
    if status == 'FAIL':
        raise ValueError(f'PIXEL64_TRANSPARENT_GATE_FAILED: {gates}')
    return report
