# Local shared Asset Pipeline MCP

Registered in the Windows user's `~/.codex/config.toml` as `asset_pipeline`.
Restart the MCP server in Codex Settings, or start a new session, to load its tools.
This registration applies to local Codex clients using this user configuration;
cloud/remote hosts require their own installation.

Operator scripts are in `scripts/local_mcp/windows`, outside the distributable
`plugin/` package. This preserves the existing no-Python plugin packaging gate.

## Runtime

- Pinned origin/main: `12c21092baacfc4c939ebe5eaa1473e063c69551`.
- Launcher: `C:/workspace/asset-pipeline/workspace/mcp_runtime/launch.py`.
- Python: `C:/workspace/asset-pipeline/.venv/Scripts/python.exe`.
- Sources allowed: `C:/workspace` only. Supply absolute project paths.
- Outputs: `C:/workspace/asset-pipeline/workspace/plugin_runs`, partitioned by project_id.
- Compiler and child CLI import paths are pinned to this runtime.
- Dirty primary checkout and research artifacts are preserved.

Six tools: asset_capabilities, asset_build_brief, asset_route, asset_generate,
asset_continue_animation, asset_inspect_run. Compile occurs through the existing
pipeline; there is no separate compile MCP tool. Read the pinned runtime's
`docs/style_menu/AGENT_RECIPE_SELECTION_GUIDE_v1.md` and style menu before choosing
a model. Preserve explicit choices, generation budgets and human review gates.

## Verification (2026-10-07)

Actual stdio handshake and exact six-tool inventory PASS. Launched from isekai's
directory: reference access PASS, direct krea2_base route ROUTED; unsupported
character-reference route BLOCKED as required. Generation calls: 0.
MCP tests: 28 passed. Python CLI help PASS. ComfyUI 0.39.1 connection available;
Aseprite 1.3.18.6 and ffmpeg available. These checks do not establish generation
quality or approve any assets. Full protocol report: `verification.json`.

Windows restricted sandbox blocked strict path resolution in the first test
attempt; the same tests passed in the normal local host execution environment.

User config backup: `~/.codex/config.toml.before-asset-pipeline-20261007.bak`.
To update, deploy a separately verified main snapshot and then update revision.txt;
do not point the host at a temporary/archivable worktree or overwrite dirty main.

## Merge review verification (2026-10-08)

The archived revision's deploy/launch/verify scripts were executed again in the
separate `C:/workspace/asset-pipeline/workspace/mcp_review` directory. Actual
stdio handshake, exact six-tool inventory and external-project reference access
passed; the unsupported reference route was BLOCKED and direct Krea2 routing was
ROUTED. Generation calls: 0. The configured live runtime and user config were not
changed. A longer managed-worktree path hit the Windows path-length limit;
preserved failure artifacts remain there, and the documented short host path
passed. Use a short runtime directory on this Windows host.

This pins the historical `12c2109` snapshot. New main features, including Manual /
Rescue Override, require a separate verified runtime refresh; merging this
reference does not upgrade the installed runtime. Official Plugin Creator was
not run; local packaging/protocol validation is separate.
