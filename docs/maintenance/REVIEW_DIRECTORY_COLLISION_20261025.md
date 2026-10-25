# Review directory collision — 2026-10-25

Branch `codex/review-directory-uniqueness-20261025`, based on `a56428a`.
This separate fix was required by the full regression after the
[Factory namespace correction](FACTORY_ROOT_NAMESPACE_RACE_20261025.md).

## Trigger and change

`test_review_preserves_original_manifest_and_unreviewed_state` failed when two
calls to `build_review` received exactly the same `now()` value. The old directory
name was solely that timestamp, so the second `mkdir(exist_ok=False)` raised
WinError 183. This was not a path-policy rejection or duplicate generation.

Review invocations now use a UUID directory under the existing `review_artifacts`
parent. The timestamp is retained explicitly as `created_at` in the report.
Atomic creation still rejects a preexisting directory; there is no overwrite,
silent reuse or automatic retry. UUID directory names are 32 characters, avoiding
the length increase of appending a UUID to the old timestamp directory name.
Existing timestamp-named artifacts remain untouched and readable by their paths.

The preview algorithm, source image/manifest, artifact hashes, review checklist,
advisory state and approval effect are unchanged. The report gains one additive
metadata field; CLI/MCP contracts and production defaults stay unchanged.

## Reproduction and validation

The existing preservation test now freezes the clock. It failed deterministically
on the old implementation with the same FileExistsError, then passed with the
new directory allocation. It checks distinct output directories, equal recorded
creation times, unchanged original bytes and the same unreviewed/advisory state.

- Combined review, path-namespace, Factory and security subset: **111 passed**,
  4.76s.
- Required editable `.[dev,motion]` install and installed CLI help: PASS.
- Final full offline regression: **708 passed, 1 skipped**, no failures, 257.68s
  (709 cases). The skip is the unavailable local migration benchmark fixture.
  Both the original Factory concurrency test and the frozen-clock review test
  passed. The earlier receipt-replacement error did not recur in this final run;
  this directory fix does not claim to solve that separate I/O issue.
- `git diff --check`: PASS; the primary cleanup checkout remains clean.

The current combined offline regression gate is PASS. This does not clear any
real-generation, model-quality, human-review or production activation gate.

Local evidence is retained under ignored
`workspace/factory-roots-debug-20261025/`: `review-frozen-before.log`,
`review-focused-after.log`, `review-install.log`, `review-cli-help.log` and
`pytest-review-release.log`. Earlier namespace and full-suite failure records
are retained separately; they are not relabelled as passing runs.

No actual generation, human approval, Golden/SOT change, live MCP replacement or
operational activation was executed. Model/FP8 adapter and real E2E gates remain
independent. Revert this commit to restore timestamp-only allocation; no data
migration or deletion is required. The Factory namespace fix is a separate
commit and does not need to be reverted with this one.
