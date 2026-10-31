# Changelog

## Unreleased — motion export names per action, 2026-10-31

- Name Godot/Phaser motion exports from the request: `<action>.tres` and Phaser key
  `<asset_id>_<action>` (recorded in `placement.json`), so several actions no longer collide.

## Unreleased — Aseprite output decoding, 2026-10-31

- Decode Aseprite output as UTF-8 with replacement so non-ASCII (e.g. Korean) paths on
  Windows code pages raise the coded Aseprite error path instead of UnicodeDecodeError.

## Unreleased — run status after lost processes, 2026-10-31

- MCP inspection reports FAILED when the generation process exited while its manifest was RUNNING;
  ComfyUI waits fail fast when a prompt is neither queued nor in history.

## Unreleased — low-severity hardening, 2026-10-31

- Report a hung `codex login status` as UNAVAILABLE, not logged out; require factory statuses to
  end in `REVIEW_REQUIRED`; publish listening/style reviews atomically; keep ACTIVE CLI evidence
  inside the repository root.

## Unreleased — motion timing on millisecond containers, 2026-10-31

- Accept constant-rate WebM/MKV motion clips whose timestamps are rounded to the container
  timebase (e.g. 24/30 fps at 1 ms); real frame-interval jitter is still rejected.

## Unreleased — routing and contract gate fixes, 2026-10-31

- Reject attached short CLI options (`-sVALUE`, `-C/tmp`) in registry `cli_args`; check
  equipment `subject_side`/`location` against the source trait even without `visible_count`;
  return PromptSpec schema errors as BLOCKED; record model_profile-based selection as explicit.

## Unreleased — paid-run record preservation, 2026-10-31

- Keep provider/factory records after a generation request was sent: validate variant/factory
  result inputs with the planned allowed roots, parse full CLI output (trim logs only), copy
  orphan outputs into the run, record unexpected post-run errors, check ComfyUI output folders
  before queueing, never leave `generation.json` RUNNING, and record motion child receipts first.

## Unreleased — BGM output class offline contract, 2026-10-30

- Add `BGM` (`create --type bgm`, `bgm-review`) on an EXPERIMENTAL ComfyUI YuE2 workflow
  validated against captured `object_info`: instrumental/loop defaults, duration/clipping/loudness
  QA, whole-file loop point and seam check, explicit listening review. Zero generations run.

## Unreleased — Factory CLI provider provenance, 2026-10-30

- Fix `factory execute` marking successful Codex/Grok candidates FAILED after generation:
  only the provider's original save location (`source_path`) is exempt from root checks.
  Identity variants reuse the same check instead of skipping manifest validation.

## Unreleased — project identity edits and alpha delivery, 2026-10-30

- Add explicit Grok/Codex project reference edits with exact RGBA input, pinned SOT,
  fixed preserve lists, one-attempt execution and local portrait alpha delivery.
- Preserve opaque RGB and verify neutral source backdrops; reject injected image
  arguments and mismatched edit tools. Record real edits and per-output user identity
  acceptance while keeping final art/Golden/Aseprite approval separate.

## Unreleased — same-character expression/pose variants, 2026-10-28

- Add `factory variant-plan/variant-run`: one selected NONPIXEL_IMAGE base, explicit reference-edit
  provider, fixed preserve lists, one authorized attempt in the shared Factory budget. Fake-CLI tests only;
  no real generation. Grok is the only registered edit path; Codex and AGY remain follow-up steps.

## Unreleased — explicit nonpixel motion through create, 2026-10-27

- Connect `create --type nonpixel-animation --motion-job` and the core create API
  to the existing Factory motion coordinator, pinned plan and original budget gates.
- Reject mixed direct overrides, missing job/plan/output and replay generation
  consent before dispatch; keep parent stills and terminal failure evidence intact.
- Preserve prompt/brief-only blocking, default research settings, still/SFX paths,
  six MCP arguments and all review/activation gates. No new live generation authorized.

## Unreleased — nonpixel production priority, 2026-10-27

- Apply the user's decision to prioritize nonpixel still images and animation;
  defer pixel production work to research without deleting existing paths.
- Reconcile the Factory index with implemented explicit motion jobs and dated
  replay/engine evidence. Record remaining entrypoint, quality, game integration
  and separately authorized generation gates. No runtime/default changes.

## Unreleased — existing-image Pixel64 postprocessing A/B, 2026-10-27

- Compare two archived raw images through existing Refiner orders and isolated
  Pixel Art Fixer defaults; re-evaluate eight outputs with the unchanged Gate.
