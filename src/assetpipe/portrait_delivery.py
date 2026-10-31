"""Explicit mask/contain delivery for NONPIXEL_IMAGE. No generation or automatic approval.

Two triggers share one implementation:
- a project Visual SOT ``delivery_profile`` (character portraits, explicit workflow binding);
- a brief alone: ``constraints.resolution`` plus ``constraints.transparency: true`` on a workflow
  without native transparent output, using the ``nonpixel_delivery`` section of config/pipeline.yaml.
"""
import copy
import hashlib
import importlib.metadata
from pathlib import Path

import yaml

from PIL import Image, ImageOps

from .styles.project import project_sot

MODEL_SHA256 = '309c8469258dda742793dce0ebea8e6dd393174f89934733ecc8b14c76f4ddd8'
SOURCE_BACKGROUND = ('Uniform solid white backdrop for the opaque source image, flat and featureless, '
                     'without any pattern, texture, decorative marks or transparency visualization. '
                     'The delivery pipeline will remove this temporary source backdrop locally.')
SOURCE_FRAMING = ('Keep the complete hairstyle inside the source canvas with visible white headroom '
                  'above its highest point. Keep both shoulders readable within the head-to-chest framing. '
                  'Do not cut hair at the top edge; retain the source-defined viewing angle and eye line.')
GENERIC_SOURCE_FRAMING = ('Keep the complete subject inside the source canvas with visible white margin on every side. '
                          'Do not crop the subject at any canvas edge; center it on the plain backdrop and keep the '
                          'requested viewing angle.')
DEFAULT_SECTION = 'nonpixel_delivery'
MATTING_PARAMETERS = {'foreground_threshold': 240, 'background_threshold': 10, 'erode_structure_size': 10}
MASK_CONTEXT_FRACTION = 0.1
SOURCE_WHITE_TOLERANCE = 10
SOURCE_WHITE_MINIMUM_FRACTION = 0.99


def _source_background(image, mask, background_rgb=(255,255,255)):
    """Propagate confident background through the verified source backdrop color.

    Never seed from the temporary padding or from canvas edges alone: a white
    collar can touch the bottom edge. Enclosed white details have no seed.
    """
    import numpy as np
    from scipy.ndimage import binary_propagation
    rgb, values = np.asarray(image), np.asarray(mask)
    white = np.max(np.abs(rgb.astype(np.int16) - np.asarray(background_rgb)), axis=2) <= SOURCE_WHITE_TOLERANCE
    confident = values < MATTING_PARAMETERS['background_threshold']
    seeds = white & confident
    background = binary_propagation(seeds, mask=white)
    refined = values.copy()
    refined[background] = 0
    return Image.fromarray(refined), Image.fromarray(background), {
        'operation': 'SOURCE_BACKGROUND_CONNECTED_TO_CONFIDENT_BACKGROUND',
        'background_tolerance': SOURCE_WHITE_TOLERANCE, 'connectivity': 4,
        'seed_mask_below': MATTING_PARAMETERS['background_threshold'],
        'padding_or_edge_seeds': False, 'seed_pixels': int(seeds.sum()),
        'verified_white_fraction': float((rgb.min(axis=2)[confident] >= 245).mean()) if confident.any() else 0.0,
        'verified_background_fraction': float(white[confident].mean()) if confident.any() else 0.0,
        'background_rgb': list(background_rgb),
        'minimum_background_fraction': SOURCE_WHITE_MINIMUM_FRACTION,
        'background_pixels': int(background.sum()),
        'changed_mask_pixels': int((refined != values).sum())}


