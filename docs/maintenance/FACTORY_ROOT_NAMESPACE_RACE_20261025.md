# Factory reservation path rejection — 2026-10-25

Branch `codex/factory-concurrency-roots-20261025`, based on `e11ec77`.
User-authorized follow-up to the
[actual-base audit's failed regression gate](../research/KREA2_BASE_CONTRACT_20261025.md).

## Cause and evidence

The losing concurrent Factory invocation sometimes returned `Path is outside
configured roots` instead of `FACTORY_BUDGET_ALREADY_RESERVED`. Only one synthetic
provider call occurred; duplicate generation was not observed.

A temporary test-only observer captured three independent failures in 30
concurrent cases. In each case, the configured root and requested budget path
were ordinary `C:\...` paths, but `Path.resolve(strict=False)` returned
`\\?\C:\...\workspace\factory_budget`. No root-policy environment variable was set.
`WindowsPath.is_relative_to` treats those namespace spellings as different
anchors, so the same location was rejected before atomic reservation.

This is a directory-creation timing problem, not a full-suite-only dependency:
the isolated repeat produced **3 failed / 27 passed**. An instrumented baseline
full run happened to pass, consistent with the intermittent observations.

The installed Python 3.11.9 `ntpath.realpath` conditionally removes its extended
prefix after filesystem checks, as shown in the
[official CPython source](https://github.com/python/cpython/blob/v3.11.9/Lib/ntpath.py).
This is consistent with the captured namespace variation during concurrent
directory creation. Individual WinAPI calls were not instrumented; no particular
WinAPI error code or CPython security defect is asserted.

## Change and preserved boundaries

`src/assetpipe/paths.py` still resolves the filesystem path first with the caller's
original `strict` value. Already accepted resolved paths are returned unchanged.
Only after the original containment check fails, a pure comparison helper treats
safe resolved extended DOS and UNC spellings as aliases of their ordinary forms.
It then repeats component-based containment against the same configured roots.

The helper does not reinterpret GLOBALROOT, volume/device namespaces, trailing
dots/spaces, reserved DOS names, alternate streams, parent traversal or control/
wildcard characters. Such extended spellings remain unconverted. Explicitly
configured extended roots retain their representation on successful alias
resolution, preserving downstream identity checks. POSIX paths are unchanged.
UNC conversion is tested as pure path logic; no live network share was contacted.

No filesystem-resolution error is swallowed, and no lexical substitute is used
before link resolution. Actual symlink and junction escapes remain rejected for
existing and missing files, including extended input spelling. Authorization,
atomic `mkdir` reservation, provider dispatch and receipt code are unchanged.
There is no generation retry, lock replacement, fallback or extra permission.

Reserved-name checks use `ntpath.isreserved` where available, with the Python
3.11/3.12 `PureWindowsPath` compatibility branch. Python 3.13.12 independently
executed eight pure-path cases using the modern API; this is not a second full
test-suite run or a filesystem/network test on that runtime.

## Tests and current status

- Two deterministic regression cases inject the observed extended result **after
  real resolution**, at the budget directory and reservation directory. Both
  fail on the original implementation. They pass after the fix while retaining
  the original one-call/one-reservation assertions.
- Same independent concurrent repeat after the fix: **30 / 30 passed**.
- Final focused namespace, Factory execution and security checks: **102 passed**,
  4.61s. Coverage includes explicit extended roots, overlapping roots, sibling
  rejection, special-name non-conversion and real link/junction escape checks.
- An earlier focused run encountered the separately known Windows `WinError 5`
  while replacing a receipt file in `test_bad_result_cannot_advance[wrong_project]`.
  The final focused run passed that case. Receipt code was not changed; that
  earlier failure remains recorded and is not claimed fixed by namespace handling.
- Required editable `.[dev,motion]` install and installed `assetpipe --help`: PASS.
- Full offline regression: **707 passed, 1 failed, 1 skipped**, 238.59s.
  All Factory concurrency and namespace/security cases passed. The failure is
  `test_review_preserves_original_manifest_and_unreviewed_state`: two review
  invocations received the same clock value and collided on the timestamp-only
  output directory (WinError 183). It is a separate, now evidenced issue; the
  whole regression gate remains BLOCKED pending its independent fix.
  Follow-up: the [separate review allocation fix](REVIEW_DIRECTORY_COLLISION_20261025.md)
  retains this failed run and records the combined final regression separately.
  On that stacked branch, the final combined suite is **708 passed, 1 skipped**,
  no failures, 257.68s. This clears the current offline regression gate; the
  historical failed run above remains a failed run.
- The migration benchmark skip is unchanged. `git diff --check` passed.

Local ignored evidence: `workspace/factory-roots-debug-20261025/`, including
`root-rejections.jsonl`, `repeat.log`, `deterministic-before.log`,
`repeat-release.log` (30 passed in 1.49s), `focused-release.log`, `focused-final.log`, `python313.json`
and `pytest-release.log`. The observer and repeat harness live there as test-only
artifacts and are not shipped as production modules. The initial attempted
duplicate-node invocation collected only one test; its `isolated-loop.log` is
not counted as the 30-case repetition.

## Reuse, quality, remaining gates and rollback

The existing `RootResolver`, filesystem resolution and component containment are
preserved; no new security subsystem or provider is introduced. The existing
Factory concurrency test is reused, with improved assertion diagnostics. Tests
never submit an actual provider request or approve an asset.

This fix addresses a false root denial, not pixel-art quality. All previous
real-model/FP8 adapter, actual generation, human review and engine-import gates
remain independent. No Golden/SOT, workflow default, six MCP contract, live
adapter configuration or operating service changes are made.

Revert this commit to restore previous behavior. Only the shared path policy,
its tests and evidence documentation change; there is no data migration or
runtime activation to reverse.
