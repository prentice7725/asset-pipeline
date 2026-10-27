# Godot diagnostic startup timing correction, 2026-10-27

Branch: `codex/godot-startup-timing-20261027`, base `8910f47`.
**LOCAL_GODOT_STARTUP_DIAGNOSTIC_PASS / REVIEW_REQUIRED**.
This corrects the isolated validation harness. No production game runtime or
asset animation is changed or certified.

## Observed cause

The [rabbit import diagnostic](RABBIT_ENGINE_IMPORT_20261027.md) reported a
1017ms first cycle against a nominal 1166.667ms, followed by near-nominal cycles.
The new probe logs wall time, process delta, each animation frame and, in
OpenGL mode, each post-draw frame without image readback during measurement.

The original scheduling pattern awaits two SceneTree `process_frame` signals,
then calls `play()` from that coroutine. Actual instrumentation reproduced a
145.010ms first process delta and a frame change only **0.021ms** after the
declared start. Multiple animation frames can therefore advance immediately.
PNG readback/encoding before playback took 422.525ms in the final control run;
its first cycle was 1033.365ms. A separately imposed 250ms loading stall also
reproduced the early wrap in the exploratory tests.

The evidence identifies pre-start work/current-frame delta leaking into this
diagnostic's animation start. It does not establish a corrupt sprite, wrong
24fps duration, or a Godot engine defect. The project reports delta smoothing
enabled, but no engine-implementation claim or global smoothing change is made.
Simply removing PNG export still left startup timing bias; a fixed 500ms wait
reduced it to about one process interval without correcting the start phase.

## Correction and scope

Tracked fixture: `tests/fixtures/godot/startup_timing.gd`.
It reuses native AnimatedSprite2D/SpriteFrames and the existing rabbit `.tres`,
atlas, 28-frame range and pivot. It changes only the diagnostic's scheduling:

1. Complete the explicit load/export stimulus before arming playback.
2. Keep the sprite stopped while checking six consecutive stable process steps.
   For this 60Hz fixture, both wall and engine intervals must be 8..25ms, differing
   by at most 4ms. Startup fails closed after 2s without stability.
3. Start from a Node `_process` callback after animation processing for that
   frame, instead of the earlier SceneTree `process_frame` notification.
4. Reset frame/progress to zero, record a new start clock and call `play()`.
5. During timing, collect small event records only. Any GPU readback/PNG capture
   happens after measurement and `pause()`, so it cannot contaminate the sample.

These bounds are an explicit **60Hz test-fixture policy**, not a portable gameplay
component, a fixed 100ms loading delay or a rule for arbitrary display rates.
Observed readiness waits were about 100..117ms after arming. Real game integration
must account for its own loading lifecycle, frame rate and timing policy.
FPS, Engine time scale, delta smoothing, sprites, source timestamps, colors and
the motion recipe were not changed to make the measurement pass.

## Final exact-code validation

The final stored fixture SHA-256 is
`80928e337b7cf63b83c6a1fef680e7d0b66b67f74c6b979fe8f8b51758fc2f74`.
It was copied byte-exact into a fresh isolated Godot project under ignored
`workspace/godot-startup-timing-20261027/`. The same existing Godot 4.7.2 portable
binary ran all seven final cases sequentially. No download or installation.

The declared acceptance window was **±22ms** around 1166.667ms: one 60Hz process
interval plus about 5ms scheduling allowance. It is a local diagnostic tolerance,
not exact millisecond delivery or a perceptual quality score. Every guarded case
checks three loops, complete chronological 0..27 order/wrap and a non-immediate
first frame change. The unguarded control must reproduce an early first wrap.

| Final case | First cycle, ms | Subsequent cycles, ms |
| --- | --- | --- |
| Original export + two signals, headless | 1033.365, expected control failure | 1166.608, 1149.968 |
| Guard + PNG export, headless | 1166.622 | 1166.650, 1168.298 |
| Guard + 250ms stall, headless | 1166.628 | 1166.638, 1169.322 |
| Guard + no extra work, headless | 1182.752 | 1166.608, 1151.585 |
| Guard + PNG export, actual OpenGL | 1166.640 | 1166.625, 1166.616 |
| Guard + 250ms stall, actual OpenGL | 1166.625 | 1166.633, 1166.609 |
| Guard + no extra work, actual OpenGL | 1183.280 | 1166.633, 1166.616 |

All 18 guarded cycle intervals satisfy the predeclared window. In all six cases
the first frame change was about 49..50ms after start rather than immediate.
All three OpenGL cases first rendered frame 0. Headless results are not relabeled
as viewport rendering; the OpenGL runs report the actual Windows display server
and NVIDIA renderer. Captured native PNGs were saved only after timing finished.

The initial guard draft had a GDScript bool inference parse error. It was fixed
with an explicit bool type before these final runs. The parser failure log and
all prototype/control measurements are retained; they are not PASS evidence.
Final code remains unchanged throughout the seven final diagnostic executions.
Two additional negative controls actually exited 2: a 1000fps CLI cap cannot
satisfy this 60Hz readiness policy and times out before playback, and an unknown
case is rejected before loading. Prior valid result files remain hash-identical;
failed controls are not relabeled as successful playback.

## Reproduction, evidence and remaining gates

Use a **fresh isolated project**, never an existing game project: copy the rabbit
fixture's `project.godot`, `walk.tres`, `sprites.png` and the tracked diagnostic as
`timing.gd` into a new directory under `workspace/`. Import once with the same
Godot executable, then run:

```powershell
& <godot-console.exe> --headless --path <isolated-project> --editor --import
& <godot-console.exe> --headless --path <isolated-project> --script res://timing.gd -- --case=guarded_export
```

The project must cap processing at 60Hz and contain this 28-frame, 24fps `walk`
resource. The default case is `guarded_none`; only the documented diagnostic case
allowlist is accepted. The fixture writes diagnostic JSON, optional readback PNGs
and post-measurement capture into that isolated project. It is not an approval API.

Ignored evidence includes `run_final.py`, `validated-cases.json`, original/prototype
results, native per-case logs, exact local script copy, actual imports/captures and
software regression logs. The validator binds fixture and Godot hashes, asserts
frame order/tolerance and verifies all **241 original/source/candidate files**
before and after. No old receipt or source report was rewritten to hide its result.

The prior raw rabbit engine evidence still has its early first cycle; this report
supersedes that harness limitation for the explicitly tested local start method.
It does not retroactively make the old measurements PASS. Production scene
loading/startup, target-device scheduling, anatomical foot contact, edge/readability
and required human Aseprite review remain unapproved. No image generation, retry,
provider switch, Golden/SOT or operational activation occurred.

| Current validation | Result |
| --- | --- |
| Required editable install `.[dev,motion]` | PASS |
| Installed `assetpipe --help` | PASS |
| Full offline pytest | 756 passed, 1 skipped; 643.52s |
| Final native Godot cases | Legacy defect reproduced; six guarded cases within declared tolerance |
| Negative controls | Unstable clock and unknown case rejected before playback, exit 2 |
| Sprite/SpriteFrames copies | Byte-exact originals; Engine time scale remains 1 |
| Source/candidate preservation | All 241 file hashes match |

The skipped local migration benchmark lacks local data and is not a PASS.
Native Godot executions, rather than the Python suite, are the evidence for this
GDScript behavior. The fixture digest binds the actual locally executed bytes;
a checkout that changes line endings requires fresh validation rather than edits
to old receipts.

Rollback: revert the new diagnostic fixture and this documentation change. Stop
using the optional guarded test method while retaining all measurements and source
assets. No production runtime, global project setting or data migration needs
reversal.
