# Krea2 Pixel64 bounded CUDA base check, 2026-10-27

Branch: `codex/pixel64-gpu-compatibility-20261027`, base `1c6ffbf`.
**CUDA_BASE_PROJECTION_EXECUTED / ADAPTER_COMPATIBILITY_BLOCKED**.
Image generation: NOT_RUN. Image quality impact: NOT_MEASURED.

## What changed and what did not

The existing `scripts/krea2_loader_probe.py` gains explicit
`--probe-device cuda` for the same two bounded base projections. CPU remains
the default. The installed parser still executes on CPU; CUDA is restricted to
temporary base Linear objects, without an active model, hook or service change.
The CPU-only `--probe-lora` hypothesis rejects CUDA before weight hashing/loading.
No alpha is inferred and the verified CPU DoRA arithmetic is not ported/reworked.

The existing safetensors header/offset/shape checks, base mapper, workflow filename
binding, original-file hashes and native ComfyUI quantized Linear loader are reused.
Each base projection remains capped at 64MiB raw payload. CUDA preflight requires
availability and at least 1GiB free according to `torch.cuda.mem_get_info(0)` after
context initialization. Unavailable/low-memory cases report BLOCKED; no CPU fallback,
other-job interruption, service offload or model unload request is introduced.

CUDA executes seeds 7/7725, BF16 inputs scaled by 0.1, shapes `(2,in)` and
`(1,3,in)` for each projection. It checks output shape/dtype/device, finite values,
native repeatability, unchanged inputs and native state/quantization flags.
Dense BF16 reference differences are measured, not used to claim FP8 is bit-exact
or to set an image-quality score. Tensor digests copy temporary values to CPU for
byte hashing; existing CPU digest semantics are unchanged.

## Actual execution and immutable inputs

The installed ComfyUI Python actually executed the two projections on
**NVIDIA GeForce RTX 5060 Laptop GPU**, CUDA device 0, capability 12.0,
torch **2.12.1+cu130**. No full Krea2 model was instantiated or sampled.

| Input | SHA-256 |
| --- | --- |
| Base `krea2_turbo_fp8_scaled.safetensors` | `eb4dd8c612cfd10f64f25b057e6e6bbcb5737c94a7372177e456dbf7579502f1` |
| LoRA `k2-pixel64.safetensors` | `53f1033700a866eaf6f56026cc352e26cd7d0563d4b32957dbbd3765b60d47bf` |
| Existing experimental workflow | `e00859b2a18186b42a20c166257bf74be2f7dc55e7c0e86e484d6d207c6d4c5e` |
| Executed probe script | `63ba69065c69be7e18466b8d2a7613d054178a3e2b586901d2460b3c50365006` |

All original files and recorded installed loader sources match before/after.
The base is streamed for hashing/header access; only two selected projections
are materialized. The ComfyUI queue was read-only checked empty before testing.
GPU/kernel caches were directed under the ignored experiment folder. No model,
node or dependency installation, new checkpoint, provider change or production
configuration modification occurred.

| Projection | Native full-precision-MM flag | CUDA cases | Largest difference from dense BF16 |
| --- | --- | --- | --- |
| `blocks.0.attn.wk` | false, preserved | 4 finite/repeatable/unchanged | 0.109375 |
| `blocks.0.attn.gate` | true, preserved | 4 finite/repeatable/unchanged | 0 |

All eight outputs are on cuda:0. Both public native state digests and flags remain
unchanged. Peak PyTorch-allocated memory reported by this process was
335,581,696 bytes (about 320MiB), excluding CUDA context and non-PyTorch/global
allocations. This is not a global GPU reservation or memory-limit certification.
The pre/post `nvidia-smi` snapshots and Torch's own preflight metrics are retained;
they have different accounting scopes. No hardware FP8 Tensor Core/kernel-path
profiling or complete quantized-runtime equivalence is claimed.

## CPU regression and actual remaining blocker

The existing CPU research hypothesis was rerun unchanged with explicit
alpha/rank=1 and the same hash-pinned upstream methods. All **24 cases** again
exactly match that controlled hybrid oracle, and the entire per-case records
equal the previous 2026-10-25 result. This confirms CPU-path preservation; it
does not establish the author's alpha or whole-model inference behavior.

The real installed converter/parser still emits **120 patches consuming 240 A/B
tensors and reports 120 unloaded `.magnitude` keys**. Top-level status is
INCOMPLETE_ADAPTER in both runs. The original adapter remains unchanged.
The file metadata names ai-toolkit 0.12.9 and a Raw/unfiltered base path but gives
neither a confirmed training checkout, alpha nor a base content hash matching
the current Turbo FP8 file. Those missing values are not inferred from rank.

This step verifies native CUDA execution for two base targets only. It does not
apply LoRA on GPU, verify the other 118 targets, offloading/full-model memory,
the author's quantization stack, art quality or production compatibility.
Renaming `.magnitude` to `.dora_scale`, forcing full-precision flags or merging
BF16 weights is not adopted as a fix.

The next compatibility prerequisite is confirmed authored base/alpha/export
semantics or a source-compatible export/loader, then a job-isolated full-target
adapter check preserving native base forwarding. Only after those gates should
separately authorized image A/B and Pixel Gate/art/manual-edit measurements run.
There is no new generation budget in this change, and no 32px promotion.

## Reproduction and current tests

```powershell
& <ComfyUI>/.venv/Scripts/python.exe scripts/krea2_loader_probe.py --comfy-root <ComfyUI> --lora <models>/loras/k2-pixel64.safetensors --base <models>/diffusion_models/krea2_turbo_fp8_scaled.safetensors --workflow config/workflows/krea2_pixel64_smoke_experimental.json --probe-layers --probe-device cuda --output workspace/new_probe/gpu-base.json
```

Use a new output filename. Parser status can remain INCOMPLETE_ADAPTER even when
the requested bounded base probe exits 0; exit 0 is not LoRA/full-pipeline PASS.
A blocked CUDA projection exits 2 with its evidence. The default CPU invocation
and existing explicit CPU LoRA source/hypothesis guards are retained.

Focused tests: **24 passed**, 0.13s, including CUDA unavailable/memory-floor
rejection, no default CUDA query and invalid GPU/LoRA combinations before input
loading. Current required validation:

| Check | Result |
| --- | --- |
| Editable install `.[dev,motion]` | PASS |
| Installed `assetpipe --help` | PASS |
| Full offline pytest | 778 passed, 1 skipped; 493.34s |
| Actual selected CUDA base inputs | 8 finite/repeatable/state-preserved cases |
| Actual CPU LoRA hypothesis | 24 exact cases; per-case records and consumed tensor digests equal prior |

The skip is the unavailable local migration benchmark; it is not a PASS.
The old report's failed historical suite is not relabeled as a current PASS.

Ignored `workspace/pg27/` retains `gpu-base.json`, `cpu-hypothesis.json`, native
warnings/logs, per-input/state digests, `verified-summary.json`, pre/post GPU
snapshots, caches and software-test evidence. `verify.py` independently checks
eight CUDA cases, exact CPU historical parity, unchanged original hashes and
the shared executed script digest. No approval state is manufactured.

Changed files: the existing loader probe and its unit tests, this report,
README/CHANGELOG and a follow-up link in the earlier isolation report.
Rollback by reverting this optional probe extension. Installed ComfyUI, original
weights, workflows, production providers and Golden/SOT require no reversal.
