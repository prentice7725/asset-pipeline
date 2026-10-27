"""Read-only video preflight and immutable research inputs. No dispatch API."""
import json
import math
import shutil
from pathlib import Path
from urllib.parse import quote, urlsplit

import yaml

from ...factory.planner import plan_file
from ...factory.provenance import fingerprint, Sources
from ...manifests import now, write
from ...paths import RootResolver
from ...registry import load_registry
from ..._ported.comfy_bridge.client import ComfyClient
from ..._ported.comfy_bridge.workflow_loader import load_workflow


def _policy(root, allowed_roots):
    root = Path(root).resolve(strict=True)
    resolver = RootResolver(allowed_roots if allowed_roots is not None else [root], base=root)
    resolver(root)
    return root, resolver


def preflight_file(request_path, root, *, allowed_roots=None, inspect_installation=False):
    """Report separate source/compiler/install/capability gates; never reserve budget.

    Live inventory is GET-only. Node presence and filenames cannot verify reference
    cardinality, semantic roles, weight contents or real generation quality.
    """
    root, resolver = _policy(root, allowed_roots)
    config_resolver = RootResolver([root], base=root)
    plan = plan_file(request_path, root, allowed_roots=resolver.roots)
    if (plan['output_mode'] != 'IMAGE_TO_SPRITE'
            or plan['factory_line'] not in {'NONPIXEL', 'REFERENCE_MOTION'}
            or not plan['images']):
        raise ValueError('MOTION_PREFLIGHT_SOURCE_UNSUPPORTED: existing nonpixel/reference images required')
    workflow_id = plan['motion_contract'].get('workflow_id')
    if not workflow_id:
        raise ValueError('MOTION_WORKFLOW_REQUIRED: choose an explicit registered video workflow')
    # Validate configured transitive paths before the existing registry reads them.
    registry_path = config_resolver('config/workflow_registry.yaml')
    raw_registry = yaml.safe_load(registry_path.read_text(encoding='utf-8'))
    for entry in raw_registry.get('workflows', {}).values():
        if entry.get('workflow_file'):
            path = config_resolver(entry['workflow_file'])
            if not path.is_relative_to(root / 'config/workflows'):
                raise ValueError('MOTION_CONFIG_PATH_INVALID')
            name = entry.get('workflow_name', '')
            if not name or Path(name).name != name or '/' in name or '\\' in name:
                raise ValueError('MOTION_CONFIG_PATH_INVALID')
            config_resolver(root / 'config/workflows' / (name + '.json'))
        evidence = entry.get('validation', {}).get('evidence')
        if evidence:
            config_resolver(evidence, strict=False)
    registry = load_registry(root)
    workflow = registry.get(workflow_id)
    if (not workflow or workflow.get('engine', 'comfyui') != 'comfyui'
            or workflow['output_class'] != 'NONPIXEL_ANIMATION'
            or workflow['status'] == 'REJECTED'):
        raise ValueError('MOTION_WORKFLOW_UNSUPPORTED: registered ComfyUI NONPIXEL_ANIMATION required')
    graph = load_workflow(workflow['workflow_name'], root / 'config/workflows')
    settings_path = config_resolver('config/pipeline.yaml')
    profiles_path = config_resolver('config/model_profiles.yaml')
    settings = yaml.safe_load(settings_path.read_text(encoding='utf-8')).get('comfyui', {})
    issues = []

    def block(code, message):
        issues.append({'code': code, 'message': message})

    required_bindings = ['prompt', 'seed', 'input_image', 'length']
    for binding in required_bindings:
        if binding not in graph.bindings:
            block('MOTION_BINDING_MISSING', binding)
    for executable in ['ffmpeg', 'ffprobe']:
        if not shutil.which(executable):
            block('MOTION_TOOL_UNAVAILABLE', executable)
    motion = plan['motion_contract']
    if motion['background_policy'] != 'PRESERVE_OR_REVIEW':
        block('MOTION_ALPHA_NOT_VERIFIED', 'Background removal requires a separately verified policy')
    if (not math.isfinite(motion['fps']) or not math.isfinite(motion['duration_seconds'])
            or motion['fps'] > 60 or motion['duration_seconds'] > 10 or motion['target_frames'] > 240):
        block('MOTION_PACKAGE_LIMIT', 'Downstream package supports at most 60fps / 10s / 240 frames')
    if abs(motion['target_frames'] / motion['fps'] - motion['duration_seconds']) > 1 / motion['fps']:
        block('MOTION_TIMING_MISMATCH', 'Frame count, FPS and duration disagree')
    declared_fps = graph.defaults.get('fps')
    if declared_fps is None or motion['fps'] != declared_fps:
        block('MOTION_FPS_NOT_SUPPORTED', 'Requested FPS differs from the workflow declared FPS')
    profiles = yaml.safe_load(profiles_path.read_text(encoding='utf-8')).get('profiles', {})
    if workflow.get('model_profile') not in profiles:
        block('MOTION_PROMPT_PROFILE_MISSING', 'Canonical compiler needs an explicit configured video model profile')
    # Never substitute the still model's dialect or invent an external reference subject.
    if not (plan['source_brief'].get('prompt') or plan['source_brief']['identity']['canonical_traits']
            or plan['source_brief'].get('prompt_spec')):
        block('MOTION_PROMPT_SOURCE_UNSPECIFIED', 'Reference images alone do not define project canon or a PromptSpec')
    block('REFERENCE_CAPABILITY_NOT_VERIFIED', 'Exact ordered reference roles need actual provider consumption evidence')
    block('MODEL_CONTENT_HASHES_NOT_VERIFIED', 'Live filenames do not verify installed model contents')
    block('GENERATION_AUTHORIZATION_NOT_EVALUATED', 'No generation consent or budget is evaluated in preflight')
    installation = {'status': 'NOT_RUN', 'nodes': {}, 'models': {}}
    if inspect_installation:
        address = settings.get('base_url', 'http://127.0.0.1:8188')
        url = urlsplit(address)
        if (url.scheme != 'http' or url.hostname not in {'127.0.0.1', 'localhost', '::1'}
                or url.username or url.password or url.path not in {'', '/'} or url.query or url.fragment):
            raise ValueError('MOTION_LOCAL_SERVER_REQUIRED')
        client = ComfyClient(address, request_timeout=3)
        try:
            stats = client.check_connection()
            classes = sorted({node['class_type'] for node in graph.api_prompt.values()})
            node_info = {}
            # A global catalog can run slow/broken schema hooks for unrelated
            # extensions. Query every needed class directly; never skip a class.
            for name in classes:
                response = client._json('/object_info/' + quote(name, safe=''))
                if not isinstance(response, dict):
                    raise ValueError('Invalid object_info response')
                if name in response:
                    node_info[name] = response[name]
            installation.update(status='INVENTORY_ONLY', version=stats.get('system', {}).get('comfyui_version'),
                                nodes={name: node_info.get(name) for name in classes})
            for name in classes:
                if name not in node_info:
                    block('MOTION_NODE_MISSING', name)
            for name, binding in graph.bindings.items():
                node = graph.api_prompt[binding['node']]
                schema = node_info.get(node['class_type'], {}).get('input', {})
                inputs = {**schema.get('required', {}), **schema.get('optional', {})}
                spec = inputs.get(binding['input'])
                if spec is None:
                    block('MOTION_BINDING_UNAVAILABLE', name + ': ' + binding['input'])
                elif name == 'length' and isinstance(spec, list) and len(spec) > 1 and isinstance(spec[1], dict):
                    limits = spec[1]
                    value = motion['target_frames']
                    minimum, maximum, step = limits.get('min'), limits.get('max'), limits.get('step')
                    if ((minimum is not None and value < minimum)
                            or (maximum is not None and value > maximum)
                            or (step and minimum is not None and (value - minimum) % step)):
                        block('MOTION_FRAME_COUNT_UNSUPPORTED', 'Requested length violates the live node schema')
            for folder, names in workflow.get('models', {}).items():
                present = client.list_models(folder)
                installation['models'][folder] = {name: name in present for name in names}
                for name in names:
                    if name not in present:
                        block('MOTION_MODEL_MISSING', folder + '/' + name)
        except Exception as exc:
            installation.update(status='UNAVAILABLE', error=str(exc))
            block('COMFYUI_UNAVAILABLE', str(exc))
    else:
        block('MOTION_INSTALLATION_NOT_CHECKED', 'Use explicit read-only installation inspection')
    return {'schema_version': 1, 'kind': 'MOTION_PREFLIGHT', 'status': 'BLOCKED',
            'plan': plan, 'workflow': {'id': workflow_id, 'sha256': graph.sha256,
                                     'status': workflow['status'], 'bindings': graph.bindings,
                                     'defaults': graph.defaults, 'models': workflow.get('models', {})},
            'configuration': [{'path': str(path), 'sha256': fingerprint(path)} for path in
                              [registry_path, settings_path, profiles_path, graph.path]],
            'references': [{**image, 'order': index} for index, image in enumerate(plan['images'])],
            'installation': installation, 'issues': issues, 'dispatches': 0,
            'budget_reservations': 0, 'uploads': 0, 'generation_allowed': False,
            'reference_consumption': 'NOT_VERIFIED', 'review_state': 'REVIEW_REQUIRED', 'game_ready': False}


