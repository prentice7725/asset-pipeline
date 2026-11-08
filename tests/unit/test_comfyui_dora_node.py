"""Structure checks for the experimental ai-toolkit DoRA ComfyUI node (no torch/ComfyUI needed)."""
import pytest

from integrations import comfyui_dora


def _triple(stem):
    return {f'{stem}.lora_A.weight': 'A', f'{stem}.lora_B.weight': 'B', f'{stem}.magnitude': 'M'}


def test_groups_complete_triples_in_a_b_magnitude_order():
    groups = comfyui_dora.group_triples({**_triple('diffusion_model.blocks.0.attn.wk'),
                                         **_triple('diffusion_model.blocks.0.attn.gate')})
    assert groups == {'diffusion_model.blocks.0.attn.wk': ('A', 'B', 'M'),
                      'diffusion_model.blocks.0.attn.gate': ('A', 'B', 'M')}


def test_missing_magnitude_is_rejected_not_loaded_partially():
    state = _triple('x')
    del state['x.magnitude']
    with pytest.raises(ValueError, match='INCOMPLETE_TRIPLES'):
        comfyui_dora.group_triples(state)


@pytest.mark.parametrize('extra', ['x.alpha', 'x.dora_scale', 'x.lora_down.weight'])
def test_unexpected_keys_are_rejected(extra):
    with pytest.raises(ValueError, match='UNEXPECTED_KEY'):
        comfyui_dora.group_triples({**_triple('x'), extra: 'T'})


def test_node_is_registered_under_one_explicit_name():
    assert list(comfyui_dora.NODE_CLASS_MAPPINGS) == ['AssetpipeAIToolkitDoRALoader']
    assert 'EXPERIMENTAL' in comfyui_dora.AssetpipeAIToolkitDoRALoader.DESCRIPTION


def test_adapter_survives_comfyui_two_argument_rebuild(monkeypatch):
    """comfy.lora.prefetch_prepared_value rebuilds adapters as type(a)(loaded_keys, weights)."""
    import sys
    import types

    class Base:
        pass

    stubs = {'torch': types.SimpleNamespace(float32='float32'),
             'comfy': types.ModuleType('comfy'),
             'comfy.model_management': types.ModuleType('comfy.model_management'),
             'comfy.weight_adapter': types.ModuleType('comfy.weight_adapter'),
             'comfy.weight_adapter.base': types.SimpleNamespace(WeightAdapterBase=Base)}
    for name, module in stubs.items():
        monkeypatch.setitem(sys.modules, name, module)
    adapter_cls = comfyui_dora._adapter_class()
    adapter = adapter_cls({'k'}, ('A', 'B', 'M', 0.5))
    rebuilt = type(adapter)(adapter.loaded_keys, adapter.weights)
    assert rebuilt.weights == ('A', 'B', 'M', 0.5) and rebuilt.loaded_keys == {'k'}
