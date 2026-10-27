"""Installed ComfyUI parser and bounded projection probes; never generate or rewrite weights.

Run with the installed ComfyUI Python, not the assetpipe environment. A diagnostic
identity key map isolates file-format parsing; it does not verify base-model mapping.
"""
import argparse
import hashlib
import importlib
import json
import logging
import math
import struct
import sys
from types import SimpleNamespace
from datetime import datetime, timezone
from pathlib import Path


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def diagnostic_map(keys):
    stems = sorted(key[:-len('.lora_A.weight')] for key in keys
                   if key.endswith('.lora_A.weight'))
    if not stems or any(stem + '.lora_B.weight' not in keys for stem in stems):
        raise ValueError('Expected paired lora_A.weight / lora_B.weight tensors')
    return {stem: stem + '.weight' for stem in stems}


def read_header(path):
    with path.open('rb') as stream:
        prefix = stream.read(8)
        if len(prefix) != 8:
            raise ValueError('TRUNCATED_HEADER')
        size = struct.unpack('<Q', prefix)[0]
        if not 2 <= size <= 16_000_000:
            raise ValueError('HEADER_SIZE_OUT_OF_SCOPE')
        data = stream.read(size)
        if len(data) != size:
            raise ValueError('TRUNCATED_HEADER')
    header = json.loads(data)
    payload = path.stat().st_size - 8 - size
    for key, value in header.items():
        if key == '__metadata__':
            continue
        offsets, shape = value['data_offsets'], value['shape']
        if (len(offsets) != 2 or any(type(n) is not int for n in offsets)
                or not 0 <= offsets[0] <= offsets[1] <= payload
                or any(type(n) is not int or n < 0 for n in shape)):
            raise ValueError('INVALID_TENSOR_HEADER: ' + key)
    return header


def assess_base_contract(base, lora, key_map):
    quant = json.loads(base.get('__metadata__', {}).get('_quantization_metadata', '{}')).get('layers', {})
    rows = []
    for stem in diagnostic_map(lora):
        target = key_map.get(stem)
        file_key = target.removeprefix('diffusion_model.') if isinstance(target, str) else None
        tensor = base.get(file_key, {})
        a, b = lora[stem + '.lora_A.weight']['shape'], lora[stem + '.lora_B.weight']['shape']
        magnitude = lora.get(stem + '.magnitude', {}).get('shape')
        match = (len(a) == len(b) == 2 and a[0] > 0 and a[0] == b[1]
                 and tensor.get('shape') == [b[0], a[1]] and magnitude == [b[0]])
        layer = file_key.removesuffix('.weight') if file_key else None
        conf = quant.get(layer)
        scale = base.get((layer + '.weight_scale') if layer else '', {})
        rows.append({'lora_stem': stem, 'mapped_target': target, 'base_key': file_key,
                     'base_shape': tensor.get('shape'), 'base_dtype': tensor.get('dtype'),
                     'down_shape': a, 'up_shape': b, 'magnitude_shape': magnitude,
                     'rank': a[0] if len(a) == 2 else None, 'shape_match': match,
                     'quant_config': conf, 'scale_shape': scale.get('shape'),
                     'scale_dtype': scale.get('dtype'),
                     'quant_header_match': bool(conf and conf.get('format') == 'float8_e4m3fn'
                         and tensor.get('dtype') == 'F8_E4M3' and scale.get('shape') == []
                         and scale.get('dtype') == 'F32')})
    return {'scope': 'INSTALLED_MAPPER_ON_HEADER_ONLY_KREA2_SKELETON',
            'targets': len(rows), 'shape_matches': sum(r['shape_match'] for r in rows),
            'quant_header_matches': sum(r['quant_header_match'] for r in rows),
            'alpha_tensor_count': sum(k.endswith('.alpha') for k in lora),
            'alpha_over_rank': 'UNKNOWN_NOT_INFERRED',
            'authored_base': lora.get('__metadata__', {}).get('ss_base_model'),
            'actual_model_instantiation': 'NOT_RUN', 'weight_application': 'NOT_RUN',
            'production_compatibility': 'BLOCKED', 'rows': rows}


