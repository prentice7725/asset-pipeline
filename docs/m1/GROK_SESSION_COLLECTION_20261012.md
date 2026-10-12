# Grok canonical-cwd collection correction — 2026-10-12

## Observed failures

SKY_RENDEZVOUS `sr_canyon_sky_20261012/c00e2a6c80e34d3bb0b99478f576f385`
failed with OUTPUT_UNCORRELATED; `sr_canyon_far_20261012/700fea31a1954823a493187e56b74b03`
failed with OUTPUT_MISSING. Both preserved Grok 1.0.50 stdout containing an exact
invocation sessionId and text ending `images/1.jpg`.

Read-only filesystem inspection found the matching session stores under the
URL-encoded canonical long cwd. The pipeline had prepared only the URL-encoded
8.3 cwd. Grok resolved the short cwd before persisting its session directory.
The absolute-path extractor additionally treated the slash in `images/1.jpg`
as `/1.jpg`; an HTTPS URL could be misread as a drive path starting `s:`.
This inspection did not import, hash, promote or regenerate the real images.

## Change and preserved security boundaries

Keep the verified 8.3 command cwd, job uniqueness, private API-key home and
one-attempt invocation UUID. Derive one additional store from that same job's
canonical cwd and trusted session home before dispatch. No shared-home/session
directory enumeration is added to collection, and no directory is derived from
an arbitrary CLI-reported path. Only the exact reported invocation ID below
these predetermined stores or the private workdir can supply newly created files.

Both stores participate in the pre-dispatch snapshot. Session-entry symlinks and
Windows junction aliases are rejected before scanning; resolved containment is
checked for scanned and explicit files before metadata/content reads. Conflicting
parsed/nested IDs fail closed. Other sessions and missing correlation never become
fallback output. Multiple resulting images retain OUTPUT_AMBIGUOUS handling.

Relative/URL text fragments are not reinterpreted as absolute filesystem paths.
Relative text alone does not authorize a file: collection still requires a
reported owned session and a real new contained file. Genuine drive/POSIX
absolute paths retain their explicit containment check.

The patch includes the previously deployed Windows namespace/8.3 isolation
dependencies which were not yet on main. Existing local provider files and tests
are preserved rather than reset. Codex shares the absolute-path correction and
conflicting-ID guard; no Codex generated_images global fallback is restored.

## Limits and operation

The canonical URL component must be representable within the filesystem's
255-byte component limit. An unrepresentable additional store is not searched or
guessed; the legacy short-cwd store remains the only configured session store.
This does not claim Grok 1.0.50 supports every deeply configured canonical cwd.
Existing Windows short-path/path-budget blocking and no-8.3 rejection remain.
Filesystem replacement between validation and reads remains a limitation.

Synthetic fixtures reproduce the observed text/encoding mismatch, canonical and
legacy stores, missing/foreign IDs, sibling aliases, external absolute paths and
concurrency. They make zero model requests and create no real approval.
The six MCP schemas, quality/review gates, provider EXPERIMENTAL status and
single-attempt/no-fallback policies remain unchanged.

This source correction does not replace the pinned operational runtime or retry
either failed generation. Their existing budgets remain consumed. Runtime
rollout, any existing-output recovery and a new paid E2E need their own authorized
steps. Never use arbitrary shell generation to bypass the production skill.

## Offline validation

Windows / Python 3.11.9 / MCP 1.30.0: **560 PASS / 0 FAIL / 0 ERROR / 1 SKIP**
(561 cases). The existing migration benchmark is unavailable in the isolated
checkout; it remains skipped. Focused collection/Windows/security: **57 PASS**;
additional Windows P1 fixtures: **22 PASS**. Editable installation, CLI help and
actual offline MCP initialize/tools/list with exact six full schemas and negative
paths passed. The owned test server exited via EOF. Four original provider/test
source files retained their byte hashes. Model generation, operational activation,
real approval and failed-run retry remain NOT_RUN.
