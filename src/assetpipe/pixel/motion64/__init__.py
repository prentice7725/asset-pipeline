"""Pixel64 walk animation from one motion video: reference, contact sheet, reviewed selection,
64px pixelization locked to the approved master palette, measurements and delivery.

Machine steps only report; phase choice and art judgement stay with the human reviewer."""
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from ...manifests import now, write

PHASE_COUNTS = (4, 6, 8)
REFERENCE_SIZE = 768
DEFAULT_TOLERANCE = 24


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _rgb(path):
    with Image.open(path) as image:
        return np.asarray(image.convert('RGB'), dtype=np.int16)


def _border_color(rgb):
    border = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
    colors, counts = np.unique(border, axis=0, return_counts=True)
    return tuple(int(v) for v in colors[counts.argmax()])


def _mask(rgb, background, tolerance):
    return np.abs(rgb - np.asarray(background, dtype=np.int16)).max(axis=2) > tolerance


def _bbox(mask):
    ys, xs = np.nonzero(mask)
    if not len(ys):
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def master_geometry(master, tolerance=DEFAULT_TOLERANCE):
    """Subject box, baseline, palette and background of the approved opaque 64px master."""
    rgb = _rgb(master)
    background = _border_color(rgb)
    mask = _mask(rgb, background, tolerance)
    box = _bbox(mask)
    if box is None:
        raise ValueError('PIXEL64_MOTION_MASTER_EMPTY: master has no subject pixels')
    colors = np.unique(rgb[mask], axis=0)
    return {'size': [rgb.shape[1], rgb.shape[0]], 'background_rgb': list(background), 'bbox': list(box),
            'subject_height': box[3] - box[1], 'baseline': box[3], 'center_x': (box[0] + box[2]) / 2,
            'palette': ['#%02X%02X%02X' % tuple(int(v) for v in c) for c in colors]}


def build_reference(master, output, *, size=REFERENCE_SIZE):
    """Nearest-neighbour integer upscale of the approved master for the video model's reference image."""
    with Image.open(master) as image:
        source = image.convert('RGB')
    if size % source.width or size % source.height or source.width != source.height:
        raise ValueError('PIXEL64_MOTION_REFERENCE_SCALE: reference size must be an integer multiple of a square master')
    scale = size // source.width
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    path = output / 'reference.png'
    source.resize((size, size), Image.NEAREST).save(path)
    record = {'kind': 'PIXEL64_MOTION_REFERENCE', 'master': str(Path(master).resolve()), 'master_sha256': _sha(master),
              'scale': scale, 'size': [size, size], 'resample': 'NEAREST', 'reference': str(path), 'reference_sha256': _sha(path),
              'created_at': now()}
    write(output / 'reference.json', record)
    return record


