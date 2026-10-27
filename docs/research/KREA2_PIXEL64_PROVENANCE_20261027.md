# Pixel64 distribution and export provenance, 2026-10-27

Branch: `codex/pixel64-export-provenance-20261027`, base `a0e702b`.
**DISTRIBUTION_IDENTITY_CONFIRMED / COMPATIBILITY_STILL_BLOCKED**.
Machine-readable observations: [provenance record](KREA2_PIXEL64_PROVENANCE_20261027.json).
No production code/config, installed loader or weights changed.

## Distribution identity: resolved

The local `k2-pixel64.safetensors` has SHA-256
`53f1033700a866eaf6f56026cc352e26cd7d0563d4b32957dbbd3765b60d47bf`,
size **74,406,744 bytes**. It matches both:

- The publisher's [Hugging Face metadata](https://huggingface.co/api/models/e-n-v-y/Krea-2-Pixel-Art?blobs=true),
  revision `2fa8d14a24a62f5f3679326f782548c97039d9c2`, filename `k2-pixel64.safetensors`,
  exact LFS content hash and size.
- The [Civitai full-file hash lookup](https://civitai.com/api/v1/model-versions/by-hash/53f1033700a866eaf6f56026cc352e26cd7d0563d4b32957dbbd3765b60d47bf),
  model `2942217`, version `3331476`, file `3217724`, exact SHA-256 and byte size.

The initial lookup using the embedded `sshs_model_hash` value returned 404;
the full-file SHA lookup succeeded. These are different hash fields, not evidence
of a bad local download. The matching distribution bytes do not fix the parser.
No replacement/new model payload was downloaded.

The publisher's [pinned model card](https://huggingface.co/e-n-v-y/Krea-2-Pixel-Art/blob/2fa8d14a24a62f5f3679326f782548c97039d9c2/README.md)
declares Krea-2-Raw as base. The pinned current tree contains README,
`.gitattributes`, examples and the three resolution variants; no adapter config
or training YAML was present. Civitai's inspected trainingDetails is null. The
two inspected HF discussions address tile maps and a dataset, not alpha/export.
These bounded observations do not claim the author has never shared settings
elsewhere. Metadata still does not identify the exact training checkout, alpha
or authored base content hash. Rank does not establish those missing values.

## Published example is metadata, not our baseline

Seven publisher PNG examples were inspected for embedded workflow metadata;
no remote image was generated or used as project canon. The 64px example
[`images/ComfyUI_00150.png`](https://huggingface.co/e-n-v-y/Krea-2-Pixel-Art/blob/2fa8d14a24a62f5f3679326f782548c97039d9c2/images/ComfyUI_00150.png)
contains a 1024×1024 UI workflow with these selected widget values:

| Node | Observed metadata |
| --- | --- |
| UNETLoader 4 | `d/krea2_DasiwaKrea2TurboRaw_mirroredskiesV1Turbo_full_int8.safetensors` |
| LoraLoaderModelOnly 8 | `krea2/k2-pixel64.safetensors`, strength 1, mode 0 |
| Other LoRA node 25 | chibi filename/0.4 is present, but mode 4; not counted as active evidence |
| Refiner 137 | 64×64, 16 colors, palette-first and scale-to-original true |
| Core version metadata | 0.25.0, not an execution attestation |

Its `properties.models` download hints disagree with selected widget values:
the base hint points at Turbo FP8, and the pixel LoRA hint names warmpastel.
Therefore those hints must not be treated as actual checkpoint identity. No
checkpoint content hash or submitted API prompt/history accompanies this sample.
The graph was inspected as data and was not executed.

Our existing workflow selects `krea2_turbo_fp8_scaled.safetensors`; this sample
does not provide a controlled reference for that exact local base or prove full
magnitude application. Different filenames alone also do not prove mathematical
incompatibility. No Dasiwa model, extra LoRA, node or published workflow was
installed/adopted to imitate the example.

## Pinned official parser: actual isolated replay

Official ComfyUI source was pinned at
[`426f5eea52a7ece1dd599fff4cb6cd1f352ddd24`](https://github.com/Comfy-Org/ComfyUI/tree/426f5eea52a7ece1dd599fff4cb6cd1f352ddd24).
The reviewed `comfy/lora.py` SHA-256 is
`0934b66bda0f3a56475cb3a57b866948c4d92196dfca2cc8e001fbe96a3adbbc`.

Before execution, **10 dependency files** (adapter registry/classes/base and
converter) were checked byte-identical between that pinned source and the
installed ComfyUI. The reviewed `load_lora` and `bias_key` functions were then
AST-extracted unchanged into a temporary CPU namespace and run on the actual
adapter through the existing converter, diagnostic key map and summary helpers.
This reuses the parser; it does not rewrite it or patch the installed function.
The upstream GPL source/headers remain in ignored research evidence, without
copying parser implementation into production modules.

Actual result: **120 A/B patches, 240 consumed A/B keys, 120 unloaded magnitude
keys, INCOMPLETE_ADAPTER**. Input tensors, original file and installed source
hashes remained unchanged. This is stronger evidence than a string search for
`magnitude`, but its scope is still only the pinned parser with byte-identical
dependencies under the installed CPU runtime. The identity key map does not
validate base target application. No complete new ComfyUI installation, model
load, inference stack, GPU patching or image-quality test was performed.

Consequently a routine upgrade to the inspected parser is not demonstrated as
a fix. This does not claim that every third-party loader or future release is
incompatible, and no global upgrade/downgrade is proposed.

The [creator Refiner](https://github.com/envy-ai/ComfyUI-Krea2-Pixel-Art-Refiner/tree/0b01ea37f1573ca26a8511337e7d9d77759ee2c7)
is pinned at the same existing revision `0b01ea37f1573ca26a8511337e7d9d77759ee2c7`.
Its entrypoint registers six image postprocessing nodes; inspected entrypoint and
node sources do not supply a LoRA loader compatibility patch. They were not
installed/executed in this investigation.

## Validation, remaining gates and rollback

This change tracks only the report, observational JSON, README/CHANGELOG and a
follow-up link. Actual checks were public metadata HTTP retrieval, local full-file
hash/size equality, PNG workflow inspection and isolated parser execution. The
previous 778-pass/1-skip Python suite is historical and was not rerun or used as
evidence of model compatibility here. No production pipeline code changed.

Ignored `workspace/pp27/` retains pinned API responses and SHA-256 logs, source
files, seven PNG examples and extracted workflow data, source dependency checks,
`upstream-parser-replay.json`, warnings, verified observations and read-only
verification scripts. Local model weights were neither uploaded nor rewritten.
No author message, issue, PR or external comment was sent.

Remaining blockers are authored alpha/export semantics and exact base/training
provenance, followed by a format-specific full-target/quantized adapter check.
The conditional PEFT alpha/rank=1 research hypothesis is not promoted to fact.
Only after a justified candidate exists should a separately authorized image A/B
measure quality. Blind key renaming, guessing missing settings, copying sample
defaults or buying generation attempts does not close these gates. Existing
Pixel64 remains experimental; 32px, Golden/SOT and runtime activation stay closed.

Rollback: revert these documentation/observation changes. Keep the source and
diagnostic evidence. There is no installed code, checkpoint, config or active
pipeline change to reverse.

Follow-up: [isolated external loader candidate check](KREA2_LOADER_CANDIDATE_20261027.md)
retains all 120 magnitudes in the reviewed grouping/value path, but rejects
cross-strength/dtype equivalence with the pinned forward reference. It does not
resolve authored settings or approve a production loader.
