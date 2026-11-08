"""High-level core contracts shared by CLI integrations; no MCP dependency."""
import copy
from .paths import resolve_path, validate_run_manifest
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

def factory_plan(request_path, root, *, allowed_roots=None):
    """Read-only M3.0 presentation; no change to six MCP argument schemas."""
    from .factory import plan_file
    return plan_file(request_path, root, allowed_roots=allowed_roots)

def factory_execute(request_path, root, *, authorize_generation=False, seed=None, allowed_roots=None):
    from .factory.executor import execute_file
    return execute_file(request_path, root, authorize_generation=authorize_generation,
                        seed=seed, allowed_roots=allowed_roots)

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
        # VALIDATED: 실제 생성 증거가 지금 그래프와 맞는 워크플로. workflow id로 지정하면 allow_experimental 없이 쓴다.
        'validated_workflows': {k: {'output_class': v['output_class'], 'capabilities': v['capabilities'], 'tags': v['tags'],
            'selection': v.get('selection'), 'presets': sorted(v.get('presets', {})), 'evidence_check': v.get('evidence_check')}
            for k, v in registry.items() if v['status'] == 'VALIDATED'},
        'providers': ['comfyui', 'aseprite', 'codex_cli', 'grok_cli'], 'provider_readiness': readiness, 'external_cli_workflows': external, 'animation_actions': {'PIXEL_ANIMATION': ['walk'], 'NONPIXEL_ANIMATION': []},
        'optional_recovery': {'pixel_art_fixer': 'OPTIONAL_RECOVERY_NOT_AUTO_DISPATCHED'},
        'nonpixel_motion': {'status': 'SUPPORTED_EXPERIMENTAL', 'entrypoint': 'create --type nonpixel-animation --motion-job',
            'requires': ['pinned Factory motion job', 'plan SHA256', 'new output directory'],
            'reference_count': 1, 'source': 'existing NONPIXEL_IMAGE parent', 'automatic_generation': False,
            'generation_requires': ['prepared generation job', 'existing authorization', 'explicit consent', 'existing video executor gates'],
            'review_state': 'REVIEW_REQUIRED', 'game_ready': False},
        'environment_readiness': {'comfyui': comfy, 'aseprite': aseprite, 'ffmpeg': {'ready': bool(shutil.which('ffmpeg'))}},
        'limitations': ['codex_cli/grok_cli are EXPERIMENTAL, NONPIXEL_IMAGE only; request them by workflow id with allow_experimental. Seed, exact resolution, transparency and native negative prompts are unsupported; no automatic fallback between providers', 'NONPIXEL_ANIMATION requires an explicit pinned motion job; prompt/brief-only video execution remains unavailable', 'Eight reviewed blue-tunic/white-background walk phases only', 'Existing reviewed motion required; idle and attack are unsupported', 'krea2_pixel64 (VALIDATED, PIXEL_STATIC 64x64) needs the repository DoRA node installed in ComfyUI and is requested by workflow id; runs stop at RESOLUTION_REVIEW_REQUIRED, the transparent copy is a review candidate, and resolution review, Aseprite review and static approval are human CLI steps (review-resolution, export-static, approve-static)', 'BGM (audio_yue2_bgm) is EXPERIMENTAL with no real-generation evidence; request it by workflow id with allow_experimental. Instrumental by default; vocals, mood and loop seams require listening review', 'SFX synth (sfx_rfxgen) is EXPERIMENTAL with no real-execution evidence; it renders an explicit hash-pinned rfxgen .rfx (brief synth object, workflow id, allow_experimental), never interprets prompts, and still requires listening review']}

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

def route_brief(brief, root, resolver=None):
    missing = []
    try:
        validate(brief)
        decision = route(brief, load_registry(root))
    except ValueError as exc:
        return {'status': 'BLOCKED', 'selected_pipeline': brief.get('output_class', 'UNKNOWN'), 'selected_workflow': None, 'reason': str(exc), 'required_capabilities': [], 'missing_requirements': [str(exc)], 'fallback_candidates': [], **getattr(exc, 'details', {})}
    if brief['source']['type'] == 'DOCUMENTS' and not brief['identity']['canonical_traits']:
        missing.append('Source-backed canonical traits must be extracted into a prepared brief before generation')
    if brief['output_class'] == 'NONPIXEL_ANIMATION':
        missing.append('NONPIXEL_ANIMATION requires create --type nonpixel-animation --motion-job with a pinned plan; brief-only execution is unavailable')
    if brief['output_class'] == 'PIXEL_ANIMATION':
        try:
            animation_preflight(brief, resolver)
        except (ValueError, OSError, KeyError) as exc:
            missing.append(str(exc))
    return {**decision, 'status': 'BLOCKED' if missing else 'ROUTED', 'selected_pipeline': brief['output_class'],
        'reason': decision['selection_reason'], 'missing_requirements': missing}

