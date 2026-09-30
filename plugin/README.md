# Asset Pipeline local plugin

Create validated game-ready visual assets from prompts, reference images, or
project design sources using registered local production workflows.

```text
ChatGPT/Codex host → plugin instructions + six MCP tools → assetpipe → local providers
```

This package contains instructions/references and MCP wiring. Install the engine
separately; production code, models, and benchmark outputs are not copied here.
Start with [local setup](../docs/plugin/LOCAL_SETUP.md) and [tool contract](../docs/plugin/MCP_TOOL_CONTRACT.md).

The supported compatibility manifest is .codex-plugin/plugin.json. Its stdio MCP
command expects assetpipe-mcp on the host PATH and ASSETPIPE_MCP_CONFIG pointing
to a trusted local adapter config. The launcher fails closed without a config.

Local SDK/MCP execution is verified. Official Creator validation and actual
ChatGPT/Codex plugin-host installation are not yet verified. Creator was not
available, so overall M0 PASS is withheld. ChatGPT web remote registration is not
provided by this local-only package; no public endpoint or app ID is invented.

Read [status](../docs/plugin/STATUS.json) for measured gates. No public plugin
submission or publishing is performed. A ZIP is written under ignored workspace/
by scripts/package_plugin.py after MCP smoke evidence has passed.
