# P3 PixelOE API recovery and quality result

## State

The original P3 generation experiment **failed quality validation**. Its ComfyUI `PixelOEPixelize+` node attempt did **not** produce an image: the node raised `ModuleNotFoundError` and the other 11 prepared PixelOE jobs were skipped. This report adds a separate recovery check that successfully called the already-installed official PixelOE Torch API on one existing G01 frame crop. The recovery outputs are research candidates and both fail the unchanged Pixel Gate. No approval was granted.

No new image was generated, no package was installed or upgraded, and no global or ComfyUI environment was changed. The generated source and its provenance remain untouched.

## Verified local cause

| Item | Verified value |
|---|---|
| ComfyUI | `0.38.2`, local workspace `C:\Users\seung\AppData\Local\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI` |
| Loaded node pack | `comfyui_essentials 1.1.0` |
| Node source | `custom_nodes/comfyui_essentials/image.py`, SHA-256 `f31084cd23ff87e8e46e85f7c864e7de9ba398ffaf31f79850d04f48ea28e192` |
| Actual ComfyUI Python | `.../ComfyUI/.venv/Scripts/python.exe`, Python `3.13.12`, Torch `2.12.1+cu130` |
| Installed PixelOE | `1.0.0`, already satisfied by the node pack's unpinned `pixeloe` requirement |
| Old import lookup | `pixeloe.pixelize` — absent in the installed package |
| Legacy API location | `pixeloe.legacy.pixelize` — present |
| Current Torch API | `pixeloe.torch.pixelize` — present and executed |

The loaded node calls `from pixeloe.pixelize import pixelize` at `image.py:888`. Its live schema exposes `downscale_mode={contrast,bicubic,nearest,center,k-centroid}`, `target_size=128` (0–16384, step 8), `patch_size=16` (4–32, step 2), `thickness=2` (1–16), `color_matching=true`, and `upscale=true`. Thus the live node cannot request thickness 0. The source makes the old import unconditionally before image conversion.

The actual installed API lookup confirmed the exact mismatch: the package version is present, but the old top-level module path is not. Official PixelOE 1.0.0 includes the Torch API `pixeloe.torch.pixelize`; its implementation explicitly skips outline expansion when `thickness <= 0`. The module move, not an absent PixelOE installation, explains the prior exception. We did not patch the installed ComfyUI node.

The 1.0.0 release documentation and source are maintained by PixelOE's official publisher: [PyPI project and release](https://pypi.org/project/pixeloe/), [official Torch API documentation](https://github.com/KohakuBlueleaf/PixelOE#python-api), [1.0.0 release Torch implementation](https://github.com/KohakuBlueleaf/PixelOE/blob/1d45ba0b5c51c3d998b19043a168366a8f170eaa/src/pixeloe/torch/pixelize.py), and [legacy implementation at that release](https://github.com/KohakuBlueleaf/PixelOE/blob/1d45ba0b5c51c3d998b19043a168366a8f170eaa/src/pixeloe/legacy/pixelize.py).

## Actual offline API run

Input: existing G01 human archer south/front crop `post/pixelOE_inputs/G01_1_south_front.png` (256×256 RGB, opaque white, no alpha). It is a derived crop from the untouched 512×512 original, raw SHA-256 `3ad21be81240b861db9c839268d349b3c6f7f3eb1ea39752858a0981f072f7b8`; crop SHA-256 `c2d2b8f01210d8e80bc90057431318dcc2aab7fe703fc65c6d0182e2d02cbb65`. Existing crop provenance specifies bbox `[106,3,176,133]`, aspect-preserving contain to 224×224, centered in 256×256, no crop.

Both calls used the official `pre_resize` helper (bicubic, target size 32, patch size 16), contrast downscale, color matching enabled, quantization disabled, no post-upscale, `backend="torch"` on the installed ComfyUI CUDA runtime. This creates actual 32×32 PNG files. Thickness 0 and 2 are two executions on that one fixed input; they are not generated samples.

