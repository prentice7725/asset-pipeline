"""Explicit Factory motion stages, delegating algorithms and generation authority."""
import copy
import json
import shutil
from pathlib import Path

from jsonschema import Draft202012Validator

from ..brief import obj
from ..manifests import now, write
from ..paths import RootResolver
from .planner import plan_file
from .provenance import Sources, fingerprint
from ..motion.recipe import SCHEMA as RECIPE_V1, SCHEMA_V2 as RECIPE_V2

HASH = {'type': 'string', 'pattern': '^[a-f0-9]{64}$'}
PATH = {'type': 'string', 'minLength': 1}
SCHEMA = obj({'schema_version': {'type': 'integer', 'const': 1},
    'kind': {'const': 'FACTORY_MOTION_JOB'}, 'request_ref': PATH, 'request_sha256': HASH,
    'input': {'oneOf': [obj({'kind': {'const': 'EXISTING_VIDEO'}, 'path': PATH, 'sha256': HASH,
                            'generation_record': obj({'path': PATH, 'sha256': HASH}, ['path', 'sha256'])},
                           ['kind', 'path', 'sha256']),
                        obj({'kind': {'const': 'PREPARED_GENERATION'}, 'run_ref': PATH,
                             'seed': {'type': 'integer', 'minimum': 0, 'maximum': 2**32-1},
                             'width': {'type': 'integer'}, 'height': {'type': 'integer'}},
                            ['kind', 'run_ref', 'seed', 'width', 'height'])]},
    'recipe': {'oneOf': [obj({k: copy.deepcopy(schema['properties'][k])
                              for k in ['schema_version', 'selection', 'alpha']},
                             ['schema_version', 'selection', 'alpha'])
                        for schema in [RECIPE_V1, RECIPE_V2]]}},
    ['schema_version', 'kind', 'request_ref', 'request_sha256', 'input', 'recipe'])


def _digest(value):
    import hashlib
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _policy(root, allowed_roots):
    root = Path(root).resolve(strict=True)
    resolver = RootResolver(allowed_roots if allowed_roots is not None else [root], base=root)
    resolver(root)
    return root, resolver


def _receipt(path, sha, outputs):
    """Read pinned internal metadata; resolve each data link only when used.

    Compiler-code and retired model paths are provenance, not data-root grants.
    External job/request documents still use the strict Sources validator.
    """
    path = outputs(path)
    if fingerprint(path) != sha:
        raise ValueError('FACTORY_MOTION_RECEIPT_CHANGED')
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise ValueError('FACTORY_MOTION_RECEIPT_INVALID')
    return value


