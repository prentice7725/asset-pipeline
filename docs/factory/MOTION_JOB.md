# Explicit Factory motion jobs

This CLI integrates the existing Factory request, video/package, explicit recipe
and native engine resource stages. It does not activate ordinary Factory
IMAGE_TO_SPRITE dispatch, approve art or select a loop/background automatically.
Static image and SFX commands remain independent and unchanged.

## General nonpixel create entrypoint

The same coordinator is available through the general Python/CLI create path:

```powershell
assetpipe factory motion-plan --job workspace/my-job.json
assetpipe create --type nonpixel-animation --motion-job workspace/my-job.json `
  --motion-plan-sha256 <returned-plan-sha256> --output workspace/my-new-motion-run
```

This is an explicit experimental continuation of one existing NONPIXEL_IMAGE
parent, not prompt-only animation routing. The job pins the request, video or
prepared generation input, source hashes, frame selection and alpha policy.
`--output` must name a new directory under the configuration root's workspace.
Use `--allowed-root` for each permitted external source root, including the
configuration root when needed; the same root set must be used for planning
and execution. Output remains restricted to the configuration root's workspace.

The command prints the existing `factory_motion.json` receipt path. Inspect it
with `factory motion-inspect --run ... --manifest-sha256 ...`; do not treat it
as the still-image `run_manifest.json` format. Engine resources are written by
the existing exporter; engine loading and human review remain separate stages.

For `PREPARED_GENERATION` only, both `--authorization <file>` and
`--authorize-generation` are necessary in addition to the existing executor's
research/config/model/one-attempt gates. Replay rejects generation consent.
The new entrypoint never prepares an authorization, enables research, generates
a parent still, retries or switches Provider automatically. This implementation
does not authorize a fresh live generation test.

Direct prompt/brief/reference/action, seed, workflow/style/model/preset,
project/asset overrides, SFX duration and `--allow-experimental` cannot be
combined with a motion job. Use the pinned job rather than ambiguous overrides.
Motion authorization/plan/root flags without `--motion-job` are rejected, so
ordinary still/SFX create retains its existing behavior.

Python callers use `create(None, root, output, motion_job=job_path,
motion_plan_sha256=plan_sha, resolver=optional_root_resolver, ...)`.
The explicit wrapper reuses `factory.motion.run_job`; no extraction, alpha,
loop selection, packing, engine export, ledger or approval implementation is
duplicated. Brief-only NONPIXEL_ANIMATION remains blocked. The six MCP tool
argument contracts and ordinary Factory motion activation are unchanged.

## Input and support boundary

[Job schema](../../schemas/factory_motion_job_v1.schema.json) and
[placeholder example](../../examples/factory_motion_job.json) define the new
`FACTORY_MOTION_JOB` envelope. Existing Factory requests, budgets and six MCP tool
schemas are unchanged. Relative job paths resolve against the job file's directory.
The example's zero hashes/source paths and 1..5 frame range must be replaced with
actual, deliberately reviewed inputs; they are not recommended animation settings.

A job pins the original Factory request SHA-256 and contains:

- `input.kind=EXISTING_VIDEO`: exact video path/hash. No provider calls,
  authorization or budget reservation. Optional `generation_record:{path,sha256}`
  preserves historical generation evidence byte-exact as an opaque attachment.
  It never grants new generation consent or proves reference consumption.
- `input.kind=PREPARED_GENERATION`: an existing prepared-input directory and
  explicit seed/width/height. Its source plan must exactly match the pinned
  Factory request. Execution delegates to the existing one-request video adapter.
- `recipe`: explicit recipe `schema_version`, inclusive `selection` and `alpha`.
  Both existing v1 and v2 policies are reused. Source package path/hash are filled
  only after packaging and bound through the existing recipe plan/apply checks.

Current scope is **one existing NONPIXEL_IMAGE parent and one IDENTITY_PRIMARY
reference**. External-image-only sources, 2/3 references, generated-still chains
and Pixel64 motion are rejected before generation. This does not undo those
Factory planning contracts; it limits this execution adapter to demonstrated scope.
The embedded `source_plan` retains the generic Factory's original blocked dispatch
state. Offline replay does not need that backend; prepared generation still has
to pass the existing executor's live gates. Those old states are not relabeled PASS.

For a newly generated still, finish the existing IMAGE_ONLY run first, then create
an EXISTING_RUN motion request pointing to its immutable output. Source and
motion runs stay independent. A failing video stage cannot regenerate or edit the
source image. Ordinary `factory execute` keeps its existing motion block.

## Offline video replay

```powershell
assetpipe --root . factory motion-plan --job workspace/job.json

