"""Single-reference ComfyUI capability probe. Disabled by default; no auto approval."""
import copy
import json
import math
import os
import re
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

import yaml

from . import _policy, inspect_prepared, preflight_file
from ...factory.provenance import Sources, fingerprint
from ...manifests import now, write
from ...paths import RootResolver
from ...providers.cli_runner import assert_not_nested
from ...registry import load_registry
from .prompt import compile_reference_prompt
from ..._ported.comfy_bridge.client import ComfyClient
from ..._ported.comfy_bridge.runner import patch_workflow
from ..._ported.comfy_bridge.workflow_loader import load_workflow


def digest(value):
    import hashlib
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _compiler_sources(root):
    """Bind style/SOT files and reject aliases before the shared compiler reads."""
    resolver = RootResolver([root], base=root)
    pending = [resolver('config/styles')]
    visited, files = set(), {}
    while pending:
        directory = pending.pop()
        if directory in visited:
            continue
        visited.add(directory)
        for entry in directory.iterdir():
            path = resolver(entry)
            if path.is_dir():
                pending.append(path)
            elif path.suffix.lower() in {'.yaml', '.yml', '.json'}:
                files[str(path)] = fingerprint(path)
    # A consent digest also binds the shared semantic compiler implementation.
    package = Path(__file__).resolve().parents[2]
    for directory in ('prompts', 'styles', 'art_direction'):
        for path in (package / directory).rglob('*.py'):
            files[str(path)] = fingerprint(path)
    return [{'path': path, 'sha256': sha} for path, sha in sorted(files.items())]


