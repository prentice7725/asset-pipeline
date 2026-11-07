"""Read an explicit project palette file into the brief's ``constraints.palette`` color list.

Supported formats: GIMP ``.gpl`` (``R G B [name]`` rows), Lospec ``.hex`` (``RRGGBB`` per line) and
Paint.NET ``.txt`` (``AARRGGBB`` per line, ``;`` comments). The palette is never inferred from an
image; the file hash is returned so the run manifest can pin exactly which palette was used.
"""
import hashlib
import re
from pathlib import Path

MAX_COLORS = 256
_HEX6 = re.compile(r'^#?([0-9A-Fa-f]{6})$')
_HEX8 = re.compile(r'^([0-9A-Fa-f]{2})([0-9A-Fa-f]{6})$')


def _gpl(lines):
    if not lines or lines[0].strip() != 'GIMP Palette':
        raise ValueError('PALETTE_FILE_INVALID: .gpl must start with "GIMP Palette"')
    colors = []
    for number, line in enumerate(lines[1:], 2):
        text = line.strip()
        if not text or text.startswith('#') or re.match(r'^(Name|Columns)\s*:', text):
            continue
        parts = text.split()
        try:
            rgb = [int(v) for v in parts[:3]]
        except ValueError:
            raise ValueError(f'PALETTE_FILE_INVALID: line {number}: {text!r}') from None
        if len(rgb) != 3 or not all(0 <= v <= 255 for v in rgb):
            raise ValueError(f'PALETTE_FILE_INVALID: line {number}: {text!r}')
        colors.append('#%02X%02X%02X' % tuple(rgb))
    return colors


def _hex(lines):
    colors = []
    for number, line in enumerate(lines, 1):
        text = line.strip()
        if not text:
            continue
        match = _HEX6.match(text)
        if not match:
            raise ValueError(f'PALETTE_FILE_INVALID: line {number}: {text!r}')
        colors.append('#' + match.group(1).upper())
    return colors


def _paint_net(lines):
    colors = []
    for number, line in enumerate(lines, 1):
        text = line.strip()
        if not text or text.startswith(';'):
            continue
        match = _HEX8.match(text)
        if not match:
            raise ValueError(f'PALETTE_FILE_INVALID: line {number}: {text!r}')
        if match.group(1).upper() != 'FF':
            raise ValueError(f'PALETTE_FILE_INVALID: line {number}: palette colors must be opaque')
        colors.append('#' + match.group(2).upper())
    return colors


READERS = {'.gpl': ('GIMP_GPL', _gpl), '.hex': ('LOSPEC_HEX', _hex), '.txt': ('PAINT_NET_TXT', _paint_net)}


def load_palette_file(path):
    path = Path(path)
    if path.suffix.lower() not in READERS:
        raise ValueError(f'PALETTE_FILE_FORMAT_UNSUPPORTED: {path.suffix} (use .gpl, .hex or .txt)')
    data = path.read_bytes()
    kind, reader = READERS[path.suffix.lower()]
    colors = reader(data.decode('utf-8-sig').splitlines())
    duplicates = sorted({c for c in colors if colors.count(c) > 1})
    if duplicates:
        raise ValueError(f'PALETTE_FILE_DUPLICATE_COLORS: {duplicates[:5]}')
    if not colors:
        raise ValueError('PALETTE_FILE_EMPTY')
    if len(colors) > MAX_COLORS:
        raise ValueError(f'PALETTE_FILE_TOO_LARGE: {len(colors)} > {MAX_COLORS}')
    return {'path': str(path.resolve()), 'sha256': hashlib.sha256(data).hexdigest(), 'format': kind,
            'colors': colors, 'color_count': len(colors)}
