# Asset Pipeline contributor instructions

Read docs/bootstrap_directive.md and docs/migration_inventory.json before pipeline changes.
The legacy pixel-pipeline is read-only migration source; do not rename, delete, or refactor it.
Keep Python CLI primary, workflows in config/workflows, and all run artifacts outside source modules.
Do not rewrite verified algorithms or add GUI, web UI, MCP, DB, model research, or cloud deployment.
Never advance past a failed gate. Verify external tools with real executions before reporting PASS.
Preserve intermediates, source hashes, generation parameters, QA reports, and explicit review states.
Generated images/animations remain candidates until required Aseprite review.
Safe operations must not redesign identity, clothing, equipment, or silhouette semantics.
The verified direct profile requires explicit blue-tunic/white-background compatibility; never infer it.
Run `.venv/Scripts/python -m pip install -e ".[dev,motion]"`, `.venv/Scripts/python -m pytest`, and `assetpipe --help`.
Stop at ASSET_PIPELINE_V0_1_BOOTSTRAP_PASS. New features require a separate user request.

The user-authorized Plugin M0 milestone permits a local thin MCP adapter under
integrations/mcp and instructions/reference packaging under plugin. Read
docs/plugin/M0_DIRECTIVE.md for this milestone. Keep production algorithms in
assetpipe, expose exactly six high-level tools, restrict model paths to configured
roots, and preserve all QA/review gates. No public plugin publishing or cloud service.
Do not claim Plugin Creator validation passed unless the official creator actually ran.

The user-authorized M1 milestone permits NONPIXEL_IMAGE multi-provider generation (comfyui, codex_cli,
grok_cli) under src/assetpipe/providers. Read docs/m1/M1_DIRECTIVE.md and docs/m1/PROVIDERS.md. Pixel/SFX paths and
the six MCP tool contracts stay unchanged. CLI providers stay EXPERIMENTAL and explicit_only until
scripts/provider_e2e.py has recorded real-generation evidence; the registry loader rejects ACTIVE without it.
Never add API-key bypasses, implicit provider fallback, automatic retries, or fabricated images. Report a missing or
unauthenticated CLI as BLOCKED/UNAVAILABLE and do not declare M1 complete without real E2E evidence.

The user-authorized M2 milestone permits shared NONPIXEL_IMAGE Style Intelligence under
config/styles and assetpipe.styles. Read docs/m2/STYLE_INTELLIGENCE.md. Preserve Visual SOT
locks, explicit model choices, all QA gates and six MCP tools. Never fabricate style approval,
quality scores or evidence; M2 tests cannot replace provider real-generation E2E.

The user-authorized M2.6 milestone permits offline prompt mining, candidate recipes and source analysis. Read docs/style/PROMPT_MINING_METHOD.md and RECIPE_VALIDATION.md. Submit zero generations in this milestone; M2.5 real image and full pipeline validation follows with a separately authorized budget. Preserve production defaults, six MCP contracts, legacy pixel baseline and all review gates.

The user-authorized M2.5 resumption permits existing-candidate static revalidation and a resumable local style lab. Separate historical equivalence from current approved-master E2E. Never synthesize human Aseprite review; stop at REVIEW_REQUIRED until actual approval. The initial 12-sample PIXEL_STATIC/NONPIXEL_IMAGE cohort executes independently through its own model/workflow preflight and output-specific QA, with persistent pre-reserved budget and no retries or fallback. Only PIXEL_ANIMATION E2E requires a currently approved compatible Static Master. Preserve explicit legacy art rejection and never promote the legacy fixture. Read docs/style/M25_BLOCKER.md.
