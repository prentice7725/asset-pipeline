"""Pixel64 마스크 부분 편집 (P3).

명시한 편집 명세(JSON)만 적용한다. 편집 영역(mask)은 각 연산의 사각형과 지정 픽셀의 합집합이며,
그 밖의 픽셀은 하나도 바뀌면 안 된다. 출력 색은 잠긴 팔레트(기본: 원본의 불투명 색 집합) 안에
있어야 하고, 보호 영역(손·장비·얼굴 등)을 건드리는 연산은 쓰기 전에 거부한다.

연산:
- erase_colors: rect 안에서 colors에 속한 픽셀만 투명하게 한다 (예: 바닥 그림자 제거).
- replace_color: rect 안에서 from 색을 to 색으로 바꾼다.
- set_pixels: 지정 좌표에 색을 칠하거나 null이면 투명하게 한다.

결과는 후보이며 사람 검토가 필요하다. 원본 파일은 바꾸지 않는다.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

from ...manifests import now, write_new

KIND = 'PIXEL64_MASKED_EDIT'
SPEC_KIND = 'PIXEL64_MASKED_EDIT_SPEC'
OPERATIONS = {'erase_colors', 'replace_color', 'set_pixels'}
PREVIEW_SCALE = 8


def _invalid(detail):
    return ValueError(f'PIXEL64_EDIT_SPEC_INVALID: {detail}')


def _sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def _color(value, where):
    if (not isinstance(value, list) or len(value) != 3
            or not all(isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 255 for v in value)):
        raise _invalid(f'{where} must be [r, g, b] integers 0-255')
    return tuple(value)


def _rect(value, size, where):
    if (not isinstance(value, list) or len(value) != 4
            or not all(isinstance(v, int) and not isinstance(v, bool) for v in value)):
        raise _invalid(f'{where} must be [x0, y0, x1, y1] integers')
    x0, y0, x1, y1 = value
    if not (0 <= x0 < x1 <= size[0] and 0 <= y0 < y1 <= size[1]):
        raise _invalid(f'{where} {value} is empty or outside {list(size)}')
    return x0, y0, x1, y1


def _rect_mask(rect, shape):
    mask = np.zeros(shape, dtype=bool)
    x0, y0, x1, y1 = rect
    mask[y0:y1, x0:x1] = True
    return mask


def _colors_mask(rgb, colors):
    mask = np.zeros(rgb.shape[:2], dtype=bool)
    for color in colors:
        mask |= (rgb == np.array(color, dtype=np.uint8)).all(axis=2)
    return mask


def _preview(before, after, changed, path):
    height, width = changed.shape
    yy, xx = np.mgrid[0:height, 0:width]
    checker = np.where(((yy // 2 + xx // 2) % 2)[..., None] == 0, [200, 200, 200], [150, 150, 150]).astype(np.uint8)

    def flat(rgba):
        return np.where(rgba[..., 3:4] == 255, rgba[..., :3], checker).astype(np.uint8)

    marks = flat(after).copy()
    marks[changed] = (255, 0, 255)
    strip = np.concatenate([flat(before), flat(after), marks], axis=1)
    Image.fromarray(strip, 'RGB').resize((strip.shape[1] * PREVIEW_SCALE, height * PREVIEW_SCALE),
                                         Image.NEAREST).save(path)


def load_spec(path):
    raw = Path(path).read_bytes()
    spec = json.loads(raw.decode('utf-8'))
    if not isinstance(spec, dict) or spec.get('kind') != SPEC_KIND or spec.get('schema_version') != 1:
        raise _invalid(f'kind must be {SPEC_KIND} and schema_version 1')
    unknown = set(spec) - {'kind', 'schema_version', 'reason', 'operations', 'protected', 'palette'}
    if unknown:
        raise _invalid(f'unknown fields {sorted(unknown)}')
    if not isinstance(spec.get('reason'), str) or not spec['reason'].strip():
        raise _invalid('reason is required')
    if not isinstance(spec.get('operations'), list) or not spec['operations']:
        raise _invalid('operations must be a non-empty list')
    return spec, _sha_bytes(raw)


def apply_edit(source, spec_path, output_dir, *, created_by, expected_size=(64, 64)):
    source, output_dir = Path(source), Path(output_dir)
    if output_dir.exists():
        raise FileExistsError(f'PIXEL64_EDIT_OUTPUT_EXISTS: {output_dir}')
    if not created_by or not str(created_by).strip():
        raise ValueError('PIXEL64_EDIT_CREATED_BY_REQUIRED')
    spec, spec_sha = load_spec(spec_path)
    source_bytes = source.read_bytes()
    with Image.open(source) as opened:
        size = opened.size
        before = np.asarray(opened.convert('RGBA'), dtype=np.uint8).copy()
    if size != tuple(expected_size):
        raise ValueError(f'PIXEL64_EDIT_SIZE_MISMATCH: {size} != {tuple(expected_size)}')
    if not np.isin(before[..., 3], (0, 255)).all():
        raise ValueError('PIXEL64_EDIT_SOURCE_ALPHA_NOT_BINARY')
    shape = before.shape[:2]
    source_palette = {tuple(int(v) for v in pixel) for pixel in before[before[..., 3] == 255][:, :3]}
    if spec.get('palette', 'source') == 'source':
        palette, palette_mode = source_palette, 'SOURCE_OPAQUE_COLORS'
    elif isinstance(spec['palette'], list) and spec['palette']:
        palette = {_color(c, 'palette entry') for c in spec['palette']}
        palette_mode = 'EXPLICIT'
    else:
        raise _invalid("palette must be 'source' or a non-empty color list")
    protected = np.zeros(shape, dtype=bool)
    protected_rects = [_rect(r, size, 'protected rect') for r in spec.get('protected', [])]
    for rect in protected_rects:
        protected |= _rect_mask(rect, shape)

    after = before.copy()
    mask = np.zeros(shape, dtype=bool)
    op_reports = []
    for index, op in enumerate(spec['operations']):
        where = f'operations[{index}]'
        kind = op.get('op') if isinstance(op, dict) else None
        if kind not in OPERATIONS:
            raise _invalid(f'{where}.op must be one of {sorted(OPERATIONS)}')
        rgb, opaque = after[..., :3], after[..., 3] == 255
        if kind == 'erase_colors':
            if set(op) != {'op', 'rect', 'colors'} or not isinstance(op['colors'], list) or not op['colors']:
                raise _invalid(f'{where} needs rect and a non-empty colors list')
            area = _rect_mask(_rect(op['rect'], size, f'{where}.rect'), shape)
            colors = [_color(c, f'{where}.colors') for c in op['colors']]
            target = area & opaque & _colors_mask(rgb, colors)
            new = lambda sel: after.__setitem__(sel, 0)
        elif kind == 'replace_color':
            if set(op) != {'op', 'rect', 'from', 'to'}:
                raise _invalid(f'{where} needs rect, from and to')
            area = _rect_mask(_rect(op['rect'], size, f'{where}.rect'), shape)
            source_color, target_color = _color(op['from'], f'{where}.from'), _color(op['to'], f'{where}.to')
            target = area & opaque & _colors_mask(rgb, [source_color])
            new = lambda sel, c=target_color: after.__setitem__(sel, (*c, 255))
        else:
            if set(op) != {'op', 'pixels'} or not isinstance(op['pixels'], list) or not op['pixels']:
                raise _invalid(f'{where} needs a non-empty pixels list of [x, y, [r, g, b] | null]')
            area = np.zeros(shape, dtype=bool)
            writes = []
            for item in op['pixels']:
                if not isinstance(item, list) or len(item) != 3 or not all(isinstance(v, int) for v in item[:2]):
                    raise _invalid(f'{where}.pixels entries must be [x, y, [r, g, b] | null]')
                x, y, value = item
                if not (0 <= x < size[0] and 0 <= y < size[1]):
                    raise _invalid(f'{where}.pixels {[x, y]} outside image')
                rgba = (0, 0, 0, 0) if value is None else (*_color(value, f'{where}.pixels color'), 255)
                area[y, x] = True
                writes.append((y, x, rgba))
            target = area.copy()

            def new(_sel, writes=writes):
                for y, x, rgba in writes:
                    after[y, x] = rgba
        hit = target & protected
        if hit.any():
            ys, xs = np.nonzero(hit)
            raise ValueError(f'PIXEL64_EDIT_PROTECTED_REGION: {where} would change {int(hit.sum())} protected pixels, first {[int(xs[0]), int(ys[0])]}')
        snapshot = after.copy()
        new(target)
        changed = (snapshot != after).any(axis=2)
        if not changed.any():
            raise ValueError(f'PIXEL64_EDIT_OP_NO_EFFECT: {where} changed no pixels')
        mask |= area
        op_reports.append({'index': index, 'op': kind, 'changed_pixels': int(changed.sum())})

    output_dir.mkdir(parents=True)
    image_path = output_dir / 'edited.png'
    preview_path = output_dir / 'review_preview.png'
    Image.fromarray(after, 'RGBA').save(image_path)
    with Image.open(image_path) as written:
        check = np.asarray(written.convert('RGBA'), dtype=np.uint8)
    _preview(before, check, (before != check).any(axis=2), preview_path)

    changed = (before != check).any(axis=2)
    opaque = check[..., 3] == 255
    out_colors = {tuple(int(v) for v in pixel) for pixel in check[opaque][:, :3]}
    gates = {
        'size': list(check.shape[1::-1]) == list(expected_size),
        'alpha_binary': bool(np.isin(check[..., 3], (0, 255)).all()),
        'transparent_rgb_zero': bool((check[~opaque][:, :3] == 0).all()) if (~opaque).any() else True,
        'changed_outside_mask': int((changed & ~mask).sum()),
        'changed_in_protected': int((changed & protected).sum()),
        'colors_outside_palette': len(out_colors - palette),
        'foreground_present': bool(opaque.any()),
    }
    passed = (gates['size'] and gates['alpha_binary'] and gates['foreground_present']
              and gates['changed_outside_mask'] == 0 and gates['changed_in_protected'] == 0
              and gates['colors_outside_palette'] == 0)
    report = {
        'kind': KIND,
        'schema_version': 1,
        'status': 'PASS_REVIEW_REQUIRED' if passed else 'FAIL',
        'created_by': str(created_by).strip(),
        'created_at': now(),
        'reason': spec['reason'].strip(),
        'source': str(source.resolve()),
        'source_sha256': _sha_bytes(source_bytes),
        'spec': str(Path(spec_path).resolve()),
        'spec_sha256': spec_sha,
        'output': str(image_path.resolve()),
        'output_sha256': _sha_bytes(image_path.read_bytes()),
        'review_preview': str(preview_path.resolve()),
        'review_preview_legend': 'before | after | after with changed pixels in magenta; checkerboard = transparent',
        'palette_mode': palette_mode,
        'protected_rects': [list(r) for r in protected_rects],
        'mask_pixels': int(mask.sum()),
        'changed_pixels': int(changed.sum()),
        'operations': op_reports,
        'opaque_colors_before': len(source_palette),
        'opaque_colors_after': len(out_colors),
        'gates': gates,
        'review': 'HUMAN_REQUIRED',
    }
    write_new(output_dir / 'edit_report.json', report)
    if not passed:
        raise ValueError(f'PIXEL64_EDIT_GATE_FAILED: {gates}')
    return report
