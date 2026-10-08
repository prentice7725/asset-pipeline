# STYLE MENU v1 Manual / Rescue Override

This change is offline implementation only: GENERATION_NOT_RUN. No new benchmark,
model download, global winner edit, project SOT edit or human art approval.

> STYLE MENU primary model is an evidence-informed default for the evaluated fixtures and style-fidelity goals, not a universal subject-capability lock or production approval.

## Actual code audit and benchmark scope

Baseline is origin/main `12c2109`, with `styles/menu.py`, 24 operational entries,
structured Style Contracts and model-specific recipes. The original local main
`aca0a40` predates these contracts; implementation uses a separate worktree.

The immutable `research/style_catalog/style_menu_v1/evidence_archive.json` records
KREA1596_24X3X3_20261006: 24 styles, Anima Base rebuilt / Anima Turbo / Krea2,
seeds 7725–7727, 216 images. The actual fixture is
`config/style_menu/anima_family_synthetic_fixture_v1.yaml`: one adult traveler,
short dark brown hair, blue knee-length coat, dark trousers and closed shoes,
one brass compass in the subject's left hand, standing FRONT, complete head-to-toe
framing and visible feet. Style-conditioned scenery varies, but these are
character/equipment/scenery observations, not independent aircraft, vehicle,
mecha, creature or architecture benchmarks. Same-seed repeatability was not
measured. The traveler is SYNTHETIC_NOT_CANON.

Baseline snapshots in `tests/fixtures/style_menu_routes_v1.json` were obtained by
executing the pre-change HEAD menu binder with the original router contract.
They cover all 24 styles, including both explicit STYLE-117 selection policies
(25 complete route decisions). Default decision JSON remains exactly equal.

## Brief and routing contract

Optional `subject_domain`: character, aircraft, vehicle, mecha, architecture,
creature, environment, prop, ui_illustration. It is never inferred from asset_type.
Missing fields keep the previous routing. `style_lock` defaults to true and
cannot be false for an override. The eight Style Contract targets (medium,
palette, linework, shading, lighting, background, texture, value_structure) remain
in the existing PromptSpec compiler. Retaining targets does not prove artwork
equivalence on another model.

The identifiers are distinct: art_style is a menu slug, style_id is its stable
STYLE ID, model_profile is a registry model family, workflow_id is a registered
execution path, provider is the workflow engine, executor is the commanding
runtime/agent. `krea2_base` is a workflow alias, `krea2` is a model profile.
Passing the former to model_override yields MODEL_OVERRIDE_IS_WORKFLOW_ALIAS,
with the correct profile in the error. Model-only selection requires exactly
one matching NONPIXEL_IMAGE workflow; otherwise specify workflow_override.

Priority: approved USER_MANUAL override → explicit project asset model binding
→ approved SUBJECT_RESCUE → menu default → block. A rescue conflicting with a
project binding yields SOT_BINDING_CONFLICT and requires a separate USER_MANUAL
exception. Style/canon locks, recipe fingerprints, capabilities, provider status,
permissions and budget apply at every level. No silent fallback or retry.

`visual_sot.yaml` may keep project-level model_profile/workflow_id or add
`asset_model_bindings: {asset_id: {model_profile, workflow_id,
hard_model_prohibition}}`. This affects only the named asset; unrelated assets
retain the defaults. Source is mandatory for model bindings. Normal model
bindings may be superseded by approved USER_MANUAL. A hard_model_prohibition
requires approval's `sot_exception_approved: true` and exact
`sot_exception_source` matching the actual SOT source. No SOT file is rewritten.
An explicit SOT experimental binding still requires Brief allow_experimental;
manual overrides never borrow the menu primary's experimental consent.

## Manual approval

Prepare a normal complete Brief with these additional fields:

```yaml
project_id: sky
asset_id: assault
art_style: retro_sci_fi_anime
style_id: STYLE-103
subject_domain: aircraft
style_lock: true
model_override: krea2
workflow_override: krea2_base
override_mode: USER_MANUAL
override_reason: Anima route repeatedly failed aircraft geometry.
override_approval: workspace/sky/approvals/assault_manual.json
```

Approval JSON must contain matching project_id, asset_id, style_id,
model_override, workflow_override, executor_override (omit/null when absent),
override_mode and override_reason, plus real human_approval:
`{approved: true, reviewed_by, reviewed_at, reason}`. The agent must not invent
these records. Paths resolve against the configured root and cannot escape it.
An approval for one asset cannot authorize another.

Use `assetpipe route --brief ... --output ...` or compile-prompt for offline
inspection. Route approval does not authorize generation. Every override records
USER_OVERRIDE or APPROVED_SUBJECT_RESCUE, original primary/binding and selected
model/workflow/provider, project/SOT references, exact approval bytes/hash,
subject, failure evidence, style fingerprint/recipe and rejected routes.

