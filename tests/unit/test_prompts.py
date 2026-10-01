import copy
from pathlib import Path
import pytest
from assetpipe.brief import make, validate
from assetpipe.prompts import compile_prompt, workflow_values
from assetpipe.registry import load_registry
from assetpipe.router import route
from assetpipe.providers.comfyui import ComfyUIProvider
from assetpipe._ported.config import load_config

ROOT = Path(__file__).resolve().parents[2]


def brief():
    result = make(asset_id='courier', output_class='NONPIXEL_IMAGE', prompt='legacy compatibility')
    result.pop('prompt')
    result['prompt_spec'] = {'subject': 'Fantasy courier', 'appearance': ['green hood', 'mushroom backpack'],
        'pose': 'walking right', 'composition': 'full body, side view', 'style': ['pixel art'],
        'constraints': ['single character'], 'aspectRatio': '1:1',
        'styleSources': [{'url': 'https://kreastyles.thetacursed.com/', 'description': 'flat colors, crisp outlines'}]}
    return validate(result)


def test_adapters_preserve_requirements_without_mutating_canon():
    value = brief()
    original = copy.deepcopy(value)
    registry = load_registry(ROOT)
    anima = compile_prompt(value, registry['anima_base'], ROOT)
    krea = compile_prompt(value, registry['krea2_base'], ROOT)
    assert anima['positive'] != krea['positive']
    for compiled in (anima, krea):
        for requirement in ('green hood', 'mushroom backpack', 'walking right', 'single character', 'flat colors'):
            assert requirement in compiled['positive']
        assert compiled['prompt_spec']['styleSources'][0]['url'].startswith('https:')
    assert value == original


def test_prompt_spec_keeps_brief_style_and_silhouette_constraints():
    value = brief()
    value['constraints']['style'] = 'watercolor illustration'
    value['constraints']['silhouette'] = 'large triangular hat'
    workflow = load_registry(ROOT)['krea2_base']
    compiled = compile_prompt(value, workflow, ROOT)
    assert 'watercolor illustration' in compiled['prompt_spec']['style']
    assert 'large triangular hat' in compiled['prompt_spec']['constraints']
    assert 'watercolor illustration' in compiled['positive']
    assert 'large triangular hat' in compiled['positive']


def test_unsupported_requirements_block_routing():
    registry = load_registry(ROOT)
    value = brief()
    value['workflow_preferences']['id'] = 'krea2_base'
    value['prompt_spec']['negative'] = ['heavy armor']
    with pytest.raises(ValueError, match='capabilities'):
        route(value, registry)
    del value['prompt_spec']['negative']
    value['prompt_spec']['textInImage'] = ['POST']
    with pytest.raises(ValueError, match='text_rendering'):
        route(value, registry)


def test_aspect_ratio_is_workflow_input_and_conflicts_block():
    value = brief()
    workflow = load_registry(ROOT)['krea2_base']
    compiled = compile_prompt(value, workflow, ROOT)
    values = workflow_values(compiled, workflow, value)
    assert values['width'] == values['height']
    value['constraints']['resolution'] = [512, 768]
    with pytest.raises(ValueError, match='conflicts'):
        workflow_values(compiled, workflow, value)


def test_provider_passes_compiled_prompts_to_existing_workflow_adapter(monkeypatch, tmp_path):
    captured = {}
    def execute(config, **kwargs):
        captured.update(kwargs)
        return []
    monkeypatch.setattr('assetpipe.providers.comfyui.run_workflow', execute)
    value = brief()
    workflow = load_registry(ROOT)['krea2_base']
    ComfyUIProvider(load_config(ROOT / 'config/pipeline.yaml')).generate(value, workflow, tmp_path, 42)
    assert captured['seed'] == 42 and 'mushroom backpack' in captured['prompt']
    assert captured['negative_prompt'] == ''
    assert (tmp_path / 'compiled_prompt.json').is_file()
