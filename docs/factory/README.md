# M3 factory planning index

**Status:** M3.0 offline contracts and M3.1 offline SFX receipts are implemented; factory dispatch, real milestone acceptance and runtime activation remain unimplemented/unverified.

Implementation references: [M3.0 contract](M30_OFFLINE_CONTRACT.md), [M3.1 SFX](M31_SFX_OFFLINE.md).

## Read in order

1. [Factory Architecture v1](FACTORY_ARCHITECTURE_V1.md) — four lines, conditional IMAGE_ONLY vs IMAGE_TO_SPRITE, versioned request envelope, multi-image role and provenance policy, child run isolation, release boundaries.
2. [M3 Factory Workplan](M3_FACTORY_WORKPLAN.md) — main-branch inventory, phased implementation M3.0..M3.6, proposed PR order, negative tests, E2E gates and definition of done.

## Decision register (2026-10-11)

| Decision | Value |
| --- | --- |
| A NONPIXEL | IMAGE_ONLY or explicitly requested IMAGE_TO_SPRITE |
| B REFERENCE_MOTION | 1..3 explicit existing image inputs; IMAGE_TO_SPRITE |
| C SFX | AUDIO_ONLY |
| D PIXEL64 | 64x64 IMAGE_ONLY or explicitly requested IMAGE_TO_SPRITE |
| 32px native pixel art | ON_HOLD_RESEARCH |
| Model/style selection | Keep existing 24-style menu, project SOT and model limitations |
| Motion generation | Shared A/B/D backbone only after verified ComfyUI backend support |
| Paid generation and deployment | Not authorized by design document; distinct gates |
| Approvals | All machine-generated output stays REVIEW_REQUIRED until actual review |
| Existing six MCP tools | Preserve compatibility; do not expand in planning PR |

No runtime files, registry entries, workflow graphs, operational status, SOT documents, or approved masters are changed by this planning package.
