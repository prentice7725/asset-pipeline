# Motion provider preflight and prepared inputs

This is the next offline slice after [existing-video packaging](MOTION_PACKAGE.md).
It reuses Factory v1 source/parent validation, the workflow registry/loader,
configured-root boundaries and the ComfyUI client. No new generator, prompt
compiler, workflow, provider promotion or MCP tool is introduced.

```powershell
assetpipe --root <repo> motion-preflight --request workspace/motion_request.json
assetpipe --root <repo> motion-preflight --request workspace/motion_request.json --inspect-installation
assetpipe --root <repo> motion-prepare --request workspace/motion_request.json --output workspace/prepared_motion_001
assetpipe --root <repo> motion-inspect --run workspace/prepared_motion_001
```

The request is the existing Factory v1 IMAGE_TO_SPRITE envelope, with NONPIXEL
EXISTING_RUN or REFERENCE_MOTION EXTERNAL_IMAGES/EXISTING_RUN. Set an explicit
`motion.workflow_id`, currently `nonpixel_motion_contract` for investigation.
No still is generated. PIXEL64, GENERATE, IMAGE_ONLY and AUDIO_ONLY are rejected
by this video-specific command; their original paths continue independently.

By default preflight is offline, does not allocate providers, and has zero
uploads, dispatches and budget reservations. `--inspect-installation` explicitly
permits only GET inventory on the configured loopback ComfyUI URL with bounded
request timeouts. It records installed node input schemas and checks binding
presence, live length limits and model filenames. Node or filename presence is
**INVENTORY_ONLY**, not verified reference conditioning, loaded model hashes or
working video generation. Non-loopback URLs are rejected before connecting.
All commands accept explicit `--allowed-root` source roots; these must also
include the configuration root. No model path is supplied through these commands.

Preflight reports each unresolved gate independently: missing explicit workflow,
unsupported workflow/output class, missing prompt profile or subject, mismatched
FPS/duration/frame count, unsupported alpha, missing tools/bindings/models/nodes,
unverified reference role/count consumption, unverified model content and missing
generation authorization. Current video config lacks a `model_profile`; the code
does not borrow the parent's still-image dialect or manufacture a new subject.
The canonical source Brief and requested motion remain in the plan for later
compilation once an appropriate explicit video profile is verified.

Prepare copies all 1/2/3 images without composition or dropping references,
records exact role/order/hash and source/configuration fingerprints, and ends at
**PREPARED_BLOCKED**. It writes no executable graph and no budget authorization.
Outputs must be a fresh directory under the configuration root's workspace.
Failures keep intermediates with FAILED status; existing runs cannot be replaced.
Inspect revalidates source hashes, roles/order, copied bytes and configurations;
it rejects changed generation/review flags. It is not a resume/approve command.
The original still/run is never written. Filesystem replacement between checks
and reads remains subject to the existing trusted local ownership assumption.

## Implementation and evidence limits

Changed: `providers/video/__init__.py`, additive CLI commands,
`tests/unit/test_video_preflight.py`, this document and README/CHANGELOG.
The tests use synthetic source files and fake GET inventories. Every upload,
queue, poll and download method is forbidden in offline fixtures. The suite
checks no generation from planning/preparation, unsupported requests, unavailable
backend, hash/configuration/role drift, copy failure and exact input preservation.
Synthetic node inventories do not establish actual installed capabilities.

There is deliberately no readiness promotion: `generation_allowed=false`,
`reference_consumption=NOT_VERIFIED`, `game_ready=false` and REVIEW_REQUIRED.
Factory `execute` IMAGE_TO_SPRITE and legacy NONPIXEL_ANIMATION execution remain
blocked. This change does **not** complete the generation adapter or real I2V E2E.
Next: verify local installation, configure an evidence-backed video prompt
profile and exact reference mapping, then implement the one-request research
executor with a separately authorized real-generation budget. Do not bypass
these gates by restoring the discarded project-specific executors.

Rollback: revert this change commit. Existing packaging, still images, SFX,
six MCP schemas, Golden/SOT and runtime pointers are unchanged. Preserve prepared
directories and any failure evidence. Validation results are recorded in
[the dated evidence report](MOTION_PREFLIGHT_VALIDATION_20261023.md).
