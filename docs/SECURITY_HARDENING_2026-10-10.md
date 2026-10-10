# SECURITY-HARDENING-2026-10-10

Status: offline security regression verified. Provider generation not run.

Existing uncommitted modifications were preserved. No reset, revert, commit,
runtime replacement, workflow promotion, or legacy algorithm changes were made.

## Changes

- `assetpipe.paths.RootResolver` resolves symlinks/junctions and checks configured
  source/output containment. The MCP adapter passes this policy into routing,
  approval/provenance preflight and manifest inspection. It serializes the same
  host-controlled policy in `ASSETPIPE_ALLOWED_ROOTS` for its spawned CLI.
- Approval validates the source manifest, resolution report, evidence files,
  report candidates and nested declared provenance references. Files consumed
  for hashes or image validation are resolved before access. The approved export
  must identify the same master and validated export, with matching hashes.
- Codex global `generated_images` discovery and Grok shared sessions/home
  fallback were removed. A single reported session or the invocation's private
  workdir supplies correlation. Explicit paths obey the same containment rules;
  scans check resolved containment before file metadata access. Conflicting IDs,
  outside paths and updated previously populated sessions fail closed.
- Freshness remains an additional requirement. Copied reference inputs are in
  the pre-execution snapshot. Preservation checks containment again. Missing
  correlated outputs return `OUTPUT_MISSING`; invalid correlation returns
  `OUTPUT_UNCORRELATED`. The existing output-count ambiguity gate, single attempt,
  no retry, no provider fallback, hash, pixel and human review gates remain.

## Verification

- Required editable installation with `[dev,motion]`: succeeded. Initial sandbox
  attempts failed due package-index access and missing offline wheel support;
  the authorized normal-access installation succeeded.
- Final full pytest: **344 passed**, zero failures or skips, 82.18 seconds.
- **31 new synthetic security cases** cover nested provenance escapes, report
  rows, valid provenance, export consistency, environment propagation, Windows
  symlinks/junctions, scanned/explicit escapes, missing correlation, other-session
  images, same-session images, reused sessions, concurrent sessions, multiple
  outputs, Grok fallback removal and unchanged hash/pixel blocking.
- New tests invoke no model generation or approval-writing operation. Synthetic
  serialized records are marked as test data and confined to temporary directories.
- Both `assetpipe --help` and `python -m assetpipe --help`: exit 0.
- `git diff --check`: exit 0. Six MCP tool contracts remain unchanged.

## Separate lifecycle investigation

Initial CIM access was restricted by the sandbox; authorized read-only queries
provided process PID, parent PID, creation time, command line and Windows session.
Active PID 29084 was created at 15:11:24 JST, owned by Codex app-server PID 47164
(created at 15:10:14 JST). Its Python child PID 43576 was created afterward in
Windows session 11. The venv launcher and interpreter child are one ownership
chain; this observation alone does not establish a leaked server.

`scripts/mcp_lifecycle_probe.py` starts only its own server, sends initialize and
tools/list, then closes stdin. The saved probe (PID 14768, interpreter child 4716)
returned exactly six tools, exited 0 after EOF in 0.344 seconds, and had empty
stderr. A follow-up query found none of its recorded PIDs still present. The
existing active launcher PIDs remained present. No processes were terminated.

Evidence: `workspace/security/2026-10-10/mcp_lifecycle.json` and
`workspace/security/2026-10-10/process_followup.json` (local ignored run artifacts).
The probe preserves its temporary configuration and performs no generation.

## Remaining limits

- The active MCP launcher loads a pinned runtime under `workspace/mcp_runtime`.
  That copy was not modified or restarted; this patch requires a deliberate
  runtime update before the active server uses the hardened source.
- Synthetic tests do not establish real Codex/Grok output protocol compatibility.
  Real generation E2E was not run; missing session correlation intentionally
  fails closed. Correlation depends on the CLI reporting a truthful unique
  session ID and maintaining its session-directory contract.
- Standalone trusted Python/CLI callers without a resolver or the host policy
  retain their existing filesystem access. MCP supplies the boundary explicitly;
  the environment policy is host-controlled configuration, not an OS sandbox.
- References outside configured roots are rejected even when their hashes match.
  Historical provenance must be made available within explicitly configured roots.
- Resolution and access checks are not atomic filesystem-handle locking. A hostile
  local actor able to mutate allowed directories concurrently can still introduce
  check/use races; these tests do not establish protection against that threat.
- EOF shutdown of an idle owned probe does not prove host crash/disconnect or
  in-flight generation shutdown behavior. Active processes were left untouched.

Passing tests creates no human Aseprite approval, production-readiness claim,
provider ACTIVE promotion or Visual SOT promotion.
