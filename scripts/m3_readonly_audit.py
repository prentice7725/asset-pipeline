"""Read-only local evidence collection. No model imports, installs or generation."""
import argparse
import hashlib
import json
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--comfy-root', required=True, type=Path)
    parser.add_argument('--lora', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    report = {'collected_at': datetime.now(timezone.utc).isoformat(),
              'generation': 'NOT_RUN', 'loader_execution': 'NOT_RUN',
              'quality_impact': 'NOT_MEASURED', 'reference_consumption': 'NOT_VERIFIED',
              'python': sys.version}
    with args.lora.open('rb') as stream:
        length = struct.unpack('<Q', stream.read(8))[0]
        if length > 16_000_000:
            raise ValueError('Unexpected safetensors header size')
        header = json.loads(stream.read(length))
    keys = [key for key in header if key != '__metadata__']
    report['lora'] = {'path': str(args.lora.resolve()), 'sha256': sha(args.lora),
                      'tensor_count': len(keys),
                      'magnitude_keys': sum(key.endswith('.magnitude') for key in keys),
                      'dora_scale_keys': sum(key.endswith('.dora_scale') for key in keys),
                      'ab_keys': sum('.lora_A' in key or '.lora_B' in key for key in keys)}
    report['loader_sources'] = []
    for relative in ['comfy/lora.py', 'comfy/weight_adapter/lora.py']:
        path = args.comfy_root / relative
        text = path.read_text(encoding='utf-8')
        report['loader_sources'].append({'path': str(path.resolve()), 'sha256': sha(path),
                                         'magnitude_literal_present': '.magnitude' in text,
                                         'dora_scale_literal_present': '.dora_scale' in text})
    try:
        with urlopen('http://127.0.0.1:8188/system_stats', timeout=3) as response:
            stats = json.load(response)
        with urlopen('http://127.0.0.1:8188/object_info', timeout=3) as response:
            nodes = json.load(response)
        names = ['DenoMiniMaxH3ReferenceImageLoader', 'DenoMiniMaxH3ReferenceToVideo',
                 'VHS_VideoCombine', 'LoraLoaderModelOnly']
        report['comfyui'] = {'status': 'READ_ONLY_INVENTORY', 'system': stats.get('system'),
                             'nodes': {name: nodes.get(name) for name in names},
                             'note': 'Node presence/schema is not execution or count/role verification'}
    except Exception as exc:
        report['comfyui'] = {'status': 'BLOCKED_INVENTORY_UNAVAILABLE', 'error': str(exc)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(args.output)


if __name__ == '__main__':
    main()
