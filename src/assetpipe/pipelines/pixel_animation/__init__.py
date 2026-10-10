from pathlib import Path
from ...paths import resolve_path
import hashlib
import json
from PIL import Image
from ...pixel.direct.ported import run_direct
from ..._ported.pixel_gate.analyzer import analyze_image
from ..._ported.pixel_gate.report import write_report
from ...providers.aseprite import AsepriteProvider
from ...manifests import write
from ...motion.extractor import decode_direct_reference

def preflight(brief, resolver=None):
    production = brief.get('production', {})
    required = ['static_master', 'approval_record', 'motion_reference', 'selection', 'direct_profile']
    if any(not production.get(k) for k in required):
        raise ValueError('Pixel animation requires approved static master, approval record, existing motion reference, reviewed semantic selection, and explicit direct_profile')
    production = dict(production)
    for key in ('static_master', 'approval_record'):
        production[key] = str(resolve_path(production[key], resolver))
    master = Path(production['static_master'])
    from ..pixel_static.approval import validate_approval
    validate_approval(master, production['approval_record'], resolver)
    for key in ('selection', 'motion_reference'):
        production[key] = str(resolve_path(production[key], resolver))
    selection = json.loads(Path(production['selection']).read_text(encoding='utf-8'))
    phases = ['CONTACT_A', 'DOWN_A', 'PASSING_A', 'UP_A', 'CONTACT_B', 'DOWN_B', 'PASSING_B', 'UP_B']
    rows = selection.get('selection', [])
    if selection.get('action') != brief['animation']['action'] or brief['animation']['action'] != 'walk':
        raise ValueError('Verified direct profile currently supports reviewed walk selections only')
    if [r.get('phase') for r in rows] != phases or not selection.get('reviewed_by'):
        raise ValueError('Eight unique reviewed semantic walk phases are required')
    indices = [r['source_frame'] for r in rows]
    if any(type(i) is not int or i < 0 for i in indices) or indices != sorted(set(indices)):
        raise ValueError('Semantic frames must be unique chronological nonnegative integers')
    if brief['animation']['frame_target'] not in (None, 8):
        raise ValueError('Verified direct profile requires eight frames')
    video = Path(production['motion_reference']).resolve()
    if resolve_path(selection.get('source_video', ''), resolver) != video:
        raise ValueError('Semantic selection source video mismatch')
    if production['direct_profile'] != 'blue_tunic_white_matte_v1':
        raise ValueError('Unknown verified direct profile')
    return production, master, video, indices

def run(brief, config, directory, manifest):
    production, master, video, indices = preflight(brief)
    canvas = brief['constraints']['resolution'] or [160, 160]
    with Image.open(master) as opened:
        colors = sorted(set(opened.convert('RGBA').getdata()))
        palette = ['#%02X%02X%02X' % p[:3] for p in colors if p[3]]
    if brief['constraints']['palette'] and set(brief['constraints']['palette']) != set(palette):
        raise ValueError('Requested palette conflicts with approved master palette')
    extracted = directory / '010_source_frames'
    decode = decode_direct_reference(video, extracted, max(indices))
    if any(not (extracted / f'frame_{i:04d}.png').is_file() for i in indices):
        raise ValueError('Motion reference has insufficient frames')
    manifest['pipeline_steps'].append({'step': 'reviewed_semantic_selection_and_extraction', 'status': 'PASS', 'decoder': decode, 'source_video_sha256': hashlib.sha256(video.read_bytes()).hexdigest(), 'selection_sha256': hashlib.sha256(Path(production['selection']).read_bytes()).hexdigest()})
    alignment = run_direct(asset_id=brief['asset_id'], static_master=master, source_video=video, source_frames=extracted,
        selection_path=production['selection'], output_dir=directory / '020_direct', canvas=canvas, profile=production['direct_profile'])
    paths = [Path(row['final_path']) for row in alignment['frames']]
    manifest['pipeline_steps'].append({'step': 'CHARACTER_LOCAL_DIRECT', 'status': 'PASS', 'report': str(directory / '020_direct/alignment_report.json')})
    reports = []
    for path in paths:
        report = analyze_image(path, max_colors=len(palette), allowed_palette=palette, target_width=canvas[0], target_height=canvas[1])
        write_report(report, directory / '030_pixel_gate' / path.stem)
        reports.append(report)
    manifest['qa_results'].extend(reports)
    if any(r['status'] != 'PASS' for r in reports):
        raise ValueError('Pixel Gate did not PASS every animation frame')
    manifest['pipeline_steps'].append({'step': 'pixel_gate', 'status': 'PASS', 'frames_passed': len(reports)})
    export = AsepriteProvider(config).export(paths, directory / '040_aseprite', brief['asset_id'], brief['animation']['action'])
    manifest['qa_results'].append(export)
    manifest['pipeline_steps'].append({'step': 'aseprite_export', 'status': 'PASS', 'exact_rgba_match': export['pixel_integrity']['exact_rgba_match']})
    manifest['outputs'] = [str(p) for p in paths] + [export['master'], export['sprite_sheet'], export['json_metadata']]
    manifest['status'] = 'EXPORT_READY_REVIEW_REQUIRED'
    manifest['game_ready'] = False
    return manifest
