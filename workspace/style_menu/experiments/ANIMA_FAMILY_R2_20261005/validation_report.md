# Anima Family R2 — R1/R2 actual-image review

**Cohort:** ANIMA_FAMILY_R2_20261005 · **State:** REVIEW_REQUIRED · **Golden:** not approved · **Production recommendation:** none

[R1 → R2 comparison card](comparison_card.png) · [R2 plan](../../anima_family_r2/plan.json) · [model preflight](../../anima_family_r2/preflight.json) · [live preflight](../../anima_family_r2/live_preflight.json) · [R2 results](results.json) · [fresh R2 reservation](reservation.json) · [hash and artifact inventory](image_inventory.json) · [model hashes](model_hashes.json)

## Execution

- Fetched origin and used branch feat/anima-family-pipeline-v1 at requested HEAD d4f984efd1c4c7c1378405b5237db266da0c15b2. R1 evidence is kept in its original cohort directory from commit 267529838ab989c58868277f1a850fb963468eb4.
- Read docs/style_menu/ANIMA_FAMILY_PIPELINE_v1.md, GitHub Issue #8, scripts/anima_family_pipeline.py, config/model_profiles.yaml, config/workflow_registry.yaml, and config/style_menu/nonpixel_prompt_research_v0.yaml before dispatch.
- Pipeline check passed; the plan contains exactly STYLE-001/STYLE-004 × anima_base_rebuilt/anima_turbo, cohort ANIMA_FAMILY_R2_20261005, seed 7725 and zero pixel/LoRA/VAE changes. PromptSpec was compiled by anima_hybrid_v2. No final prompt was manually rewritten.
- ComfyUI live preflight passed immediately before dispatch: version 0.38.2, queue 0/0, RTX 5060 Laptop, all eight workflow node classes present and all expected model names available in loaders. The runner created a separate four-call R2 reservation; R1's consumed reservation was not reused.
- Four calls attempted/completed, failures 0, retries 0. All four output PNGs are 512×768 and pass basic image QA. Each R2 cell preserves original PNG, SHA-256, run_manifest.json, generation.json, compiled_prompt.json, workflow.json and route_decision.json; their per-file hashes are in the inventory.
- One sample per cell: repeatability remains NOT_MEASURED. Semantic, anatomy and art judgment below is direct visual review, not automated approval.

## Model hash preflight against R1

All four model files were present and matched their R1 SHA-256 at preflight and immediate pre-dispatch recheck. Any changed hash would have blocked dispatch.

| Model file | Bytes | SHA-256 | R1 comparison |
|---|---:|---|---|
| anima-base-v1.0.safetensors | 4182218328 | bd43b7cffe1ed1153d9c41e7beb2f18cb1273eafbaa3af3edd6a173dc90a006e | MATCH |
| anima-turbo-v1.1.safetensors | 4182230656 | fba11953276b57edf59d1dc4f1857ac05aa079c56f982b4d7c20298d57d3f7eb | MATCH |
| qwen_3_06b_base.safetensors | 1192135096 | cd2a512003e2f9f3cd3c32a9c3573f820bb28c940f73c57b1ddaa983d9223eba | MATCH |
| qwen_image_vae.safetensors | 253806246 | a70580f0213e67967ee9c95f05bb400e8fb08307e017a924bf3441223e023d1f | MATCH |

No checkpoint, encoder, VAE, LoRA, quantization, workflow or resolution substitution was made. Base-rebuilt remained 30 steps / CFG 4 / er_sde-simple; Turbo remained 10 / CFG 1 / euler-simple. Seed 7725 remained fixed.

## R2 originals

| Cell | Model | steps / CFG / sampler | Comfy prompt ID | Workflow SHA-256 | Original PNG SHA-256 | Preserved original / manifest |
|---|---|---:|---|---|---|---|
| STYLE-001_anima_base_rebuilt | anima-base-v1.0.safetensors | 30 / 4.0 / er_sde | e3c63717-12cc-4da1-bc0d-734ea19cc735 | fa645baddd1f50ccc983a745339bb478d43ee69c7e993322f4eb5536f6744ac8 | e734eed2f49cf77b8420039ddb980d83c9e62a784c25f5cf5156cdc54c6bf717 | [PNG](workspace/style_menu/experiments/ANIMA_FAMILY_R2_20261005/runs/STYLE-001_anima_base_rebuilt/010_generation/001_STYLE_001_anima_base_rebuilt_r2_00001_.png) · [manifest](workspace/style_menu/experiments/ANIMA_FAMILY_R2_20261005/runs/STYLE-001_anima_base_rebuilt/run_manifest.json) |
| STYLE-001_anima_turbo | anima-turbo-v1.1.safetensors | 10 / 1.0 / euler | 946cb8de-3c3f-414e-b6fa-e9c9d12cbe7c | 34c66b56e2e8ac7b911d7e99ea6c4fb4f2400b28dc607800fd40a5b477b69319 | 125236a03328582fd6a8e8b84440a280633cfc3c6413156d0f211fb706111475 | [PNG](workspace/style_menu/experiments/ANIMA_FAMILY_R2_20261005/runs/STYLE-001_anima_turbo/010_generation/001_STYLE_001_anima_turbo_r2_00001_.png) · [manifest](workspace/style_menu/experiments/ANIMA_FAMILY_R2_20261005/runs/STYLE-001_anima_turbo/run_manifest.json) |
| STYLE-004_anima_base_rebuilt | anima-base-v1.0.safetensors | 30 / 4.0 / er_sde | d3522770-7e12-4af7-bac7-b5d38dd1a528 | fa645baddd1f50ccc983a745339bb478d43ee69c7e993322f4eb5536f6744ac8 | ddd11fc37b65040ba4b37b735406d4dc71330f9d694c9632325ad4a8bf4b2f4d | [PNG](workspace/style_menu/experiments/ANIMA_FAMILY_R2_20261005/runs/STYLE-004_anima_base_rebuilt/010_generation/001_STYLE_004_anima_base_rebuilt_r2_00001_.png) · [manifest](workspace/style_menu/experiments/ANIMA_FAMILY_R2_20261005/runs/STYLE-004_anima_base_rebuilt/run_manifest.json) |
| STYLE-004_anima_turbo | anima-turbo-v1.1.safetensors | 10 / 1.0 / euler | 6ed7022c-1659-4494-b7cb-30ac5d732b3f | 34c66b56e2e8ac7b911d7e99ea6c4fb4f2400b28dc607800fd40a5b477b69319 | e95028703309fa63e4434d6f454ac49a22059d91ff1b0904881a2105bb34f7e7 | [PNG](workspace/style_menu/experiments/ANIMA_FAMILY_R2_20261005/runs/STYLE-004_anima_turbo/010_generation/001_STYLE_004_anima_turbo_r2_00001_.png) · [manifest](workspace/style_menu/experiments/ANIMA_FAMILY_R2_20261005/runs/STYLE-004_anima_turbo/run_manifest.json) |

