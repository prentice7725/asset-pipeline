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

When project owners request **NONPIXEL_IMAGE** style work, prioritize
[Style Intelligence](../../references/STYLE_INTELLIGENCE.md),
the machine-readable `config/style_menu/nonpixel_prompt_research_v0.yaml`,
and [Production Instructions](../../instructions/PRODUCTION.md).
Study-only recipes can be exported with `python scripts/nonpixel_research.py export`;
those study packets are not native production PromptSpecs. Protect project SOT
identity; vary one palette/linework/shading/texture variable at a time and retain
failed candidates. PIXEL style STYLE-005 is HOLD and excluded from all nonpixel
pilot generation. Codex/Grok CLI providers have separate historical 2026-10-01
REAL_GENERATION_VERIFIED records; validate files/sha before planning any new
paid smoke, and do not batch stylistic cross-model experiments for them.

When project owners request an **illustrated style menu**, read
[Style Intelligence](../../references/STYLE_INTELLIGENCE.md)
and [Agent Prompt Production](../../references/AGENT_PROMPT_WORKFLOW.md).
Menu IDs are external preview candidates (Krea2 creator examples) only;
EXTERNAL_PREVIEW_ONLY must never be silently promoted to locally VERIFIED or
PROJECT_APPROVED. Do not claim 32px pixel quality from a pixel-themed preview.
The menu may help shortlisting but can never overwrite project SOT identity,
required output class, or actual style approvals. As the user requests,
Codex/Claude may propose *separate trial variants* of palette, linework,
materials, LoRA, VAE and model workflow, but all changed combinations need
independent compatibility and actual-image review, not silent production fallback.

For a user asking how to design a project's own reference, model choice or style,
read [Style Intelligence](../../references/STYLE_INTELLIGENCE.md)
and the live model/workflow/style registries. The handbook is pipeline-side usage
knowledge, **not** a mandatory project reference-document schema. Project visual
SOT controls art identity and style choice; keep the existing Asset Brief/PromptSpec
as the tool interchange contract. Distinguish capability, comparative evidence and
human-approved Golden styles; never invent performance preferences.

Before recommending model, style, LoRA or workflow to a project, consult
[Style Routing](../../references/STYLE_ROUTING.md)
and run `assetpipe knowledge --model-id <model_variant>` or
`assetpipe knowledge --style-id <style_id>` if the local CLI is available.
The command reads checked-in registry and report metadata only; output
`art_quality=UNKNOWN` is **not** a score to optimize. Historical technical QA
or model-author marketing claims cannot be presented as comparative visual proof.
If knowledge validation fails, report the contradiction without silently choosing
another model. This query is optional metadata inspection and never overrides
project visual SOT, existing six MCP tool schemas or runtime routing.

Research caution (2026-10-04): [Style Routing](../../references/STYLE_ROUTING.md)
records that the handbook remains INVENTORY_ONLY and model-specific art quality
is NOT established. The [benchmark protocol notes](../../references/STYLE_ROUTING.md)
is a proposal, not authorization to generate. Model/recipe recommendation requires
actual comparable outputs and reviewed evidence; never infer superiority from tags,
workflow ACTIVE status, partial smoke QA or offline-compiled prompts.
