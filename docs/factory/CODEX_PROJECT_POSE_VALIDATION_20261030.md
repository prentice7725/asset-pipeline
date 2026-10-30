# Codex project pose validation — 2026-10-30

State: **REAL_POSE_EDIT_TECHNICAL_PASS / IDENTITY_ACCEPTED_BY_USER**.
This verifies the existing POSE path on source commit `655e45c`; no pipeline
code, project contract, style, registry or public schema changed. It follows the
[expression edit validation](CODEX_PROJECT_REFERENCE_EDIT_VALIDATION_20261030.md)
and its offline correction of the shared body-pose prohibition.

## Input and explicit trial

The same user-selected Nakamura Yuto school portrait is the sole reference:
`4f20aa36e0785472925252664c27aa4c76febf52f27f4aff36b3a0e5569c40df`.
The derived test action raises his right hand beside his shoulder, palm toward
the viewer, while retaining the neutral expression, head/gaze, torso, portrait
framing, canvas, face, hair, school uniform and STYLE-104 rendering. It does not
introduce a canonical character action or approve unspecified colors.

The compiled plan passed source/base/prompt review without the contradictory
body-pose prohibition. Verification uses the standing uncapped-count approval,
with each run explicitly reserved for one attempt and no automatic retry or
provider fallback. This is not operational generation authorization.

## Failure and distinct corrected execution

1. Authorization `53a978879fb14f069eb85f983b0c53dd` was consumed by a failed run.
   Codex exited before native session initialization: app-server/profile access
   was denied under the host sandbox. Stdout was empty; no image-generation tool
   ran. Its failed receipt, stderr, plan and authorization remain preserved.
2. After diagnosis, authorization `e665026801ed4ecb9ef98eb79640fb26` reserved a
   distinct run. Host execution allowed the existing Codex profile to initialize;
   native Codex `--sandbox read-only`, isolation, prompt, QA and preservation
   rules remained in effect. The failed authorization was not reused.

There were **two CLI invocations and two reservations**, but **one actual image
tool call**. The successful own native session
`01a18bf7-d24c-7aa3-a285-d4acb7085f99` records one decoded PNG attachment matching
the selected base hash, one `exec` wrapper invoking `image_gen` once with that
invocation's copied RGBA, and one matching tool result. No other tool methods or
automatic fallback were observed. CLI version is `0.164.0`; the observed agent
model does not identify the underlying image-generation backend.

Local processing retained the original image, verified opaque RGB before resize
and produced **1212×1300 PNG RGBA** with basic QA passing. Output SHA-256:
`154e38265f4925bbabb990548f1f0529417a86a663bf8554e64752082aba137f`.

## Visual and human review

The reviewed output shows the right palm facing the viewer with five visible
fingers and a neutral expression. Pale fringes around dark hair remain a final
alpha/art review item; this trial does not polish or approve those edges.

The user answered **“포즈 변형도 동일 인물로 수용”** for this exact comparison.
A separate human-review record pins the base, output, comparison, manifest and
receipt hashes. It accepts identity preservation for the pose variant only.
Immutable execution receipts retain HUMAN_REQUIRED / REVIEW_REQUIRED; final
art, Golden/Aseprite and operational activation remain unapproved and
`game_ready=false`.

## Checks and preserved evidence

The [compact evidence summary](CODEX_PROJECT_POSE_EVIDENCE_20261030.json) includes
both runs, hashes, native attachment/tool audit, local RGBA checks and the exact
user review. Images, full session records and intermediates remain in ignored
workspace paths. Artifact hashes, native audit and delivery checks passed.

No new full pytest run is claimed for this evidence-only change. The unchanged
pipeline source previously passed **845 tests, 1 skipped**; its earlier evidence
is linked separately. Both providers remain experimental and explicit-only;
generic M1 T2I promotion, live MCP replacement and production use are not implied.

Rollback removes this validation summary/report and index updates while retaining
both spent reservations, raw artifacts and immutable execution records.
