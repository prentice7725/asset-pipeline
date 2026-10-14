# Uncommitted-work review — 2026-10-14

Reference for developers and operators deciding what to publish from preserved local work.

## Publication decision

The initial baseline contains **78 modified/untracked files** at `main@f6212c6`
after the previous integration and link-only repairs. Six existing files are
selected for publication, together with this new inventory and Windows CI wiring
(eight PR files in total). The other **72 files
remain local**, with no reset, deletion, SOT activation or experimental promotion.

This PR adds the 22 synthetic Windows P1 regressions for Codex/Grok session
aliases, nested junction/symlink chains, case variants, normal session collection
and external-root rejection. The underlying production fixes are already on main.
The test uses the existing security helper and providers; no experimental feature
file is needed. Tests create only synthetic records under test temporary roots.
The offline collection workflow now triggers for this test file and runs its 22
cases on Windows. A report check rejects skips, failures or errors so missing
symlink privileges cannot silently count as verified Windows coverage.

The four dated reports receive a historical-context preface. Original text and
reported hashes/counts are retained. They are not new activation recommendations
or claims about today's runtime. The factory index links this review and the old
inventory. The Antigravity investigation remains a separate PR (#23).

## Preserved inventory

Every path below was present before this publication task. The grouping is a
publication decision, not a judgment that preserved experiments should be deleted.

### Publish now (6 files)

Missing Windows security regressions and dated security/stabilization/reorganization records. Historical statuses remain historical; no production source is included.

- `docs/factory/GROK_WINDOWS_STABILIZATION_20261011.md`
- `docs/factory/PROJECT_REORGANIZATION_20261011.md`
- `docs/factory/README.md`
- `docs/plugin/SECURITY_P1_REVALIDATION_2026-10-10.md`
- `docs/plugin/SECURITY_RELEASE_BLOCKERS_2026-10-10.md`
- `tests/unit/test_security_p1_revalidation.py`

### Preserve: model and SOT change (3 files)

Changes the portrait segmenter from u2netp to isnet-anime and changes the project delivery SOT. Requires separately reviewed model provenance, optional dependency and artifact evidence; no SOT or default model change in this PR.

- `config/styles/projects/isekai_examiner/visual_sot.yaml`
- `docs/PORTRAIT_BACKGROUND_REMOVAL.md`
- `src/assetpipe/portrait_delivery.py`

### Preserve: experimental implementation (25 files)

Fusion, project-scoped video, portrait extension/repair and their CLI/API/config/test dependencies remain local. Some executors read/hash stored request paths directly rather than through configured-root validation, and extension/repair do not uniformly enforce the no-artifacts-in-source policy. Passing current synthetic tests is not a security review or production acceptance. M2.7 Gate B code is retained without authorization to run it.

- `README.md`
- `config/portrait_extensions.yaml`
- `config/styles/video_recipes.yaml`
- `config/workflows/deno_minimax_h3_fusion_experimental.json`
- `config/workflows/krea2_portrait_extend_api.json`
- `config/workflows/krea2_portrait_repair_api.json`
- `docs/FUSION_ANIMATION.md`
- `docs/NONPIXEL_TRANSFORMATION_VALIDATION_2026-10-10.md`
- `docs/NONPIXEL_TRANSFORMATION_VIDEO.md`
- `docs/PORTRAIT_EXTENSION.md`
- `docs/PORTRAIT_REPAIR.md`
- `examples/fusion_request.json`
- `src/assetpipe/api.py`
- `src/assetpipe/cli/__init__.py`
- `src/assetpipe/motion/fusion.py`
- `src/assetpipe/motion/rendezvous.py`
- `src/assetpipe/pipelines/__init__.py`
- `src/assetpipe/pipelines/nonpixel_animation/__init__.py`
- `src/assetpipe/portrait_extend.py`
- `src/assetpipe/portrait_repair.py`
- `tests/unit/test_fusion.py`
- `tests/unit/test_m27_gate_b.py`
- `tests/unit/test_portrait_extend.py`
- `tests/unit/test_portrait_repair.py`
- `tests/unit/test_rendezvous_video.py`

### Preserve: research (35 files)

32/48/64 pixel workflow graphs, scripts, research reports and the older menu remain separate from production defaults. Their referenced local evidence is not promoted or deleted.

- `config/workflows/anima_hires_pixel32_contract_experimental.json`
- `config/workflows/anima_hires_pixel48_contract_experimental.json`
- `config/workflows/anima_pixel32_contract_experimental.json`
- `config/workflows/anima_pixel48_contract_experimental.json`
- `config/workflows/anima_pixelate_1024_nearest256_experimental.json`
- `config/workflows/krea2_hires_pixel32_contract_experimental.json`
- `config/workflows/krea2_hires_pixel48_contract_experimental.json`
- `config/workflows/krea2_pixel32_contract_experimental.json`
- `config/workflows/krea2_pixel48_contract_experimental.json`
- `config/workflows/krea2_pixel64_contract_experimental.json`
- `config/workflows/krea2_pixel64_knight_experimental.json`
- `config/workflows/p4_single_master_S01_standard.json`
- `config/workflows/p4_single_master_S02_pixelate.json`
- `config/workflows/p5_highres_A_Anima.json`
- `config/workflows/p5_highres_B_Krea2.json`
- `config/workflows/p5_rework_krea2_01.json`
- `config/workflows/p5_rework_krea2_02.json`
- `config/workflows/p5_rework_krea2_03.json`
- `config/workflows/p7_A_general.json`
- `config/workflows/p7_B_friendly.json`
- `docs/research/ANIMA_1024_NEAREST256_20261003.md`
- `docs/research/ANIMA_KREA2_HIRES_PIXEL32_48_20261005.md`
- `docs/research/CODEX_GROK_PIXEL32_48_20261005.md`
- `docs/research/GPT_KREA2_ASEPRITE32_48_20261006.md`
- `docs/research/GPT_REFERENCE32_48_20261006.md`
- `docs/research/GPT_REFINER32_PIPELINE_20261005.md`
- `docs/research/GPT_REPEAT32_48_20261006.md`
- `docs/research/KREA2_PIXEL64_KNIGHT_20261005.md`
- `docs/research/P7_PSEUDO_PIXEL_RECOVERY_20261006.md`
- `docs/style/PIXEL_STYLE_CONTRACT_v0.1.md`
- `docs/style_menu/NONPIXEL_COMPARISON_REPORT_v0.1.md`
- `docs/style_menu/NUMBERED_CANDIDATE_MENU_v0.1.md`
- `scripts/m27_gate_b.py`
- `scripts/p7_pseudo_pixel_recovery.py`
- `scripts/refiner32_experiment.py`

### Preserve: historical plugin notes (9 files)

Nine local skill/reference changes expand packaging with historical research notes. The maintained production menu already exists. Keep these until their relevance, package size and link/authorization boundaries receive separate review.

- `plugin/references/AGENT_RECIPE_SELECTION_GUIDE_v0.1.md`
- `plugin/references/ASSET_PIPELINE_MODEL_STYLE_HANDBOOK_v0.1.md`
- `plugin/references/CODEX_NONPIXEL_WORK_ORDER_v0.1.md`
- `plugin/references/MODEL_CAPABILITY_GUIDE_v0.1.md`
- `plugin/references/MODEL_STYLE_BENCHMARK_PROTOCOL_v0.1.md`
- `plugin/references/MODEL_STYLE_EVIDENCE_AUDIT_20261004.md`
- `plugin/references/NONPIXEL_PROMPT_RESEARCH_v0.1.md`
- `plugin/references/NUMBERED_CANDIDATE_MENU_v0.1.md`
- `plugin/skills/asset-production/SKILL.md`

## Validation and next gates

Validation ran against a source checkout built from origin/main plus only the
selected files. This avoids counting the uncommitted experimental features
as dependencies or test evidence for this PR.

| Check | Result |
| --- | --- |
| Full isolated-source pytest | **588 PASS / 0 FAIL / 0 ERROR / 1 SKIP**, 199.18 seconds |
| Windows P1 job command and no-skip report gate | **22 PASS / 0 SKIP** |
| MCP initialize, exact six full schemas and negative paths | PASS; owned server exited on EOF |
| CLI help and isolated-source import | PASS; imports explicitly pinned to the review checkout |
| Deferred files | 72 byte-identical |
| Operating runtime baseline | 4,702 file hashes unchanged |
| Historical report bodies | Four unchanged, with context prefixed |

The single existing SKIP is `test_assetpipe.py`'s local migration benchmark,
whose external data is unavailable from the isolated source checkout. That
equivalence remains unverified here; it is not converted into PASS. The new
Windows cases all executed on this Windows host. Hosted CI results are separate
from these local results.

The full preserved working tree previously passed 663 tests, but that is a
different test cohort. No generation or paid request is made. Provider ACTIVE,
Golden/Aseprite approval, project SOT and the operating MCP runtime are unchanged.
Official Plugin Creator validation and real generation E2E are not performed.

Before publishing experimental executors, review all transitive read/hash paths,
output directories, persisted authorization and graph bindings, replay/concurrency
reservations, project scoping and optional dependencies. Add adversarial fixtures
for the gaps; do not delete tests, relax assertions or reuse synthetic approvals.
Human identity/art review remains independent of technical QA.

Local backup/evidence: `workspace/uncommitted_review/20261014/` contains
`local-before.zip`, `local-before.patch`, `before.json`, `selection.json`,
test reports and preservation results. Original operating files are compared
against the start of this task; this does not renew a historical candidate seal.
No new deployable candidate is built, installed or activated.
