"""Project palette files, background-preserving projection and delivery palette conformance."""
import numpy as np
import pytest
from PIL import Image

from assetpipe.pipelines import pixel_static
from assetpipe.pixel.palette import load_palette_file
from assetpipe.pixel.quantize import quantize_candidate

GPL = """GIMP Palette
Name: test
Columns: 4
# comment
  0   0   0\tBlack
255 0 77 Red
41 173 255
"""


def test_reads_gpl_hex_and_paint_net(tmp_path):
    (tmp_path / 'a.gpl').write_text(GPL, encoding='utf-8')
    (tmp_path / 'b.hex').write_text('000000\nff004d\n\n29ADFF\n', encoding='utf-8')
    (tmp_path / 'c.txt').write_text(';paint.net\nFF000000\nFFFF004D\nFF29ADFF\n', encoding='utf-8')
    expected = ['#000000', '#FF004D', '#29ADFF']
    for name, kind in (('a.gpl', 'GIMP_GPL'), ('b.hex', 'LOSPEC_HEX'), ('c.txt', 'PAINT_NET_TXT')):
        loaded = load_palette_file(tmp_path / name)
        assert loaded['colors'] == expected and loaded['format'] == kind and len(loaded['sha256']) == 64


@pytest.mark.parametrize('name, text, match', [
    ('x.gpl', 'not gimp\n1 2 3\n', 'must start'),
    ('x.gpl', 'GIMP Palette\n1 2 300\n', 'line 2'),
    ('x.hex', '00000\n', 'line 1'),
    ('x.hex', '000000\n000000\n', 'DUPLICATE'),
    ('x.hex', '\n', 'EMPTY'),
    ('x.txt', '80000000\n', 'opaque'),
    ('x.act', '', 'UNSUPPORTED'),
])
def test_invalid_palette_files_are_rejected(tmp_path, name, text, match):
    (tmp_path / name).write_text(text, encoding='utf-8')
    with pytest.raises(ValueError, match=match):
        load_palette_file(tmp_path / name)


def _candidate(tmp_path):
    image = np.full((64, 64, 3), 252, dtype=np.uint8)
    image[10:50, 20:44] = (200, 20, 70)    # near #FF004D
    image[20, 30] = (250, 250, 250)        # light highlight inside the subject, within bg tolerance
    image[30, 30] = (60, 60, 60)           # near black
    path = tmp_path / 'refined.png'
    Image.fromarray(image, 'RGB').save(path)
    return path


PALETTE = ['#000000', '#FF004D', '#29ADFF']


def test_background_is_kept_exactly_and_everything_else_snaps_to_palette(tmp_path):
    out, report = quantize_candidate(_candidate(tmp_path), tmp_path / 'q', allowed_palette=PALETTE,
                                     background=((255, 255, 255), 10))
    rgb = np.asarray(Image.open(out).convert('RGB'))
    assert tuple(rgb[0, 0]) == (255, 255, 255) and tuple(rgb[15, 25]) == (255, 0, 77)
    assert tuple(rgb[30, 30]) == (0, 0, 0)
    assert tuple(rgb[20, 30]) == (255, 255, 255)  # bg-like highlight keeps bg color (enclosed review item)
    colors = {tuple(c) for c in rgb.reshape(-1, 3)}
    assert colors <= {(0, 0, 0), (255, 0, 77), (41, 173, 255), (255, 255, 255)}
    assert report['method'] == 'NEAREST_ALLOWED_PALETTE_KEEP_BACKGROUND'
    assert report['background_kept']['pixels'] == 64 * 64 - 40 * 24 + 1


def test_background_keep_requires_palette(tmp_path):
    with pytest.raises(ValueError, match='explicit palette'):
        quantize_candidate(_candidate(tmp_path), tmp_path / 'q', background=((255, 255, 255), 10))


def test_gate_palette_adds_background_only_for_transparent_delivery():
    brief = {'constraints': {'palette': list(PALETTE)}}
    manifest = {}
    allowed = pixel_static.gate_palette(brief, {'background_rgb': [255, 255, 255], 'tolerance': 10}, manifest)
    assert allowed == PALETTE + ['#FFFFFF'] and manifest['gate_palette']['background_exception'] == '#FFFFFF'
    assert pixel_static.manifest_gate_palette({**manifest, 'asset_brief': brief}) == allowed
    assert pixel_static.gate_palette(brief, None, {}) == PALETTE
    assert pixel_static.gate_palette({'constraints': {'palette': []}}, {'background_rgb': [255, 255, 255]}, {}) is None


class _FakeAseprite:
    def __init__(self, config):
        pass

    def export(self, images, directory, name):
        return {'status': 'PASS', 'master': str(directory / 'master.aseprite')}


def test_delivery_reports_enclosed_background_as_palette_review(monkeypatch, tmp_path):
    import assetpipe.providers.aseprite as aseprite
    monkeypatch.setattr(aseprite, 'AsepriteProvider', _FakeAseprite)
    out, _ = quantize_candidate(_candidate(tmp_path), tmp_path / 'q', allowed_palette=PALETTE,
                                background=((255, 255, 255), 10))
    manifest = {'pipeline_steps': [], 'asset_id': 'x'}
    pixel_static.transparent_delivery(out, {'background_rgb': [255, 255, 255], 'tolerance': 10}, None,
                                      tmp_path, manifest, [64, 64], palette=PALETTE)
    conformance = manifest['transparent_delivery']['palette_conformance']
    assert conformance == {'status': 'REVIEW_REQUIRED', 'colors_outside_palette': ['#FFFFFF'], 'pixels_outside_palette': 1}
    assert manifest['transparent_delivery']['status'] == 'ENCLOSED_BACKGROUND_REVIEW_REQUIRED'


def test_cli_palette_file_fills_brief_and_pins_source(monkeypatch, tmp_path, capsys):
    from pathlib import Path
    from assetpipe import cli
    root = Path(__file__).resolve().parents[2]
    (tmp_path / 'p.hex').write_text('000000\nFF004D\n', encoding='utf-8')
    captured = {}
    monkeypatch.setattr(cli, 'create', lambda brief, *a, **k: captured.update(brief=brief, kwargs=k) or 'manifest')
    assert cli.main(['--root', str(root), 'create', '--type', 'pixel-static', '--prompt', 'knight',
                     '--palette-file', str(tmp_path / 'p.hex')]) == 0
    assert captured['brief']['constraints']['palette'] == ['#000000', '#FF004D']
    assert captured['kwargs']['palette_source']['color_count'] == 2
    assert cli.main(['--root', str(root), 'create', '--type', 'sfx', '--prompt', 'hit',
                     '--palette-file', str(tmp_path / 'p.hex')]) == 1
    assert 'only supported for PIXEL_STATIC' in capsys.readouterr().err
