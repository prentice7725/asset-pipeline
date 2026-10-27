# Rabbit actual engine import and foot-baseline check, 2026-10-27

Branch: `codex/rabbit-engine-import-20261027`, base `9916efd`.
**REAL_ENGINE_IMPORT_RENDER_PASS / STARTUP_TIMING_REVIEW_REQUIRED**.
Human Aseprite review and game-ready approval remain pending.

## Input and reused implementation

Input is the [rabbit v2 loop/alpha candidate](RABBIT_MOTION_RECIPE_20261027.md):
source frames 14..41, 28 frames at 24fps, original pivot (256,510).
Candidate manifest SHA-256:
`d060cce9ebc43ce7a26805abdc0b490eb76ede45419c3905029c756ba433015d`.
RGBA atlas is 4096×2048, SHA-256
`55ac5b9550597a1a66762044298976a0f125a86dcb09747fe508b8b6658a24d5`.
Only 28 cells animate; the four unused cells are excluded.

This validation reuses the existing isolated [engine import fixtures](MOTION_ENGINE_IMPORT_20261027.md),
adapting frame counts/ranges, duration and the texture key for this input. No
production exporter, CLI, MCP, generation algorithm or GUI/web product was added.
Both engines use their native import/animation formats:

| Setting | Godot | Phaser |
| --- | --- | --- |
| Resource | SpriteFrames `.tres`, 28 AtlasTexture entries | Native spritesheet, explicit 0..27 frame range |
| Frame cells | 512×512, 8 columns, source atlas rectangles | Same; runtime cut rectangles checked |
| Animation | walk, 24fps, loop true | walk, 24fps, repeat -1 |
| Pivot mapping | centered=false, offset=(-256,-510) | origin=(0.5,510/512), display origin=(256,510) |
| Stationary root | (256,300), fixed | (256,300), fixed |
| Display scale | 0.5, inspection only | 0.5, inspection only |
| Movement stimulus | Separate copies translated at 60px/s | Same; not a calibrated gait speed |

Existing local Godot **4.7.2 stable** CLI actually executed `--version`, import,
headless runtime and separate real OpenGL viewport rendering. The previous
portable binary was reused; no new install/download. Console executable SHA-256:
`c8f0a6bc45a19b33541501e57f6f7cd972ab18453743266339d495cbbe846643`.
The renderer reported NVIDIA GeForce RTX 5060 Laptop GPU / OpenGL 3.3 NVIDIA 617.42.

Existing local Phaser **4.2.1** and its license were copied into the fixture.
Library SHA-256:
`66348b1b5141e49b7d5ebbe688cddcb502eab1cb00f21c538686a5b2c5abe4de`.
Actual Chromium **153.0.8010.12** ran WebGL with SwiftShader launch flags via
existing playwright-core. This is not target-device GPU/performance certification.

Projects, copied assets/libraries, diagnostics and captures are confined to ignored
`workspace/rabbit-engine-import-20261027/`. The browser HTTP server bound only to
127.0.0.1 on an ephemeral port and closed in `finally`. Chromium closed and Godot
exited automatically. No existing game/editor project or live server was changed.

## Executed checks and timing

| Check | Actual observation |
| --- | --- |
| Native frames / order / wrap | 28, 0..27 then wrap, both engines |
| Observed loops | 3 in each engine |
| Playback frame events | Godot 100; Phaser 84 |
| Nominal cycle | 1166.667ms |
| Godot first cycle | 1017ms; deviation, **not timing PASS** |
| Godot subsequent cycles | 1166ms, 1171ms |
| Phaser measured wrap intervals | 1180.3ms, 1164.9ms |
| Actual rendered captures | 28×1024×640 per engine, dark/light backgrounds |
| Runtime errors | No recorded Phaser engine/page/load errors; Godot commands exited 0 |
| Godot imported frame readback | All 28 alpha channels and nontransparent RGBA exact |
| Source sprite copies | Both engine PNG byte hashes match source |
| Protected files | 119 candidate + 122 upstream/source/config files unchanged |

