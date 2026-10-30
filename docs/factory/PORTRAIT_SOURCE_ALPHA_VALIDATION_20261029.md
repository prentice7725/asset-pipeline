# Portrait source and alpha handoff validation — 2026-10-29

Scope: the existing NONPIXEL project portrait path, with the existing Krea2
workflow, U2NetP/rembg model and `LOCAL_MASK_UNIFORM_CONTAIN` delivery profile.
No new provider, style, public schema, MCP tool, pixel processing or deployment.
The user authorized pipeline verification without a fixed generation-count cap;
each live job still uses a separate one-request authorization and durable ledger.
Human identity/art acceptance remains required.

## Reproduction and controlled trial

The earlier human candidate had a patterned opaque background, broad alpha residue
and mottled rendering. Its generator prompt contained the final delivery request
`transparent alpha; no baked background`, although the T2I workflow renders RGB
and the delivery stage supplies alpha locally.

One controlled job changed only the technical source-background instruction, plus
the asset ID used to separate evidence. Seed `20261029`, model/workflow, project
style, character requirements, generation parameters, final RGBA dimensions and
the initial segmentation algorithm were held fixed. Its separate authorization
is `b44d7212fa5c49a5a9d5a5c80071c3d6`. The resulting raw image had a plain white
background and visibly flatter skin/clothing; broad segmentation fringe remained.
This is one paired observation, not a general success rate or identity test.

## Initial implementation (2026-10-29)

- For the registered local-alpha portrait profile only, deterministic compilation
  supplies a uniform white opaque source backdrop. It preserves the original
  Brief and final transparency constraint and records the requested environment
  separately in compiled metadata. Ordinary scenes and environment layers retain
  their own scene prompts. Workflow graph, model and style bindings are unchanged.
- Reuse the pinned rembg segmentation and its existing closed-form matte estimator
  with fixed library defaults (foreground 240, background 10, erosion size 10).
  Call the estimator directly so its failure cannot silently fall back to naive
  compositing. Save the raw segmentation, matte estimate, final alpha and audit.
- Use only the estimated alpha. Foreground-color estimates visibly recolored the
  old patterned source's uniform, so the final implementation preserves source
  RGB exactly before the existing uniform resize. The estimate remains an
  intermediate, not the delivered color image.
- Give segmentation a white context border, fixed at 10% of the shorter source
  dimension. Preserve that input and full predicted mask, then map the mask back
  to exact source coordinates before matting. The three-image offline comparison
  restored the fresh sample's missing shoulders. It did not solve white hair-edge
  islands or the old patterned background. No source image is padded or cropped
  in final delivery, and no per-image parameter was selected.

No per-image threshold tuning, morphology painting, identity redesign or manual
cleanup was used. Source images, earlier failed/poor candidates and their immutable
receipts remain unchanged. A matte failure, invalid output or constant alpha
stops delivery and preserves evidence; it cannot emit a final portrait.

## Offline and real-image verification

The initial regression tests reproduced missing source-stage separation and a
matting exception incorrectly reaching naive final delivery. After implementation,
**20 project portrait tests passed**, including actual installed-library white
clothing preservation, exact pre-resize RGB preservation, failed matte handling,
opaque/invalid output blocking, context-to-source mask geometry, preserved white
context input, invalid context mask blocking and unaffected ordinary scene prompts.

Both original human RGB renders were reprocessed through the changed code with
zero new generations. Source hashes and every pre-resize RGB pixel matched their
originals. The compiled positive prompt equals the controlled trial's actual
prompt. Light/dark review composites are retained. The patterned old source still
has contamination; source-background preparation and alpha estimation are both
necessary, and neither automatically certifies artistic suitability.

An earlier full regression was stopped after the foreground-color issue was
identified, before final RGB preservation was validated. Its partial log remains
separate and is not a PASS. The RGB-preserving version before context preprocessing
passed 807 tests with 1 local-benchmark skip. The final context version completed
on 2026-10-30 with **808 passed, 1 skipped** in 900.03 seconds. The skip remains
the unavailable local migration benchmark. Evidence hashes are in the
[small evidence summary](PORTRAIT_SOURCE_ALPHA_EVIDENCE_20261029.json).
A context-version full run with a workspace-local pytest temporary directory
stopped making visible progress and was terminated without claiming PASS. Its log
is retained as `pytest-context.log`. The final run uses the normal temporary
directory, verbose progress and a 90-second diagnostic stack dump to distinguish
actual results from a stalled execution. The initial sandbox-local focused run
also encountered Windows temporary-file replacement permissions; the workspace
temporary-directory focused run passed all 20 tests.
The diagnostic stack captured a wait inside an actual Aseprite subprocess, and
the slow test subsequently passed. This is retained as execution evidence rather
than attributing the delay to portrait matting or hiding the interrupted run.

Two full-path jobs exercised the source-background compiler and RGB-preserving
matting delivery before the context change. The same-seed job
`55bef7d7a9a7469faa9e309ce5e841c4` used ComfyUI's cached sampler and decoder; it
does not count as fresh model inference. The seed-20261030 job
`2d9d6e0255e34ffba2ff655c8c3a3ecd` executed sampler and decoder, as confirmed by
its successful history with neither node 3 nor node 8 cached. Both delivered
1212x1300 RGBA and remained candidates. Final context code was then replayed
against the original patterned, controlled plain and fresh immutable raw images
with zero further generations. It preserved source bytes and all pre-resize RGB
pixels, without revising any original execution receipt.

