"""Run-scoped override authorization, evidence and durable dispatch reservation."""
import hashlib
import json
from pathlib import Path

from . import approval, digest

DOMAINS = ['character', 'aircraft', 'vehicle', 'mecha', 'architecture', 'creature',
           'environment', 'prop', 'ui_illustration']
FAILURES = ['AIRCRAFT_GEOMETRY_FAILURE', 'VEHICLE_TOPOLOGY_FAILURE',
            'MECHA_TOPOLOGY_FAILURE', 'COMPOSITION_FAILURE', 'PERSPECTIVE_FAILURE',
            'SILHOUETTE_FAILURE', 'UNUSABLE_CROP', 'SCENE_STRUCTURE_FAILURE',
            'ROLE_IDENTITY_FAILURE']
OVERRIDE_FIELDS = {'model_override', 'workflow_override', 'executor_override',
                   'override_mode', 'override_reason', 'override_approval',
                   'failure_evidence', 'generation_authorization'}


def record_file(reference, root):
    """Records and referenced artifacts must stay inside the configured root."""
    path = (Path(root) / reference).resolve()
    if not path.is_relative_to(Path(root).resolve()):
        raise ValueError('Override evidence path outside configuration root')
    try:
        raw = path.read_bytes()
        record = json.loads(raw)
    except (OSError, ValueError) as exc:
        raise ValueError('Override evidence unavailable: ' + str(path)) from exc
    if not isinstance(record, dict):
        raise ValueError('Override evidence must be an object')
    return record, hashlib.sha256(raw).hexdigest()


def scoped(record, brief, style_id):
    for key, expected in [('project_id', brief.get('project_id', 'default')),
                          ('asset_id', brief['asset_id']), ('style_id', style_id)]:
        if record.get(key) != expected:
            raise ValueError('Override approval/evidence scope mismatch: ' + key)


def failure_records(brief, root, style_id, primary_workflow):
    references = brief.get('failure_evidence', [])
    if len(references) < 2 or len(set(references)) != len(references):
        raise ValueError('Rescue requires at least two distinct actual failure records')
    records, originals = [], set()
    for reference in references:
        record, sha = record_file(reference, root)
        scoped(record, brief, style_id)
        approval(record)
        if (record.get('state') != 'PRIMARY_ROUTE_SUBJECT_FAILURE'
                or record.get('workflow_id') != primary_workflow
                or record.get('subject_domain') != brief.get('subject_domain')
                or record.get('failure_type') not in FAILURES
                or not record.get('conditions')
                or not record.get('review_source')
                or not record.get('uncertainty')):
            raise ValueError('Rescue failure conditions/type/review/uncertainty invalid')
        artifact = (Path(root) / record.get('original_path', '')).resolve()
        if not artifact.is_relative_to(Path(root).resolve()) or not artifact.is_file():
            raise ValueError('Rescue original artifact unavailable')
        try:
            actual = hashlib.sha256(artifact.read_bytes()).hexdigest()
        except OSError as exc:
            raise ValueError('Rescue original artifact unreadable') from exc
        if actual != record.get('original_sha256') or actual in originals:
            raise ValueError('Rescue original hash mismatch or duplicate artifact')
        originals.add(actual)
        records.append({'id': reference, 'sha256': sha, 'record': record})
    return records


