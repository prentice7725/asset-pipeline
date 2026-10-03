# Krea2 Pixel Art 64px local smoke — 2026-10-03

Status: EXPERIMENTAL / EXPORT_READY_REVIEW_REQUIRED. No production registry promotion or approved Static Master.

## Scope and sources

The user authorized installing the creator's 64px LoRA and Refiner, generating one front-facing human archer, then one additional redraw. Two requests completed; no retries or fallback. Later review preparation generated no images.

- LoRA: https://huggingface.co/e-n-v-y/Krea-2-Pixel-Art
- Refiner: https://github.com/envy-ai/ComfyUI-Krea2-Pixel-Art-Refiner
- Refiner source commit: `0b01ea37f1573ca26a8511337e7d9d77759ee2c7`
- LoRA filename: `k2-pixel64.safetensors`
- LoRA SHA256: `53f1033700a866eaf6f56026cc352e26cd7d0563d4b32957dbbd3765b60d47bf`

LoRA model card displays MIT; base-model licensing applies independently. This local experiment does not establish commercial clearance.

## Reproducible settings

Use the explicitly named API graphs in `config/workflows/krea2_pixel64_smoke_experimental.json` and `config/workflows/krea2_pixel64_redraw_experimental.json`. Neither graph is registered for automatic production routing.

Krea2 Turbo FP8, LoRA strength 1.0, 1024x1024, batch 1, 8 steps, Euler/simple, CFG 1.0. The 64px trigger phrase is omitted per creator recommendation. Official Refiner: width=64, height=64, colors=24, color_reduction_first=true, scale_to_original=false. No transparent-background conversion or identity redesign.

| Run | Seed | Prompt ID | Output | Pixel Gate | Client generation/refinement time |
| --- | --- | --- | --- | --- | --- |
| Initial | 7725 | `19e8a022-be01-49ae-9386-3daa59055a91` | 64x64, 22 colors | PASS | 50.72s |
| Redraw | 7726 | `31dc3fb5-ccfc-49e3-bc11-aed585dea11d` | 64x64, 22 colors | PASS | 41.86s |

Redraw prompt explicitly requests fingers overlapping the bow grip and a grouped three-arrow quiver. Its native candidate SHA256 is `fc4127752e7e1334c1750990a6729832cdbf2371a75696b35e27dd47765746e0`.

## Review and technical verification

The user positively assessed archer readability and hand/bow connection and chose to retain SD proportions. This selects the redraw for further review; it is not human Aseprite approval.

Agent observations: clear archer equipment and hand/grip contact; readable body and clothing clusters. Pose is slightly three-quarter rather than strictly front-facing. Background remains opaque. No quality score or project canon approval is claimed. `idle_down.png` was not available; reference comparison NOT_RUN.

Existing static processing ran binary-alpha-only safe refinement, Pixel Gate and native 64px Resolution Gate. The unchanged-size resolution candidate automatically passed and Codex explicitly selected 64px as orchestrator for review. This does not establish 32px readability or feature-specific preservation: the resolution profile has no identity-feature masks.

Actual Aseprite 1.3.18.6 build/export passed; layer `Pixel`, tag `static`, one 125ms frame. RGBA roundtrip changed zero pixels. A separate reopening/export of the saved master also changed zero pixels. State remains EXPORT_READY_REVIEW_REQUIRED; no human Aseprite approval, animation, Golden recipe or approved Static Master.

## Adapter compatibility warning

The installed ComfyUI loader applied 120 model patches but reported 120 unloaded `.magnitude` keys. Actual safetensors header contains 240 LoRA A/B tensors and 120 magnitude tensors. Installed loader recognizes `.dora_scale` and does not consume the file's `.magnitude` keys. Complete authored-adapter compatibility is therefore unverified; quality impact is unmeasured. No loader patch, weight conversion or ComfyUI upgrade was performed.

## Evidence location and repository validation

Local run artifacts remain under ignored `workspace/runs/krea2_pixel64_smoke_20261003` and `workspace/runs/krea2_pixel64_redraw_20261003`: original images, native outputs, nearest-neighbor previews, model hashes, parameters, budget reservations, prompt receipts/history, QA, feedback and manifests. The redraw's `static_review/060_aseprite/master.aseprite` is the review candidate. These artifacts and downloaded weights/source are not included in this Git commit.

Required editable `.[dev,motion]` install passed with network escalation, pytest: 207 passed, installed `assetpipe --help`: PASS. Shell PATH did not expose the command, so its installed executable was used. No production algorithm changes.