def _unmatte_source_edges(image, alpha, background_rgb=(255,255,255)):
    """Recover straight-alpha RGB from C = alpha*F + (1-alpha)*background.

    Opaque pixels and the alpha channel are preserved exactly. This is valid
    only after the caller verifies the explicit uniform source-backdrop contract.
    """
    import numpy as np
    rgb = np.asarray(image).copy()
    values = np.asarray(alpha)
    edge = (values > 0) & (values < 255)
    a = values[edge, None].astype(np.float64) / 255
    recovered = np.clip(np.rint((rgb[edge].astype(np.float64) - (1 - a) * np.asarray(background_rgb)) / a), 0, 255).astype(np.uint8)
    changed = int(np.any(rgb[edge] != recovered, axis=1).sum())
    rgb[edge] = recovered
    result = Image.fromarray(rgb).convert('RGBA')
    result.putalpha(alpha)
    return result, {'operation': 'STRAIGHT_ALPHA_SOURCE_UNMATTE', 'background_rgb': list(background_rgb),
                    'translucent_pixels': int(edge.sum()), 'changed_rgb_pixels': changed,
                    'opaque_rgb': 'PRESERVED_EXACTLY', 'alpha': 'PRESERVED_EXACTLY'}


def default_profile(brief, root, workflow_id, workflow=None):
    """Brief-only delivery: explicit dimensions and transparency without a project SOT profile.

    The brief's own constraints are the request; nothing is inferred. Workflows that
    already deliver transparent output are left alone. Returns None when the pipeline
    config has no ``nonpixel_delivery`` section, so routing blocks as before.
    """
    constraints = brief['constraints']
    if (brief['output_class'] != 'NONPIXEL_IMAGE' or not constraints['resolution']
            or constraints['transparency'] is not True):
        return None
    if workflow is None:
        from .registry import load_registry
        workflow = load_registry(root).get(workflow_id)
    if workflow is None or workflow.get('capabilities', {}).get('transparent_output'):
        return None
    root = Path(root).resolve()
    config = yaml.safe_load((root / 'config/pipeline.yaml').read_text(encoding='utf-8')) or {}
    value = config.get(DEFAULT_SECTION)
    if not value:
        return None
    if (not isinstance(value, dict) or value.get('operation') != 'LOCAL_MASK_UNIFORM_CONTAIN'
            or value.get('human_review_required') is not True):
        raise ValueError('Unsupported default delivery policy')
    value = copy.deepcopy(value)
    value['model_path'] = str((root / value['model_path']).resolve())
    value['model_roots'] = [str((root / p).resolve()) for p in value['model_roots']]
    value.update(workflow_id=workflow_id, source='PIPELINE_DEFAULT',
                 trigger='BRIEF_RESOLUTION_AND_TRANSPARENCY', max_file_kb=constraints.get('max_file_kb'))
    return value


def framing_text(brief):
    return SOURCE_FRAMING if brief['asset_type'] == 'character_portrait' else GENERIC_SOURCE_FRAMING


def profile(brief, root, workflow_id, workflow=None):
    sot, sot_path = project_sot(brief, root)
    value = sot.get('delivery_profile')
    if not value:
        # A registered project contract keeps authority over its asset class; the brief-only
        # default applies only when the project has no Visual SOT contract at all.
        return None if sot else default_profile(brief, root, workflow_id, workflow)
    if not (brief.get('project_contract_required') is True
            and brief['output_class'] == 'NONPIXEL_IMAGE'
            and brief['asset_type'] == 'character_portrait'
            and value.get('workflow_id') == workflow_id):
        return None
    if value.get('operation') != 'LOCAL_MASK_UNIFORM_CONTAIN' or value.get('human_review_required') is not True:
        raise ValueError('Unsupported portrait delivery policy')
    if not brief['constraints']['resolution'] or brief['constraints']['transparency'] is not True:
        raise ValueError('Portrait delivery requires explicit dimensions and transparent output')
    if sot.get('_reference_edit'):
        value['project_reference_edit'] = {**sot['_reference_edit'],
            'sot_path': str(sot_path.resolve()), 'sot_sha256': hashlib.sha256(sot_path.read_bytes()).hexdigest()}
    return value


