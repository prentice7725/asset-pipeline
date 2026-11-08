"""Numeric check: assetpipe ai-toolkit DoRA node merge vs the verified ordered candidate forward.

Run with the ComfyUI Python (torch required):
    <ComfyUI>/.venv/Scripts/python.exe scripts/krea2_dora_node_check.py --output <new.json>

`candidate_forward` (scripts/krea2_dora_numeric_probe.py) was previously shown exactly equal to the
pinned ai-toolkit 0.12.9 forward. Here the node's merged weight is used as a plain linear layer and
compared against that candidate on synthetic tensors. FP32/FP64 only: ComfyUI computes LoRA merges in
float32 (lora_compute_dtype); BF16 merging is known to differ and is not claimed.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))

import torch  # noqa: E402

from integrations.comfyui_dora import aitoolkit_dora_weight  # noqa: E402
from krea2_dora_numeric_probe import candidate_forward  # noqa: E402

TOLERANCE = {torch.float64: 1e-10, torch.float32: 1e-5}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f'refusing to overwrite {args.output}')
    rows = []
    for dtype in (torch.float64, torch.float32):
        for out_f, in_f, rank in ((5, 3, 2), (3, 5, 2), (4, 4, 2), (64, 48, 8), (1536, 512, 32)):
            for strength in (0.0, 0.5, 1.0):
                for ratio in (1.0, 0.5):
                    for batch_shape in ((2,), (2, 3)):
                        gen = torch.Generator().manual_seed(7725 + out_f + in_f + rank)
                        weight = torch.randn(out_f, in_f, generator=gen, dtype=torch.float64).to(dtype)
                        down = (torch.randn(rank, in_f, generator=gen, dtype=torch.float64) * 0.1).to(dtype)
                        up = (torch.randn(out_f, rank, generator=gen, dtype=torch.float64) * 0.1).to(dtype)
                        magnitude = (torch.linalg.vector_norm(weight.double(), dim=1)
                                     * (1 + 0.1 * torch.randn(out_f, generator=gen, dtype=torch.float64))).to(dtype)
                        x = torch.randn(*batch_shape, in_f, generator=gen, dtype=torch.float64).to(dtype)
                        reference = candidate_forward(x, weight, down, up, magnitude, None, strength=strength,
                                                      alpha_over_rank=ratio, torch=torch)
                        merged = aitoolkit_dora_weight(weight, down, up, magnitude, strength=strength,
                                                       alpha_over_rank=ratio)
                        node = torch.nn.functional.linear(x, merged)
                        diff = (node - reference).abs().max().item()
                        tol = TOLERANCE[dtype]
                        ok = torch.allclose(node, reference, atol=tol, rtol=tol)
                        rows.append({'dtype': str(dtype).split('.')[-1], 'shape': [out_f, in_f, rank],
                                     'strength': strength, 'alpha_over_rank': ratio, 'batch': list(batch_shape),
                                     'max_abs_diff': diff, 'max_abs_reference': reference.abs().max().item(),
                                     'relative_to_output_scale': diff / max(reference.abs().max().item(), 1e-30),
                                     'within_tolerance': bool(ok)})
    summary = {}
    for row in rows:
        key = f"{row['dtype']}"
        s = summary.setdefault(key, {'cases': 0, 'within_tolerance': 0, 'max_abs_diff': 0.0, 'max_relative_to_output_scale': 0.0})
        s['max_relative_to_output_scale'] = max(s['max_relative_to_output_scale'], row['relative_to_output_scale'])
        s['cases'] += 1
        s['within_tolerance'] += row['within_tolerance']
        s['max_abs_diff'] = max(s['max_abs_diff'], row['max_abs_diff'])
    result = {'kind': 'KREA2_DORA_NODE_NUMERIC_CHECK', 'created_at': datetime.now(timezone.utc).isoformat(),
              'torch': torch.__version__, 'reference': 'scripts/krea2_dora_numeric_probe.py candidate_forward',
              'tolerance': {'float64': 1e-10, 'float32': 1e-5}, 'summary': summary,
              'status': 'PASS' if all(r['within_tolerance'] for r in rows) else 'FAIL', 'rows': rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=1)
    print(json.dumps({'status': result['status'], 'summary': summary}, indent=1))


if __name__ == '__main__':
    main()
