# Krea2 BF16 execution-order candidate — 2026-10-25

Branch `codex/krea2-dora-ordered-20261025`, based on `3205c46`.
The user requested the next offline step after the
[BF16 merge mismatch](KREA2_DORA_NUMERIC_20261025.md). No generation budget is used.

## Result

**ORDERED_DENSE_EXACT_PASS**, restricted to synthetic dense CPU inference.
The ordered candidate and pinned upstream method outputs are exactly equal
according to `torch.equal` at each tested dtype, without widening tolerances.

| Dtype | Exact outputs / cases | Maximum absolute difference |
| --- | --- | --- |
| FP64 | 320 / 320 | 0 |
| FP32 | 320 / 320 | 0 |
| BF16 | 320 / 320 | 0 |

Twelve unsupported-input checks also reject as required. The same enlarged
matrix retains the old merged candidate as a counterexample: all **240 nonzero
BF16 merge cases** differ, maximum absolute output error **0.125**. This matrix
has more shapes/strengths than the earlier 216-case experiment; these numbers
are not an image-quality comparison with the prior 0.0625 maximum.

This is not proof of Krea2 model compatibility. Actual base/LoRA weights are not
loaded, the exact authored training checkout and alpha remain unverified,
quantized/FP8 base support is blocked, and production compatibility stays
**BLOCKED**. Generation count is zero and quality impact **NOT_MEASURED**.

## Implementation and reuse

The existing `scripts/krea2_dora_numeric_probe.py` gains an explicit
`--candidate ordered` mode. It reuses the same pinned source files, hash checks,
AST extraction, upstream-method fixture, real installed `weight_decompose`
counterexample and reporting. The default remains the old `merged` diagnostic;
there is no implicit fallback or replacement of the failing merge.

`candidate_forward` preserves these source operations separately:

1. Original linear forward including its original bias; strength zero returns it.
2. Two low-rank linear operations, followed by the dtype-rounded runtime alpha
   ratio and the batch multiplier, then the source's output dtype cast.
3. `B @ A` multiplied by the mean of the dtype-rounded multiplier, adapted-weight
   norm, and a separate bias-free magnitude-correction forward.
4. Correction added to the scaled low-rank output, then added to the original
   output. There is no reassociation into one merged matrix.

Shared dense-input validation avoids a second incompatible shape/dtype contract.
Additional checks reject incompatible/empty/nonfinite inputs and wrong bias.
Every comparison verifies that synthetic input, weight, A/B, magnitude and bias
tensors remain unchanged. Invalid norm, missing alpha, unsupported dtype and
quantized paths fail closed. No checkpoint is written or hook registered.

## Evidence boundary

The reference is still the hash-pinned extracted methods from ai-toolkit commit
[`6d8afa5684000b69db97cc40504a972a85615e3b`](https://github.com/ostris/ai-toolkit/blob/6d8afa5684000b69db97cc40504a972a85615e3b/toolkit/network_mixins.py),
declaring version 0.12.9. This is a version-compatible source candidate, not the
author's confirmed training environment. All source/installed-loader hashes and
the full-runtime limitations are described in the preceding numeric report.
The adapted ordering retains upstream MIT attribution in
`scripts/licenses/ai-toolkit-MIT.txt`; the full ai-toolkit dependency stack is not
installed or imported.

Seed 7725 generates identical FP64 fixture values before dtype conversion.
The 960 cases span five `(out, in, rank)` shapes: `(5,3,2)`, `(3,5,2)`, `(4,4,2)`,
`(7,3,1)`, `(3,7,3)`; bias present/absent; 2D/3D inputs; alpha/rank
`0.25, 0.5, 1, 2`; strengths `0, 0.1, 0.5, 1`; and three dtypes. Each invocation
uses one uniform strength. Dropout, training, mixed dtype, per-example different
strengths, quantized tensors, GPU kernels and actual model integration remain
outside the validated scope.

## Reproduce and remaining gates

```powershell
& <ComfyUI>/.venv/Scripts/python.exe scripts/krea2_dora_numeric_probe.py `
  --candidate ordered `
  --source-dir workspace/krea2-dora-numeric-20261025/source `
  --comfy-root <ComfyUI> `
  --output workspace/krea2-dora-ordered-20261025/ordered-release.json
```

Use a fresh output filename. Ordered mode returns exit 0 only when all outputs
are exactly equal; mismatch returns nonzero. Its result still explicitly records
`production_compatibility=BLOCKED`. Source or installed-loader hash drift rejects
execution. Default merged mode retains exit 2 for its known BF16 mismatch.

The next meaningful gate is actual base/adapter key mapping, alpha provenance and
FP8/quantized-base inference behavior. CPU synthetic equality cannot clear those
gates or authorize real image generation. No automatic retry, production workflow
change, model/node installation, Golden/SOT change or review approval is included.

## Validation and rollback

Local ignored `workspace/krea2-dora-ordered-20261025/` contains `ordered-release.json`,
all case/guard details, logs and the final validation summary. It references the
previous pinned source directory; source files and installed loader are unchanged.
Validation executed on this branch:

- Ordered numeric mode: **960 / 960 exact outputs**, 12 / 12 unsupported-input
  checks rejected; exit 0, script hash matches `ordered-release.json`.
- Default merged mode: historical 216-case result reproduced, including all 48
  nonzero BF16 mismatches; expected exit 2 retained in `merged-regression.log`.
- Required editable `.[dev,motion]` install and installed `assetpipe --help`: PASS.
- Full offline regression: **680 passed, 1 skipped**, no failures, 354.07s.
  The skipped `test_direct_frames_are_identical_to_verified_legacy` requires
  unavailable local migration benchmark data. No actual-generation E2E is claimed.
- `git diff --check`: PASS. No changed production/configuration/MCP files;
  primary cleanup checkout remains clean.

The prior merged candidate's BF16 gate remains failed. The new exact-output
result clears only the ordered dense CPU candidate's numerical gate, not any
actual-model, quantized-base or release gate.

Revert this commit to remove the optional diagnostic mode. Production `src`,
configuration, CLI/MCP contracts, installed loader and original weights are
unchanged; no runtime switch is required.
