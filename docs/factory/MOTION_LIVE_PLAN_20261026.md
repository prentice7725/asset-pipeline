# Motion generation preparation — 2026-10-26

Follow-up: the user subsequently approved one request. The
[real-generation evidence](MOTION_REAL_E2E_20261026.md) records its newly rebound
plan, consumed budget, successful technical chain and remaining human review.
This page retains the earlier no-generation preparation snapshot and hash.

Branch: `codex/motion-live-plan-20261026`, base `3d974fa`.

**PLAN_PREPARED / GENERATION_BLOCKED / HUMAN_REVIEW_REQUIRED**.
This is an actual local installation and source-file check, not I2V E2E evidence.
No production source/configuration, six MCP contracts or legacy algorithm changes.

## Selected candidate and concrete plan

The reference is the existing M1 Codex-provider smoke output of a single fox scout
with a red scarf. Its original manifest is
`C:/workspace/asset-pipeline/workspace/m1_e2e/codex_imagegen/20261001T121258Z/run_manifest.json`.
The recorded output is
`010_generation/codex_cli/raw/01_exec-1491db27-70c8-4e24-82da-1474d2e3910b.png`
relative to that directory. The file was visually inspected: one full-body fox
with existing scout clothing/backpack. No crop, composition or redesign was made.
Another inspected candidate showed two views on one canvas and was not selected.

Selection is for planning a capability probe, not human art/Static Master approval.
The parent remains `CANDIDATE_READY_REVIEW_REQUIRED`, `game_ready=false`.
Its source Brief and output bytes are preserved unchanged. No new canonical traits
are inserted into the parent; the existing prompt is compiled unchanged, followed
by explicit motion instructions and existing preservation constraints.

| Item | Frozen value |
| --- | --- |
| Project / child asset | `default` / `m3_fox_motion_probe` |
| Workflow | `nonpixel_motion_contract`, EXPERIMENTAL |
| Reference count / role | 1 / `IDENTITY_PRIMARY` |
| Reference SHA-256 | `fcaaa5f36bb11c4f27d670d729a52d4771f67e08f5b2a94f3907bbfec2d2417d` |
| Parent manifest SHA-256 | `a8badb358fe66a9e05fa879f590d3c95f524573b00f595d11ef4966b2dae3117` |
| Width / height / seed | 512 / 512 / 7725 |
| Frames / FPS / duration | 56 / 24 / 56÷24 seconds (~2.333) |
| Action | Walk in place, fixed camera, entire single fox visible; preserve identity, clothing, equipment, colors and silhouette; no redesign or added equipment |
| Background | `PRESERVE_OR_REVIEW`; no alpha-removal claim |
| Workflow SHA-256 | `93993033246c7fef3ba19117f7a219950ec7fd3f062cff69ba684ae6b2e9ab26` |
| Execution plan SHA-256 | `8596907aad8fd9a0a43c565a2357ea21dc232c93c792c80559228520c7d45707` |

56 = 17×3+5 meets this adapter's frame rule. The 8-column, 7-row 512px
atlas would contain 14,680,064 pixels, below the existing 32M limit.
This timing is a small capability probe; it does not establish a complete walk
cycle, loop quality or adequate animation sampling.

## Current local checks

The Comfy connector's `server_info` returned a tool error. The existing Python
Comfy client then reached configured loopback `http://127.0.0.1:8188` using GET
only. No server start/restart, node installation, memory unload or queue operation.

- Actual `/system_stats`: ComfyUI **0.42.4**, Python **3.13.12**, PyTorch
  **2.12.1+cu130**, local Desktop deployment.
- **15/15 required node classes** returned individual live schemas.
- **5/5 required model filenames** are listed by the live server.
- The exact 512×512/56-frame graph template passed existing `_validate_graph`,
  including selected VHS codec options. This is local schema validation; no
  `/prompt` submission or server execution/weight loading was performed.
- Existing prepare/inspect/execution-plan functions ran against the real parent.
  The installed CLI's `motion-execution-plan` output exactly equals the Python API
  plan, including its digest. Source hashes and plan stability were rechecked.
- Evidence collection made **20 GET requests**; uploads, queue submissions and
  budget reservations were **0**. FFmpeg and FFprobe `-version` both executed
  successfully: `N-124387-gaa14727cd5-20260504`. No video was decoded in this task.

