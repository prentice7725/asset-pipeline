# M3 audit / offline motion package — validation 2026-10-23

Base main: `4320bf864addabffdb2f2e66871b61052514a555`.
Branch: `codex/m3-motion-audit-20261023`, isolated checkout under
`workspace/checkouts/m3-motion-audit-20261023` in the original repository.
Windows 10 build 26300, Python 3.11.9, Pillow 12.2.0, OpenCV 5.0.0,
pytest 9.1.1, MCP 1.30.0. The worktree venv uses system site packages;
the existing operating environment and pinned runtime were not replaced.

## Results

| Check | Result | Evidence / limits |
| --- | --- | --- |
| Required `pip install -e ".[dev,motion]"` | PASS | Initial restricted-network build failed; rerun with network permission completed. Existing full suite additionally required `.[dev,motion,mcp]`, installed only in worktree venv |
| Full offline pytest | **603 PASS / 1 SKIP / 0 FAIL / 0 ERROR** | `workspace/pytest-full-short.log`, 230.98s, 604 cases; short basetemp `C:/workspace/asset-pipeline/workspace/m3t` |
| Factory / motion / MCP focused suite | **139 PASS** | `workspace/pytest-focused.log`; includes existing extraction/keyframes, factory/execution and adapter six-tool tests |
| Final package regression after final review | **15 PASS** | `pytest tests/unit/test_motion_package.py -q --basetemp C:/workspace/asset-pipeline/workspace/m3final`, 6.88s. Final review added raw-frame provenance and moved source revalidation before review-template creation; this focused rerun validates the final changes |
| Installed `assetpipe --help`, `motion-package --help` | PASS | Installed executable in worktree `.venv/Scripts/assetpipe`; existing command options preserved |
| Installed CLI video packaging smoke | PASS, research only | `workspace/cli-motion-smoke.log`; existing synthetic FFV1 AVI → six chronological frames → RGBA atlas, manifest/review-required outputs |
| Schema/legacy/default preservation | PASS (diff + tests) | `git diff --exit-code origin/main -- integrations/mcp schemas/factory_request_v1.schema.json config/workflow_registry.yaml src/assetpipe/_ported`; exact six tools exercised in adapter tests |
| Whitespace | PASS | `git diff --check` |
| ComfyUI live node inventory | **BLOCKED** | MCP server_info error; localhost read-only fallback connection refused (WinError 10061). `workspace/evidence/m3-readonly-audit-local.json` |
| Current Krea2 loader execution / quality impact | **NOT_RUN / NOT_MEASURED** | Actual model header/hash and loader source rechecked, no model load or weight patch |
| Real I2V / 1,2,3-reference consumption / Pixel64 A/B | **NOT_RUN** | No generation budget authorized or consumed |
| Alpha removal / Godot / Phaser / human art approval | **NOT_RUN** | Opaque research atlas only; no game-readiness assertion |

The single SKIP is `tests/unit/test_assetpipe.py::test_direct_frames_are_identical_to_verified_legacy`:
local migration benchmark data is absent from this isolated checkout. Historical
exact-match records are preserved but are not reported as a new PASS.

Initial full-suite attempts in long worktree/temp paths failed existing CLI
Windows path-budget checks, and one default sandbox temp run could not atomically
replace a manifest (WinError 5). The old logs are retained in `workspace/`.
An isolated Grok synthetic case passed with a short temp path, followed by the
entire suite passing there. No product path limits, test assertions or security
gates were weakened to obtain PASS. Initial MCP collection also failed until the
existing optional test dependency was installed; that run is not counted as PASS.

## Change units and reuse

Audit unit: `docs/factory/M3_REAUDIT_20261023.md`, `scripts/m3_readonly_audit.py`.
Records code/test evidence and read-only local/third-party findings. The collector
reads a safetensors header and hashes files; it does not execute the loader.

Motion unit: `src/assetpipe/motion/package.py`, the additive command in
`src/assetpipe/cli/__init__.py`, `tests/unit/test_motion_package.py`,
`docs/factory/MOTION_PACKAGE.md`, README and CHANGELOG plus this evidence record.
Reuses `RootResolver`, Factory planning/provenance, manifest writer,
`decode_direct_reference` and `extract_motion` with its existing alignment.
No legacy algorithm, provider dispatch contract or MCP schema is rewritten.

## Measured improvement and remaining gates

The measured improvement is delivery of a previously absent offline artifact:
a real locally encoded synthetic video produces an atlas whose six tiles match
the aligned RGBA frame bytes. Source/request/parent hashes remain unchanged during
normal execution and forced child failure. All timeline slots, including held
poses, survive packing. These are software/codec properties, not measured art gains.
Silhouette quality, equipment readability, manual-edit time, identity preservation,
animation loop quality and user acceptance remain **NOT_MEASURED/REVIEW_REQUIRED**.

Factory IMAGE_TO_SPRITE remains BLOCKED_BACKEND_NOT_VERIFIED. Every new research
manifest has generation NOT_RUN, provider_input_consumption NOT_VERIFIED,
game_ready false and review_state REVIEW_REQUIRED. A failed child retains source
video/intermediates and a FAILED receipt; no retry/fallback or review is fabricated.
Real E2E still needs live backend capability verification, explicit count/role
binding, one-shot authorized generation budget, and actual human review.

## Rollback

Revert the motion change commit to remove the new command, module and docs; audit
history can remain. No migration, installation of ComfyUI nodes, registry change,
Golden promotion, SOT rewrite or runtime rollout must be reversed. Preserve all
existing/new runs, original videos, failure evidence and any durable reservations.
No public PR publication, live MCP pointer change or operational activation is
part of this local validation record.

Verdict: **OFFLINE_PASS for the tested package/contracts; GENERATION_NOT_RUN;
M3_SHARED_I2V_BLOCKED; HUMAN_REVIEW_REQUIRED**. M3.0–M3.6 are not declared complete.
