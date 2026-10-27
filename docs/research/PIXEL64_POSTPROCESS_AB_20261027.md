# Existing-image Pixel64 postprocess comparison, 2026-10-27

Branch `codex/pixel64-postprocess-ab-20261027`, base `25ea796`.
**COMPARISON_EXECUTED / EXTERNAL_DEFAULT_NOT_ADOPTED**.
[Machine-readable current observations](PIXEL64_POSTPROCESS_AB_20261027.json).

## Inputs and bounded execution

The two existing archer runs `krea2_pixel64_smoke_20261003` and
`krea2_pixel64_redraw_20261003` retain their original 1024px PNGs and historical
64px outputs under `C:/workspace/asset-pipeline/workspace/runs/`.
Raw/output hashes were checked against their existing manifests. All 104 files
in both run directories were hashed before and after and remained unchanged.
These are two poses/candidates of the same character, not a diverse benchmark.
Both originate from the incomplete-magnitude loader session; this comparison
does not repair or approve that LoRA and cannot represent a fully applied adapter.

No images were generated, uploaded or redesigned. No dependency, model or custom
node was installed. No workflow, production source, default, review record,
Golden/SOT or MCP contract changed. Existing opaque backgrounds remain opaque.
Artifacts and reviewed third-party source remain outside source modules under
ignored `workspace/pixel64-postprocess-ab-20261027/`.

The four independent arms were declared in `plan.json` before image processing:

1. Existing 64px output through the unchanged Safe Refiner with binary-alpha-only
   settings: no palette projection, resize, trim or isolated-pixel removal.
2. Existing creator Refiner, palette reduction before grid collapse: 64x64,
   24 colors, `scale_to_original=false`, matching the historical settings.
3. The same creator Refiner, grid collapse before palette reduction, otherwise
   identical parameters. This is an explicit alternative, not a retry/fallback.
4. Pixel Art Fixer Python API, full-mode defaults, automatic grid, two-stage
   reconstruction, `k_colors=0`, no forced step, palette snap or dark-stroke mode.
   OpenCV RNG seed was explicitly set to 7725 before each independent case.

The [creator Refiner](https://github.com/envy-ai/ComfyUI-Krea2-Pixel-Art-Refiner/tree/0b01ea37f1573ca26a8511337e7d9d77759ee2c7)
was executed from its existing archived source through the original node's
`execute` method in a local CPU process, without a server submission.
The first preflight stopped before any image processing because the archive's
CRLF bytes differ from the upstream LF hash. Universal-newline text equality
was verified; the original archive bytes were pinned as SHA-256
`74605aa0ac8d78df14992638ba2cdf1d9c139e3e199660e7e2d1408e31e39956`.
Neither copy was modified. This correction and initial stop are retained in
`preflight-correction.json`; no processing failure was retried.

[Pixel Art Fixer](https://github.com/Retro-Diffusion/pixel-art-fixer/tree/ef376e57e1c272633ca2dbf5f29ec3fcf6596465)
was pinned at `ef376e57e1c272633ca2dbf5f29ec3fcf6596465`; its MIT license
and Python source hashes are retained. Its actual `pixelfixer.api.process`
function was imported from the isolated source folder. The documented CLI was
not used: the inspected CLI imports `detector`, while the package is named
`pixelfixer`. This source observation is not a reproduced CLI test result.
No import alias, package patch or new production adapter was introduced.

## Current measurements

Every output was evaluated now with the existing Pixel Analyzer, target 64x64
and max_colors=24. Its technical PASS does not approve artwork or equipment.

| Arm | Initial: size / colors / Gate | Redraw: size / colors / Gate |
| --- | --- | --- |
| Historical candidate + safe no-op | 64x64 / 22 / PASS | 64x64 / 22 / PASS |
| A: palette then grid, current CPU | 64x64 / 22 / PASS | 64x64 / 22 / PASS |
| B: grid then palette, current CPU | 64x64 / 24 / PASS | 64x64 / 24 / PASS |
| C: Fixer automatic, full defaults | 64x64 / 879 / FAIL | 64x64 / 853 / FAIL |

Safe Refiner changed zero RGBA pixels in both historical candidates. Fixer
correctly selected 16px cells / 64x64 output in both cases, decision
`fast:ac+rl(S)`, tool-reported confidence `high`. This is two observed detection
results, not replication of its published 94% benchmark.

Fixer's reconstructions failed the existing color budget and high-gradient
heuristic. They were not resized again, quantized into compliance, exported to
Aseprite, used as a master or advanced past the failed gate. Default two-stage
reconstruction does not impose our 24-color output palette; this result does not
prove that every possible configuration or a separately designed combination
would fail. No parameter sweep was performed.

### Current replay is not historical pixel equivalence

Arm A has the same color count and Gate result as the historical creator output,
but differs in 3,444/4,096 initial and 3,712/4,096 redraw RGBA pixels. Most of
these changes are small; max RGB channel differences are 33 and 21, mean absolute
RGB differences 0.664876 and 0.646566 (8-bit units). There are 578 and 55 pixels
whose maximum channel change exceeds one. Alpha is unchanged.

Therefore this is a current CPU execution, **not bit-exact historical replay**.
The cause is not established; no device, runtime or PNG-rounding explanation is
asserted without a controlled test. Preserved historical outputs remain the
selected historical candidates. Neither current A nor B replaces them.

## Visual review and interpretation

The local nearest-neighbor contact sheet `comparison.png` shows A/B/C for both
raw inputs. Agent inspection finds the archer, bow and quiver recognizable in
all six previews. B changes small face/equipment clusters; there is no justified
claim that these edits improve identity or reduce manual work. C retains many
near-duplicate colors, visible as fine tonal variation. These are agent
observations, not human art approval or measured equipment identity scores.

The existing border-color silhouette heuristic returns matching bounding boxes
for A/B (initial 34x60; redraw 45x60). C returns full-canvas bounds and extra
components because its near-white background is not a uniform exact border color.
These masks are diagnostic proxies; full-canvas bounds do not prove a geometric
silhouette expansion, and bounding-box agreement does not prove identity lock.
No new semantic mask or background-removal algorithm was invented for this study.

Palette budget, dimensions, alpha, changed pixels, timing and hashes are measured.
Silhouette semantics, bow/hand contact quality, equipment readability at gameplay
scale and manual editing time remain **HUMAN_REVIEW_REQUIRED / NOT_MEASURED**.
All technically passing new candidates require actual Aseprite review before
promotion. No human review, approved Static Master or Golden recipe is inferred.

## Decision and verification

Keep the existing Refiner path and historical selected candidate. Do not add
automatic Pixel Art Fixer dispatch or change processing order/defaults on this
evidence. A known 64px grid already works here; automatic detection alone adds no
demonstrated production-quality improvement. Pixel Grid Tools and
ComfyUI-PixelPipeline were not executed in this comparison.

Actual checks: 8 current Gate evaluations, two zero-change Safe Refiner calls,
six independent CPU postprocess executions, original/source hash preservation,
JSON consistency and preview inspection. The prior Python regression suite is
historical and was not rerun for this documentation-only change. No offline
test result is used as a new model-quality PASS.

Reproduce using the retained `compare.py` with the installed ComfyUI Python;
it imports current `assetpipe.pixel` analyzer/refiner, preserves source files,
and refuses to overwrite `plan.json`. The source-fetch manifest, exact parameters,
runtime versions, source code hashes, per-arm Gate reports, raw results and
preview hash are retained and summarized in the linked observation JSON.

Rollback: revert this report/observation and README/CHANGELOG changes. No live
configuration or installed code needs reversal. Keep the original candidates
and local comparison evidence.
