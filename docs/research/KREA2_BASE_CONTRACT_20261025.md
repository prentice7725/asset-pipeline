# Krea2 actual base/adapter contract — 2026-10-25

Branch `codex/krea2-base-contract-20261025`, based on `d39fcd9`.
User-authorized follow-up to the [ordered dense candidate](KREA2_DORA_ORDERED_20261025.md).
No image generation, checkpoint conversion, installed patch or activation.

## Result

The real installed Krea2 mapper resolves all **120 LoRA targets** against the
current base header. All 120 A/B/rank/magnitude shapes match their mapped base
weight shapes, and all 120 have FP8 e4m3fn quantization metadata plus scalar F32
weight scales. Every LoRA rank is **32**. Forty-eight targeted layers declare
`full_precision_matrix_mult=true`; the other 72 do not.

The native parser still produces **120 patches without magnitude**, consumes
240 A/B tensors and logs 120 unloaded magnitude tensors even using this
base-derived map instead of the earlier diagnostic identity map.
Global adapter status remains **INCOMPLETE_ADAPTER** and production **BLOCKED**.

| Actual-file CPU projection | Native load / dequantization / forward | Native output vs dense BF16 reference |
| --- | --- | --- |
| `blocks.0.attn.wk` | All executed; actual `QuantizedTensor`, metadata keeps full-precision MM false | Max absolute difference **0.109375**, not equal |
| `blocks.0.attn.gate` | All executed; metadata sets full-precision MM true | Exactly equal, max difference **0** |

This compares two **base-only** linear forwards with deterministic synthetic
inputs. LoRA application is **NOT_RUN**. A forward execution PASS is not an
adapter-compatibility, numerical-equivalence or quality PASS. The installed
quantized path contains input-quantization behavior absent from a plain dense
BF16 reference; the observed difference is not classified as a model defect or
an image-quality score. No mode was forced to erase that difference.

## Actual inputs and scope

The unchanged workflow is `config/workflows/krea2_pixel64_smoke_experimental.json`,
SHA256 `e00859b2a18186b42a20c166257bf74be2f7dc55e7c0e86e484d6d207c6d4c5e`.
Its explicit UNET and LoRA filenames must match the supplied files.

| File | Bytes / SHA256 |
| --- | --- |
| `krea2_turbo_fp8_scaled.safetensors` | 13,141,730,784 bytes; `eb4dd8c612cfd10f64f25b057e6e6bbcb5737c94a7372177e456dbf7579502f1` |
| `k2-pixel64.safetensors` | `53f1033700a866eaf6f56026cc352e26cd7d0563d4b32957dbbd3765b60d47bf` |

Full-file hashes, workflow and loader-source hashes are checked before/after
the probe. Base bytes are streamed for hashing, not loaded as a full model.
The safetensors headers contain 686 base tensors and 360 adapter tensors.

Detected header configuration: Krea2, features 6144, channels 16, patch 2,
28 blocks, 48 heads, 12 KV heads, 12 text layers and text dimension 2560.
The mapper runs on a clearly marked header-only Krea2 skeleton: meta-device
tensors carry shapes/dtypes, no full Krea2 constructor or weight allocation.
It calls installed `detect_unet_config` and `model_lora_keys_unet`, not a copied
mapping algorithm. This proves the stated metadata mapping, not successful
full-model load or patch application.

Adapter targets cover main blocks **0–19**, two text-fusion layerwise blocks and
two refiner blocks. No keys target main blocks 20–27. This is partial adapter
coverage, not evidence that extra keys should be invented or those blocks are
defective. The author's intended layer selection is not available.

The opt-in isolated probe reads only `wk` and `gate` projection payloads, each
bounded to 64 MiB, plus their real scales. It invokes installed
`convert_old_quants`, `mixed_precision_ops.Linear`, strict state loading,
native dequantization and native CPU forward using each layer's own metadata.
The base/adapter files and installed sources are not modified. It records a
blocked phase/error if a native operation fails; no substitute codec or forward
fallback is implemented. Output shapes are `[2,1536]` and `[2,6144]` respectively.
Real scales are recorded in the local report; no GPU kernel is exercised.

## Alpha evidence and remaining provenance gap

The file has zero `.alpha` tensors and no recorded training alpha configuration.
Its metadata names `krea2_raw_unfiltered2.safetensors` as the authored base; the
current workflow uses **Turbo FP8**. Neither filename proves matching weights or
author intent. The authored base hash and training configuration are unavailable.

