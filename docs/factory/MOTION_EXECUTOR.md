# Single-reference motion research executor

The first generation adapter connects an existing NONPIXEL_IMAGE parent to the
registered MiniMax H3 workflow, then to the existing video/frame/atlas package.
It is a **capability probe**, not production activation or verified semantic
conditioning. Defaults remain `video_research.enabled: false`, no model roots,
EXPERIMENTAL workflow and no actual generation evidence.

## Scope

- One existing parent image with role IDENTITY_PRIMARY. The parent Brief and
  manifest are preserved. External images without source canon, 2/3-reference
  probes, PIXEL64 and static regeneration are not implemented by this executor.
- An explicit natural-language **research** profile for the existing workflow
  reuses `compile_prompt`; source identity/equipment, available project/style
  gates and negative instructions remain in the shared compiler. The profile is
  not a new model or evidence of model quality. Negative instructions require
  visual review; no native negative-conditioning support is claimed.
- Explicit seed/width/height. The known adapter accepts 17k+5 frames at 24fps,
  at most 240 frames, dimensions divisible by 16, 64..1344, and area no greater
  than 768x1344. The existing atlas also imposes its 32M-pixel limit. The common
  default 768x768/56-frame graph exceeds that atlas limit; choose explicit
  fitting dimensions before consenting. No automatic resizing or frame dropping.
  These are software limits; the live node schema can impose stricter limits.
- PRESERVE_OR_REVIEW background only. Alpha removal, identity/loop quality,
  Godot/Phaser imports, Golden approval and game readiness remain separate gates.

## Concrete plan before execution consent

First use [motion preparation](MOTION_PREFLIGHT.md) to freeze references. Then:

```powershell
assetpipe --root <repo> motion-execution-plan --run workspace/prepared_motion --seed 7 --width 512 --height 512
```

This does not upload or generate. It revalidates the prepared input, compiles
the original source Brief with the explicitly selected video profile, and emits
the prompt, parameters, reference hashes, graph template and execution-plan hash.
The template has unresolved reference/authorization markers and is not submitted.
Changes to source, request, prepared input, compiler/style/SOT files, configured
workflow or executor source invalidate the hash. Project/compiler conflicts
fail rather than stripping locks or borrowing a still-image model's profile.

Actual execution additionally requires separate user approval to enable the
local research setting and a reviewed one-request authorization. The caller must
coordinate these approvals; a file declaration is not a signed identity proof.
The implementation never generates an authorization or human review record.
Configured model roots must be absolute existing directories. Every model
selected by graph inputs must also be declared in the registry and hash contract;
omissions, extra/duplicate entries, ambiguity, root escapes or hash mismatch block.

The operator's JSON authorization has exactly these fields:

| Field | Required value |
| --- | --- |
| schema_version | integer 1 |
| kind | MOTION_ONE_REQUEST_AUTHORIZATION |
| authorization_id | unique 32-character lowercase hexadecimal ID |
| execution_plan_sha256 | exact reviewed execution-plan hash |
| project_id / asset_id | exact plan identity |
| purpose | SINGLE_REFERENCE_CAPABILITY_PROBE |
| max_requests | integer 1 |
| authorized_by / reason | actual attribution and scope of consent |
| models | exact list of folder, name, SHA-256 records for every required weight |

Only after that consent, an operator may call:

```powershell
# Generates if all gates pass; not run by this implementation/validation task.
assetpipe --root <repo> motion-execute --run workspace/prepared_motion --seed 7 --width 512 --height 512 --authorization workspace/actual_authorization.json --authorize-generation
```

## One attempt, preserved evidence

Before reservation the executor checks local hashes, GET-only live node/model
inventory and graph input types/options/ranges, source/compiler integrity and
authorization. Only the probe's explicitly unverified reference semantics,
locally addressed model-hash gate and separately checked budget declaration are
handled by the research path. Other failed preflight gates are not ignored.
Only loopback HTTP is supported; nested-provider execution is rejected.
Only workflow-required node classes are queried, so slow schema hooks from
unrelated extensions do not block the entire global catalog. VHS codec widgets
are checked against its live selected-format declarations, including pixel
format/CRF/metadata options; undeclared widgets are still rejected.

It atomically reserves the ID under the existing root-scoped
`workspace/factory_budget/<id>` ledger **before the first upload**. This shares
the namespace with still/audio reservations. Failed upload, lost queue response,
timeout or QA failure never releases that reservation. There is no retry or
provider fallback. A different installation's ledger is not a global charge lock;
authorization IDs and installations must be coordinated by the operator.

The executor uploads the exact preserved reference, patches only known workflow
bindings and uses an ID-specific output prefix. It checks returned prompt IDs,
the exact submitted graph against execution history, and exactly one matching
MP4 output. Another run's prefix/subfolder, ambiguous output or mismatched
history fails closed. The original video is saved before decoding/packing.
After potentially long generation and after packing, the original source/plan
is revalidated; a newly edited valid request cannot take ownership of old video.

The ledger retains `motion_execution.json`, `compiled_prompt.json`,
`submitted_graph.json`, `history.json`, original MP4 and the package's original
copy, decoded/raw/aligned frames, atlas, timing/pivots and review template.
Partial failures remain FAILED and inspectable; the parent/prepared input is
never mutated. One separately authorized ID permits one upload/queue attempt,
not unbounded calls or an implicit retry of ambiguous completion.

## Evidence interpretation and limits

HISTORY_GRAPH_MATCHED proves graph correlation/binding only; reference-role
semantics remain NOT_VERIFIED. Local hashes bind configured files, not a proof
of the server's in-memory weights. Filename presence is not model-content proof.
Trusted local configuration/ownership and correct server model-root setup remain
necessary; file replacement between validation and I/O is a limitation. Weight
stat changes during generation cause failure, but this is not a signed execution
environment or a race-free filesystem sandbox.

Every successful probe remains CANDIDATE_REVIEW_REQUIRED / game_ready=false.
The existing package's generation NOT_RUN field describes its decoding/packing
stage; the parent probe receipt carries the queue ID and generation provenance.
No provider ACTIVE promotion, synthetic human approval or automatic Golden/SOT
change occurs. Ordinary Factory `execute` motion and six MCP schemas stay unchanged.

Rollback: revert the executor commit, including its candidate profile/CLI/config.
Never delete durable reservations, originals or failure evidence when rolling
back. This task performed no operational enablement or real generation to undo.
See [dated validation](MOTION_EXECUTOR_VALIDATION_20261024.md).
