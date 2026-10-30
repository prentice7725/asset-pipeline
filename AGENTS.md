# Asset Pipeline contributor instructions

## Current focus (read first)

The active workstream is the M3 Factory NONPIXEL production path, decided by the user on
2026-10-27. Read docs/factory/NONPIXEL_PRODUCTION_PLAN_20261027.md and docs/factory/MOTION_JOB.md.
The goal is one general path: NONPIXEL still → explicit motion job → frames/alpha/loop →
atlas and native Godot/Phaser export → human review. Work on that path's implementation order only.

Frozen until the user explicitly reopens them in a new request:
- Krea2 / Pixel64 / LoRA / DoRA / FP8 loader research, pixel postprocessing A/B, 32px research.
- Per-sample polishing of existing fox/rabbit candidates (extra alpha, loop, timing reports).
- New providers, new styles, new MCP tools or schema changes.
Do not start frozen work because a document lists it as "remaining"; ask the user instead.

Reopened by the user on 2026-10-28 (identity variants only): read docs/factory/IDENTITY_VARIANT.md.
A selected T2I base image is edited once by an explicit reference-edit provider to change expression
or pose. This permits the variant job contract, Codex CLI reference input and an Antigravity (AGY)
Nano Banana adapter following docs/m1/ANTIGRAVITY_NANO_BANANA_PROVIDER_DESIGN_20261014.md. Keep fixed
preserve lists, one attempt, no retry/fallback, HUMAN_REQUIRED identity review and the six MCP tools.

Reopened by the user on 2026-10-30 (BGM only): BGM output class via ComfyUI YuE2, offline contract first.
Read docs/BGM.md. Instrumental by default, vocals and loop seams are listening review items; MiniMax Music
and other paid cloud nodes are not used. Real generation needs a separate request.

Change discipline:
- One topic per branch/PR. Do not bundle research commits into a feature PR.
- Prefer code plus tests over new dated reports. Add a dated validation document only when
  real execution evidence must be preserved, and link it from docs/factory/README.md, not README.md.
- Keep README.md a usage guide; keep CHANGELOG entries to a few lines.
- Production/operational generation needs a separately authorized budget in the current request.
- User decision (2026-10-29): verification of the authorized pipeline has no fixed generation
  budget/count cap. Do not request approval again solely for additional verification trials.
  Keep each run explicit, individually reserved and logged; never reuse a spent authorization
  or hide retries/fallback. Failed gates still block downstream execution: diagnose/correct
  the failure before a distinct, justified validation run. This does not reopen frozen work
  or authorize production use, human art approval, deployment or live MCP replacement.
- Keep new run outputs, images, videos and zip evidence out of git (workspace/ is ignored; never
  force-add). Commit only small JSON/Markdown summaries with hashes. tests/unit/test_repository_size_guard.py
  rejects new tracked files over 1 MB and new tracked workspace paths.

## Baseline rules

Read docs/bootstrap_directive.md and docs/migration_inventory.json before pipeline changes.
The legacy pixel-pipeline is read-only migration source; do not rename, delete, or refactor it.
Keep Python CLI primary, workflows in config/workflows, and all run artifacts outside source modules.
Do not rewrite verified algorithms or add GUI, web UI, MCP, DB, model research, or cloud deployment.
Never advance past a failed gate. Verify external tools with real executions before reporting PASS.
Preserve intermediates, source hashes, generation parameters, QA reports, and explicit review states.
Generated images/animations remain candidates until required Aseprite review.
Safe operations must not redesign identity, clothing, equipment, or silhouette semantics.
The verified direct profile requires explicit blue-tunic/white-background compatibility; never infer it.
Run `.venv/Scripts/python -m pip install -e ".[dev,motion,mcp]"`, `.venv/Scripts/python -m pytest`, and `assetpipe --help`.
(`mcp` is required because pytest collects integrations/mcp/tests.)
The v0.1 bootstrap stopped at ASSET_PIPELINE_V0_1_BOOTSTRAP_PASS. New features require a separate user request.

## Historical milestone scopes

The sections below record earlier authorizations. Their rules still apply to the code they
introduced; their "stop" points describe those milestones, not the current focus above.

The user-authorized Plugin M0 milestone permits a local thin MCP adapter under
integrations/mcp and instructions/reference packaging under plugin. Read
docs/plugin/M0_DIRECTIVE.md for this milestone. Keep production algorithms in
assetpipe, expose exactly six high-level tools, restrict model paths to configured
roots, and preserve all QA/review gates. No public plugin publishing or cloud service.
Do not claim Plugin Creator validation passed unless the official creator actually ran.

The user-authorized M1 milestone permits NONPIXEL_IMAGE multi-provider generation (comfyui, codex_cli,
grok_cli) under src/assetpipe/providers. Read docs/m1/M1_DIRECTIVE.md and docs/m1/PROVIDERS.md. Pixel/SFX paths and
the six MCP tool contracts stay unchanged. CLI providers stay EXPERIMENTAL and explicit_only until
scripts/provider_e2e.py has recorded real-generation evidence; the registry loader rejects ACTIVE without it.
Never add API-key bypasses, implicit provider fallback, automatic retries, or fabricated images. Report a missing or
unauthenticated CLI as BLOCKED/UNAVAILABLE and do not declare M1 complete without real E2E evidence.

The user-authorized M2 milestone permits shared NONPIXEL_IMAGE Style Intelligence under
config/styles and assetpipe.styles. Read docs/m2/STYLE_INTELLIGENCE.md. Preserve Visual SOT
locks, explicit model choices, all QA gates and six MCP tools. Never fabricate style approval,
quality scores or evidence; M2 tests cannot replace provider real-generation E2E.

The user-authorized M2.6 milestone permits offline prompt mining, candidate recipes and source analysis. Read docs/style/PROMPT_MINING_METHOD.md and RECIPE_VALIDATION.md. Submit zero generations in this milestone; M2.5 real image and full pipeline validation follows with a separately authorized budget. Preserve production defaults, six MCP contracts, legacy pixel baseline and all review gates.

The user-authorized M2.5 resumption permits existing-candidate static revalidation and a resumable local style lab. Separate historical equivalence from current approved-master E2E. Never synthesize human Aseprite review; stop at REVIEW_REQUIRED until actual approval. The initial 12-sample PIXEL_STATIC/NONPIXEL_IMAGE cohort executes independently through its own model/workflow preflight and output-specific QA, with persistent pre-reserved budget and no retries or fallback. Only PIXEL_ANIMATION E2E requires a currently approved compatible Static Master. Preserve explicit legacy art rejection and never promote the legacy fixture. Read docs/style/M25_BLOCKER.md.

The user-authorized M2.7 subject-first Visual Hierarchy change is NONPIXEL_IMAGE
offline Gate A only. Read docs/style/M27_SUBJECT_FIRST.md. Integrate explicit
subject integrity and art direction through the existing PromptSpec compiler,
M2 styles and M2.6 mining path. Preserve canon, camera, counts, style fingerprints,
all QA/review gates and six MCP contracts. Generate zero images; Gate B needs a
separate request budget. Stop at OFFLINE_CONTRACT_PASS / GENERATION_NOT_RUN.