- Record correct automatic 64px detection but 879/853-color external outputs
  failing the 24-color Gate. Do not promote or add automatic postprocessing.
- Preserve zero-change Safe Refiner results, historical CPU replay differences,
  all 104 archive files and explicit review/adapter limitations. Zero generations.

## Unreleased — Pixel64 loader candidate isolation, 2026-10-27

- Execute reviewed InvokeAI grouping/value conversion on the unchanged adapter:
  retain all 120 magnitudes without installing a provider or inferring alpha.
- Compare extracted weight/parameter methods with the pinned ai-toolkit forward:
  54 synthetic CPU cases, 24 within tolerance and 30 different. Record full-strength
  FP32 agreement separately from fractional-strength and BF16 differences.
- Keep candidate adoption blocked; add static-only RunComfy A/B merge inspection.
  Production code, installed loaders, defaults, generation and reviews unchanged.

## Unreleased — Pixel64 distribution/export provenance, 2026-10-27

- Confirm local LoRA full-file hash/size against publisher HF revision and Civitai
  version. Preserve bounded missing-training/config evidence and sample workflow
  widget/download-hint disagreement without installing models or adopting defaults.
- Execute pinned official parser functions with ten byte-identical dependencies:
  120 A/B patches and 120 unloaded magnitude keys; no installed-loader patch.
- Record evidence in docs/research/KREA2_PIXEL64_PROVENANCE_20261027.md/json.
  Production code/config, generation, approval and compatibility state stay unchanged.

## Unreleased — bounded Pixel64 CUDA base compatibility probe, 2026-10-27

- Add explicit CUDA base-projection mode to the existing loader diagnostic;
  keep CPU default and reject GPU use of the CPU-only LoRA hypothesis.
- Execute eight native CUDA input cases across two real FP8 projections with
  unchanged state/flags; reproduce all 24 prior CPU hybrid case records exactly.
- Preserve INCOMPLETE_ADAPTER: 120 magnitude keys remain unloaded. No image
  generation, GPU LoRA/full-model approval, checkpoint or production activation.
- See docs/research/KREA2_GPU_BASE_20261027.md for evidence, limits and rollback.
- Complete required install/CLI and 778 offline tests with one unavailable-data
  skip; GPU base checks do not promote the incomplete LoRA or certify image quality.

## Unreleased — explicit Factory motion jobs, 2026-10-27

- Add additive Factory motion prepare/plan/run/inspect commands, binding request,
  video/prepared inputs and explicit v1/v2 recipes. Reuse the existing package,
  recipe, root/hash and single-attempt generation gates; no default activation.
- Export native Godot SpriteFrames and Phaser atlas/animation resources with
  exact sprite bytes, original frame lineage and pivot placement metadata.
- Replay existing fox/rabbit videos through the installed CLI with exact 20/28
  RGBA results, then consume both native exports in actual engines. Zero new
  generation requests; all candidates remain REVIEW_REQUIRED.
- See docs/factory/MOTION_JOB.md and MOTION_JOB_VALIDATION_20261027.md for scope,
  checks, remaining blocks and rollback.
- Validate required install/CLI checks and 772 offline tests passed with one
  unavailable-data skip; preserve 725 existing source/candidate/evidence files.

## Unreleased — Godot diagnostic startup scheduling, 2026-10-27

- Reproduce early animation wrap caused by pre-start work/current-frame delta
  in the isolated harness. Preserve raw failing control evidence.
- Add a 60Hz validation fixture that waits for stable process/wall intervals,
  starts after animation processing and avoids readback while measuring playback.
- Verify six guarded conditions in headless and actual OpenGL against a declared
  ±22ms cycle tolerance, preserving source assets and production game runtime.
- See docs/factory/GODOT_STARTUP_TIMING_20261027.md for measurements and limits.
- Complete required install/CLI checks and 756 offline tests (one unavailable-data
  skip); verify fail-closed native controls and 241 unchanged source/candidate hashes.

## Unreleased — actual rabbit Godot/Phaser import, 2026-10-27

- Reuse isolated native engine fixtures for the rabbit's 28-frame RGBA candidate.
  Execute actual imports, three playback loops, 56 native rendered captures and
  frame/pivot/readback checks; preserve all 241 source/candidate file hashes.
- Measure a 1..2 screen-pixel boot-bottom/baseline gap on both backgrounds.
  Keep anatomical foot contact and Godot's shortened first-cycle timing open.
- Document evidence and rollback in docs/factory/RABBIT_ENGINE_IMPORT_20261027.md.
  No production source/config change, generation or human/Golden approval.

## Unreleased — rabbit-specific offline loop and alpha recipe, 2026-10-27

