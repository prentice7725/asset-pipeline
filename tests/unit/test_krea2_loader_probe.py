"""Reporting must not promote partial parser results to adapter compatibility."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

spec = importlib.util.spec_from_file_location(
    'krea2_loader_probe', Path(__file__).parents[2] / 'scripts/krea2_loader_probe.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


@pytest.mark.parametrize('keys', [[], ['x.magnitude'], ['x.lora_A.weight']])
def test_unpaired_or_unrecognized_format_is_rejected(keys):
    with pytest.raises(ValueError):
        probe.diagnostic_map(keys)


def test_top_level_unloaded_scale_blocks_even_when_ab_consumed():
    keys = {'x.lora_A.weight': None, 'x.lora_B.weight': None, 'x.magnitude': None}
    adapter = SimpleNamespace(loaded_keys=set(keys) - {'x.magnitude'},
                              weights=(SimpleNamespace(shape=(3, 2)),
                                       SimpleNamespace(shape=(2, 3)), None, None, None, None))
    result = probe.summarize(keys, keys, {'x.weight': adapter},
                             ['lora key not loaded: x.magnitude'])
    assert result['status'] == 'INCOMPLETE_ADAPTER'
    assert result['unloaded_keys'] == ['x.magnitude']
    assert result['weight_application'] == 'NOT_RUN'
    assert result['base_model_mapping'] == 'NOT_VERIFIED'


def test_no_patches_cannot_pass_when_loader_is_silent():
    keys = {'x.lora_A.weight': None, 'x.lora_B.weight': None}
    assert probe.summarize(keys, keys, {}, [])['status'] == 'INCOMPLETE_ADAPTER'