def base_mapping(header, torch):
    import comfy.lora
    import comfy.model_base
    import comfy.model_detection
    types = {'F8_E4M3': torch.float8_e4m3fn, 'BF16': torch.bfloat16,
             'F32': torch.float32, 'F16': torch.float16, 'I64': torch.int64, 'U8': torch.uint8}
    shapes = {k: torch.empty(v['shape'], dtype=types[v['dtype']], device='meta')
              for k, v in header.items() if k != '__metadata__'}
    config = comfy.model_detection.detect_unet_config(shapes, '', metadata=header.get('__metadata__'))
    if config.get('image_model') != 'krea2':
        raise ValueError('BASE_NOT_DETECTED_AS_KREA2')

    class HeaderKrea2(comfy.model_base.Krea2):
        def __init__(self):
            # Intentionally no Krea2 constructor or actual model layer allocation.
            torch.nn.Module.__init__(self)
            self.model_config = SimpleNamespace(unet_config=config)

        def state_dict(self):
            return {'diffusion_model.' + k: v for k, v in shapes.items()}

    return comfy.lora.model_lora_keys_unet(HeaderKrea2(), {}), config


def tensor_digest(tensor, torch):
    raw = tensor.detach().cpu().contiguous().reshape(-1).view(torch.uint8).numpy().tobytes()
    metadata = json.dumps({'dtype': str(tensor.dtype), 'shape': list(tensor.shape)}, sort_keys=True).encode()
    return hashlib.sha256(metadata + b'\n' + raw).hexdigest()


