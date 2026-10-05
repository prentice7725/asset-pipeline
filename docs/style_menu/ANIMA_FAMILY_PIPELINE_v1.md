# Anima Family Pipeline v1

Status: EXPERIMENTAL / generation validation required.

This pipeline replaces hand-authored final Anima prompts with a model-aware path:

`PromptSpec + style semantics -> anima_hybrid compiler -> model profile defaults -> workflow preset -> local ComfyUI -> manifest/review`.

## Model family

- `anima_base`: legacy B1 workflow/profile retained unchanged for evidence reproducibility.
- `anima_base_rebuilt`: official-guidance Base baseline, explicit-only experimental.
  - Base checkpoint `anima-base-v1.0.safetensors`
  - shared `qwen_3_06b_base.safetensors` and `qwen_image_vae.safetensors`
  - official quality/negative defaults are supplied by `config/model_profiles.yaml`
  - R1 pilot preset: 512x768, 30 steps, CFG 4, er_sde/simple
- `anima_turbo`: new explicit-only experimental candidate.
  - expected checkpoint `anima-turbo-v1.1.safetensors`
  - same text encoder and VAE
  - R1 pilot preset: 512x768, 10 steps, CFG 1, euler/simple
  - no LoRA

Official source: https://huggingface.co/circlestone-labs/Anima

The model card recommends Anima-Turbo as a starting point and specifies CFG 1 at 8-12 steps. It also documents the common quality prefix, negative prompt, hybrid tag/caption prompting, and Base's 30-50 step CFG 4-5 range.

## No final prompt templates

`scripts/anima_family_pipeline.py` owns the controlled test fixture and builds the same PromptSpec for Base-rebuilt and Turbo. The `anima_hybrid` compiler formats it. The style menu contributes model-neutral style semantics, not a complete prompt string.

Subject mutation cues are removed from style semantics when they conflict with the synthetic fixture. In particular, STYLE-004's historical `small body` cue cannot alter the adult comparison fixture.

## Local commands

Offline contract:

```powershell
python scripts/anima_family_pipeline.py check
python scripts/anima_family_pipeline.py plan --output workspace/style_menu/anima_family_r2/plan.json
```

Before generation, place the official Turbo checkpoint under the configured ComfyUI `models/diffusion_models` directory if it is missing. Do not silently substitute another Turbo file, quantization or LoRA. Then hash all required files:

```powershell
python scripts/anima_family_pipeline.py check --models-root C:\path\to\ComfyUI\models --hash-models --output workspace/style_menu/anima_family_r2/preflight.json
```

Controlled R1 execution (four calls, zero retries):

```powershell
python scripts/anima_family_pipeline.py execute \
  --plan workspace/style_menu/anima_family_r1/plan.json \
  --models-root C:\path\to\ComfyUI\models \
  --output-dir workspace/style_menu/experiments/ANIMA_FAMILY_R2_20261005 \
  --authorization-note "User requested Turbo introduction, rebuilt baseline and re-experiment on 2026-10-05" \
  --confirm-generation
```

The runner blocks before dispatch if any checkpoint/text encoder/VAE is missing, writes a four-call reservation ledger, submits each job at most once, and records failures without retrying. Pixel generation, LoRA application and VAE changes are outside this cohort.

## R1 matrix

- STYLE-001 × `anima_base_rebuilt`
- STYLE-001 × `anima_turbo`
- STYLE-004 × `anima_base_rebuilt`
- STYLE-004 × `anima_turbo`

All cells use the same structured adult traveler fixture, seed 7725 and 512x768 comparison canvas. This is a baseline-family comparison, not a Golden approval. Results remain REVIEW_REQUIRED until the original PNGs and manifests are visually reviewed.


## R1 actual-output findings and R2 correction

R1 was executed locally from Git commit `267529838ab989c58868277f1a850fb963468eb4`. Four Anima-family cells completed at 512x768 / seed 7725 with no retries. All remain REVIEW_REQUIRED.

The actual comparison revealed two pipeline-level defects:

- the synthetic fixture forced a neutral environment while STYLE-001 required cyberpunk night/red/black treatment;
- the hybrid prompt repeated the exact-one compass requirement through subject, appearance, integrity and constraints, coinciding with a visible duplicate-compass failure in STYLE-004 Base.

R2 therefore changes the compiler/fixture rather than hand-editing four final prompts:

- `compiler_revision=anima_hybrid_v2`;
- appearance facts already present in the subject are omitted from the caption;
- structured equipment traits are omitted from appearance and emitted once through the equipment relationship contract;
- full-character integrity instructions do not repeat the entire subject sentence;
- exact-one equipment adds native-negative guards against duplicated required equipment;
- STYLE menu enum-like axis metadata does not reach Anima as model tokens;
- background/lighting are style-consistent instead of forcing a neutral environment;
- controlled equipment uses explicit `subject's anatomical left hand` and front view.

The next prepared cohort ID is `ANIMA_FAMILY_R2_20261005`. R1 artifacts remain historical evidence tied to the earlier commit and must not be re-labelled as R2.

R2 remains a four-call, no-retry comparison and needs a fresh reservation before execution.
