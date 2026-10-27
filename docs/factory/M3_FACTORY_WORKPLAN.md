# M3 Factory Workplan — four lines with optional sprite production

> 2026-10-27 사용자 우선순위 변경: **넌픽셀 정지 이미지·애니메이션 우선,
> 픽셀 경로는 연구과제**. 현재 개발 순서와 검증 경계는
> [넌픽셀 생산 계획](NONPIXEL_PRODUCTION_PLAN_20261027.md)을 따른다.
> 아래 날짜·baseline·미구현 표는 2026-10-11의 역사적 계획이며 현재 상태 판정이 아니다.

**Plan state:** READY_FOR_REVIEW / NOT_EXECUTED
**Date:** 2026-10-11 (Asia/Tokyo)
**Baseline:** main abd7fe246b36be3d79a8ea1ed9d7a022339f16d0
**Product decision:** A NONPIXEL, B REFERENCE_MOTION(1..3), C SFX, D PIXEL64. In A/D both IMAGE_ONLY and opt-in IMAGE_TO_SPRITE are terminal choices; 32px remains ON_HOLD_RESEARCH.
**Authority:** This plan implements the user-specified factory shape. It is not runtime activation, a generation authorization, or a project SOT change.

## 0. Current reality and gap

| Capability | Existing implementation/evidence | Gap to target |
| --- | --- | --- |
| SOT-derived Brief + model routing | src/assetpipe/brief, router, PromptSpec, STYLE-101..124 | explicit factory line/output mode; project-scoped terminal criteria |
| NONPIXEL still image | pipelines/nonpixel_image, ComfyUI real QA; Codex/Grok provider proof at historical M2 | independent terminal IMAGE_ONLY contract / later continuation in unified factory |
| Static pixel pipeline | pixel_static + Pixel Gate + resolution review + Aseprite | 64px registered research candidate promotion gate, not an automatic 32px/legacy replacement |
| Pixel64 experiment | docs/research/KREA2_PIXEL64_SMOKE_20261003.md: two native 64px Pixel Gate PASS, Aseprite roundtrip PASS, human approval absent | integrate proven recipe/refiner with explicit EXPERIMENTAL gate; generalize only after evidence |
| Existing animation | pixel_animation supports one reviewed blue-tunic walk path; _ported motion extraction present | generalized I2V, frame sequencing, character tracking, spritesheet export E2E |
| NONPIXEL_ANIMATION | pipelines/nonpixel_animation.run raises experimental-unavailable | implement behind controlled capability gates |
| Multi-reference B | Source refs exist in Brief; no counted/role-based 1..3 I2V contract | new role-aware import and provider-specific input conditioning |
| SFX | pipelines/sfx, FLAC+WAV, audio QA and CLI/MCP real smoke | listening review acceptance, factory naming/presets and operational smoke matrix |
| Host integration | six MCP tools, local plugin and security tests | compatible factory exposure, pinned-runtime release gates and live validation |

Baseline note: README/docs show historical pass counts from different milestones; no single old pytest number is a current release verdict. On each PR run and record a fresh suite, exact environment, skips, expected external dependency coverage and reasons.

## 1. Delivery strategy and PR boundaries

- Deliver as **small reviewable PRs**, not one large refactor. Reuse existing core; avoid duplicate prompt compilers, generic video algorithms, and new UI/cloud/DB features.
- Every phase supplies **contract → offline tests → local integration → real smoke if authorized → human review**. Tests never fabricate art/audio approval.
- No workflow/model installation, external paid generation, permanent SOT change, Golden approval, provider ACTIVE promotion or live MCP runtime pointer switch is implicit in a code merge.
- Keep the six MCP schemas unchanged in the first iteration; adapt internal capabilities behind existing tools or create a separately reviewed versioned change when unavoidable.
- Treat external video generator support as **unknown until checked**. Never claim 2/3-image support from a one-image I2V smoke.
- Never overwrite approved stills or delete old runs; child motion outputs get distinct run IDs and provenance.

## 2. Milestones, order and acceptance gates

### M3.0 — Factory contract and compatibility (P0)

**Depends on:** existing main; security runtime approval tracked separately.

Implementation:
1. Add versioned factory request validator, line/output-mode matrix and compatibility mapping to existing Asset Brief/output_class.
2. Define source kind GENERATE / EXISTING_RUN / EXTERNAL_IMAGES and independent image/motion run relationship.
3. Separate image-only completion from video continuation. IMAGE_ONLY must not preflight video backend or reserve video budget.
4. Preserve legacy PIXEL_ANIMATION walk and legacy NONPIXEL_ANIMATION unavailable behavior when factory envelope is absent.
5. Provide plan/dry-run/inspect presentation using current CLI/API structure. No silent route or model changes.