| Candidate | PNG SHA-256 | RGB colors | Alpha/background | Pixel Gate | Gradient / AA | Silhouette clusters |
|---|---|---:|---|---|---|---|
| PixelOE thickness 0 | `8ef33d9879a6964269a93744e1886a1fe377c49ea3befd084bb76622f03b64b1` | 238 | RGB; alpha absent; white-matte input | **FAIL** | HIGH / HIGH | 2 connected; largest ratio 0.9966; 1 isolated pixel |
| PixelOE thickness 2 | `94cedea5efcb7bac8e64eecf6ce0a4fd36c3924d153a9e24e9f6c1598041943f` | 226 | RGB; alpha absent; white-matte input | **FAIL** | HIGH / HIGH | 2 connected; largest ratio 0.7301; 0 isolated pixels |
| Existing NN → MedianCut 32 opaque-white baseline | `3f5fac38ac12d0d5f04fbbfcaa3cf3f809768b0ce2d0d27dec2210225747ee73` | 32 | RGB; alpha absent; opaque white | PASS on this crop only | LOW / LOW | 2 connected; largest ratio 0.9968; 1 isolated pixel |

All three were remeasured with the unchanged `assetpipe._ported.pixel_gate.analyzer.analyze_image`: max colors 32, gradient threshold 0.18, target 32×32. Both PixelOE outputs fail because the colors exceed the cap and both gradient and anti-alias suspicion are HIGH. Thickness 2 changes cluster coverage and makes the silhouette larger; that numeric change alone does not establish better identity or equipment readability. The single baseline technical PASS is not production success. Neither output was art-reviewed, and the source itself still contains repeated front-facing figures despite the requested multi-direction layout.

The outer border is uniform for each PixelOE output, but the color-matched API result does not preserve exact `#ffffff` pixels across its full matte; t0 has no exact-white pixel and t2 has 541 pixels not exactly `#ffffff`. Gate silhouette metrics above, not exact-white occupancy, are the cluster evidence. PixelOE preserves the RGB white matte and produces no alpha; transparent-edge behavior remains untested. Human review is still required for 1× identity, bow readability, silhouette semantics, matte fringe, and whether thickness 2 merges equipment/body clusters.

## Artifacts

- Original G01 raw PNG: `../../generated/G01/83aacbc7_000.png` — unchanged.
- Actual PixelOE output: `pixeloe_t0_32x32.png`, `pixeloe_t2_32x32.png`.
- Existing method baseline: `../G01/south_front/P1_NN_THEN_MEDIANCUT_32/32px_opaque_white.png` — unchanged.
- Native logical-resolution comparison: `comparison_native_1x.png` (each candidate panel is 32×32).
- Display-only 4× nearest comparison: `comparison_nearest_4x.png` (not used for measurements).
- API parameters, runtime, output hashes and color counts: `pixeloe_execution.json`.
- Same-gate reports and comparison metrics: `gate_*.json`, `comparison_results.json`.
- Captured invocation output: `execution.log`; QA invocation output: `qa_execution.log`.
- Reproduction scripts: `run_pixeloe_api.py`, `analyze_and_compare.py`.
- Original ComfyUI node failure/schema record: parent `../pixeloe_runtime.json` and `../pixelOE_workflows.json`.

## Revised generation plan

Generation budget is **0** until separately approved. No more generation was requested or sent in this recovery. When separately authorized, start with one subject and one direction: a centered human archer facing south/front, filling most of a simple-background 512×512 source. Submit a matched standard-Anima-VAE / Pixelate-x4-VAE pair with identical prompt, seed and settings (2 images total). Do not ask for multiple characters or views in one sheet. Compare both outputs through the same 32×32 PixelOE thickness 0/2 and existing NN+palette treatments, unchanged Pixel Gate, native 1× and nearest 4× review, then local pixel edits and actual human review. Add a second subject only if the first paired comparison answers the pipeline question; an archer-plus-orc VAE screen would require 4 images total. No Static Master or Golden Recipe approval may occur automatically.
