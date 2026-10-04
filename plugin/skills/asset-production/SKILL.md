---
name: asset-production
description: Create or continue game visual assets through the connected Asset Pipeline MCP tools using prompts, approved references, or project design sources. Use for Asset Pipeline production requests; requires its local MCP connection.
---

Read [production instructions](../../instructions/PRODUCTION.md) before production.
Use the six existing Asset Pipeline MCP tools for high-level operations; the
installed `assetpipe` engine owns routing, deterministic compilation, execution,
QA, manifests, and review gates.

For a `NONPIXEL_IMAGE` request, follow the shared agent-led art direction,
model-aware PromptSpec authoring, independent semantic review, bounded correction,
and post-generation visual review in
[Agent Prompt Production](../../references/AGENT_PROMPT_WORKFLOW.md). Codex and
Claude use this same contract. Do not wait for human prompt approval during normal
production. Keep explicit human approval for Golden Assets and changes to final
project canon.

- For source extraction, consult [Asset Brief](../../references/ASSET_BRIEF_SCHEMA.md).
- To choose an output, consult [output classes](../../references/OUTPUT_CLASSES.md).
- For user-selected workflows, consult [routing rules](../../references/ROUTING_RULES.md)
  and [workflow status rules](../../references/WORKFLOW_STATUS_RULES.md).
- To continue pixel animation, consult [pixel contract](../../references/PIXEL_PIPELINE_CONTRACT.md).
- For visual style selection, read [Style Intelligence](../../references/STYLE_INTELLIGENCE.md).
  Preserve project Visual SOT locks, canonical traits, and explicit model choices.
- For offline recipe research and validation handoff, read [Style Routing](../../references/STYLE_ROUTING.md).

Pixel, SFX, animation, and existing output-class gates keep their current
production contracts. Never substitute arbitrary shell execution, image editing,
or experimental recovery for the configured production path. When the local MCP
connection or required deterministic compiler is unavailable, report it and stop
before generation.

For cross-project asset reference documents using YAML-front-matter Markdown, read
[Shared project-reference intake](../../references/PROJECT_REFERENCE_INTAKE.md)
before building the existing Asset Brief. This is a source-to-Brief convention, not
an implemented Markdown importer or a new MCP tool. Treat DRAFT, EXAMPLE_ONLY and
BLOCKED_SOURCE_GAP references as non-generatable; follow the project SOT and the
existing review gates.
