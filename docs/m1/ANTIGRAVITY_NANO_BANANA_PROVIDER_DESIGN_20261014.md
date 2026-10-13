# M3-A2 Antigravity CLI / Nano Banana image provider — integration design

**State:** DESIGN_ONLY / EXPERIMENTAL_CANDIDATE / NO_GENERATION_RUN / NO_RUNTIME_SWITCH
**Recorded:** 2026-10-14 (Asia/Tokyo)
**Code baseline:** `main@f103d37bc9bbeca8e39b109876f9183c90604cbf`
**Product decision:** Candidate **Asset Worker 2 = Antigravity CLI `agy`** for NONPIXEL_IMAGE, especially image-reference editing and expression variants. Existing Grok remains available but is **not** selected by the new candidate or automatically uninstalled. Replace its role only after equivalent verified capabilities and explicit approval.

## 1. Source-verified product capabilities vs missing evidence

Official Antigravity sources:

- [Antigravity models](https://antigravity.google/docs/models): describes **Nano Banana 2** as the additional model used by the generative image tool; the agent-facing reasoning `--model` selector is separate. Do not pretend `--model` pins a Nano Banana image backend or a specific paid API model ID.
- [Antigravity SDK tools](https://antigravity.google/docs/sdk/tools/): defines built-in `generate_image` for generating **or editing** images.
- [Headless CLI](https://antigravity.google/docs/cli/headless/): supports `agy -p/--print`, `--output-format json|stream-json`, `--print-timeout`, cached interactive login, structured terminal status. CLI headless is noninteractive. Exit 0 does **not** alone prove tool execution or image generation; approvals can be soft-denied.
- [Antigravity CLI changelog, 2026-10-03 v1.2.16](https://antigravity.google/docs/changelog?tab=cli): `image-generator` subagent can inspect outputs with **up to 3 attempts**. This is a critical conflict with Asset-Pipeline's existing exactly-one-dispatch/no-implicit-retry budget contract.
- [Antigravity plans](https://antigravity.google/docs/plans): quotas/overage availability depend on the account/plan and are not guarantees for any asset run.
- [Independent 2026-08-13 CLI image smoke](https://github.com/I-am-Sage/google-ai-pro-skills/blob/main/google-ai-studio/references/antigravity-cli.md): reports headless 1024 JPEG without an API key and an artifact path. **External observation**, not an Asset-Pipeline E2E proof.

| Required behavior | Evidence state |
| --- | --- |
| CLI headless request and JSON result | Officially documented |
| Tool for image creation/edit | Officially documented |
| Image backend model called Nano Banana family | Official product documentation; precise per-run backend may not be exposed |
| Headless creates image and returns file | Independent external smoke only |
| Edit with one **existing** reference portrait | **NOT_VERIFIED_IN_OUR_PIPELINE** |
| Same identity, expression-only variants | **ART_QUALITY_NOT_VERIFIED** |
| Deterministic seed / exact pixel dimensions / alpha | **UNSUPPORTED_OR_UNVERIFIED**, block if contractual |
| Output artifact path correlation, containment, session identity | **NOT_VERIFIED** |
| Exactly 1 internal image generation attempt | **NOT_PROVEN; known up-to-three-attempt subagent behavior** |
| Credentials, subscriptions, quotas and usable production license | Check per operator/environment; no assumptions |

## 2. Placement — do not conflate provider, executor and reasoning model

Proposed separate adapter:

```text
Project ACTIVE/SOT -> Asset Brief / STYLE MENU -> model-specific compiler
   -> NONPIXEL_IMAGE provider selection
      +-- comfyui (Anima / Krea2, unchanged)
      +-- codex_cli (existing worker 1)
      +-- agy_cli (experimental worker 2, proposed)
      +-- grok_cli (existing, no automatic removal)
   -> original image + hashes -> shared QA -> REVIEW_REQUIRED
   -> OPTIONAL portrait expression variation -> independent child run(s)
```

- Candidate provider key: `antigravity_cli`. Suggested experimental workflow key: `agy_nano_banana_image`. Use a **new provider module**, not a Grok class rename.
- An Antigravity reasoning model slug (`agy models`) selects the planning/orchestration model. The image generation tool may use Nano Banana 2 (official documentation) but cannot be guaranteed to be that exact release by passing a reasoning slug.
- **Generator vs executor:** In rescue contracts do not confuse "the agent orchestrating the call" with the image `provider` / backend. If user selects worker 2, require an explicit scope; keep style, project identity and chosen workflow lineage.
- Do not change STYLE-101..124 primary model preferences, existing recipe fingerprints, or other provider auto-routing. `EXPERIMENTAL` + `explicit_only` initially.
- Keep MCP at exactly six tools. New provider may be invoked through existing compatible factory/API entrypoints after tests; do not introduce incompatible request/schema mutations in the same PR.

## 3. Intended CLI headless smoke (COMMAND SPEC ONLY, NO RUN)

```powershell
# First authenticate through the supported interactive CLI on the machine.
agy --version
agy models

# Example intentionally does not invoke paid generation here.
# To run a paid smoke, require a separately authorized request+budget;
# verify CLI flags with the exact locally installed version first.
agy --print "Use the built-in generate_image tool for a single explicitly authorized art brief; do not use shell commands, source-code tools or other agents. Report the exact generated artifact path and any visible backend label." --output-format stream-json --print-timeout 10m
```

Restrictions:
1. Run in a fresh, trusted, **job-specific workspace outside all project trees**. Never hand off project SOT, unrelated paths, or write access to the source code.
2. Use the existing environment allowlist and credential redaction; interactively login once, then reuse the existing user's authorized session without inventing API tokens.
3. Do **not** pass `--dangerously-skip-permissions`. CLI can auto-allow writes in the active workspace; constrain its workspace, and verify exact effective permissions and tools. The SDK may allow `CapabilitiesConfig` tool restrictions; investigate a typed SDK adapter if CLI cannot restrict tool surface.
4. Observe `stream-json` tool events, terminal `status`, stderr error and actual produced files. A zero exit code or a response that merely describes an image is never success.
5. Correlate exactly one newly created image to the **own request/conversation** and permitted artifact path using fresh snapshots, SHA256, file identity, no symlink/junction escape, no arbitrary shared-home fallback. Reject ambiguous, foreign or prior-session output.
6. Preserve the original, editing reference bytes/hashes, prompt, reported image model label (`NOT_EXPOSED` when missing), version, usage (`NOT_REPORTED` when missing), tool calls and child/subagent evidence. Do not invent deterministic seed or exact backend name.
7. No implicit rerun after timeout, ambiguous completion, malformed output or failed visual review. Reserve the budget durably **before** process launch.
8. **Critical budget gate:** a CLI invocation can trigger up to 3 underlying image attempts via the built-in image-generator subagent. Until locally proven enforceable one-attempt behavior (or a separately reviewed budget contract explicitly authorizes the real maximum with reliable evidence), **block paid dispatch as `INTERNAL_ATTEMPT_BUDGET_UNVERIFIED`**. Merely requesting "one tool call" in natural language is not sufficient.

The sample command is a research template, not approval to generate. Prefer a non-generating capability/permissions inspection first.

## 4. First product: reference portrait expression variants

Initial user need: `isekai_examiner` / same portrait/person, fixed proportions/hair/clothes/accessories/crop/style; vary expression only.

Suggested product contract — **future additive schema, not currently accepted by factory**:

```yaml
factory_line: NONPIXEL
output_mode: IMAGE_ONLY
production_subtype: PORTRAIT_EXPRESSION_VARIANT
source:
  kind: EXISTING_RUN
  image_run_id: <approved_or_explicitly_research_allowed_source_run>
  source_image_sha256: <real_sha256>
identity_lock:
  project_sot_source: <actual_source>
  character_id: <canonical_character_id>
  preserve: [face_geometry, hairstyle, outfit, accessories, pose, framing, style]
variation:
  expression: surprised
  change_scope: facial_expression_only
provider:
  id: antigravity_cli
  workflow_id: agy_nano_banana_image
  selection: explicit_only
```

- Do not declare an image/reference capability in the registry until the adapter **actually sends the PNG bytes/path to `generate_image`** and receives a corresponding edited output, with evidence of reference consumption.
- One neutral approved base image may produce independent **neutral/smile/angry/surprised/sad/thinking** children, each with own budget/run/QA; no uncontrolled batch generation.
- Character identity features are derived from the project's source and the approved base image; no generic image "similarity" score automatically approves identity.
- Test exact crop/canvas, clothing/gear count, hands, hair, silhouette and facial feature consistency; distinguish **expression change** from **identity drift**. Any facial/identity review still requires a human decision.
- Preserve existing image-only terminal completion. Motion/video/sprite extraction must **not** be triggered for expression sets unless separately explicitly requested.
- Respect currently experimental/non-negative-conditioning limitations; prompt exclusion text cannot guarantee constraints.

## 5. Implementation phases and gates

**P0 — offline feasibility (no generation):**
- Detect `agy` version, supported `--print`, stream outputs, interactive login state without leaking secrets, permissions and tool catalog.
- Audit Antigravity image-generator child retry semantics and whether CLI/SDK can enforce a genuine hard one-generation bound.
- Determine where image artifacts are written and which return events unambiguously correlate files to the invocation. Validate Windows long-path and ACL/permission effects.
- Choose `agy` CLI vs typed SDK by achievable restriction/evidence, not by preferences.

**P1 — adapter + contract (fake tool only):**
- Implement `src/assetpipe/providers/antigravity_cli/` using current `cli_runner` reusable isolation/correlation primitives, extend registry/loader, provider readiness and fail-closed capability gate.
- Add fake CLI fixture, JSON/NDJSON parsers, tests for missing login, soft denial `exit=0`, no tool call, over-attempt, one vs multiple outputs, edit reference omitted, corrupt/foreign files, symlink/junction, secret echo, recursion, timeout and concurrent jobs.
- Keep `generation_requests == 0` in CI. Old 6 MCP schemas and unchanged default routing asserted.

**P2 — budget-authorized E2E:**
- Separate **one simple T2I** and **one reference-image-edit** cohort under explicit user authorization; prove tool execution, tool count, image count, input consumption, generated original, correlation and QA.
- Record real account version, image model label if surfaced, paid/plan usage where exposed, attempts and reviewed images. If auto three-attempt mode cannot be disabled/tracked with consent, keep BLOCKED and evaluate SDK/direct Gemini Image API instead.
- Never automatically mark image quality approved.

**P3 — project trial and promotion:**
- Same-person expression trial: neutral base + one emotion change, followed by controlled multi-expression set only with separate budget. Blind human review of identity lock and expression readability.
- If consistently successful, elect Antigravity as **preferred manual worker 2** for image edits; deprecating/hiding Grok default selection is a **separate reversible decision**. Never destroy Grok evidence or active registered path solely because a new provider exists.
- Publish accepted platform/version, backend uncertainty, known limits, run SHA, and explicit production-readiness state.

## 6. Stop conditions / relation to M3

- Stop if no bound on model image attempts, insufficient source isolation, account/usage not authorized, reference image not actually consumed, or output correlation can't be proven.
- Keep existing M3 factory modes, PIXEL64, SFX, shared motion route, pixel rules and source-first project canon unchanged.
- This design does not grant production activation, an external charge, a provider ACTIVE promotion or project SOT changes. Preserve failure evidence and exact old code behavior.

**Suggested first review evidence:** Official model/SDK/headless/changelog links above; follow with one offline `agy` version/capability/permissions probe on the user's authenticated host.
