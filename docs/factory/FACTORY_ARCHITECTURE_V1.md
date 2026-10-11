# Factory Architecture v1 — M3 four production lines

**State:** PROPOSED / DOCUMENTATION_ONLY / NO_RUNTIME_CHANGES
**Decision date:** 2026-10-11 (Asia/Tokyo)
**Repository baseline:** main at abd7fe246b36be3d79a8ea1ed9d7a022339f16d0
**Purpose:** Turn the existing Asset-Pipeline into a reliable game-asset factory without losing its existing evidence, review, security, or source-of-truth boundaries.

## 1. Authorized product scope

32px native pixel-art production is **ON_HOLD_RESEARCH**. Preserve all historical pixel algorithms, fixtures, manifests and tests; do not promote, delete, or silently route new 32px production work. The immediate factory has four lines:

| Line | Source | Terminal product | Optional downstream | Current evidence boundary |
| --- | --- | --- | --- | --- |
| **A NONPIXEL** | project SOT / brief / prompt | **IMAGE_ONLY** (independently complete) | **IMAGE_TO_SPRITE** = image -> video -> frames -> sprite sheet | Still-image generation real E2E exists; general NONPIXEL_ANIMATION execution is a stub |
| **B REFERENCE_MOTION** | existing/imported **1, 2, or 3 images** | **IMAGE_TO_SPRITE** = references -> video -> frames -> sprite sheet | no prerequisite still-image generation | New general multi-reference motion contract, not yet implemented |
| **C SFX** | explicit text SFX brief | **AUDIO_ONLY** = FLAC/WAV + audio QA + listening review | none | CLI/MCP real-generation QA exists, human listening approval pending |
| **D PIXEL64** | project SOT / brief / prompt | **IMAGE_ONLY** (64x64 reviewed static master) | **IMAGE_TO_SPRITE** = static -> video -> frames -> pixel-preserving process -> sprite sheet | Two 64px technical smoke PASS candidates; still EXPERIMENTAL and unapproved |

**Invariant:** For A and D, video generation and sprite extraction are strictly opt-in. IMAGE_ONLY is a real completion branch, not a failed or incomplete animation. For B, input images are existing inputs; do not regenerate them implicitly. A failed motion child cannot invalidate a previously reviewed/approved still image. No branch is game-ready solely because technical QA passed.

## 2. Factory topology

~~~text
Project ACTIVE/SOT + approved art + user request
  -> source-backed Asset Brief / PromptSpec
  -> validated factory plan (line, source, terminal output, limits, budget)
  |
  +-- A NONPIXEL: style menu -> image generation -> image QA -> review
  |                | IMAGE_ONLY: stop and export image review package
  |                + approved source / explicit research authorization
  |                   -> shared motion backbone
  |
  +-- B REFERENCE_MOTION: 1..3 source images -> role/provenance validation
  |                      -> shared motion backbone
  |
  +-- C SFX: direct SFX prompt -> Stable Audio -> PCM WAV
  |          -> technical audio QA -> listening review package
  |
  +-- D PIXEL64: fixed 64x64 generator/refiner -> pixel/identity QA
                   -> Aseprite static review
                   | IMAGE_ONLY: stop and export static-master package
                   + approved source / explicit research authorization
                      -> shared motion backbone
                      
shared motion backbone:
  image role/ordering check -> provider capability preflight
  -> image-to-video generation (one paid attempt per authorization)
  -> preserve original video + parameters + SHA
  -> FFmpeg frame extraction
  -> semantic temporal selection / alignment (no unsupported auto-approval)
  -> background/alpha processing (explicit, reviewable)
  -> sprite export + sheet metadata
  -> domain-specific QA + human review
  -> candidate package (never automatic SOT/Golden approval)
~~~

The shared motion backbone is one service used by A/B/D. Reuse existing **motion/extractor**, **_ported/motion_extractor**, **pixel/direct**, Aseprite bridges, and manifest utilities where their verified contracts apply. Never generalize the historical blue_tunic_white_matte_v1 eight-frame walk profile to arbitrary subjects.