def contact_sheet(frames_dir, output, *, columns=8, thumb=128):
    """Numbered thumbnails of every decoded frame so a person can choose walk phases."""
    frames = sorted(Path(frames_dir).glob('frame_*.png'))
    if not frames:
        raise ValueError('PIXEL64_MOTION_NO_FRAMES')
    rows = (len(frames) + columns - 1) // columns
    sheet = Image.new('RGB', (columns * thumb, rows * (thumb + 16)), (40, 40, 40))
    draw = ImageDraw.Draw(sheet)
    for i, path in enumerate(frames):
        with Image.open(path) as image:
            tile = image.convert('RGB').resize((thumb, thumb), Image.BILINEAR)
        x, y = (i % columns) * thumb, (i // columns) * (thumb + 16)
        sheet.paste(tile, (x, y + 16))
        draw.text((x + 3, y + 2), str(int(path.stem.split('_')[1])), fill=(255, 255, 0))
    sheet.save(output)
    return {'contact_sheet': str(output), 'frames': len(frames)}


def validate_selection(selection_path, video_sha256):
    """Reviewed walk selection: 4, 6 or 8 unique chronological source frames from this exact video."""
    selection = json.loads(Path(selection_path).read_text(encoding='utf-8'))
    frames = selection.get('frames')
    if selection.get('action') != 'walk':
        raise ValueError('PIXEL64_MOTION_SELECTION_ACTION: only walk is supported')
    if not str(selection.get('reviewed_by', '')).strip():
        raise ValueError('PIXEL64_MOTION_SELECTION_UNREVIEWED: reviewed_by is required')
    if selection.get('source_video_sha256') != video_sha256:
        raise ValueError('PIXEL64_MOTION_SELECTION_VIDEO_MISMATCH')
    if not isinstance(frames, list) or len(frames) not in PHASE_COUNTS:
        raise ValueError(f'PIXEL64_MOTION_SELECTION_COUNT: choose {PHASE_COUNTS} frames')
    if any(type(i) is not int or i < 0 for i in frames) or frames != sorted(set(frames)):
        raise ValueError('PIXEL64_MOTION_SELECTION_ORDER: frames must be unique chronological nonnegative integers')
    fps = selection.get('fps', 8)
    if type(fps) not in (int, float) or not 1 <= fps <= 30:
        raise ValueError('PIXEL64_MOTION_SELECTION_FPS: fps must be between 1 and 30')
    return {**selection, 'fps': fps, 'sha256': _sha(selection_path)}


def _snap(rgb, palette):
    colors = np.asarray([[int(h[i:i + 2], 16) for i in (1, 3, 5)] for h in palette], dtype=np.int32)
    flat = rgb.reshape(-1, 3).astype(np.int32)
    nearest = ((flat[:, None, :] - colors[None, :, :]) ** 2).sum(axis=2).argmin(axis=1)
    return colors[nearest].reshape(rgb.shape).astype(np.uint8)


def pixelize(frame_paths, master, output, *, tolerance=DEFAULT_TOLERANCE):
    """One shared transform for every frame: scale from the median subject height to the master's,
    anchor the median baseline and centre to the master's, then snap colours to the master palette.
    Per-frame drift is measured, not corrected, so walking-in-place stays honest."""
    geometry = master_geometry(master, tolerance)
    width, height = geometry['size']
    sources = [_rgb(p) for p in frame_paths]
    background = _border_color(sources[0])
    boxes = []
    for path, rgb in zip(frame_paths, sources):
        box = _bbox(_mask(rgb, background, tolerance))
        if box is None:
            raise ValueError(f'PIXEL64_MOTION_FRAME_EMPTY: {Path(path).name}')
        boxes.append(box)
    median_height = float(np.median([b[3] - b[1] for b in boxes]))
    scale = geometry['subject_height'] / median_height
    anchor_y = float(np.median([b[3] for b in boxes]))
    anchor_x = float(np.median([(b[0] + b[2]) / 2 for b in boxes]))
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    frames = []
    for index, (path, rgb) in enumerate(zip(frame_paths, sources)):
        scaled_size = (max(1, round(rgb.shape[1] * scale)), max(1, round(rgb.shape[0] * scale)))
        image = Image.fromarray(rgb.astype(np.uint8), 'RGB').resize(scaled_size, Image.BOX)
        coverage = Image.fromarray((_mask(rgb, background, tolerance) * 255).astype(np.uint8), 'L').resize(scaled_size, Image.BOX)
        left = round(anchor_x * scale - geometry['center_x'])
        top = round(anchor_y * scale - geometry['baseline'])
        window = (left, top, left + width, top + height)
        color = np.asarray(image.crop(window), dtype=np.int16)
        alpha = np.asarray(coverage.crop(window)) >= 128
        clipped = _touches_window(np.asarray(coverage) >= 128, window)
        rgba = np.zeros((height, width, 4), dtype=np.uint8)
        rgba[..., :3] = _snap(color, geometry['palette'])
        rgba[..., 3] = np.where(alpha, 255, 0)
        rgba[~alpha, :3] = 0
        destination = output / f'frame_{index:02d}.png'
        Image.fromarray(rgba, 'RGBA').save(destination)
        frames.append({'index': index, 'source': str(path), 'source_sha256': _sha(path), 'path': str(destination),
                       'sha256': _sha(destination), 'source_bbox': list(boxes[index]), 'clipped': clipped})
    report = {'kind': 'PIXEL64_MOTION_PIXELIZE', 'master': str(Path(master).resolve()), 'master_sha256': _sha(master),
              'master_geometry': geometry, 'source_background_rgb': list(background), 'tolerance': tolerance,
              'transform': {'scale': scale, 'median_source_height': median_height, 'anchor_source': [anchor_x, anchor_y],
                            'resample': 'BOX', 'alpha_threshold': 0.5, 'color': 'NEAREST_MASTER_PALETTE'},
              'frames': frames, 'measurements': measure([f['path'] for f in frames], master, tolerance),
              'review': 'HUMAN_REQUIRED', 'created_at': now()}
    write(output / 'pixelize_report.json', report)
    return report


def _touches_window(mask, window):
    left, top, right, bottom = window
    ys, xs = np.nonzero(mask)
    return bool(len(ys) and (xs.min() < left or ys.min() < top or xs.max() >= right or ys.max() >= bottom))


def measure(frame_paths, master, tolerance=DEFAULT_TOLERANCE):
    """Identity and stability numbers only; thresholds are set after the first real run."""
    geometry = master_geometry(master, tolerance)
    master_rgb = _rgb(master)
    master_mask = _mask(master_rgb, geometry['background_rgb'], tolerance)
    usage_master = _usage(master_rgb[master_mask], geometry['palette'])
    rows, previous = [], None
    for path in frame_paths:
        with Image.open(path) as image:
            rgba = np.asarray(image.convert('RGBA'))
        opaque = rgba[..., 3] == 255
        box = _bbox(opaque)
        row = {'path': str(path), 'opaque_pixels': int(opaque.sum()),
               'opaque_ratio_to_master': round(float(opaque.sum()) / float(master_mask.sum()), 3)}
        if box:
            row.update(bbox=list(box), height=box[3] - box[1], width=box[2] - box[0],
                       baseline_shift=box[3] - geometry['baseline'],
                       center_shift=round((box[0] + box[2]) / 2 - geometry['center_x'], 1),
                       palette_usage_l1=round(float(np.abs(_usage(rgba[opaque][:, :3], geometry['palette']) - usage_master).sum()), 3))
        if previous is not None:
            changed = (previous != rgba).any(axis=2) & (opaque | (previous[..., 3] == 255))
            union = opaque | (previous[..., 3] == 255)
            row['changed_fraction_vs_previous'] = round(float(changed.sum()) / max(1, int(union.sum())), 3)
        rows.append(row)
        previous = rgba
    return {'rule': 'REPORT_ONLY_THRESHOLDS_NOT_SET', 'frames': rows}


def _usage(pixels, palette):
    index = {tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)): n for n, h in enumerate(palette)}
    counts = np.zeros(len(palette))
    for color, count in zip(*np.unique(pixels.reshape(-1, 3), axis=0, return_counts=True)):
        n = index.get(tuple(int(v) for v in color))
        if n is not None:
            counts[n] += count
    return counts / max(1.0, counts.sum())


