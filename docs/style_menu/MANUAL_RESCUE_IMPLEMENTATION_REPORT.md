# Manual / Rescue Override implementation report — 2026-10-08

Status: OFFLINE_CONTRACT_PASS / GENERATION_NOT_RUN.
Branch: `codex/style-manual-rescue`, based on origin/main `12c2109`.
Changes are in the attached `style-manual-rescue` worktree.
The original `C:/workspace/asset-pipeline` checkout and its existing local edits
were preserved. No public plugin publishing, SOT mutation or new model generation.

## Changes

| Files | Result |
|---|---|
| `src/assetpipe/brief/__init__.py`, `schemas/asset_brief.schema.json` | Optional subject domain, style lock, run-scoped override and evidence/budget file references |
| `src/assetpipe/styles/menu.py` | Approved manual override, asset SOT model binding, rescue priority, model/workflow separation and executor blocking |
| `src/assetpipe/styles/overrides.py` | Scoped approval, hashed repeated failure evidence, advisory candidates, optional read-only installation probes and durable one-request budget |
| `src/assetpipe/router/__init__.py` | Shared existing capability/recipe checks and original/selected/rejected route audit |
| `src/assetpipe/prompts/__init__.py` | Existing model-specific compiler reused for advisory proposals; no new prompt generator |
| `src/assetpipe/pipelines/__init__.py` | Pre-dispatch authorization/reservation, existing QA/manifest preservation and original output hashes |
| `src/assetpipe/cli/__init__.py` | `rescue-plan`, which never generates |
| `tests/unit/test_style_overrides.py`, `tests/fixtures/style_menu_routes_v1.json` | 31 offline tests and 25 complete baseline decisions for 24 styles |
| `README.md`, docs and plugin copies of `AGENT_RECIPE_SELECTION_GUIDE_v1.md` | Manual / Rescue Override contract and limitations |
| `MANUAL_RESCUE_OVERRIDE.md`, this report | Approval/evidence/budget schema guidance, actual fixture scope, validation and SOT follow-up |

The menu YAML, catalog, model recipes and workflow registry were not modified.
No Grok STYLE-103 recipe or unverified dialect was added.

## Routing before / after

| Case | Before | After |
|---|---|---|
| No override, STYLE-101–124 | Original menu bindings | Entire route decision JSON identical; STYLE-117 includes both policies |
| STYLE-103 + approved Krea2 override | Binding conflict | USER_OVERRIDE: krea2 / krea2_base / comfyui; original Anima default recorded |
| STYLE-103 + Grok without recipe | Menu binding conflict | Explicit missing compatible recipe block |
| Grok executor + Krea2 ComfyUI | No supported executor contract | EXECUTOR_UNAVAILABLE; provider never silently changed to grok_cli |
| Workflow alias used as model | Undifferentiated binding conflict | MODEL_OVERRIDE_IS_WORKFLOW_ALIAS with correct model profile |
| Mismatched model/workflow or style | Blocked | Blocked |
| Hard SOT model prohibition | No supported run exception | Requires explicit scoped SOT exception approval; SOT untouched |
| Rescue without repeated approved evidence | No supported rescue | Blocked |
| Rescue proposal only | No proposal command | At most three compatible candidates; zero generation authorization/requests |
| Override create without budget or reused request ID | No override dispatch path | Blocked before provider call; no silent fallback/retry |
| PIXEL_STATIC / PIXEL_ANIMATION / SFX | Existing paths and gates | Existing routes/gates unchanged; optional subject field does not change route |

## Executed verification

- `.venv/Scripts/python -m pip install -e ".[dev,motion]"`: PASS.
- `.venv/Scripts/python -m pip install -e ".[mcp]"`: PASS. The fresh worktree
  initially lacked this existing optional dependency; the collection error was
  resolved before completing the full gate.
- `.venv/Scripts/python -m pytest --junitxml=workspace/manual_rescue/pytest.xml`:
  **363 passed, 1 skipped**, 108.05 seconds. The skipped pre-existing test is
  `tests/unit/test_assetpipe.py:125`, local migration benchmark data unavailable.
  No failed tests/errors. All 31 new tests pass, including the complete baseline
  decision comparison, scope isolation, SOT priority, unavailable executor,
  fingerprint/capability/EXPERIMENTAL gates, proposal-only behavior, budget replay
  protection and manifest/QA/provenance retention.
- `.venv/Scripts/assetpipe --help`: PASS; rescue-plan visible.
- Actual CLI route and compile-prompt for the unchanged STYLE-103 example: PASS,
  Anima Base rebuilt remains the default. No provider generation call.
- Protected-file audit against HEAD: **325 files unchanged**. All **216 archived
  original PNG SHA256 values match** the immutable evidence archive. Includes
  menu winners, catalog/recipes/registry, provider implementations, PIXEL/SFX/motion
  code, all six MCP contracts and historical evidence.
- `git diff --check`: PASS. Original checkout was not reset or merged.

Local verification artifacts are under `workspace/manual_rescue`: pytest.xml,
protected_files.json, default_route.json and default_compiled.json. Unit fixtures
use temporary test-only approvals and existing regression images; they are not
real generation evidence or human artwork approvals.

## Remaining limits and SKY RENDEZVOUS follow-up

This verifies routing/authorization/compiler contracts, not better aircraft
geometry, style fidelity or production quality. No real override generation E2E,
rescue image experiment, new provider authentication/install/cost verification,
benchmark, Golden promotion or Aseprite art approval occurred.

Grok/Codex/Claude executor connections remain unavailable. Installing a provider
CLI does not verify the commanding agent. Grok STYLE-103 remains blocked pending
a separately implemented compatible recipe/dialect and real validation.
Installation probes report model/node presence only; full hashes/licenses/costs
still require execution preflight. The initial override budget allows one request
per approval and conservatively consumes ambiguous/failed dispatches.

Future subject-specific winners are not activated or inferred from these tests.
Global primary_model and historical winner records remain intact; PROVISIONAL is
never promoted automatically. Semantic/composition/style review stays unvalidated
and outputs remain REVIEW_REQUIRED, with existing human/Aseprite gates preserved.

For SKY RENDEZVOUS, the SOT owner should separately review a revision retaining
STYLE-103 and current Assault/Buster identity, silhouette, colors and equipment;
explicitly distinguish independent Assault from Buster heavy-gunship roles;
identify approved failure artifacts and asset-local model-exception authority;
approve a concrete Krea2 workflow exception and separate generation budget if
desired. Requiring Grok as executor also needs a verified connection adapter.
These are proposed follow-ups based on the request, not edits to the live game
SOT. No Google Drive document was read or modified by this implementation.

See [the full contract](MANUAL_RESCUE_OVERRIDE.md) for the exact approval, failure
and generation authorization record fields.