New source evidence narrows the alpha question. In pinned ai-toolkit 0.12.9
[`LoRASpecialNetwork.__init__`](https://github.com/ostris/ai-toolkit/blob/6d8afa5684000b69db97cc40504a972a85615e3b/toolkit/lora_special.py),
the PEFT branch assigns alpha equal to rank; transformer-related branches can
force PEFT format. The
[network save path](https://github.com/ostris/ai-toolkit/blob/6d8afa5684000b69db97cc40504a972a85615e3b/toolkit/network_mixins.py)
uses A/B naming and removes alpha in PEFT output. Therefore **alpha/rank=1 has
source support conditional on this pinned PEFT training/export path**. It is not
inferred solely from missing tensors, and does not prove that the author's
checkout, custom conversion, settings and base model followed that exact path.
The machine report deliberately retains `alpha_over_rank=UNKNOWN_NOT_INFERRED`.

Inspected source hashes:

- `toolkit/lora_special.py`: `dcca49bceb2b5660cd14a53c15ffd0d38ff6a07eb1630f6f69b729132f9d385e`.
- `toolkit/config_modules.py`: `c16dff9e0ccb5b577f0f892cf118b024dbe6ec56c0905c1a011b34ba16ef482d`.
- Installed `comfy/ops.py`: `2a5e52fe5176be3ac48becebf1678509867f769c1467fa7c7115d1897c16a429`.
- Installed `comfy/model_patcher.py`: `7edc88d9eae6a88637625d257dc73684cfc012a29446bf88e70d22e3a6be3994`.

The complete nine installed source hashes, config, per-target rows and source
download manifest are preserved with the local evidence. Source analysis did not
execute a complete ai-toolkit training/export environment.

## Reproduce

The existing `scripts/krea2_loader_probe.py` now accepts optional base/workflow
arguments. Original adapter-only usage remains supported. `--probe-layers` is
explicit and requires the base/workflow pair; omitting it performs no base-layer
forward. No complete model, generation node, sampler or server is started.

```powershell
& <ComfyUI>/.venv/Scripts/python.exe scripts/krea2_loader_probe.py `
  --comfy-root <ComfyUI> --lora <models>/loras/k2-pixel64.safetensors `
  --base <models>/diffusion_models/krea2_turbo_fp8_scaled.safetensors `
  --workflow config/workflows/krea2_pixel64_smoke_experimental.json `
  --probe-layers --output workspace/krea2-base-contract-20261025/base.json
```

Use a new output filename. Exit 0 means evidence collection completed; inspect
the explicit `INCOMPLETE_ADAPTER`, per-phase outcomes and BLOCKED state before
interpreting it. This diagnostic cannot approve a recipe or model.

Next implementation can test a quantized-forward-preserving adapter on these
isolated real projections under an explicitly declared alpha hypothesis. It must
retain the native base forward, scale and layer flags; it must not quietly replace
all FP8 execution with dense BF16 or promote that hypothesis to authored approval.
Full model/GPU behavior, base provenance and separately budgeted generation A/B
remain distinct gates. No retry, provider fallback, 32px promotion or Golden/SOT
approval is authorized by the present results.

## Validation and rollback

Ignored `workspace/krea2-base-contract-20261025/` contains the complete `base.json`,
warnings, alpha source files/manifest, test/install/help logs and final summary.
Focused tests: **11 passed** (0.07s), including six new shape/missing-target,
scale, alpha-non-inference and invalid-offset checks.
The required editable install and installed CLI help passed. Full offline
regression is **BLOCKED**, with the exact evidence preserved:

- Initial full suite: **685 passed, 1 failed, 1 skipped**, 410.26s.
- Full recheck with local variables: **685 passed, 1 failed, 1 skipped**, 369.76s.
  Both fail existing `test_concurrent_jobs_cannot_share_authorization`.
- The recheck records one successful receipt and one `Path is outside configured
  roots` result, instead of the expected `ALREADY_RESERVED`. Exactly one synthetic
  provider call was observed; this is not evidence of duplicate generation.
- That single test in isolation: **1 passed**, 0.37s. Entire Factory execution
  test file in isolation: **41 passed**, 2.17s. These results do not replace either
  failed full-suite result or establish that the cause has been fixed.
- Root cause of the full-suite-only path rejection remains **NOT_RESOLVED**.
  It is not attributed to the prior Windows file-replacement error. Factory and
  root-policy implementations were not modified or weakened to hide the failure.
- The skip is the existing unavailable local migration benchmark fixture.
  `git diff --check` passed and the primary cleanup checkout remains clean.

Resolve this regression gate before any integration/release work. The model
header and isolated FP8 observations remain scoped component evidence; no whole
pipeline PASS, quality improvement or operational activation is claimed.

Follow-up: [Windows reservation namespace diagnosis and fix](../maintenance/FACTORY_ROOT_NAMESPACE_RACE_20261025.md)
reproduces this rejection independently of full-suite order and preserves its
original failure logs. The historical results above are not relabelled as PASS.

Only the existing diagnostic/tests and documentation change. Production code,
configuration, six MCP contracts, installed loader and original model files stay
unchanged. Revert this commit to roll back; no runtime switch is needed.