def pack_sheet(frame_paths, output, source_indices):
    """Horizontal strip of equal 64px frames for engine export; pivot is the bottom centre."""
    images = [Image.open(p).convert('RGBA') for p in frame_paths]
    width, height = images[0].size
    if any(image.size != (width, height) for image in images):
        raise ValueError('PIXEL64_MOTION_FRAME_SIZE_MISMATCH')
    sheet = Image.new('RGBA', (width * len(images), height), (0, 0, 0, 0))
    for i, image in enumerate(images):
        sheet.paste(image, (i * width, 0))
    sheet.save(output)
    return [{'rect': [i * width, 0, width, height], 'pivot': [width // 2, height], 'original_source_frame_index': source}
            for i, source in enumerate(source_indices)]


def build_animation(*, master, approval_record, video, selection_path, output, config, asset_id):
    """Approved master + one motion video + reviewed selection -> 64px walk candidate (REVIEW_REQUIRED)."""
    from ..._ported.pixel_gate.analyzer import analyze_image
    from ..._ported.pixel_gate.report import write_report
    from ...motion.exports import write_engine_resources
    from ...motion.extractor import decode_direct_reference
    from ...pipelines.pixel_static.approval import validate_approval
    from ...providers.aseprite import AsepriteProvider
    master, video, output = Path(master).resolve(), Path(video).resolve(), Path(output).resolve()
    validate_approval(master, approval_record)
    video_sha = _sha(video)
    selection = validate_selection(selection_path, video_sha)
    output.mkdir(parents=True, exist_ok=False)
    manifest = {'kind': 'PIXEL64_MOTION_ANIMATION', 'asset_id': asset_id, 'action': 'walk', 'status': 'RUNNING',
                'master': str(master), 'master_sha256': _sha(master), 'approval_record': str(Path(approval_record).resolve()),
                'approval_record_sha256': _sha(approval_record), 'video': str(video), 'video_sha256': video_sha,
                'selection': str(Path(selection_path).resolve()), 'selection_sha256': selection['sha256'],
                'frames_selected': selection['frames'], 'fps': selection['fps'], 'steps': [], 'created_at': now()}
    write(output / 'animation_manifest.json', manifest)
    try:
        decoded = output / '010_frames'
        decode = decode_direct_reference(video, decoded, max(selection['frames']))
        paths = [decoded / f'frame_{i:04d}.png' for i in selection['frames']]
        if any(not p.is_file() for p in paths):
            raise ValueError('PIXEL64_MOTION_VIDEO_TOO_SHORT: selected frame beyond the decoded video')
        manifest['steps'].append({'step': 'decode', 'status': 'PASS', 'decoder': decode})
        report = pixelize(paths, master, output / '020_pixel64')
        manifest['steps'].append({'step': 'pixelize', 'status': 'PASS', 'report': str(output / '020_pixel64/pixelize_report.json'),
                                  'clipped_frames': [f['index'] for f in report['frames'] if f['clipped']]})
        frames = [Path(f['path']) for f in report['frames']]
        palette = report['master_geometry']['palette']
        width, height = report['master_geometry']['size']
        gates = []
        for frame in frames:
            gate = analyze_image(frame, max_colors=len(palette), allowed_palette=palette, target_width=width, target_height=height)
            write_report(gate, output / '030_pixel_gate' / frame.stem)
            gates.append(gate['status'])
        manifest['steps'].append({'step': 'pixel_gate', 'status': 'PASS' if all(g == 'PASS' for g in gates) else 'FAIL', 'frames': gates})
        if any(g != 'PASS' for g in gates):
            raise ValueError('PIXEL64_MOTION_PIXEL_GATE_FAILED: not every frame passed')
        duration = round(1000 / selection['fps'])
        export = AsepriteProvider(config).export(frames, output / '040_aseprite', asset_id, 'walk', duration=duration)
        manifest['steps'].append({'step': 'aseprite', 'status': export['status'], 'master': export['master'],
                                  'exact_rgba_match': export['pixel_integrity']['exact_rgba_match']})
        engine = output / '050_engine'
        engine.mkdir()
        rects = pack_sheet(frames, engine / 'sprites.png', selection['frames'])
        write_engine_resources(engine, rects, float(selection['fps']), action='walk', asset_id=asset_id,
                               placement={'animation_manifest': str(output / 'animation_manifest.json')})
        manifest['steps'].append({'step': 'engine_export', 'status': 'PASS', 'output': str(engine)})
        manifest.update(status='EXPORT_READY_REVIEW_REQUIRED', review='HUMAN_REQUIRED', game_ready=False)
    except Exception as exc:
        manifest.update(status='FAILED', error=str(exc))
        write(output / 'animation_manifest.json', manifest)
        raise
    write(output / 'animation_manifest.json', manifest)
    return manifest