def authorize_override(brief, root, style_id, primary_workflow):
    if not (brief.get('model_override') or brief.get('workflow_override')):
        raise ValueError('Override requires explicit model or workflow')
    if brief.get('style_lock', True) is not True:
        raise ValueError('STYLE_LOCK_CONFLICT: override cannot change style')
    if not brief.get('override_reason', '').strip() or not brief.get('override_approval'):
        raise ValueError('Override requires reason and explicit user approval evidence')
    record, sha = record_file(brief['override_approval'], root)
    scoped(record, brief, style_id)
    approval(record)
    for key in ('model_override', 'workflow_override', 'executor_override',
                'override_mode', 'override_reason'):
        if record.get(key) != brief.get(key):
            raise ValueError('Override approval request mismatch: ' + key)
    failures = []
    if brief['override_mode'] == 'SUBJECT_RESCUE':
        if not brief.get('subject_domain') or record.get('rescue_exploration_approved') is not True:
            raise ValueError('Rescue requires subject domain and exploration approval')
        failures = failure_records(brief, root, style_id, primary_workflow)
        if record.get('failure_evidence_sha256s') != [item['sha256'] for item in failures]:
            raise ValueError('Rescue approval must bind exact failure evidence hashes')
    return {'reference': brief['override_approval'], 'sha256': sha, 'record': record}, failures


def executor_context(brief):
    # This engine has no agent dispatch/connection adapter. An installed CLI is
    # a generation provider, not proof that its agent commands this execution.
    requested = brief.get('executor_override')
    if requested not in (None, 'local_python'):
        raise ValueError('EXECUTOR_UNAVAILABLE: no verified connection for ' + requested)
    return {'requested': requested, 'actual': 'local_python',
            'verification': 'IN_PROCESS_PYTHON_ENGINE', 'agent': 'NOT_VERIFIED'}


def reserve_generation(brief, root, decision):
    """One approval permits one dispatch. Exclusive mkdir persists across restarts."""
    audit = decision.get('override')
    if not audit:
        return None
    reference = brief.get('generation_authorization')
    if not reference:
        raise ValueError('OVERRIDE_GENERATION_NOT_AUTHORIZED: explicit budget required')
    record, sha = record_file(reference, root)
    scoped(record, brief, audit['style_id'])
    approval(record)
    if (record.get('generation_approved') is not True or type(record.get('max_requests')) is not int or record.get('max_requests') != 1
            or record.get('override_approval_sha256') != audit['approval']['sha256']
            or record.get('workflow_id') != decision['selected_workflow']
            or record.get('model_profile') != audit['selected']['model_profile']
            or not record.get('cost_acknowledgement') or not record.get('request_id')):
        raise ValueError('OVERRIDE_GENERATION_NOT_AUTHORIZED: budget/scope mismatch')
    key = digest({'project': record['project_id'], 'request_id': record['request_id']})
    directory = (Path(root) / 'workspace/override_budget' / key).resolve()
    if not directory.is_relative_to(Path(root).resolve()):
        raise ValueError('Override budget reservation outside configuration root')
    directory.parent.mkdir(parents=True, exist_ok=True)
    try:
        directory.mkdir()
    except FileExistsError as exc:
        raise ValueError('OVERRIDE_BUDGET_CONSUMED: retry requires a new user authorization') from exc
    reservation = {'authorization': reference, 'authorization_sha256': sha,
                   'request_id': record['request_id'], 'max_requests': 1,
                   'reserved_requests': 1, 'state': 'RESERVED_NO_RETRY',
                   'workflow_id': record['workflow_id']}
    (directory / 'reservation.json').write_text(json.dumps(reservation, indent=2), encoding='utf-8')
    return reservation