def fp8_lora_cases(module, dense, state, name, ratio, texts, torch):
    """Controlled hybrid oracle: pinned dense norm/correction + native base call.

    This does not execute an author's quantization stack or install a model hook.
    """
    from krea2_dora_numeric_probe import candidate_forward, make_module, upstream_class
    cls = upstream_class(texts, torch)
    stem = 'diffusion_model.' + name
    a, b, m = [state[stem + suffix] for suffix in
               ['.lora_A.weight', '.lora_B.weight', '.magnitude']]
    immutable = [a.clone(), b.clone(), m.clone(), dense.clone()]
    native_before = {key: tensor_digest(value, torch) for key, value in module.state_dict().items()}
    flags_before = {'full_precision_mm': module._full_precision_mm, 'quant_format': module.quant_format}
    rows = []
    for seed in [7, 7725]:
        for shape in [(2, dense.shape[1]), (1, 3, dense.shape[1])]:
            x = torch.randn(*shape, generator=torch.Generator().manual_seed(seed),
                            dtype=torch.bfloat16) * .1
            x_before = x.clone()
            for strength in [0., .5, 1.]:
                reference = make_module(cls, dense, a, b, m, None, strength, ratio, shape[0], torch)
                # Keep the source's dense norm weight but bind its original
                # forward to the real quantized op. The boundary is explicit.
                reference.org_forward = module.forward
                with torch.no_grad():
                    native = module(x)
                    repeated = module(x)
                    if not torch.isfinite(native).all() or not torch.equal(native, repeated):
                        raise ValueError('NATIVE_BASE_REPEATABILITY_NOT_VERIFIED')
                    expected = reference(x)
                    actual = candidate_forward(x, dense, a, b, m, None, strength=strength,
                        alpha_over_rank=ratio, torch=torch, base_forward=module.forward)
                    dense_candidate = candidate_forward(x, dense, a, b, m, None,
                        strength=strength, alpha_over_rank=ratio, torch=torch)
                    perturbed = candidate_forward(x, dense, a, b, m * .9, None,
                        strength=strength, alpha_over_rank=ratio, torch=torch, base_forward=module.forward)
                if not all(torch.isfinite(value).all() for value in [expected, actual, dense_candidate, perturbed]):
                    raise ValueError('NONFINITE_HYBRID_OUTPUT')
                if not torch.equal(x, x_before):
                    raise AssertionError('INPUT_MUTATED')
                exact = bool(torch.isfinite(expected).all() and torch.equal(actual, expected))
                sensitivity = (actual.float() - perturbed.float()).abs().max().item()
                if (strength == 0 and (not torch.equal(actual, native) or sensitivity != 0)):
                    raise AssertionError('ZERO_STRENGTH_NOT_NATIVE_NOOP')
                if strength > 0 and sensitivity == 0:
                    raise AssertionError('MAGNITUDE_SENSITIVITY_NOT_EXERCISED')
                rows.append({'seed': seed, 'input_shape': list(shape), 'strength': strength,
                    'alpha_over_rank': ratio, 'exact_hybrid_oracle_equal': exact,
                    'hybrid_oracle_max_abs_error': (actual.float() - expected.float()).abs().max().item(),
                    'dense_candidate_max_abs_error': (actual.float() - dense_candidate.float()).abs().max().item(),
                    'magnitude_perturbation_max_abs_error': sensitivity,
                    'native_noop_equal': torch.equal(actual, native) if strength == 0 else None})
    if not all(torch.equal(t, old) for t, old in zip([a, b, m, dense], immutable)):
        raise AssertionError('WEIGHT_TENSORS_MUTATED')
    native_after = {key: tensor_digest(value, torch) for key, value in module.state_dict().items()}
    if native_before != native_after:
        raise AssertionError('NATIVE_QUANTIZED_STATE_MUTATED')
    if flags_before != {'full_precision_mm': module._full_precision_mm, 'quant_format': module.quant_format}:
        raise AssertionError('NATIVE_QUANTIZATION_FLAGS_MUTATED')
    return {'status': 'ISOLATED_HYBRID_EXACT_PASS' if all(r['exact_hybrid_oracle_equal'] for r in rows)
                     else 'ISOLATED_HYBRID_MISMATCH',
            'oracle_scope': 'PINNED_METHODS_WITH_DENSE_NORM_AND_NATIVE_BASE_FORWARD',
            'authored_quantized_runtime': 'NOT_VERIFIED', 'alpha_hypothesis': ratio,
            'alpha_provenance': 'EXPLICIT_RESEARCH_HYPOTHESIS_NOT_AUTHORED_CONFIRMATION',
            'consumed_tensors': {stem + suffix: tensor_digest(t, torch) for suffix, t in
                zip(['.lora_A.weight', '.lora_B.weight', '.magnitude'], [a, b, m])},
            'native_state_sha256': native_before, 'native_flags': flags_before,
            'all_inputs_and_weights_unchanged': True,
            'production_compatibility': 'BLOCKED', 'cases': rows}


def assess_probe_device(torch, device):
    if device == 'cpu':
        return {'status': 'AVAILABLE', 'device': 'cpu'}
    if device != 'cuda':
        raise ValueError('PROBE_DEVICE_UNSUPPORTED')
    if not torch.cuda.is_available():
        return {'status': 'BLOCKED', 'device': 'cuda', 'reason': 'CUDA_UNAVAILABLE'}
    free, total = torch.cuda.mem_get_info(0)
    result = {'status': 'AVAILABLE', 'device': 'cuda:0', 'free_bytes': free, 'total_bytes': total,
              'minimum_free_bytes': 1024**3, 'name': torch.cuda.get_device_name(0),
              'capability': list(torch.cuda.get_device_capability(0)),
              'scope': 'SEPARATE_PROCESS_BOUNDED_BASE_PROJECTIONS_ONLY'}
    if free < result['minimum_free_bytes']:
        result.update(status='BLOCKED', reason='CUDA_FREE_MEMORY_BELOW_PROBE_FLOOR')
    return result


