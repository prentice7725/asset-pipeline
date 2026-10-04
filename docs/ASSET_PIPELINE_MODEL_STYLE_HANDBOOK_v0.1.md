# ASSET-PIPELINE MODEL & STYLE HANDBOOK v0.1

> Status: WORKING DRAFT · Updated: 2026-10-04 · Repository snapshot: main reviewed 2026-10-04
>
> **Who reads this:** game-project owners, artists, Codex and Claude agents designing their **own project-specific art reference** before calling Asset Pipeline.
> **What this is:** a product/technique capability handbook. NOT a mandatory project-document template; NOT a new project canon; NOT an executable preference engine.
>
> The project decides WHAT its art is; Asset Pipeline documents HOW to attempt production, which supported workflow can express it, and WHAT was actually proven. Asset Pipeline never selects a new identity, costume, art style or game resolution on behalf of a project.

## 1. Start here (project authoring)

1. Read this handbook's **workflow capability matrix**, **style look-up**, **test evidence**, and **known limitations**.
2. Read your project's own ACTIVE/SOT, existing Golden Assets, renderer/size contracts, and related Git runtime integration (Source First). Do not treat this handbook as source of character lore, costume design, palette or art canon.
3. Author your project's own reference in its established format. Define visual purpose, actual appearance, viewpoint, equipment relationships, palette/shading language, source references, desired delivery canvas/frame/anchor/alpha and what counts as an acceptable in-game result. The project may cite style IDs, example run hashes and workflow IDs from this handbook, and should explain deviations.
4. Distinguish **final asset dimensions** from **model generation canvas**, **native logical pixel frame**, and **on-screen display**. For example, a game wanting 32×32 sprite frames should not copy a 1024×1024 model canvas into its SOT as the output size.
5. When handing work to the skill, have Codex/Claude read that project's reference and SOT, extract evidence into the existing Asset Brief and model-neutral PromptSpec, route to a compatible registered workflow, compile and independently review before any authorized generation.
6. Use existing output-specific image/Pixel Gate/Aseprite QA, actual-image semantic inspection, project approval and runtime integration. A 'TESTED' model experiment alone is not a project art approval.

There is **no requirement** for PROJECT_PROFILE.md / ASSET_REFERENCE_*.md / ASSET_MANIFEST.md or any common file hierarchy. Keep reference format determined by the individual project. The shared technical exchange contract is already `schemas/asset_brief.schema.json`.

## 2. Legend: what do these labels mean?

- **ACTIVE WORKFLOW**: currently registered for routing; not a blanket assertion of visual excellence or project approval.
- **EXPERIMENTAL / EXPLICIT_ONLY**: must be explicitly chosen and capability checked; not automatic fallback.
- **UNTESTED**: described or proposed, but no applicable generation/comparison result.
- **OFFLINE_COMPILED / NORMALIZED**: prompt compilation or source normalization only; no measured image result.
- **TESTED**: specific run/QA evidence for named scenario; DOES NOT generalize to all subjects, sizes and project art styles.
- **APPROVED**: independently recorded human selection for named style + recipe + target. A different project cannot inherit this approval without reviewing its own SOT and desired runtime use.
- **BLOCKED / NOT SUPPORTED**: stop rather than hallucinate a feature or switch workflow silently.

Three different scores must not be conflated: capability availability, empirical visual quality, and end-project usability. Only evidence-backed comparisons can say 'this model is better at X'. Workflow tags are intended use, not benchmark results.

## 3. Installed/registered model workflow quick reference

| Workflow / model family | Registry status | Candidate use based on registered tags & authoring dialect, NOT a performance ranking | Hard capability limits in current registry |
|---|---|---|---|
| `anima_base` / Anima Base | ACTIVE, NONPIXEL_IMAGE | Anime-oriented illustration, characters/portraits, fantasy concept drafting; hybrid short tags and clear caption-like relationships | T2I only; native negative supported; no image reference, inpainting, direct transparent output or image-to-image |
| `krea2_base` / Krea2 Turbo | ACTIVE, NONPIXEL_IMAGE | Descriptive concept illustration, polished/fantasy subject and setting compositions; full clear natural-language directions | T2I only; current workflow has **no native negative prompt**; no character reference, direct alpha, or i2i |
| `anima_pixelate_x4_vae` / Anima + Pixelate x4 VAE | ACTIVE, PIXEL_STATIC | Experimental pixel-looking character candidates and Pixel Gate/Aseprite downstream | No direct reference/alpha; actual 2026-10-01 pixel cohort failed Pixel Gate, **not a reliable 32px-ready recipe** |
| `tomohi_character` / Anima Aesthetic + Tomohi LoRA | EXPERIMENTAL, explicit_only | Candidate stylized anime portrait tests; trigger `tomohi`; not a proven cross-project default | No direct alpha/reference; requires actual LoRA/workflow readiness; no automatic selection |
| `codex_imagegen` | EXPERIMENTAL, explicit_only | Alternative natural-language NONPIXEL candidate when explicitly authorized | No guaranteed seed, exact resolution, direct alpha, native negative, reference binding |
| `grok_imagine` | EXPERIMENTAL, explicit_only | Alternative NONPIXEL candidate with registered editing/reference claims; verify on actual selected tool | No guaranteed seed, exact resolution, direct alpha or native negative |
| Krea2 Pixel Art LoRA + Refiner | **EXPERIMENTAL RESEARCH ONLY; NOT registered production workflow** | Observed two 64×64 native pixel candidates passing technical Pixel Gate in a narrow smoke test | Does not establish 32px legibility; opaque background; loader reported unused .magnitude keys; no approved Golden Master |

