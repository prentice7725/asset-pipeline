"""Explicit offline candidate transformations. No generator, retry or approval API."""
import copy
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import shutil

from jsonschema import Draft202012Validator
import numpy as np
from PIL import Image

from ..brief import obj
from ..factory.provenance import Sources, fingerprint
from ..manifests import now, write
from ..paths import RootResolver
from ..pixel.direct.ported import white_border_matte, edge_connected
from .package import pack_review_atlas

HASH = {'type': 'string', 'pattern': '^[a-f0-9]{64}$'}
INT = {'type': 'integer', 'minimum': 0, 'maximum': 2048}
CLEANUP = obj({'regions': {'type': 'array', 'minItems': 1, 'maxItems': 16,
                          'items': {'type': 'array', 'items': INT, 'minItems': 4, 'maxItems': 4}},
               'rgb_min': {'type': 'array', 'items': {'type': 'integer', 'minimum': 0, 'maximum': 255},
                           'minItems': 3, 'maxItems': 3}}, ['regions', 'rgb_min'])
SCHEMA = obj({
    'schema_version': {'type': 'integer', 'const': 1},
    'kind': {'const': 'MOTION_REVIEW_RECIPE'},
    'source_manifest': {'type': 'string', 'minLength': 1}, 'source_sha256': HASH,
    'selection': obj({'start_frame': {'type': 'integer', 'minimum': 1, 'maximum': 240},
                      'end_frame': {'type': 'integer', 'minimum': 1, 'maximum': 240}},
                     ['start_frame', 'end_frame']),
    'alpha': {'oneOf': [obj({'method': {'const': 'PRESERVE'}, 'cleanup': CLEANUP}, ['method']),
                        obj({'method': {'const': 'EDGE_CONNECTED_WHITE'},
                             'background_rgb': {'const': [255, 255, 255]},
                             'tolerance': {'type': 'integer', 'const': 60}, 'cleanup': CLEANUP},
                            ['method', 'background_rgb', 'tolerance'])]},
}, ['schema_version', 'kind', 'source_manifest', 'source_sha256', 'selection', 'alpha'])
SCHEMA.update({'$schema': 'https://json-schema.org/draft/2020-12/schema',
               '$id': 'urn:assetpipe:motion-review-recipe:1'})
SCHEMA_V2 = copy.deepcopy(SCHEMA)
SCHEMA_V2['$id'] = 'urn:assetpipe:motion-review-recipe:2'
SCHEMA_V2['properties']['schema_version']['const'] = 2
SCHEMA_V2['properties']['alpha']['oneOf'][1]['properties']['tolerance'] = {
    'type': 'integer', 'minimum': 0, 'maximum': 60}
REVIEW_CHECKS = ['loop_selection', 'alpha_edges', 'identity_equipment_silhouette',
                 'pivot_and_foot_contact', 'engine_import', 'game_readability', 'aseprite_review']


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _policy(root, allowed_roots):
    root = Path(root).resolve(strict=True)
    resolver = RootResolver(allowed_roots if allowed_roots is not None else [root], base=root)
    resolver(root)
    return root, resolver