def preflight(value):
    model = Path(value['model_path']).resolve()
    roots = [Path(p).resolve() for p in value['model_roots']]
    if not any(model.is_relative_to(root) for root in roots):
        raise ValueError('Portrait alpha model is outside configured model roots')
    if not model.is_file() or hashlib.sha256(model.read_bytes()).hexdigest() != MODEL_SHA256:
        raise ValueError('Portrait alpha model missing or hash mismatch; automatic download is disabled')
    if importlib.metadata.version('rembg') != '2.0.69':
        raise ValueError('Portrait delivery requires rembg 2.0.69')
    return model


def process(source, resolution, value, directory, max_file_kb=None):
    model = preflight(value)
    from rembg import new_session, remove
    from rembg.bg import alpha_matting_cutout
    from .manifests import write
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    image = Image.open(source).convert('RGB')
    session = new_session('u2net_custom', model_path=str(model), providers=['CPUExecutionProvider'])
    # Give the existing segmenter background context at clipped canvas edges.
    # Only the model input is padded; return its mask to source coordinates.
    border = max(1, round(min(image.size) * MASK_CONTEXT_FRACTION))
    mask_input = ImageOps.expand(image, border=border, fill='white')
    mask_input.save(directory / 'segmentation_input.png')
    context_mask = remove(mask_input, session=session, only_mask=True).convert('L')
    if context_mask.size != mask_input.size:
        raise ValueError('Portrait segmentation returned invalid dimensions')
    context_mask.save(directory / 'segmentation_context_mask.png')
    mask = context_mask.crop((border, border, border + image.width, border + image.height))
    mask.save(directory / 'segmentation_mask.png')
    extrema = mask.getextrema()
    if extrema[0] == extrema[1]:
        raise ValueError('Portrait alpha mask has no foreground/background separation')
    background_rgb = (255,255,255)
    # Reference edits and the brief-only default accept a light uniform neutral backdrop
    # (T2I models rarely emit pure #FFFFFF); project T2I profiles stay pure-white only.
    if value.get('source_background_policy') == 'UNIFORM_NEUTRAL':
        import numpy as np
        samples = np.asarray(image)[np.asarray(mask) < MATTING_PARAMETERS['background_threshold']]
        if not len(samples):
            raise ValueError('Portrait source has no confident background samples')
        background_rgb = tuple(int(v) for v in np.rint(np.median(samples,axis=0)))
        if min(background_rgb) < 220 or max(background_rgb)-min(background_rgb) > 10:
            raise ValueError('Portrait reference source backdrop is not light neutral')
        refined_mask, source_background, refinement = _source_background(image, mask, background_rgb)
    else:
        refined_mask, source_background, refinement = _source_background(image, mask)
    refined_mask.save(directory / 'matting_input_mask.png')
    source_background.save(directory / 'source_background_mask.png')
    audit = {'operation': 'REMBG_CLOSED_FORM_MATTING', 'status': 'RUNNING',
             'parameters': dict(MATTING_PARAMETERS), 'fallback': 'NONE',
             'rgb_policy': 'PRESERVE_OPAQUE_RGB_UNMATTE_WHITE_EDGES' if background_rgb == (255,255,255)
                           else 'PRESERVE_OPAQUE_RGB_UNMATTE_NEUTRAL_EDGES',
             'source_background_refinement': refinement,
             'segmentation_context': {'fraction': MASK_CONTEXT_FRACTION, 'border_pixels': border,
                                      'fill': 'WHITE', 'input_size': list(mask_input.size),
                                      'mask_source_box': [border, border, border + image.width, border + image.height]},
             'rembg_version': importlib.metadata.version('rembg'),
             'pymatting_version': importlib.metadata.version('pymatting'),
             'source_sha256': hashlib.sha256(Path(source).read_bytes()).hexdigest(),
             'segmentation_mask_sha256': hashlib.sha256((directory / 'segmentation_mask.png').read_bytes()).hexdigest(),
             'human_review': 'REVIEW_REQUIRED', 'approval_effect': 'NONE'}
    write(directory / 'alpha_processing.json', audit)
    try:
        if refinement['verified_background_fraction'] < SOURCE_WHITE_MINIMUM_FRACTION:
            kind = 'white' if background_rgb == (255,255,255) else 'neutral'
            raise ValueError(f'Portrait source backdrop is not verified uniform {kind}; edge unmatting is blocked')
        # Call directly: rembg.remove(alpha_matting=True) silently falls back to
        # naive compositing on ValueError, which must not hide a failed gate.
        estimate = alpha_matting_cutout(image, refined_mask, **MATTING_PARAMETERS)
        if estimate.mode != 'RGBA' or estimate.size != image.size:
            raise ValueError('Portrait matting returned an invalid image')
        estimate.save(directory / 'matting_estimate.png')
        alpha = estimate.getchannel('A')
        if alpha.getextrema()[0] == alpha.getextrema()[1]:
            raise ValueError('Portrait matte has no foreground/background separation')
        # The estimator erodes its trimap and can make a narrow known-background
        # channel uncertain again. Retain the explicit source-background evidence.
        alpha.paste(0, mask=source_background)
        if alpha.getextrema()[0] == alpha.getextrema()[1]:
            raise ValueError('Portrait refined matte has no foreground/background separation')
        alpha.save(directory / 'alpha_mask.png')
        # Keep the uncorrected RGB/alpha combination as evidence. Discard the
        # estimator's foreground RGB; recover only translucent white-backed
        # edges with the compositing equation, preserving opaque source colors.
        source_rgba = image.convert('RGBA')
        source_rgba.putalpha(alpha)
        source_rgba.save(directory / 'masked_source_rgb.png')
        rgba, audit['edge_rgb'] = _unmatte_source_edges(image, alpha, background_rgb)
    except Exception as exc:
        audit.update(status='FAILED', error=str(exc))
        write(directory / 'alpha_processing.json', audit)
        raise
    audit['status'] = 'COMPLETED_REVIEW_REQUIRED'
    write(directory / 'alpha_processing.json', audit)
    rgba.save(directory / 'masked_original.png')
    output, placement = contain(rgba, resolution, directory / 'portrait.png', max_file_kb)
    record = {'operation': value['operation'], 'source': str(source),
              'source_sha256': hashlib.sha256(Path(source).read_bytes()).hexdigest(),
              'model_sha256': MODEL_SHA256, 'rembg_version': '2.0.69',
              'alpha_processing': audit, 'profile_source': value.get('source', 'PROJECT_SOT'),
              'source_size': list(image.size), **placement,
              'crop': False, 'output_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
              'human_review': 'REVIEW_REQUIRED', 'approval_effect': 'NONE',
              'checks': {key: 'NOT_REVIEWED' for key in
                         ('hair_and_clothing_preserved', 'no_halo', 'no_background',
                          'source_crop_preserved', 'identity_preserved')}}
    write(directory / 'delivery_record.json', record)
    return output, record


def contain(rgba, resolution, output, max_file_kb=None):
    """Uniformly scale an RGBA image into the exact target canvas, centered, never cropped.

    PNG compression is the only size lever; the limit is recorded, never enforced by
    degrading the image. QA fails a delivery that stays above ``max_file_kb``.
    """
    target = tuple(int(v) for v in resolution)
    scale = min(target[0] / rgba.width, target[1] / rgba.height)
    size = (max(1, round(rgba.width * scale)), max(1, round(rgba.height * scale)))
    resized = rgba.resize(size, Image.Resampling.LANCZOS)
    offset = ((target[0] - size[0]) // 2, (target[1] - size[1]) // 2)
    canvas = Image.new('RGBA', target, (0, 0, 0, 0))
    canvas.paste(resized, offset)
    output = Path(output)
    canvas.save(output, optimize=True)
    file_size = output.stat().st_size
    return output, {'delivery_size': list(target), 'uniform_scale': scale, 'resized_size': list(size),
                    'offset': list(offset), 'file_size_bytes': file_size, 'max_file_kb': max_file_kb,
                    'within_file_limit': None if not max_file_kb else file_size <= max_file_kb * 1024}
