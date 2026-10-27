# General nonpixel motion create validation — 2026-10-27

Branch `codex/nonpixel-create-motion-20261027`, base `953c61a`.
Scope: an explicit continuation entrypoint, not automatic animation activation.
New live generation: **NOT_RUN**. Human/Aseprite approval: **NOT_GRANTED**.
[Machine-readable validation](NONPIXEL_CREATE_VALIDATION_20261027.json).

## Change and reuse

`pipelines.create` accepts an explicit motion job and expected plan SHA, without
a new Brief. `pipelines/nonpixel_animation.run` delegates to the existing Factory
`run_job`. The CLI exposes this as `create --type nonpixel-animation --motion-job`.
The output receipt remains `factory_motion.json`; inspection uses existing
`factory motion-inspect`. Capability metadata distinguishes this supported
experimental path from blocked prompt/Brief-only animation routing.

The original Factory request/job schema, source planner, RootResolver, single
attempt generation ledger, video executor, package/recipe pipeline and native
exporter remain unchanged. No verified extraction, alpha, loop, palette or
packing algorithm is rewritten. Static images, SFX and six MCP argument schemas
are preserved. No research config, model installation, Golden/SOT or live MCP
replacement is included.

The command requires an explicit job, pinned plan and new output; direct
prompt/reference/seed/workflow/style/project overrides are rejected. Existing
video replay rejects generation consent. Prepared generation still needs both
an existing authorization file and explicit consent plus all original executor
gates. A job neither regenerates its parent image nor retries failed work.

## Actual installed CLI replay

Fresh plans were computed for the existing fox/rabbit jobs. The installed
general `create` command processed their existing original videos, and existing
`factory motion-inspect` checked the resulting receipts.

| Check | Fox | Rabbit |
| --- | --- | --- |
| Exact RGBA frames vs prior Factory candidate | 20 | 28 |
| Pivot and original frame order | Unchanged | Unchanged |
| Native sprite image vs prior export | Exact SHA match | Exact SHA match |
| Inspection | FACTORY_MOTION_INTEGRITY_PASS_REVIEW_REQUIRED | FACTORY_MOTION_INTEGRITY_PASS_REVIEW_REQUIRED |
| New generation | 0 | 0 |

All 725 previously protected source/candidate/evidence file hashes still match.
These runs exercise real FFmpeg processing and exported resource creation, not
new video generation or new engine loading. Existing engine validation remains
dated evidence; no Godot/Phaser, foot-contact or visual-quality PASS is inherited.
The candidate receipts remain `game_ready=false`, `REVIEW_REQUIRED`.

The local replay harness initially read the protected-hash envelope as a flat
map after both media runs had completed. It failed on the literal key
`protected_hashes`. A separate verifier checked that explicit nested field
against all 725 files and both completed results, without rerunning media or
changing pipeline code. The original failure log and verification are preserved.

## Software validation

The focused codec/entrypoint run recorded 42 passes and 38 fixture errors. Those
errors were the existing Windows `MOTION_OUTPUT_PATH_LIMIT` guard rejecting an
overlong test root. The test root was shortened without weakening the guard;
the executor module then passed all 43 cases. The first failure log is retained.

The first full regression ran inside the restricted sandbox; junction-creation
fixtures failed before exercising their security assertions. The isolated
canonical-collection module reproduced that environment failure (9 passes,
one junction setup failure), then passed all 13 tests under ordinary escalated
execution. The sandbox full run was interrupted and retained as incomplete;
the complete suite was restarted with that verified execution permission.
No junction/security test was skipped or weakened to obtain a PASS.

The first complete ordinary-permission run finished with 788 passes, one skip
and one failure (605.27s). The unchanged Style Lab static experiment test received
Windows `WinError 5` during atomic `manifest.json` replacement. The staged JSON
and failure log were retained; the writer and its no-retry behavior were not
changed. Style Lab plus manifest-write tests then passed all 18 cases in 1.16s
without code changes. The cause is not established and the failed full run is
not relabeled PASS. A fresh complete run is recorded separately below.

New tests exercise actual CLI video replay without still/video generation,
parent image/manifest preservation on stale-plan/consent/decode failures,
ambiguous/incomplete CLI input rejection, and the general Python create path
using the original single-attempt ledger with a fake Comfy client and real codec
processing. Fake-client cases are not real model E2E evidence.

The final fresh complete run (`pytest-full-03.log`) passed **789 tests**, with
**one skip**, in **530.83s**. The skipped local migration benchmark has no local
data and is not a PASS. Both complete runs and the incomplete sandbox run remain
separate evidence; the successful rerun does not establish the cause of the
earlier Windows replacement failure. No writer retry or production workaround
was added. A final post-test hash audit again matched all 725 protected files.

| Check | Current result |
| --- | --- |
| Required editable install `.[dev,motion]` | PASS |
| Installed `assetpipe --help` and `create --help` | PASS |
| Short-root executor focused rerun | 43 passed |
| Style Lab + manifest isolation | 18 passed |
| Final complete offline regression | 789 passed, 1 skipped |
| Installed create, existing fox/rabbit videos | Exact 20/28-frame replay; zero generations |
| Documentation links / diff whitespace | PASS |

## Remaining scope and rollback

Remaining: separately budgeted generation through the new entrypoint, external
image-only parents, 2/3-reference capability, new actions, gameplay/edge/identity
review and required human approval. Prompt-only video, ordinary Factory motion
activation and default research enabling remain unavailable. Pixel research is
not a prerequisite for any of this work.

Evidence remains in ignored `workspace/nonpixel-create-validation-20261027/`:
installed CLI help, two pinned plans, create/inspect logs, fresh intermediates,
receipts, results, source integrity and all regression logs. Earlier focused and
installation logs remain in `workspace/nonpixel-entry-*.log`.

Rollback: revert this additive create/module/capability/test/documentation change.
The old explicit Factory/standalone motion commands and still/SFX paths remain.
Preserve completed candidates, original inputs and any consumed authorization
ledger; rolling back code never refunds or replays a generation authorization.