The existing headless Godot diagnostic flushes two process frames after image
export and excludes explicit stop-reset events. Nevertheless this run's first
wrap was about 150ms shorter than nominal. The startup behavior is retained as
**REVIEW_REQUIRED**, rather than hidden by another run or claimed exact from
frame zero. Subsequent observed cycles are close to nominal; no deterministic
gameplay startup or frame-budget certification is inferred. Fixing/rechecking
initial playback under real game loading remains a follow-up.

Godot's generated import enables `process/fix_alpha_border=true`, with lossless
compression and no mipmaps. RGB under alpha=0 changed in 232,226 readback pixels;
alpha and every nontransparent RGBA pixel remained exact. This is hidden-RGB
normalization, not byte-exact imported-image equality. No source PNG was altered.
Phaser was checked through runtime frame rectangles, origins and actual canvas
captures; a separate Phaser texture RGBA roundtrip is not claimed.

## Foot baseline and visual observations

Both actual engines captured every candidate frame. For stationary upper actors,
the diagnostic measured brown boot pixels in screen crop x130..379, y230..300,
using R>G+8, R>B+8, R<160, G<100 and B<100. Red pivot markers and background
colors do not meet this mask. The explicit baseline is y300.

The measured baseline-minus-lowest-boot-pixel is **1..2 screen pixels** in all
28 frames, in both engines, on both dark and light backgrounds. This uses a
pixel-centre convention and 0.5 display scale. `foot-proxy.json` records every
frame, including bottom-band x extents/centroid, and the method/limitations.

This is a screen-space boot-bottom proxy. BOTTOM_CENTER alignment already
anchors the lowest silhouette, so its stability is partly imposed. The color
mask can omit antialiased toe edges and cannot associate anatomical left/right
support feet. It does not measure planted-foot world velocity, collision, root
motion calibration or foot-slip magnitude. The uncalibrated translated copies
are only an inspection stimulus. **Anatomical foot contact is not approved.**

Agent inspection of all-frame contact sheets and actual native captures shows
white face, ears, satchel and leg interiors present. Thin bright contours remain
visible on dark backgrounds; boot overlap, slight pose movement and gameplay
readability need human review. No halo correction, pivot edit or identity change
was made. The candidate's reviewer/check fields remain null, `game_ready=false`.

## Evidence, remaining work and rollback

Ignored experiment folder retains `prepare.py`, adapted fixture scripts,
`source-preservation.json`, `fixture-provenance.json`, import/runtime/render logs,
engine-native resources, actual generated import data, Godot imported-frame
readbacks, 56 native viewport/canvas screenshots, frame/loop measurements,
`verification.json` and explicit-limit `final-verification.json`.
`final-source-audit.json` binds 241 unchanged files. `candidate-inspect.json`
independently rechecks recipe integrity after both engines ran.
`engine-comparison.png` crops actual native captures; it is not a fabricated render.

Current validation consists of real engine executions and readback/hash checks.
The previous 756-pass/1-skip offline suite is historical; it was not rerun or
substituted for engine evidence. Only documentation is tracked in this change;
production source/config/contracts remain unchanged. No generation or retry,
model/node installation, budget reservation, human approval, Golden/SOT update,
MCP replacement or operational activation occurred.

Remaining gates: Godot startup timing, anatomical support-foot/gameplay motion,
readability/edge review and required human Aseprite approval. Both-character
import success is evidence for these specific samples, not universal compatibility.

Follow-up: the [startup diagnostic correction](GODOT_STARTUP_TIMING_20261027.md)
identifies the harness start-phase issue and verifies a guarded local start method.
The original timings above remain unchanged; production game startup still needs
its own integration validation.

Rollback: revert this documentation commit and stop using the isolated fixtures.
Preserve source/candidate/evidence and spent generation authorizations. No system
installation, production application or SOT migration requires reversal.