- Add optional v2 recipe white-distance input (explicit integer 0..60) while
  preserving fixed v1 behavior and reusing the verified connected-border utility.
  Keep source RGB, alpha monotonicity, provenance and all review gates.
- Reject the rabbit's destructive distance-60 mask. Select source frames 14..41
  and explicit distance 32 after comparison; preserve original frames and failed
  analysis. No generation, inferred cleanup regions or automatic approval.
- See docs/factory/RABBIT_MOTION_RECIPE_20261027.md for evidence and rollback.
- Validate with 756 offline tests passed, one unavailable-data skip, actual
  rabbit v2 and fox v1 CLI replays, 122 source hashes and exact APNG roundtrip.

## Unreleased — source style semantics for motion research, 2026-10-27

- Revalidate styled references against their original still workflow and exact
  historical compilation before deriving natural-language video instructions.
  Preserve style contracts, subject/camera context and source provenance.
- Reject source drift, unsupported capabilities and overrides. Bind shared
  compiler code to the existing one-request research plan. Keep production
  dispatch, six MCP contracts and human/Golden gates unchanged.
- Complete the already authorized rabbit video once: 56 frames at 24fps,
  original/graph/history retained, five package output hashes verified and
  research configuration restored. Rabbit loop/alpha/engine/art review remains pending.
- Validate with 750 offline tests passed, one unavailable migration-data skip,
  and the required editable install/CLI checks.
- See docs/factory/MOTION_SOURCE_STYLE_20261027.md for execution evidence,
  limitations and rollback.

## Unreleased — second-character source and motion blocker, 2026-10-27

- Generate one user-requested white-rabbit reference through the existing six-tool
  Asset Pipeline route; preserve technical QA, actual framing/pose discrepancies
  and pending art review. No repair generation or provider fallback.
- Reproduce STYLE-107 still-workflow binding conflict in the existing motion plan.
  Preserve the style lock and stop before video upload/budget/queue; no second-character E2E PASS.
- Record the explicit motion-style compiler integration gap without production
  code/config changes. See docs/factory/MOTION_SECOND_CHARACTER_20261027.md.

## Unreleased — explicit offline motion review recipes, 2026-10-27

- Add versioned recipe schema and plan/apply/inspect CLI for explicit contiguous
  frame selection, preserved or declared white alpha and local cleanup regions.
- Bind source/code/parameters to a plan hash; preserve intermediates, source
  lineage, failure receipts and separate pending review stages. No generation,
  retry, inferred selection, approval API or production/MCP changes.
- Share existing bounded atlas packing with the video package; retain verified
  algorithms. Replay the real fox asset through installed CLI with all 20 RGBA
  frames matching manual cleanup. See docs/factory/MOTION_REVIEW_RECIPE.md.

## Unreleased — real Godot / Phaser import checks, 2026-10-27

- Import the unchanged 20-frame RGBA candidate into isolated Godot 4.7.2 and
  Phaser 4.2.1 projects; exercise actual native animation/resource/origin APIs.
- Capture real Godot OpenGL and Chromium WebGL renders, verify frame order,
  steady loops and visible imported pixels. Preserve startup-timing limitations.
- Documentation/evidence only; no production/runtime/asset/approval changes.
  See docs/factory/MOTION_ENGINE_IMPORT_20261027.md for methods and remaining gates.

## Unreleased — requested leg-gap and ground cleanup, 2026-10-27

- Make a separate alpha-only candidate removing pale lower-body matte and ground
  remnants in explicit regions; preserve RGB, dark boot cores, timing and pivots.
- Verify all 20 atlas/APNG frames, unchanged source hashes and untouched review
  state. No generation or runtime changes; see docs/factory/MOTION_ALPHA_CLEANUP_20261027.md.

## Unreleased — explicit motion alpha comparisons, 2026-10-27

- Reuse existing local U2NetP and edge-connected white-mask primitives on separate
  copies of the 20-frame loop. Retain masks, RGBA atlases and true-alpha previews.
- Reject the learned mask for white-feature alpha loss; keep the border mask as
  NEEDS_CLEANUP for bright fringe and residual shadow. No quality PASS or fallback.
- Verify RGB/source/timing preservation and decoded APNG frames; leave runtime,
  configuration and human approval unchanged. See docs/factory/MOTION_ALPHA_CANDIDATE_20261027.md.

## Unreleased — derived fox loop candidate, 2026-10-27

- Extract original frames 13..32 as a separate 20-frame/24fps candidate; preserve
  full source lineage and reuse FFV1 plus existing offline motion packaging.
