# M2.7 subject-first visual hierarchy — offline contract

User authorized on 2026-10-03 from the supplied Subject-First directive. Scope is
NONPIXEL_IMAGE and offline Gate A only: zero generations, downloads, retries or
fallback. Existing technical gates, six MCP schemas and human approval remain.

## Evidence and interpretation

Local main at start: 4309d4d with existing uncommitted Visual Hierarchy changes.
Read the four original M2.6 run manifests, compiled PromptSpecs, recipe metadata,
generation parameters, actual patched graphs and saved server histories under
workspace/visual_hierarchy/m26_scene_comparison_20261003. All positive/negative
strings and submitted graphs match their saved server history. All four historical
compilations remain exactly equal when recompiled without the new optional fields.
Detailed hashes and comparisons are in workspace/visual_hierarchy/m27_offline/source_audit.json.

Observed prompt facts: garment nouns repeat in subject/appearance; earlier focus
text includes garment-only prohibition terms in positive; native negative is empty;
there was no structured connected-body lock. Possible effects on garment salience
are hypotheses, not established causes. Two matched pairs do not establish general
model or recipe quality. Historical images and approval records are untouched.

## Contract and existing paths

PromptSpec accepts optional `subject_integrity` and `art_direction`. Existing fields
and compilation are unchanged when both are absent. They are compiled in the existing
compile_spec used by runtime M2 and offline M2.6 compile_candidate; there is no second
prompt generator. The earlier Brief-level focal-intent field remains compatible,
but cannot be combined with the structured PromptSpec contract in one Brief.

`subject_integrity` requires class and identity_source. Classes are full_character,
costume_item, prop and environment. Full characters explicitly require
whole_subject_required=true and physically_connected_body=true. mandatory_parts are
explicit author input; no species, clothing, pose or anatomy is inferred. Equipment
entries cite an exact source_trait and explicit worn/carried relationship. A visible
count must equal one unambiguous numeric or English one-to-twelve count in that trait.
An explicitly located counted item must have that location in its source trait.
Unsupported/free-text count inference is rejected rather than guessed.

camera_view defaults to from_source. Explicit front/rear/left/right requires matching
source pose/composition/constraints. Recognized source phrases are front view,
front-facing, rear view, back view, rear-facing, from behind, left side view and
right side view. Conflicting recognized views or visible-count/location incompatibility
raise BRIEF_COMPOSITION_CONFLICT. Arbitrary prose, occlusion and camera geometry are
not automatically solved; leave unspecified camera unchanged and review it.

Structured art_direction requires the same focal_target class and an explicit source.
Optional controls cover coherent value masses, connected shadows, selective subject
detail, subordinate background texture, silhouette contrast and landmark preservation.
With a selected style it must bind that exact style_sha256. A fingerprint proves
which style was addressed, not human aesthetic approval. Locked Visual SOT plus new
art direction is conservatively blocked pending reconciliation in project source.
Free-text stylistic contradictions are not automatically certified compatible.

The compiler prefixes a complete-subject sentence, source-required connected parts,
worn/carried equipment/counts and existing pose. Existing canonical traits, silhouette,
source camera, style descriptors, forbidden requirements and recipe remain intact.
Art direction follows existing scene/style content. Anima keeps its caption/tag adapter;
Krea2 and natural-language adapters use sentences without injected Anima tags.
No undeclared camera or action is invented. Forbidden substitutions go to native
negative only when explicitly supplied; unsupported native negative blocks routing
and compilation, even if natural-language negative instructions are available.

Recipe mutation of the new contracts or deletion of Brief canonical/visual traits,
silhouette, style or forbidden requirements blocks compilation. Existing recipe
fingerprints/evidence/approval loaders are not modified. PIXEL/SFX reject new fields.

## Offline fixtures and future comparison

examples/m27 contains forest_gate and market_street fixtures for C_subject_lock and
D_background_subordinate. They retain historical scene requirements, six belt pouches,
blue tunic, insignia, landmark, recipe, resolution and source camera. Added connected
body requirements are explicitly recorded as a derived synthetic fixture contract
from the user-authorized directive, never as approved project canon. No front view,
new action or pouch placement was invented.

Both conditions use mined_clean_anime_cel / clean_anime_cel__anima_base. C contains a
whole-subject lock and focal target. D adds only subordinate background texture.
Compiled candidates live in workspace/visual_hierarchy/m27_offline/prepared, remain
NOT_RUN and cannot replace old generation evidence. Example offline compilation:

```powershell
assetpipe mining compile --candidate-id mined_clean_anime_cel --brief examples/m27/forest_gate_C_subject_lock.json --workflow anima_base --output workspace/visual_hierarchy/m27_offline/example_compiled.json
```

Future Gate B requires separately authorized maximum four requests, persisted budget,
real model/workflow preflight, unchanged pair settings and original receipts/hashes.
This document and Gate A do not authorize dispatch.

## Review and status

Compilation records semantic/composition/art as NOT_VALIDATED and human review as
REVIEW_REQUIRED. New-contract candidates receive separate SEMANTIC, COMPOSITION and
ART checklists from the existing visual-review CLI, all NOT_VALIDATED initially.
Humans may record REVIEW_REQUIRED or SEMANTIC_REVIEW_FAILED when body, attachment,
counts or landmarks fail; technical QA PASS never supplies semantic/art approval.
No automated captioning, segmentation score, quality ranking or recipe promotion.

Final Gate A status and test counts are recorded after checks in
workspace/visual_hierarchy/m27_offline/verification.json. Generation state remains
GENERATION_NOT_RUN; artwork and style compatibility remain NOT_VALIDATED pending
actual image and human review.

## Gate A follow-up review (2026-10-03)

The supplied Gate A review / Gate B entry document authorizes offline evidence
review only. Gate B remains NOT_AUTHORIZED; no model preflight, budget reservation
or generation is claimed complete. A future four-request plan must use the existing
resumable style lab, real preflight and persistent reservation before any dispatch.

source_snapshot.json records HEAD, local origin/main tracking ref, status, diff stat
and tracked/untracked files; this is local evidence, not independent GitHub review.
evidence_review.json records fresh historical string/graph comparisons and hashes,
and structural C/D comparisons including seed, workflow inputs and recipe hash.

Counted equipment always records VIEW_VISIBILITY_REVIEW_REQUIRED. Unspecified
placement is preserved even with rear view. Only opposing explicit view/location
patterns are blocked; arbitrary geometry, occlusion, synonym and negation analysis
remain unassessed. Recognized camera patterns are explicitly distinguished from
SOURCE_VIEW_UNASSESSED; neither certifies absence of natural-language conflicts.

C/D compares background subordination after the same subject contract. Historical
M2.6 baseline/focal images are qualitative context only and cannot isolate or prove
the independent effect of subject-first compilation. All semantic, composition,
art and human approvals remain unvalidated. Synthetic fixtures remain synthetic.
