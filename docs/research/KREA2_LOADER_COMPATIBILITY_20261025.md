# Krea2 Pixel64 loader compatibility — 2026-10-25

Branch: `codex/krea2-loader-audit-20261025`, based on `e575fe0`.
User-authorized M3 Phase 2 compatibility investigation; no generation budget used.

## Result

**INCOMPLETE_ADAPTER**, reproduced with the installed ComfyUI parser on CPU.
The real adapter file produces 120 `LoRAAdapter` patches consuming 240 A/B
tensors; the loader explicitly reports 120 unloaded `.magnitude` tensors.
All 120 parsed patches have `dora_scale=None`, `alpha=None`.
The converter preserves the input key set (360 tensors).

This confirms a current parser-format gap, not merely a missing string in source.
It does **not** establish base-model key mapping, GPU patch application, authored
training equivalence or the size/direction of any image-quality effect.
Current quality impact remains **NOT_MEASURED** and generation **NOT_RUN**.
The historical two Pixel Gate passes do not change this conclusion.

## Existing implementation reused

- Real installed `comfy.lora_convert.convert_lora` followed by
  `comfy.lora.load_lora`; production functions are imported, not copied or patched.
- The unchanged `k2-pixel64.safetensors` is loaded on CPU with safetensors.
- Existing experimental workflows and Pixel Gate/Refiner remain untouched.
- `scripts/krea2_loader_probe.py` is an explicit diagnostic script, outside the
  production routing path. It imports no server or custom nodes and submits no
  requests. It needs the **ComfyUI virtual environment** with torch/safetensors.

The probe constructs an identity key map from the file's paired A/B stems to
isolate parser behavior. It does not load a base model. Patch counts therefore
mean parser outputs, not successfully applied model weights. Loader warnings are
captured directly; adapter `loaded_keys` is a shared accumulator in this installed
version and is reported only as a union, not attributed independently per patch.

## Reproduce

```powershell
& <ComfyUI>/.venv/Scripts/python.exe scripts/krea2_loader_probe.py `
  --comfy-root <ComfyUI> `
  --lora <models>/loras/k2-pixel64.safetensors `
  --output workspace/krea2-loader-audit-20261025/probe-release.json
