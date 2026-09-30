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
