# Project portrait reference edit validation — 2026-10-30

The user explicitly authorized the proposed project-specific reference-edit
contract and local RGBA delivery on 2026-10-30. The selected human base remains
the exact PNG SHA-256
`4f20aa36e0785472925252664c27aa4c76febf52f27f4aff36b3a0e5569c40df`.
Its selection is not Golden/final art approval.

## Contract and safeguards

The new topic branches from portrait-alpha commit `591f2d2`. The original checkout's
pending Codex-reference implementation is separate. No live MCP replacement,
production activation or public plugin publication occurred.

The isekai portrait SOT explicitly permits only the existing Grok editor for an
explicit single RGBA reference, final 1212x1300 alpha and human review. Base T2I
remains Krea2-bound, and the STYLE-104 definition/fingerprint is unchanged. Its
Grok recipe is `UNTESTED`; registry/native capability flags remain experimental.
Local delivery supplies final alpha/size, not an invented native Grok capability.
Unsupported projects/editors and changed final constraints remain blocked.

The plan pins the project SOT file hash and effective contract. A changed SOT
invalidates the plan before budget reservation; the execution's compiled contract
and exact RGBA reference-copy record are compared with that plan afterward.
Expression edits replace the parent's old expression instructions while retaining
body pose and the fixed preserve list. Reference editing does not reapply the
T2I headroom/crop instruction. The six MCP schemas and public variant job schema
remain unchanged; the authorized project SOT configuration gains the edit policy.

## Actual execution and correction

1. `b23e1777fd4a4257b5589bba01627f6e`: one actual `image_edit` returned an opaque
   light-gray source. White-background verification rejected it. The run and
   variant receipt remain FAILED, with raw output, masks and audit preserved.
2. Diagnosis measured median background RGB `[240,242,241]`; 99.9927% of confident
   background samples lay within 10/channel. Offline replay used the same source
   without generation and recovered RGBA while preserving opaque source colors.
3. The reference-only policy now measures a light neutral background: every
   median channel >=220, channel range <=10, and at least 99% of confident samples
   within 10/channel. Source-connected background propagation and edge RGB
   recovery use that verified color. Default T2I keeps its fixed white rule.
   A nonuniform neutral-pattern fixture is rejected; the gate is not skipped.
4. A distinct corrected validation, `48adc226d31e4f5ea933c39bd9e3fa77`, used a new
   job and authorization ID. One actual `image_edit` completed through local
   delivery and basic QA, producing 1212x1300 RGBA. Its measured backdrop was
   `[240,240,239]`, with 99.9954% uniform-background support. No reservation was
   reused and no automatic retry/provider fallback ran.

Both exact invocation chat histories confirm one `image_edit`, one image argument
matching the copied reference path, and the provider's selected base hash. This
proves reference dispatch, not visual identity preservation. The original failed
receipt is not relabeled PASS by later offline processing or the new execution.

Successful output SHA-256:
`79ccf570b995d1402f21e0626bf4065c206e1e273d7413378fc9e453ce4fb3cc`.
The coordinator reports `CANDIDATE_REVIEW_REQUIRED`, `identity_review=HUMAN_REQUIRED`
and `game_ready=false`. Side-by-side comparison is retained for human assessment
of face, hair, clothing, style, pose and framing. No machine score or human
approval is fabricated.

On 2026-10-30 the user answered **"동일 인물 변형으로 수용"** to the comparison's
face/hair/uniform/style/body-pose/framing review. The separate human-review record
binds the exact base, edited output, comparison, manifest and receipt hashes.
Identity preservation is therefore **ACCEPTED_BY_USER** for this expression
candidate. Immutable run receipts retain their original `HUMAN_REQUIRED` state;
the later human decision is recorded separately. Final art, Golden and Aseprite
approval remain ungranted, and `game_ready` remains false.

## Checks and evidence

Focused tests cover project-only routing, unchanged T2I/other-editor blocking,
fixed size/alpha, neutral-expression conflict, copied RGBA hash, local delivery,
SOT plan invalidation before reservation, one request and spent-budget rejection.
Background tests cover white and measured-neutral compositing, preserved opaque
RGB/alpha, and nonuniform-source rejection. An earlier full test run was stopped
when pre-generation semantic review found the neutral-expression conflict; its
partial log is not PASS.

The final full run passed **821 tests, 1 skipped** in 419.99 seconds. The skip is
the unavailable local migration benchmark. Editable installation with
dev/motion/MCP/portrait extras and CLI help also completed in the dedicated
portrait environment. The tested entrypoint is the current development CLI;
the installed MCP runtime was not replaced.

The final full regression, code hashes, real run/receipt hashes and human review
state are in [the compact evidence summary](PROJECT_REFERENCE_EDIT_EVIDENCE_20261030.json).
Images and sessions remain in ignored local workspace/provider directories; only
small Markdown/JSON summaries are committed. Generic M1 promotion and formal
`provider_e2e.py` evidence are separate and are not inferred from this project trial.

Rollback reverts this branch's project policy, compiler/route/provider/coordinator
changes and tests/docs to `591f2d2`, retaining selected input, raw results, failed
receipts and spent authorizations. It does not revert the prior portrait-alpha fix.
