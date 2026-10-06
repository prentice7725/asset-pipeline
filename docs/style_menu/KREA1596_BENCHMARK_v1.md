# Krea1596 24-style / 3-model / 3-seed comparison

Cohort: `KREA1596_24X3X3_20261006`. Budget: exactly 216 reserved opportunities, retry 0, fallback 0.

- Research source: ThetaCursed Explorer commit `eb690aa57bc6974af6b4b3b8c5a780195bcadf78`.
- All 1,596 source records were read and matched against classification IDs; all 24 shortlist entries are KEEP_BASE_STYLE and their folder/preview paths match pinned source records.
- Candidate IDs CAND-001..024 map to separate catalog contracts STYLE-101..124; existing STYLE-001/004 and R1/R2/R3 evidence remain unchanged.
- Same completed synthetic FRONT traveler fixture, 512x768, seeds 7725/7726/7727 across all models. One brass compass in anatomical left hand (image right); blue knee-length coat, trousers, dark closed shoes and complete head-to-toe framing.
- Anima Base-rebuilt: 30 steps, CFG 4, er_sde/simple. Anima Turbo v1.1: 10 steps, CFG 1, euler/simple. Krea2 Turbo: existing fp8_scaled checkpoint/encoder, 8 steps, CFG 1, euler/simple. No LoRA, checkpoint/encoder/VAE change or resolution sweep.
- Both Anima profiles use the existing quality-tag plus structured-caption compiler. Krea uses structured prose and exclusion instructions. Krea has no native negative conditioning; instructions are not guarantees. No hand-written completed prompt or prompt enhancement.
- Native style source camera, clothing, extra subjects and skeletal motifs do not override fixture. Monochrome styles retain a blue-coat exception; voxel uses FRONT instead of the source isometric camera. These are documented transfer limitations.
- Three different seeds measure variation consistency/seed robustness. Exact same-seed rerun repeatability stays NOT_MEASURED; equal integer seeds across distinct models do not imply equivalent noise.
- Preserve original PNG, SHA256, manifest, generation.json, compiled_prompt.json, workflow.json and route decision for each attempted cell. Durable reservation precedes dispatch; failed execution/QA gate stops the cohort without retry.
- Review style fidelity and fixture compliance separately. Known R3 failures (compass anatomical side, unintended extra people, unreadable face, weak figure gouache) remain evaluation criteria. No model winner is inferred from offline compilation or image QA.
- All outputs REVIEW_REQUIRED; no Golden, project SOT or automatic model preference updates. Preview URLs remain source links; no Explorer image redistribution or production/commercial license approval is claimed.

Artifacts: `workspace/style_menu/krea1596/plan.json`, `preflight.json`, `source_audit.json`; actual cohort under `workspace/style_menu/experiments/KREA1596_24X3X3_20261006`.


## Actual local execution result

2026-10-06 cohort KREA1596_24X3X3_20261006 completed 216/216 calls, 0 execution failures and 0 retries. All 216 originals were hash-verified and visually reviewed. Advisory preferences: Krea2 Turbo 11 styles, HOLD 13; all REVIEW_REQUIRED. Same-seed repeatability NOT_MEASURED. No production or Golden approval.

Local artifacts: `workspace/style_menu/experiments/KREA1596_24X3X3_20261006/validation_report.md`, `comparison_card.md`, `model_menu_review_required.json`, `image_inventory.json`, `execution_audit.json`, `local_checks.json`. Source shortlist remains historical; measured menu is separate. Full pytest 332 passed/1 skipped (unavailable local migration benchmark), CLI help, Anima offline check and git diff --check passed.
