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

For a user asking how to design a project's own reference, model choice or style,
read [Model & Style Handbook](../../../docs/ASSET_PIPELINE_MODEL_STYLE_HANDBOOK_v0.1.md)
and the live model/workflow/style registries. The handbook is pipeline-side usage
knowledge, **not** a mandatory project reference-document schema. Project visual
SOT controls art identity and style choice; keep the existing Asset Brief/PromptSpec
as the tool interchange contract. Distinguish capability, comparative evidence and
human-approved Golden styles; never invent performance preferences.

Research caution (2026-10-04): [Model & Style Evidence Audit](../../../docs/research/MODEL_STYLE_EVIDENCE_AUDIT_20261004.md)
records that the handbook remains INVENTORY_ONLY and model-specific art quality
is NOT established. The [benchmark protocol](../../../docs/research/MODEL_STYLE_BENCHMARK_PROTOCOL_v0.1.md)
is a proposal, not authorization to generate. Model/recipe recommendation requires
actual comparable outputs and reviewed evidence; never infer superiority from tags,
workflow ACTIVE status, partial smoke QA or offline-compiled prompts.
