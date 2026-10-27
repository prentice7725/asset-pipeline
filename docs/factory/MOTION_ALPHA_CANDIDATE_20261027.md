# Fox motion alpha experiments — 2026-10-27

Follow-up: the user requested leg-gap/ground-remnant removal. A
[separate local alpha cleanup](MOTION_ALPHA_CLEANUP_20261027.md) addresses those
regions while preserving this experiment and the remaining review requirements.

Branch: `codex/motion-alpha-candidate-20261027`, base `9888e49`.
Input: the [20-frame loop candidate](MOTION_LOOP_CANDIDATE_20261027.md), original
frames 13..32, 512×512 at 24fps. **ALPHA_CLEANUP_REQUIRED / REVIEW_REQUIRED**.
No generation, model download, production enablement or human approval.

## Actual results

Two separate explicit experiments reuse existing mask primitives. Neither is
installed as a production animation route or automatic fallback. Both retain
the input canvas, RGB pixels, timing, frame order, alignment offsets and pivot.
Only alpha changes; there is no pixelization, palette reduction, pose reconstruction,
crop, resize or silhouette redraw. Original opaque assets remain unchanged.

| Experiment | Existing implementation | Advisory result |
| --- | --- | --- |
| Local U2NetP | `portrait_delivery.preflight/process`, CPU mask, scale 1 and offset `[0,0]` | **REJECTED_FOR_ALPHA_LOSS**. Dark-matte comparison exposes partial transparency in white muzzle and ear interior, light edging and residual ground shadow. Do not use as an approved sprite. |
| Edge-connected white | `pixel.direct.ported.white_border_matte`, explicit white background, Euclidean RGB distance 60, four-connected flood | **NEEDS_CLEANUP**. White muzzle, tail tip and scarf visibly retained in the reviewed frames; thin bright fringe and a pale ground-shadow remnant remain. Binary alpha has hard edges. Not a clean production matte. |

The first defect was reported before starting the second separate experiment.
No failed quality gate was promoted to PASS. Both failed/limited outputs and their
reports are retained; no provider or existing pipeline retry/fallback was added.
Human Aseprite review, engine import and gameplay approval have not advanced.

## Existing implementation reuse and environment

The worktree venv lacks rembg/ONNX Runtime. The original repository venv already
contains **rembg 2.0.69 / onnxruntime 1.31.0**, so it executed the existing local
mask primitive with the worktree's source explicitly on its import path. No pip
install or external model fetch was performed. Its preflight verified the local
model path under the explicitly supplied model root and the existing fixed hash:

`C:/workspace/asset-pipeline/workspace/local_models/u2netp.onnx`

SHA-256 `309c8469258dda742793dce0ebea8e6dd393174f89934733ecc8b14c76f4ddd8`.
Hash was rechecked after processing. CPUExecutionProvider was explicit. Every
frame's mask, masked original, output and existing delivery record is retained.
Only the mask/contain primitive was invoked for a dated experiment: no portrait
profile, project SOT or production animation capability was enabled or invented.
Per-frame learned masks had no temporal smoothing and failed advisory inspection.

The second experiment calls only the existing `white_border_matte` image utility.
It does **not** execute the blue-tunic direct pixel pipeline/profile or claim
blue-tunic compatibility. It uses no model. The returned alpha is applied to a
fresh copy of the original RGB, including RGB under transparent pixels; the helper's
transparent-RGB zeroing is not used. No verified function was changed.
Disconnected enclosed white regions remain foreground by this method, but border
connectivity is not a semantic guarantee for every white character feature.

## What was inspected

Dark/light composites were compared with opaque source at original frames
13, 18, 25 and 32. Enlarged original/U2NetP/edge-white comparisons examine muzzle
and ear interior, white tail tip, red scarf and boots/ground shadow. A chronological
dark-matte contact sheet shows all 20 edge-white frames. The first mask's obvious
white-feature transparency and the second mask's remaining bright outline/shadow
are visible on dark backgrounds; a white background alone hides these defects.

No numeric identity/quality score or improvement percentage is fabricated. RGB
equality does not prove identity preservation after alpha changes: the failed
U2NetP mask demonstrates that distinction. Full-speed temporal flicker, anatomical
foot contact and required human Aseprite acceptance remain unverified.

## Outputs and real checks

Relative to this independent worktree:
`workspace/motion-alpha-candidate-20261027/` retains dated scripts/logs and:

- `candidate/`: rejected U2NetP masks/RGBA frames, delivery records, atlas,
  composited previews, true-alpha APNG, verification and untouched review template.
- `border_candidate/`: comparison RGBA frames, per-frame matte reports/source
  mappings, `sprites_rgba.png`, `atlas.json`, true-alpha `transparent-preview.png`,
  checker GIF, dark/light contact sheet, verification and review template.
- `alpha-advisory.json`, `edge-details.png`, `all-20-border-dark.png`: disposition
  and inspection evidence; these do not write human review decisions.

| Edge-white output | SHA-256 |
| --- | --- |
| RGBA sprite atlas | `fc66fd6f008cd29dd695b6b457367c6f25d5c01b1c27a56955fd60906b535689` |
| Atlas JSON | `ad22f323cabe46c4b170f6dd94c13668a079916b685884184e19771f6e7d888d` |
| True-alpha APNG | `8d5cf86a0427b91cb8f8577c78f6f43c5bfbe0b32a45249ae0f23cacf2c2e1fc` |

Both methods completed real processing of all 20 inputs. Every output's RGB equals
its source exactly. Atlas cells match the corresponding RGBA frames; frame count,
timing and source indices are preserved. True-alpha APNG was decoded and all 20
RGBA frames matched exactly. APNG timing totals 833ms (1ms granularity); checker
GIF is only an opaque, palette-quantized visualization. The border candidate's
alpha values are 0/255; U2NetP retains soft alpha. Neither is approved as halo-free.

**241 protected original files** (opaque derived candidate, original run artifacts
and pipeline configuration) were hashed before and after, with no change. Output
hashes were independently recomputed. Production `src`, `config` and integrations
have no diff. No new generation or budget reservation occurred. Runtime code is
unchanged; the earlier 720-pass/1-skip software suite is historical and was not
rerun or substituted for alpha-quality validation here.

## Remaining work and rollback

Stop before engine/game acceptance. Edge/shadow cleanup must be explicit and
compared against original fur, ear, tail and boot contours; do not erode globally
or remove pale colors indiscriminately. Any repaired matte needs full-frame and
temporal inspection on dark/light backgrounds, followed by required Aseprite
human review. Headroom and anatomical pivot issues from earlier review also remain.
Candidate `review.json` files stay `REVIEW_REQUIRED`, reviewer null and checks null;
the advisory rejection/cleanup dispositions are separate from human approval.

Tracked changes are this report and documentation links/status only. Rollback:
revert the documentation commit and stop using the alpha candidates. Retain both
experiments, original opaque frames and consumed generation evidence. No node,
model, dependency, runtime or SOT installation/change needs reversal.
