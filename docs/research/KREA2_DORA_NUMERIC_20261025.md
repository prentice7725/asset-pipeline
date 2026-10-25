# Krea2 magnitude: isolated numeric validation — 2026-10-25

Branch `codex/krea2-dora-numeric-20261025`, based on `fd620b4`.
User-authorized next step after the [installed loader audit](KREA2_LOADER_COMPATIBILITY_20261025.md).
This implements an **unregistered dense merge candidate and diagnostic**, not a
production loader, model conversion or generated-image experiment.

## Result and gates

**FP32_FP64_PASS_BF16_MISMATCH** against hash-pinned extracted upstream methods.
The BF16 merge fails the stated tolerance. **Production compatibility remains
BLOCKED**; the candidate is not connected to the Pixel64 workflow.

| CPU comparison | Cases within tolerance / total | Largest absolute output error | Meaning |
| --- | --- | --- | --- |
| FP64 | 72 / 72 | 1.7763568394002505e-15 | Dense source-candidate arithmetic agrees within 1e-10 absolute/relative tolerance |
| FP32 | 72 / 72 | 1.430511474609375e-06 | Dense source-candidate arithmetic agrees within 1e-5 absolute/relative tolerance |
| BF16 | 24 / 72 | 0.0625 | Only zero-strength cases meet 1e-5 absolute/relative tolerance; all 48 nonzero-strength cases mismatch |
| Unsupported-input guards | 8 / 8 rejected | n/a | Float8, integer, mixed dtype, wrong magnitude axis, invalid strength, unknown alpha, nonfinite values and zero adapted norm rejected |

No tolerance was relaxed to make BF16 pass. These are deterministic synthetic
linear-layer outputs, not pixel-quality measurements. All actual Krea base/LoRA
weights remain unloaded in this step. Actual model mapping, quantized-base
behavior and image quality are unverified; generation count is zero.

## Source recovery

