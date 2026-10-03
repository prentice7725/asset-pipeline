# Advisory visual hierarchy — initial implementation

Authorized on 2026-10-03. Existing production defaults, six MCP tool schemas,
technical QA and approval algorithms are unchanged. No generation budget is
authorized by this implementation. Real artistic improvement remains NOT_TESTED.

## Current user-directed scope — 2026-10-03

Three independent tracks must not be conflated:

- Anima + Pixelate x4 VAE: verify a 1024x1024 generation followed by explicit
  nearest-neighbor conversion to 256x256. This path is currently NOT_VERIFIED;
  prior 512x768 raw-output gate failures do not establish its result. Preserve the
  original and conversion settings, measure the converted candidate and keep all
  technical gates and required human reviews. A 256x256 PNG alone is not proof of
  coherent pixel clusters or preserved identity. Do not silently quantize colors,
  resize again to 64/32, swap VAE variants or change production defaults.
- Krea2 64px LoRA plus the existing creator Refiner: local 64x64 generation and
  Pixel Gate were verified in two recorded runs. Image quality still requires
  improvement and human review; keep EXPERIMENTAL / EXPORT_READY_REVIEW_REQUIRED.
  See ../research/KREA2_PIXEL64_SMOKE_20261003.md. This is not an approved Static
  Master or complete authored-adapter compatibility claim.
- Visual Hierarchy evaluation: NONPIXEL_IMAGE only, with a complete character
  and background in the same scene. Use existing M2.6 candidate/recipe compilation
  and existing execution/QA paths. Keep each pair's recipe, style, model/workflow,
  scene requirements and supported seed fixed; change only the declared composition
  direction. Preserve required background clues. Pixel generation and pixel quality
  improvement are not evidence for this evaluation.

The existing visual-review CLI may still create advisory pixel previews; that does
not enroll pixel candidates in the Visual Hierarchy experiment. The recipe-free
four-image scene cohort is historical exploratory evidence, not M2.6 validation.
Its budget is exhausted. A separately user-started corrected M2.6 comparison has
now executed four requests under workspace/visual_hierarchy/m26_scene_comparison_20261003.
It used mined_clean_anime_cel / clean_anime_cel__anima_base and the existing
style_lab.execute_prepared path. All four dispatched prompts matched the M2.6
compilation; all four technical QA reports passed. Both focus variants depict
detached clothing rather than a complete scout, and baseline character heads are
unclear. Focal composition improvement is NOT_VALIDATED; human review remains
NOT_REVIEWED. This is not a general model-quality conclusion or style approval.
The experiment used existing PromptSpec composition, not the new optional
art_direction field with styles. No retry, fallback or automatic promotion occurred.

## 1. Existing candidate review

```powershell
assetpipe visual-review --run workspace/runs/example --image workspace/runs/example/output.png
```

Only PIXEL_STATIC or NONPIXEL_IMAGE runs in CANDIDATE_READY_REVIEW_REQUIRED or
EXPORT_READY_REVIEW_REQUIRED are accepted. Failed technical steps block this
command. The selected image must be a manifest output inside the run directory;
multiple outputs require an explicit selection. This command does not approve,
revalidate or advance a run. Manifest, originals, QA and approval records remain
untouched. Each invocation creates a separate review_artifacts directory.

Artifacts: byte-identical original copy, native matte preview, 64px-long-side
thumbnail without upscaling, grayscale thumbnail, blurred thumbnail and labeled
contact sheet. Pixel previews use nearest-neighbor; illustrations use Lanczos.
Blurred pixel previews are advisory value-mass views, never production assets.
The sheet is for presentation; exact-size preview PNGs are authoritative for scale.
`--matte R G B` records the transparency-compositing background (default white).
`--display-size WIDTH HEIGHT` creates a preview at the explicitly supplied display
size; it does not establish actual game context, cropping or accessibility.
Without display rules context review is marked unavailable.

visual_review.json records source/manifest hashes, preview hashes, Pillow version,
settings, asset role and checklist decisions, initially NOT_REVIEWED. A human may
write decisions and notes with their identity/time/reason in this companion file;
it is advisory and never substitutes for Aseprite or formal Static Master approval.
No quality scores, segmentation metrics or universal thresholds are introduced.

## 2. Optional nonpixel focal intent

Prepared Asset Briefs may supply:

```yaml
art_direction:
  version: 1
  authority: EXPLICIT_BRIEF
  source: "User's explicit asset brief"
  primary_focus:
    - visible insignia
```

Each focus must exactly match an existing canonical trait, visual trait, PromptSpec
appearance or subject. Arbitrary new anatomy, equipment or identity is rejected.
This is explicit authoring input, not automatic interpretation of source documents.
PromptSpec's public schema is unchanged: focal intent becomes a composition sentence
compiled by the existing Anima, Krea2 and natural-language adapters. Brief schema
has the optional new field. Missing intent produces identical compiled output.
Route and compiled prompt retain the intent, hash and INTENT_ONLY_REVIEW_REQUIRED.
Existing generation records retain these through the brief and compiled prompt.

The initial version conservatively blocks intent together with an existing
composition, style descriptors, styleSources or resolved catalog/pack/SOT selection,
using ART_DIRECTION_CONFLICT_REVIEW_REQUIRED before provider dispatch. It cannot
reconcile arbitrary free-text style conflicts. Keep the source composition/style
and express the reconciled direction there; do not remove a project lock to make
the new field pass. PIXEL/SFX reject this field. Native negative and text capability
checks remain mandatory. Focus does not authorize removal of required clues or gear.

Grouped shadows, restrained textures, background recession, role-dependent automatic
direction and support for combining independent intent with locked styles remain
deferred until their conflict contracts are specified. 70:20:10 is not a gate.

## 3. Real comparison next

Before submitting requests, choose a fixed model/workflow, matched source briefs,
explicit total request budget, preserved model/workflow hashes and provider preflight.
Reserve budget before dispatch; no retries/fallback. Preserve original prompts, seeds
where supported, receipts, outputs and independent human notes. Test focal readability
and required-feature retention together. Technical tests do not prove art improvement.
