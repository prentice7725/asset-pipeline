# Changelog

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