Executor is independent of provider. `executor_override: grok` with krea2_base
means a Grok agent commanding ComfyUI, not grok_cli generation. This engine has
no verified agent connection/dispatch adapter: codex/grok/claude overrides are
EXECUTOR_UNAVAILABLE, even if their provider CLI is installed. Only
local_python is currently verifiable (the executing Python engine); the outer
agent remains NOT_VERIFIED. Omit executor_override for normal local engine
routing. Do not report the requested agent as actually connected.

STYLE-103 has Anima/Krea recipes. Grok's STYLE-103 recipe remains absent and is
blocked explicitly. No untested Grok compiler dialect or recipe is invented in
this change. CLI seed/exact-resolution/transparency/native-negative limitations,
reference support checks and explicit EXPERIMENTAL consent remain enforced.

## Rescue proposal and evidence

`assetpipe rescue-plan --brief ... --output workspace/sky/rescue_plan.json`
compiles at most three compatible alternatives without executing any provider.
By default installation is NOT_VERIFIED. `--inspect-installation` performs only
read-only live ComfyUI connection, node and model-list checks. It distinguishes
LIVE_INVENTORY_PRESENT, MISSING_DEPENDENCIES and UNAVAILABLE; inventory presence
is not model-hash/license/auth/cost validation or artwork quality evidence.

Brief failure_evidence lists at least two distinct approved JSON records, with
matching project/asset/style, primary workflow_id and subject_domain. Each needs:

- state: PRIMARY_ROUTE_SUBJECT_FAILURE
- failure_type: AIRCRAFT_GEOMETRY_FAILURE, VEHICLE_TOPOLOGY_FAILURE,
  MECHA_TOPOLOGY_FAILURE, COMPOSITION_FAILURE, PERSPECTIVE_FAILURE,
  SILHOUETTE_FAILURE, UNUSABLE_CROP, SCENE_STRUCTURE_FAILURE or ROLE_IDENTITY_FAILURE
- conditions: the actual prompt/settings/seed and evaluation circumstances
- original_path and original_sha256: actual generated artifact or review record,
  existing inside the configured root; duplicate originals are rejected
- review_source and uncertainty: who/what observed the defect and its limits
- human_approval: explicit approval of the failure evidence

All original records and record hashes are retained. A technical image QA PASS
is not a semantic/design PASS. AI observations must retain uncertainty and need
approved evidence before rescue; a speculative model ranking is insufficient.
ROLE_IDENTITY_FAILURE distinguishes independent Assault from a Buster-style
heavy gunship without changing either role's canon.

Each proposal reports model/workflow/provider, reason, recipe state/fingerprint,
required/unsupported capabilities, targeted failure codes (hypotheses), known
limits and installation/auth/cost/approval requirements. A proposal has
generation_authorized=false and generation_requests=0.

To select one, use override_mode SUBJECT_RESCUE and an exact approval recording
rescue_exploration_approved=true and failure_evidence_sha256s in Brief order.
Generation requires a separate budget authorization. Proposal and evidence never
automatically produce a fallback or promote a candidate.

## Dispatch budget and audit

An override create call also needs generation_authorization pointing to JSON
with exact project/asset/style, workflow_id/model_profile,
override_approval_sha256, real human_approval, generation_approved=true,
max_requests=1, request_id and cost_acknowledgement. This initial contract permits
one dispatch per approval. Multi-image exploration requires separately approved
requests; no extension/retry is implicit.

The existing compiler validates first. An exclusive persistent reservation under
workspace/override_budget is written before provider dispatch. The same project
request_id cannot be used twice, including after timeout, failed generation or a
process restart. Ambiguous/failed dispatches remain consumed. Provider preflight
and QA still apply; no seed or model quality claim is synthesized.

The manifest retains original Brief, existing generation/QA/provenance fields,
compiled prompt, source hashes and override audit. Initial generation_state is
GENERATION_NOT_RUN; DISPATCH_STARTED conservatively includes unknown outcomes,
and success is GENERATED_REVIEW_REQUIRED. Outputs and rejected image outputs
receive SHA256 entries. Semantic/composition/style reviews are NOT_VALIDATED;
review_state remains REVIEW_REQUIRED. Human/Aseprite gates are unchanged.

## Future subject bindings and SKY RENDEZVOUS follow-up

The run-scoped subject field and evidence can support a future subject_overrides
catalog, but this change intentionally does not activate any subject model winner.
Any future PROVISIONAL route requires real subject evidence and separate human
approval; it cannot automatically become APPROVED or replace a global primary.

For SKY RENDEZVOUS, propose a separate SOT revision retaining STYLE-103 and all
Assault/Buster canon: explicitly describe independent Assault role, topology,
equipment, palette, silhouette and camera; mark model choice as an evidence-informed
default; identify the asset-local exception authority and hard prohibitions;
reference actual aircraft failure records and approve the concrete Krea2 workflow
exception plus a separate generation budget. If Grok must command the workflow,
a verified executor connection is a prerequisite and currently unavailable.
The SOT owner must review and apply that revision. Git changes here do not modify
Google Drive SOT. No aircraft quality improvement is claimed.
