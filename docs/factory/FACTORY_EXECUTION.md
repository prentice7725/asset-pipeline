# Explicit still/audio factory execution

`factory execute` connects GENERATE requests for NONPIXEL/PIXEL64 IMAGE_ONLY and
SFX AUDIO_ONLY to the existing `pipelines.create` entry point. Existing route,
style/model compiler, provider, pixel/Aseprite and audio gates still apply.
Motion is blocked with BLOCKED_BACKEND_NOT_VERIFIED before still generation.
Existing-run sources are read-only and cannot trigger regeneration. The six MCP
schemas, legacy CLI behavior and pinned operating runtime are unchanged.

Plan/dry-run/inspect remain read-only. To execute later, an authorized operator
must supply both `--authorize-generation` and an explicit uint32 `--seed`, plus
`authorization.generation_budget` in the request. Its path is relative to the
request document and must remain inside the configured source roots. Those roots
must also explicitly include the configuration/output root. Authorization does
not come from a plan or from an art approval field.

The budget document has exactly these fields (illustrative values, not approval):

```json
{
  "schema_version": 1,
  "type": "FACTORY_GENERATION_AUTHORIZATION",
  "authorization_id": "0123456789abcdef0123456789abcdef",
  "project_id": "example_game",
  "asset_id": "example_asset",
  "request_sha256": "<SHA-256 of exact request bytes>",
  "workflow_id": "<explicitly authorized selected workflow>",
  "workflow_sha256": "<registry workflow hash>",
  "seed": 7,
  "max_requests": 1,
  "authorized_by": "<actual authorizing operator>",
  "reason": "<actual budget scope and consent>"
}
```

Create this record only after actual generation consent. The request references
the budget path; hashing the request does not include the budget file contents.
Changing the request, selected workflow, project, asset or seed blocks execution.
The adapter does not issue authorization templates or manufacture approval.
Budget attribution is an operator declaration, not a signed identity proof.

```powershell
# May generate/charge: do not run without separate generation consent.
assetpipe factory execute --request workspace/authorized_request.json --seed 7 --authorize-generation
```

Preflight and source revalidation precede an atomic directory reservation under
`workspace/factory_budget/<authorization_id>`. The directory is never released
after errors or ambiguous completion. Reusing the same ID, including concurrently,
fails closed. Do not delete reservations or reuse IDs to retry failed attempts.
Reservations are scoped to this configuration root; copying budgets to another
installation is not a global charge lock. Operators must coordinate installations
and assign an ID to each separately authorized request.

The isolated `run/` receives existing generation intermediates and QA. Adjacent
`execution.json` records request/budget/source fingerprints, route, seed, attempt,
failure or candidate state, manifest/output hashes and required human review.
SFX naming/category metadata is passed through unchanged. Existing override
authorization/reservation gates remain additional requirements.
FAILED QA never advances to candidate completion. All successful results remain
CANDIDATE_REVIEW_REQUIRED and game_ready false; no Golden, SOT, approved master,
provider ACTIVE or automatic listening approval is created.

Security tests cover paths, aliases, stale sources, scope mismatch, concurrency,
failed attempts and invalid results using synthetic dispatch only. Filesystem
replacement between validation and I/O remains a limitation; run with trusted
local ownership. A declaration cannot prove human consent, and seed semantics of
external CLI providers remain their existing unsupported/reproducibility policy.
Offline tests do not establish real-generation acceptance or production readiness.

## Offline validation — 2026-10-11

Windows / Python 3.11.9 isolated checkout: **542 PASS / 0 FAIL / 0 ERROR / 1 SKIP**
(543 cases). The existing local migration benchmark is unavailable in this
checkout and remains skipped. Factory contracts/execution: **96 PASS**, including
41 new synthetic adapter cases; additional Windows P1 fixtures: **22 PASS**.
Editable installation, CLI help, offline planning, actual MCP initialize/tools/list,
exact six-schema comparison and negative paths passed. Owned MCP test servers
closed via EOF. The first suite found a test module reload leaking monkeypatch
state; removing that reload fixed the regression without weakening assertions.

Pinned runtime files (954) retained their hashes. Historical uncommitted files
(75) retained their hashes; a separate portrait-repair CLI change in the original
checkout was preserved and excluded. Local evidence is outside source modules at
`workspace/reorganization/20261011/factory-execution/` in the original checkout.
No real generation, charged request, human approval, deployment candidate or
operational runtime replacement/restart/termination occurred.
Verdict: **OFFLINE_PASS / REAL_GENERATION_NOT_RUN / HUMAN_REVIEW_NOT_RUN**.
