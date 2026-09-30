# Asset Pipeline

Asset Pipeline is a workflow-driven production toolkit that turns prompts,
reference images, and project design sources into validated game-ready visual
assets using ComfyUI, deterministic post-processing, and Aseprite.

The Python CLI, **`assetpipe`**, connects generation, quality gates, and export.
Generated images remain candidates, motion videos remain references, and pixel
exports require final review in Aseprite before use in a game.

## Current status

**v0.1 bootstrap verified:** 47 tests passed in the original Windows environment,
including real Aseprite round trips. The pixel animation smoke reproduced all
eight legacy frames with identical RGBA values. Real ComfyUI image generation
and a document-to-brief routing smoke also passed.

These are local validation results; external tools, models, and benchmark runs
are not bundled. See [acceptance evidence](docs/bootstrap_status.json).

| Output class | Available behavior |
| --- | --- |
| `PIXEL_STATIC` | Candidate generation, analysis, binary-alpha refinement, Pixel and Resolution Gates, then reviewed Aseprite export. |
| `PIXEL_ANIMATION` | Approved static master + existing reviewed motion, verified eight-frame character-local walk pixelization, palette projection, Pixel Gate, and Aseprite export. |
| `NONPIXEL_IMAGE` | ComfyUI generation, basic image QA, and output for visual review. |
| `NONPIXEL_ANIMATION` | Experimental pipeline contract; production execution is unavailable in v0.1. |

## Requirements

- Python **3.11 or newer**.
- ComfyUI running at the configured endpoint (default: `http://127.0.0.1:8188`).
- Models and custom nodes required by the selected workflow.
- Aseprite with CLI/Lua support for pixel mastering and export.
- FFmpeg on `PATH` for the verified direct animation path.

The registry describes the original validated installation. Check workflow model
names and nodes against your installation before generating. Model weights,
Aseprite, generated images/videos, and legacy benchmark data are not distributed.

## Quick start

### Install on Windows

```powershell
git clone https://github.com/prentice7725/asset-pipeline.git
cd asset-pipeline
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,motion]"
assetpipe --help
```

Without activation, use `.venv\Scripts\python.exe` and
`.venv\Scripts\assetpipe.exe` directly. External integration was verified on
Windows; other operating systems are unverified.

### Configure providers

Edit [config/pipeline.yaml](config/pipeline.yaml) for the ComfyUI URL and timeouts.
Set `aseprite.executable` or `ASEPRITE_PATH` for Aseprite; discovery also checks
`PATH` and common installation locations. Keep workflow graphs under
[config/workflows](config/workflows), separate from Python code.

### Generate a nonpixel image candidate

With the registered Anima Base model installed and ComfyUI running:

```powershell
assetpipe create --type nonpixel-image --asset-id scout --workflow anima_base --preset smoke --seed 101 --prompt "fantasy scout, short brown hair, blue cloak, light armor, dagger"
```

The command prints the run manifest path. Outputs and reports are retained under
`workspace/runs/<asset_id>/<run_id>/`. Review the image before using it in a game.

### Route a document-backed brief without generation

```powershell
assetpipe brief from-docs tests/fixtures/character_test.md --prepared examples/character_test_brief.yaml --output workspace/document_brief.json
assetpipe route --brief workspace/document_brief.json --output workspace/document_route.json
```

This document example is self-contained. Codex or a human reads project sources
and prepares the brief. `from-docs` validates that prepared brief and its source
paths; it does not automatically interpret documents or invent canonical traits.

Run commands from the repository root, or supply `assetpipe --root <repository>`
before the subcommand when working from another directory.

## Asset Brief and routing

All input passes through the [Asset Brief schema](schemas/asset_brief.schema.json).
The brief records asset ID/type, output class, purpose, sources, canonical and
visual traits, constraints, animation requirements, workflow preferences,
forbidden elements, unknowns, and source notes.

Document facts are classified as **EXPLICIT**, **DERIVED**, or **UNSPECIFIED**.
Unknowns never become canon automatically. Project documents remain the source
of truth; Asset Pipeline does not own project settings or resolve canon conflicts.

```powershell
assetpipe create --brief examples/character_test_brief.yaml
assetpipe brief schema --output schemas/asset_brief.schema.json
```

[config/workflow_registry.yaml](config/workflow_registry.yaml) declares output
classes, capabilities, tags, priority, status, workflow files, and model inventory.
The router checks output class and capabilities, then matching tags, status
eligibility, and priority. Compatible explicit workflow selection takes precedence.

