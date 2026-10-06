> **Operational menu entrypoint:** read [Agent Guide v1](AGENT_RECIPE_SELECTION_GUIDE_v1.md) and workspace `config/styles/style_menu_v1.yaml` first for current NONPIXEL_IMAGE style selection. User-selected `art_style` binds an explicit model/recipe/workflow; it does not manufacture APPROVED/Golden state. The M2/research rules below still govern generic catalog routing and historical studies.

# Style Intelligence (M2)

The local engine owns `config/styles/catalog.yaml`, `model_recipes.yaml`, and
`config/styles/projects/<project_id>/{visual_sot,style_pack}.yaml`. Both Codex
and Claude Code use this shared skill; do not maintain separate model rankings.

Read the project's visual source documents first. Resolve the style in this order:
project Visual SOT → approved project Style Pack → common catalog → model defaults.
Put the project folder ID and optional `style_id` in a prepared Asset Brief.
An explicit style conflicting with the Visual SOT lock must be blocked, not silently
replaced. Canonical identity, clothing, equipment and silhouette stay in the Brief;
catalog descriptors must never supply new canonical traits.

Explore catalog sources and candidate recipes with the user. Catalog entries from
the Krea2 Style Explorer are community references, not official model certification
or project approval. Anima's model card is a prompting source, not proof of a
style/model combination's quality. Record source URL, entry ID where available,
and interpretation. Do not invent scores, rankings, or tested capabilities.

Use `workflow_preferences.id` or `workflow_preferences.model_profile` to preserve
an explicit workflow/model choice. An EXPERIMENTAL workflow still requires
`allow_experimental: true`. Call `asset_route` before `asset_generate`; capability
or style incompatibility blocks generation. An unknown style ID is an error.
Styles currently apply to NONPIXEL_IMAGE only; pixel/SFX production stays unchanged.

UNTESTED combinations require an explicit workflow/model for comparison.
TESTED means actual generation and QA evidence; APPROVED additionally requires
human approval. Neither a unit test nor M2 comparison verifies Codex/Grok M1 E2E.
Record the route's style ID, source layer, fingerprints, recipe version and status
with the run. The manifest and compiled prompt must agree with that route.

Have the user review generated candidates in the required review tool. Record
human approval only when actually given; do not fill approval fields for them.
Automatic selection requires both APPROVED style and APPROVED recipe, backed by
matching generation evidence. Preserve all existing review and QA gates.

When the connection is unavailable, report the missing local connection using
the skill's existing rule. Repository contributors can use the Python CLI to
inspect routes and `scripts/style_compare.py` to run a sequential Anima/Krea2
comparison; this does not create an additional MCP tool or authorize retries.