**Likely files:** new src/assetpipe/factory/{contracts,planner,provenance} modules; schemas/factory_request_v1.schema.json; src/assetpipe/brief, router, api and CLI narrow adapters; tests/unit/test_factory_contract.py and compatibility fixtures. Location is proposed, not an assertion that files exist.

**Acceptance:**
- Valid A IMAGE_ONLY, A IMAGE_TO_SPRITE, B IMAGE_TO_SPRITE (1/2/3 inputs), C AUDIO_ONLY, D IMAGE_ONLY, D IMAGE_TO_SPRITE route to correct **plans** without dispatch.
- Wrong combinations, >3/zero B sources, missing image roles, invalid path or unsupported modes fail closed **before** any paid call.
- Existing Brief/CLI and six MCP schemas unchanged; old motion fixtures bit-for-bit retained.
- IMAGE_ONLY dry run shows exactly **zero** video tasks/allocations/budget reservations.
- Evidence: schema validation matrix + full Python tests + CLI help + MCP exact schema diff.

### M3.1 — C SFX operational closure (P0, fastest completed line)

**Depends on:** M3.0 contract; may develop in parallel with M3.2.

Implementation:
1. Wrap existing Stable Audio 3 Medium generation in C/AUDIO_ONLY mode, without a new provider or a second prompt compiler.
2. Add category and naming metadata, durable clip receipt, sample/format verification, and listening review checklist. Do not change source sample encoding casually.
3. Audit project-scoped output isolation and no-music/no-voice advisory limits.

**Likely files:** pipelines/sfx, examples/sfx_*.yaml, docs/SFX.md, test_sfx, small metadata validator.

**Acceptance:** offline validation for short impact, UI cue and ambience contracts; real generation smoke for representative examples **only with explicit generation budget**; FLAC/WAV, SHA, duration, RMS/peak, manifest and review package correct. Human listens and records pass/hold; automated QA alone remains REVIEW_REQUIRED. No I2V calls.

### M3.2 — Shared video → frames → sprite backbone (P0, prerequisite for A/B/D motion)

**Depends on:** M3.0.

Implementation:
1. Read-only local ComfyUI inventory for installed video models, workflows/nodes, I2V conditioning input count, output video format, dimensions, duration and cost. Produce an evidence-based capability matrix.
2. Register only verified video workflows with explicit count/role support and EXPERIMENTAL or validated status; no assumption that Minimax reference workflow covers all inputs/subjects.
3. Implement motion preflight, generation adapter, original-video preservation, source-hash/frame provenance, FFmpeg decoding and frame selection interfaces.
4. Implement alignment, alpha/background policy, frame atlas or per-frame export, pivot/time metadata and technical sprite QA.
5. Ensure motion dispatch is child of an immutable still/reference source; no retroactive state overwrite. No auto retries, provider switching or unbounded polling.

**Likely files:** new src/assetpipe/providers/video and pipelines/shared_motion; existing motion/extractor/alignment/keyframes/temporal, manifests, config/workflow_registry.yaml, tests/unit and integration fixtures.

**Acceptance:**
- One authorized real I2V example yields original video, verified source hashes, ordered frames, sprite sheet and atlas/metadata plus manifests. If actual video capability unavailable, mark **BLOCKED_BACKEND_NOT_VERIFIED**, not PASS.
- Offline tests include zero-length/corrupt video, missing frames, size changes, discontinuity, invalid background removal, failed video dispatch, unsupported codec and stale source.
- A forced child motion failure leaves an existing IMAGE_ONLY result untouched and still inspectable.
- Distinguish technical image/sprite QA from human motion-quality and game-readability review.

### M3.3 — A NONPIXEL image-only + optional motion E2E (P1)

**Depends on:** M3.0 and M3.2. IMAGE_ONLY subset may ship before M3.2.

Implementation:
1. Reuse existing STYLE MENU v1 + provider/PromptSpec + nonpixel_image path.
2. Expose **IMAGE_ONLY** as a first-class end state; produce usable image candidate package and no video task.
3. Add explicit continue-from-existing-run motion path; source identity, reference hash, style and project SOT contract remain bound.
4. Allow user-authorized exploratory motion from a nonapproved candidate only as RESEARCH / REVIEW_REQUIRED, not production-ready.

