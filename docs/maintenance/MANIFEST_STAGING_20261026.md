# Independent JSON staging — 2026-10-26

## Scope and evidence

Previous full regression at `c192842` recorded 712 passed, 3 failed and 1 skipped.
The three failures reached `assetpipe.manifests.write`, at `.tmp.replace(path)`,
with Windows error 5. Their isolated rerun passed. The owning external process,
if any, was not identified; antivirus/indexing attribution is not established.

The shared writer reused the same `<target>.tmp` for every call. A deterministic
two-thread barrier before publication reproduces the staging collision in the
old implementation (observed Windows error 5). This establishes a defect in the
writer, **not proof that concurrency caused all three historical failures**.
The old implementation also failed the fixed-staging-file preservation case;
the initial focused run was 2 failed / 3 passed.

## Changes and reuse

- Reuse the existing `src/assetpipe/manifests/__init__.py` public `write` function.
  No new persistence service, generation loop or provider behavior.
- Serialize before creating staging state. Exclusively create a unique temporary
  file in the target directory with `NamedTemporaryFile(delete=False)`.
- Close the owned handle, then call the existing `Path.replace` exactly once.
  Successful publication leaves no staging file from that call.
- Serialize the short replacement step through one process-local lock. Staging
  and serialization remain concurrent. This also covers different path spellings
  for the same target without a persistent per-path lock registry. Other processes
  are not coordinated, and this does not reserve budgets or lock whole pipelines.
- Propagate errors. Retain a failed staging file for inspection and preserve the
  previous target when replacement is denied. Do not retry or overwrite in place.
- Concurrent writes have last-successful-replace-wins semantics. This is not a
  read/modify/write transaction or a new budget reservation mechanism.
- Preserve JSON content/format, public signature, QA and review states, configured
  roots, generation reservations and all six MCP contracts. No legacy algorithms
  or production configuration changed.

## Validation

`tests/unit/test_manifest_writes.py` covers concurrent publication, preservation
of another fixed `.tmp`, serialization failure, single-attempt failed publication,
and a real Windows handle that withholds delete sharing. The last case reproduces
a real OS replacement denial without mocks; it confirms fail-closed behavior,
not recovery from a locked destination. Final focused result: **5 passed** (0.14 s).

The first implementation used only independent staging. Its full regression was
**719 passed / 1 failed / 1 skipped** (285.54 s): the new concurrent test produced
Windows error 5 even with distinct temporary sources. Thus independent staging
alone was insufficient. The final implementation adds publication serialization;
the test synchronizes completed staging and explicitly detects overlapping replace
calls. The initial full log is retained separately from final validation.

Final full regression: **720 passed / 1 skipped** in **298.65 s**, 721 collected,
Windows Python 3.11.9 / pytest 9.1.1. The skip is the existing unavailable local
migration benchmark fixture. The three historically failing cases pass in this
full run; this does not prove that arbitrary external locks cannot recur.

Required editable `.[dev,motion]` installation and installed `assetpipe --help`
both passed. `git diff --check` passed. Status: **OFFLINE_REGRESSION_PASS**;
**GENERATION_NOT_RUN**. No asset quality improvement is claimed by these IO tests.
Local logs: `workspace/manifest-staging-20261026/` (ignored run artifacts).

## Remaining limits and rollback

Independent staging removes shared temporary-file collisions; the process-local
lock prevents simultaneous publications from this writer's threads. A process that
locks the destination can still deny publication. No unbounded or bounded retry
is added, no provider is resubmitted, and no failed gate is advanced. No claim of
power-loss durability (`fsync`) or cross-call transaction isolation is made.

No image/video generation, image quality measurement, Golden/SOT approval,
production activation or live MCP replacement occurred. Motion real-generation
E2E and full Krea2 loader compatibility remain BLOCKED as previously documented.

Rollback: revert this commit; the public API is unchanged. Inspect retained
`.manifest.json.<unique>.tmp` files against their target before any manual cleanup;
they are evidence, not automatically published state.
