---
name: asset-production
description: Create or continue game visual assets through the connected Asset Pipeline MCP tools using prompts, approved references, or project design sources. Use for Asset Pipeline production requests; requires its local MCP connection.
---

Read [production instructions](../../instructions/PRODUCTION.md) before generation.
Use the six Asset Pipeline MCP tools for high-level operations; the installed
assetpipe engine owns all production algorithms and review gates.

- For source extraction, consult [Asset Brief](../../references/ASSET_BRIEF_SCHEMA.md).
- To choose an output, consult [output classes](../../references/OUTPUT_CLASSES.md).
- For user-selected workflows, consult [routing rules](../../references/ROUTING_RULES.md)
  and [workflow status rules](../../references/WORKFLOW_STATUS_RULES.md).
- To continue pixel animation, consult [pixel contract](../../references/PIXEL_PIPELINE_CONTRACT.md).
- For visual style selection or model comparison, read [Style Intelligence](../../references/STYLE_INTELLIGENCE.md).
  Codex CLI and Claude Code use this same knowledge contract and the engine's configured catalog;
  retain project Visual SOT locks, canonical traits, and explicit user model choices.

When tools are unavailable, report the missing local connection. Do not substitute
arbitrary shell, image editing, or experimental recovery for the production path.

For offline recipe research and validation handoff, read [Style Routing](../../references/STYLE_ROUTING.md).
