from pathlib import Path
import secrets
import json
from uuid import uuid4
from ..brief import validate
from ..registry import load_registry
from ..router import route
from ..manifests import write, now
from .._ported.config import load_config
from . import pixel_animation, pixel_static, nonpixel_image, nonpixel_animation

def create(brief, root, output=None, seed=None):
    validate(brief)
    root = Path(root).resolve()
    directory = Path(output).resolve() if output else root / 'workspace/runs' / brief['asset_id'] / uuid4().hex[:12]
    directory.mkdir(parents=True, exist_ok=False)
    manifest = {'schema_version': 1, 'asset_id': brief['asset_id'], 'input_type': brief['source']['type'], 'asset_brief': brief,
        'output_class': brief['output_class'], 'workflow': {}, 'generation': {}, 'pipeline_steps': [], 'qa_results': [],
        'outputs': [], 'timestamps': {'started': now()}, 'status': 'RUNNING', 'game_ready': False}
    path = directory / 'run_manifest.json'
    write(path, manifest)
    try:
        registry = load_registry(root)
        decision = route(brief, registry)
        write(directory / 'route_decision.json', decision)
        workflow = registry[decision['selected_workflow']]
        manifest['workflow'] = {'id': decision['selected_workflow'], 'hash': workflow['hash'], 'version': workflow['version'], 'model': workflow['models'], 'loras': workflow.get('loras', workflow['models'].get('loras', []))}
        manifest['pipeline_steps'].append({'step': 'router', 'status': 'PASS', 'mode': decision['execution_mode']})
        chosen_seed = secrets.randbits(32) if seed is None else seed
        manifest['generation'] = {'seed': chosen_seed, 'resolution': brief['constraints']['resolution'], 'prompt': brief.get('prompt'), 'negative_prompt': brief.get('negative_prompt', ''), 'comfy_prompt_id': None, 'mode': decision['execution_mode']}
        write(path, manifest)
        config = load_config(root / 'config/pipeline.yaml')
        kind = brief['output_class']
        if kind == 'PIXEL_ANIMATION':
            pixel_animation.run(brief, config, directory, manifest)
        elif kind == 'PIXEL_STATIC':
            pixel_static.run(brief, workflow, config, directory, manifest, chosen_seed)
        elif kind == 'NONPIXEL_IMAGE':
            nonpixel_image.run(brief, workflow, config, directory, manifest, chosen_seed)
        else:
            nonpixel_animation.run()
    except Exception as exc:
        manifest['status'] = 'FAILED'
        manifest['error'] = str(exc)
        raise
    finally:
        generation = directory / '010_generation/generation.json'
        if generation.exists():
            generated = json.loads(generation.read_text(encoding='utf-8'))
            manifest['generation'].update({'seed': generated['seed'], 'prompt': generated['prompt'], 'negative_prompt': generated['negative_prompt'], 'comfy_prompt_id': generated['prompt_id'], 'resolution': [generated['generation_parameters'].get('width'), generated['generation_parameters'].get('height')], 'parameters': generated['generation_parameters']})
        manifest['timestamps']['finished'] = now()
        write(path, manifest)
    return path
