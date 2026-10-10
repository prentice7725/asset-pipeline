# P1 session alias correction — 2026-10-10

The P1 identified in the runtime preparation review is corrected in the working
tree and in a new isolated pinned-runtime candidate. The operational runtime has
not been installed, replaced or restarted. This is offline verification, not
approval, production readiness or SOT promotion.

## Defect and correction

Containment relative to the shared session parent previously allowed a reported
session directory to be a symlink/junction to a sibling session. Codex and Grok
could consequently collect the sibling's images despite a matching reported ID.

`assetpipe.providers.cli_runner.session_scope` canonicalizes the trusted parent
and inspects the reported session entry with `lstat` before scanning or checking
image metadata. It rejects symlinks, Windows reparse points (including junctions),
canonical-directory mismatches and non-directory entries with
`OUTPUT_UNCORRELATED`. It rechecks session identity after collection. A missing
session directory continues to yield no image. The common function protects both
providers and both explicit and scanned output paths. Existing containment,
freshness, ambiguity, hash, pixel and review gates remain in force; the global
image fallback was not restored.

The patch changes only `src/assetpipe/providers/cli_runner.py` and
`tests/unit/test_security_hardening.py`. The existing uncommitted Grok provider and
fake-provider edits were preserved and are excluded from the pinned candidate.
A test-root helper accommodates both the current source's invocation-specific
Grok parent and the preserved pinned provider's original layout.

## Offline evidence

Evidence directory: `workspace/security/runtime-prep-p1-fix/`.

- Before correction, all eight new sibling-alias cases failed: Codex/Grok ×
  symlink/junction × scanned/explicit. The tests prohibit image scanning and
  usability checks before alias rejection. All eight pass after correction.
- Corrected isolated candidate full pytest: **415 passed, 1 skipped**, 416 total.
  The skipped test requires local migration benchmark data absent from the
  isolated copy. No synthetic test creates an actual approval or external image.
- Source full pytest with shorter workspace basetemp: **350 passed, 2 failed**.
  One failure is the existing isolation assertion that temporary jobs must be
  outside the repository (the chosen basetemp was inside it); the other is a
  `FileNotFoundError` in the preexisting uncommitted Grok isolated-home path.
  Default-temp provider tests likewise fail in that Grok path. Extended Windows
  paths are incompatible with the fake CLI launcher. These source failures are
  unresolved and this report does not label the whole working tree PASS.
- Actual stdio MCP initialize/tools-list and safe dispatch for all six tools:
  PASS. Exact six schemas match the unchanged pinned runtime. Root traversal,
  nested source manifest/evidence and symlink escape rejection: PASS.
- Both CLI help smoke checks and isolated Python/module import identification:
  PASS. Python 3.11.9; test process uses the existing isolated test venv, candidate
  source/imports and read-only operational dependency directories. Capability
  readiness is an offline test stub, not live provider certification.
- Test-owned MCP processes closed through stdin EOF with observed exit code 0.
  No existing operational process was terminated. External generation calls: 0.
- Preservation SHA checks: all 55 preexisting dirty/untracked files, all 946
  operational runtime files and all three host pointer/config files unchanged;
  candidate files unchanged during tests.

The new sealed candidate contains 875 files. Its tree SHA-256 is
`64a44ef06d7d032aaaf3e24b6885fb05c2d61b485ebda77b886f61c5f1f7b1d7`.
Archive SHA-256:
`17705672b92b364c230d854bd9e3388fe657a530a3c3505ce8dbf91b98a3ed08`.
`candidate_provenance.json`, `sealed_candidate.json`, `pytest.xml`,
`protocol_summary.json`, `import_probe.json` and `preservation_after.json` retain
the machine-readable evidence. The earlier failed candidate and backup remain
preserved as historical evidence.

## Activation boundary and remaining limitations

Use the backup/install/rollback plan in
`SECURITY_RUNTIME_PREPARATION_2026-10-10.md`, substituting this new sealed candidate
and its hashes. Do not activate the earlier P1-affected candidate. Before a
separately approved switch, recheck process ownership and in-flight generation;
prior session/queue snapshots are not a current quiescence guarantee. No runtime
pointer change or dependency reinstall was performed. Git publication is separate
from runtime activation and does not authorize it.

Filesystem validation is path based, not an atomic handle-based read/copy. The
pre/post checks reject observed aliases but do not prove immunity to an adversary
mutating a directory between checks and file access. Operational dependency
sharing also means this is source/process isolation, not a fully independent
dependency installation. Real Codex/Grok generation, provider readiness and
approved-master E2E remain untested and require separate authorization. Preserve
single attempts, explicit providers and all review gates; a failed installation
must leave the service disconnected rather than automatically restoring an old
runtime with global fallback behavior.
