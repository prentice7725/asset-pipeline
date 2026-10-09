"""High-level core contracts shared by CLI integrations; no MCP dependency."""
import copy
from pathlib import Path
import json
import shutil
from .brief import OUTPUT_CLASSES, make, validate
from .registry import load_registry
from .router import route
from ._ported.config import load_config
from ._ported.comfy_bridge.client import ComfyClient
from ._ported.aseprite_bridge.runner import find_aseprite, get_version
from .pipelines.pixel_animation import preflight as animation_preflight

def capabilities(root):
    registry = load_registry(root)
    config = load_config(Path(root) / 'config/pipeline.yaml')
    comfy = {'ready': False}
    try:
        stats = ComfyClient(config.section('comfyui').get('base_url', 'http://127.0.0.1:8188'), request_timeout=2).check_connection()
        comfy = {'ready': True, 'version': stats.get('system', {}).get('comfyui_version')}
    except Exception as exc:
        comfy['reason'] = str(exc)
    aseprite = {'ready': False}
    try:
        executable = find_aseprite(config.section('aseprite').get('executable'))
        if executable:
            aseprite = {'ready': True, 'version': get_version(executable, timeout=5)}
    except Exception as exc:
        aseprite['reason'] = str(exc)
    from .providers import diagnose_providers
    readiness = diagnose_providers(config)
    external = {k: {'engine': v['engine'], 'status': v['status'], 'selection': v.get('selection'), 'capabilities': v['capabilities'], 'validation': v.get('validation', {}).get('status')}
        for k, v in registry.items() if v.get('engine', 'comfyui') != 'comfyui'}
    return {'supported_output_classes': OUTPUT_CLASSES, 'input_types': ['DIRECT_PROMPT', 'REFERENCE_IMAGE', 'PROJECT_SOURCES'],
        'active_workflows': {k: {'output_class': v['output_class'], 'capabilities': v['capabilities'], 'tags': v['tags']} for k, v in registry.items() if v['status'] == 'ACTIVE'},
        'providers': ['comfyui', 'aseprite', 'codex_cli', 'grok_cli'], 'provider_readiness': readiness, 'external_cli_workflows': external, 'animation_actions': {'PIXEL_ANIMATION': ['walk'], 'NONPIXEL_ANIMATION': []},
        'optional_recovery': {'pixel_art_fixer': 'OPTIONAL_RECOVERY_NOT_AUTO_DISPATCHED'},
        'environment_readiness': {'comfyui': comfy, 'aseprite': aseprite, 'ffmpeg': {'ready': bool(shutil.which('ffmpeg'))}},
        'limitations': ['codex_cli/grok_cli are EXPERIMENTAL, NONPIXEL_IMAGE only; request them by workflow id with allow_experimental. Seed, exact resolution, transparency and native negative prompts are unsupported; no automatic fallback between providers', 'NONPIXEL_ANIMATION is contract-only', 'Eight reviewed blue-tunic/white-background walk phases only', 'Existing reviewed motion required; idle and attack are unsupported']}

def build_brief(*, request_text, output_class, asset_id='asset', source_documents=(), reference_image=None, action=None, prepared_brief=None, workflow_id=None):
    if prepared_brief is not None:
        brief = validate(copy.deepcopy(prepared_brief))
        if brief['output_class'] != output_class:
            raise ValueError('Prepared brief output class differs from requested output')
    else:
        brief = make(asset_id=asset_id, output_class=output_class, prompt=request_text, reference=reference_image, action=action)
        if source_documents:
            brief['source'] = {'type': 'DOCUMENTS', 'paths': list(source_documents), 'references': [reference_image] if reference_image else []}
            brief['source_notes'] = [{'classification': 'UNSPECIFIED', 'text': 'Canonical facts require source extraction into a prepared brief', 'source': p} for p in source_documents]
            brief['unspecified_elements'].append('source-backed canonical traits')
    if source_documents:
        if brief['source']['type'] != 'DOCUMENTS' or set(brief['source']['paths']) != set(source_documents):
            raise ValueError('Document brief must identify exactly the supplied source documents')
        if any(note['source'] not in source_documents for note in brief['source_notes']):
            raise ValueError('Document notes must cite the supplied sources')
    if workflow_id:
        brief['workflow_preferences']['id'] = workflow_id
    return validate(brief)

def route_brief(brief, root):
    missing = []
    try:
        validate(brief)
        decision = route(brief, load_registry(root))
    except ValueError as exc:
        return {'status': 'BLOCKED', 'selected_pipeline': brief.get('output_class', 'UNKNOWN'), 'selected_workflow': None, 'reason': str(exc), 'required_capabilities': [], 'missing_requirements': [str(exc)], 'fallback_candidates': [], **getattr(exc, 'details', {})}
    if brief['source']['type'] == 'DOCUMENTS' and not brief['identity']['canonical_traits']:
        missing.append('Source-backed canonical traits must be extracted into a prepared brief before generation')
    if brief['output_class'] == 'NONPIXEL_ANIMATION':
        missing.append('NONPIXEL_ANIMATION production execution is unavailable in v0.1')
    if brief['output_class'] == 'PIXEL_ANIMATION':
        try:
            animation_preflight(brief)
        except (ValueError, OSError, KeyError) as exc:
            missing.append(str(exc))
    return {**decision, 'status': 'BLOCKED' if missing else 'ROUTED', 'selected_pipeline': brief['output_class'],
        'reason': decision['selection_reason'], 'missing_requirements': missing}

def inspect_manifest(path):
    path = Path(path)
    manifest = json.loads(path.read_text(encoding='utf-8'))
    raw_status = manifest['status']
    if raw_status == 'FAILED':
        status = 'FAILED'
    elif 'REVIEW_REQUIRED' in raw_status:
        status = 'REVIEW_REQUIRED'
    else:
        status = raw_status
    route_path = path.parent / 'route_decision.json'
    review = [raw_status] if status == 'REVIEW_REQUIRED' else []
    qa = [{'status': r.get('status'), 'step': r.get('step', 'pixel_gate' if 'alpha' in r else 'aseprite' if 'pixel_integrity' in r else 'qa')} for r in manifest.get('qa_results', [])]
    return {'status': status, 'engine_status': raw_status, 'asset_id': manifest['asset_id'], 'output_class': manifest['output_class'],
        'workflow_id': manifest.get('workflow', {}).get('id'), 'workflow': manifest.get('workflow', {}),
        'manifest': str(path), 'qa': qa, 'outputs': manifest.get('outputs', []), 'review_items': review,
        'route': json.loads(route_path.read_text(encoding='utf-8')) if route_path.exists() else None,
        'error': manifest.get('error'), 'error_code': manifest.get('error_code'), 'provider': provider_summary(manifest), 'game_ready': manifest.get('game_ready', False)}


def provider_summary(manifest):
    """외부 CLI provider 실행 기록 중 검토에 필요한 요약만 돌려준다(로그·프롬프트 원문은 제외)."""
    record = manifest.get('generation', {}).get('provider')
    if not record:
        return None
    keys = ('provider_id', 'engine', 'tool', 'status', 'error_code', 'cli_version', 'model', 'auth', 'duration_seconds', 'request', 'usage_support', 'reproducibility', 'negative_prompt_mode', 'retry')
    return {key: record[key] for key in keys if key in record}
