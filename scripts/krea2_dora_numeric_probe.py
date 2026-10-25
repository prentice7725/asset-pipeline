"""Isolated dense CPU comparison against pinned ai-toolkit 0.12.9 methods.

This is an unregistered research candidate, not a ComfyUI patch or checkpoint
converter. No model files, servers, custom nodes or generation are used.
Select --candidate ordered for an execution-order-preserving forward; the
default merged candidate deliberately retains its measured BF16 failure.
Upstream methods are compiled unchanged from hash-pinned local source files;
the complete ai-toolkit dependency/runtime environment is NOT executed.
"""
# candidate_forward adapts ai-toolkit inference ordering, Copyright (c) 2024
# Ostris, LLC, MIT; notice retained in licenses/ai-toolkit-MIT.txt.
import argparse
import ast
import hashlib
import json
import math
import sys
import weakref
from datetime import datetime, timezone
from pathlib import Path

SOURCE_COMMIT = '6d8afa5684000b69db97cc40504a972a85615e3b'
SOURCE_HASHES = {
    'version.py': '5048231d23b7f18ed374381b77430be0f301ac7f342de34f305bc8c2e984ba6b',
    'DoRA.py': '0b7a66971db200d0389a2d0b73ba8f242dc0d576db262511b4278ee7efe03ae9',
    'network_mixins.py': '0c1b621503231a9a7f165f7631ff34f7a888857a6ea0969190d6c05ae50f3e8f',
    'LICENSE': 'e73058fe55271c3bb4f991e695110525c9597f254360413968e01c95b0180f51',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pinned_sources(directory):
    texts = {}
    for name, expected in SOURCE_HASHES.items():
        path = directory / name
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError('SOURCE_HASH_MISMATCH: ' + name)
        texts[name] = data.decode('utf-8')
    return texts


def source_functions(text, filename, class_name, names, namespace):
    tree = ast.parse(text, filename)
    scope = tree.body if class_name is None else next(
        node.body for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)
    functions = [node for node in scope if isinstance(node, ast.FunctionDef) and node.name in names]
    if {node.name for node in functions} != set(names):
        raise ValueError('UPSTREAM_METHOD_CONTRACT_CHANGED')
    # No imports or unrelated statements are executed. Bodies remain unchanged.
    exec(compile(ast.Module(body=functions, type_ignores=[]), filename, 'exec'), namespace)
    return {node.name: namespace[node.name] for node in functions}


def upstream_class(texts, torch):
    # Markers only satisfy inactive dense-only isinstance checks. Quantized
    # modules/inputs are excluded, not simulated as upstream quanto execution.
    class ExcludedQuantizedType:
        pass

    namespace = {'torch': torch, 'nn': torch.nn, 'F': torch.nn.functional,
                 'Module': object, 'Network': object,
                 'QTensor': ExcludedQuantizedType, 'QBytesTensor': ExcludedQuantizedType}
    source_functions(texts['network_mixins.py'], 'pinned/network_mixins.py', None,
                     ['broadcast_and_multiply'], namespace)
    methods = source_functions(texts['network_mixins.py'], 'pinned/network_mixins.py',
                               'ToolkitModuleMixin', ['forward', '_call_forward'], namespace)
    source_functions(texts['DoRA.py'], 'pinned/DoRA.py', None, ['transpose'], namespace)
    methods.update(source_functions(texts['DoRA.py'], 'pinned/DoRA.py', 'DoRAModule',
                                    ['get_orig_weight', 'get_orig_bias', '_get_weight_norm',
                                     'apply_dora'], namespace))
    return type('DoRAModule', (torch.nn.Module,), methods)


def validate_dense(weight, down, up, magnitude, *, strength, alpha_over_rank, torch):
    tensors = [weight, down, up, magnitude]
    allowed = {torch.float64, torch.float32, torch.bfloat16}
    if any(t.is_quantized or t.dtype not in allowed for t in tensors):
        raise ValueError('QUANTIZED_OR_UNSUPPORTED_DTYPE')
    if len({t.dtype for t in tensors}) != 1 or any(t.device.type != 'cpu' for t in tensors):
        raise ValueError('UNIFORM_CPU_DTYPE_REQUIRED')
    if not math.isfinite(strength) or not 0 <= strength <= 1:
        raise ValueError('STRENGTH_OUT_OF_SCOPE')
    if not math.isfinite(alpha_over_rank) or alpha_over_rank <= 0:
        raise ValueError('EXPLICIT_POSITIVE_ALPHA_RATIO_REQUIRED')
    if (weight.ndim != 2 or down.ndim != 2 or up.ndim != 2 or magnitude.ndim != 1
            or down.shape[1] != weight.shape[1] or up.shape[0] != weight.shape[0]
            or up.shape[1] != down.shape[0] or magnitude.shape[0] != weight.shape[0]):
        raise ValueError('DENSE_OUTPUT_AXIS_SHAPES_REQUIRED')
    if not all(torch.isfinite(t).all().item() for t in tensors):
        raise ValueError('NONFINITE_INPUT')


def candidate_weight(weight, down, up, magnitude, *, strength, alpha_over_rank, torch):
    """Unregistered merged candidate; BF16 equivalence is known to fail."""
    validate_dense(weight, down, up, magnitude, strength=strength,
                   alpha_over_rank=alpha_over_rank, torch=torch)
    if strength == 0:
        return weight.clone()
    delta = up @ down
    adapted = weight + strength * delta
    norm = torch.linalg.vector_norm(adapted, dim=1)
    if not torch.isfinite(norm).all().item() or (norm == 0).any().item():
        raise ValueError('ZERO_OR_NONFINITE_ADAPTED_NORM')
    return adapted * (magnitude / norm)[:, None] + strength * (alpha_over_rank - 1) * delta


def candidate_forward(x, weight, down, up, magnitude, bias, *, strength, alpha_over_rank, torch,
                      base_forward=None):
    """Unregistered dense inference candidate preserving pinned source ordering.

    Keep the two low-rank linears, dtype-rounded runtime scale and multiplier,
    mean multiplier in the norm branch, correction and final additions separate.
    This is restricted to uniform CPU dtype and one uniform inference strength.
    It does not install a hook, merge weights, or infer the actual file's alpha.
    """
    validate_dense(weight, down, up, magnitude, strength=strength,
                   alpha_over_rank=alpha_over_rank, torch=torch)
    if (x.is_quantized or x.dtype != weight.dtype or x.device.type != 'cpu'
            or x.ndim not in (2, 3) or x.shape[-1] != weight.shape[1]
            or any(size == 0 for size in x.shape)):
        raise ValueError('DENSE_MATCHING_INPUT_REQUIRED')
    if bias is not None and (bias.is_quantized or bias.dtype != weight.dtype
            or bias.device.type != 'cpu' or bias.shape != (weight.shape[0],)):
        raise ValueError('MATCHING_BIAS_REQUIRED')
    if not torch.isfinite(x).all().item() or (bias is not None and not torch.isfinite(bias).all().item()):
        raise ValueError('NONFINITE_INPUT')
    if base_forward is not None and not callable(base_forward):
        raise ValueError('EXPLICIT_BASE_FORWARD_CALLABLE_REQUIRED')
    original = (torch.nn.functional.linear(x, weight, bias) if base_forward is None
                else base_forward(x))
    if (original.dtype != x.dtype or original.device != x.device
            or original.shape != (*x.shape[:-1], weight.shape[0])
            or not torch.isfinite(original).all().item()):
        raise ValueError('BASE_FORWARD_OUTPUT_CONTRACT_MISMATCH')
    if strength == 0:
        return original
    runtime_scale = torch.tensor(alpha_over_rank, dtype=down.dtype)
    multiplier = torch.full((x.shape[0],), strength, dtype=down.dtype)
    low_rank = torch.nn.functional.linear(torch.nn.functional.linear(x.to(down.dtype), down), up)
    low_rank = low_rank * runtime_scale
    scaled = (low_rank * multiplier.reshape(x.shape[0], *([1] * (x.ndim - 1)))).to(original.dtype)
    scaled_delta = (up @ down) * multiplier.mean()
    norm = torch.linalg.norm(weight + scaled_delta.to(weight.device), dim=1).detach()
    if not torch.isfinite(norm).all().item() or (norm == 0).any().item():
        raise ValueError('ZERO_OR_NONFINITE_ADAPTED_NORM')
    adapted = weight + scaled_delta
    correction = (magnitude / norm - 1).view(1, -1) * torch.nn.functional.linear(x.to(adapted.dtype), adapted)
    scaled = scaled + correction.to(original.dtype)
    return original + scaled


def make_module(cls, weight, down, up, magnitude, bias, strength, ratio, batch, torch):
    module = cls()
    base = torch.nn.Linear(weight.shape[1], weight.shape[0], bias=bias is not None,
                           dtype=weight.dtype)
    base.weight.data.copy_(weight)
    if bias is not None:
        base.bias.data.copy_(bias)
    module.org_module = [base]
    module.org_forward = base.forward
    module.lora_down = torch.nn.Linear(down.shape[1], down.shape[0], bias=False, dtype=weight.dtype)
    module.lora_up = torch.nn.Linear(up.shape[1], up.shape[0], bias=False, dtype=weight.dtype)
    module.lora_down.weight.data.copy_(down)
    module.lora_up.weight.data.copy_(up)
    module.magnitude = torch.nn.Parameter(magnitude.clone())
    module.register_buffer('_runtime_scale', torch.tensor(ratio, dtype=weight.dtype))
    module.dropout = module.rank_dropout = module.module_dropout = None
    module.lora_dim = down.shape[0]

    class Network:
        is_lorm = False
        is_active = True
        is_merged_in = False

    network = Network()
    network._multiplier = strength
    network.torch_multiplier = torch.full((batch,), strength, dtype=weight.dtype)
    module._network_keepalive = network
    module.network_ref = weakref.ref(network)
    return module.eval()


def compare_matrix(texts, torch, weight_decompose, candidate='merged'):
    cls = upstream_class(texts, torch)
    rows = []
    for dtype in [torch.float64, torch.float32, torch.bfloat16]:
        # The same FP64-generated fixture values are cast into each dtype.
        generator = torch.Generator().manual_seed(7725)
        shapes = [(5, 3, 2), (3, 5, 2), (4, 4, 2)]
        if candidate == 'ordered':
            shapes += [(7, 3, 1), (3, 7, 3)]
        for out_dim, in_dim, rank in shapes:
            w = torch.randn(out_dim, in_dim, generator=generator, dtype=torch.float64).to(dtype)
            a = (torch.randn(rank, in_dim, generator=generator, dtype=torch.float64) * .15).to(dtype)
            b = (torch.randn(out_dim, rank, generator=generator, dtype=torch.float64) * .15).to(dtype)
            m = (torch.linalg.vector_norm(w.double(), dim=1) * 1.2).to(dtype)
            for with_bias in [False, True]:
                bias = torch.randn(out_dim, generator=generator, dtype=torch.float64).to(dtype) if with_bias else None
                for input_dims in [(7, in_dim), (2, 4, in_dim)]:
                    x = torch.randn(*input_dims, generator=generator, dtype=torch.float64).to(dtype)
                    for ratio in ([.25, .5, 1., 2.] if candidate == 'ordered' else [1., .5]):
                        for strength in ([0., .1, .5, 1.] if candidate == 'ordered' else [0., .5, 1.]):
                            module = make_module(cls, w, a, b, m, bias, strength, ratio, x.shape[0], torch)
                            inputs = [x, w, a, b, m] + ([bias] if bias is not None else [])
                            before = [value.clone() for value in inputs]
                            with torch.no_grad():
                                expected = module(x)
                                if candidate == 'ordered':
                                    actual = candidate_forward(x, w, a, b, m, bias, strength=strength,
                                                               alpha_over_rank=ratio, torch=torch)
                                    merged_weight = candidate_weight(w, a, b, m, strength=strength,
                                                                     alpha_over_rank=ratio, torch=torch)
                                    merged_output = torch.nn.functional.linear(x, merged_weight, bias)
                                else:
                                    merged = candidate_weight(w, a, b, m, strength=strength,
                                                              alpha_over_rank=ratio, torch=torch)
                                    actual = torch.nn.functional.linear(x, merged, bias)
                                # Counterexample: even with an output-axis reshape,
                                # the installed DoRA branch is not this source's math.
                                alias = weight_decompose(m[:, None], w.clone(), b @ a,
                                                         ratio, strength, dtype, lambda t: t)
                                alias_output = torch.nn.functional.linear(x, alias, bias)
                            if not all(torch.equal(value, original) for value, original in zip(inputs, before)):
                                raise AssertionError('SYNTHETIC_INPUT_MUTATED')
                            atol = rtol = 1e-10 if dtype == torch.float64 else 1e-5
                            finite = torch.isfinite(expected).all() and torch.isfinite(actual).all()
                            rows.append({'dtype': str(dtype), 'shape': [out_dim, in_dim, rank],
                                'bias': with_bias, 'input_shape': list(input_dims),
                                'alpha_over_rank': ratio, 'strength': strength,
                                'max_abs_error': (actual.double() - expected.double()).abs().max().item(),
                                'exact_output_equal': bool(finite and torch.equal(actual, expected)),
                                'within_tolerance': bool(finite and torch.allclose(actual, expected, atol=atol, rtol=rtol)),
                                'atol': atol, 'rtol': rtol,
                                'renamed_reshaped_installed_max_abs_error':
                                    (alias_output.double() - expected.double()).abs().max().item()})
                            if candidate == 'ordered':
                                rows[-1]['merged_max_abs_error'] = (merged_output.double() - expected.double()).abs().max().item()
    return rows


def rejection_checks(torch, candidate='merged'):
    w = torch.eye(3)
    a = torch.ones(2, 3)
    b = torch.ones(3, 2)
    m = torch.ones(3)
    defaults = dict(weight=w, down=a, up=b, magnitude=m, strength=.5,
                    alpha_over_rank=1., torch=torch)
    cases = [
        ('float8_base', {'weight': w.to(torch.float8_e4m3fn)}, 'QUANTIZED_OR_UNSUPPORTED_DTYPE'),
        ('integer_base', {'weight': w.to(torch.int8)}, 'QUANTIZED_OR_UNSUPPORTED_DTYPE'),
        ('mixed_dtype', {'down': a.double()}, 'UNIFORM_CPU_DTYPE_REQUIRED'),
        ('wrong_axis', {'magnitude': torch.ones(3, 1)}, 'DENSE_OUTPUT_AXIS_SHAPES_REQUIRED'),
        ('invalid_strength', {'strength': 1.5}, 'STRENGTH_OUT_OF_SCOPE'),
        ('unknown_alpha', {'alpha_over_rank': float('nan')}, 'EXPLICIT_POSITIVE_ALPHA_RATIO_REQUIRED'),
        ('nonfinite', {'magnitude': torch.full((3,), float('inf'))}, 'NONFINITE_INPUT'),
        ('zero_norm', {'weight': torch.zeros_like(w), 'down': torch.zeros_like(a)},
         'ZERO_OR_NONFINITE_ADAPTED_NORM'),
    ]
    rows = []
    for name, overrides, expected in cases:
        try:
            if candidate == 'ordered':
                candidate_forward(torch.ones(2, 3), bias=None, **(defaults | overrides))
            else:
                candidate_weight(**(defaults | overrides))
        except ValueError as exc:
            if str(exc) != expected:
                raise AssertionError((name, str(exc), expected)) from exc
            rows.append({'case': name, 'status': 'REJECTED_AS_REQUIRED', 'reason': expected})
        else:
            raise AssertionError('Unsupported case accepted: ' + name)
    if candidate == 'ordered':
        for name, x, bias, reason in [
            ('mixed_input', torch.ones(2, 3, dtype=torch.float64), None, 'DENSE_MATCHING_INPUT_REQUIRED'),
            ('empty_input', torch.ones(0, 3), None, 'DENSE_MATCHING_INPUT_REQUIRED'),
            ('wrong_bias', torch.ones(2, 3), torch.ones(1), 'MATCHING_BIAS_REQUIRED'),
            ('nonfinite_input', torch.full((2, 3), float('nan')), None, 'NONFINITE_INPUT'),
        ]:
            try:
                candidate_forward(x, bias=bias, **defaults)
            except ValueError as exc:
                if str(exc) != reason:
                    raise AssertionError((name, str(exc), reason)) from exc
                rows.append({'case': name, 'status': 'REJECTED_AS_REQUIRED', 'reason': reason})
            else:
                raise AssertionError('Unsupported case accepted: ' + name)
        for name, callback, reason in [
            ('noncallable_base', 'invalid', 'EXPLICIT_BASE_FORWARD_CALLABLE_REQUIRED'),
            ('wrong_base_shape', lambda x: x[:, :1], 'BASE_FORWARD_OUTPUT_CONTRACT_MISMATCH'),
            ('wrong_base_dtype', lambda x: x.double(), 'BASE_FORWARD_OUTPUT_CONTRACT_MISMATCH'),
            ('nonfinite_base', lambda x: torch.full_like(x, float('nan')), 'BASE_FORWARD_OUTPUT_CONTRACT_MISMATCH'),
        ]:
            try:
                candidate_forward(torch.ones(2, 3), bias=None, base_forward=callback, **defaults)
            except ValueError as exc:
                if str(exc) != reason:
                    raise AssertionError((name, str(exc), reason)) from exc
                rows.append({'case': name, 'status': 'REJECTED_AS_REQUIRED', 'reason': reason})
            else:
                raise AssertionError('Unsupported callback accepted: ' + name)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir', type=Path, required=True)
    parser.add_argument('--comfy-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--candidate', choices=['merged', 'ordered'], default='merged')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output must be a new file')
    texts = pinned_sources(args.source_dir)
    root = args.comfy_root.resolve()
    base = root / 'comfy/weight_adapter/base.py'
    loader_hash = sha(base)
    if loader_hash != '484f0d83a96e700f80c793e4bcc6a897d633233e51a59191d91da5e59da345c7':
        raise ValueError('INSTALLED_LOADER_CHANGED_REAUDIT_REQUIRED')
    sys.argv = [sys.argv[0], '--cpu']
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(root))
    import torch
    from comfy.weight_adapter.base import weight_decompose
    if Path(sys.modules[weight_decompose.__module__].__file__).resolve() != base:
        raise ValueError('DIFFERENT_COMFY_INSTALLATION_IMPORTED')
    rows = compare_matrix(texts, torch, weight_decompose, args.candidate)
    rejections = rejection_checks(torch, args.candidate)
    summary = {}
    for dtype in ['torch.float64', 'torch.float32', 'torch.bfloat16']:
        subset = [row for row in rows if row['dtype'] == dtype]
        summary[dtype] = {'cases': len(subset), 'passed': sum(r['within_tolerance'] for r in subset),
                          'exact_output_equal': sum(r['exact_output_equal'] for r in subset),
                          'max_abs_error': max(r['max_abs_error'] for r in subset)}
    if pinned_sources(args.source_dir) != texts or sha(base) != loader_hash:
        raise ValueError('INPUT_CHANGED_DURING_PROBE')
    dense_pass = all(r['within_tolerance'] for r in rows if r['dtype'] != 'torch.bfloat16')
    exact_pass = all(r['exact_output_equal'] for r in rows)
    if args.candidate == 'ordered' and not any(
            r['merged_max_abs_error'] > 0 for r in rows if r['dtype'] == 'torch.bfloat16'):
        raise AssertionError('BF16_MERGE_COUNTEREXAMPLE_NOT_EXERCISED')
    result = {'collected_at': datetime.now(timezone.utc).isoformat(), 'candidate': args.candidate,
        'status': ('FP32_FP64_PASS_BF16_MISMATCH' if dense_pass and
                   summary['torch.bfloat16']['passed'] != summary['torch.bfloat16']['cases']
                   else 'DENSE_SOURCE_CANDIDATE_PASS' if dense_pass else 'NUMERIC_MISMATCH'),
        'source_commit': SOURCE_COMMIT, 'source_version': '0.12.9', 'source_hashes': SOURCE_HASHES,
        'training_commit_match': 'NOT_VERIFIED', 'upstream_scope': 'HASH_PINNED_EXTRACTED_DENSE_METHODS',
        'full_upstream_runtime': 'NOT_RUN', 'quantized_base': 'BLOCKED_UNSUPPORTED',
        'actual_model_weights': 'NOT_LOADED', 'generation': 'NOT_RUN', 'quality_impact': 'NOT_MEASURED',
        'production_compatibility': 'BLOCKED', 'inputs_unchanged': True,
        'installed_weight_decompose_sha256': loader_hash, 'probe_sha256': sha(Path(__file__)),
        'python': sys.version, 'torch_version': torch.__version__, 'device': 'cpu',
        'summary': summary, 'cases': rows, 'rejection_checks': rejections}
    if args.candidate == 'ordered':
        result['status'] = 'ORDERED_DENSE_EXACT_PASS' if exact_pass else 'ORDERED_DENSE_MISMATCH'
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'status': result['status'], 'summary': summary}))
    if args.candidate == 'ordered' and not exact_pass:
        raise SystemExit(2)
    if not dense_pass:
        raise SystemExit(1)
    if not all(r['within_tolerance'] for r in rows):
        # A successful diagnostic must not look like full adapter compatibility
        # to a caller that checks only the process exit code.
        raise SystemExit(2)


if __name__ == '__main__':
    main()
