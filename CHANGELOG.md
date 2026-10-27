# Changelog

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
