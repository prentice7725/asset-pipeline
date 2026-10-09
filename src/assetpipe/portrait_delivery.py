"""Explicit portrait mask/contain delivery. No generation or automatic approval."""
import hashlib
import importlib.metadata
from pathlib import Path

from PIL import Image

from .styles.project import project_sot

MODEL_SHA256 = '309c8469258dda742793dce0ebea8e6dd393174f89934733ecc8b14c76f4ddd8'


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
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    image = Image.open(source).convert('RGB')
    session = new_session('u2net_custom', model_path=str(model), providers=['CPUExecutionProvider'])
    mask = remove(image, session=session, only_mask=True).convert('L')
    extrema = mask.getextrema()
    if extrema[0] == extrema[1]:
        raise ValueError('Portrait alpha mask has no foreground/background separation')
    mask.save(directory / 'alpha_mask.png')
    rgba = image.convert('RGBA')
    rgba.putalpha(mask)
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
    from .manifests import write
    record = {'operation': value['operation'], 'source': str(source),
              'source_sha256': hashlib.sha256(Path(source).read_bytes()).hexdigest(),
              'model_sha256': MODEL_SHA256, 'rembg_version': '2.0.69',
              'source_size': list(image.size), 'delivery_size': list(target),
              'uniform_scale': scale, 'resized_size': list(size), 'offset': list(offset),
              'crop': False, 'output_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
              'human_review': 'REVIEW_REQUIRED', 'approval_effect': 'NONE',
              'checks': {key: 'NOT_REVIEWED' for key in
                         ('hair_and_clothing_preserved', 'no_halo', 'no_background',
                          'source_crop_preserved', 'identity_preserved')}}
    write(directory / 'delivery_record.json', record)
    return output, record
