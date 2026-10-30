"""Explicit portrait mask/contain delivery. No generation or automatic approval."""
import hashlib
import importlib.metadata
from pathlib import Path

from PIL import Image, ImageOps

from .styles.project import project_sot

MODEL_SHA256 = '309c8469258dda742793dce0ebea8e6dd393174f89934733ecc8b14c76f4ddd8'
SOURCE_BACKGROUND = ('Uniform solid white backdrop for the opaque source image, flat and featureless, '
                     'without any pattern, texture, decorative marks or transparency visualization. '
                     'The delivery pipeline will remove this temporary source backdrop locally.')
SOURCE_FRAMING = ('Keep the complete hairstyle inside the source canvas with visible white headroom '
                  'above its highest point. Keep both shoulders readable within the head-to-chest framing. '
                  'Do not cut hair at the top edge; retain the source-defined viewing angle and eye line.')
MATTING_PARAMETERS = {'foreground_threshold': 240, 'background_threshold': 10, 'erode_structure_size': 10}
MASK_CONTEXT_FRACTION = 0.1
SOURCE_WHITE_TOLERANCE = 10
SOURCE_WHITE_MINIMUM_FRACTION = 0.99


def _source_background(image, mask):
    """Propagate existing confident background through near-white source only.

    Never seed from the temporary padding or from canvas edges alone: a white
    collar can touch the bottom edge. Enclosed white details have no seed.
    """
    import numpy as np
    from scipy.ndimage import binary_propagation
    rgb, values = np.asarray(image), np.asarray(mask)
    white = rgb.min(axis=2) >= 255 - SOURCE_WHITE_TOLERANCE
    confident = values < MATTING_PARAMETERS['background_threshold']
    seeds = white & confident
    background = binary_propagation(seeds, mask=white)
    refined = values.copy()
    refined[background] = 0
    return Image.fromarray(refined), Image.fromarray(background), {
        'operation': 'SOURCE_WHITE_CONNECTED_TO_CONFIDENT_BACKGROUND',
        'white_tolerance': SOURCE_WHITE_TOLERANCE, 'connectivity': 4,
        'seed_mask_below': MATTING_PARAMETERS['background_threshold'],
        'padding_or_edge_seeds': False, 'seed_pixels': int(seeds.sum()),
        'verified_white_fraction': float(white[confident].mean()) if confident.any() else 0.0,
        'minimum_white_fraction': SOURCE_WHITE_MINIMUM_FRACTION,
        'background_pixels': int(background.sum()),
        'changed_mask_pixels': int((refined != values).sum())}


def _unmatte_white_edges(image, alpha):
    """Recover straight-alpha RGB from C = alpha*F + (1-alpha)*white.

    Opaque pixels and the alpha channel are preserved exactly. This is valid
    only after the caller verifies the explicit white source-backdrop contract.
    """
    import numpy as np
    rgb = np.asarray(image).copy()
    values = np.asarray(alpha)
    edge = (values > 0) & (values < 255)
    a = values[edge, None].astype(np.float64) / 255
    recovered = np.clip(np.rint((rgb[edge].astype(np.float64) - (1 - a) * 255) / a), 0, 255).astype(np.uint8)
    changed = int(np.any(rgb[edge] != recovered, axis=1).sum())
    rgb[edge] = recovered
    result = Image.fromarray(rgb).convert('RGBA')
    result.putalpha(alpha)
    return result, {'operation': 'STRAIGHT_ALPHA_WHITE_UNMATTE', 'background_rgb': [255,255,255],
                    'translucent_pixels': int(edge.sum()), 'changed_rgb_pixels': changed,
                    'opaque_rgb': 'PRESERVED_EXACTLY', 'alpha': 'PRESERVED_EXACTLY'}


def profile(brief, root, workflow_id):
    sot, _ = project_sot(brief, root)
    value = sot.get('delivery_profile')
    if not value:
        return None
    if not (brief.get('project_contract_required') is True
            and brief['output_class'] == 'NONPIXEL_IMAGE'
            and brief['asset_type'] == 'character_portrait'
            and value.get('workflow_id') == workflow_id):
        return None
    if value.get('operation') != 'LOCAL_MASK_UNIFORM_CONTAIN' or value.get('human_review_required') is not True:
        raise ValueError('Unsupported portrait delivery policy')
    if not brief['constraints']['resolution'] or brief['constraints']['transparency'] is not True:
        raise ValueError('Portrait delivery requires explicit dimensions and transparent output')
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


def process(source, resolution, value, directory):
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
    refined_mask, source_background, refinement = _source_background(image, mask)
    refined_mask.save(directory / 'matting_input_mask.png')
    source_background.save(directory / 'source_background_mask.png')
    audit = {'operation': 'REMBG_CLOSED_FORM_MATTING', 'status': 'RUNNING',
             'parameters': dict(MATTING_PARAMETERS), 'fallback': 'NONE',
             'rgb_policy': 'PRESERVE_OPAQUE_RGB_UNMATTE_WHITE_EDGES',
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
        if refinement['verified_white_fraction'] < SOURCE_WHITE_MINIMUM_FRACTION:
            raise ValueError('Portrait source backdrop is not verified uniform white; edge unmatting is blocked')
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
        rgba, audit['edge_rgb'] = _unmatte_white_edges(image, alpha)
    except Exception as exc:
        audit.update(status='FAILED', error=str(exc))
        write(directory / 'alpha_processing.json', audit)
        raise
    audit['status'] = 'COMPLETED_REVIEW_REQUIRED'
    write(directory / 'alpha_processing.json', audit)
    rgba.save(directory / 'masked_original.png')
    target = tuple(resolution)
    scale = min(target[0] / rgba.width, target[1] / rgba.height)
    size = (max(1, round(rgba.width * scale)), max(1, round(rgba.height * scale)))
    resized = rgba.resize(size, Image.Resampling.LANCZOS)
    offset = ((target[0] - size[0]) // 2, (target[1] - size[1]) // 2)
    canvas = Image.new('RGBA', target, (0, 0, 0, 0))
    canvas.paste(resized, offset)
    output = directory / 'portrait.png'
    canvas.save(output)
    record = {'operation': value['operation'], 'source': str(source),
              'source_sha256': hashlib.sha256(Path(source).read_bytes()).hexdigest(),
              'model_sha256': MODEL_SHA256, 'rembg_version': '2.0.69',
              'alpha_processing': audit,
              'source_size': list(image.size), 'delivery_size': list(target),
              'uniform_scale': scale, 'resized_size': list(size), 'offset': list(offset),
              'crop': False, 'output_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
              'human_review': 'REVIEW_REQUIRED', 'approval_effect': 'NONE',
              'checks': {key: 'NOT_REVIEWED' for key in
                         ('hair_and_clothing_preserved', 'no_halo', 'no_background',
                          'source_crop_preserved', 'identity_preserved')}}
    write(directory / 'delivery_record.json', record)
    return output, record