def plan_recipe(recipe_path, root, *, allowed_roots=None):
    """Read-only concrete plan; mandatory external digest binds subsequent apply."""
    root, resolver = _policy(root, allowed_roots)
    sources = Sources(resolver)
    recipe_path, sha, recipe = sources.document(recipe_path)
    schema = SCHEMA_V2 if recipe.get('schema_version') == 2 else SCHEMA
    errors = list(Draft202012Validator(schema).iter_errors(recipe))
    if errors:
        raise ValueError('MOTION_RECIPE_INVALID: ' + '; '.join(e.message for e in errors))
    manifest_path, manifest_sha, manifest = sources.document(
        recipe['source_manifest'], recipe['source_sha256'], recipe_path.parent)
    if (manifest.get('type') != 'OFFLINE_MOTION_PACKAGE'
            or manifest.get('status') != 'OFFLINE_PACKAGE_REVIEW_REQUIRED'
            or manifest.get('review_state') != 'REVIEW_REQUIRED'
            or manifest.get('game_ready') is not False
            or manifest.get('plan', {}).get('mapped_output_class') != 'NONPIXEL_ANIMATION'):
        raise ValueError('MOTION_RECIPE_SOURCE_BLOCKED: completed nonpixel package required')
    outputs = []
    for row in manifest['outputs']:
        path = sources.file(row['path'], manifest_path.parent)
        if not path.is_relative_to(manifest_path.parent) or fingerprint(path) != row['sha256']:
            raise ValueError('MOTION_RECIPE_SOURCE_CHANGED: package output')
        outputs.append({'path': str(path), 'sha256': row['sha256']})
    matches = [row for row in outputs if Path(row['path']).name == 'atlas.json']
    if len(matches) != 1:
        raise ValueError('MOTION_RECIPE_SOURCE_INVALID: exactly one atlas required')
    atlas_path, atlas_sha, atlas = sources.document(matches[0]['path'], matches[0]['sha256'])
    fps = Fraction(atlas['fps'])
    size = manifest['probe']['size']
    frames = atlas['frames']
    if (not 0 < fps <= 60 or not 1 <= len(frames) <= 240 or len(size) != 2
            or any(type(v) is not int or not 0 < v <= 2048 for v in size)
            or fps != Fraction(manifest['probe']['fps'])
            or len(frames) != manifest['probe']['frame_count']):
        raise ValueError('MOTION_RECIPE_SOURCE_INVALID: timing or dimensions')
    first, last = recipe['selection']['start_frame'], recipe['selection']['end_frame']
    if not 1 <= first <= last <= len(frames):
        raise ValueError('MOTION_RECIPE_SELECTION_INVALID')
    columns = min(last - first + 1, max(1, 4096 // size[0]))
    if columns * size[0] * math.ceil((last - first + 1) / columns) * size[1] > 32_000_000:
        raise ValueError('MOTION_RECIPE_ATLAS_LIMIT')
    for box in recipe['alpha'].get('cleanup', {}).get('regions', []):
        x0, y0, x1, y1 = box
        if not 0 <= x0 < x1 <= size[0] or not 0 <= y0 < y1 <= size[1]:
            raise ValueError('MOTION_RECIPE_REGION_INVALID')
    selected = []
    for position in range(first - 1, last):
        row = frames[position]
        if (row['index'] != position or row['source_frame_index'] != position + 1
                or not math.isclose(row['timestamp_seconds'], position / float(fps), abs_tol=1e-6)
                or not math.isclose(row['duration_ms'], 1000 / float(fps), abs_tol=1e-6)
                or row['pivot'] != [size[0] / 2, size[1] - 2]):
            raise ValueError('MOTION_RECIPE_SOURCE_INVALID: frame metadata')
        checked = copy.deepcopy(row)
        for key, hash_key in [('path', 'sha256'), ('raw_path', 'raw_sha256')]:
            path = sources.file(row[key], atlas_path.parent)
            if not path.is_relative_to(manifest_path.parent) or fingerprint(path) != row[hash_key]:
                raise ValueError('MOTION_RECIPE_SOURCE_CHANGED: selected frame')
            with Image.open(path) as image:
                if image.format != 'PNG' or list(image.size) != size:
                    raise ValueError('MOTION_RECIPE_SOURCE_INVALID: selected frame dimensions')
            checked[key] = str(path)
        selected.append(checked)
    implementation = {str(path): fingerprint(path) for path in [Path(__file__),
        Path(__file__).with_name('package.py'), Path(__file__).parents[1] / 'pixel/direct/ported.py',
        Path(__file__).parents[1] / 'paths.py', Path(__file__).parents[1] / 'manifests/__init__.py']}
    normalized = copy.deepcopy(recipe)
    normalized['source_manifest'] = str(manifest_path)
    result = {'schema_version': 1, 'kind': 'MOTION_RECIPE_PLAN',
              'recipe_path': str(recipe_path), 'recipe_sha256': sha, 'recipe': normalized,
              'source_manifest': str(manifest_path), 'source_sha256': manifest_sha,
              'source_outputs': outputs, 'source_atlas': str(atlas_path), 'source_atlas_sha256': atlas_sha,
              'frames': selected, 'size': size, 'fps': str(fps), 'implementation': implementation,
              'review_requirements': REVIEW_CHECKS, 'review_state': 'REVIEW_REQUIRED',
              'generation_requests': 0, 'game_ready': False}
    result['plan_sha256'] = _digest(result)
    return result


def apply_recipe(recipe_path, plan_sha256, output, root, *, allowed_roots=None):
    """One fresh offline candidate, with immutable intermediates and pending review."""
    root, resolver = _policy(root, allowed_roots)
    plan = plan_recipe(recipe_path, root, allowed_roots=resolver.roots)
    if plan['plan_sha256'] != plan_sha256:
        raise ValueError('MOTION_RECIPE_PLAN_CHANGED')
    outputs = RootResolver([root], base=root)
    output = outputs(output, strict=False)
    workspace = outputs(root / 'workspace', strict=False)
    source_paths = [Path(plan['recipe_path']), Path(plan['source_manifest'])]
    source_paths += [Path(r[k]) for r in plan['frames'] for k in ['path', 'raw_path']]
    if (workspace != root / 'workspace' or output == workspace or not output.is_relative_to(workspace)
            or any(p.is_relative_to(output) for p in source_paths)):
        raise ValueError('MOTION_RECIPE_OUTPUT_INVALID')
    output.mkdir(parents=True, exist_ok=False)
    receipt = {'schema_version': 1, 'kind': 'MOTION_RECIPE_RECEIPT', 'status': 'STARTED',
               'started_at': now(), 'plan': plan, 'frames': [], 'outputs': [],
               'generation_requests': 0, 'review_state': 'REVIEW_REQUIRED', 'game_ready': False,
               'retry': 'NONE', 'fallback': 'NONE'}
    manifest = output / 'recipe_manifest.json'
    try:
        write(manifest, receipt)
        shutil.copyfile(plan['recipe_path'], output / 'recipe-input.json')
        if fingerprint(output / 'recipe-input.json') != plan['recipe_sha256']:
            raise ValueError('MOTION_RECIPE_SOURCE_CHANGED: recipe snapshot')
        write(output / 'recipe.json', plan['recipe'])
        write(output / 'plan.json', plan)
        for name in ['source', 'masked', 'final', 'masks']:
            (output / name).mkdir()
        alpha = plan['recipe']['alpha']
        for index, row in enumerate(plan['frames']):
            if fingerprint(Path(row['path'])) != row['sha256']:
                raise ValueError('MOTION_RECIPE_SOURCE_CHANGED')
            preserved = output / 'source' / f'{index:04d}.png'
            shutil.copyfile(row['path'], preserved)
            if fingerprint(preserved) != row['sha256']:
                raise ValueError('MOTION_RECIPE_SOURCE_CHANGED')
            with Image.open(preserved) as source:
                rgba = source.convert('RGBA')
            if alpha['method'] == 'EDGE_CONNECTED_WHITE':
                if alpha['tolerance'] == 60:
                    matte, alpha_report = white_border_matte(rgba)
                else:
                    # v2 explicitly narrows the mask input to the verified span-fill.
                    # No inferred background, global color key or altered RGB.
                    rgb = np.asarray(rgba)[:, :, :3].astype(np.int32)
                    background = edge_connected(np.sum((rgb - 255) ** 2, axis=2) <= alpha['tolerance'] ** 2)
                    matte = rgba.copy()
                    matte.putalpha(Image.fromarray(np.where(background, 0, 255).astype(np.uint8)))
                    alpha_report = {'method': 'EXPLICIT_V2_EDGE_CONNECTED_WHITE',
                        'background_rgb': [255, 255, 255],
                        'background_tolerance_rgb_distance': alpha['tolerance'],
                        'transparent_pixels': int(background.sum()),
                        'foreground_pixels': int((~background).sum())}
                # Never reintroduce already transparent source pixels.
                rgba.putalpha(Image.fromarray(np.minimum(np.asarray(rgba)[:, :, 3],
                                                        np.asarray(matte)[:, :, 3])))
            else:
                alpha_report = {'method': 'PRESERVE_SOURCE_ALPHA'}
            masked = output / 'masked' / f'{index:04d}.png'
            rgba.save(masked)
            pixels = np.asarray(rgba).copy()
            removed = np.zeros(pixels.shape[:2], dtype=bool)
            if 'cleanup' in alpha:
                cleanup = alpha['cleanup']
                region = np.zeros(pixels.shape[:2], dtype=bool)
                for x0, y0, x1, y1 in cleanup['regions']:
                    region[y0:y1, x0:x1] = True
                removed = region & np.all(pixels[:, :, :3] >= np.asarray(cleanup['rgb_min']), axis=2) & (pixels[:, :, 3] > 0)
                pixels[removed, 3] = 0
            if not np.any(pixels[:, :, 3]):
                raise ValueError('MOTION_RECIPE_EMPTY_FOREGROUND')
            final = output / 'final' / f'{index:04d}.png'
            mask = output / 'masks' / f'{index:04d}.png'
            Image.fromarray(pixels).save(final)
            Image.fromarray(removed.astype(np.uint8) * 255).save(mask)
            receipt['frames'].append({**row, 'candidate_index': index,
                'original_source_frame_index': row['source_frame_index'],
                'original_timestamp_seconds': row['timestamp_seconds'],
                'source_path': row['path'], 'source_sha256': row['sha256'],
                'preserved_path': str(preserved), 'preserved_sha256': fingerprint(preserved),
                'masked_path': str(masked), 'masked_sha256': fingerprint(masked),
                'removed_mask_path': str(mask), 'removed_mask_sha256': fingerprint(mask),
                'alpha_report': alpha_report,
                'removed_pixels': int(removed.sum()), 'path': str(final), 'sha256': fingerprint(final)})
        packed = pack_review_atlas(receipt['frames'], plan['size'], float(Fraction(plan['fps'])), output)
        write(output / 'atlas.json', {'fps': plan['fps'], 'frames': packed,
             'pivot_policy': 'CANVAS_BOTTOM_CENTER_REVIEW_REQUIRED',
             'loop_quality': 'REVIEW_REQUIRED', 'alpha_quality': 'REVIEW_REQUIRED',
             'source_manifest': plan['source_manifest'], 'source_sha256': plan['source_sha256'],
             'review_state': 'REVIEW_REQUIRED', 'game_ready': False})
        write(output / 'review.json', {'status': 'REVIEW_REQUIRED', 'reviewed_by': None,
                                      'checks': {name: None for name in REVIEW_CHECKS}})
        if plan_recipe(recipe_path, root, allowed_roots=resolver.roots) != plan:
            raise ValueError('MOTION_RECIPE_SOURCE_CHANGED: final revalidation')
        receipt['outputs'] = [{'path': str(p), 'sha256': fingerprint(p)}
                              for p in sorted(output.rglob('*')) if p.is_file() and p != manifest]
        receipt['status'] = 'CANDIDATE_REVIEW_REQUIRED'
    except Exception as exc:
        receipt.update(status='FAILED', error=str(exc))
        raise
    finally:
        receipt['finished_at'] = now()
        write(manifest, receipt)
    return manifest


def inspect_recipe(run, root, *, expected_sha256, allowed_roots=None):
    """Check source/code/output integrity, not human approval or operational readiness."""
    root, resolver = _policy(root, allowed_roots)
    path = RootResolver([root], base=root)(Path(run) / 'recipe_manifest.json')
    _, _, receipt = Sources(resolver).document(path, expected_sha256)
    if receipt.get('kind') != 'MOTION_RECIPE_RECEIPT' or receipt.get('status') != 'CANDIDATE_REVIEW_REQUIRED':
        raise ValueError('MOTION_RECIPE_RUN_BLOCKED')
    plan = receipt['plan']
    if (plan_recipe(plan['recipe_path'], root, allowed_roots=resolver.roots) != plan
            or receipt.get('review_state') != 'REVIEW_REQUIRED' or receipt.get('game_ready') is not False
            or receipt.get('generation_requests') != 0):
        raise ValueError('MOTION_RECIPE_SOURCE_CHANGED')
    required = {path.parent / name for name in ['recipe-input.json', 'recipe.json', 'plan.json', 'sprites.png', 'atlas.json', 'review.json']}
    required.update(path.parent / folder / f'{index:04d}.png'
                    for index in range(len(plan['frames'])) for folder in ['source', 'masked', 'final', 'masks'])
    declared = [resolver(row['path']) for row in receipt['outputs']]
    present = {p.resolve() for p in path.parent.rglob('*') if p.is_file() and p != path}
    if len(set(declared)) != len(declared) or set(declared) != required or present != required:
        raise ValueError('MOTION_RECIPE_OUTPUT_CHANGED: exact artifact inventory required')
    for row in receipt['outputs']:
        target = resolver(row['path'])
        if not target.is_relative_to(path.parent) or fingerprint(target) != row['sha256']:
            raise ValueError('MOTION_RECIPE_OUTPUT_CHANGED')
    review = json.loads((path.parent / 'review.json').read_text(encoding='utf-8'))
    if review != {'status': 'REVIEW_REQUIRED', 'reviewed_by': None,
                  'checks': {name: None for name in REVIEW_CHECKS}}:
        raise ValueError('MOTION_RECIPE_REVIEW_CHANGED: no approval API in this milestone')
    return {'status': 'ARTIFACT_INTEGRITY_PASS_REVIEW_REQUIRED',
            'manifest_sha256': fingerprint(path), 'plan_sha256': plan['plan_sha256'],
            'generation_requests': 0, 'review_state': 'REVIEW_REQUIRED', 'game_ready': False}