# Use the returned plan_sha256; choose a fresh output directory.
assetpipe --root . factory motion-run --job workspace/job.json --plan-sha256 <job-plan-sha256> --output workspace/new_motion_job

# Use motion-run's manifest_sha256.
assetpipe --root . factory motion-inspect --run workspace/new_motion_job --manifest-sha256 <receipt-sha256>
```

All commands accept repeated `--allowed-root`; include the config root and only
the specific source/provenance roots needed. Outputs must be in a fresh directory
under that config root's `workspace/`, and cannot contain their inputs. There is
no overwrite, failed-run resume or retry option. Replay rejects generation flags
and authorization arguments instead of silently ignoring them.

## Separately authorized video generation

`factory motion-prepare --request <factory-request> --output <new-prepared-dir>`
delegates unchanged to the existing offline input freezer. It performs no upload.
Put that directory and explicit dimensions/seed in a PREPARED_GENERATION job, then
run `factory motion-plan` to inspect both the job and `generation_plan`.

Two hashes serve different contracts: `plan_sha256` binds the full Factory job;
`generation_plan.execution_plan_sha256` binds the existing
`MOTION_ONE_REQUEST_AUTHORIZATION`. The latter authorization remains exactly the
existing video adapter's schema, including max_requests=1 and model hashes.

```powershell
assetpipe --root . factory motion-run --job workspace/generation-job.json --plan-sha256 <job-plan-sha256> --output workspace/new_motion_job --authorization workspace/video-authorization.json --authorize-generation
```

The research backend remains disabled by default. This command does not change
configuration, enable a provider, allocate a new implicit budget or create consent.
Authorized configuration changes require re-preparation/replanning and a budget
bound to that new video plan, as before. Live node/model/hash checks, local server
policy, graph/history matching, one upload/queue and the durable shared budget
directory remain owned by `providers.video.executor`. A second attempt with a
spent ID fails there; no second coordinator reservation or fallback is introduced.

No real generation was authorized or run in the integration validation. Synthetic
dispatch tests do not replace a separately budgeted live generation check.

## Outputs, failure and inspection

The run retains `job-input.json`, `factory_motion.json`, a separately packaged
original video/decoded/aligned frames (or an immutable link to the delegated
generation package), the generated full `recipe.json` and `candidate/` with the
existing source/masked/final/mask/atlas/review evidence. Optional historical
generation bytes are copied as `historical-generation.json`, without following
old model paths or interpreting them as current read permissions.

`exports/` contains exact copied `sprites.png`, native Godot `walk.tres`, native
Phaser atlas and animation JSON, and `placement.json` with original frame indices,
pivot mapping and candidate digest. This is resource formatting, not a new
extraction/packing algorithm. No animation frame, RGB, pivot or timing is changed.

- Godot: load `walk.tres` as SpriteFrames. Its sibling image is referenced by a
  relative path. Use the recorded centered/offset mapping from `placement.json`.
- Phaser: load atlas as texture key `motion` with the sibling PNG and
  `phaser-atlas.json`; pass the loaded `phaser-animation.json` unchanged to
  `scene.anims.create()`. Apply the recorded origin separately.

Initial validation failures create no run. A downstream failure leaves a FAILED
coordinator receipt and whatever intermediates exist; later stages do not run.
Generated failures leave their original executor ledger intact. Until that ledger
is available, a failed generated job records generation_requests=null, not a
fabricated zero. Neither failed nor partially completed runs can pass inspection.

Inspection requires the caller's expected receipt SHA-256, replans the exact job,
checks the exact output inventory/hashes, source package and recipe integrity,
and, when applicable, the original video executor/authorization receipts. Source,
parameters or implementation drift block reuse. External job/request JSON uses
the existing strict Sources boundary. Pinned internal receipts treat compiler/
retired-model paths as metadata; each actually dereferenced data link still passes
RootResolver. This is a trusted-local integrity mechanism, not signed attestation
or a race-free filesystem sandbox.

Successful jobs remain **CANDIDATE_REVIEW_REQUIRED / game_ready=false**.
`engine_import:NOT_RUN` in the immutable run describes the automatic job stages:
writing resources does not certify engine loading, startup timing, foot contact
or artistic quality. Separate actual validation evidence does not edit that run
into an approval. Aseprite/human review, Golden/SOT and operational activation
remain separate gates.

[Dated integration evidence and rollback](MOTION_JOB_VALIDATION_20261027.md).

[General create entrypoint validation](NONPIXEL_CREATE_VALIDATION_20261027.md).
