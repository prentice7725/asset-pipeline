from pathlib import Path
from ...providers.comfyui import ComfyUIProvider
from ...providers.aseprite import AsepriteProvider
from ..._ported.pixel_gate.analyzer import analyze_image
from ..._ported.pixel_gate.refiner import refine_image
from ..._ported.pixel_gate.resolution import run_resolution_gate
from ..._ported.pixel_gate.report import write_report

def run(brief, workflow, config, directory, manifest, seed):
    paths = ComfyUIProvider(config).generate(brief, workflow, directory / '010_generation', seed)
    if len(paths) != 1:
        raise ValueError('Static pipeline expects one image candidate')
    size = brief['constraints']['resolution']
    initial = analyze_image(paths[0], max_colors=config.section('pixel').get('max_colors', 32))
    write_report(initial, directory / '020_analyzer')
    manifest['qa_results'].append(initial)
    manifest['pipeline_steps'].append({'step': 'candidate_analysis', 'status': initial['status']})
    # Only binary alpha is automatic. Palette/resizing/silhouette changes require explicit review.
    refined = refine_image(paths[0], directory / '030_refiner', profile='binary_alpha_only', analyzer_max_colors=config.section('pixel').get('max_colors', 32))
    manifest['pipeline_steps'].append({'step': 'safe_refine', 'operation': 'binary_alpha_only', 'report': str(directory / '030_refiner/refine_report.json')})
    path = directory / '030_refiner/refined.png'
    gate = analyze_image(path, max_colors=config.section('pixel').get('max_colors', 32), allowed_palette=brief['constraints']['palette'] or None,
        target_width=size[0] if size else None, target_height=size[1] if size else None)
    write_report(gate, directory / '040_pixel_gate')
    manifest['qa_results'].append(gate)
    manifest['pipeline_steps'].append({'step': 'pixel_gate', 'status': gate['status']})
    manifest['outputs'] = [str(path)]
    if gate['status'] == 'FAIL':
        raise ValueError('Pixel Gate failed; downstream Aseprite export locked')
    if gate['status'] != 'PASS':
        manifest['status'] = 'PIXEL_GATE_REVIEW_REQUIRED'
        return manifest
    resolution = run_resolution_gate(path, directory / '050_resolution', profile_name='asset_brief', profile={}, project_root=config.root, candidates=[size[1]] if size else None)
    manifest['qa_results'].append(resolution)
    manifest['status'] = 'RESOLUTION_REVIEW_REQUIRED'
    manifest['pipeline_steps'].append({'step': 'resolution_gate', 'status': 'REVIEW_REQUIRED', 'report': str(directory / '050_resolution/resolution_report.json')})
    return manifest

def export_reviewed(config, run_dir, review_path, manifest):
    import json
    import hashlib
    directory = Path(run_dir).resolve()
    review = json.loads(Path(review_path).read_text(encoding='utf-8'))
    report_path = directory / '050_resolution/resolution_report.json'
    if manifest['status'] != 'RESOLUTION_REVIEW_REQUIRED':
        raise ValueError('Run is not waiting for resolution review')
    if review.get('status') != 'SELECTED' or review.get('candidate_status') != 'AUTO_PASS_REVIEW_REQUIRED' or not review.get('reviewed') or not review.get('reason') or not review.get('reviewed_by'):
        raise ValueError('Explicit passing resolution review with reviewer and reason is required')
    if review.get('source_report_sha256') != hashlib.sha256(report_path.read_bytes()).hexdigest():
        raise ValueError('Resolution report changed since review')
    report = json.loads(report_path.read_text(encoding='utf-8'))
    row = next(r for r in report['candidates'] if r['logical_height'] == review['selected_resolution'])
    if row.get('status') != 'AUTO_PASS_REVIEW_REQUIRED':
        raise ValueError('Selected resolution candidate did not pass')
    candidate = Path(row['image'])
    if hashlib.sha256(candidate.read_bytes()).hexdigest() != row['sha256']:
        raise ValueError('Reviewed candidate hash changed')
    gate = analyze_image(candidate, target_width=row['width'], target_height=row['height'], allowed_palette=manifest['asset_brief']['constraints']['palette'] or None)
    manifest['qa_results'].append(gate)
    if gate['status'] != 'PASS':
        raise ValueError('Reviewed candidate Pixel Gate did not PASS')
    export = AsepriteProvider(config).export([candidate], directory / '060_aseprite', manifest['asset_id'])
    manifest['qa_results'].append(export)
    manifest['outputs'] += [export['master'], export['sprite_sheet'], export['json_metadata']]
    manifest['static_validation'] = {
        'resolution_review': str(Path(review_path).resolve()),
        'resolution_review_sha256': hashlib.sha256(Path(review_path).read_bytes()).hexdigest(),
        'resolution_report_sha256': hashlib.sha256(report_path.read_bytes()).hexdigest(),
        'candidate': str(candidate.resolve()),
        'candidate_sha256': hashlib.sha256(candidate.read_bytes()).hexdigest(),
        'export': str(Path(export['sprite_sheet']).resolve()),
        'export_sha256': hashlib.sha256(Path(export['sprite_sheet']).read_bytes()).hexdigest(),
        'aseprite_master': str(Path(export['master']).resolve()),
        'aseprite_master_sha256': hashlib.sha256(Path(export['master']).read_bytes()).hexdigest(),
    }
    manifest['status'] = 'EXPORT_READY_REVIEW_REQUIRED'
    return manifest
