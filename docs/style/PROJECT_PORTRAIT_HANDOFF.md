# Project portrait handoff

The isekai examiner portrait contract is registered under
`config/styles/projects/isekai_examiner/visual_sot.yaml`. It applies only to
`character_portrait` and the explicitly selected `environment_background_layer`.
The common STYLE-104 catalog, model, workflow and all review gates are unchanged.

Use `project_id: isekai_examiner` and `project_contract_required: true` in the Brief.
This explicit requirement blocks an unregistered project instead of silently using
the common catalog. Existing Briefs without this opt-in remain compatible.

A portrait uses `subject_integrity.class: character_portrait`,
`whole_subject_required: false`, `physically_connected_body: true` and explicit
source-required visible parts. A full-character contract is not a bust contract.
For this project adaptation, omit `prompt_spec.style_contract_id`: the project
style is source-backed descriptors, not the unchanged common structured contract.
Preserve Brief style descriptions, sources, identity and all forbidden requirements.

## Explicit project production path

The user selected positive natural-language exclusions plus mandatory human review.
The project-scoped policy preserves every project forbidden element and subject
substitution in the positive prompt and an itemized NOT_REVIEWED checklist. Krea2
still has no native negative support. Other projects retain native subject gates.

Install the optional `portrait` dependencies. The configured local U2NetP model
must be inside configured roots and match SHA256
`309c8469258dda742793dce0ebea8e6dd393174f89934733ecc8b14c76f4ddd8`.
Official source: https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2netp.onnx
Production never downloads weights or falls back to another model.
For this explicit local-alpha profile, the compiler renders an opaque, uniform
white source backdrop and records the requested environment in `portrait_source`.
The Brief's final transparency requirement remains unchanged. Ordinary images
and environment layers keep their original scene prompts.
The compiler also requests complete hair within the canvas and visible headroom,
while retaining requested composition in metadata. This is a prompt instruction,
not a guaranteed framing result; inspect the generated source. A later trial with
explicit numeric headroom in the Brief avoided top clipping but did not exactly
meet its requested 12% margin.

For segmentation only, the processor adds a fixed white border of 10% of the
shorter source dimension, then maps the predicted mask back to original source
coordinates. It preserves the padded model input and full context mask as evidence.
Source framing, RGB and final contain-fit geometry remain unchanged.

The processor preserves the raw segmentation mask, rembg matting estimate, final
alpha, uncorrected source-RGB cutout, corrected cutout and final PNG. Before
matting, existing confident-background seeds propagate only through source pixels
within 10/255 of white using four-neighbor connectivity. Canvas edges and temporary
padding never seed removal, so an isolated white shirt touching the bottom remains.
At least 99% of confident-background samples must match that white tolerance;
otherwise delivery fails and preserves evidence. This is not a general color key
for arbitrary backgrounds or unoutlined white foreground touching white backdrop.

The processor discards estimated foreground colors. Fully opaque RGB stays exact;
only translucent RGB is recovered using `C = alpha*F + (1-alpha)*white` before
uniform resizing. This prevents white-backdrop contamination when recomposited on
dark backgrounds. Alpha is unchanged by RGB recovery. `alpha_processing.json` records fixed parameters,
library versions, hashes and failures. A matting error stops the run with no
fallback to naive compositing. Hair, clothing, edges and identity need human review.

Generate at 1216x1304, apply local segmentation and alpha matting, then uniformly contain-fit and
transparently pad to 1212x1300. No crop is applied. Scale and offsets are recorded.
Existing-image execution validated RGBA and exact dimensions; this is processor
evidence, not generation E2E or art approval. ComfyUI readiness is a separate gate.
The [2026-10-29 source/alpha validation](../factory/PORTRAIT_SOURCE_ALPHA_VALIDATION_20261029.md)
adds real generation and offline replay evidence, including remaining quality failures.

## Project portrait reference edit

For the explicitly authorized portrait reference-edit contract, see
[identity variants](../factory/IDENTITY_VARIANT.md). It retains STYLE-104 and the
Krea2 base path, but binds an explicit Grok reference input to local RGBA delivery.
The reference is copied byte-for-byte; a verified uniform light neutral backdrop
may be measured for compositing. Ordinary T2I retains the white-background rule.
No native Grok alpha/exact-resolution capability or style approval is implied.

## Environment STYLE-111 route

For the Day 01 backwall, the prepared Brief sets `project_id: isekai_examiner` and
`project_contract_required: true`. STYLE MENU v1 maps `watercolor_storybook` to
STYLE-111/Krea2. The project Visual SOT supplies an environment-specific, UNTESTED
descriptor adaptation and recipe, so `style_selection` identifies
`PROJECT_VISUAL_SOT` and does not take the character-focused COMMON_STYLE_CATALOG
definition. The route also reports the menu source and its CAND-011 exemplar
separately; CAND-011 is the exemplar recorded by the current STYLE MENU v1 entry.

The wall-only opaque layer uses positive natural-language exclusions and the
mandatory per-item review contract. Native Krea2 negative support remains false.
The recipe and style stay UNTESTED, and no generation or art approval is implied.

No generation or seed submission is part of this repair. Recipes and style remain
UNTESTED; every candidate still requires actual human review.
