# MCP tool contract

Exactly six tools are advertised. Generated request schemas live under
integrations/mcp/schemas and match the server's advertised schemas. Unknown fields,
wrong types, unknown tools, and invalid briefs are rejected before execution.

| Tool | Inputs | Result |
| --- | --- | --- |
| asset_capabilities | none | Output/input classes, ACTIVE workflows, providers, actions, recovery policy, actual environment readiness, per-provider `provider_readiness` (AVAILABLE/BLOCKED/UNAVAILABLE, no paid request) and `external_cli_workflows`. |
| asset_build_brief | request_text; optional requested_output_type, asset_id, source_document_paths, reference_image, action, prepared_brief, workflow_id | Validated brief, BRIEF_READY, unresolved review items; BLOCKED if output type is unknown. |
| asset_route | brief | Pipeline/workflow, reason, required capabilities, missing requirements, fallbacks; ROUTED or BLOCKED. |
| asset_generate | Exactly one of brief / brief_file; optional seed | Core CLI launch with run_id, RUNNING, manifest reference; missing requirements return BLOCKED without launch. |
| asset_continue_animation | asset_reference (known run UUID or configured brief path), action, output_class, optional animation_constraints | Existing primary animation path or explicit BLOCKED. |
| asset_inspect_run | run_id | Read-only status, engine_status, route, workflow, manifest reference, QA summary, produced files, reviews, `error_code` and a `provider` summary for CLI-provider runs. |

Continuation constraints may contain production references, resolution, frame_target,
and motion_constraints. The core validates the actual approved master, motion,
semantic selection, action, profile, and palette. No animation action is promoted
from a requested example into a supported capability: current pixel support is walk only.

Responses are structuredContent objects. Details remain in manifest/file references;
logs and raw images are not embedded. REVIEW_REQUIRED retains raw engine_status
and game_ready=false. Launch acceptance is not PASS. Malformed requests use MCP
tool errors; valid requests with missing production requirements return BLOCKED.

M1 adds fields to existing results only; the six tools and their request schemas are unchanged. CLI-provider runs
(codex_imagegen, grok_imagine) are EXPERIMENTAL and explicit_only. A run can end BLOCKED or UNAVAILABLE (provider not
signed in or not installed) in addition to FAILED and REVIEW_REQUIRED. `assetpipe-mcp` refuses to start inside a
provider CLI job (`ASSETPIPE_PROVIDER_DEPTH`) to stop recursive invocation.
