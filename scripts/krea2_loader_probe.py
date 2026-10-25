"""CPU-only installed ComfyUI adapter parser probe; never generates or rewrites weights.

Run with the installed ComfyUI Python, not the assetpipe environment. A diagnostic
identity key map isolates file-format parsing; it does not verify base-model mapping.
"""
import argparse
import hashlib
import importlib
import json
import logging
import sys
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
    args = parser.parse_args()
    root, lora = args.comfy_root.resolve(), args.lora.resolve()
    if args.output.exists() or args.output.resolve() == lora:
        parser.error('Output must be a new file')
    relatives = ['comfy/lora.py', 'comfy/lora_convert.py',
                 'comfy/weight_adapter/lora.py', 'comfy/weight_adapter/base.py']
    before = {relative: sha(root / relative) for relative in relatives}
    weight_before = sha(lora)
    # ComfyUI consumes argv at import time. Do not leak this script's arguments.
    sys.argv = [sys.argv[0], '--cpu']
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(root))
    import torch
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
    messages = []

    class Capture(logging.Handler):
        def emit(self, record):
            messages.append(record.getMessage())

    capture = Capture(level=logging.WARNING)
    logger = logging.getLogger()
    logger.addHandler(capture)
    try:
        patches = loader.load_lora(converted, diagnostic_map(converted), log_missing=True)
    finally:
        logger.removeHandler(capture)
    result = summarize(state, converted, patches, messages)
    result.update(collected_at=datetime.now(timezone.utc).isoformat(),
                  python=sys.version, torch_version=torch.__version__, device='cpu',
                  probe_sha256=sha(Path(__file__)),
                  lora={'path': str(lora), 'sha256': weight_before, 'metadata': metadata},
                  loader_sources=before,
                  key_map='DIAGNOSTIC_IDENTITY_FROM_FILE_STEMS_NOT_BASE_MODEL')
    if weight_before != sha(lora) or before != {r: sha(root / r) for r in relatives}:
        raise ValueError('Inputs changed during probe')
    result['inputs_unchanged'] = True
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({k: result[k] for k in ['status', 'patch_count', 'generation']}))


if __name__ == '__main__':
    main()