def inspect_manifest(path, resolver=None):
    path = resolve_path(path, resolver)
    manifest = json.loads(path.read_text(encoding='utf-8'))
    # Same exemption as Factory: a CLI provider's original save location is provenance, not a read.
    validate_run_manifest(manifest, resolver)
    raw_status = manifest['status']
    if raw_status == 'FAILED':
        status = 'FAILED'
    elif 'REVIEW_REQUIRED' in raw_status:
        status = 'REVIEW_REQUIRED'
    else:
        status = raw_status
    route_path = resolve_path(path.parent / 'route_decision.json', resolver, strict=False)
    review = [raw_status] if status == 'REVIEW_REQUIRED' else []
    qa = [{'status': r.get('status'), 'step': r.get('step', 'pixel_gate' if 'alpha' in r else 'aseprite' if 'pixel_integrity' in r else 'qa')} for r in manifest.get('qa_results', [])]
    result = {'status': status, 'engine_status': raw_status, 'asset_id': manifest['asset_id'], 'output_class': manifest['output_class'],
        'workflow_id': manifest.get('workflow', {}).get('id'), 'workflow': manifest.get('workflow', {}),
        'manifest': str(path), 'qa': qa, 'outputs': manifest.get('outputs', []), 'review_items': review,
        'route': json.loads(route_path.read_text(encoding='utf-8')) if route_path.exists() else None,
        'error': manifest.get('error'), 'error_code': manifest.get('error_code'), 'provider': provider_summary(manifest), 'game_ready': manifest.get('game_ready', False)}
    delivery = transparent_summary(manifest, resolver)
    if delivery is not None:
        result['transparent_delivery'] = delivery
    approval = static_approval_summary(path, resolver) if manifest['output_class'] == 'PIXEL_STATIC' else None
    if approval is not None:
        result['static_approval'] = approval
    if manifest['output_class'] == 'PIXEL_STATIC' and status == 'REVIEW_REQUIRED' and not (approval or {}).get('valid'):
        # 사람 단계는 MCP로 대신하지 않는다. 다음에 무엇을 해야 하는지만 알려 준다.
        result['next_human_steps'] = {
            'RESOLUTION_REVIEW_REQUIRED': ['assetpipe review-resolution --run <run> --resolution <px> --reviewed-by <name> --reason <text>',
                                           'assetpipe export-static --run <run> --resolution-review <run>/resolution_review.json'],
            'EXPORT_READY_REVIEW_REQUIRED': ['open 060_aseprite/master.aseprite in Aseprite',
                                             'assetpipe approve-static --run <run> --reviewed-by <name> --reason <text> --aseprite-reviewed [--transparent <transparent.png>]'],
        }.get(raw_status, [])
    if manifest.get('audio_clip_receipt_path'):
        receipt = resolve_path(manifest['audio_clip_receipt_path'],resolver,strict=False)
        if not receipt.is_relative_to(path.parent):
            raise ValueError('SFX receipt must remain inside its run')
        result['audio_clip_receipt'] = str(receipt)
    return result


def static_approval_summary(manifest_path, resolver=None):
    """run 폴더의 approval_record.json을 다시 검증해 요약한다. 기록이 없으면 None."""
    from .pipelines.pixel_static.approval import validate_approval
    record_path = resolve_path(Path(manifest_path).parent / 'approval_record.json', resolver, strict=False)
    if not record_path.is_file():
        return None
    record = json.loads(record_path.read_text(encoding='utf-8'))
    try:
        validate_approval(record.get('approved_export', ''), record_path, resolver)
    except (ValueError, OSError, KeyError) as exc:
        return {'valid': False, 'record': str(record_path), 'error': str(exc)}
    delivery = record.get('delivery') or {}
    return {'valid': True, 'status': record['status'], 'record': str(record_path), 'approved_export': record['approved_export'],
            'reviewed_by': record['reviewed_by'], 'approved_at': record['approved_at'],
            'transparent': delivery.get('transparent'), 'transparent_possible_holes': delivery.get('possible_holes')}


def transparent_summary(manifest, resolver=None):
    """투명 납품본 상태와 구멍 가능성 수. 보고서는 같은 run 폴더 안의 것만 읽는다."""
    record = manifest.get('transparent_delivery')
    if not record:
        return None
    summary = {key: record[key] for key in ('status', 'reason', 'output', 'preview', 'aseprite_roundtrip', 'review') if key in record}
    if record.get('output'):
        report_path = resolve_path(Path(record['output']).parent / 'transparent_report.json', resolver, strict=False)
        if report_path.is_file():
            report = json.loads(report_path.read_text(encoding='utf-8'))
            regions = report.get('unresolved_enclosed_regions') or []
            summary['unresolved_enclosed_regions'] = len(regions)
            summary['possible_holes'] = report.get('possible_holes', len(regions))
    return summary


def provider_summary(manifest):
    """외부 CLI provider 실행 기록 중 검토에 필요한 요약만 돌려준다(로그·프롬프트 원문은 제외)."""
    record = manifest.get('generation', {}).get('provider')
    if not record:
        return None
    keys = ('provider_id', 'engine', 'tool', 'status', 'error_code', 'cli_version', 'model', 'auth', 'duration_seconds', 'request', 'usage_support', 'reproducibility', 'negative_prompt_mode', 'retry')
    return {key: record[key] for key in keys if key in record}