```

Use an unused output filename on subsequent diagnostic runs. The script hashes
the input weights and four loader sources before/after execution, forces CPU
imports, disables dependency bytecode writes, records runtime/probe hashes and
never saves altered tensors. It rejects an unrecognized/unpaired A/B format.

Local runtime: Python 3.13.12, torch `2.12.1+cu130`, CPU mode. The separate
standalone launcher Python lacks torch; its initial probe failed before loading
weights. The installed ComfyUI `.venv` completed the actual probe.

| Input | SHA256 |
| --- | --- |
| `k2-pixel64.safetensors` | `53f1033700a866eaf6f56026cc352e26cd7d0563d4b32957dbbd3765b60d47bf` |
| `comfy/lora.py` | `373c6b83f40fe58e8d6c4671525da4335418c3b6a52a13793e5543b1e8c686e1` |
| `comfy/lora_convert.py` | `00da79c3bb4a6ecd73e17243735801295699072e32bbcba43d9b7429fdbcaf2e` |
| `comfy/weight_adapter/lora.py` | `e506062b4eb189be4c36f88270e0fd4dcce038c79a98f7163604ed6b44efe4b5` |
| `comfy/weight_adapter/base.py` | `484f0d83a96e700f80c793e4bcc6a897d633233e51a59191d91da5e59da345c7` |

## Why renaming is insufficient

The adapter metadata identifies `ai-toolkit` version `0.12.9`, a Krea2 raw base,
and 475 training steps. The existing smoke uses Krea2 **Turbo FP8**, so base-model
compatibility is another independent variable, not fixed by tensor key aliases.

Official source inspected and pinned at
[`73ebae13a468942ded8b47991b5d56eeeea25c36`](https://github.com/ostris/ai-toolkit/blob/73ebae13a468942ded8b47991b5d56eeeea25c36/toolkit/models/DoRA.py):
`DoRAModule` stores a learned output-axis magnitude and normalizes using the
adapted weight `W + delta`. The corresponding
[network mapping source](https://github.com/ostris/ai-toolkit/blob/73ebae13a468942ded8b47991b5d56eeeea25c36/toolkit/network_mixins.py)
also maps magnitude keys. This is current source; correspondence to the exact
training version `0.12.9` is **NOT_VERIFIED**. It supports a DoRA-format hypothesis,
not proof that the file can be converted losslessly with a rename.

The installed ComfyUI `weight_decompose` output-axis branch instead takes its
denominator norm from the original `W` and expects a broadcast-compatible scale.
An actual CPU call with synthetic 2x3 matrices demonstrates two distinct issues:

- A flat magnitude vector `[5, 5]` raises a shape error against a 2x3 weight.
- Reshaping the vector to `[2, 1]` avoids that error but does not establish matching
  math. With `W=[[3,4,0],[0,0,5]]`, `delta=[[1,0,0],[0,0,1]]`, strength/alpha=1,
  the installed result is `[[4,4,0],[0,0,6]]`. Normalizing the adapted rows gives
  `[[3.5355339,3.5355339,0],[0,0,5]]`; max absolute difference is **1.0**.

This controlled arithmetic probe used the real installed function; its reference
calculation is an equation evaluation, not an execution of upstream ai-toolkit.
It measures neither real adapter quality nor the full source forward pass.
No renamed/reshaped checkpoint was created, no installed loader was patched,
and no global loader upgrade is proposed as an untested fix.

## Next bounded implementation and remaining gates

Follow-up: [pinned-source numeric validation](KREA2_DORA_NUMERIC_20261025.md)
identifies a 0.12.9 source candidate and compares extracted forward methods.
FP32/FP64 agree within tolerance, but BF16 merging mismatches; operational
compatibility remains blocked. Exact authored training provenance is still absent.

1. Recover/pin the actual training implementation and effective alpha/strength,
   base-model revision, dtype and magnitude axis. Current metadata alone does
   not fully identify that execution environment.
2. In isolation, compare a proposed format-specific adapter with the matching
   source forward/merge behavior at strengths 0, 0.5 and 1, including non-square
   projections, bias, dtype and quantized-base behavior. Reuse existing loader
   entry points; do not replace the shared loader or silently rename weights.
3. Only after numeric equivalence, request a separately budgeted fixed-input,
   fixed-seed baseline/corrected A/B. Record original/native output hashes,
   silhouette, palette, equipment readability and manual editing effort.
4. Keep the existing experimental Pixel64 path, no 32px promotion, no automatic
   fallback/retry and no Golden/Static Master approval inferred from these tests.

## Validation, artifacts and rollback

The local ignored `workspace/krea2-loader-audit-20261025/` retains the complete
`probe-release.json` and warnings, `arithmetic.json`, pinned upstream source files
and their hashes in `upstream/sources.json`, install and regression logs.
Upstream DoRA SHA256: `0b7a66971db200d0389a2d0b73ba8f242dc0d576db262511b4278ee7efe03ae9`.
Upstream network mixin SHA256: `0c1b621503231a9a7f165f7631ff34f7a888857a6ea0969190d6c05ae50f3e8f`.

Validation executed on this branch:

- Required editable `.[dev,motion]` install and installed `assetpipe --help`: PASS.
  An initial no-build-isolation install attempt lacked `bdist_wheel`; the required
  normal build-isolated install then completed successfully.
- New diagnostic tests: **5 passed** (0.04s), including missing A/B pairs, ignored
  scale despite consumed A/B, and a silent loader producing no patches.
- Full offline suite: **675 passed, 1 failed, 1 skipped** (405.77s / 677 cases).
  The failure was the existing
  `test_full_synthetic_probe_connects_to_real_video_packaging`: Windows denied
  `os.replace` of `motion_execution.json.tmp` with WinError 5. No loader assertion
  failed. The migration benchmark skip is unavailable local fixture data.
- That exact synthetic E2E test rerun with a fresh temporary directory:
  **1 passed** (2.90s). There is no production retry added. The original full-suite
  failure log is retained; this is not reported as a clean full-suite PASS.
- `git diff --check`: PASS. No changes under `src`, `config`, `integrations/mcp`
  or the ported algorithms; the primary cleanup checkout remains clean.

No measured image-quality improvement is claimed. All generation, activation,
SOT/Golden, MCP and engine-import gates remain unchanged. Rollback consists of
reverting this diagnostic/documentation commit; there is no runtime configuration
or installed model/loader change to reverse.
