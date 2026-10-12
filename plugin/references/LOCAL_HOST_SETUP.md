# Local host setup

The plugin carries instructions and six MCP tools. The separately installed
engine owns generation, QA, manifests and review; this package grants no generation
budget and never changes Golden, Visual SOT or provider ACTIVE state.

The portable `.mcp.json` template expects `assetpipe-mcp` on the host PATH and
`ASSETPIPE_MCP_CONFIG` pointing to a trusted adapter YAML. Merely enabling the
plugin does not supply that configuration. The YAML identifies `core_root`,
`source_roots` and `output_root`; never derive these from an arbitrary chat folder.

For a host using an approved pinned runtime, prepare a local installation copy
with `scripts/configure_local_plugin.py` in the engine repository:

```text
python scripts/configure_local_plugin.py --source <installed-plugin> --output <new-local-copy> --python <trusted-python> --launcher <approved-pinned-launcher> --report <local-report.json>
```

The copy uses the supplied absolute Python/launcher paths, checks document links
and preserves the source installation. It does not install, restart, generate or
advance review state. Do not substitute the mutable repository checkout for an
approved pinned engine. Machine-specific paths belong in the local installation,
not the shared plugin template.

Before applying that copy, preserve the existing installed files and confirm they
still match the preparation report. Then verify the copied wiring with actual MCP
initialize/tools/list, exact six schemas and an outside-root denial. Close only
the owned test server via EOF; do not terminate active operational sessions.

After application, open a new Codex conversation and check that the skill and six
tools load. Existing conversations may retain earlier plugin definitions. If a
manual host MCP entry also exists, verify which registration serves the new
conversation before removing either entry. Matching both to the same approved
launcher avoids silently selecting another engine while this remains unresolved.

See [engine resources](ENGINE_RESOURCES.md) for installation, tool-contract and
historical validation records. Local tests are distinct from official Plugin
Creator validation, representative paid generation and actual human review.
