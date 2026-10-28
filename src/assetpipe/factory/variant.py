"""동일 인물 변형(표정·포즈) 작업: 기존 NONPIXEL_IMAGE 베이스 1장 → 참조 편집 1회.

T2I 베이스는 기존 정지 경로가 만든다. 이 모듈은 사람이 고른 베이스 출력 하나를 해시로 고정하고,
참조 편집 기능이 등록된 provider를 명시해 한 번만 실행한다. 재시도·provider 전환·자동 승인은 없다.
부모 검증은 Factory planner의 EXISTING_RUN 경로를, 예산 예약은 Factory 실행기와 같은 디렉터리를 쓴다.
"""
import copy
import json
import re
from pathlib import Path

from jsonschema import Draft202012Validator

from ..brief import obj, validate as validate_brief
from ..manifests import now, write
from ..paths import RootResolver
from .planner import plan as plan_request
from .provenance import Sources, fingerprint

HASH = {'type': 'string', 'pattern': '^[a-f0-9]{64}$'}
TEXT = {'type': 'string', 'minLength': 1, 'maxLength': 300}
IDENTIFIER = {'type': 'string', 'pattern': '^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$'}
KINDS = ['EXPRESSION', 'POSE']
SCHEMA = obj({'schema_version': {'type': 'integer', 'const': 1},
    'kind': {'const': 'FACTORY_IDENTITY_VARIANT_JOB'},
    'project_id': IDENTIFIER, 'asset_id': IDENTIFIER,
    'base': obj({'manifest_ref': TEXT, 'manifest_sha256': HASH,
                 'image': obj({'path': TEXT, 'sha256': HASH}, ['path', 'sha256']),
                 'selected_by': TEXT, 'reason': TEXT},
                ['manifest_ref', 'manifest_sha256', 'image', 'selected_by', 'reason']),
    'variation': obj({'kind': {'enum': KINDS}, 'target': TEXT}, ['kind', 'target']),
    'provider': obj({'workflow_id': IDENTIFIER}, ['workflow_id'])},
    ['schema_version', 'kind', 'project_id', 'asset_id', 'base', 'variation', 'provider'])
SCHEMA['$schema'] = 'https://json-schema.org/draft/2020-12/schema'
SCHEMA['$id'] = 'urn:assetpipe:factory-identity-variant-job:1'

# 변형 종류별로 바꿀 것과 유지할 것을 고정한다. 작업 파일에서 유지 항목을 줄일 수 없다.
IDENTITY = ['face shape and facial features', 'hairstyle and hair color', 'outfit and clothing details',
            'accessories', 'equipment and item count', 'body proportions', 'color palette', 'rendering style']
CHANGE = {'EXPRESSION': 'facial expression', 'POSE': 'body pose'}
PRESERVE = {'EXPRESSION': IDENTITY + ['body pose', 'framing and canvas', 'background'],
            'POSE': IDENTITY + ['background']}
# 베이스 모델용 화풍 바인딩·우회 필드. 편집 provider에는 맞지 않으므로 계획에 기록하고 제거한다.
# 화풍은 참조 이미지 자체와 유지 항목(rendering style)으로 전달한다.
PARENT_ONLY = ['style_id', 'art_style', 'style_selection_policy', 'model_override', 'workflow_override',
               'executor_override', 'override_mode', 'override_reason', 'override_approval',
               'failure_evidence', 'generation_authorization']
AUTHORIZATION_FIELDS = {'schema_version', 'type', 'authorization_id', 'project_id', 'asset_id',
                        'plan_sha256', 'workflow_id', 'workflow_sha256', 'max_requests',
                        'authorized_by', 'reason'}


def _digest(value):
    import hashlib
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _policy(root, allowed_roots):
    root = Path(root).resolve(strict=True)
    resolver = RootResolver(allowed_roots if allowed_roots is not None else [root], base=root)
    resolver(root)
    return root, resolver