**Acceptance:**
- A1: one real nonpixel IMAGE_ONLY run reaches review package without any video engine invocation.
- A2: a separately authorized motion continuation references the **same** still-image hash and yields video, frames and sprite sheet.
- A3: invalid/failed motion child leaves A1 unchanged; optional re-inspection can resume without re-generating still.
- At least two subject roles (character and non-character/background) exercise IMAGE_ONLY; do not assert every still is animatable.

### M3.4 — B reference-based 1/2/3-image motion E2E (P1)

**Depends on:** M3.2.

Implementation:
1. External image ingestion with count=1,2,3; validate format, path root, SHA, provenance/license declaration, role and ordering.
2. Model adapter maps declared roles to actual **provider-supported** inputs. If role-count not supported, block before paid dispatch.
3. Explicitly distinguish IDENTITY_PRIMARY, ALTERNATE_VIEW, POSE_ANCHOR, START_FRAME, END_FRAME, STYLE_REFERENCE. Do not infer poses, transitions or story from the number of files.
4. Run through the shared motion backbone and preserve per-input hashes and conditioning metadata.

**Acceptance:**
- Three independent real E2E validation cells: **1**, **2**, **3** reference images. Each must show that all requested images were actually consumed by the video workflow, and output video + sprites are produced and reviewed.
- If no true 3-input provider exists, B3 remains **BLOCKED_UNSUPPORTED**; no silent composition, dropped references or false green completion.
- Invalid path/symlink/junction, duplicate/ref-role conflict, changed source, wrong file count, and unsupported provider cases tested before model use.

### M3.5 — D PIXEL64 static + optional motion E2E (P1)

**Depends on:** M3.0; motion subset also depends on M3.2. Research candidate does not imply approval.

Implementation:
1. Use 2026-10-03 Krea2 Pixel64 experiment as reproducible initial candidate, verify local LoRA/refiner compatibility including unused magnitude tensors. Do **not** silently convert or patch weights.
2. Define **64x64 logical output**, palette/cluster/silhouette/alpha and Aseprite roundtrip gates. Register experiment as explicit-only until full validation and human review.
3. For D IMAGE_ONLY, stop at reviewed static candidate/master; do not require video tooling.
4. For D IMAGE_TO_SPRITE, route approved/explicit research still to shared I2V, then recover to 64x64 with explicit palette/identity contract for **every** frame; temporal consistency, jitter, color drift and Aseprite sprite export receive dedicated QA.

**Acceptance:**
- D1: representative 64x64 static candidate passes intended technical gates and human static review before approved-master status.
- D2: source hash -> video -> frames -> 64px sprite sheet; all target frames satisfy actual pixel gate and approved palette or remain blocked/review-required.
- D3: pixel frame temporal/identity QA and actual sprite preview/in-game review evidence recorded; no universal 64px success claimed from two historical smoke images.
- No 32px candidate is quietly rerouted to 64px without an explicit request/contract change.

### M3.6 — Release, project integration, evidence and operations (P1)

**Depends on:** independently passing terminal modes for each claimed ready line; security approval separate.

Implementation:
1. Publish a machine-readable factory capability/status matrix with NOT_IMPLEMENTED, OFFLINE_PASS, REAL_E2E_REVIEW_REQUIRED, HUMAN_APPROVED and READY_FOR_GAME states; prevent misleading parent status inheritance.
2. Run an actual project SOT -> Brief -> factory plan -> requested terminal output trial and verify source-first style/identity/cost constraints.
3. Update README, Korean operating examples, existing plugin/MCP instructions and production support matrix; preserve historical evidence without overwriting it.
4. Validate pinned-runtime rollout separately: provenance hash, candidate build, security/path checks, exact six tools, live process quiescence, backup, install smoke, rollback and user approval.

**Acceptance:** each line/mode has a named real evidence ID or explicit BLOCKED reason, original output hashes, test result, human-review status and operational owner. No production-ready label based on synthetic tests.

## 3. Explicit PR sequence

| PR group | Scope | Safe parallelism | Merge gate |
| --- | --- | --- | --- |
| M3-01 | factory request/schema/planner with backward-compatible default | first | offline + legacy parity |
| M3-02 | C SFX close-out | after M3-01, parallel to M3-03 | audio QA + listening-review evidence |
| M3-03 | shared motion adapter/extract/export | after M3-01 | verified video provider + one real end-to-end trial |
| M3-04 | A IMAGE_ONLY and continuation | after M3-01, motion part after M3-03 | child isolation + two end modes |
| M3-05 | B 1/2/3 reference ingest/conditioning | after M3-03 | 1/2/3 actual consumption proof |
| M3-06 | D PIXEL64 static/extract | static after M3-01, motion after M3-03 | 64px full gates + frame consistency |
| M3-07 | docs, integration and release gates | after above | evidence-led operational go/no-go |

