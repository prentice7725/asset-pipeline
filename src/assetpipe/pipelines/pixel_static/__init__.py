from pathlib import Path
from ...providers.comfyui import ComfyUIProvider
from ...providers.aseprite import AsepriteProvider
from ..._ported.pixel_gate.analyzer import analyze_image
from ..._ported.pixel_gate.refiner import refine_image
from ..._ported.pixel_gate.resolution import run_resolution_gate
from ..._ported.pixel_gate.report import write_report

def run(brief, workflow, config, directory, manifest, seed):
    paths = ComfyUIProvider(config).generate(brief, workflow, directory / '010_generation', seed)
    # A workflow may save declared intermediates (e.g. the raw image before an in-graph refiner)
    # ahead of the single candidate; they are preserved and hashed, never gated or exported.
    preserved = workflow.get('preserved_intermediate_outputs', 0)
    if len(paths) != 1 + preserved:
        raise ValueError('Static pipeline expects one image candidate')
    if preserved:
        import hashlib
        manifest['pipeline_steps'].append({'step': 'generation_intermediates',
            'outputs': [{'path': str(p), 'sha256': hashlib.sha256(Path(p).read_bytes()).hexdigest()}
                        for p in paths[:preserved]]})
    return process_candidate(paths[-1], brief, config, directory, manifest,
                             transparent=workflow.get('transparent_delivery'))


