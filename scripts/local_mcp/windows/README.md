# Windows local deployment reference

These scripts preserve the actual shared MCP installation performed on this host.
They are host-specific operator scripts, not production pipeline modules or an
automatic installer. Review paths before using them on another machine.

Keep these Python operator scripts outside `plugin/`; that package intentionally
contains no production, adapter or installer Python code. On this Windows host,
use a short runtime path: deeply nested worktree paths can exceed the Windows
path-length limit while extracting the pinned archive.

The deployed copy lives under ignored `workspace/mcp_runtime`, not this directory.
No model files, generated images, source ZIP, user config or config backups are
included in Git.

To reproduce on the same configured host:

1. Copy these four scripts to `workspace/mcp_runtime`.
2. Run `git archive 12c21092baacfc4c939ebe5eaa1473e063c69551 --format=zip --output=workspace/mcp_runtime/source.zip` from the repository root.
3. Run `.venv/Scripts/python workspace/mcp_runtime/deploy.py`.
4. Back up the user's `.codex/config.toml` securely, then register:
   `codex mcp add asset_pipeline -- C:/workspace/asset-pipeline/.venv/Scripts/python.exe C:/workspace/asset-pipeline/workspace/mcp_runtime/launch.py`.
5. Run `configure_host.py` with that Python to set timeouts, then `verify.py` to
   perform an actual stdio handshake and read-only calls. Verification requires
   the explicitly referenced isekai project sample; change it for another host.
6. Restart the MCP server in Codex settings so sessions receive the tool list.

The launcher pins both server and child CLI imports to the archived revision.
It retains the six tool contracts, source-root restrictions and review gates.
`verify.py` never calls generation or animation tools.

See `docs/plugin/LOCAL_CODEX_MCP_SETUP.md` for the observed installation results.
