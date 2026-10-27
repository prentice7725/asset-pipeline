# Actual FP8 projections with LoRA hypothesis — 2026-10-25

Branch `codex/krea2-fp8-lora-probe-20261025`, based on `abd9bb4`.
User-authorized continuation after the
[base contract probe](KREA2_BASE_CONTRACT_20261025.md) and regression fixes.
This step uses real installed tensor values with synthetic CPU inputs. It runs
no full Krea2 model, image sampler, server request, GPU kernel or generation.

## Outcome and limits

With **explicit research hypothesis alpha/rank=1**, the candidate matches a
controlled hybrid oracle exactly in **24 / 24 cases**, maximum absolute error 0.
The oracle is the pinned upstream dense norm/correction methods with their base
forward bound to the real native ComfyUI FP8 projection. It is **not** an
execution or verification of the author's complete quantized runtime.

| Real projection | Exact hybrid cases | Largest difference from dense-base candidate | Largest effect of multiplying magnitude by 0.9 |
| --- | --- | --- | --- |
| `blocks.0.attn.wk` | 12 / 12 | 0.109375 | 0.53125 |
| `blocks.0.attn.gate` | 12 / 12 | 0 | 0.1875 |

Across both layers, all eight zero-strength cases exactly retain native FP8
output and ignore magnitude perturbation. All sixteen nonzero cases respond to
the magnitude perturbation. This demonstrates actual tensor use in this isolated
candidate, not merely key presence. These values are linear-output differences,
not measured image-quality improvements or palette/silhouette scores.

Native state, quantization flags, actual A/B/magnitude and dense norm weights,
inputs and original files are unchanged before/after the probe. Native forward
repeatability is checked for each case. `wk` retains full-precision MM false;
`gate` retains the metadata's full-precision MM true. Neither flag is forced.

**Production compatibility remains BLOCKED.** The normal installed parser still
reports **INCOMPLETE_ADAPTER**, with 120 magnitude keys unloaded. No production
loader fix, registered hook, provider integration or workflow replacement is
performed. Only two of the 120 adapter targets are exercised with actual weights.
The authored Raw base versus current Turbo base, authored training/export
provenance, other targets, GPU and complete model behavior remain unverified.

## Reused implementation and oracle boundary

The existing loader diagnostic gains explicit `--probe-lora`, `--source-dir` and
`--alpha-over-rank` options. All are guarded: the LoRA hypothesis requires the
existing base/workflow pair and opt-in layer execution; missing, nonfinite,
nonpositive or unused hypothesis declarations reject before model hashing or
loading. Alpha is never inferred from absent tensors. Its source-supported PEFT
condition is described in the preceding base report and remains a hypothesis.

`candidate_forward` in the existing numeric diagnostic accepts an optional
explicit base-forward callable. With no callable its previous dense behavior
is preserved. With a callable it keeps that native result as the original term,
while preserving the already verified ordering of the separate low-rank and
magnitude-correction terms. Wrong callable/output shape, dtype, device or
nonfinite output rejects instead of silently substituting dense execution.

The reference reuses hash-pinned methods from ai-toolkit 0.12.9 commit
`6d8afa5684000b69db97cc40504a972a85615e3b` through the existing AST harness.
Its temporary fixture holds the real dequantized BF16 weight for the norm and
the real adapter A/B/magnitude values. Only its original forward is bound to the
native FP8 op. This deliberately prescribed hybrid boundary does not establish
that the author's quanto implementation or ComfyUI's normal weight-patching
path has identical semantics. Full constructors/training/export are not run.

Both selected projections have no bias in the actual base header. A bias-bearing
projection rejects rather than discarding bias. The existing 64 MiB per-base-
projection payload limit, native strict load, source hashes and configured
workflow filename binding remain in force. No checkpoint or merged weight is
written. The callback is local to temporary probe objects; it installs no hook
on an operating model or service.

## Inputs and protocol

- Base: `krea2_turbo_fp8_scaled.safetensors`, SHA256
  `eb4dd8c612cfd10f64f25b057e6e6bbcb5737c94a7372177e456dbf7579502f1`.
- LoRA: `k2-pixel64.safetensors`, SHA256
  `53f1033700a866eaf6f56026cc352e26cd7d0563d4b32957dbbd3765b60d47bf`.