def plan_job(job_path, root, *, allowed_roots=None):
    """Read-only plan; replay never imports or calls a generation provider."""
    root, resolver = _policy(root, allowed_roots)
    sources = Sources(resolver)
    path, sha, job = sources.document(job_path)
    Draft202012Validator(SCHEMA).validate(job)
    request, _, _ = sources.document(job['request_ref'], job['request_sha256'], path.parent)
    planned = plan_file(request, root, allowed_roots=resolver.roots)
    if (planned['output_mode'] != 'IMAGE_TO_SPRITE' or planned['parent'] is None
            or planned['source_brief']['output_class'] != 'NONPIXEL_IMAGE'
            or len(planned['images']) != 1 or planned['images'][0]['role'] != 'IDENTITY_PRIMARY'):
        raise ValueError('FACTORY_MOTION_SCOPE: one existing nonpixel IDENTITY_PRIMARY required')
    recipe = copy.deepcopy(job['recipe'])
    if not isinstance(recipe, dict) or set(recipe) != {'schema_version', 'selection', 'alpha'}:
        raise ValueError('FACTORY_MOTION_RECIPE_INVALID')
    probe_recipe = {**recipe, 'kind': 'MOTION_REVIEW_RECIPE', 'source_manifest': 'bound-after-package',
                    'source_sha256': '0'*64}
    Draft202012Validator(RECIPE_V2 if recipe['schema_version'] == 2 else RECIPE_V1).validate(probe_recipe)
    selection = recipe['selection']
    if not selection['start_frame'] <= selection['end_frame'] <= planned['motion_contract']['target_frames']:
        raise ValueError('FACTORY_MOTION_SELECTION_INVALID')
    incoming = job['input']
    if incoming['kind'] == 'EXISTING_VIDEO':
        from ..motion.package import _probe
        video = sources.file(incoming['path'], path.parent)
        if fingerprint(video) != incoming['sha256']:
            raise ValueError('FACTORY_MOTION_VIDEO_CHANGED')
        probe = _probe(video)
        from fractions import Fraction
        motion = planned['motion_contract']
        if (probe['frame_count'] != motion['target_frames']
                or abs(float(Fraction(probe['fps']))-motion['fps']) > 1e-6
                or abs(probe['duration_seconds']-motion['duration_seconds']) > 1/motion['fps']):
            raise ValueError('FACTORY_MOTION_VIDEO_CONTRACT_MISMATCH')
        input_plan = {**incoming, 'path': str(video), 'probe': probe}
        if 'generation_record' in incoming:
            row = incoming['generation_record']
            history = sources.file(row['path'], path.parent)
            if fingerprint(history) != row['sha256']:
                raise ValueError('FACTORY_MOTION_HISTORY_CHANGED')
            # Preserve historical bytes, without interpreting old model paths as
            # current inputs or treating this record as fresh generation consent.
            input_plan['generation_record'] = {'path': str(history), 'sha256': row['sha256']}
        generation = None
    else:
        from ..providers.video.executor import execution_plan
        prepared = resolver(path.parent / incoming['run_ref'])
        generation = execution_plan(prepared, root, allowed_roots=resolver.roots,
                                    **{k: incoming[k] for k in ['seed', 'width', 'height']})
        if generation['source_plan'] != planned:
            raise ValueError('FACTORY_MOTION_PREPARED_REQUEST_MISMATCH')
        input_plan = {**incoming, 'run_ref': str(prepared)}
    package = Path(__file__).parents[1]
    implementations = [Path(__file__), Path(__file__).with_name('planner.py'),
        Path(__file__).with_name('contracts.py'), Path(__file__).with_name('provenance.py')]
    implementations += [package / name for name in ['motion/package.py', 'motion/recipe.py',
        'motion/exports.py', 'motion/extractor/__init__.py', 'pixel/direct/ported.py',
        'paths.py', 'manifests/__init__.py']]
    implementations += sorted((package / '_ported/motion_extractor').rglob('*.py'))
    result = {'schema_version': 1, 'kind': 'FACTORY_MOTION_PLAN',
        'job_path': str(path), 'job_sha256': sha, 'source_plan': planned,
        'input': input_plan, 'recipe': recipe, 'generation_plan': generation,
        'implementation': {str(p): fingerprint(p) for p in implementations},
        'stages': ['video_or_authorized_probe', 'package', 'explicit_recipe', 'native_engine_resources'],
        'dispatches': 0, 'budget_reservations': 0, 'review_state': 'REVIEW_REQUIRED', 'game_ready': False}
    if sources.document(path)[1] != sha or plan_file(request, root, allowed_roots=resolver.roots) != planned:
        raise ValueError('FACTORY_MOTION_SOURCE_CHANGED')
    if incoming['kind'] == 'EXISTING_VIDEO' and fingerprint(video) != incoming['sha256']:
        raise ValueError('FACTORY_MOTION_VIDEO_CHANGED')
    if incoming.get('generation_record') and fingerprint(history) != incoming['generation_record']['sha256']:
        raise ValueError('FACTORY_MOTION_HISTORY_CHANGED')
    result['plan_sha256'] = _digest(result)
    return result


