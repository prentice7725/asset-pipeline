# Requested lower-body alpha cleanup — 2026-10-27

Follow-up: [actual Godot / Phaser import checks](MOTION_ENGINE_IMPORT_20261027.md)
exercise this unchanged candidate's native resources, playback, pivot mapping
and rendered appearance. Human art review and anatomical foot-slide assessment
remain open.

Branch: `codex/motion-alpha-cleanup-20261027`, base `acfac95`.
The user explicitly requested removal of the white area between the legs and the
ground shadow visible in the [border-mask comparison](MOTION_ALPHA_CANDIDATE_20261027.md).
Result: **TARGETED_ALPHA_CLEANUP_CANDIDATE / REVIEW_REQUIRED**.

## Local edit and result

A separate candidate removes visible pale pixels only in the lower-body/ground
regions. All 20 frames retain their original RGB, 512px canvas, source frame
mapping (13..32), 24fps timing, alignment and pivot. No model or generation call,
interpolation, redrawing, resizing, global erosion or production pipeline change.

Final explicit selection, in half-open image coordinates:

- Leg-gap region: `(245,350)..(420,512)`.
- Ground region: `(0,480)..(512,512)`.
- Select only previously visible pixels satisfying `R>=170, G>=145, B>=110`;
  set their alpha to zero, preserving all RGB bytes.

This is a local, source-specific cleanup selection, not a general background
removal algorithm or verified production profile. Dark boot pixels and orange
leg pixels outside that pale predicate are unchanged. All RGBA outside those
regions is byte-identical, including muzzle, ears, scarf and white tail tip.
Some pale antialiased lower-body edge pixels are intentionally removed with the
residual matte; this does not establish perfect anatomical/edge preservation.

All 20 frames were inspected on a dark contact sheet. Before/removal-overlay/after
details for original frames 13, 22, 23 and 32 show the leg-gap patch and pale ground
remnant removed while the dark boot contours remain visually recognizable. The
first local candidate left a small far-left ground fragment; it is retained as
`candidate/`. The final `candidate_v2/` expands only the ground selection to the
full bottom 32 rows and removes that fragment. No source was overwritten.

## Evidence and validation

Artifacts relative to this independent worktree:
`workspace/motion-alpha-cleanup-20261027/candidate_v2/`:

- `frame_00.png`..`frame_19.png`, per-frame removed-pixel masks and records.
- `parameters.json`, `sprites_rgba.png`, `atlas.json`, unchanged-coordinate mapping.
- True-alpha `transparent-preview.png` (APNG), checker/dark GIF previews.
- `all-20-dark.png`, `lower-body-comparison.png` (pink marks removed pixels).
- `verification.json`, untouched human `review.json` template.

| Output/check | Actual result |
| --- | --- |
| Frames / FPS | 20 / 24; original source frames 13..32 |
| Alpha-cleared pixels | 48,092 total; 1,777..5,265 per frame |
| RGB / outside-region RGBA | Exactly preserved for all 20 frames |
| Nonpale pixels | RGBA exactly preserved; no new opaque pixels |
| Selected pale ground pixels remaining | Zero in the bottom-32-row selection, all 20 frames |
| Atlas/APNG | All cells and 20 decoded APNG frames match output RGBA exactly |
| Source preservation | 269 protected files retain their before/after hashes |
| Sprite PNG SHA-256 | `c463819877db5cca5ba31dfdf29df54828ee3213a974b8602b2ffe933e06a38f` |
| Atlas JSON SHA-256 | `40e88c103aa2d221fa2032f36cc829dc13ab882e2c4c76407357754b35b302d2` |
| APNG SHA-256 | `e778f7a4dd2213a113d202ed78846a1afe9e92defcafcc63032ad45a89282960` |
| Parameters SHA-256 | `0f227002d5b5d0cde57ac44e6c3c3abd276db46e9f0511ddbce0ae41293a3423` |

The original opaque run, earlier alpha comparison, masks, consumed generation
reservation and disabled pipeline configuration remain intact. No runtime source,
CLI, MCP, config, model, dependency, Golden/SOT or deployment changed. Existing
720-pass/1-skip software results are historical; current checks are real asset
pixel/atlas/APNG/hash checks, not a newly rerun software suite or a quality score.

## Remaining review and rollback

The requested gap/ground remnants are addressed in the inspected frames. A thin
bright outline elsewhere remains from the earlier binary matte. Temporal edge
flicker, full silhouette acceptance, anatomical pivot, engine import and required
Aseprite human approval remain open. `review.json` stays `REVIEW_REQUIRED`, reviewer
null and checks null; `game_ready=false`. The user's cleanup request is not recorded
as blanket art approval. GIF previews are composited/quantized; RGBA PNG/APNG and
atlas timing are authoritative.

Tracked changes: this report, README, CHANGELOG and prior alpha-report follow-up.
Rollback: revert the documentation commit and stop using the v2 candidate; prior
assets are untouched. Keep the first edit, v2, explicit selection parameters,
removed-pixel masks and original assets for audit and later review.