- Verify every raw/aligned pixel, atlas cell, timing and pivot against source;
  record endpoint RGB change without treating it as animation approval.
- Keep original artifacts and human review unchanged; no generation or runtime
  changes. See docs/factory/MOTION_LOOP_CANDIDATE_20261027.md.

## Unreleased — advisory review of existing fox motion, 2026-10-26

- Inspect all 56 preserved frames, loop boundary and top-border contacts; reuse
  existing motion metric/cycle proxies without editing verified algorithms.
- Record loop/headroom/anchor correction priorities and produce separate review
  previews. Preserve 119 artifact hashes and untouched human review state.
- No generation, asset correction, runtime/config change or approval. See
  docs/factory/MOTION_ADVISORY_REVIEW_20261026.md for measurements and limitations.

## Unreleased — one authorized real motion E2E, 2026-10-26

- Run the existing single-reference research executor once after explicit user
  approval: 512x512, 56 frames at 24fps, seed 7725. One reservation/upload/queue
  submission, zero retries; server history exactly matches the submitted graph.
- Preserve original MP4, decoded/raw/aligned frames, 4096x3584 sprite atlas,
  timing/pivots and untouched review package; verify hashes and all atlas cells.
- Restore temporary research configuration byte-for-byte after execution and
  preserve source hashes. No runtime code or production activation changes.
  Candidate remains REVIEW_REQUIRED; see docs/factory/MOTION_REAL_E2E_20261026.md.

## Unreleased — motion pre-generation evidence, 2026-10-26

- Reuse existing preparation, inspection and execution-plan CLI/API with one real
  existing nonpixel candidate; freeze a 512x512/56-frame/24fps/seed-7725 plan.
- Recheck 15 live node schemas, 5 server-listed model names, selected graph inputs
  and SHA-256 of 43.84 GB of local weights. Preserve source bytes and review state.
- Documentation/evidence only: no runtime/config change, authorization, upload,
  queue submission, generation or budget reservation. See
  docs/factory/MOTION_LIVE_PLAN_20261026.md for hashes and remaining gates.

## Unreleased — independent JSON staging, 2026-10-26

- Exclusively create a same-directory temporary file for each manifest write,
  eliminating collisions through the previously shared `.json.tmp` path.
- Serialize short publication calls within the process; distinct sources alone
  still reproduced Windows error 5 under simultaneous replacement.
- Preserve single-attempt atomic replacement, failed staging evidence and previous
  target bytes on denial. No provider/file-publication retries or gate changes.
- Add concurrent publication and real Windows share-delete lock regressions.
  See docs/maintenance/MANIFEST_STAGING_20261026.md for evidence and limits.

## Unreleased — isolated native-FP8 LoRA hypothesis, 2026-10-25

- Extend existing research diagnostics with explicit alpha/source guards and a
  native base-forward callback, preserving dense mode and native quantization flags.
- Exercise real A/B/magnitude values on two actual FP8 projections: 24 exact
  controlled-hybrid comparisons, zero-strength noops and magnitude sensitivity.
- Check native quantized state, input/weight immutability and source/file hashes.
  Reject blocked/mismatched requested probes with exit 2 and preserve evidence.
- No full model integration, installed loader patch, generation or quality claim.
  See docs/research/KREA2_FP8_LORA_ISOLATION_20261025.md.

## Unreleased — unique advisory review directories, 2026-10-25

- Allocate each visual review a UUID directory and retain the clock value as
  `created_at`, so identical timestamps cannot collide on the output directory.
- Preserve source bytes, review/approval state and existing artifacts. Add a
  frozen-clock regression to the existing review-preservation test; no retries
  or generation changes. See docs/maintenance/REVIEW_DIRECTORY_COLLISION_20261025.md.

## Unreleased — Windows Factory reservation namespace race, 2026-10-25

- Fix false configured-root rejection when concurrent directory creation leaves
  an extended Windows prefix on an otherwise equivalent resolved budget path.
- Keep filesystem resolution first, existing successful spellings, configured
  roots, atomic reservation and provider retry behavior unchanged. Restrict
  alias comparison to ordinary DOS/UNC semantics; retain special namespaces.
- Add deterministic budget/reservation alias injection and boundary regression
  tests, including existing/missing symlink and junction escape paths.
  See docs/maintenance/FACTORY_ROOT_NAMESPACE_RACE_20261025.md.

## Unreleased — Krea2 actual base contract probe, 2026-10-25

- Extend the existing loader diagnostic with optional workflow-bound base hashing,
  header/meta-device Krea2 detection and installed native key mapping.
