"""Palette budget quantization for PIXEL_STATIC candidates, applied before Pixel Gate.

Only opaque RGB values change. Dimensions, pixel positions and the (already binary) alpha
channel are preserved, and no dithering is used so flat pixel-art planes stay flat. The
result is still a candidate: Pixel Gate re-analyzes it and human review remains required.
"""
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
from PIL import Image

from ..._ported.pixel_gate.analyzer import _parse_color

STRIP_WIDTH = 4096


def _unique_count(pixels):
    return 0 if not len(pixels) else len(np.unique(pixels.reshape(-1, 3), axis=0))


def _median_cut(pixels, max_colors):
    """Median-cut the opaque pixels only, so transparent pixels never consume palette slots."""
    count = len(pixels)
    rows = -(-count // STRIP_WIDTH)
    padded = np.zeros((rows * STRIP_WIDTH, 3), dtype=np.uint8)
    padded[:count] = pixels
    padded[count:] = pixels[-1]
    strip = Image.fromarray(padded.reshape(rows, STRIP_WIDTH, 3), 'RGB')
    quantized = strip.quantize(colors=max_colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    return np.asarray(quantized.convert('RGB')).reshape(-1, 3)[:count]


def _nearest(pixels, palette):
    table = np.asarray(palette, dtype=np.int32)
    distances = ((pixels[:, None, :].astype(np.int32) - table[None, :, :]) ** 2).sum(axis=2)
    return table[distances.argmin(axis=1)].astype(np.uint8)


def quantize_candidate(source, directory, *, max_colors=32, allowed_palette=None):
    """Write ``quantized.png`` and a report under ``directory``; return (path, report).

    With an explicit brief palette every opaque pixel snaps to its nearest allowed color;
    otherwise colors are median-cut down to ``max_colors``. Candidates already within budget
    are copied unchanged (status NOT_NEEDED).
    """
    if max_colors < 1:
        raise ValueError('max_colors must be at least 1.')
    source = Path(source).resolve()
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=False)
    with Image.open(source) as opened:
        opened.seek(0)
        rgba = np.array(opened.convert('RGBA'))
    opaque = rgba[..., 3] > 0
    pixels = rgba[opaque][:, :3]
    before = _unique_count(pixels)
    palette = sorted({_parse_color(color) for color in allowed_palette}) if allowed_palette else None
    if palette is not None and not palette:
        raise ValueError('Allowed palette must contain at least one color.')
    if palette is not None:
        method = 'NEAREST_ALLOWED_PALETTE'
        allowed = {tuple(color) for color in palette}
        needed = any(tuple(color) not in allowed for color in np.unique(pixels, axis=0)) if len(pixels) else False
    else:
        method = 'MEDIAN_CUT'
        needed = before > max_colors
    output = directory / 'quantized.png'
    changed = 0
    if needed:
        mapped = _nearest(pixels, palette) if palette is not None else _median_cut(pixels, max_colors)
        changed = int(np.any(mapped != pixels, axis=1).sum())
        rgba[opaque, :3] = mapped
        Image.fromarray(rgba, 'RGBA').save(output)
    else:
        shutil.copyfile(source, output)
    after_pixels = rgba[opaque][:, :3]
    after = _unique_count(after_pixels)
    result_palette = [f'#{r:02X}{g:02X}{b:02X}' for r, g, b in
                      (map(int, row) for row in np.unique(after_pixels, axis=0))] if len(after_pixels) else []
    report = {
        'step': 'palette_quantize', 'status': 'APPLIED' if needed else 'NOT_NEEDED', 'method': method,
        'max_colors': max_colors, 'allowed_palette': [f'#{r:02X}{g:02X}{b:02X}' for r, g, b in palette] if palette else None,
        'dither': 'NONE', 'alpha': 'PRESERVED_EXACTLY', 'dimensions': 'PRESERVED_EXACTLY',
        'unique_colors_before': before, 'unique_colors_after': after, 'changed_pixels': changed,
        'opaque_pixels': int(opaque.sum()), 'result_palette': result_palette,
        'source': str(source), 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'output': str(output), 'output_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
        'human_review': 'REVIEW_REQUIRED', 'approval_effect': 'NONE',
    }
    (directory / 'quantize_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    (directory / 'quantize_report.md').write_text('\n'.join([
        '# Palette quantization', '', f'- **Status:** {report["status"]} ({method}, no dither)',
        f'- **Unique colors:** {before} -> {after} (budget {max_colors})',
        f'- **Changed pixels:** {changed} of {report["opaque_pixels"]} opaque',
        '- **Alpha / dimensions:** preserved exactly', '- **Review:** REVIEW_REQUIRED; Pixel Gate re-analyzes the result', '']),
        encoding='utf-8')
    return output, report