def prepare_file(request_path, output, root, *, allowed_roots=None):
    """Freeze source inputs for research without network, executable graph or approval."""
    root, resolver = _policy(root, allowed_roots)
    report = preflight_file(request_path, root, allowed_roots=resolver.roots)
    outputs = RootResolver([root], base=root)
    directory = outputs(output, strict=False)
    workspace = outputs(root / 'workspace', strict=False)
    if workspace != root / 'workspace' or directory == workspace or not directory.is_relative_to(workspace):
        raise ValueError('MOTION_OUTPUT_INVALID: use a new directory under workspace')
    directory.mkdir(parents=True, exist_ok=False)
    record = {'schema_version': 1, 'kind': 'MOTION_PREPARED_INPUTS',
              'status': 'PREPARING', 'created_at': now(), 'preflight': report,
              'generation_allowed': False, 'game_ready': False, 'review_state': 'REVIEW_REQUIRED',
              'retry': 'NONE', 'fallback': 'NONE', 'copied_references': []}
    manifest_path = directory / 'prepared_motion.json'
    try:
        write(manifest_path, record)
        reference_dir = directory / 'references'
        reference_dir.mkdir()
        for reference in report['references']:
            source = resolver(reference['path'])
            if fingerprint(source) != reference['sha256']:
                raise ValueError('MOTION_SOURCE_CHANGED')
            target = reference_dir / (str(reference['order']) + '_' + reference['role'] + source.suffix.lower())
            shutil.copyfile(source, target)
            if fingerprint(target) != reference['sha256']:
                raise ValueError('MOTION_SOURCE_CHANGED')
            record['copied_references'].append({**reference, 'preserved_path': str(target)})
        # Source/config drift cannot produce a completed preparation.
        if preflight_file(request_path, root, allowed_roots=resolver.roots) != report:
            raise ValueError('MOTION_SOURCE_CHANGED: preflight no longer matches')
        record['status'] = 'PREPARED_BLOCKED'
    except Exception as exc:
        record.update(status='FAILED', error=str(exc))
        raise
    finally:
        write(manifest_path, record)
    return manifest_path