def variation_constraints(kind, target):
    return ['Image edit of the provided reference image; the result shows the same character.',
            f'Change only the {CHANGE[kind]} to: {target}.',
            'Keep unchanged: ' + ', '.join(PRESERVE[kind]) + '.']


def variant_brief(parent, job, image_path):
    """부모 Brief의 정체성·금지 요소는 그대로 두고 소스·provider·변형 지시만 바꾼다."""
    brief = copy.deepcopy(parent)
    removed = [key for key in PARENT_ONLY if key in brief]
    for key in removed:
        brief.pop(key)
    kind, target = job['variation']['kind'], job['variation']['target']
    brief.update(asset_id=job['asset_id'], project_id=job['project_id'])
    brief['source'] = {'type': 'REFERENCE_IMAGE', 'paths': [image_path], 'references': []}
    brief['workflow_preferences'] = {'id': job['provider']['workflow_id'], 'allow_experimental': True}
    spec = copy.deepcopy(brief.get('prompt_spec')) or {
        'subject': brief.get('prompt') or ', '.join(brief['identity']['canonical_traits'])}
    if not spec['subject'].strip():
        raise ValueError('IDENTITY_VARIANT_SUBJECT_MISSING: parent Brief has no subject')
    if kind == 'POSE':
        spec['pose'] = target
    spec['constraints'] = list(dict.fromkeys(spec.get('constraints', []) + variation_constraints(kind, target)))
    spec.pop('style_contract_id', None)
    brief['prompt_spec'] = spec
    brief['source_notes'] = brief['source_notes'] + [
        {'classification': 'EXPLICIT', 'text': f'{kind} variant: {target}', 'source': 'identity variant job'}]
    return validate_brief(brief), removed


def plan_variant(job_path, root, *, allowed_roots=None):
    """읽기 전용 계획. provider 호출·예산 예약을 하지 않는다."""
    root, resolver = _policy(root, allowed_roots)
    sources = Sources(resolver)
    path, sha, job = sources.document(job_path)
    Draft202012Validator(SCHEMA).validate(job)
    base = job['base']
    request = {'factory_contract_version': 1, 'factory_line': 'NONPIXEL', 'output_mode': 'IMAGE_ONLY',
               'project_id': job['project_id'], 'asset_id': job['asset_id'],
               'image': {'style_source': 'IDENTITY_BASE_REFERENCE'}, 'motion': None,
               'source': {'kind': 'EXISTING_RUN', 'manifest_ref': base['manifest_ref'],
                          'manifest_sha256': base['manifest_sha256'],
                          'images': [{**base['image'], 'role': 'IDENTITY_PRIMARY'}]}}
    planned = plan_request(request, root, resolver=resolver, base=path.parent)
    parent_path = Path(planned['parent']['manifest_path'])
    if fingerprint(parent_path) != planned['parent']['manifest_sha256']:
        raise ValueError('IDENTITY_VARIANT_SOURCE_CHANGED')
    manifest = json.loads(parent_path.read_text(encoding='utf-8'))
    if (manifest.get('output_class') != 'NONPIXEL_IMAGE' or manifest.get('game_ready') is not False
            or manifest.get('status') != 'CANDIDATE_READY_REVIEW_REQUIRED'
            or any(row.get('status') == 'FAIL' for row in manifest.get('qa_results', []))):
        raise ValueError('IDENTITY_VARIANT_BASE_INVALID: base must be a QA-passing NONPIXEL_IMAGE candidate')
    if planned['parent']['asset_id'] == job['asset_id']:
        raise ValueError('IDENTITY_VARIANT_ASSET_ID: variant needs its own asset_id')
    image = planned['images'][0]
    brief, removed = variant_brief(planned['source_brief'], job, image['path'])
    from ..api import route_brief
    from ..registry import load_registry
    decision = route_brief(brief, root, resolver)
    if decision['status'] != 'ROUTED' or decision['selected_workflow'] != job['provider']['workflow_id']:
        raise ValueError('IDENTITY_VARIANT_ROUTE_BLOCKED: ' + '; '.join(decision.get('missing_requirements') or [str(decision.get('reason'))]))
    workflow = load_registry(root)[decision['selected_workflow']]
    capabilities = workflow['capabilities']
    if (workflow['output_class'] != 'NONPIXEL_IMAGE' or not capabilities.get('image_to_image')
            or not capabilities.get('character_reference') or not workflow.get('backend', {}).get('edit_tool')):
        raise ValueError('IDENTITY_VARIANT_PROVIDER_UNSUPPORTED: no registered reference edit path')
    result = {'schema_version': 1, 'kind': 'FACTORY_IDENTITY_VARIANT_PLAN',
        'job_path': str(path), 'job_sha256': sha, 'parent': planned['parent'], 'base_image': image,
        'base_selection': {'selected_by': base['selected_by'], 'reason': base['reason'],
                           'meaning': 'IDENTITY_BASE_CHOICE_NOT_ART_APPROVAL'},
        'variation': {**job['variation'], 'change': CHANGE[job['variation']['kind']],
                      'preserve': PRESERVE[job['variation']['kind']]},
        'removed_parent_fields': removed, 'brief': brief,
        'workflow': {'id': decision['selected_workflow'], 'hash': workflow['hash'],
                     'engine': workflow.get('engine'), 'status': workflow['status'],
                     'validation': copy.deepcopy(workflow.get('validation', {}))},
        'source_documents': planned['source_documents'],
        'dispatches': 0, 'budget_reservations': 0, 'retry': 'NONE', 'fallback': 'NONE',
        'identity_review': 'HUMAN_REQUIRED', 'review_state': 'REVIEW_REQUIRED', 'game_ready': False}
    if sources.document(path)[1] != sha or fingerprint(Path(image['path'])) != image['sha256']:
        raise ValueError('IDENTITY_VARIANT_SOURCE_CHANGED')
    result['plan_sha256'] = _digest(result)
    return result


