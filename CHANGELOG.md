# Changelog

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