def run_job(job_path, plan_sha256, output, root, *, authorization=None,
            authorize_generation=False, allowed_roots=None):
    """One new run directory; never resume failed stages or retry a provider."""
    root, resolver = _policy(root, allowed_roots)
    plan = plan_job(job_path, root, allowed_roots=resolver.roots)
    if plan['plan_sha256'] != plan_sha256:
        raise ValueError('FACTORY_MOTION_PLAN_CHANGED')
    generated = plan['input']['kind'] == 'PREPARED_GENERATION'
    if generated and (authorize_generation is not True or authorization is None):
        raise ValueError('FACTORY_MOTION_GENERATION_NOT_AUTHORIZED')
    if not generated and (authorization is not None or authorize_generation):
        raise ValueError('FACTORY_MOTION_REPLAY_DISALLOWS_GENERATION')
    auth_record = None
    if generated:
        auth_path, auth_sha, _ = Sources(resolver).document(authorization)
        auth_record = {'path': str(auth_path), 'sha256': auth_sha}
    outputs = RootResolver([root], base=root)
    output = outputs(output, strict=False)
    workspace = outputs(root / 'workspace', strict=False)
    inputs = [Path(plan['job_path']), Path(plan['source_plan']['request']['path'])]
    inputs += [Path(row['path']) for row in plan['source_plan']['images']]
    inputs += [Path(row['path']) for row in plan['source_plan']['source_documents']]
    inputs += [Path(plan['input']['run_ref'] if generated else plan['input']['path'])]
    if plan['input'].get('generation_record'):
        inputs.append(Path(plan['input']['generation_record']['path']))
    if (workspace != root / 'workspace' or output == workspace or not output.is_relative_to(workspace)
            or any(p.is_relative_to(output) for p in inputs)):
        raise ValueError('FACTORY_MOTION_OUTPUT_INVALID')
    output.mkdir(parents=True, exist_ok=False)
    receipt = {'schema_version': 1, 'kind': 'FACTORY_MOTION_RECEIPT', 'status': 'STARTED',
        'started_at': now(), 'plan': plan, 'stages': [], 'outputs': [],
        'generation_requests': None if generated else 0,
        'authorization': auth_record,
        'engine_import': 'NOT_RUN',
        'retry': 'NONE', 'fallback': 'NONE', 'review_state': 'REVIEW_REQUIRED', 'game_ready': False}
    manifest = output / 'factory_motion.json'
    try:
        write(manifest, receipt)
        shutil.copyfile(plan['job_path'], output / 'job-input.json')
        if fingerprint(output / 'job-input.json') != plan['job_sha256']:
            raise ValueError('FACTORY_MOTION_SOURCE_CHANGED')
        from ..motion.package import package_video
        if generated:
            from ..providers.video.executor import execute_prepared
            incoming = plan['input']
            child = execute_prepared(incoming['run_ref'], authorization, root,
                authorize_generation=True, allowed_roots=resolver.roots,
                **{k: incoming[k] for k in ['seed', 'width', 'height']})
            # 생성 요청은 이미 나갔다. 아래 검증이 실패해도 하위 영수증을 찾을 수 있게 먼저 기록한다.
            receipt['generation_receipt'] = {'path': str(child), 'sha256': None}
            child = outputs(child)
            receipt['generation_receipt'] = {'path': str(child), 'sha256': fingerprint(child)}
            data = json.loads(child.read_text(encoding='utf-8'))
            if (data.get('status') != 'CANDIDATE_REVIEW_REQUIRED' or data.get('execution_plan') != plan['generation_plan']
                    or data.get('authorization_sha256') != auth_record['sha256']
                    or data.get('review_state') != 'REVIEW_REQUIRED' or data.get('game_ready') is not False
                    or data.get('queue_attempts') != 1 or data.get('uploads') != 1):
                raise ValueError('FACTORY_MOTION_GENERATION_RECEIPT_INVALID')
            package_manifest = outputs(data['package_manifest_path'])
            if fingerprint(package_manifest) != data['package_manifest_sha256']:
                raise ValueError('FACTORY_MOTION_GENERATION_RECEIPT_INVALID')
            receipt['generation_requests'] = data['queue_attempts']
        else:
            if plan['input'].get('generation_record'):
                row = plan['input']['generation_record']
                shutil.copyfile(row['path'], output / 'historical-generation.json')
                if fingerprint(output / 'historical-generation.json') != row['sha256']:
                    raise ValueError('FACTORY_MOTION_HISTORY_CHANGED')
            package_manifest = package_video(plan['source_plan']['request']['path'], plan['input']['path'],
                plan['input']['sha256'], output / 'package', root, allowed_roots=resolver.roots)
        receipt['stages'].append({'kind': 'PACKAGE', 'path': str(package_manifest),
                                  'sha256': fingerprint(package_manifest)})
        write(manifest, receipt)
        from ..motion.recipe import plan_recipe, apply_recipe, inspect_recipe
        recipe_path = output / 'recipe.json'
        write(recipe_path, {**plan['recipe'], 'kind': 'MOTION_REVIEW_RECIPE',
              'source_manifest': str(package_manifest), 'source_sha256': fingerprint(package_manifest)})
        recipe_plan = plan_recipe(recipe_path, root, allowed_roots=resolver.roots)
        recipe_manifest = apply_recipe(recipe_path, recipe_plan['plan_sha256'], output / 'candidate',
                                       root, allowed_roots=resolver.roots)
        inspect_recipe(recipe_manifest.parent, root, expected_sha256=fingerprint(recipe_manifest),
                       allowed_roots=resolver.roots)
        receipt['stages'].append({'kind': 'RECIPE', 'path': str(recipe_manifest),
                                  'sha256': fingerprint(recipe_manifest)})
        write(manifest, receipt)
        from ..motion.exports import export_candidate
        export_candidate(recipe_manifest.parent, fingerprint(recipe_manifest), output / 'exports', root,
                         allowed_roots=resolver.roots)
        if plan_job(job_path, root, allowed_roots=resolver.roots) != plan:
            raise ValueError('FACTORY_MOTION_SOURCE_CHANGED')
        if generated and fingerprint(auth_path) != auth_sha:
            raise ValueError('FACTORY_MOTION_AUTHORIZATION_CHANGED')
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


