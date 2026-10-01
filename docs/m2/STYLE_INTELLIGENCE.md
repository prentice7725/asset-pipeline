# M2 Style Intelligence

Style Intelligence applies only to NONPIXEL_IMAGE. Existing style-free briefs,
PromptSpec fields, PIXEL/SFX paths and the six MCP tool schemas are preserved.

## Knowledge files

- `config/styles/catalog.yaml`: stable style IDs, version, state, expression,
  colors, linework, shading, texture, forbidden elements, required capabilities,
  source URLs and selected Explorer entry IDs. Descriptor adaptations are local
  proposals; none is approved project canon.
- `config/styles/model_recipes.yaml`: per-style/per-workflow candidate recipes for
  Anima, Krea2, Tomohi, Codex ImageGen and Grok Imagine. The existing model profile
  controls the prompt adapter and generation defaults. A recipe includes exact
  style fingerprint, prompt additions, capability requirements, version and sources.
- `config/styles/projects/<project_id>/visual_sot.yaml`: project style lock.
- `config/styles/projects/<project_id>/style_pack.yaml`: approved project pack.

Resolution priority: Visual SOT → approved Style Pack → common catalog → existing
model default. No style selected means no style change to legacy routing.
An explicit `style_id` may select a catalog/pack entry, but cannot override SOT.

A Visual SOT file has `style_id`, `source` (the real project source path/URL), and
optionally `style` containing a full style definition. A Style Pack has `status`,
`human_approval`, optional `default_style_id`, and `styles` containing local full
definitions (an empty mapping imports catalog entries). Optional `recipes` uses the
same `style_id → workflow_id → recipe` mapping as the common recipe file, and takes
precedence for that project. Custom definitions require a matching recipe fingerprint;
project recipes do not overwrite other projects' common recipes.
See `examples/m2_project_style_pack.example.yaml`.
Copy into the configured project directory only after real human approval.

## CLI

```powershell
assetpipe route --brief examples/m2_style_compare.yaml --output workspace/m2/route.json
assetpipe create --brief examples/m2_style_compare.yaml --workflow anima_base --output workspace/m2/anima
assetpipe create --type nonpixel-image --prompt "A fox scout" --style-id graphic-risograph --model-profile krea2
python scripts/style_compare.py --brief examples/m2_style_compare.yaml
```

The example's route command is intentionally blocked until a workflow/model is
selected or human-approved defaults exist. Use a prepared Brief with
`workflow_preferences.id: anima_base` to inspect its candidate route.
Comparison uses the same source Brief, seed and resolution, varying only explicit
workflow selection. Each model keeps its configured sampler/steps/adapter; equal
seeds do not imply equal latent noise or equivalent image quality. The script
checks live model installation, saves source Brief, prompts, raw images, QA,
manifest hashes and per-combination evidence, and never retries or approves.

## Approval and evidence

States are UNTESTED, TESTED, APPROVED and REJECTED. Automatic style routing requires
APPROVED style and recipe plus an ACTIVE compatible workflow. Explicit choices
still pass capability checks and existing EXPERIMENTAL opt-in. There are no new
quality scores or learned model priorities; existing registry ordering breaks ties
among approved candidates only.

TESTED/APPROVED recipes require `evidence` pointing to a real comparison evidence
JSON within the repository root. The loader checks style/workflow/version,
manifest hash, candidate-ready state, all QA PASS and output hashes. APPROVED also
requires `human_approval: {approved: true, reviewed_by: ..., reviewed_at: ...,
reason: ...}`. Approval records are supplied by the project owner, not by the agent.
On style definition/approval edits update matching recipe fingerprints; changed
style content invalidates older recipes. Real generation evidence remains local
under workspace and is not silently replaced by unit-test results.

`route_decision.json`, compiled prompt and manifest record identical style ID,
source layer/file, definition fingerprint/version/state, recipe version/state/hash,
source URLs, evidence location, lock and final selection reason.

Codex and Claude share `plugin/skills/asset-production/SKILL.md` and its style
reference. Production algorithms and knowledge stay in the installed engine.
No additional MCP tool, GUI or agent-specific catalog is introduced.
