"""Explicit, one-attempt adapter to existing still/audio pipelines. No motion."""
import json
import re
from pathlib import Path

from ..paths import RootResolver, validate_references
from ..manifests import now, write
from ..providers.cli_runner import assert_not_nested
from .planner import plan_file
from .provenance import Sources, validate_run_manifest


def execute_file(request_path, root, *, authorize_generation=False, seed=None,
                 allowed_roots=None):
    assert_not_nested()
    if authorize_generation is not True:
        raise ValueError('FACTORY_GENERATION_NOT_AUTHORIZED: explicit execution consent required')
    if type(seed) is not int or not 0 <= seed <= 2**32 - 1:
        raise ValueError('FACTORY_SEED_REQUIRED: explicit uint32 seed required')
    root = Path(root).resolve(strict=True)
    resolver = RootResolver(allowed_roots if allowed_roots is not None else [root], base=root)
    output_resolver = RootResolver([root], base=root)
    resolver(root)  # Execution configuration/output root must be explicitly allowed too.
    planned = plan_file(request_path, root, allowed_roots=resolver.roots)
    source = Sources(resolver)
    request_file, request_hash, request = source.document(planned['request']['path'])
    if request['output_mode'] == 'IMAGE_TO_SPRITE':
        raise ValueError('BLOCKED_BACKEND_NOT_VERIFIED: factory motion dispatch unavailable')
    if request['source']['kind'] != 'GENERATE':
        raise ValueError('FACTORY_SOURCE_READ_ONLY: existing sources cannot be regenerated')
    reference = request.get('authorization', {}).get('generation_budget')
    if not reference:
        raise ValueError('FACTORY_GENERATION_NOT_AUTHORIZED: one-attempt budget required')
    authorization_path, authorization_hash, authorization = source.document(reference, base=request_file.parent)
    fields = {'schema_version', 'type', 'authorization_id', 'project_id', 'asset_id',
              'request_sha256', 'workflow_id', 'workflow_sha256', 'seed',
              'max_requests', 'authorized_by', 'reason'}
    if (set(authorization) != fields or type(authorization['schema_version']) is not int
            or authorization['schema_version'] != 1
            or authorization['type'] != 'FACTORY_GENERATION_AUTHORIZATION'
            or type(authorization['max_requests']) is not int or authorization['max_requests'] != 1
            or type(authorization['seed']) is not int or authorization['seed'] != seed):
        raise ValueError('FACTORY_AUTHORIZATION_INVALID: explicit single-attempt contract required')
    identifier = authorization['authorization_id']
    if (not isinstance(identifier, str) or not re.fullmatch(r'[a-f0-9]{32}', identifier)
            or any(not isinstance(authorization[key], str) or not authorization[key].strip()
                   for key in ['authorized_by', 'reason'])):
        raise ValueError('FACTORY_AUTHORIZATION_INVALID: identity and attribution required')
    for key, expected in [('project_id', request['project_id']), ('asset_id', request['asset_id']),
                          ('request_sha256', request_hash)]:
        if authorization[key] != expected:
            raise ValueError('FACTORY_AUTHORIZATION_MISMATCH: ' + key)
    from ..api import route_brief
    from ..registry import load_registry
    from ..prompts import compile_prompt
    brief = planned['source_brief']
    validate_references(brief, resolver)
    decision = route_brief(brief, root, resolver)
    if decision['status'] != 'ROUTED':
        raise ValueError('FACTORY_ROUTE_BLOCKED: ' + '; '.join(decision['missing_requirements']))
    workflow = load_registry(root)[decision['selected_workflow']]
    if (authorization['workflow_id'] != decision['selected_workflow']
            or authorization['workflow_sha256'] != workflow['hash']):
        raise ValueError('FACTORY_AUTHORIZATION_MISMATCH: selected workflow')
    if brief['output_class'] == 'SFX':
        from ..pipelines.sfx import preflight
        preflight(brief, clip=planned['audio_contract'])
    else:
        compile_prompt(brief, workflow, root)  # Existing model/style compiler gates, before reservation.
    # Re-read every bound source before taking the durable budget; never dispatch stale plans.
    if plan_file(request_file, root, allowed_roots=resolver.roots) != planned:
        raise ValueError('FACTORY_SOURCE_CHANGED: replan required')
    if source.document(authorization_path)[1] != authorization_hash:
        raise ValueError('FACTORY_AUTHORIZATION_CHANGED')
    budget_root = output_resolver(root / 'workspace/factory_budget', strict=False)
    if budget_root != root / 'workspace/factory_budget':
        raise ValueError('FACTORY_BUDGET_PATH_INVALID: aliased budget directory')
    budget_root.mkdir(parents=True, exist_ok=True)
    reservation = output_resolver(budget_root / identifier, strict=False)
    if reservation != budget_root / identifier:
        raise ValueError('FACTORY_BUDGET_PATH_INVALID: aliased reservation')
    try:
        reservation.mkdir()  # Atomic across concurrent jobs; never released, even on failure.
    except FileExistsError as exc:
        raise ValueError('FACTORY_BUDGET_ALREADY_RESERVED') from exc
    receipt_path = reservation / 'execution.json'
    run = reservation / 'run'
    receipt = {'schema_version': 1, 'type': 'FACTORY_EXECUTION_RECEIPT',
               'status': 'RESERVED', 'project_id': request['project_id'], 'asset_id': request['asset_id'],
               'factory_line': request['factory_line'], 'output_mode': request['output_mode'],
               'request_path': str(request_file), 'request_sha256': request_hash,
               'authorization_path': str(authorization_path), 'authorization_sha256': authorization_hash,
               'source_documents': planned['source_documents'], 'route': decision,
               'seed': seed, 'attempts': 1, 'retry': 'NONE', 'fallback': 'NONE',
               'game_ready': False, 'review_state': 'REVIEW_REQUIRED', 'started_at': now()}
    try:
        write(receipt_path, receipt)
        from ..pipelines import create
        receipt['status'] = 'DISPATCH_STARTED'
        write(receipt_path, receipt)
        manifest_path = create(brief, root, run, seed, resolver=resolver,
                               clip=planned['audio_contract'],
                               expected_workflow={'id': decision['selected_workflow'], 'hash': workflow['hash']})
        manifest_path = output_resolver(manifest_path)
        if manifest_path != run / 'run_manifest.json':
            raise ValueError('FACTORY_RESULT_INVALID: unexpected manifest')
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        validate_run_manifest(manifest, output_resolver)
        if (manifest.get('game_ready') is not False or 'REVIEW_REQUIRED' not in manifest.get('status', '')
                or any(manifest.get(key) != brief[key] for key in ['asset_id', 'project_id', 'output_class'])):
            raise ValueError('FACTORY_RESULT_INVALID: candidate identity/review state differs')
        if any(item.get('status') == 'FAIL' for item in manifest.get('qa_results', [])):
            raise ValueError('FACTORY_QA_BLOCKED: candidate failed technical QA')
        from ..audio.sfx import sha
        if not manifest.get('outputs'):
            raise ValueError('OUTPUT_MISSING: factory candidate has no artifacts')
        artifacts = []
        for output in manifest.get('outputs', []):
            if not isinstance(output, str):
                raise ValueError('FACTORY_RESULT_INVALID: unexpected output contract')
            artifact = output_resolver(output)
            if not artifact.is_relative_to(run):
                raise ValueError('FACTORY_RESULT_INVALID: output outside its run')
            artifacts.append({'path': str(artifact), 'sha256': sha(artifact)})
        receipt.update(status='CANDIDATE_REVIEW_REQUIRED', manifest_path=str(manifest_path),
                       manifest_sha256=sha(manifest_path), engine_status=manifest['status'], artifacts=artifacts)
    except Exception as exc:
        receipt.update(status='FAILED', error=str(exc))
        raise
    finally:
        receipt['finished_at'] = now()
        write(receipt_path, receipt)
    return receipt_path
