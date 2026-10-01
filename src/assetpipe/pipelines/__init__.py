from pathlib import Path
import secrets
import json
from uuid import uuid4
from ..brief import validate
from ..registry import load_registry
from ..router import route
from ..manifests import write, now
from .._ported.config import load_config
from ..providers.base import ProviderError
from ..providers.cli_runner import assert_not_nested
from . import pixel_animation, pixel_static, nonpixel_image, nonpixel_animation

def create(brief, root, output=None, seed=None):
    # 생성 CLI 안에서 다시 시작된 assetpipe 실행(재귀·무한 호출)은 어떤 작업도 하기 전에 거부한다.
    assert_not_nested()
    validate(brief)
    root = Path(root).resolve()
    project_id = brief.get('project_id', 'default')
    directory = Path(output).resolve() if output else root / 'workspace' / project_id / 'runs' / brief['asset_id'] / uuid4().hex[:12]
    directory.mkdir(parents=True, exist_ok=False)
    manifest = {'schema_version': 1, 'project_id': project_id, 'asset_id': brief['asset_id'], 'input_type': brief['source']['type'], 'asset_brief': brief,
        'output_class': brief['output_class'], 'workflow': {}, 'generation': {}, 'pipeline_steps': [], 'qa_results': [],
        'outputs': [], 'timestamps': {'started': now()}, 'status': 'RUNNING', 'game_ready': False}
    path = directory / 'run_manifest.json'
    write(path, manifest)
    try:
        registry = load_registry(root)
        # Keep CLI/direct execution on the same blocking preflight used by MCP.
        # The import is local to avoid an import cycle while api.py imports pixel animation preflight.
        from ..api import route_brief
        decision = route_brief(brief, root)
        write(directory / 'route_decision.json', decision)
        if decision.get('style_selection'):
            manifest['style_selection'] = decision['style_selection']
        if decision['status'] == 'BLOCKED':
            raise ValueError('; '.join(decision['missing_requirements']) or decision['reason'])
        workflow = registry[decision['selected_workflow']]
        engine = workflow.get('engine', 'comfyui')
        manifest['workflow'] = {'id': decision['selected_workflow'], 'hash': workflow['hash'], 'version': workflow['version'], 'model': workflow['models'], 'loras': workflow.get('loras', workflow['models'].get('loras', []))}
        if engine != 'comfyui':
            manifest['workflow'].update({'engine': engine, 'selection': workflow.get('selection'), 'status': workflow['status']})
        manifest['pipeline_steps'].append({'step': 'router', 'status': 'PASS', 'mode': decision['execution_mode']})
        chosen_seed = secrets.randbits(32) if seed is None else seed
        manifest['generation'] = {'seed': chosen_seed, 'resolution': brief['constraints']['resolution'], 'prompt': brief.get('prompt'), 'negative_prompt': brief.get('negative_prompt', ''), 'comfy_prompt_id': None, 'mode': decision['execution_mode']}
        if engine != 'comfyui':
            # CLI provider는 seed와 정확한 재현을 지원하지 않는다. 임의 seed를 만들어 기록하지 않고 미지원으로 표시한다.
            manifest['generation'].update({'seed': None, 'seed_support': 'UNSUPPORTED', 'requested_seed': seed, 'exact_reproduction': 'UNSUPPORTED', 'comfy_prompt_id': None})
        write(path, manifest)
        config = load_config(root / 'config/pipeline.yaml')
        kind = brief['output_class']
        if kind == 'SFX':
            from .sfx import run
            run(brief, workflow, config, directory, manifest, chosen_seed)
        elif kind == 'PIXEL_ANIMATION':
            pixel_animation.run(brief, config, directory, manifest)
        elif kind == 'PIXEL_STATIC':
            pixel_static.run(brief, workflow, config, directory, manifest, chosen_seed)
        elif kind == 'NONPIXEL_IMAGE':
            # CLI provider에는 임의로 만든 seed를 넘기지 않는다(사용자가 지정한 값만 '요청됨'으로 기록).
            nonpixel_image.run(brief, workflow, config, directory, manifest, chosen_seed if engine == 'comfyui' else seed)
        else:
            nonpixel_animation.run()
    except Exception as exc:
        # 사용자 조치가 필요한 provider 상태(BLOCKED/UNAVAILABLE)는 일반 실패와 구분해 기록한다.
        manifest['status'] = exc.status if isinstance(exc, ProviderError) else 'FAILED'
        manifest['error'] = str(exc)
        if isinstance(exc, ProviderError):
            manifest['error_code'] = exc.code
        raise
    finally:
        compiled_path = directory / '010_generation/compiled_prompt.json'
        if compiled_path.exists():
            manifest['generation']['compiled_prompt'] = json.loads(compiled_path.read_text(encoding='utf-8'))
        generation = directory / '010_generation/generation.json'
        if generation.exists():
            generated = json.loads(generation.read_text(encoding='utf-8'))
            manifest['generation'].update({'seed': generated['seed'], 'prompt': generated['prompt'], 'negative_prompt': generated['negative_prompt'], 'comfy_prompt_id': generated['prompt_id'], 'resolution': [generated['generation_parameters'].get('width'), generated['generation_parameters'].get('height')], 'parameters': generated['generation_parameters']})
            if brief['output_class'] == 'SFX':
                manifest['generation'].pop('resolution', None)
                manifest['generation']['duration_seconds'] = generated['generation_parameters']['duration_seconds']
        manifest['timestamps']['finished'] = now()
        write(path, manifest)
    return path