All four compiled records identify compiler_revision anima_hybrid_v2. The exact compiler output, relationship contract and native negative guards are preserved in each cell's compiled_prompt.json.

## Direct R1 → R2 findings

The card puts R1 and R2 Anima outputs side-by-side. Its B1 Krea thumbnails are explicitly context only and are excluded from any Anima model ranking.

| Required question | Direct result |
|---|---|
| STYLE-001 red/black cyberpunk/night recovered vs R1? | **Partly.** R2 Base has a stronger black/night and cyan-edge treatment, but red neon/industrial detail is still absent. R2 Turbo still has a white background, so that mismatch is **not fixed**. |
| STYLE-001 face and blue-coat readability retained? | **Mixed.** Both R2 faces and coats remain identifiable. R2 Base's face is darker/less readable than R1 while the blue coat silhouette and cyan edge stay clear. Turbo's face and coat stay clear. |
| STYLE-004 exactly one compass? | **Yes in both R2 cells.** The visible duplicate from R1 Base is not reproduced; each R2 image shows one compass. |
| Compass connected to anatomical left hand? | **No in either R2 cell.** Both front-view images place the compass in the hand on the viewer's left, which is the subject's anatomical right. The explicit R2 relationship did not correct laterality. |
| Full subject and both feet visible? | **Yes in all four R2 images.** Both feet are visible. |
| STYLE-004 gouache/storybook retained? | **Weak/mixed.** R2 Base becomes flatter and more graphic on white, losing the warm paper/gouache feel visible in R1 Base. Turbo keeps a warm background but remains clean cel/anime shading rather than painterly gouache. |
| R1 Base duplicate-compass issue gone? | **Visually absent in this one R2 Base sample.** Compiler v2 removes duplicated equipment mentions and appends duplicate-equipment guards. This single sample does not prove a universal defect rate. |

### Pipeline defect disposition

- **Equipment duplication:** the R1 Base STYLE-004 defect did not recur; code path is anima_hybrid_v2 and the R2 outputs each show one compass. Mark this sample-level defect as **RESOLVED IN R2 SAMPLE**, not generally guaranteed.
- **Anatomical laterality:** **NOT RESOLVED.** Compiler prompt asks for the subject's anatomical left hand, but both STYLE-004 outputs render it viewer-left/subject-right. Further model-aware grounding or subject-view instruction needs a separate authorized cohort.
- **Fixture/style conflict:** the forced neutral environment has been removed from the fixture, but model behavior still under-delivers red neon in STYLE-001 and Turbo still defaults to white. The prompt-level fixture conflict is corrected; visual style adherence remains **UNRESOLVED**.
- **STYLE-004 medium:** Base R2 sacrificed some warm paper/gouache character while fixing the compass count. This is a remaining trade-off, not an approval.

B1 Krea remains a contextual image reference only. Its different model and 1024×1024 B1 canvas are not used to rank the R2 Anima models.

## Gate state

- Four real generations: **PASS, 4/4**.
- Technical PNG QA: **PASS, 4/4**.
- Visual evidence: complete; all candidates stay **REVIEW_REQUIRED**.
- Golden approval, production recommendation, and project SOT update: **not performed**.
- Anima-family offline checks: **PASS** — pipeline check/preflight valid and targeted compiler/prompt tests 12 passed.
- Full pytest: **PASS** — 286 passed, 1 skipped because local migration benchmark data is unavailable.
- assetpipe --help: **PASS**. git diff --check: **PASS**.
- The full-suite repair changed eight package-skill links to references already inside the plugin package; plugin package tests pass 3/3. No Plugin Creator validation was run or claimed.
