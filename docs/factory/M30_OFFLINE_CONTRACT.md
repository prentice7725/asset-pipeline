# M3.0 — offline factory contract

Version 1 is an envelope separate from the unchanged Asset Brief.
`schemas/factory_request_v1.schema.json` validates structure; `assetpipe.factory`
also checks paths, hashes, roles, parent identity and project binding.

| Line | Terminal modes | Source kinds | Planned output class |
| --- | --- | --- | --- |
| NONPIXEL | IMAGE_ONLY / IMAGE_TO_SPRITE | GENERATE / EXISTING_RUN | NONPIXEL_IMAGE / NONPIXEL_ANIMATION |
| REFERENCE_MOTION | IMAGE_TO_SPRITE | EXTERNAL_IMAGES / EXISTING_RUN, 1..3 images | NONPIXEL_ANIMATION |
| SFX | AUDIO_ONLY | GENERATE | SFX |
| PIXEL64 | IMAGE_ONLY / IMAGE_TO_SPRITE | GENERATE / EXISTING_RUN | PIXEL_STATIC / PIXEL_ANIMATION |

Run `assetpipe factory plan --request request.json`, `factory dry-run`, or
`factory inspect` to revalidate and print a plan. They do not dispatch, allocate
providers, reserve budgets or approve. IMAGE_ONLY/AUDIO_ONLY have no video tasks
or video dependency probes. The default root is `--root`; repeated
`--allowed-root` options supply the complete explicit source-root list.

Requests and linked documents are JSON. Relative inputs resolve from the request
directory; document references resolve from their containing document. Resolved
symlink/junction escapes are rejected before reads/hashes. Duplicate roles,
physical images or content fail closed.

GENERATE requires `brief_ref` with matching project, asset and output class.
EXISTING_RUN requires `manifest_ref`, `manifest_sha256` and image records (`path`,
`sha256`, `role`). Images must be recorded outputs; the original validated Brief,
identity and model choices remain unchanged. Missing parent Briefs block planning.
EXTERNAL_IMAGES additionally require ownership/license declarations, which do
not establish legal rights. Roles are IDENTITY_PRIMARY, ALTERNATE_VIEW,
POSE_ANCHOR, START_FRAME, END_FRAME and STYLE_REFERENCE; actual backend input
consumption remains unverified.

PIXEL64 requires explicit logical 64x64 in request and source Brief, without 32px
promotion. Motion is a separate child run; frames/sprites belong to it and must
bind exact source receipts before dispatch. A valid plan returns
`OFFLINE_CONTRACT_PASS` and `NOT_IMPLEMENTED_FACTORY_DISPATCH`; execution, QA,
review and SOT gates remain pending. Motion retains `BLOCKED_BACKEND_NOT_VERIFIED`.
Legacy routing, motion fixtures and six MCP schemas remain unchanged.

See [M3.1 SFX metadata](M31_SFX_OFFLINE.md).