def inspect_prepared(run, root, *, allowed_roots=None):
    """Revalidate exact prepared sources/config; no resume, uploads or approval."""
    root, resolver = _policy(root, allowed_roots)
    output_resolver = RootResolver([root], base=root)
    run = output_resolver(run)
    path = output_resolver(run / 'prepared_motion.json')
    _, _, record = Sources(resolver).document(path)
    if record.get('kind') != 'MOTION_PREPARED_INPUTS' or record.get('status') != 'PREPARED_BLOCKED':
        raise ValueError('MOTION_PREPARATION_INVALID')
    report = record['preflight']
    current = preflight_file(report['plan']['request']['path'], root, allowed_roots=resolver.roots)
    if current != report:
        raise ValueError('MOTION_SOURCE_CHANGED: request, references or configuration differs')
    copies = record['copied_references']
    if len(copies) != len(current['references']):
        raise ValueError('MOTION_REFERENCE_BINDING_INVALID')
    for copy, expected in zip(copies, current['references']):
        preserved = output_resolver(copy['preserved_path'])
        if (not preserved.is_relative_to(run / 'references')
                or {key: value for key, value in copy.items() if key != 'preserved_path'} != expected
                or fingerprint(preserved) != expected['sha256']):
            raise ValueError('MOTION_REFERENCE_BINDING_INVALID')
    if (record.get('generation_allowed') is not False or record.get('game_ready') is not False
            or record.get('review_state') != 'REVIEW_REQUIRED'):
        raise ValueError('MOTION_PREPARATION_INVALID: review/generation state changed')
    return record
