# Routing rules

Call asset_route with the validated brief. The core router owns selection:
output class, required capabilities, matching tags, eligible status, then priority.
A compatible explicit workflow ID wins. Unsupported references/negative prompts
or output capabilities block execution. Routing never generates an image.

Return selected_pipeline, selected_workflow, reason, required_capabilities,
missing_requirements, and fallback_candidates. Do not implement a second router.