Do not assume sequence numbering proves readiness; individual PRs can merge as blocked or experimental with truthful status and preserved QA. Delivery can be parallelized for implementation, but real run authorization, release approval and runtime replacement are separate decisions.

## 4. Test matrix and non-negotiable negative cases

| Mode / case | No generation | Real E2E expectation | Failure isolation |
| --- | --- | --- | --- |
| A IMAGE_ONLY | validate + route without video dependency | 1 representative image, full review package | video absent by design |
| A IMAGE_TO_SPRITE | verify parent image and authorized budget | image ref -> video -> ordered frames -> sprites | parent image unmodified |
| B with 1 image | role/format + capability check | real video consumes 1 hash | no static generation |
| B with 2 images | ordered role compatibility | real video consumes both hashes | do not discard 2nd |
| B with 3 images | exact 3 conditioning inputs | real video consumes all 3 hashes | unsupported -> BLOCKED |
| C AUDIO_ONLY | no image/video nodes invoked | FLAC/WAV QA + listening review | no video/pixel path |
| D IMAGE_ONLY | 64 logical canvas + Pixel Gate | 64px export and Aseprite review | no video dependency |
| D IMAGE_TO_SPRITE | verified master + motion preflight | video + 64px all-frame QA + Aseprite | parent master intact |
| 32px | no default production plan | ON_HOLD_RESEARCH only | no auto promotion |

Always exercise negative/fault injection for path escape, missing approval, source hash drift, cap mismatch, missing models, missing workflow nodes, unavailable video engine, timeout, ambiguous outputs, unsupported ref counts, broken video, corrupt frame, palette failure, and incomplete manifest. Provider failures should not cause hidden fallback/retry or previously consumed budget reuse.

## 5. Evidence and measurement

Track per line and mode:

- **Input fidelity:** source/SOT identity, image hash/role, model and workflow fingerprints.
- **Delivery:** terminal artifact produced, QA status, human-review state, rerun/blocked reason.
- **Reliability:** attempted dispatches, successes, technical failures, lost/corrupt outputs, duplicated provider calls, unauthorized generation (target 0).
- **Art usability:** subject/pose/gear correctness, silhouette, camera stability, temporal identity, pixel-frame shimmer, audio semantic fidelity; reviewer evidence, not hallucinated scores.
- **Cost and lead time:** actual provider-reported usage when available; label NOT_REPORTED where unavailable.
- **Approval:** number of human-approved assets and verified in-game uses, separately from generated candidates.

No target percentages can be honestly inferred from the existing tiny real cohorts. Establish baselines from new authorized trials before introducing SLA or hard pass-rate targets.

## 6. Out of scope / stop rules

- 32px art production, novel pixel reconstruction research, default model re-ranking, new style menu expansion, SOT rewriting, automatic human/Golden approval, new GUI/web interface, cloud/DB, new public plugin submission, new MCP tools by default.
- Any real image, video or SFX generation requires explicit authorized run budget. This plan itself submits **zero** generation requests.
- No changes to live Windows MCP pinned runtime or user host registration without separate, verified approval.
- Code merge ≠ provider ACTIVE; static pass ≠ motion pass; video output ≠ sprite quality pass; QA pass ≠ game-ready; source file hash ≠ license approval.

## 7. Definition of done

- **Contract done:** a valid plan and fail-closed dry run for every line/mode, backward-compatible with old consumers.
- **Static done:** A/D IMAGE_ONLY complete without touching the I2V stack, with stable independent manifests and honest review status.
- **Motion done:** A, B(1/2/3), D meet their own actual end-to-end terminal trials with exact input-consumption provenance and reviewed sprite packages.
- **SFX done:** audio artifact produced, QA complete, explicit listening-review outcome recorded.
- **Factory done:** no claimed-ready mode lacks real reproducible evidence, human/art approval remains explicit, and authorized deployment/rollback gate is passed. If 3-image capability is unavailable, factory is **partially operational**, not falsely complete.

Reference: [Factory Architecture v1](FACTORY_ARCHITECTURE_V1.md).