def run_variant(job_path, plan_sha256, authorization, root, *, authorize_generation=False, allowed_roots=None):
    """승인된 1회 편집. 예약은 실패해도 해제하지 않으며 같은 예산 ID로 다시 실행할 수 없다."""
    from ..providers.cli_runner import assert_not_nested
    assert_not_nested()
    if authorize_generation is not True or authorization is None:
        raise ValueError('IDENTITY_VARIANT_NOT_AUTHORIZED: explicit consent and authorization required')
    root, resolver = _policy(root, allowed_roots)
    plan = plan_variant(job_path, root, allowed_roots=resolver.roots)
    if plan['plan_sha256'] != plan_sha256:
        raise ValueError('IDENTITY_VARIANT_PLAN_CHANGED')
    sources = Sources(resolver)
    auth_path, auth_sha, auth = sources.document(authorization)
    if (set(auth) != AUTHORIZATION_FIELDS or type(auth['schema_version']) is not int or auth['schema_version'] != 1
            or auth['type'] != 'IDENTITY_VARIANT_AUTHORIZATION'
            or type(auth['max_requests']) is not int or auth['max_requests'] != 1
            or not isinstance(auth['authorization_id'], str) or not re.fullmatch(r'[a-f0-9]{32}', auth['authorization_id'])
            or any(not isinstance(auth[key], str) or not auth[key].strip() for key in ['authorized_by', 'reason'])):
        raise ValueError('IDENTITY_VARIANT_AUTHORIZATION_INVALID: explicit single-attempt contract required')
    expected = {'project_id': plan['brief']['project_id'], 'asset_id': plan['brief']['asset_id'],
                'plan_sha256': plan['plan_sha256'], 'workflow_id': plan['workflow']['id'],
                'workflow_sha256': plan['workflow']['hash']}
    for key, value in expected.items():
        if auth[key] != value:
            raise ValueError('IDENTITY_VARIANT_AUTHORIZATION_MISMATCH: ' + key)
    outputs = RootResolver([root], base=root)
    budget_root = outputs(root / 'workspace/factory_budget', strict=False)
    if budget_root != root / 'workspace/factory_budget':
        raise ValueError('FACTORY_BUDGET_PATH_INVALID: aliased budget directory')
    budget_root.mkdir(parents=True, exist_ok=True)
    reservation = outputs(budget_root / auth['authorization_id'], strict=False)
    if reservation != budget_root / auth['authorization_id']:
        raise ValueError('FACTORY_BUDGET_PATH_INVALID: aliased reservation')
    try:
        reservation.mkdir()  # Factory 실행기와 같은 원자적 예약. 실패해도 해제하지 않는다.
    except FileExistsError as exc:
        raise ValueError('FACTORY_BUDGET_ALREADY_RESERVED') from exc
    receipt_path, run = reservation / 'variant.json', reservation / 'run'
    receipt = {'schema_version': 1, 'type': 'IDENTITY_VARIANT_RECEIPT', 'status': 'RESERVED',
               'plan': plan, 'authorization': {'path': str(auth_path), 'sha256': auth_sha},
               'attempts': 1, 'retry': 'NONE', 'fallback': 'NONE', 'reference_input': 'NOT_VERIFIED',
               'identity_review': 'HUMAN_REQUIRED', 'review_state': 'REVIEW_REQUIRED', 'game_ready': False,
               'started_at': now()}
    try:
        write(receipt_path, receipt)
        (reservation / 'job-input.json').write_bytes(Path(plan['job_path']).read_bytes())
        if fingerprint(reservation / 'job-input.json') != plan['job_sha256']:
            raise ValueError('IDENTITY_VARIANT_SOURCE_CHANGED')
        from ..pipelines import create
        receipt['status'] = 'DISPATCH_STARTED'
        write(receipt_path, receipt)
        manifest_path = outputs(create(plan['brief'], root, run, None, resolver=resolver,
                                       expected_workflow={'id': plan['workflow']['id'], 'hash': plan['workflow']['hash']}))
        if manifest_path != run / 'run_manifest.json':
            raise ValueError('IDENTITY_VARIANT_RESULT_INVALID: unexpected manifest')
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        # CLI provider 기록의 source_path는 provider가 처음 저장한 위치(출처)이며 여기서 읽지 않는다.
        # 실제로 쓰는 출력 파일만 아래에서 실행 폴더 안에 있는지 확인한다.
        if (manifest.get('game_ready') is not False or manifest.get('status') != 'CANDIDATE_READY_REVIEW_REQUIRED'
                or any(manifest.get(key) != plan['brief'][key] for key in ['asset_id', 'project_id', 'output_class'])
                or not manifest.get('outputs')):
            raise ValueError('IDENTITY_VARIANT_RESULT_INVALID: candidate identity/review state differs')
        # 참조 이미지가 provider 입력으로 복사됐는지만 확인한다. 모델이 실제로 반영했는지는 사람이 본다.
        provider = manifest.get('generation', {}).get('provider', {})
        if provider.get('reference', {}).get('sha256') != plan['base_image']['sha256'] or provider.get('tool') != 'image_edit':
            raise ValueError('IDENTITY_VARIANT_REFERENCE_NOT_SENT: provider record lacks the base image input')
        artifacts = []
        for output in manifest['outputs']:
            artifact = outputs(output)
            if not artifact.is_relative_to(run):
                raise ValueError('IDENTITY_VARIANT_RESULT_INVALID: output outside its run')
            artifacts.append({'path': str(artifact), 'sha256': fingerprint(artifact)})
        if sources.document(auth_path)[1] != auth_sha:
            raise ValueError('IDENTITY_VARIANT_AUTHORIZATION_CHANGED')
        receipt.update(status='CANDIDATE_REVIEW_REQUIRED', reference_input='COPIED_TO_PROVIDER_INPUT',
                       manifest_path=str(manifest_path), manifest_sha256=fingerprint(manifest_path), artifacts=artifacts)
    except Exception as exc:
        receipt.update(status='FAILED', error=str(exc))
        raise
    finally:
        receipt['finished_at'] = now()
        write(receipt_path, receipt)
    return receipt_path