def propose_rescue(brief, root, *, inspect_installation=False):
    """Advisory only: optional read-only live probes never queue a generation."""
    import copy
    import yaml
    from ..brief import validate
    from ..registry import load_registry
    from ..router import _route_bound
    from ..prompts import _compile_bound_prompt
    from .menu import bind_menu
    validate(brief)
    if brief['output_class'] != 'NONPIXEL_IMAGE' or not brief.get('subject_domain'):
        raise ValueError('Rescue proposal requires NONPIXEL_IMAGE and subject_domain')
    primary_brief = {k: copy.deepcopy(v) for k, v in brief.items() if k not in OVERRIDE_FIELDS}
    registry = load_registry(root)
    bound, menu = bind_menu(primary_brief, root, registry)
    if not menu:
        raise ValueError('Rescue proposal requires an operational style menu selection')
    failures = failure_records(brief, root, menu['style_id'], bound['workflow_preferences']['id'])
    data = yaml.safe_load((Path(root) / 'config/styles/style_menu_v1.yaml').read_text(encoding='utf-8'))
    candidates, rejected = [], {}
    inventory, nodes, probe_error = {}, None, None
    if inspect_installation:
        from .._ported.config import load_config
        from .._ported.comfy_bridge.client import ComfyClient
        config = load_config(Path(root) / 'config/pipeline.yaml')
        client = ComfyClient(config.section('comfyui').get('base_url', 'http://127.0.0.1:8188'), request_timeout=2)
        try:
            client.check_connection()
            nodes = client._json('/object_info')
            folders = {folder for wf in registry.values() for folder, files in wf.get('models', {}).items() if files}
            inventory = {folder: client.list_models(folder) for folder in sorted(folders)}
        except Exception as exc:
            probe_error = str(exc)
    for binding in data['styles'][menu['art_style']]['bindings'].values():
        workflow_id = binding['workflow_id']
        if workflow_id == bound['workflow_preferences']['id']:
            continue
        trial = copy.deepcopy(bound)
        trial.pop('art_style', None)
        trial.pop('style_selection_policy', None)
        # A locked project style remains checked by resolve_style. This is only
        # candidate compilation, never a run-specific SOT binding exception.
        trial['workflow_preferences'] = {'id': workflow_id, 'model_profile': binding['model_profile'],
                                          'allow_experimental': True}
        try:
            decision = _route_bound(trial, registry, root)
            compiled = _compile_bound_prompt(trial, registry[workflow_id], root)
        except ValueError as exc:
            rejected[workflow_id] = str(exc)
            continue
        wf = registry[workflow_id]
        missing = []
        installation = 'NOT_VERIFIED'
        if inspect_installation:
            if probe_error:
                installation = 'UNAVAILABLE'
            else:
                missing = [folder + '/' + name for folder, names in wf.get('models', {}).items()
                           for name in names if name not in inventory.get(folder, [])]
                graph = json.loads((Path(root) / wf['workflow_file']).read_text(encoding='utf-8'))
                missing += [node['class_type'] for node in graph.values() if node['class_type'] not in nodes]
                installation = 'MISSING_DEPENDENCIES' if missing else 'LIVE_INVENTORY_PRESENT'
        candidates.append({
            'model_profile': wf['model_profile'], 'workflow_id': workflow_id,
            'provider': wf.get('engine', 'comfyui'), 'installation': installation,
            'missing_dependencies': missing, 'probe_error': probe_error,
            'reason': 'Explicit style-compatible alternative to the evidenced failing primary route',
            'recipe': decision['style_selection'], 'required_capabilities': decision['required_capabilities'],
            'unsupported_capabilities': [key for key, value in wf['capabilities'].items() if not value],
            'potential_failure_targets': sorted({item['record']['failure_type'] for item in failures}),
            'expected_improvement': 'HYPOTHESIS_NOT_VALIDATED',
            'known_limitations': menu['known_limitations'] + ['Subject capability and artwork fidelity are unverified'],
            'execution_requirements': ['User rescue exploration approval', 'One-request durable generation budget',
                                       'Live installation/authentication and cost preflight', 'Explicit EXPERIMENTAL opt-in where required',
                                       'Human semantic/composition/style review'],
            'compiled_prompt': compiled, 'generation_state': 'GENERATION_NOT_RUN'})
        if len(candidates) == 3:
            break
    return {'state': 'PRIMARY_ROUTE_SUBJECT_FAILURE', 'failure_evidence': failures,
            'candidates': candidates, 'rejected_candidates': rejected,
            'generation_state': 'GENERATION_NOT_RUN', 'generation_requests': 0,
            'generation_authorized': False, 'review_state': 'REVIEW_REQUIRED',
            'fallback_policy': 'NONE_AUTOMATIC'}