## 3. Factory request contract (target, not current schema)

Keep the existing output_class enum, existing CLI behavior, and six MCP tool names/argument schemas compatible until an independently reviewed migration. Introduce a **versioned factory orchestration envelope**, mapped onto the current validated Asset Brief only after implementation.

~~~yaml
factory_contract_version: 1
factory_line: NONPIXEL                 # NONPIXEL | REFERENCE_MOTION | SFX | PIXEL64
output_mode: IMAGE_ONLY                # IMAGE_ONLY | IMAGE_TO_SPRITE | AUDIO_ONLY
project_id: game_a
asset_id: scout_idle
source:
  kind: GENERATE                      # GENERATE | EXISTING_RUN | EXTERNAL_IMAGES
  brief_ref: path/to/validated_brief.json
  images: []                          # reference motion: 1..3 explicit image references
image:
  style_source: project_active_sot
motion: null                          # MUST be absent/null in IMAGE_ONLY / AUDIO_ONLY
audio: null
authorization:
  generation_budget: explicit_when_needed
  approval_source: explicit_when_needed
~~~

Rules:

- A allows IMAGE_ONLY or IMAGE_TO_SPRITE with source kind GENERATE or EXISTING_RUN. If generating and continuing, keep separate source and motion run identities.
- D allows IMAGE_ONLY or IMAGE_TO_SPRITE, with output logical master **64x64** and explicit pixel/identity quality gates. A 1024px generation canvas is not a 1024px logical sprite.
- B allows IMAGE_TO_SPRITE only; source kind EXTERNAL_IMAGES or EXISTING_RUN; exact image count **1..3**. Reference role and source order are explicit, not guessed.
- C allows AUDIO_ONLY only; route to the existing SFX pipeline. No video, sprite, palette, or image generation calls.
- IMAGE_ONLY must not allocate a video provider, reserve video budget, check video nodes, or run an extractor.
- Legacy Briefs without factory envelope continue using existing output_class routing and semantics. Existing PIXEL_ANIMATION/NONPIXEL_ANIMATION routes are not silently reinterpreted.
- New envelope fields are **proposals**, not supported by current schema/CLI/MCP yet. Do not send them to current production APIs before a versioned validator is implemented.

### Multi-image source roles (B)

~~~yaml
factory_line: REFERENCE_MOTION
output_mode: IMAGE_TO_SPRITE
source:
  kind: EXTERNAL_IMAGES
  images:
    - path: assets/scout_front.png
      role: IDENTITY_PRIMARY
    - path: assets/scout_side.png
      role: ALTERNATE_VIEW
    - path: assets/scout_raised_weapon.png
      role: POSE_ANCHOR
motion:
  action: attack
  fps: 12
  duration_seconds: 1.5
  target_frames: 8
  background_policy: PRESERVE_OR_REVIEW
~~~

Allowed documented roles should include IDENTITY_PRIMARY, ALTERNATE_VIEW, POSE_ANCHOR, START_FRAME, END_FRAME and STYLE_REFERENCE. The chosen video adapter must explicitly declare which role combinations and count it supports. Multiple views, multiple keyframes, and independent references are **not interchangeable**. Do not pass three images to a one-image workflow and silently drop two; block with UNSUPPORTED_REFERENCE_CONTRACT unless a separately validated conditioning transform exists. The sample values above are illustrative and not approved animation parameters.

## 4. Atomic run / artifact boundaries

