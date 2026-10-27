# Explicit motion review recipe v1

This offline CLI path turns a completed NONPIXEL motion package into a separate
candidate using explicit frame selection and alpha instructions. It captures the
manual decisions from the fox experiment without generalizing their art choices.
It never generates, retries, chooses a loop automatically, changes a pivot,
approves human review or promotes a production provider.

## Contract and workflow

[Versioned JSON schema](../../schemas/motion_review_recipe.schema.json) and
[fox-shaped example](../../examples/motion_review_recipe.json) describe v1.
The example's source path/hash are placeholders and must be replaced. Its frame
range, white-background declaration and lower-body rectangles belong to the fox
example; do not silently copy them to another character.

Required fields:

| Field | Meaning |
| --- | --- |
| `schema_version`, `kind` | `1`, `MOTION_REVIEW_RECIPE` |
| `source_manifest`, `source_sha256` | Exact completed offline NONPIXEL package and its SHA-256 |
| `selection.start_frame/end_frame` | Explicit contiguous 1-based inclusive source range; no deduplication or resampling |
| `alpha.method` | `PRESERVE` existing alpha, or explicit `EDGE_CONNECTED_WHITE` |
| White-method declaration | Exactly `background_rgb:[255,255,255]`, `tolerance:60`; no background inference or other profile |
| Optional `alpha.cleanup` | Explicit half-open pixel rectangles and inclusive RGB minimum; clear alpha only for matching visible pixels inside those rectangles |

`PRESERVE` describes the initial alpha operation. If optional cleanup is supplied,
that explicit local edit still applies. White masking uses the existing connected
border utility only; it does not run/approve the blue-tunic pixel direct profile,
quantize colors or activate a portrait/animation segmentation model. Existing
source transparency is never turned opaque by masking. RGB is retained everywhere,
including under transparent pixels. RGB equality alone does not prove silhouette
or identity preservation after alpha changes; human review remains mandatory.

```powershell
# Store logs/plans outside the fresh candidate output directory.
assetpipe --root . motion-recipe-plan --recipe workspace/recipe.json > workspace/plan.json

# Use the exact plan_sha256 printed by the previous command.
assetpipe --root . motion-recipe-apply --recipe workspace/recipe.json --plan-sha256 <plan-sha256> --output workspace/new_candidate

# Use the exact manifest_sha256 printed by apply.
assetpipe --root . motion-recipe-inspect --run workspace/new_candidate --manifest-sha256 <manifest-sha256>
```

All three commands accept repeated `--allowed-root`. When set, include the
configuration root and every explicitly permitted source/provenance root. Output
is restricted separately to a **new** directory inside the configuration root's
`workspace/`; it cannot contain selected sources. Existing directories are never
overwritten. Source/JSON paths pass the existing RootResolver/Sources boundary
checks before reads, including historical linked provenance. No model paths,
download, provider dispatch, authorization or budget reservation is exposed.

## Plan binding and failure behavior

The read-only plan checks schema, source completion/review status, every declared
package-output hash, selected raw/aligned frame hashes, explicit timing/dimensions,
range, pivots and region bounds. Inputs are bounded to the existing 240-frame,
60fps, 2048px and 32M-atlas limits. Unknown fields (including approval declarations)
are rejected. Paths relative to the original recipe keep their original base;
the plan uses normalized absolute links.

The digest binds the original recipe bytes, source package/atlas/output hashes,
selected frame metadata and implementation files. Apply requires that exact
digest. The bound implementation files are the recipe, shared package/packer,
existing border-matte module, RootResolver and manifest writer. Apply
rechecks selected bytes during copy, and revalidates the full plan after
processing. Source/code/parameter drift stops the candidate. Failed initial gates
create no output; failures after output creation retain a `FAILED` receipt and
intermediates. Empty foreground is rejected. No retry, resume or implicit fallback.

Inspect requires the caller's expected receipt hash, rechecks sources/code and
the exact declared/present artifact inventory and all output hashes. Missing,
changed or extra files block integrity PASS. It is a trusted-local integrity check,
not a signed execution environment or a race-free filesystem sandbox; owners can
still replace files between checks and reads. No stronger attestation is claimed.

## Outputs and review stages

- `recipe-input.json`: exact input bytes, with recorded source recipe hash.
- `recipe.json`: normalized reference snapshot; `plan.json`: bound concrete plan.
- `source/`: exact aligned-input copies; `masked/`: alpha before local cleanup;
  `masks/`: explicit removed-pixel masks; `final/`: RGBA candidates.
- `sprites.png`, `atlas.json`: existing shared packer; original source-frame index
  and timestamp, source/raw/final hashes, duration, offset and pivot are retained.
  Candidate indices/timing restart at zero; original indices remain separate.
- `recipe_manifest.json`: status, plan, frame reports, output hashes and failures.
- `review.json`: reviewer null and checks null for loop selection, alpha edges,
  identity/equipment/silhouette, pivot/foot contact, engine import, readability
  and required Aseprite review.

Successful apply remains **CANDIDATE_REVIEW_REQUIRED**, `game_ready=false`.
Successful inspect is **ARTIFACT_INTEGRITY_PASS_REVIEW_REQUIRED**. Neither means
the selected cycle, white features, alpha edges or anatomical contact are approved.
No human-review write API is introduced here. Altering review flags makes this
v1 candidate snapshot fail inspection rather than silently promoting it.
Later human approval must use a separately designed/authorized review process;
these commands cannot fabricate it or replace existing Golden/SOT gates.

Engine evidence from an earlier artifact is not automatically carried forward as
approval for a new output. Source hashes, explicit notes and actual import/review
evidence can inform a later human decision. The ordinary Factory IMAGE_TO_SPRITE
production dispatch, still/SFX defaults and six MCP contracts remain unchanged.

## Reuse, evidence and rollback

Implementation: `assetpipe.motion.recipe`, three additive CLI commands, schema,
example and tests. Existing Source/RootResolver, manifest writer and border-mask
utility are reused. The existing package's atlas arithmetic was extracted into
`pack_review_atlas` and shared with recipes; no ported algorithm was modified.

The [dated validation](MOTION_REVIEW_RECIPE_VALIDATION_20261027.md) records actual
installed-CLI replay against the original real-generation package. All 20 final
RGBA frames and atlas pixels match the earlier manually edited fox candidate;
this establishes replay equivalence, not cross-character quality or approval.

Rollback: revert this implementation commit, including CLI/schema/example and
the shared-packing extraction. Preserve every old/new receipt, original source,
mask/intermediate and consumed generation reservation. No operational enablement,
live MCP replacement, model/node installation or SOT migration is needed.
