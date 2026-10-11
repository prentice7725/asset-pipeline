# M3.1 — SFX receipts and explicit listening review

This change supplies offline contracts for short impact, UI cue and ambience.
It reuses the Stable Audio workflow, prompt construction and PCM conversion.
No provider promotion, audio model or factory dispatcher is added. Representative
real generation and human listening acceptance remain **NOT_RUN**.

## Plan C/AUDIO_ONLY

```powershell
assetpipe factory plan --request examples/sfx_short_impact_factory.json
assetpipe factory dry-run --request examples/sfx_ui_cue_factory.json
assetpipe factory inspect --request examples/sfx_ambience_factory.json
```

Envelopes point to unchanged Brief JSON and carry `duration_seconds`, optional
`category`, `clip_name`, `no_music` and `no_voice`. Categories are IMPACT, UI_CUE,
AMBIENCE and UNSPECIFIED; duration must match the Brief. Metadata is separate from
legacy Brief/MCP arguments. Plans return AUDIO metadata with zero dispatches and
reservations; the factory executor remains unimplemented. The existing pipeline
accepts optional `clip` metadata for a future authorized adapter. Legacy calls
default to UNSPECIFIED and the asset WAV name. Music/voice exclusions remain
advisory prompt requirements and require listening; no classifier proves absence.

## Evidence and isolation

Original FLAC and 16-bit PCM WAV are preserved. FFprobe verifies one FLAC audio
stream. WAV QA retains existing decoding/duration/non-silence gates and records
rate, channels, peak, RMS and clipping fraction. Conversion must preserve source
rate/channels. It does not normalize, trim or remove clips automatically.

`020_audio/clip_receipt.json` records project/asset/run identity, category/name,
workflow metadata, FLAC/WAV SHA-256, generation/QA hashes, sample metrics and
review-required state. State starts before dispatch and becomes FAILED on error.
Originals/intermediates remain available. An existing audio directory blocks a
second call before dispatch. The Comfy prefix includes project, asset and a
distinct run-path digest; same-named clips in different projects stay isolated.
Paths must resolve inside the run before inspection/review. Escapes, hash drift,
project mismatch, ambiguous output and failed QA block review. FFmpeg/FFprobe
have bounded timeouts; no shell invocation, retry or provider fallback is added.

## Submit listening observations

Passing clips receive `listening_review_template.json` with REVIEW_REQUIRED,
`listened: false`, blank reviewer/reason and null checks. Listen, then submit
true/false for intended effect, unwanted music/voice/noise, audible clipping,
onset/tail and game context. Set PASS/HOLD/REJECT, reviewer and reason. PASS
requires all checks true; missing listening declaration or stale evidence blocks.

```powershell
assetpipe --root C:/workspace/asset-pipeline sfx-review --run workspace/example_game/runs/clip/run_id --review workspace/listening_observations.json --listened
```

A new immutable `listening_review.json` binds receipt hash and recording time.
Existing reviews are never overwritten. No Golden, approved master, ACTIVE, SOT
or game-ready state is created. Even submitted PASS keeps `game_ready: false`;
run and receipt remain candidates. A named reviewer record cannot itself prove
that the person listened.

## Limits

Synthetic calibration sine/silence fixtures exercise real FFmpeg/FFprobe,
failure preservation, concurrent project isolation, drift and explicit HOLD.
They make no model calls and create no real approvals. Real representative
generation requires a separately approved budget; listening acceptance is also
missing. Historical smoke is not reused as new evidence. Passing tests do not
complete real M3.1 acceptance or establish production readiness. Filesystem
replacement between path validation and reads remains a limitation.

## Validation — 2026-10-11

Windows / Python 3.11.9 / MCP 1.30.0 isolated PR checkout:

- Full pytest: **501 PASS / 0 FAIL / 0 ERROR / 1 SKIP** (502 cases).
- Focused factory/SFX tests: **92 PASS**; additional Windows P1 fixtures: **22 PASS**.
- The existing SKIP is `test_direct_frames_are_identical_to_verified_legacy`:
  local migration benchmark data is absent from the isolated checkout. It stays
  skipped here; an independent read-only run in the original checkout passed.
- Actual offline MCP initialize/tools/list, exact six schema comparison and
  negative root-path tests passed. The owned test server exited via EOF.
- Editable install, CLI help and all three actual factory example plans passed.
- Existing original uncommitted files (76) and operating runtime files (954)
  retained their byte hashes. Main, registry and pinned runtime were not replaced.

Local logs/receipts are outside source modules under
`workspace/reorganization/20261011/m31/` in the original workspace. No model
generation, charged request, real approval, new deployment candidate or live
process termination occurred. Verdict: **OFFLINE_PASS / REAL_GENERATION_NOT_RUN /
HUMAN_LISTENING_NOT_RUN**, not complete M3.1 acceptance or activation readiness.
