# Motion research executor — validation 2026-10-24

Branch: `codex/m3-motion-executor-20261024`, base `42a5c50`.
Worktree: `workspace/checkouts/m3-motion-audit-20261023` in the original repo.
The original cleanup checkout, pinned MCP runtime and legacy pixel repository
were not modified by this task. No discarded portrait/fusion/project-specific
module is restored.

## Implemented behavior

- A read-only execution plan reuses the canonical prompt compiler and binds its
  output, source parent/reference, preparation, style/SOT/configuration files,
  selected workflow, explicit dimensions/seed and executor source to one hash.
- A separate one-shot capability-probe authorization plus explicit generation
  flag and locally enabled research configuration is required for execution.
  Real config stays disabled with empty model roots. The known MiniMax workflow
  remains EXPERIMENTAL; the new profile is a research dialect mapping only.
- All graph-selected model inputs must be covered by registry declarations and
  actual local SHA-256 checks under configured absolute model roots. The plan
  also rejects known Windows output-path and atlas-size overflow before charging.
- The existing durable factory budget namespace atomically limits each ID to one
  upload/queue attempt, including failure/concurrency cases. No auto retry,
  budget release or provider fallback. Immutable source preparations are reusable
  only with a separately authorized new budget, not an automatic second attempt.
- The submitted/history graph, prompt ID and output prefix are correlated before
  download. Original video is preserved and passed to the existing codec/frame/
  alignment/atlas package. Parent stills are not written. Source drift during a
  long generation or packaging prevents a successful candidate receipt.
- Reference role semantics, identity/art/loop quality, alpha removal, Golden,
  SOT approval and game-engine imports remain unverified. Every candidate has
  REVIEW_REQUIRED and game_ready false.

## Actual local installation evidence

GET-only checks on 2026-10-24 reached **ComfyUI 0.42.4**. The global `/object_info`
catalog timed out. Individual required-node routes, verified against the local
server implementation, responded normally. Preflight now queries exactly the
workflow's classes rather than unrelated extensions' schema hooks.

- **15/15 required node classes present** via individual GETs.
- **5 required model filenames listed**. This does not prove loaded weight hashes.
- A 512x512 / seed 7 / five-frame synthetic-source plan passed the actual live
  node schema/type/option/range check. This is a graph dry check, not generation.
- VHS publishes codec-specific pix_fmt/CRF/metadata inputs under its selected
  format descriptor rather than top-level inputs. The validator now checks these
  declarations explicitly and rejects unknown/invalid options. No gate is skipped.
- Actual uploads, queue POSTs, generation requests, budget reservations and
  operational activation: **0**.

Evidence in `workspace/motion-executor-validation/`:
`backend-readonly.json` (initial global timeout), `backend-targeted.json`,
`backend-scoped-readonly.json` (complete required-node inventory),
`live-graph-drycheck-final.json`, and installed `cli-plan.json`/help logs.
The earlier dry-check failure for an unsupported top-level pix_fmt description
is retained as `live-graph-drycheck.json`; the new selected-format validation
resolved it without dropping that option or weakening unknown-input rejection.

## Offline software validation

Final complete regression: **671 PASS / 1 SKIP / 0 FAIL / 0 ERROR**, 672 cases,
665.20s. Windows build 26300, Python 3.11.9, pytest 9.1.1, Pillow 12.2.0,
OpenCV 5.0.0.93, MCP 1.30.0. Command:
`.venv/Scripts/python -m pytest -q --basetemp C:/workspace/asset-pipeline/workspace/mex24ship`.
Log: `workspace/motion-executor-validation/pytest-release.log`.
The temp root is outside this independent source worktree, preserving existing
CLI isolation checks. The existing local migration benchmark is unavailable, so
`test_direct_frames_are_identical_to_verified_legacy` remains SKIP; old evidence
is not counted as a new pass. Focused runs also passed the executor, source drift, parent preservation, budget
scope/replay/concurrency and real codec/atlas chain with a **fake ComfyUI client**.
The synthetic fixtures never load weights or call the actual generation server.
They write clearly labeled synthetic consent records only under test temporary
directories; these are not real human authorization or art evidence.

Additional regressions cover 2/3-reference rejection without dropped inputs,
required project contract preservation, coherent source/request changes during
generation, graph-model hash coverage, selected VHS codec widgets, and scoped
node inventory. The knowledge inventory's strict expected profile count is now
9 because one explicit research compiler profile was added; model variants stay
10 and workflow count stays 11. No production model was added or ranked.

Required editable `.[dev,motion]` install and installed CLI/plan/help checks ran.
Earlier long-test-path and restricted Windows file-replacement failures are
retained in the worktree logs. Final validation uses a short temp path outside
the independent source checkout and local filesystem permissions. No assertions,
path limits, model hashes or security gates were relaxed to obtain a pass.

## Change files, remaining gates and rollback

Changed production/config files: `providers/video/executor.py`, the GET-only
inventory in `providers/video/__init__.py`, additive CLI commands, one candidate
model-profile mapping, the existing EXPERIMENTAL workflow metadata and disabled
research settings. Tests and README/CHANGELOG/usage/evidence docs accompany them.
Reused: Factory plan/provenance/roots/manifests, existing compiler and style locks,
Comfy client/workflow patcher and existing motion extraction/packing. Ported
algorithms, workflow graphs, existing Factory executor and six MCP schemas are
unchanged.
The shared runner creates its output directory after queue submission; this
adapter instead calls the same client and patcher directly so the reservation,
state and graph evidence exist before the first generation side effect.

Software delivery is measured; artistic improvement is **NOT_MEASURED**.
Actual I2V E2E is **NOT_RUN**, not a synthetic PASS. It still needs real source
selection, explicit one-request consent, correct local/server model-root setup,
local weight hashes and required visual/Aseprite review. 2/3-reference production,
PIXEL64 motion, alpha removal, engine import and normal Factory motion dispatch
are not completed by this single-reference research adapter.

Rollback: revert this executor change, including its candidate profile and
additive CLI/config. Keep all run/receipt/budget directories and source/failure
evidence. No deployed runtime or actual model/node installation needs reversal.

Verdict: **RESEARCH_EXECUTOR_IMPLEMENTED / REAL_INSTALLATION_SCHEMA_CHECKED /
REAL_GENERATION_NOT_RUN / HUMAN_REVIEW_REQUIRED**, with production activation off.