def process_candidate(candidate, brief, config, directory, manifest, *, transparent=None):
    """Shared static gates for generated or explicitly imported existing candidates."""
    size = brief['constraints']['resolution']
    initial = analyze_image(candidate, max_colors=config.section('pixel').get('max_colors', 32))
    write_report(initial, directory / '020_analyzer')
    manifest['qa_results'].append(initial)
    manifest['pipeline_steps'].append({'step': 'candidate_analysis', 'status': initial['status']})
    # Only binary alpha is automatic. Palette/resizing/silhouette changes require explicit review.
    refined = refine_image(candidate, directory / '030_refiner', profile='binary_alpha_only', analyzer_max_colors=config.section('pixel').get('max_colors', 32))
    manifest['pipeline_steps'].append({'step': 'safe_refine', 'operation': 'binary_alpha_only', 'report': str(directory / '030_refiner/refine_report.json')})
    path = directory / '030_refiner/refined.png'
    pixel = config.section('pixel')
    palette = gate_palette(brief, transparent, manifest)
    if pixel.get('quantize_to_budget', True):
        # Color budget reduction is an explicit, recorded step; Pixel Gate re-analyzes the result
        # and the candidate still needs human review.
        from ...pixel.quantize import quantize_candidate
        background = ((transparent.get('background_rgb', (255, 255, 255)), transparent.get('tolerance', 10))
                      if transparent and brief['constraints']['palette'] else None)
        path, quantized = quantize_candidate(path, directory / '035_quantize', max_colors=pixel.get('max_colors', 32),
                                             allowed_palette=brief['constraints']['palette'] or None, background=background)
        manifest['qa_results'].append(quantized)
        # Keep the unquantized evidence visible: reducing colors does not make a smooth
        # illustration pixel art, so the reviewer sees what the source analysis found.
        manifest['pipeline_steps'].append({'step': 'palette_quantize', 'status': quantized['status'], 'operation': quantized['method'],
            'unique_colors_before': quantized['unique_colors_before'], 'unique_colors_after': quantized['unique_colors_after'],
            'source_analysis_status': initial['status'], 'source_failure_reasons': initial['reasons']['failure'],
            'report': str(directory / '035_quantize/quantize_report.json')})
    gate = analyze_image(path, max_colors=config.section('pixel').get('max_colors', 32), allowed_palette=palette,
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
    if transparent:
        transparent_delivery(path, transparent, config, directory, manifest, size,
                             palette=brief['constraints']['palette'] or None)
    return manifest


def gate_palette(brief, transparent, manifest):
    """Colors the opaque candidate may use: the brief palette, plus the declared background when a
    transparent delivery copy will remove it. Recorded so later review/approval gates use the same set."""
    palette = brief['constraints']['palette'] or None
    if palette and transparent:
        background = '#%02X%02X%02X' % tuple(int(v) for v in transparent.get('background_rgb', (255, 255, 255)))
        manifest['gate_palette'] = {'allowed': list(palette) + ([background] if background not in palette else []),
                                    'background_exception': background, 'reason': 'removed by transparent_delivery'}
        return manifest['gate_palette']['allowed']
    return palette


def manifest_gate_palette(manifest):
    return (manifest.get('gate_palette') or {}).get('allowed') or manifest['asset_brief']['constraints']['palette'] or None


def transparent_delivery(path, settings, config, directory, manifest, size, *, palette=None):
    """Binary-alpha delivery copy of the gated opaque candidate, declared per workflow.

    The opaque candidate stays the reviewed output. A border that is not the declared background
    (e.g. generated side bars) or enclosed background pockets stop here as review items with the
    reason recorded; hole seeds are never guessed. Aseprite round trip runs only on a produced copy.
    """
    from ...pixel.transparent import make_transparent
    from ...providers.aseprite import AsepriteProvider
    from ...manifests import write_new
    output = directory / '070_transparent'
    step = {'step': 'transparent_delivery', 'source': str(path)}
    try:
        report = make_transparent(path, output, background_rgb=settings.get('background_rgb', (255, 255, 255)),
                                  tolerance=settings.get('tolerance', 10), expected_size=tuple(size) if size else (64, 64),
                                  created_by='assetpipe pixel_static transparent_delivery')
    except ValueError as exc:
        code = str(exc).split(':', 1)[0]
        if not code.startswith('PIXEL64_TRANSPARENT_'):
            raise
        step.update(status='BLOCKED_REVIEW_REQUIRED', reason=str(exc))
        manifest['pipeline_steps'].append(step)
        manifest['transparent_delivery'] = {'status': 'BLOCKED_REVIEW_REQUIRED', 'reason': str(exc)}
        return
    step.update(status=report['status'], report=str(output / 'transparent_report.json'), output=report['output'],
                unresolved_enclosed_regions=len(report['unresolved_enclosed_regions']))
    conformance = None
    if palette:
        # Unresolved enclosed background pockets keep the background color and show up here.
        from ..._ported.pixel_gate.analyzer import _parse_color
        import numpy as np
        from PIL import Image
        with Image.open(report['output']) as opened:
            rgba = np.asarray(opened.convert('RGBA'))
        allowed = {_parse_color(c) for c in palette}
        opaque = rgba[rgba[..., 3] > 0][:, :3]
        outside = [tuple(int(v) for v in c) for c in np.unique(opaque, axis=0) if tuple(int(v) for v in c) not in allowed]
        outside_pixels = int(sum((opaque == np.asarray(c)).all(axis=1).sum() for c in outside))
        conformance = {'status': 'PASS' if not outside else 'REVIEW_REQUIRED', 'colors_outside_palette':
                       ['#%02X%02X%02X' % c for c in outside], 'pixels_outside_palette': outside_pixels}
        step['palette_conformance'] = conformance
    export = AsepriteProvider(config).export([Path(report['output'])], output / 'aseprite', manifest['asset_id'])
    write_new(output / 'aseprite_roundtrip.json', export)
    step['aseprite_roundtrip'] = export['status']
    manifest['pipeline_steps'].append(step)
    manifest['transparent_delivery'] = {'status': report['status'], 'output': report['output'],
                                        'preview': str(output / 'review_preview.png'),
                                        'aseprite_roundtrip': export['status'], 'review': 'HUMAN_REQUIRED'}
    if conformance is not None:
        manifest['transparent_delivery']['palette_conformance'] = conformance

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
    gate = analyze_image(candidate, target_width=row['width'], target_height=row['height'], allowed_palette=manifest_gate_palette(manifest))
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