| Status | Selection policy |
| --- | --- |
| `ACTIVE` | Eligible for automatic selection. |
| `VALIDATED` | Available when explicitly requested. |
| `EXPERIMENTAL` | Requires explicit workflow ID and `allow_experimental: true` in the brief. |
| `REJECTED` | Never executed. |

The registry includes Anima + Pixelate x4 VAE for static pixel candidates,
Anima Base and Krea2 Base for nonpixel images, and experimental Tomohi.
Unsupported reference input or capabilities cause an error rather than silently
being dropped. `route_decision.json` records reasons and fallback candidates.

## Pixel production

### Static assets

```text
Brief → Router → ComfyUI candidate → Analyzer → Safe Refiner
      → Pixel Gate → Resolution Gate → reviewed Aseprite master → export
```

```powershell
assetpipe create --type pixel-static --asset-id warrior --prompt "sword wielding fantasy warrior"
```

Automatic static refinement is limited to binary alpha. Failed gates lock
export; review-required states pause the run. Identity, clothing, equipment,
and silhouette semantics are never automatically redesigned.

For a run at `RESOLUTION_REVIEW_REQUIRED`, record a passing review with
`assetpipe.pixel.resolution.record_resolution_review`, including selected height,
reviewer, and reason. Export the hash-verified candidate with:

```powershell
assetpipe export-static --run workspace/runs/<asset_id>/<run_id> --resolution-review <review.json>
```

### Pixel animation

```text
Approved static master + existing reviewed motion
  → semantic frames → CHARACTER_LOCAL_DIRECT → exact master palette
  → Pixel Gate → Aseprite → sprite sheet
```

Supply a prepared brief with `production.static_master`, `approval_record`,
`motion_reference`, `selection`, and `direct_profile`. Approval must match the
static master SHA-256; reviewed semantic selections must identify the supplied
video. New motion generation is not automatically dispatched in v0.1.

The verified `blue_tunic_white_matte_v1` profile supports eight reviewed walk
phases with a blue-tunic character and white reference background. It retains
one shared-scale downsample followed by binary alpha and exact palette projection.
FFmpeg reproduces the legacy RGB conversion; OpenCV conversion changes pixels
and is not substituted in this path. This is not a universal anchoring algorithm.

[examples/pixel_animation_smoke.yaml](examples/pixel_animation_smoke.yaml) references
an adjacent legacy `pixel-pipeline` checkout. Its approved master and motion data
are not bundled; adapt paths to your approved inputs before running.

Aseprite verifies exact RGBA round trips, frame count, timing, tags, and metadata.
Exports remain `EXPORT_READY_REVIEW_REQUIRED` with `game_ready: false` until final
human review. Pixel Art Fixer remains optional recovery policy only; articulated
reconstruction and pose recreation are excluded from production defaults.

## Run records

Every create attempt writes `run_manifest.json`, including failures. Runs retain
routing decisions, workflow hashes/versions, models/LoRAs, seed, prompts,
resolution, ComfyUI prompt ID, pipeline steps, QA, outputs, and timestamps.
Intermediate files are preserved and existing run directories are never overwritten.
Manifests support reproduction and QA; they do not replace project canon.

Generated files and local publication backups under `workspace/` are Git-ignored.

## Development

```powershell
python -m pip install -e ".[dev,motion]"
python -m pytest
assetpipe --help
```

Real Aseprite tests skip when Aseprite is unavailable. Exact animation regression
skips when the local legacy benchmark is absent. Unit tests do not require a
running ComfyUI server.

```text
src/assetpipe/
  brief/ router/ registry/     # Input contract and workflow selection
  providers/                  # ComfyUI and Aseprite adapters
  pipelines/                  # Four output-class paths
  pixel/ motion/              # Pixel and motion interfaces
  manifests/ cli/             # Run records and CLI
  _ported/                    # Preserved verified implementations
config/                       # Provider settings and workflows
schemas/ examples/ tests/ docs/
```

[Migration inventory](docs/migration_inventory.json) records source hashes and
adaptations. Bootstrap scripts require the original adjacent legacy checkout and
local benchmark inputs. They are migration utilities, not installation steps;
do not rerun them over an active installation.

## Scope

v0.1 is a minimum workflow-driven CLI foundation. GUI, web UI, MCP server,
cloud deployment, database, model research, automatic art direction, and general
animation reconstruction are outside its scope. Further features require a
separate milestone.