Scope note: `minimax_character_motion_reference` is registered for PIXEL_ANIMATION **motion reference** and requires a compatible approved Static Master; it is not a standalone style choice. `audio_stable_audio_3_medium` is a sound effects route, not a drawing model. NONPIXEL_ANIMATION general production is not ready; unsupported work must be blocked.

**Do not claim** Anima universally draws faces better or Krea2 universally draws backgrounds better: the repository does not yet contain a comparable, controlled, human-reviewed benchmark demonstrating this.

Canonical machine records: `config/workflow_registry.yaml`, `config/model_profiles.yaml`, `config/styles/model_recipes.yaml`. The latest live `asset_capabilities` and `asset_route` checks win over this dated summary if installed models/workflows change.

## 4. How to look up and invoke a style

| Style ID | Aesthetic description in catalog | Current evidence (as of snapshot) | Candidate workflow(s) |
|---|---|---|---|
| `anime-cel` | 2D anime, crisp contours, discrete cel shadows | Style UNTESTED | Anima Base, Krea2 candidate recipes (check registry) |
| `clean_anime_cel` | clean closed linework, flat shadow groups, low texture | UNTESTED / offline compiled only for mined recipes | Anima Base candidate, not an approved default |
| `graphic-risograph` | bold graphic forms, color blocks, print-like grain | Style UNTESTED; individual Anima/Krea2 recipes TESTED in M2 evidence, not human APPROVED | Anima Base or Krea2 only after compatibility check |
| `ink-storybook` | fine ink, muted pastel, cross-hatching | UNTESTED | candidate only |
| `storybook_gouache` | painted storybook, subtle paper/brush texture | UNTESTED / INSUFFICIENT_EVIDENCE | candidate only |
| `painterly_fantasy` | fantasy painting, layered values, restrained brushwork | UNTESTED / pixel experiments do NOT validate it as pixel art | candidate only |
| `limited_palette_pixel` | limited-palette cluster / stepped pixel contour concept | UNTESTED; Anima Pixelate cohort fails hard pixel color/gradient gates | not a verified native 32px recipe |

Do not conflate `anime-cel` (hyphenated original catalog entry) and `clean_anime_cel` (mined candidate). Match IDs exactly. Style IDs describe art grammar, not a character's identity, equipment, background setting or automatic quality guarantee.

Source definitions:
- `config/styles/catalog.yaml`: meaning, palette/line/shading/texture descriptors, status, source URLs.
- `config/styles/model_recipes.yaml`: style × workflow recipes and evidence/status.
- `config/styles/recipes/{anima,krea2,pixel}.yaml`: offline mined/adapted recipes. Do not treat NOT_RUN as production-capable.
- `config/styles/projects/<project_id>/visual_sot.yaml`, `style_pack.yaml`: project style lock/approved overrides when present and genuinely reviewed.
- `docs/style/GOLDEN_RECIPE_REGISTRY.md`, `docs/style/RECIPE_VALIDATION.md`: approvals, provenance, outstanding gates.

### Agent lookup algorithm (no guessing)

1. Query intended **output class** and constraints: alpha, native pixel dimensions, negative requirements, image reference, video/motion, text-in-image and delivery.
2. List candidates registered as compatible; do not infer real support from model marketing claims.
3. For a desired aesthetic search the style catalog by ID, study its definition and compare actual evidence for the exact workflow/style pair.
4. Select only a workflow that honors all hard constraints, preserving explicit project/user choices. A hard negative prompt requirement currently blocks Krea2 Base rather than being silently erased.
5. If no empirically suitable model has passed the target-specific conditions, mark **RESEARCH_REQUIRED** / **UNVERIFIED**, explain the gap and propose a controlled comparison; never describe an untested recipe as optimal.
6. A project may choose the model after reviewing the handbook; store its choice as a project reference, not a global pipeline default.
7. The final request is converted using the existing Asset Brief/PromptSpec and compiled with Anima (tags + caption) or Krea2 (direct descriptive sentences). Do NOT assemble a large mechanical pile of repeated character nouns.

## 5. Specific verified examples and limits

### 5.1 Pixel: Anima + Pixelate x4 VAE
`docs/style/PIXEL_ROOT_CAUSE_AUDIT_20261001.md` examined eight actual candidate images from the Pixelate pipeline. All eight failed Pixel Gate; color counts and gradient suspicion indicated illustration-like outputs. The audit did not certify native 32px assets. A passing 'prompt compiler' or a workflow label saying 'pixel' is not evidence that it can deliver final 32×32 game sprites.

