# Codex project reference-edit validation — 2026-10-30

The user explicitly approved adding Codex to the portrait project edit contracts.
This topic branches from integration commit `1165490`; it does not activate a
live MCP runtime or production use. The standing verification-count approval
does not change the single-request reservation or human review rules.

## Contract and offline correction

The installed `codex-cli 0.164.0` reported ChatGPT login and an enabled
image-generation feature, and advertised `exec --image`. The first project plan
was blocked by the prior Grok-only binding; no generation/reservation occurred.
The user then approved the bounded project-contract extension.

`reference_edit_contracts` now explicitly names the existing Grok and Codex
workflow/model pairs. The old `reference_edit_contract` remains valid for legacy
single-editor configurations; declaring both formats, an empty map, an unknown
editor or mismatched model fails closed. Krea2 T2I, STYLE-104's definition and
fingerprint, the exact selected RGBA, preserve lists, final 1212x1300 alpha,
verified-background gates and human review are retained. The Codex recipe remains
UNTESTED, and native exact-resolution/alpha flags remain false.

The new Codex project route test failed under the old contract and passed after
the extension. Both providers' fake end-to-end tests check exact RGBA hashing,
pinned SOT invalidation before reservation, local delivery, one request and spent
authorization rejection. The focused suite passed 42 tests.

A later offline cross-check reproduced an inherited shared-composition ban on
body-pose changes that contradicted POSE jobs. Only this redundant shared ban was
removed; EXPRESSION keeps its body-pose lock in the coordinator and fixed preserve
list. The actual expression image below was generated before that redundant
clause removal and retained the same expression/body-pose intent. No additional
image was generated for this correction. The focused final suite passed 43 tests;
POSE behavior was checked offline, not by a real pose-generation trial.

## One actual reference edit

- Authorization: `9eccb362c3cc40ba82b8b7d43480220b`, `max_requests=1`.
- Base SHA-256: `4f20aa36e0785472925252664c27aa4c76febf52f27f4aff36b3a0e5569c40df`.
- CLI session: `01a18bca-733d-7270-a610-cac955d0188d`.
- Target: surprised expression, eyes slightly widened and mouth slightly open;
  retain face/hair/uniform/style/body pose/framing/canvas.
- Output SHA-256: `11e51d16bb81b8ce8ac475244911cfde263a861a8c43fbddadb3c7389c8e4347`.

The provider copied the input byte-for-byte and attached it with `--image`, with
the variadic argument terminated before the stdin prompt. The original read-only
sandbox, ignored user config/rules and isolated working directory were retained.
No permission relaxation, API-key bypass, automatic retry or fallback was used.

CLI stdout contained only thread/turn and final-message events, so its summary
alone was not treated as tool-use proof. The exact owned native rollout records:

- one initial PNG attachment whose decoded bytes hash equals the selected base;
- one `exec` wrapper calling `tools.image_gen__imagegen` once, with a single
  `referenced_image_paths` entry matching that invocation's copied RGBA;
- one matching tool result, and no other tool-method calls;
- one correlated original PNG under this same CLI session, preserved before
  local processing. Account metadata and transcript image blobs are not exported.

The observed agent model was `gpt-6.1-sol`; this does not identify the underlying
image-generation backend or establish exact reproducibility. Usage/billing beyond
what the CLI reports was not independently verified.

Local delivery measured backdrop RGB `[254,254,254]` with 99.9965% uniform-background
support, reused the pinned mask/matting model, preserved opaque RGB before uniform
resize and produced **1212x1300 PNG RGBA** with all basic QA passing. The receipt
is `CANDIDATE_REVIEW_REQUIRED`; the manifest is
`CANDIDATE_READY_REVIEW_REQUIRED`, with `game_ready=false`.

## Review, checks and evidence

The comparison shows the source and Codex output; human identity-preservation
review is requested for this exact output. The earlier Grok acceptance does not
approve the Codex image. Final art, Golden/Aseprite and operational activation
remain separate, including when identity preservation is accepted.

The final full regression, consent, source/code hashes, rollout hash, manifest,
receipt, raw/final hashes and current human-review state are recorded in the
[compact evidence summary](CODEX_PROJECT_REFERENCE_EDIT_EVIDENCE_20261030.json).
The final full suite passed **845 tests**, with **1 skipped** for unavailable
local migration benchmark data, in **710.80 seconds**. The editable install of
`.[dev,motion,mcp,portrait]` and `assetpipe --help` also completed successfully in
the dedicated portrait environment; the live MCP environment was left running.
Images, the full native session and environment remain outside tracked source.
The six MCP tools and public variant-job/Brief schemas are unchanged. Generic M1
T2I `provider_e2e.py` evidence and ACTIVE promotion are not claimed by this trial.

Rollback reverts this topic's project config/parser, tests and documentation to
`1165490` while retaining raw output, selected base, consumed authorization and
immutable execution receipts.