def cuda_forward_cases(module, dense, torch):
    rows = []
    for seed in [7, 7725]:
        for shape in [(2, dense.shape[1]), (1, 3, dense.shape[1])]:
            x = (torch.randn(*shape, generator=torch.Generator().manual_seed(seed),
                             dtype=torch.bfloat16) * .1).to('cuda:0')
            before = tensor_digest(x, torch)
            with torch.no_grad():
                actual, repeated = module(x), module(x)
                expected = torch.nn.functional.linear(x, dense)
            torch.cuda.synchronize(0)
            if (actual.device != x.device or actual.dtype != torch.bfloat16
                    or actual.shape != (*shape[:-1], dense.shape[0])
                    or not torch.isfinite(actual).all() or not torch.equal(actual, repeated)):
                raise ValueError('CUDA_NATIVE_OUTPUT_CONTRACT_OR_REPEATABILITY_FAILED')
            if before != tensor_digest(x, torch):
                raise ValueError('CUDA_PROBE_INPUT_MUTATED')
            rows.append({'seed': seed, 'input_shape': list(shape), 'device': str(actual.device),
                'native_repeatable': True, 'input_unchanged': True,
                'dense_reference_max_abs_error': (actual.float()-expected.float()).abs().max().item(),
                'dense_reference_exact_equal': torch.equal(actual, expected),
                'input_sha256': before, 'output_sha256': tensor_digest(actual, torch)})
    return rows


def isolated_fp8_layers(base_path, header, torch, *, lora_state=None, ratio=None, texts=None, device='cpu'):
    from safetensors import safe_open
    import comfy.ops
    import comfy.utils
    quant = json.loads(header['__metadata__']['_quantization_metadata'])['layers']
    rows = []
    for name in ['blocks.0.attn.wk', 'blocks.0.attn.gate']:
        row = {'layer': name, 'scope': 'ACTUAL_BASE_PROJECTION_CPU_ONLY' if device == 'cpu' else 'ACTUAL_BASE_PROJECTION_CUDA_ONLY',
               'lora_application': 'NOT_RUN', 'generation': 'NOT_RUN'}
        phase = 'LOAD'
        try:
            spec = header[name + '.weight']
            if name + '.bias' in header:
                raise ValueError('PROJECTION_BIAS_OUT_OF_PROBE_SCOPE')
            if spec['data_offsets'][1] - spec['data_offsets'][0] > 64 * 1024 * 1024:
                raise ValueError('PROJECTION_EXCEEDS_READ_LIMIT')
            with safe_open(str(base_path), framework='pt', device='cpu') as handle:
                state = {name + '.weight': handle.get_tensor(name + '.weight'),
                         name + '.weight_scale': handle.get_tensor(name + '.weight_scale')}
            row['quant_config'] = quant[name]
            row['actual_scale'] = state[name + '.weight_scale'].item()
            if not torch.isfinite(state[name + '.weight_scale']).all() or row['actual_scale'] <= 0:
                raise ValueError('INVALID_SCALE')
            state, _ = comfy.utils.convert_old_quants(state, metadata={
                '_quantization_metadata': json.dumps({'layers': {name: quant[name]}})})
            local = {k.removeprefix(name + '.'): v for k, v in state.items()}
            ops = comfy.ops.mixed_precision_ops(compute_dtype=torch.bfloat16)
            module = ops.Linear(spec['shape'][1], spec['shape'][0], bias=False, device=device)
            module.load_state_dict(local, strict=True)
            native_before = {key: tensor_digest(value, torch) for key, value in module.state_dict().items()}
            flags_before = {'full_precision_mm': module._full_precision_mm, 'quant_format': module.quant_format}
            row.update(load_status='PASS', weight_type=type(module.weight).__name__,
                       full_precision_mm=module._full_precision_mm)
            phase = 'DEQUANTIZE'
            dense = module.weight.dequantize().to(torch.bfloat16)
            row.update(dequantize_status='PASS', dense_dtype=str(dense.dtype),
                       dense_finite=bool(torch.isfinite(dense).all()))
            if not row['dense_finite']:
                raise ValueError('NONFINITE_DEQUANTIZED_WEIGHT')
            x = torch.randn(2, spec['shape'][1], generator=torch.Generator().manual_seed(7725),
                            dtype=torch.bfloat16) * .1
            x = x.to(device)
            phase = 'FORWARD'
            with torch.no_grad():
                expected = torch.nn.functional.linear(x, dense)
                actual = module(x)
            if not torch.isfinite(actual).all():
                raise ValueError('NONFINITE_NATIVE_FORWARD')
            row.update(forward_status='PASS', output_shape=list(actual.shape),
                       actual_device=str(actual.device),
                       dense_reference_max_abs_error=(actual.float() - expected.float()).abs().max().item(),
                       dense_reference_exact_equal=torch.equal(actual, expected))
            if device != 'cpu':
                row['cuda_cases'] = cuda_forward_cases(module, dense, torch)
                row['cuda_peak_allocated_bytes'] = torch.cuda.max_memory_allocated(0)
            if lora_state is not None:
                phase = 'LORA_HYPOTHESIS'
                row['lora_probe'] = fp8_lora_cases(module, dense, lora_state, name, ratio, texts, torch)
                row['lora_application'] = 'ISOLATED_RESEARCH_FORWARD_ONLY'
            if native_before != {key: tensor_digest(value, torch) for key, value in module.state_dict().items()}:
                raise ValueError('NATIVE_BASE_STATE_MUTATED')
            if flags_before != {'full_precision_mm': module._full_precision_mm, 'quant_format': module.quant_format}:
                raise ValueError('NATIVE_BASE_FLAGS_MUTATED')
            row['native_state_unchanged'] = True
        except Exception as exc:
            row.update(blocked_phase=phase, status='BLOCKED', error=type(exc).__name__ + ': ' + str(exc))
        else:
            row['status'] = 'BASE_LAYER_CPU_EXECUTED_NOT_LORA_COMPATIBILITY' if device == 'cpu' else 'BASE_LAYER_CUDA_EXECUTED_NOT_LORA_COMPATIBILITY'
        rows.append(row)
    return rows


