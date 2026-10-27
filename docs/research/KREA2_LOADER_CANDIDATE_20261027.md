# Pixel64 loader candidate check, 2026-10-27

Branch: `codex/pixel64-loader-candidate-20261027`, base `fa44d8c`.
**KEY_RETENTION_CONFIRMED / NUMERIC_EQUIVALENCE_REJECTED**.
Observations and all 54 numeric cases: [JSON record](KREA2_LOADER_CANDIDATE_20261027.json).
This is an isolated compatibility investigation, not a provider installation.

## Candidate and actual scope

InvokeAI's merged [Krea2 DoRA fix, PR 9517](https://github.com/invoke-ai/InvokeAI/pull/9517)
explicitly distinguishes ai-toolkit output-axis `.magnitude` from `.dora_scale`.
The inspected revision is its merge commit
`2fc8f48c066377937914d7040881973f93f6627b`, not a claim about all InvokeAI versions.
The Apache-2.0 source and license were retained under ignored
`workspace/loader-candidate-20261027/`; no external implementation was copied
into production. Public source responses and local script hashes are recorded.

The unchanged local LoRA is SHA-256
`53f1033700a866eaf6f56026cc352e26cd7d0563d4b32957dbbd3765b60d47bf`.
Actual execution of the reviewed `_group_by_layer` and `_get_lora_layer_values`
functions groups its 360 tensors into 120 triples. Every triple retains its
original A/B/magnitude tensor references; magnitude length equals the B output
dimension in all 120. No alpha override is supplied or inferred. These functions
do not establish successful DoRALayer construction, native-to-Diffusers target
mapping, quantized patching or full-model inference. The full converter and
InvokeAI installation were not executed.

## Numeric comparison exposes a remaining mismatch

The unchanged candidate `DoRALayer.get_weight` and `get_parameters` methods
were AST-extracted and invoked against temporary dense CPU tensors. A minimal
object supplies only the explicit A/B/magnitude, alpha/rank scale and no-bias
methods. Device casting uses `tensor.to(device)` on the same CPU device; this
does not test InvokeAI's autocast helper or its runtime patch application.

The reference reuses the existing hash-pinned ai-toolkit 0.12.9 method extraction
and `make_module` fixture from `scripts/krea2_dora_numeric_probe.py`. It is the
previously inspected source candidate, not a verified author's training checkout.
No candidate arithmetic or source reference was rewritten for this test.

Actual CPU run: torch `2.12.1+cu130`, shapes `(out,in,rank)` `(5,3,2)`, `(3,5,2)`,
`(4,4,2)`, seed 7725, 2D input, no bias; FP64, FP32 and BF16; explicit research
alpha/rank hypotheses 1 and 0.5; strengths 0, 0.5 and 1. All original tensors,
adapter bytes and reviewed source files remained unchanged.

| Condition | Within tolerance | Largest absolute output difference |
| --- | --- | --- |
| Strength 0, all dtypes/ratios | 18/18 | 0 |
| FP64, ratio 1, strength 1 | 3/3 | 3.56e-15 |
| FP32, ratio 1, strength 1 | 3/3 | 4.77e-7 |
| BF16, ratio 1, strength 1 | 0/3 | 0.03125 |
| Strength 0.5, all dtypes/ratios | 0/18 | 1.125 |
| Ratio 0.5, strength 1, all dtypes | 0/9 | 0.0625 |

Totals: 54 executed cases, 24 within tolerance, 30 different. All outputs are
finite. FP64 uses atol=rtol=1e-10; FP32/BF16 uses 1e-5 to diagnose forward
equivalence, not an art-quality threshold. BF16 differences alone do not show a
visible quality regression.

The candidate computes a normalized full-strength weight delta and multiplies
that delta by the requested strength afterward. The pinned ai-toolkit reference
uses the multiplier inside its adapted-direction/norm computation. Consequently
the same numeric strength does not promise the same inference semantics. The
alpha placement also differs for the tested nonunit ratio. This is a rejection
of interchangeability with this reference across the tested contract, not a
general defect declaration against InvokeAI. The upstream full-strength example
and our restricted FP32 full-strength agreement remain valid within their scope.

## Second candidate: source inspection only

[RunComfy ai-toolkit-inference](https://github.com/runcomfy-com/ai-toolkit-inference/tree/af4aec18dcd05e89abc2fcdefebeed8b5a35da70)
was pinned at `af4aec18dcd05e89abc2fcdefebeed8b5a35da70` (MIT license inspected).
In `src/pipelines/krea2.py`, `_merge_lora_to_transformer` keeps raw tensor names
but its A/B branch only performs `W += scale * (B @ A)`; it does not consume
`.magnitude` in that path. Thus that inspected path supplies no fix for our
adapter's missing DoRA magnitude. This is static source evidence only: neither
its package nor its models were installed or executed. No assertion is made
about its other architectures, future versions or ordinary LoRA support.

## Result, remaining gates and rollback

Do not install either candidate as a production replacement. The existing
Pixel64 path remains experimental and adapter compatibility **BLOCKED**.
Authored alpha, exact training implementation and base provenance remain open
from the [distribution investigation](KREA2_PIXEL64_PROVENANCE_20261027.md).
This run gives no image-quality improvement measurement and consumes zero
generation requests. No weights, installed loaders, defaults, approval states,
Golden/SOT, production source or six MCP contracts changed.

Current checks were source/hash validation, actual 120-group tensor retention,
54 isolated numeric cases and unchanged-input checks. The production regression
suite was not rerun for this documentation-only change; its historical results
are not evidence of candidate compatibility. `git diff --check` is also required.

Reproduction evidence remains in ignored `workspace/loader-candidate-20261027/`:
`fetch.py`, source/PR responses and licenses, `sources.json`, `probe.py` and
`probe-result.json`. Run the reviewed probe with the installed ComfyUI Python;
it creates its result exclusively and refuses to overwrite prior evidence.
No source bytecode writes or installed-loader patches are used. Rollback is a
revert of this report/observation and the README/CHANGELOG links.

The next useful Pixel64 work is an optional postprocessing A/B on existing
images, independently labeled as incomplete-LoRA baseline. Repeating source
searches or changing strength defaults cannot close the authored-loader gate.
