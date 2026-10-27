# One-reference motion research — real E2E evidence, 2026-10-26

Follow-up: [the advisory motion review](MOTION_ADVISORY_REVIEW_20261026.md) records
all-frame inspection, the loop seam, top-border contacts and pivot limits.
No asset correction or human approval was performed by that review.

Branch: `codex/motion-one-request-20261026`, base `1b984cb`.

**REAL_E2E_PASS — single-reference research technical chain only.**
Asset status: **CANDIDATE_REVIEW_REQUIRED**, `game_ready=false`.
Normal Factory motion dispatch and production activation remain blocked.

## Authorization and one-request scope

After reviewing the [concrete preparation](MOTION_LIVE_PLAN_20261026.md), the user
explicitly answered `승인` to one local ComfyUI generation using the selected fox
reference, 512×512, 56 frames at 24fps, followed by existing sprite/review packaging,
with research-setting enablement and no retry. That consent is recorded as user
consent in this Codex chat, not Aseprite/art approval or a signed identity proof.

The worktree's existing research setting was temporarily enabled with the actual
shared model root. The request was prepared in a new directory and a new plan hash
bound after that approved setting change. The workflow, reference, seed, dimensions,
timing and requested action match the reviewed preparation. The source Brief was
not rewritten. The authorization records the real user consent and exactly one
request; no human visual-review record was generated.

| Evidence | Value |
| --- | --- |
| Authorization / durable reservation ID | `2c301ac05cce430495f2be6f9448a246` |
| Executed plan SHA-256 | `3e370e340f28aa5b96ee9e6bb9dd3c3c989a1fc5db30b3b81535e11d51800c76` |
| Reference SHA-256 | `fcaaa5f36bb11c4f27d670d729a52d4771f67e08f5b2a94f3907bbfec2d2417d` |
| Workflow SHA-256 | `93993033246c7fef3ba19117f7a219950ec7fd3f062cff69ba684ae6b2e9ab26` |
| Server prompt ID | `de264d36-a8ad-4e26-ad36-8d1e958df782` |
| Parameters | seed 7725; 512×512; 56 frames; 24fps |
| Uploads / generation submissions / reservations | **1 / 1 / 1** |
| Retries / fallback | **0 / 0** |
| Server execution elapsed | **101.879 s** from history start/success timestamps |
| Receipt interval | 2026-10-26 21:36:07–21:37:57 JST (110.397 s) |

Before submission, the existing executor rehashed all five local model files
against the frozen hashes and rechecked live node/model schemas. The server's
existing extra-model-paths configuration points to the same shared root. No
models or nodes were downloaded/installed and no server restart or memory-unload
operation was issued. The queue was empty before this attempt.

The existing root-scoped budget ledger reserved the ID before upload. An additional
dated orchestration guard limited POST operations to one `/upload/image` and one
`/prompt`; there is no execution retry loop. This adds no production code or
alternative generation path. Existing compiler, provenance, model checks,
Comfy client, executor and motion package implementations performed the work.

## Actual chain and output verification

The server returned a successful completed history with output node `144`.
The history graph exactly equals the submitted graph, and its reference-loader
input equals the confirmed uploaded image name. The exact preserved reference
bytes were uploaded. A subsequent GET of that server input file returned the
same reference SHA-256, independently confirming upload byte preservation.
This proves recorded input/graph binding for this request;
reference-role semantics or conditioning effectiveness are not promoted to PASS.

The existing package preserved the original video, decoded it, ran the reused
motion extraction/alignment code and packed all frames into the atlas. Its QA
reports frame order preserved and dimensions passed.