The public repository has no tags in the checked tag inventory. Searching its
`version.py` history located a commit declaring `VERSION = "0.12.9"`:
[`6d8afa5684000b69db97cc40504a972a85615e3b`](https://github.com/ostris/ai-toolkit/blob/6d8afa5684000b69db97cc40504a972a85615e3b/version.py),
2026-08-09 00:58:11 UTC. The
[software metadata constructor](https://github.com/ostris/ai-toolkit/blob/6d8afa5684000b69db97cc40504a972a85615e3b/info.py)
uses this version value, consistent with the unchanged adapter file's metadata.

The last commit before the next version bump is
`72623ed3d668828a8b7f893172d6409d1d2fbb8f`; it still declares 0.12.9. The next bump,
`61da9c95d31474931856e7d9458c27f06275437a`, is dated 2026-08-09 18:39:30 UTC.
The checked four-commit interval changes neither relevant DoRA file. Both
endpoint hashes also match the files previously examined at 0.13.39 main.
This identifies a **version-compatible source candidate**, not the author's
exact training checkout, modifications, dependency lock or base-model revision.
`training_commit_match` remains **NOT_VERIFIED**.

| Pinned file | SHA256 |
| --- | --- |
| `version.py` | `5048231d23b7f18ed374381b77430be0f301ac7f342de34f305bc8c2e984ba6b` |
| `toolkit/models/DoRA.py` | `0b7a66971db200d0389a2d0b73ba8f242dc0d576db262511b4278ee7efe03ae9` |
| `toolkit/network_mixins.py` | `0c1b621503231a9a7f165f7631ff34f7a888857a6ea0969190d6c05ae50f3e8f` |
| `LICENSE` (MIT, Ostris LLC) | `e73058fe55271c3bb4f991e695110525c9597f254360413968e01c95b0180f51` |

## Executed comparison boundary

`scripts/krea2_dora_numeric_probe.py` checks these source hashes before compiling
selected AST function definitions. It executes the unmodified bodies of:

- `ToolkitModuleMixin.forward`, `_call_forward`, `broadcast_and_multiply`;
- `DoRAModule.apply_dora`, `_get_weight_norm`, `get_orig_weight`, `get_orig_bias`,
  and `transpose`.

Full ai-toolkit import, constructors, training, model integrations, network
activation wiring and quanto execution are **NOT_RUN**. Real PyTorch CPU Linear
modules supply controlled weights, bias and a uniform multiplier. Minimal network
state supplies the inference branch; marker classes satisfy inactive quantized
`isinstance` checks. This is explicitly not a full upstream runtime test. Imports
and unrelated top-level source statements are not executed. Source files and
the installed ComfyUI `weight_decompose` file are rehashed after the run.

The installed source hash remains
`484f0d83a96e700f80c793e4bcc6a897d633233e51a59191d91da5e59da345c7`.
Its real `weight_decompose` is called with a reshaped output-axis scale as a
counterexample, without editing or registering it. Each case records that
result's difference separately from the candidate's difference.

Fixtures use seed 7725 and identical FP64-generated values cast into each dtype:
5x3, 3x5 and 4x4 weights, rank 2, bias present/absent, 2D/3D inputs,
strengths 0/0.5/1 and explicit alpha/rank ratios 1/0.5. Dropout, training,
per-example differing strengths, mixed dtypes, convolution and quantized bases
are outside this candidate's scope. No missing alpha is inferred as approval
of a particular ratio for the actual model.

## Candidate semantics and why BF16 blocks merging

Write `D = B @ A`, strength `s`, alpha/rank `a`, and learned magnitude `m`.
For nonzero uniform strength, the inspected source combines an ordinary
low-rank residual with its magnitude correction. In real arithmetic the merged
candidate is:

```text
V = W + s*D
W_candidate = (m / row_norm(V))[:, None] * V + s*(a - 1)*D
y = linear(x, W_candidate, original_bias)
```

At zero strength the source bypasses the adapter, so the candidate returns `W`
directly. At fractional strength this differs from interpolating between `W`
and a fully adapted normalized weight. The explicit alpha term also matters:
the inspected forward's correction forms `W+s*D`, while the low-rank forward
uses alpha/rank separately. Assuming alpha/rank=1 hides that distinction.

The source computes separate low-rank and correction forwards with intermediate
casts and rounding. A single BF16 merged matrix does not preserve that execution
order; this measured merge therefore fails strict equivalence. The max error
0.0625 is not a measured effect on any Krea image. It must not be used to justify
a global loader patch, checkpoint rename or claimed quality improvement.

## Reproduce and remaining work

Use the existing ComfyUI Python environment, which already has torch. No package
or node installation is needed. Put the four exact pinned files above in a local
source directory (flattened filenames) and retain their MIT license.

```powershell
& <ComfyUI>/.venv/Scripts/python.exe scripts/krea2_dora_numeric_probe.py `
  --source-dir workspace/krea2-dora-numeric-20261025/source `
  --comfy-root <ComfyUI> `
  --output workspace/krea2-dora-numeric-20261025/numeric-ship.json
```

The output path must be new. Exit **2** preserves a completed diagnostic with
BF16 mismatch; exit **1** indicates full-precision mismatch or an execution/input
error; exit **0** is reserved for all tested dtypes meeting their tolerances.
The report always leaves production compatibility BLOCKED.

Next work is an execution-order-preserving inference candidate, rather than this
BF16 merge, plus actual alpha/weight mapping and quantized-base verification.
Matching the exact training environment remains a prerequisite for claims of
authored compatibility. Only after those gates pass should a separately budgeted
fixed-seed real-generation A/B be considered. There is no automatic retry,
fallback, 32px promotion, Golden/SOT change or review approval.

## Validation and rollback

Local ignored evidence lives in `workspace/krea2-dora-numeric-20261025/`:
version discovery/history, `version-interval.json`, pinned `source/` files and
manifest, complete numeric case reports, logs and final validation summary.
`numeric-ship.json` is the final 216-case result for the committed script; the
command returned the expected exit 2. Its eight rejection checks also completed.

Repository validation on this branch:

- Required editable `.[dev,motion]` installation and installed
  `assetpipe --help`: PASS; no new upstream/quantization dependencies installed.
- Source boundary tests plus the previous parser tests: **9 passed** (0.10s).
  They reject missing/tampered source before execution, exclude unselected
  top-level statements/imports and reject missing selected methods.
- Full offline regression: **680 passed, 1 skipped**, no failures, 247.48s.
  The skip is `test_direct_frames_are_identical_to_verified_legacy`, because local
  migration benchmark data is unavailable in this worktree. The previous branch's
  Windows atomic-replacement failure did not recur in this full run; no retry
  logic or shared manifest code was changed.
- `git diff --check`: PASS. Primary cleanup checkout remains clean.

Full-suite PASS refers only to the repository regression. It does not override
the independently measured BF16 mismatch or the production BLOCKED state.

The only implementation is the standalone research diagnostic; production
algorithms, workflow/configuration, CLI/MCP contracts and installed files remain
unchanged. Revert this commit to roll back; no runtime switch is needed.
