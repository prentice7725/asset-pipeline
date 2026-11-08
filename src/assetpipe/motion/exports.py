"""Native engine resource formatting for a verified, still-unapproved recipe."""
import json
import re
import shutil
from pathlib import Path
from fractions import Fraction

from PIL import Image

from .recipe import inspect_recipe
from ..factory.provenance import fingerprint
from ..manifests import write
from ..paths import RootResolver


def resource_names(action, asset_id):
    """엔진 리소스 이름. 동작별로 파일과 키가 겹치지 않게 하고, 쓸 수 없는 문자는 밑줄로 바꾼다."""
    def slug(value):
        return re.sub(r'[^a-z0-9]+', '_', str(value).lower()).strip('_')
    name = slug(action) or 'motion'
    return {'animation': name, 'godot_resource': f'{name}.tres', 'phaser_key': f'{slug(asset_id) or "asset"}_{name}'}


def export_candidate(candidate, expected_sha256, output, root, *, action, asset_id, allowed_roots=None):
    root = Path(root).resolve(strict=True)
    outputs = RootResolver([root], base=root)
    candidate = outputs(candidate)
    inspect_recipe(candidate, root, expected_sha256=expected_sha256, allowed_roots=allowed_roots)
    output = outputs(output, strict=False)
    workspace = outputs(root / 'workspace', strict=False)
    if (workspace != root / 'workspace' or output == workspace or not output.is_relative_to(workspace)
            or candidate.is_relative_to(output) or output.is_relative_to(candidate)):
        raise ValueError('MOTION_EXPORT_OUTPUT_INVALID')
    atlas = json.loads((candidate / 'atlas.json').read_text(encoding='utf-8'))
    frames = atlas['frames']
    fps = float(Fraction(atlas['fps']))
    output.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(candidate / 'sprites.png', output / 'sprites.png')
    if fingerprint(output / 'sprites.png') != fingerprint(candidate / 'sprites.png'):
        raise ValueError('MOTION_EXPORT_SOURCE_CHANGED')
    write_engine_resources(output, frames, fps, action=action, asset_id=asset_id,
                           placement={'candidate_manifest_sha256': expected_sha256})
    inspect_recipe(candidate, root, expected_sha256=expected_sha256, allowed_roots=allowed_roots)
    return [{'path': str(path), 'sha256': fingerprint(path)} for path in sorted(output.iterdir())]


def write_engine_resources(output, frames, fps, *, action, asset_id, placement, loop=True, durations_ms=None):
    """output/sprites.png 옆에 Godot SpriteFrames, Phaser atlas·animation, placement.json을 쓴다.
    frames: rect [x, y, w, h], pivot [x, y], original_source_frame_index.
    durations_ms(선택): 프레임별 표시 시간. Godot는 기본 간격의 배수, Phaser는 기본 간격에 더할 시간으로 쓴다."""
    output = Path(output)
    base_ms = 1000 / fps
    if durations_ms is not None and len(durations_ms) != len(frames):
        raise ValueError('MOTION_EXPORT_DURATIONS: one duration per frame')
    relative = [1.0] * len(frames) if durations_ms is None else [round(d / base_ms, 4) for d in durations_ms]
    names = resource_names(action, asset_id)
    parts = [f'[gd_resource type="SpriteFrames" load_steps={len(frames)+2} format=3]',
             '[ext_resource type="Texture2D" path="sprites.png" id="1_sheet"]']
    native = {}
    animation = []
    for i, frame in enumerate(frames):
        x, y, w, h = frame['rect']
        parts.append(f'[sub_resource type="AtlasTexture" id="Frame_{i}"]\n'
                     f'atlas = ExtResource("1_sheet")\nregion = Rect2({x}, {y}, {w}, {h})\nfilter_clip = true')
        name = f'frame_{i:04d}'
        native[name] = {'frame': {'x': x, 'y': y, 'w': w, 'h': h}, 'rotated': False,
                        'trimmed': False, 'spriteSourceSize': {'x': 0, 'y': 0, 'w': w, 'h': h},
                        'sourceSize': {'w': w, 'h': h}}
        entry = {'key': names['phaser_key'], 'frame': name}
        if durations_ms is not None and round(durations_ms[i] - base_ms) != 0:
            entry['duration'] = round(durations_ms[i] - base_ms)
        animation.append(entry)
    parts += ['[resource]', 'animations = [{"frames": [' + ','.join(
        '{"duration":'+str(relative[i])+',"texture":SubResource("Frame_'+str(i)+'")}' for i in range(len(frames)))
        + f'],"loop":{"true" if loop else "false"},"name":&"{names["animation"]}","speed":{fps}}}]']
    (output / names['godot_resource']).write_text('\n\n'.join(parts)+'\n', encoding='utf-8')
    with Image.open(output / 'sprites.png') as image:
        width, height = image.size
    write(output / 'phaser-atlas.json', {'frames': native,
          'meta': {'image': 'sprites.png', 'size': {'w': width, 'h': height}, 'scale': '1'}})
    write(output / 'phaser-animation.json', {'key': names['phaser_key'], 'frames': animation,
                                           'frameRate': fps, 'repeat': -1 if loop else 0})
    pivot = frames[0]['pivot']
    size = frames[0]['rect'][2:]
    write(output / 'placement.json', {'source_pivot': pivot, 'frame_size': size, **placement,
        'godot': {'centered': False, 'offset': [-v for v in pivot]},
        'animation': names,
        'phaser': {'texture_key': names['phaser_key'], 'origin': [pivot[0]/size[0], pivot[1]/size[1]]},
        'source_frame_indices': [row['original_source_frame_index'] for row in frames],
        'review_state': 'REVIEW_REQUIRED', 'game_ready': False})