def inspect_job(run, expected_sha256, root, *, allowed_roots=None):
    root, resolver = _policy(root, allowed_roots)
    outputs = RootResolver([root], base=root)
    run = outputs(run)
    workspace = outputs(root / 'workspace')
    if workspace != root / 'workspace' or run == workspace or not run.is_relative_to(workspace):
        raise ValueError('FACTORY_MOTION_OUTPUT_INVALID')
    receipt = _receipt(run / 'factory_motion.json', expected_sha256, outputs)
    if (receipt.get('kind') != 'FACTORY_MOTION_RECEIPT'
            or receipt.get('status') != 'CANDIDATE_REVIEW_REQUIRED'
            or receipt.get('review_state') != 'REVIEW_REQUIRED' or receipt.get('game_ready') is not False):
        raise ValueError('FACTORY_MOTION_RUN_BLOCKED')
    plan = receipt['plan']
    if plan_job(plan['job_path'], root, allowed_roots=resolver.roots) != plan:
        raise ValueError('FACTORY_MOTION_SOURCE_CHANGED')
    present = {str(p) for p in run.rglob('*') if p.is_file() and p != run / 'factory_motion.json'}
    declared = set()
    for row in receipt['outputs']:
        path = outputs(row['path'])
        if not path.is_relative_to(run) or str(path) in declared or fingerprint(path) != row['sha256']:
            raise ValueError('FACTORY_MOTION_OUTPUT_CHANGED')
        declared.add(str(path))
    if present != declared:
        raise ValueError('FACTORY_MOTION_OUTPUT_CHANGED')
    from ..motion.recipe import inspect_recipe
    if [row['kind'] for row in receipt['stages']] != ['PACKAGE', 'RECIPE']:
        raise ValueError('FACTORY_MOTION_STAGES_INVALID')
    stage = receipt['stages'][1]
    stage_path = outputs(stage['path'])
    if stage_path != run / 'candidate/recipe_manifest.json':
        raise ValueError('FACTORY_MOTION_STAGES_INVALID')
    inspect_recipe(stage_path.parent, root, expected_sha256=stage['sha256'],
                   allowed_roots=resolver.roots)
    package = receipt['stages'][0]
    package_path = outputs(package['path'])
    if fingerprint(package_path) != package['sha256']:
        raise ValueError('FACTORY_MOTION_RECEIPT_CHANGED')
    if plan['generation_plan']:
        row = receipt['generation_receipt']
        data = _receipt(row['path'], row['sha256'], outputs)
        authorization = receipt['authorization']
        Sources(resolver).document(authorization['path'], authorization['sha256'])
        if (data.get('execution_plan') != plan['generation_plan'] or data.get('status') != 'CANDIDATE_REVIEW_REQUIRED'
                or data.get('authorization_sha256') != authorization['sha256']
                or outputs(data['package_manifest_path']) != package_path
                or data['package_manifest_sha256'] != package['sha256']
                or data.get('queue_attempts') != 1 or receipt['generation_requests'] != 1):
            raise ValueError('FACTORY_MOTION_GENERATION_RECEIPT_INVALID')
    elif package_path != run / 'package/run_manifest.json' or receipt['generation_requests'] != 0 or receipt['authorization'] is not None:
        raise ValueError('FACTORY_MOTION_STAGES_INVALID')
    return {'status': 'FACTORY_MOTION_INTEGRITY_PASS_REVIEW_REQUIRED',
            'manifest_sha256': expected_sha256, 'plan_sha256': plan['plan_sha256'],
            'generation_requests': receipt['generation_requests'],
            'review_state': 'REVIEW_REQUIRED', 'game_ready': False}
