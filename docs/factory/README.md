# M3 factory planning index

**Current priority (2026-10-27):** build the nonpixel still/animation pipeline;
pixel paths remain a research workstream. See the
[current production plan](NONPIXEL_PRODUCTION_PLAN_20261027.md).
Explicit still/audio dispatch and opt-in Factory motion jobs are implemented.
Existing-video replay and native engine imports have dated evidence; generic
Factory motion dispatch, new-coordinator real generation, human quality acceptance
and production activation remain blocked/unverified. See
[motion integration evidence](MOTION_JOB_VALIDATION_20261027.md).

Implementation references: [M3.0 contract](M30_OFFLINE_CONTRACT.md), [M3.1 SFX](M31_SFX_OFFLINE.md).

Execution boundary: [explicit still/audio dispatch](FACTORY_EXECUTION.md).

## Read in order

1. [Factory Architecture v1](FACTORY_ARCHITECTURE_V1.md) — four lines, conditional IMAGE_ONLY vs IMAGE_TO_SPRITE, versioned request envelope, multi-image role and provenance policy, child run isolation, release boundaries.
2. [M3 Factory Workplan](M3_FACTORY_WORKPLAN.md) — main-branch inventory, phased implementation M3.0..M3.6, proposed PR order, negative tests, E2E gates and definition of done.
3. [Project reorganization, 2026-10-11](PROJECT_REORGANIZATION_20261011.md) — integrated main, preserved local work, actual runtime boundaries and stabilization-first backlog. No M3 implementation or generation is authorized by this inventory.

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

The D PIXEL64 row is the historical factory design. The 2026-10-27 priority
decision defers its production work to research and makes it independent of
nonpixel delivery; it does not remove code or activate/deactivate a registry.

No runtime files, registry entries, workflow graphs, operational status, SOT documents, or approved masters are changed by this planning package.

Current preservation review: [uncommitted-work triage, 2026-10-14](../maintenance/UNCOMMITTED_TRIAGE_20261014.md). Historical inventories below do not supersede current execution contracts.
