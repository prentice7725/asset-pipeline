# Engine resources

The paths here belong to the separately installed engine. Resolve them against
`core_root` in the trusted adapter configuration, not relative to this plugin's
cache directory. Engine registries and evidence are not copied into the plugin.
If a resource is absent, report it; do not invent evidence, pick another model or
restore a global image fallback. The project ACTIVE/SOT and existing gates remain
authoritative.

## Local installation

`docs/plugin/LOCAL_SETUP.md` describes engine prerequisites. Host-specific plugin
wiring is described in [Local host setup](LOCAL_HOST_SETUP.md).

## MCP tool contract

Read `docs/plugin/MCP_TOOL_CONTRACT.md` and `integrations/mcp/schemas/` in the
configured engine. The six names are asset_capabilities, asset_build_brief,
asset_route, asset_generate, asset_continue_animation and asset_inspect_run.

## Validation status

`docs/plugin/STATUS.json` is a historical engine validation record. New local
installation checks do not change its official Creator, real-generation or
human-review status. Report fresh evidence separately.

## Style menu configuration

Read `config/styles/style_menu_v1.yaml` in the configured engine. The 24-style
menu binds explicit model/recipe/workflow choices; it does not approve generation.

## Reviewed menu evidence

Read `research/style_catalog/style_menu_v1/STYLE_MENU_v1.md`,
`research/style_catalog/style_menu_v1/style_menu_v1.json` and
`research/style_catalog/style_menu_v1/evidence_archive.json`. Verify original
images and hashes through the configured source roots; technical evidence alone
is not human art approval.

## Manual and rescue policy

Read `docs/style_menu/MANUAL_RESCUE_OVERRIDE.md`. Its scoped authorization,
failure evidence, compiler/QA and one-attempt budget requirements stay unchanged.

## Historical recipes

Read `docs/style_menu/history/AGENT_RECIPE_SELECTION_GUIDE_v0.1.md` only for a
historical study. It does not replace the current [Agent Guide v1](AGENT_RECIPE_SELECTION_GUIDE_v1.md).

## Model knowledge

Read `docs/knowledge/MODEL_CAPABILITY_GUIDE_v0.1.md` and run the read-only
`assetpipe knowledge` command in the engine when available. UNKNOWN remains
UNKNOWN; missing comparative evidence cannot establish model superiority.
