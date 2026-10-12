# Codex local plugin registration correction — 2026-10-12

## Problem and installed correction

The installed skill loaded, but its `.mcp.json` used bare `assetpipe-mcp` without
an adapter config. That command was not on the inspected PATH. The absolute venv
entrypoint existed and rejected startup without config. An independent manual
host registration served the existing six tools through the approved pinned
launcher, masking the plugin's standalone configuration gap.

The local installation now invokes the absolute trusted venv Python with `-B`
and `workspace/mcp_runtime/launch.py` in `C:/workspace/asset-pipeline`.
That launcher retains `security-release-20261010-572b76ffe1e4` and its existing
adapter configuration. No engine source, runtime pointer, provider registry,
model, SOT, review state or generation policy was replaced.

Eight installed files were changed/added. The 14 broken README/guide/historical
links were repaired using real bundled documents or an engine-resource guide.
Registry and evidence paths resolve from the trusted adapter's core_root,
rather than from the plugin cache. Unrelated instructions, skill content and
line endings were preserved. The original installation is recoverable from a
verified ZIP before application.

## Reproducible source changes

`scripts/configure_local_plugin.py` prepares a new host-specific copy without
overwriting its source, installing, restarting or generating. It preserves
bundled historical notes, repairs flattened references only when the actual named
document exists, and rejects unresolved links, source reparse points and wrong
plugin/server identities. The portable shared template remains host-neutral.

`scripts/package_plugin.py` now validates links in every packaged Markdown
document. Previously only direct SKILL links were checked. Unknown references
are not removed or replaced with fabricated documents. A dedicated offline CI
job checks package links, preparation and help without a generation call.

## Validation

- Isolated Python 3.11.9 / MCP 1.30.0 full suite: **548 PASS / 0 FAIL / 0 ERROR / 1 SKIP**.
- The existing skip is the local migration benchmark unavailable in this checkout.
- New preparation/package regression tests: **6 PASS**.
- Editable install, CLI help and preparation help: PASS.
- Both prepared and actually installed `.mcp.json` commands: real MCP initialize,
  exact six full tool-schema comparison and outside-root denial PASS.
- Owned diagnostic servers exited via EOF with code 0. Existing operational
  sessions were not terminated or restarted.
- Installed broken Markdown links: **14 before / 0 after**.
- Official Plugin Creator validation, paid generation and human review: NOT_RUN.

Local evidence, original installation ZIP, hashes, before/after package reports
and protocol records are under
`C:/workspace/asset-pipeline/workspace/plugin_audit/20261012/`.

## Remaining host check and rollback

Open a fresh Codex conversation to verify host loading of the corrected cached
definition. The current conversation may retain the previous definition; the
stdio check proves the installed command works but is not a fresh Codex-session
load test. Manual host registration is retained until that distinction can be
verified. Both now identify the same pinned launcher.

If a rollback is required, preserve the installed files again and restore only
the changed files from `installed-plugin-before-fix.zip`; remove the two newly
added resource documents only if they still match this fix's hashes. Do not
switch the engine pointer, stop active MCP sessions or restore global image
fallback. Reinstallation can replace local paths, so repeat the preparation and
verification procedure after package updates. Passing offline checks does not
declare production readiness, provider E2E acceptance or Golden approval.

## Separate operational integrity observation

Comparison with the earlier sealed snapshot found different bytes for the live
`src/assetpipe/providers/cli_runner.py` and its bytecode cache. Normalizing CRLF/LF
made the source exactly equal to the sealed candidate; there is no source-content
diff, but the old byte/tree seal cannot be claimed for the live copy. Additional
manual approval and budget records also exist under the operational runtime's
workspace. This plugin fix did not write those files, remove them, restore the
source or reseal the runtime. Preserve them and assess operational integrity
separately before any release-integrity claim.