## Review and operational boundary

The controlled plain-background candidate has substantially less broad fringe
than the original segmentation delivery. White hair-edge islands and residual
fringe remain visibly unacceptable for a clean-alpha acceptance claim. The source
also reaches the top image boundary: local alpha and
contain-fit cannot reconstruct missing framing. Colors, casting, style fidelity
and identity preservation are not approved by this trial.

Result: technical generation/delivery wiring and automated regressions passed;
clean-alpha visual validation did not pass. No human Identity Base was selected,
and expression editing or motion must not advance on an invented approval.

All outputs remain candidates, `game_ready=false`; no human review, Golden,
production activation or live MCP replacement is implied. This branch was tested
in the dedicated portrait environment; the original checkout's pending Codex and
policy changes were preserved separately.

Local evidence is in the original checkout's ignored
`workspace/isekai-human-identity-20261029/background-source-probe/` and the original
Factory budget run directories. Only the small Markdown/JSON evidence summary is
tracked. Rollback reverts the compiler/portrait/tests/docs changes while preserving
all original inputs, outputs and spent authorizations.

## Follow-up: white gaps, edge RGB and framing (2026-10-30)

The prior RGB-exact implementation preserved an incorrect handoff assumption:
source RGB at translucent edges already contains white backdrop. Reusing it as
straight-alpha RGB blends white a second time on a dark background. A synthetic
50%-alpha colored edge reproduced this at the actual delivery call site before
the correction. A separate minimal test reproduced an open white hair gap that
the segmenter confidently mislabeled as foreground. Both tests failed before
their fixes; they are not acceptance scores inferred from image similarity.

The corrected handoff keeps the existing model and matting estimator:

- Propagate the existing mask's confident background (`mask < 10`) through source
  pixels whose RGB channels are all at least 245, with four-neighbor connectivity.
  Do not use temporary padding or canvas edges as seeds. Keep enclosed white
  details and isolated bottom-edge white clothing. Preserve both raw and refined
  masks, source-background evidence and the uncorrected cutout.
- Verify that at least 99% of confident-background samples satisfy the white-source
  contract. Reject other backdrops before matting/unmatting instead of silently
  applying a white-background formula. The old patterned render now exercises
  this expected rejection; its historical outputs remain unchanged.
- Use only estimated alpha, then remove white contamination from translucent
  RGB by the compositing equation. Preserve all fully opaque source RGB and the
  alpha channel exactly. The estimator's foreground colors are still discarded.
  This supersedes the initial all-pixel RGB-exact policy, while retaining original
  source RGB as a separate intermediate. No opaque palette/identity redesign occurs.

On the earlier fresh source, 362 near-white pixels connected to confident
background were opaque before correction and zero afterward. Original source
bytes stayed unchanged. This is a measured defect reduction on that source, not
a universal alpha-quality claim.

Three separate one-request ledgers preserve full-path validation. The first,
`bd11dc2688714b59a604d75584733ff7`, used qualitative headroom wording but still
clipped the hairstyle (172 opaque top-edge pixels); it is a framing failure.
The second, `ad82485c22ef4b75b558c9604e7088d9`, changed only composition wording
to request 12% blank space above the head at the same model/style/seed. It has
96 rows of visible headroom and no opaque top-edge pixels. Its measured margin
is about 7.4%, so exact 12% compliance is not claimed. Both sampler and decoder
executed freshly in these trials. The final handoff run
`cafbb34ff7924de3a31afef888ed90d6` retains the second trial's exact prompt/seed
and exercises the final local RGB/alpha code in a new immutable receipt; its
cache status and hashes are recorded separately.

The core portrait suite passed 24 tests after the final changes. An earlier full
run, before translucent-edge recovery was implemented, hit the existing fake-CLI
one-second timeout test: timeout/one attempt were recorded but the child call log
had not appeared. The unchanged test passed alone afterward. That interrupted
full run is retained and is not a PASS. The final full regression and immutable
evidence hashes are recorded in the
[follow-up summary](PORTRAIT_SOURCE_ALPHA_REFINEMENT_EVIDENCE_20261030.json).
The final full run passed **812 tests with 1 skipped** in 779.14 seconds, including
the unchanged CLI timeout test. The skip is the unavailable local migration
benchmark. Editable installation with dev/motion/MCP/portrait extras and CLI help
also completed in the dedicated portrait environment. Final real-source replays
passed for three white-background sources and rejected the old patterned source
at the expected background gate; no source bytes were altered.

All generated outputs remain candidates. Hair edges, colors, source casting and
style fidelity require human review. A white foreground
connected indistinguishably to a white backdrop is not proven safe by these tests.
The user subsequently selected the final handoff candidate as the Identity Base
on 2026-10-30; the separate selection record pins its manifest and image hashes.
This choice is not final art approval. The surprised-expression plan using the
explicit existing Grok editor then reproduced
`IDENTITY_VARIANT_ROUTE_BLOCKED: Explicit workflow/model conflicts with style menu binding`.
No variant budget was reserved and no edit was generated. The project SOT and
exact resolution/alpha requirements remain intact. A separate project reference-
edit contract decision is needed; an offline bounded proposal is retained with
the local evidence. No SOT override or operational activation occurred.
