"""Reproducible advisory previews; never changes production or approval state."""
import hashlib
import io
import json
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps

from ..manifests import now, write

CHECKS = (
    'subject_and_action_readable', 'large_value_masses_readable',
    'intended_focus', 'incidental_surfaces_do_not_compete',
    'grouped_colors_without_speckled_noise', 'body_clothing_equipment_separation',
    'canonical_traits_and_story_clues_preserved', 'forbidden_elements_absent',
    'actual_display_scale_and_crop_readable', 'accessibility_requirements',
)


def build_review(run, *, image=None, display_size=None, matte=(255, 255, 255)):
    run = Path(run).resolve()
    manifest_path = run / 'run_manifest.json'
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    kind = manifest.get('output_class', manifest.get('asset_brief', {}).get('output_class'))
    if kind not in {'PIXEL_STATIC', 'NONPIXEL_IMAGE'}:
        raise ValueError('Visual review supports static image candidates only')
    if manifest.get('status') not in {'CANDIDATE_READY_REVIEW_REQUIRED',
                                    'EXPORT_READY_REVIEW_REQUIRED'}:
        raise ValueError('Visual review requires a candidate past its technical gates')
    qa = manifest.get('qa_results', [])
    advisory_states = {'PASS', 'REVIEW_REQUIRED', 'ANALYSIS_COMPLETE_REVIEW_REQUIRED'}
    if not any(row.get('status') == 'PASS' for row in qa) or any(row.get('status') not in advisory_states for row in qa):
        raise ValueError('Visual review cannot advance a failed technical gate or missing QA evidence')
    if any(row.get('status') in {'FAIL', 'FAILED'} for row in
           manifest.get('qa_results', []) + manifest.get('pipeline_steps', [])):
        raise ValueError('Visual review cannot advance a failed technical gate')
    outputs = [Path(p) if Path(p).is_absolute() else run / p for p in manifest['outputs']]
    if image is None:
        if len(outputs) != 1:
            raise ValueError('Select exactly one manifest output with --image')
        source = outputs[0].resolve()
    else:
        source = Path(image).resolve()
        if source not in [p.resolve() for p in outputs]:
            raise ValueError('Selected image must be a manifest output')
    if not source.is_relative_to(run):
        raise ValueError('Review source must be inside the run directory')
    if display_size and (len(display_size) != 2 or min(display_size) < 1 or max(display_size) > 4096):
        raise ValueError('Display size must be between 1 and 4096 per axis')
    if len(matte) != 3 or any(v < 0 or v > 255 for v in matte):
        raise ValueError('Matte must contain three RGB values from 0 to 255')
    raw = source.read_bytes()
    original = Image.open(io.BytesIO(raw))
    original.load()
    if getattr(original, 'n_frames', 1) != 1:
        raise ValueError('Animated images require a separate review contract')
    rgba = original.convert('RGBA')
    flat = Image.alpha_composite(Image.new('RGBA', rgba.size, (*matte, 255)), rgba).convert('RGB')
    resample = Image.Resampling.NEAREST if kind == 'PIXEL_STATIC' else Image.Resampling.LANCZOS
    thumb = flat.copy()
    thumb.thumbnail((64, 64), resample)
    previews = {'native_matte.png': flat, 'thumbnail.png': thumb,
                'grayscale_thumbnail.png': ImageOps.grayscale(thumb),
                'blurred_thumbnail.png': thumb.filter(ImageFilter.GaussianBlur(2))}
    if display_size:
        previews['display_scale.png'] = flat.resize(tuple(display_size), resample)
    directory = run / 'review_artifacts' / now().replace(':', '').replace('+', '_')
    directory.mkdir(parents=True, exist_ok=False)
    (directory / ('original' + source.suffix)).write_bytes(raw)
    artifacts = {}
    for name, preview in previews.items():
        preview.save(directory / name)
        artifacts[name] = hashlib.sha256((directory / name).read_bytes()).hexdigest()
    # Fixed-size panels are presentation only; standalone previews retain their exact size.
    sheet = Image.new('RGB', (256 * len(previews), 280), 'white')
    from PIL import ImageDraw
    draw = ImageDraw.Draw(sheet)
    for index, (name, preview) in enumerate(previews.items()):
        panel = preview.convert('RGB').copy()
        panel.thumbnail((240, 240), resample)
        sheet.paste(panel, (index * 256 + (256 - panel.width) // 2, 24 + (240 - panel.height) // 2))
        draw.text((index * 256 + 4, 4), name, fill='black')
    sheet.save(directory / 'contact_sheet.png')
    artifacts['contact_sheet.png'] = hashlib.sha256((directory / 'contact_sheet.png').read_bytes()).hexdigest()
    report = {'schema_version': 1, 'status': 'REVIEW_REQUIRED', 'advisory_only': True,
              'generation_requests': 0, 'source': str(source),
              'source_sha256': hashlib.sha256(raw).hexdigest(),
              'manifest_sha256': hashlib.sha256(manifest_bytes).hexdigest(),
              'run_status': manifest['status'], 'output_class': kind,
              'asset_role': manifest.get('asset_brief', {}).get('asset_type', 'UNKNOWN'),
              'settings': {'thumbnail_long_side': 64, 'resampling': resample.name,
                           'matte_rgb': list(matte), 'blur_radius_thumbnail_pixels': 2,
                           'display_size': list(display_size) if display_size else None,
                           'pillow_version': __import__('PIL').__version__},
              'artifacts': artifacts,
              'context_review': 'REVIEW_REQUIRED' if display_size else 'NOT_AVAILABLE_DISPLAY_RULES_MISSING',
              'checks': {name: {'decision': 'NOT_REVIEWED', 'notes': ''} for name in CHECKS},
              'human_review': {'reviewed_by': None, 'reviewed_at': None, 'reason': None},
              'approval_effect': 'NONE'}
    contract = manifest.get('asset_brief', {}).get('prompt_spec', {}).get('subject_integrity')
    if contract:
        report['subject_integrity_requirements'] = contract
        report['review_domains'] = {
            'SEMANTIC': {'status': 'NOT_VALIDATED', 'checks': {
                key: {'decision': 'NOT_VALIDATED', 'notes': ''} for key in
                ('whole_subject', 'connected_body_parts', 'worn_or_carried_equipment',
                 'source_equipment_counts_colors_shapes', 'required_landmarks', 'forbidden_substitutions')}},
            'COMPOSITION': {'status': 'NOT_VALIDATED', 'checks': {
                key: {'decision': 'NOT_VALIDATED', 'notes': ''} for key in
                ('source_camera_view', 'silhouette_separation', 'scene_context')}},
            'ART': {'status': 'NOT_VALIDATED', 'checks': {
                key: {'decision': 'NOT_VALIDATED', 'notes': ''} for key in
                ('thumbnail_readability', 'grayscale_value_masses', 'blurred_shadow_groups', 'background_noise')}},
        }
    write(directory / 'visual_review.json', report)
    return directory / 'visual_review.json'