### 5.2 Pixel: Krea2 Pixel Art 64px LoRA
`docs/research/KREA2_PIXEL64_SMOKE_20261003.md` records two experimental requests using Krea2 Turbo + Pixel Art LoRA + Refiner at 64×64, each with Pixel Gate PASS (22 colors). One redraw was readable in reviewed equipment connections. But it has opaque background, unverified full LoRA loader compatibility, no approved Static Master and **no 32×32 quality claim**. Its workflows are not in automatic registry routing.

### 5.3 Nonpixel: M2 style comparisons
`graphic-risograph` has evidence for Anima/Krea2 individual TESTED recipes, but catalog style approval is still UNTESTED. The M2 system explicitly disallows 'Anima is superior'/'Krea2 is superior' rankings without a controlled visual comparison and recorded human assessment.

### 5.4 Modularity and actual game placement
A nonpixel 1212×1300 modular portrait may require a transparent per-part canvas, seam bleed and consistent anchors, whereas a 32px battle sprite requires a native pixel-grid frame, foot anchor and in-game nearest-neighbor readability. Neither output should copy the other's rules. The exact rules belong to the respective project's own SOT.

## 6. How projects should write references (guidance, NOT a template)

A project's reference can be a GDD section, a shot sheet, a style bible, per-actor portrait contract, an illustrated art board, or a single Markdown file. Existing project practice wins. To make it actionable for an agent, cover the following questions **where relevant**:
- What is it, which screen is it used on, and what must visually read first?
- Which SOT section or already-approved asset defines its appearance, identity and forbidden changes?
- What viewpoint, character/equipment spatial relation, material, silhouette, art grammar, hierarchy and color language are intended?
- What are final canvas/frame, layer layout, alpha, anchor, animation, rendering and runtime viewport constraints?
- Which available style/workflow is being considered, and what evidence makes it suitable or still UNVERIFIED?
- How will full-resolution and *actual game-size* visual QA work? Who can approve a Golden asset?

A real project reference can simply say, for example, "We need 32×32 native battle frames under our current pixel SOT. The Anima Pixelate route is NOT VERIFIED for this use and Krea Pixel64 proof does not satisfy it; request a dedicated 32px validation before production." It does NOT have to adopt a centralized PROJECT_PROFILE/ASSET_MANIFEST structure.

## 7. Maintenance ownership (important)

Asset Pipeline maintainers own the **handbook** and research registry: new model, downloaded weights/model hash and license, LoRA/VAE, dialect, prompt recipe, capabilities, sample subjects, measured outputs, failed cases, compatibility warning and evidence source. Do not fabricate a win/loss rate, preference score or approval.

Game projects own their **actual style decisions** and references: select from this handbook or explain custom trials, write approved material into their Drive ACTIVE/SOT, keep Git aligned with real game implementation, and publish Notion links only. An evolving pipeline handbook does not silently rewrite their locked references.

Every evidence card should eventually contain: model/variant/hash, workflow/preset/version, intended output role, reference project (if permissioned), actual source/frame size, generation parameters, n/seeds, qualitative art observations vs measured gates, reproducible manifest or screenshot, issues, usage-rights state, last verified date, reviewer and approval status. Establish a controlled image gallery/benchmark over time; no pseudo-ranking from mere registry tags.

## 8. Operational checklist for Codex / Claude

1. Read **this handbook**, referenced live registry and current project SOT; do not demand a new fixed 3-file project structure.
2. Extract the user's intended output, constraints, project-approved art direction and preferred model.
3. Query model capability and documented recipe/evidence; if untested report it as untested.
4. Use project authored references as authority for visual decisions; this handbook only chooses HOW.
5. Prepare existing `Asset Brief`, compile existing `PromptSpec`, independent semantic review, route and run only with authorization.
6. Never auto-retry, auto-approve or call an experimental workflow silently.
7. Return generated assets, full run evidence, technical QA, semantic/art review, blocked facts and candidate state. Distinguish candidate from integrated/approved game asset.

## 9. Adjacent documents and scope
- `README.md` — installation and end-user CLI/MCP setup.
- `plugin/skills/asset-production/SKILL.md` — main agent skill.
- `plugin/references/STYLE_INTELLIGENCE.md` — style selection and SOT override mechanics.
- `plugin/references/AGENT_PROMPT_WORKFLOW.md` — agent-guided art direction and review, currently limited to NONPIXEL_IMAGE.
- `docs/PROMPT_SPEC.md` — compiler/adapter semantics.
- `docs/style/MODEL_DIALECT_RULES.md` — Anima vs Krea2 dialect and source caveats.
- `docs/style/PIXEL_ROOT_CAUSE_AUDIT_20261001.md` — documented failure.
- `docs/research/KREA2_PIXEL64_SMOKE_20261003.md` — narrowly successful 64px experiment, still unapproved.