- **Image run**: source SOT fingerprint, brief, style/model/workflow, original, transformations, image QA, image review, immutable manifest, file SHA-256.
- **Motion run**: new run ID referencing the image run ID or 1..3 external image hashes and their roles; own provider, video, frame extraction, sprite QA, human review, manifest.
- **SFX run**: own audio source/generation, original FLAC, derived WAV, audio QA, listening review and manifest.
- Motion failure changes **motion** status only. Parent image state and original file hashes remain unchanged. Resume must reference the exact recorded image and approved permissions, not reconstruct from a filename.
- Reusing a still image later is first-class continuation; it never re-runs still-image generation by default.
- Any new paid dispatch is a separate, durable, approved, one-attempt budget reservation. No fallback/retry/duplicate charge on ambiguous failure.
- Raw inputs, originals, source hashes, provider execution logs (redacted), derived images, frames, final sheets, atlas data and review results remain distinguishable.
- Exported sprite package must declare frame order, dimensions, FPS/step durations, pivot/origin, source-frame index, layout, animation action and transparency policy. Do not claim semantic correctness from metadata alone.

Suggested per-project layout (conceptual; retain existing canonical workspace paths during compatibility migration):

~~~text
<configured_output_root>/<project_id>/runs/<asset_id>/
  <image_run_id>/run_manifest.json
  <motion_run_id>/run_manifest.json      # source_run_id -> image_run_id
  <sfx_run_id>/run_manifest.json
~~~

## 5. Gates and fail-closed behavior

| Boundary | Technical check | Human judgment remains |
| --- | --- | --- |
| SOT -> Brief | explicit source, no invented canon, route/registry compatibility | identity / aesthetics |
| IMAGE_ONLY nonpixel | output existence, hash, resolution, aspect/transparency contract | composition / subject / forbidden details |
| IMAGE_ONLY pixel64 | true 64x64 logical size, palette/cluster/pixel QA, Aseprite roundtrip | equipment, silhouette and artistic fitness |
| B import 1..3 | count, role, image format, hashes, containment, ownership/license declarations, provider capability | whether refs describe compatible character/scene |
| I2V dispatch | model/node presence, conditioning support, required parameters, queue and paid budget | motion plausibility |
| Video -> frames | FFmpeg decode, frame continuity/size/count, hash, selection provenance | identity/camera/pose consistency |
| Frames -> sprites | size, alpha, non-clipped silhouettes, temporal alignment, layout/metadata | visually coherent loop/attack/idle |
| Pixel64 motion | all sprite frames pass pixel, palette and logical-resolution gates; review any remapping | pixel shimmer and semantic preservation |
| SFX | duration, decoded PCM, peak/RMS/clipping, source hash | listen for intended event and unwanted voice/music |
| Release | exact package hashes, user approval, license/provenance review | actual game-context fit |

Do **not** mistake basic image QA, sprite metadata checks, or exact RGBA fixture regression for production-quality approval. Never automatically write human_approval, Static Master, Golden, game_ready or SOT updates.

## 6. Security and rollout compatibility

- Observe existing **source_roots / output_root containment**, path/symlink/junction checks, provider session-output correlation, credential isolation, recursion blocking and no global CLI output fallback.
- Imported external images may contain unrelated user data; stage only authorized files and preserve source provenance. Never expose project files to a subprocess merely to feed a reference PNG.
- MCP stays at **exactly six tools** initially. Internal routing may gain factory concepts behind a compatible adapter; modifying advertised contracts requires its own contract-version and host-compatibility gate.
- Do not change the live pinned MCP runtime when merging a design or a code PR. Deployment requires independently reviewed runtime provenance, quiescence, backup, smoke and rollback authorization.
- Model/video backend is **UNSELECTED / NOT_YET_VERIFIED**. Verify the local ComfyUI workflows, installed models and true 1/2/3-image conditioning before choosing or promoting any motion provider. Do not infer capability from a filename.
- The old experimental NONPIXEL_ANIMATION stub and historical PIXEL_ANIMATION reviewed-walk path stay intact until new E2E evidence supports an explicit replacement.

## 7. Product success criterion

A factory line is complete when a **real representative request**, from accepted source to its **requested terminal output**, produces independently auditable artifacts, passes technical gates, and is submitted for the required human review. To claim game-ready/production-ready, also record explicit human and in-game approval. Implemented code, route PASS, or CI alone is not production completion.

See [M3 execution workplan](M3_FACTORY_WORKPLAN.md) for dependencies, file-level changes, tests and stop conditions.