The initial source-root check correctly rejected a historical `source_path` in
the parent manifest outside its selected run directory. The final read policy
adds only the historical origin directory
`C:/Users/seung/.codex/generated_images/01a0f761-d7d8-7a20-9da1-8df901428fea`,
alongside the configuration root and selected parent directory. No path check
was removed, no parent manifest was rewritten and no operational root changed.
The initial denial log is retained separately.

Installed `deno_minimax_h3_reference.py` declares max 9 images, retains their order,
and maps the bundle to `ref_image_0`, `ref_image_1`, etc. Source SHA-256:
`da47f6e6e1501836d72ac01d2f473e179d77a08ec03bee5c7f16f5ede350b940`.
Its upstream `comfy_extras/nodes_minimax_h3.py` SHA-256:
`108ceff11e5a5c9a34a57bbc380447cf9941beb673a1bd421abc818de54ccd5c`.
This is source-level cardinality evidence only. Our research executor still
accepts exactly one reference. Actual role/identity/style conditioning, including
any model-specific picture-tag behavior, remains **NOT_VERIFIED**. Do not infer
2/3-reference E2E support or semantic consumption from the loader's limit.

## Local weight content

The five graph-declared files are hashed from the existing shared model directory;
no tensor/model allocation or file modification. Per-file size/mtime must remain
unchanged while hashing. Detailed paths, SHA-256 and stat records are preserved
in `workspace/motion-live-plan-20261026/model-hashes.json`.
Total checked bytes: **43,843,036,151**.

| Model file | Current local SHA-256 |
| --- | --- |
| `diffusion_models/minimax_h3_ref2va_pruned_int8_convrot.safetensors` | `9255f52b6677845ad238f20dfaafa94727053694127ab7f255c048f0f9365779` |
| `text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` | `35a88d51044231fe332301d7a62aa81e3f2cba62febeb446e2c1e3e0ef76f2c6` |
| `vae/minimax_h3_video_vae_fp16.safetensors` | `7c1f131492e7eddacaac9069a61b81bdd39de5cc96561e677c5eab1cdce5e522` |
| `vae/minimax_h3_audio_vae_fp32.safetensors` | `8e505d95dd1561d47abd43d4238fd40d9bb1ae9e147ed0a4cba778d76ae4db48` |
| `loras/MiniMax-H3-Ref2VA-Acc-8Step.safetensors` | `111c82e669f6e20e628228172edf39395f1a9fc3ad049793895e542c0f55b18c` |

These bind local disk bytes, not the server's in-memory model or authored quality.
The live preflight's `MODEL_CONTENT_HASHES_NOT_VERIFIED` gate is intentionally not
rewritten: it reports filename inventory, independently of this local evidence.

## Evidence and next authorization boundary

Ignored run artifacts are under the worktree's
`workspace/motion-live-plan-20261026/`:
`prepare_readonly.py`, `request.json`, `prepared/prepared_motion.json`, copied
reference, `live-preflight.json`, `execution-plan.json`, `cli-plan.json`,
`model-hashes.json`, installed source hashes, failure/final logs and `result.json`.
The evidence script rejects all non-GET or payload-bearing Comfy client requests.
It never calls `execute_prepared` or creates a generation authorization.

Pipeline code has not changed. The existing full regression at base `3d974fa`
was **720 passed / 1 skipped**; it was not rerun or relabeled as a new test result
for this documentation/evidence task. Current checks above are real CLI, source,
GET schema and local file-hash checks, not synthetic generation evidence.

Before one real request, the operator must approve the selected candidate,
exact one-request budget and research configuration/model-root changes. Current
`video_research.enabled` stays false and `model_roots` stays empty. **Enabling or
changing that configuration invalidates the frozen preparation/plan**: prepare
a new directory, rerun hashes/live validation and approve its newly bound plan
digest before creating a genuine one-request authorization. This report's hash
must not be reused after config/source/compiler/workflow drift. No consent or
human review attribution is fabricated here.

Real provider reference consumption, original video preservation, decoding,
alignment, sprites, loop/pivot/identity review, Aseprite approval and engine import
remain to be exercised on the actual generation. Normal Factory motion dispatch
remains blocked. Static image/SFX defaults, Golden/SOT and live MCP are unchanged.

Rollback: revert this documentation commit; no runtime migration is required.
Retain evidence files and original source candidates. No budget was reserved and
no generated video exists to undo.