| Output/check | Actual result |
| --- | --- |
| Original MP4 | 512×512; 24fps; 56 decoded frames; ~2.333333 seconds |
| Original video SHA-256 | `2b705e1330dfcf5259541142dc18044f3d4832b6e7d42e83b089e09dcf34fd4d` |
| Sprite atlas | 4096×3584, 8 columns × 7 rows, 56 cells of 512×512 |
| Sprite PNG SHA-256 | `3252a8ccdd03ffb3a4ea336f4ee3eff7662bea8f899e99b05717fb6fe0afe4a1` |
| Atlas JSON SHA-256 | `29edfc502aa29944e607e1e7f2a81c8dd9c2b54ab796b9ee581dbf7365f7b479` |
| Package manifest SHA-256 | `2d04004918ebc7df1a62c5c477b2c1330d8e35438d8668e06ba59f9767349440` |
| Raw source indices / timing | 1..56 in order; index/24 timestamps; 1000/24 ms per frame |
| Output/56 raw/56 aligned hashes | Recomputed and matched recorded hashes |
| Atlas cells | All 56 exactly match their aligned frame pixels |
| Alpha | All aligned pixels alpha 255; **opaque**, no transparency claim |
| Pivot | Existing `CANVAS_BOTTOM_CENTER_REVIEW_REQUIRED`; quality not approved |
| Review template | `REVIEW_REQUIRED`, reviewer null, all human checks null |

The package's own `generation_status=NOT_RUN` describes the decoding/packing stage;
actual generation provenance is in its parent `motion_execution.json`, server
history and submitted graph. Do not read the package-local field as no generation
having occurred in the parent research run.

## Advisory visual observation and remaining gates

A contact sheet compares the original reference with raw frames 0, 7, 14, 21, 28,
35, 42, 49 and 55. In those samples, the orange fox, red scarf, scout clothing and
backpack look consistent and alternating leg motion is visible. This is an agent's
advisory observation, not a human identity approval, numeric quality score or an
ablation proving reference conditioning. Full-speed motion/loop/pivot quality and
manual correction effort have not been approved or measured.

The start is a standing pose and the last sample is mid-step; a seamless loop is
not established. The video remains on a light opaque background. Alpha processing,
required Aseprite review, Godot/Phaser import, gameplay readability, Golden/SOT
approval, 2/3-reference generation and PIXEL64 motion remain **NOT_RUN/NOT_VERIFIED**.
No default Factory dispatch, provider promotion or general production readiness
is inferred from this one successful research chain. Normal still-image and SFX
paths remain unchanged.

## Artifacts, software checks and rollback

Run directory relative to the independent worktree:
`workspace/factory_budget/2c301ac05cce430495f2be6f9448a246/`.
It retains `motion_execution.json`, `submitted_graph.json`, `history.json`, compiled
prompt, `original.mp4` and `package/` with original copy, decoded/raw/aligned frames,
sprite PNG, atlas JSON, motion report and untouched review template.

`workspace/motion-one-request-20261026/attempt/` retains original/enabled config
snapshots, original-source hashes, recorded actual consent, authorization JSON,
new request/preparation/plan, HTTP POST counts, system/queue observations,
contact sheet, `output-verification.json` and `upload-byte-verification.json`.
The dated wrapper and verification
scripts/logs are in its parent. These are ignored local run artifacts, not source
modules; do not delete them as part of rollback or release cleanup.

The real output verification ran successfully and preserves review state. Runtime
code is unchanged; the prior full offline suite at `3d974fa` was **720 passed /
1 skipped** and was not rerun or counted as new generation evidence here. No new
software-test PASS is inferred from the real video result.

After the attempt, `config/pipeline.yaml` was restored **byte-for-byte** to its
original `enabled: false`, empty model-roots state. Original parent manifest and
image hashes match before/after. Git has no runtime/configuration diff. This
deliberate restoration invalidates prepared-plan reuse: do not try to resume or
replay the consumed authorization. A further generation needs a new explicit
budget, current preparation/hash checks and a new ID; none is authorized here.

Changed tracked files: this report, README, CHANGELOG and a dated follow-up link
in the earlier preparation report. Rollback: revert this documentation commit.
Keep the consumed reservation, consent, originals, intermediates and reports.
Golden/SOT, six MCP tools, production defaults and live runtime pointers were not
changed; no model/node installation needs reversing.
