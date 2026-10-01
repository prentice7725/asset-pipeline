# Routing rules

Call asset_route with the validated brief. The core router owns selection:
output class, required capabilities, matching tags, eligible status, then priority.
A compatible explicit workflow ID wins. Unsupported references/negative prompts
or output capabilities block execution. Routing never generates an image.

Return selected_pipeline, selected_workflow, reason, required_capabilities,
missing_requirements, and fallback_candidates. Do not implement a second router.

CLI providers (codex_imagegen, grok_imagine) are EXPERIMENTAL and explicit_only: they are never selected
automatically. Use one only when the user names it, by workflow ID with allow_experimental=true. They cannot honor
seed, exact resolution, transparency, or in-image text, so the router blocks briefs that need them. Native negative
prompts are unavailable there; forbidden elements go in as natural-language instructions that are not guaranteed.
A provider failure never falls back to another provider and is never retried automatically; report the error code.
