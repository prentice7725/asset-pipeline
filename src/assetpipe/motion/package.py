"""Offline nonpixel video receipt -> existing extraction -> review atlas.

No generation, alpha inference, pixel conversion, or provider verification.
"""
import json
import math
import re
import shutil
import subprocess
from fractions import Fraction
from pathlib import Path

from PIL import Image

from ..factory.planner import plan_file
from ..factory.provenance import fingerprint
from ..manifests import now, write
from ..paths import RootResolver
from .extractor import decode_direct_reference, extract_motion


def _probe(video):
    executable = shutil.which('ffprobe')
    if not executable:
        raise ValueError('MOTION_FFPROBE_UNAVAILABLE')
    command = [executable, '-v', 'error', '-select_streams', 'v',
               '-show_entries', 'stream=width,height,avg_frame_rate,r_frame_rate,duration:format=duration',
               '-of', 'json', str(video)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=30, check=True)
    data = json.loads(result.stdout)
    streams = data.get('streams', [])
    if len(streams) != 1:
        raise ValueError('MOTION_VIDEO_INVALID: exactly one video stream required')
    stream = streams[0]
    fps = Fraction(stream['avg_frame_rate'])
    duration = float(stream.get('duration', data.get('format', {}).get('duration', 0)))
    width, height = stream['width'], stream['height']
    if (fps <= 0 or fps > 60 or not math.isfinite(duration) or not 0 < duration <= 10
            or not 0 < width <= 2048 or not 0 < height <= 2048
            or fps * duration > 240):
        raise ValueError('MOTION_VIDEO_LIMIT: max 10s / 240 frames / 2048px / 60fps')
    if Fraction(stream['r_frame_rate']) != fps:
        raise ValueError('MOTION_TIMING_UNSUPPORTED: constant frame rate required')
    timeline_command = [executable, '-v', 'error', '-select_streams', 'v',
                        '-read_intervals', '%+#241', '-show_frames',
                        '-show_entries', 'frame=best_effort_timestamp_time,width,height',
                        '-of', 'json', str(video)]
    timeline = subprocess.run(timeline_command, capture_output=True, text=True,
                              timeout=30, check=True)
    frames = json.loads(timeline.stdout).get('frames', [])
    if not 1 <= len(frames) <= 240:
        raise ValueError('MOTION_VIDEO_LIMIT: invalid frame count')
    start = float(frames[0]['best_effort_timestamp_time'])
    for index, frame in enumerate(frames):
        timestamp = float(frame['best_effort_timestamp_time'])
        if ([frame['width'], frame['height']] != [width, height]
                or not math.isfinite(timestamp) or not math.isfinite(start)
                or abs(timestamp - start - index / float(fps)) > 0.00001):
            raise ValueError('MOTION_TIMING_UNSUPPORTED: variable timing or frame size')
    return {'command': command, 'timeline_command': timeline_command,
            'frame_count': len(frames), 'source_start_seconds': start,
            'fps': str(fps), 'duration_seconds': duration,
            'size': [width, height]}


