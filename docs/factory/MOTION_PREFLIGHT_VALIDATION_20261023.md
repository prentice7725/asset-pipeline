# Motion preflight validation — 2026-10-23

Branch: `codex/m3-motion-provider-20261023`.
Base: `acfe9de` (existing-video offline package), whose main baseline is
`4320bf864addabffdb2f2e66871b61052514a555`.
The cleaned original checkout remains untouched; this work uses the existing
independent M3 worktree. No discarded portrait/fusion/project-specific executor
is restored.

## Scope and results

- New focused suite: **28 PASS** (9.04s),
  `tests/unit/test_video_preflight.py`. It uses synthetic references, fake GET
  node/model inventories and forbidden upload/queue/poll/download methods.
- Required editable `.[dev,motion]` install: PASS after network permission.
  The first network-restricted attempt failed; its log is preserved separately.
- Installed `assetpipe --help`, `motion-preflight --help`: PASS.
- Installed CLI prepare and inspect: PASS on clearly labeled synthetic input.
  Three-reference tests preserve each input's bytes, role and order, without
  claiming actual video conditioning or semantic support.
- Actual localhost GET inventory: **UNAVAILABLE**, WinError 10061 connection
  refused at `/system_stats`. The Comfy MCP `server_info` probe also failed.
  No server start/update, model import, model/node installation or generation.
- Current `nonpixel_motion_contract`: missing explicit `model_profile`, so a
  canonical video prompt cannot yet be compiled. This is reported as its own
  gate rather than borrowing a still model's dialect or writing a second compiler.
- Full offline regression: **631 PASS / 1 SKIP / 0 FAIL / 0 ERROR**, 632 cases,
  219.24s. Command: `.venv/Scripts/python -m pytest -q --basetemp
  C:/workspace/asset-pipeline/workspace/m3vp`. This short temp root is outside
  the independent source worktree, preserving the CLI job isolation contract.
  The skip is `test_direct_frames_are_identical_to_verified_legacy`: its local
  migration benchmark is unavailable here; no historical PASS is substituted.
- `git diff --check`: PASS. No differences to six MCP contracts, Factory code,
  workflow registry/graphs, model profiles or ported algorithms from this branch's
  base. The original cleanup checkout remains clean.

Local evidence directory in the M3 worktree:
`workspace/video-provider-validation/` contains full pytest, installed CLI help,
`live-preflight.json`, `prepare-cli.json` and `inspect-cli.json`.
`workspace/video-preflight-install*.log` preserves installation outcomes.
Synthetic preparation sources remain in `workspace/test-video-preflight-03/`.
The complete prepared input directory is recorded in `prepare-cli.json`.

## Measured behavior

The new behavior is durable source preparation and explicit gate diagnostics.
All requested references remain separate, ordered and hashed. Stale input,
configuration or preserved-copy content, changed role/order, unauthorized review
flags and outside-root paths fail closed. Partial copy failure preserves FAILED
state; a new call cannot overwrite an existing preparation.
The live-schema test rejects an unavailable input binding and a requested
length that violates a synthetic node's min/max/step. These synthetic schemas
are software test evidence, not installed capability verification.

Every result remains generation_allowed=false and reference_consumption
NOT_VERIFIED. There is no runnable workflow, upload, budget reservation, queue
POST, hidden retry, provider fallback or art approval. Art quality, animation
identity, loop stability, manual editing cost and in-game readability are
NOT_MEASURED. No existing IMAGE_ONLY or AUDIO_ONLY terminal branch is made
dependent on video preflight.

## Remaining gates and rollback

The one-request generator adapter and real I2V -> frames -> sprite trial remain
pending. They require a reachable local installation, explicit video prompt
profile, actual role/count consumption evidence, verified model contents and a
separately authorized generation budget. Technical QA, human Aseprite/art review,
Golden/SOT approval and runtime activation remain independent.

Rollback: revert this follow-up commit. It adds only video preflight/preparation
code, additive CLI options, tests and documentation. Keep prepared directories
and failure evidence. No production default, registry, runtime pointer or model
file needs rollback.

Verdict: **OFFLINE_CONTRACT_TESTED / GENERATION_NOT_RUN /
BACKEND_UNAVAILABLE / REFERENCE_CAPABILITY_NOT_VERIFIED**. This is a partial
M3.2 implementation, not completion of Shared Motion Backbone E2E.