def execution_plan(run, root, *, seed, width, height, allowed_roots=None):
    """Concrete, read-only compiler/graph preview for separately scoped probe consent."""
    root, resolver = _policy(root, allowed_roots)
    longest_output = root / 'workspace/factory_budget' / ('0' * 32) / 'package/extraction/frames/raw/frame_000001_t00000000ms.png'
    if os.name == 'nt' and len(str(longest_output)) > 240:
        raise ValueError('MOTION_OUTPUT_PATH_LIMIT: choose a shorter configuration root before authorizing generation')
    record = inspect_prepared(run, root, allowed_roots=resolver.roots)
    prepared = RootResolver([root], base=root)(Path(run) / 'prepared_motion.json')
    source = record['preflight']['plan']
    references = record['copied_references']
    if (source['parent'] is None or len(references) != 1
            or references[0]['role'] != 'IDENTITY_PRIMARY'
            or source['source_brief']['output_class'] != 'NONPIXEL_IMAGE'):
        raise ValueError('MOTION_PROBE_SCOPE: one existing nonpixel IDENTITY_PRIMARY required')
    if type(seed) is not int or not 0 <= seed <= 2**32 - 1:
        raise ValueError('MOTION_SEED_REQUIRED: explicit uint32 seed')
    if any(type(value) is not int or not 64 <= value <= 1344 or value % 16 for value in [width, height]):
        raise ValueError('MOTION_DIMENSIONS_INVALID: explicit multiples of 16 within 64..1344')
    if width * height > 768 * 1344:
        raise ValueError('MOTION_DIMENSIONS_INVALID: exceeds the research adapter area limit')
    motion = source['motion_contract']
    frames, fps = motion['target_frames'], motion['fps']
    if frames < 5 or frames > 240 or (frames - 5) % 17 or fps != 24:
        raise ValueError('MOTION_TIMING_UNSUPPORTED: MiniMax probe requires 17k+5 frames at 24fps')
    if abs(frames / fps - motion['duration_seconds']) > 1e-6:
        raise ValueError('MOTION_TIMING_MISMATCH')
    columns = min(frames, 4096 // width)
    if columns * width * math.ceil(frames / columns) * height > 32_000_000:
        raise ValueError('MOTION_ATLAS_LIMIT: choose explicit dimensions within the existing packer limit')
    workflow_id = record['preflight']['workflow']['id']
    if workflow_id != 'nonpixel_motion_contract':
        raise ValueError('MOTION_ADAPTER_UNSUPPORTED')
    workflow = load_registry(root)[workflow_id]
    graph_source = load_workflow(workflow['workflow_name'], root / 'config/workflows')
    model_slots = {'unet_name': 'diffusion_models', 'vae_name': 'vae',
                   'clip_name': 'text_encoders', 'acc_lora': 'loras', 'lora_name': 'loras'}
    graph_models = {(folder, node['inputs'][slot]) for node in graph_source.api_prompt.values()
                    for slot, folder in model_slots.items() if slot in node.get('inputs', {})}
    declared_models = {(folder, name) for folder, names in workflow.get('models', {}).items() for name in names}
    if not graph_models or declared_models != graph_models:
        raise ValueError('MOTION_MODEL_DECLARATION_MISMATCH: hash coverage must match graph model inputs')
    # Fail if this specific adapter's loader, conditioning edge or output changes.
    nodes = graph_source.api_prompt
    if (nodes.get('142', {}).get('class_type') != 'DenoMiniMaxH3ReferenceImageLoader'
            or graph_source.bindings.get('input_image', {}).get('node') != '142'
            or graph_source.bindings['input_image']['input'] != 'image_paths'
            or nodes.get('141', {}).get('inputs', {}).get('ref_images') != ['142', 0]
            or nodes.get('141', {}).get('class_type') != 'DenoMiniMaxH3ReferenceToVideo'
            or nodes.get('144', {}).get('class_type') != 'VHS_VideoCombine'
            or tuple(graph_source.output_nodes) != ('144',)):
        raise ValueError('MOTION_ADAPTER_GRAPH_CHANGED')
    brief = copy.deepcopy(source['source_brief'])
    compiler_sources = _compiler_sources(root)
    # The existing compiler still enforces project/style locks; never strip them.
    compiled = compile_reference_prompt(brief, workflow, root,
                                        resolver(source['parent']['manifest_path']), motion['action'])
    if _compiler_sources(root) != compiler_sources:
        raise ValueError('MOTION_COMPILER_SOURCE_CHANGED')
    graph = patch_workflow(graph_source, prompt=compiled['positive'], negative_prompt=compiled['negative'],
                           seed=seed, input_image='__ASSETPIPE_REFERENCE_0__',
                           filename_prefix='assetpipe_motion/__AUTHORIZATION_ID__',
                           workflow_inputs={'width': width, 'height': height, 'length': frames})
    if nodes['144']['inputs'].get('frame_rate') != fps:
        raise ValueError('MOTION_ADAPTER_GRAPH_CHANGED: output FPS differs')
    result = {'schema_version': 1, 'kind': 'MOTION_CAPABILITY_PROBE_PLAN',
              'prepared_path': str(prepared), 'prepared_sha256': fingerprint(prepared),
              'project_id': source['project_id'], 'asset_id': source['asset_id'],
              'workflow_id': workflow_id, 'workflow_sha256': graph_source.sha256,
              'executor_sha256': fingerprint(Path(__file__)),
              'motion_prompt_compiler_sha256': fingerprint(Path(__file__).with_name('prompt.py')),
              'compiler_sources': compiler_sources,
              'source_plan': source, 'references': references,
              'compiled_prompt': compiled, 'graph_template': graph,
              'parameters': {'seed': seed, 'width': width, 'height': height, 'frames': frames, 'fps': fps},
              'models': workflow['models'], 'purpose': 'SINGLE_REFERENCE_CAPABILITY_PROBE',
              'reference_role_semantics': 'NOT_VERIFIED', 'game_ready': False,
              'review_state': 'REVIEW_REQUIRED', 'dispatches': 0, 'budget_reservations': 0}
    result['execution_plan_sha256'] = digest(result)
    return result


def _authorization(path, plan, resolver):
    file, sha, value = Sources(resolver).document(path)
    fields = {'schema_version', 'kind', 'authorization_id', 'execution_plan_sha256',
              'project_id', 'asset_id', 'purpose', 'max_requests', 'authorized_by', 'reason', 'models'}
    if (set(value) != fields or type(value['schema_version']) is not int or value['schema_version'] != 1
            or value['kind'] != 'MOTION_ONE_REQUEST_AUTHORIZATION'
            or type(value['max_requests']) is not int or value['max_requests'] != 1
            or not isinstance(value['authorization_id'], str)
            or not re.fullmatch('[a-f0-9]{32}', value['authorization_id'])
            or any(not isinstance(value[key], str) or not value[key].strip() for key in ['authorized_by', 'reason'])):
        raise ValueError('MOTION_AUTHORIZATION_INVALID')
    if any(value[key] != plan[key] for key in ['execution_plan_sha256', 'project_id', 'asset_id', 'purpose']):
        raise ValueError('MOTION_AUTHORIZATION_MISMATCH')
    return file, sha, value


def _models(settings, authorization, required):
    roots = settings.get('model_roots', [])
    if not isinstance(roots, list) or not roots or any(not isinstance(value, str) or not Path(value).is_absolute() for value in roots):
        raise ValueError('MOTION_MODEL_ROOTS_REQUIRED')
    resolver = RootResolver(roots)
    expected = {(folder, name) for folder, names in required.items() for name in names}
    declared = authorization['models']
    if (not isinstance(declared, list) or len(declared) != len(expected)
            or any(not isinstance(row, dict) or set(row) != {'folder', 'name', 'sha256'}
                   or any(not isinstance(row[key], str) or not row[key] for key in ['folder', 'name', 'sha256'])
                   for row in declared)):
        raise ValueError('MOTION_MODEL_HASH_CONTRACT_INVALID')
    if len({(row['folder'], row['name']) for row in declared}) != len(expected):
        raise ValueError('MOTION_MODEL_HASH_CONTRACT_INVALID')
    receipts = []
    for row in declared:
        if ((row['folder'], row['name']) not in expected or Path(row['folder']).name != row['folder']
                or not isinstance(row['sha256'], str) or not re.fullmatch('[a-f0-9]{64}', row['sha256'])):
            raise ValueError('MOTION_MODEL_HASH_CONTRACT_INVALID')
        name = PurePosixPath(row['name'].replace('\\', '/'))
        if name.is_absolute() or '..' in name.parts or ':' in str(name):
            raise ValueError('MOTION_MODEL_PATH_INVALID')
        matches = []
        for model_root in resolver.roots:
            candidate = resolver(model_root / row['folder'] / str(name), strict=False)
            if candidate.exists():
                matches.append(candidate)
        if len(matches) != 1 or not matches[0].is_file():
            raise ValueError('MOTION_MODEL_MISSING_OR_AMBIGUOUS')
        model = matches[0]
        before = model.stat()
        if fingerprint(model) != row['sha256']:
            raise ValueError('MOTION_MODEL_HASH_MISMATCH')
        after = model.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ValueError('MOTION_MODEL_CHANGED')
        receipts.append({**row, 'path': str(model), 'size': after.st_size, 'mtime_ns': after.st_mtime_ns})
    if {(row['folder'], row['name']) for row in receipts} != expected:
        raise ValueError('MOTION_MODEL_HASH_CONTRACT_INVALID')
    return receipts


def _validate_graph(graph, info):
    for node in graph.values():
        schema = info.get(node['class_type'], {}).get('input', {})
        if not schema or not set(schema.get('required', {})).issubset(node['inputs']):
            raise ValueError('MOTION_NODE_SCHEMA_MISMATCH: ' + node['class_type'])
        slots = {**schema.get('required', {}), **schema.get('optional', {})}
        # VHS publishes codec-specific widgets in the selected format's schema,
        # not as top-level optional inputs. Validate those declarations too.
        format_spec = slots.get('format', [])
        if node['class_type'] == 'VHS_VideoCombine' and len(format_spec) > 1 and isinstance(format_spec[1], dict):
            widgets = format_spec[1].get('formats', {}).get(node['inputs'].get('format'), [])
            for widget in widgets:
                if not isinstance(widget, list) or len(widget) < 2 or not isinstance(widget[0], str):
                    raise ValueError('MOTION_FORMAT_SCHEMA_INVALID')
                if widget[0] in slots:
                    raise ValueError('MOTION_FORMAT_SCHEMA_INVALID: duplicate widget')
                slots[widget[0]] = widget[1:3]
        for key, value in node['inputs'].items():
            spec = slots.get(key)
            if not isinstance(spec, list) or not spec:
                raise ValueError('MOTION_NODE_INPUT_UNSUPPORTED: ' + key)
            if isinstance(value, list) and len(value) == 2 and isinstance(value[0], str):
                if value[0] not in graph or type(value[1]) is not int or value[1] < 0:
                    raise ValueError('MOTION_GRAPH_LINK_INVALID')
                continue
            if isinstance(spec[0], list) and value not in spec[0]:
                raise ValueError('MOTION_NODE_OPTION_UNAVAILABLE: ' + key)
            if spec[0] == 'BOOLEAN' and type(value) is not bool:
                raise ValueError('MOTION_NODE_BOOLEAN_INVALID: ' + key)
            if spec[0] == 'STRING' and not isinstance(value, str):
                raise ValueError('MOTION_NODE_STRING_INVALID: ' + key)
            if spec[0] in ['INT', 'FLOAT']:
                if (type(value) not in (int, float) or not math.isfinite(value)
                        or (spec[0] == 'INT' and type(value) is not int)):
                    raise ValueError('MOTION_NODE_NUMBER_INVALID: ' + key)
                limits = spec[1] if len(spec) > 1 and isinstance(spec[1], dict) else {}
                if value < limits.get('min', -math.inf) or value > limits.get('max', math.inf):
                    raise ValueError('MOTION_NODE_NUMBER_INVALID: ' + key)
                if spec[0] == 'INT' and limits.get('step') and 'min' in limits:
                    if (value - limits['min']) % limits['step']:
                        raise ValueError('MOTION_NODE_NUMBER_INVALID: ' + key)


def execute_prepared(run, authorization_path, root, *, seed, width, height,
                     authorize_generation=False, allowed_roots=None):
    """At most one upload/queue attempt per durable, root-scoped authorization ID."""
    assert_not_nested()
    if authorize_generation is not True:
        raise ValueError('MOTION_GENERATION_NOT_AUTHORIZED')
    root, resolver = _policy(root, allowed_roots)
    plan = execution_plan(run, root, seed=seed, width=width, height=height, allowed_roots=resolver.roots)
    auth_path, auth_sha, authorization = _authorization(authorization_path, plan, resolver)
    config_path = RootResolver([root], base=root)('config/pipeline.yaml')
    config = yaml.safe_load(config_path.read_text(encoding='utf-8'))
    settings = config.get('video_research', {})
    if settings.get('enabled') is not True:
        raise ValueError('MOTION_RESEARCH_DISABLED')
    model_receipts = _models(settings, authorization, plan['models'])
    live = preflight_file(plan['source_plan']['request']['path'], root,
                          allowed_roots=resolver.roots, inspect_installation=True)
    # These gates are addressed by this explicit probe's consent and local hash check;
    # semantic conditioning remains unverified, and is never reported as PASS.
    probe_gates = {'REFERENCE_CAPABILITY_NOT_VERIFIED', 'MODEL_CONTENT_HASHES_NOT_VERIFIED',
                   'GENERATION_AUTHORIZATION_NOT_EVALUATED'}
    blocked = [issue for issue in live['issues'] if issue['code'] not in probe_gates]
    if blocked or live['installation']['status'] != 'INVENTORY_ONLY':
        raise ValueError('MOTION_PREFLIGHT_BLOCKED: ' + '; '.join(item['code'] for item in blocked))
    url = urlsplit(config['comfyui']['base_url'])
    if url.scheme != 'http' or url.hostname not in {'127.0.0.1', 'localhost', '::1'}:
        raise ValueError('MOTION_LOCAL_SERVER_REQUIRED')
    client = ComfyClient(config['comfyui']['base_url'], request_timeout=10,
                         execution_timeout=1800, poll_interval=1)
    _validate_graph(plan['graph_template'], live['installation']['nodes'])
    if (execution_plan(run, root, seed=seed, width=width, height=height,
                       allowed_roots=resolver.roots) != plan or fingerprint(auth_path) != auth_sha):
        raise ValueError('MOTION_SOURCE_CHANGED')
    outputs = RootResolver([root], base=root)
    ledger = outputs(root / 'workspace/factory_budget', strict=False)
    if ledger != root / 'workspace/factory_budget':
        raise ValueError('MOTION_LEDGER_ALIAS_INVALID')
    ledger.mkdir(parents=True, exist_ok=True)
    identifier = authorization['authorization_id']
    reservation = outputs(ledger / identifier, strict=False)
    if reservation != ledger / identifier:
        raise ValueError('MOTION_LEDGER_ALIAS_INVALID')
    try:
        reservation.mkdir()
    except FileExistsError as exc:
        raise ValueError('MOTION_BUDGET_ALREADY_RESERVED') from exc
    receipt = {'schema_version': 1, 'kind': 'MOTION_CAPABILITY_PROBE_RECEIPT',
               'status': 'RESERVED', 'started_at': now(), 'execution_plan': plan,
               'authorization_path': str(auth_path), 'authorization_sha256': auth_sha,
               'models': model_receipts, 'installation': live['installation'], 'uploads': 0, 'queue_attempts': 0,
               'review_state': 'REVIEW_REQUIRED', 'game_ready': False, 'retry': 'NONE', 'fallback': 'NONE',
               'reference_role_semantics': 'NOT_VERIFIED'}
    receipt_path = reservation / 'motion_execution.json'
    try:
        write(receipt_path, receipt)
        graph = copy.deepcopy(plan['graph_template'])
        reference = plan['references'][0]
        preserved = outputs(reference['preserved_path'])
        if fingerprint(preserved) != reference['sha256']:
            raise ValueError('MOTION_SOURCE_CHANGED')
        receipt.update(status='UPLOAD_STARTED', uploads=1)
        write(receipt_path, receipt)
        uploaded = client.upload_image(preserved)
        if (not isinstance(uploaded, str) or not uploaded or '\x00' in uploaded or '\\' in uploaded or ':' in uploaded
                or PurePosixPath(uploaded).is_absolute() or '..' in PurePosixPath(uploaded).parts
                or '\n' in uploaded or '\r' in uploaded):
            raise ValueError('MOTION_UPLOAD_REFERENCE_INVALID')
        graph['142']['inputs']['image_paths'] = uploaded
        graph['144']['inputs']['filename_prefix'] = 'assetpipe_motion/' + identifier
        _validate_graph(graph, live['installation']['nodes'])
        if execution_plan(run, root, seed=seed, width=width, height=height, allowed_roots=resolver.roots) != plan:
            raise ValueError('MOTION_SOURCE_CHANGED')
        if fingerprint(auth_path) != auth_sha:
            raise ValueError('MOTION_AUTHORIZATION_CHANGED')
        for item in model_receipts:
            stat = Path(item['path']).stat()
            if (stat.st_size, stat.st_mtime_ns) != (item['size'], item['mtime_ns']):
                raise ValueError('MOTION_MODEL_CHANGED')
        write(reservation / 'compiled_prompt.json', plan['compiled_prompt'])
        write(reservation / 'submitted_graph.json', graph)
        receipt.update(status='QUEUE_STARTED', queue_attempts=1, uploaded_reference=uploaded,
                       submitted_graph_sha256=fingerprint(reservation / 'submitted_graph.json'))
        write(receipt_path, receipt)
        prompt_id = client.queue_prompt(graph, identifier)
        if not isinstance(prompt_id, str) or not re.fullmatch('[A-Za-z0-9_-]{1,128}', prompt_id):
            raise ValueError('MOTION_PROMPT_ID_INVALID')
        receipt.update(status='QUEUED', prompt_id=prompt_id)
        write(receipt_path, receipt)
        assets = client.wait_for_outputs(prompt_id, ('144',))
        history = client._json('/history/' + prompt_id)
        write(reservation / 'history.json', history)
        executed = history.get(prompt_id, {}).get('prompt')
        if not isinstance(executed, list) or len(executed) < 3 or executed[1] != prompt_id or executed[2] != graph:
            raise ValueError('MOTION_HISTORY_GRAPH_MISMATCH')
        if len(assets) != 1:
            raise ValueError('MOTION_VIDEO_OUTPUT_AMBIGUOUS')
        asset = assets[0]
        filename = asset.get('filename', '')
        if (not isinstance(filename, str) or '/' in filename or '\\' in filename
                or not filename.startswith(identifier + '_') or not filename.lower().endswith('.mp4')
                or asset.get('subfolder') != 'assetpipe_motion' or asset.get('type', 'output') != 'output'):
            raise ValueError('MOTION_VIDEO_OUTPUT_UNCORRELATED')
        original = reservation / 'original.mp4'
        client.download_asset(asset, original)
        receipt.update(status='VIDEO_DOWNLOADED', original_video_sha256=fingerprint(original),
                       reference_binding='HISTORY_GRAPH_MATCHED')
        write(receipt_path, receipt)
        # A generation may run for minutes. Never attach its video to a newer
        # coherently edited request or parent merely because that request is valid.
        if (execution_plan(run, root, seed=seed, width=width, height=height,
                           allowed_roots=resolver.roots) != plan or fingerprint(auth_path) != auth_sha):
            raise ValueError('MOTION_SOURCE_CHANGED: source or consent changed during generation')
        for item in model_receipts:
            stat = Path(item['path']).stat()
            if (stat.st_size, stat.st_mtime_ns) != (item['size'], item['mtime_ns']):
                raise ValueError('MOTION_MODEL_CHANGED: weights changed during generation')
        from ...motion.package import package_video
        package = package_video(plan['source_plan']['request']['path'], original,
                                receipt['original_video_sha256'], reservation / 'package', root,
                                allowed_roots=resolver.roots)
        if execution_plan(run, root, seed=seed, width=width, height=height, allowed_roots=resolver.roots) != plan:
            raise ValueError('MOTION_SOURCE_CHANGED: source changed during packaging')
        receipt.update(status='CANDIDATE_REVIEW_REQUIRED', package_manifest_path=str(package),
                       package_manifest_sha256=fingerprint(package))
    except Exception as exc:
        receipt.update(status='FAILED', error=str(exc))
        raise
    finally:
        receipt['finished_at'] = now()
        write(receipt_path, receipt)
    return receipt_path