- Existing experimental smoke workflow SHA256
  `e00859b2a18186b42a20c166257bf74be2f7dc55e7c0e86e484d6d207c6d4c5e`.
- Per projection: seeds 7/7725, input shapes `(2,in)` / `(1,3,in)`, BF16 inputs
  scaled by 0.1, strengths 0/0.5/1, uniform alpha/rank 1, actual rank-32 tensors.
- Both zero- and nonzero-strength behavior are measured. Sensitivity uses a
  separate temporary `0.9*m` value; original learned magnitude is not modified.
- Typed tensor hashes include dtype/shape JSON, a newline and contiguous raw
  bytes. Scalar scales are flattened for byte hashing. Public native state-dict
  hashes and active flags are compared before/after; native repeatability and
  finite outputs are prerequisites to an exact-match result.

```powershell
& <ComfyUI>/.venv/Scripts/python.exe scripts/krea2_loader_probe.py `
  --comfy-root <ComfyUI> --lora <models>/loras/k2-pixel64.safetensors `
  --base <models>/diffusion_models/krea2_turbo_fp8_scaled.safetensors `
  --workflow config/workflows/krea2_pixel64_smoke_experimental.json `
  --probe-layers --probe-lora --alpha-over-rank 1 `
  --source-dir workspace/krea2-dora-numeric-20261025/source `
  --output workspace/krea2-fp8-lora-probe-20261025/probe-ship.json
```

Use a fresh output filename. Exit 2 preserves the report if any requested LoRA
probe is blocked or mismatched. Exit 0 means only the requested isolated probes
completed exactly; the installed parser status and production BLOCKED field
remain explicit. Source, workflow and both complete model-file hashes are
checked before/after; the full base is streamed for hashing, not instantiated.

## Validation, remaining gates and rollback

Ignored `workspace/krea2-fp8-lora-probe-20261025/` retains canonical
`probe-ship.json`, all cases/typed tensor hashes, native-state hashes/flags,
source/script hashes, loader warnings and test/install/help logs. Initial
instrumentation failed before cases when hashing scalar scales; its report is
retained. The final run uses scalar-safe hashing and contains all 24 cases.

- Actual projection probe: **24 exact cases**, eight native zero-strength noops,
  sixteen nonzero magnitude-sensitive cases; all state/input checks pass.
- Dense ordered regression remains **960 / 960 exact**, with **16** rejection
  checks, including four new base-callback/output contract checks.
- Focused parser/source/hypothesis guard tests: **22 passed**, 0.19s.
- Required editable install and installed CLI help: PASS.
- Full offline regression: **712 passed, 3 failed, 1 skipped**, 419.04s.
  The failures are existing Factory `missing_outputs`, SFX listening evidence
  `qa`, and independent NONPIXEL style-lab cases. All three fail at the shared
  `manifests.write` atomic `.tmp` replacement with Windows **WinError 5**.
  The full log preserves paths/tracebacks; this is not a tensor mismatch.
- Those three cases rerun in isolation: **3 passed**, 0.97s. Their individual
  passes do not replace the failed full run. The local file-write cause remains
  unresolved, and the full regression gate is **BLOCKED**.
- The single skip is the unavailable local migration benchmark fixture.
  `git diff --check` passed; no production/configuration/MCP files changed, and
  the primary cleanup checkout remains clean.

The next prerequisite is local atomic-write reliability while preserving one
provider attempt, source evidence and failed-gate behavior. No write retry or
provider retry is silently added by this research commit.

An eventual whole-model research adapter must preserve native base forwarding,
job isolation and quantization semantics across all targets. This local probe
does not enable one. All real-generation A/B budgets, human review, Golden/SOT,
32px promotion and operating-service changes remain separately gated. No retry,
fallback, new model/node installation or quality approval is added.

Only research diagnostics/tests and documentation change. Revert this commit to
roll back the optional probe/callback; installed code, original weights and
workflow/configuration require no rollback.

Follow-up: [bounded CUDA base execution and CPU regression](KREA2_GPU_BASE_20261027.md)
checks the same two projections on the actual GPU while preserving this report's
historical failures and incomplete-adapter/alpha/full-runtime limitations.