def package_video(request_path, video, expected_sha256, output, root, *, allowed_roots=None):
    """Package a separately supplied video as research; source consumption is UNKNOWN.

    Explicit request binds parent images but cannot prove the video used them.
    The caller must retain the provider receipt for later real E2E validation.
    """
    root = Path(root).resolve(strict=True)
    resolver = RootResolver(allowed_roots if allowed_roots is not None else [root], base=root)
    output_resolver = RootResolver([root], base=root)
    planned = plan_file(request_path, root, allowed_roots=resolver.roots)
    if (planned['output_mode'] != 'IMAGE_TO_SPRITE'
            or planned['factory_line'] not in {'NONPIXEL', 'REFERENCE_MOTION'}
            or not planned['images']):
        raise ValueError('MOTION_SOURCE_UNSUPPORTED: existing nonpixel/reference images required')
    if planned['motion_contract']['background_policy'] != 'PRESERVE_OR_REVIEW':
        raise ValueError('MOTION_ALPHA_UNAVAILABLE: explicit alpha processing requires separate validation')
    if not isinstance(expected_sha256, str) or not re.fullmatch('[a-f0-9]{64}', expected_sha256):
        raise ValueError('MOTION_SOURCE_HASH_REQUIRED')
    video = resolver(video)
    if not video.is_file() or fingerprint(video) != expected_sha256:
        raise ValueError('MOTION_SOURCE_CHANGED: video hash mismatch')
    output = output_resolver(output, strict=False)
    # Production modules and config are never artifact destinations.
    artifact_root = output_resolver(root / 'workspace', strict=False)
    if (artifact_root != root / 'workspace'
            or not output.is_relative_to(artifact_root) or output == artifact_root):
        raise ValueError('MOTION_OUTPUT_INVALID: use a fresh directory under workspace')
    if any(Path(item['path']).is_relative_to(output) for item in planned['images']):
        raise ValueError('MOTION_OUTPUT_INVALID: output contains a source')
    probe = _probe(video)
    fps = float(Fraction(probe['fps']))
    motion = planned['motion_contract']
    if (not math.isclose(motion['fps'], fps, rel_tol=1e-6)
            or abs(motion['duration_seconds'] - probe['duration_seconds']) > 1 / fps):
        raise ValueError('MOTION_CONTRACT_MISMATCH: video fps/duration differs from request')
    output.mkdir(parents=True, exist_ok=False)  # No overwrite or resume/retry.
    receipt = {'schema_version': 1, 'type': 'OFFLINE_MOTION_PACKAGE', 'status': 'STARTED',
               'started_at': now(), 'plan': planned, 'video_sha256': expected_sha256,
               'probe': probe, 'generation_status': 'NOT_RUN', 'provider_input_consumption': 'NOT_VERIFIED',
               'review_state': 'REVIEW_REQUIRED', 'game_ready': False,
               'alpha_policy': 'PRESERVED_OPAQUE_VIDEO', 'retry': 'NONE', 'fallback': 'NONE'}
    manifest = output / 'run_manifest.json'
    try:
        write(manifest, receipt)
        original = output / ('original' + video.suffix)
        shutil.copyfile(video, original)
        if fingerprint(original) != expected_sha256:
            raise ValueError('MOTION_SOURCE_CHANGED: video changed during copy')
        receipt['original_video'] = {'path': str(original), 'sha256': fingerprint(original)}
        # Decode at most one sentinel beyond our limit; never silently truncate.
        receipt['decoder'] = decode_direct_reference(original, output / 'decoded', 240)
        count = receipt['decoder']['decoded_count']
        if count != probe['frame_count'] or count != motion['target_frames']:
            raise ValueError('MOTION_FRAME_COUNT_MISMATCH: no truncation or implicit resampling')
        report = extract_motion(output / 'decoded', output / 'extraction',
                                sequence_fps=fps, sample_fps=fps)
        rows = report['frames']
        if len(rows) != count:
            raise ValueError('MOTION_FRAME_COUNT_MISMATCH: sampled timeline incomplete')
        width, height = probe['size']
        columns = min(count, max(1, 4096 // width))
        atlas_height = math.ceil(count / columns) * height
        if columns * width * atlas_height > 32_000_000:
            raise ValueError('MOTION_ATLAS_LIMIT: max 32 million pixels')
        atlas = Image.new('RGBA', (columns * width, atlas_height))
        frames = []
        for index, row in enumerate(rows):
            path = output_resolver(row['aligned_path'])
            raw = output_resolver(row['raw_path'])
            if not all(item.is_relative_to(output / 'extraction') for item in [path, raw]):
                raise ValueError('MOTION_FRAME_PATH_INVALID')
            with Image.open(path) as image:
                if image.size != (width, height):
                    raise ValueError('MOTION_FRAME_SIZE_CHANGED')
                rgba = image.convert('RGBA')
                x, y = index % columns * width, index // columns * height
                atlas.paste(rgba, (x, y))
            frames.append({'index': index, 'source_frame_index': row['source_frame_index'],
                           'timestamp_seconds': index / fps, 'duration_ms': 1000 / fps,
                           'rect': [x, y, width, height], 'pivot': [width / 2, height - 2],
                           'alignment_offset': row['alignment_offset'],
                           'alignment_status': row['alignment_status'],
                           'raw_path': str(raw), 'raw_sha256': fingerprint(raw),
                           'path': str(path), 'sha256': fingerprint(path)})
        # Held/repeated frames stay in chronological order; candidate filtering is advisory.
        atlas.save(output / 'sprites.png')
        write(output / 'atlas.json', {'fps': probe['fps'], 'frames': frames,
                                     'pivot_policy': 'CANVAS_BOTTOM_CENTER_REVIEW_REQUIRED',
                                     'loop_quality': 'NOT_EVALUATED', 'alpha_quality': 'REVIEW_REQUIRED'})
        if plan_file(request_path, root, allowed_roots=resolver.roots) != planned:
            raise ValueError('MOTION_SOURCE_CHANGED: request or parent changed')
        write(output / 'review.json', {'status': 'REVIEW_REQUIRED', 'reviewed_by': None,
                                      'checks': {key: None for key in [
                                          'identity', 'equipment', 'silhouette', 'pivot_jitter',
                                          'loop', 'alpha', 'game_readability', 'aseprite_review']}})
        receipt.update(status='OFFLINE_PACKAGE_REVIEW_REQUIRED',
                       qa={'frame_count': count, 'frame_order': 'PRESERVED',
                           'dimensions': 'PASS', 'animation_quality': 'NOT_EVALUATED'},
                       outputs=[{'path': str(path), 'sha256': fingerprint(path)} for path in [
                           original, output / 'sprites.png', output / 'atlas.json',
                           output / 'extraction/motion_report.json', output / 'review.json']])
    except Exception as exc:
        receipt.update(status='FAILED', error=str(exc))
        raise
    finally:
        receipt['finished_at'] = now()
        write(manifest, receipt)
    return manifest