def summarize(state, converted, patches, warnings):
    consumed = set()
    rows = []
    for target, adapter in sorted(patches.items()):
        if not hasattr(adapter, 'loaded_keys') or not hasattr(adapter, 'weights'):
            raise ValueError('Unexpected installed adapter contract')
        consumed.update(adapter.loaded_keys)
        up, down, alpha, mid, scale, reshape = adapter.weights
        rows.append({'target': target, 'adapter': type(adapter).__name__,
                     'up_shape': list(up.shape), 'down_shape': list(down.shape),
                     'alpha': alpha, 'dora_scale_present': scale is not None,
                     'mid_present': mid is not None, 'reshape_present': reshape is not None})
    # Log messages are the authoritative top-level loader observation; adapters'
    # loaded_keys alone would miss alpha/dora keys consumed by the outer loader.
    prefix = 'lora key not loaded: '
    unloaded = sorted(message[len(prefix):] for message in warnings
                      if message.startswith(prefix))
    expected_count = len(diagnostic_map(converted))
    return {'input_tensor_count': len(state), 'converted_tensor_count': len(converted),
            'converter_keys_unchanged': set(state) == set(converted),
            'patch_count': len(patches), 'adapter_consumed_keys': sorted(consumed),
            'unloaded_keys': unloaded, 'warnings': warnings, 'patches': rows,
            'status': ('INCOMPLETE_ADAPTER' if unloaded or len(patches) != expected_count
                       else 'PARSER_ONLY_PASS'),
            'base_model_mapping': 'NOT_VERIFIED', 'weight_application': 'NOT_RUN',
            'generation': 'NOT_RUN', 'quality_impact': 'NOT_MEASURED'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--comfy-root', type=Path, required=True)
    parser.add_argument('--lora', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--base', type=Path, help='Optional real base: hash + header/meta mapper, never full model load')
    parser.add_argument('--workflow', type=Path, help='Required with --base to bind current filenames')
    parser.add_argument('--probe-layers', action='store_true', help='Read and execute only two bounded base FP8 projections (default CPU)')
    parser.add_argument('--probe-device', choices=['cpu', 'cuda'], default='cpu',
                        help='Explicit isolated base-projection device; CUDA does not support the CPU-only LoRA hypothesis')
    parser.add_argument('--probe-lora', action='store_true', help='Explicit isolated hybrid LoRA hypothesis; never full model integration')
    parser.add_argument('--alpha-over-rank', type=float, help='Required explicit research hypothesis with --probe-lora')
    parser.add_argument('--source-dir', type=Path, help='Hash-pinned upstream sources required for hybrid oracle')
    args = parser.parse_args()
    root, lora = args.comfy_root.resolve(), args.lora.resolve()
    if args.output.exists() or args.output.resolve() == lora:
        parser.error('Output must be a new file')
    if bool(args.base) != bool(args.workflow) or (args.probe_layers and not args.base):
        parser.error('--base and --workflow must be paired; --probe-layers needs both')
    if args.probe_device != 'cpu' and (not args.probe_layers or args.probe_lora):
        parser.error('CUDA requires --probe-layers and cannot run the CPU-only --probe-lora hypothesis')
    if args.probe_lora:
        if not args.probe_layers or args.source_dir is None or args.alpha_over_rank is None:
            parser.error('--probe-lora requires --probe-layers, --source-dir and explicit --alpha-over-rank')
        if not math.isfinite(args.alpha_over_rank) or args.alpha_over_rank <= 0:
            parser.error('--alpha-over-rank must be finite and positive')
    elif args.alpha_over_rank is not None or args.source_dir is not None:
        parser.error('Research alpha/source arguments require --probe-lora')
    texts = None
    if args.probe_lora:
        from krea2_dora_numeric_probe import pinned_sources
        texts = pinned_sources(args.source_dir)
    relatives = ['comfy/lora.py', 'comfy/lora_convert.py',
                 'comfy/weight_adapter/lora.py', 'comfy/weight_adapter/base.py']
    if args.base:
        relatives += ['comfy/model_detection.py', 'comfy/model_base.py', 'comfy/utils.py',
                      'comfy/ops.py', 'comfy/model_patcher.py']
    before = {relative: sha(root / relative) for relative in relatives}
    weight_before = sha(lora)
    # ComfyUI consumes argv at import time. Do not leak this script's arguments.
    sys.argv = [sys.argv[0], '--cpu'] if args.probe_device == 'cpu' else [sys.argv[0], '--cuda-device', '0']
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(root))
    import torch
    device_report = assess_probe_device(torch, args.probe_device)
    if device_report['status'] != 'AVAILABLE':
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x', encoding='utf-8') as stream:
            json.dump({'status': 'BLOCKED', 'device_preflight': device_report,
                'generation': 'NOT_RUN', 'weight_application': 'NOT_RUN',
                'production_compatibility': 'BLOCKED'}, stream, indent=2)
        raise SystemExit(2)
    from safetensors import safe_open
    from safetensors.torch import load_file
    loader = importlib.import_module('comfy.lora')
    converter = importlib.import_module('comfy.lora_convert')
    for module, relative in [(loader, 'comfy/lora.py'), (converter, 'comfy/lora_convert.py')]:
        if Path(module.__file__).resolve() != (root / relative).resolve():
            raise ValueError('Imported a different ComfyUI installation')
    state = load_file(str(lora), device='cpu')
    with safe_open(str(lora), framework='pt', device='cpu') as handle:
        metadata = handle.metadata()
    converted = converter.convert_lora(state)
    base_report = None
    if args.base:
        workflow_hash = sha(args.workflow)
        workflow = json.loads(args.workflow.read_text(encoding='utf-8'))
        if (workflow['10']['inputs']['unet_name'] != args.base.name
                or workflow['15']['inputs']['lora_name'] != lora.name):
            raise ValueError('WORKFLOW_WEIGHT_NAME_MISMATCH')
        base_hash = sha(args.base)
        base_header, lora_header = read_header(args.base), read_header(lora)
        key_map, config = base_mapping(base_header, torch)
        base_report = assess_base_contract(base_header, lora_header, key_map)
        base_report.update(path=str(args.base.resolve()), sha256=base_hash, detected_config=config,
                           workflow_sha256=workflow_hash, workflow_path=str(args.workflow.resolve()))
        if base_report['shape_matches'] != base_report['targets'] or base_report['quant_header_matches'] != base_report['targets']:
            raise ValueError('BASE_SHAPE_OR_QUANT_CONTRACT_MISMATCH')
        if args.probe_layers:
            base_report['isolated_layers'] = isolated_fp8_layers(args.base, base_header, torch,
                lora_state=state if args.probe_lora else None, ratio=args.alpha_over_rank, texts=texts,
                device='cpu' if args.probe_device == 'cpu' else 'cuda:0')
        if base_hash != sha(args.base) or workflow_hash != sha(args.workflow):
            raise ValueError('BASE_OR_WORKFLOW_CHANGED')
    else:
        key_map = diagnostic_map(converted)
    messages = []

    class Capture(logging.Handler):
        def emit(self, record):
            messages.append(record.getMessage())

    capture = Capture(level=logging.WARNING)
    logger = logging.getLogger()
    logger.addHandler(capture)
    try:
        patches = loader.load_lora(converted, key_map, log_missing=True)
    finally:
        logger.removeHandler(capture)
    result = summarize(state, converted, patches, messages)
    if base_report is not None:
        result['base_contract'] = base_report
    result.update(collected_at=datetime.now(timezone.utc).isoformat(),
                  python=sys.version, torch_version=torch.__version__, device=args.probe_device,
                  device_preflight=device_report,
                  probe_sha256=sha(Path(__file__)),
                  lora={'path': str(lora), 'sha256': weight_before, 'metadata': metadata},
                  loader_sources=before,
                  key_map=('INSTALLED_MAPPER_ON_HEADER_ONLY_KREA2_SKELETON' if args.base
                           else 'DIAGNOSTIC_IDENTITY_FROM_FILE_STEMS_NOT_BASE_MODEL'))
    if args.probe_lora:
        from krea2_dora_numeric_probe import pinned_sources, SOURCE_COMMIT, SOURCE_HASHES
        if pinned_sources(args.source_dir) != texts:
            raise ValueError('UPSTREAM_SOURCE_CHANGED')
        result['lora_hypothesis'] = {'alpha_over_rank': args.alpha_over_rank,
            'source_commit': SOURCE_COMMIT, 'source_hashes': SOURCE_HASHES,
            'numeric_probe_sha256': sha(Path(__file__).with_name('krea2_dora_numeric_probe.py')),
            'production_compatibility': 'BLOCKED'}
    if weight_before != sha(lora) or before != {r: sha(root / r) for r in relatives}:
        raise ValueError('Inputs changed during probe')
    result['inputs_unchanged'] = True
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({k: result[k] for k in ['status', 'patch_count', 'generation']}))
    if args.probe_lora and any(row.get('lora_probe', {}).get('status') != 'ISOLATED_HYBRID_EXACT_PASS'
                              for row in base_report['isolated_layers']):
        raise SystemExit(2)
    if args.probe_device == 'cuda' and any(row.get('status') == 'BLOCKED' for row in base_report['isolated_layers']):
        raise SystemExit(2)


if __name__ == '__main__':
    main()
