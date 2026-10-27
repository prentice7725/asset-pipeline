"""Reporting must not promote partial parser results to adapter compatibility."""
import importlib.util
import json
import struct
import sys
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


@pytest.fixture
def contract():
    base = {'__metadata__': {'_quantization_metadata': json.dumps({
        'layers': {'layer': {'format': 'float8_e4m3fn'}}})},
        'layer.weight': {'shape': [4, 3], 'dtype': 'F8_E4M3'},
        'layer.weight_scale': {'shape': [], 'dtype': 'F32'}}
    lora = {'diffusion_model.layer.lora_A.weight': {'shape': [2, 3]},
            'diffusion_model.layer.lora_B.weight': {'shape': [4, 2]},
            'diffusion_model.layer.magnitude': {'shape': [4]}}
    mapping = {'diffusion_model.layer': 'diffusion_model.layer.weight'}
    return base, lora, mapping


def test_matching_base_shapes_do_not_infer_alpha_or_model_approval(contract):
    result = probe.assess_base_contract(*contract)
    assert result['shape_matches'] == result['quant_header_matches'] == 1
    assert result['alpha_over_rank'] == 'UNKNOWN_NOT_INFERRED'
    assert result['production_compatibility'] == 'BLOCKED'
    assert result['actual_model_instantiation'] == 'NOT_RUN'


@pytest.mark.parametrize('failure', ['missing_target', 'wrong_base_shape', 'wrong_magnitude'])
def test_base_contract_rejects_mapping_and_shape_errors(contract, failure):
    base, lora, mapping = contract
    if failure == 'missing_target':
        mapping.clear()
    elif failure == 'wrong_base_shape':
        base['layer.weight']['shape'] = [3, 4]
    else:
        lora['diffusion_model.layer.magnitude']['shape'] = [1, 4]
    assert probe.assess_base_contract(*contract)['shape_matches'] == 0


def test_missing_scale_never_passes_quantization_header_check(contract):
    del contract[0]['layer.weight_scale']
    result = probe.assess_base_contract(*contract)
    assert result['shape_matches'] == 1 and result['quant_header_matches'] == 0


def test_header_reader_rejects_offsets_outside_actual_payload(tmp_path):
    path = tmp_path / 'bad.safetensors'
    header = json.dumps({'weight': {'shape': [1], 'dtype': 'F32', 'data_offsets': [0, 4]}}).encode()
    path.write_bytes(struct.pack('<Q', len(header)) + header)
    with pytest.raises(ValueError, match='INVALID_TENSOR_HEADER'):
        probe.read_header(path)


@pytest.mark.parametrize('flags', [
    ['--probe-device', 'cuda'],
    ['--probe-device', 'cuda', '--probe-layers', '--probe-lora', '--source-dir', 'SOURCE', '--alpha-over-rank', '1'],
    ['--probe-lora', '--probe-layers', '--source-dir', 'SOURCE'],
    ['--probe-lora', '--probe-layers', '--alpha-over-rank', '1'],
    ['--probe-lora', '--source-dir', 'SOURCE', '--alpha-over-rank', '1'],
    ['--probe-lora', '--probe-layers', '--source-dir', 'SOURCE', '--alpha-over-rank', 'nan'],
    ['--probe-lora', '--probe-layers', '--source-dir', 'SOURCE', '--alpha-over-rank', '-1'],
    ['--alpha-over-rank', '1'], ['--source-dir', 'SOURCE'],
])
def test_lora_probe_never_infers_hypothesis_or_reads_weights_before_guard(tmp_path, monkeypatch, flags):
    output = tmp_path / 'evidence.json'
    args = ['probe', '--comfy-root', str(tmp_path), '--lora', str(tmp_path / 'lora'),
            '--base', str(tmp_path / 'base'), '--workflow', str(tmp_path / 'workflow'),
            '--output', str(output)]
    args += [str(tmp_path) if part == 'SOURCE' else part for part in flags]
    monkeypatch.setattr(sys, 'argv', args)
    def forbidden(*args):
        pytest.fail('Invalid hypothesis must reject before any weight hashing/loading')
    monkeypatch.setattr(probe, 'sha', forbidden)
    with pytest.raises(SystemExit) as exc:
        probe.main()
    assert exc.value.code == 2
    assert not output.exists()


def test_cpu_default_does_not_query_cuda():
    assert probe.assess_probe_device(SimpleNamespace(),'cpu')=={'status':'AVAILABLE','device':'cpu'}


def test_cuda_unavailable_does_not_fallback_or_query_memory():
    cuda=SimpleNamespace(is_available=lambda:False)
    result=probe.assess_probe_device(SimpleNamespace(cuda=cuda),'cuda')
    assert result['status']=='BLOCKED' and result['reason']=='CUDA_UNAVAILABLE'


@pytest.mark.parametrize('free,available',[(512*1024**2,False),(1536*1024**2,True)])
def test_cuda_memory_floor_is_explicit_and_fail_closed(free,available):
    cuda=SimpleNamespace(is_available=lambda:True,mem_get_info=lambda index:(free,8*1024**3),
        get_device_name=lambda index:'SYNTHETIC_GPU',get_device_capability=lambda index:(12,0))
    result=probe.assess_probe_device(SimpleNamespace(cuda=cuda),'cuda')
    assert result['device']=='cuda:0'
    assert (result['status']=='AVAILABLE')==available
    assert result['minimum_free_bytes']==1024**3