- Verify all 120 actual adapter targets' shapes and FP8 scale metadata. Reproduce
  120 unloaded magnitude keys with that base-derived map; no complete adapter PASS.
- Opt in to two actual base-only FP8 projection loads/dequantizations/CPU forwards;
  preserve native layer flags and report quantized-vs-dense differences explicitly.
- Record conditional PEFT alpha=rank source evidence without inventing authored
  configuration or raw/Turbo base equivalence. Production remains BLOCKED.
  See docs/research/KREA2_BASE_CONTRACT_20261025.md.

## Unreleased — Krea2 ordered dense inference candidate, 2026-10-25

- Extend the existing offline diagnostic with an explicit ordered forward that
  preserves low-rank, scale, normalization, correction and addition ordering.
- Match pinned upstream dense CPU outputs exactly in 960 FP64/FP32/BF16 cases;
  reject twelve unsupported-input cases and verify input tensors are unchanged.
- Keep the old merged candidate and its BF16 failure as a counterexample. Keep
  actual weights, FP8/quantized integration and production compatibility blocked.
- No generation, weight conversion, installed patch or CLI/MCP change. See
  docs/research/KREA2_DORA_ORDERED_20261025.md.

## Unreleased — Krea2 DoRA numeric candidate, 2026-10-25

- Pin a public ai-toolkit commit declaring 0.12.9 and hash-check the inspected
  version interval; the exact author's training checkout remains unverified.
- Add an isolated dense CPU merge candidate and execute pinned upstream method
  bodies on 216 synthetic fixtures, plus eight unsupported-input rejections.
- FP32/FP64 meet the stated tolerances; all 48 nonzero BF16 cases mismatch.
  Exit 2 records that blocked diagnostic instead of reporting full compatibility.
- Preserve production code, weights, workflows, installed loaders and review
  gates. No image generation or model-quality improvement is claimed.
  See docs/research/KREA2_DORA_NUMERIC_20261025.md.

## Unreleased — Krea2 Pixel64 loader audit, 2026-10-25

- Reproduce incomplete parsing with the installed CPU loader: 240 A/B tensors
  consumed, 120 magnitude tensors unloaded, 120 patches without DoRA scale.
- Add a read-only diagnostic and regression coverage preventing partial parser
  results from being called full model compatibility. Record source/weight hashes.
- Document shape and normalization differences that prevent a blind key rename;
  no weights, installed loader, workflow defaults or review gates are changed.
- Generation and image-quality comparison remain NOT_RUN / NOT_MEASURED.
  See docs/research/KREA2_LOADER_COMPATIBILITY_20261025.md.

## Unreleased — single-reference motion research executor, 2026-10-24

- Connect one existing nonpixel parent through the shared prompt compiler,
  explicit ComfyUI workflow, original-video preservation and existing sprite packer.
- Require exact plan-bound one-request probe consent, all configured weight
  hashes, live schema/inventory gates and a durable root-scoped reservation.
- Correlate upload, submitted/history graph and video prefix; preserve failures,
  block retries and revalidate sources after generation and packing.
- Add an explicit natural-language research profile without replacing still/SFX
  defaults. Research execution stays disabled, workflow stays EXPERIMENTAL and
  no real model generation or reference-semantic approval is claimed.

## Unreleased — video preflight and prepared inputs, 2026-10-23

- Add read-only motion preflight with explicit registered workflow, source,
  timing, compiler-profile and optional local installation checks.
- Preserve all ordered reference images and configuration fingerprints in a
  fresh research directory; reject source/configuration/copy/review-state drift.
- Keep PREPARED_BLOCKED, zero uploads/dispatches/reservations and unchanged six
  MCP contracts. Actual generation adapter, role-consumption proof and real I2V
  E2E are still pending. No deleted experimental executor is restored.

## Unreleased — M3 audit and offline motion packaging, 2026-10-23

- Re-audit M3.0–M3.6 against main 4320bf864add; distinguish implementation,
  offline checks, historical generation and outstanding real E2E gates.
- Add an explicit existing-video research package command reusing the decoder,
  extractor, alignment, source validation and manifest writer. Preserve original
  video, chronological frames, FPS, pivots and review-required atlas outputs.
- Add read-only local LoRA/header/loader and ComfyUI inventory evidence collection.
  No provider dispatch, model installation, runtime switch or approval is added.
- Actual I2V generation, alpha removal, Pixel64 comparison and game-engine imports
  remain blocked or not run. See docs/factory/M3_REAUDIT_20261023.md and
  docs/factory/M3_OFFLINE_VALIDATION_20261023.md for evidence and limits.
