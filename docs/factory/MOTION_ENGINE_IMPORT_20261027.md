# Actual Godot / Phaser import checks — 2026-10-27

Branch: `codex/motion-engine-import-20261027`, base `136088a`.
Input: the [lower-body cleanup v2 candidate](MOTION_ALPHA_CLEANUP_20261027.md).
**REAL_ENGINE_IMPORT_AND_RENDER_PASS / STEADY_PLAYBACK_CHECKED / REVIEW_REQUIRED**.
This is technical compatibility evidence, not game-ready or human art approval.

## Actual runtimes and isolation

The Godot connector reported `PLUGIN_DISCONNECTED`; no other project/editor was
opened or modified. No Godot command was on PATH or found in the bounded local
search. A broader filesystem search was stopped without altering files. The
official portable build was downloaded into the ignored validation folder only:

- **Godot 4.7.2 stable**, official `ed1daf0bf`; CLI `--version` actually executed.
- [Official release](https://github.com/godotengine/godot-builds/releases/tag/4.7.2-stable),
  `Godot_v4.7.2-stable_win64.exe.zip`, 86,013,866 bytes.
- Archive SHA-256 matched the GitHub release asset digest:
  `731980f9608d61333e5baf54a2ef17210acc7a538446c0cb9969f002aca1e953`.
- The archive was checked for output-path containment before extraction. No
  system installation, plugin installation or existing project change.

Existing local **Phaser 4.2.1** and its MIT license were copied from
`C:/workspace/brass-and-claw/node_modules/phaser/` into the isolated fixture.
That project's files were read only. Existing **playwright-core 1.63.0** drove
**Chromium 153.0.8010.12**; no npm/browser installation. Chromium was launched
headless with SwiftShader flags for WebGL, so this is not target-device GPU or
frame-budget certification. Godot's separate real renderer used **OpenGL 3.3 /
NVIDIA GeForce RTX 5060 Laptop GPU**, driver string `617.42`.

All projects, screenshots, binaries, scripts and logs are under this worktree's
`workspace/motion-engine-import-20261027/`. The Phaser HTTP server bound only to
127.0.0.1 on an ephemeral port and was closed after the test. Chromium closed,
and Godot exited automatically. No running production server was replaced.

## Native import formats and mappings

Both projects copy the exact 4096×1536 RGBA sprite sheet:
SHA-256 `c463819877db5cca5ba31dfdf29df54828ee3213a974b8602b2ffe933e06a38f`.
The sheet has 20 occupied 512px cells; four unused grid cells must not animate.

| Setting | Godot | Phaser |
| --- | --- | --- |
| Imported asset | Native `walk.tres` SpriteFrames with 20 AtlasTexture resources | Native `load.spritesheet`, 512px cells, explicit `startFrame=0,endFrame=19` |
| Animation | `walk`, 24fps, loop true | `walk`, 24fps, repeat -1 |
| Frame rectangles | `(i%8×512, floor(i/8)×512,512,512)` | Same, verified from runtime cut rectangles |
| Original pivot | `(256,510)` | `(256,510)` |
| Native pivot mapping | `centered=false`, `offset=(-256,-510)` | origin `(0.5,510/512)`, runtime display origin `(256,510)` |
| Display scale | 0.5, for inspection only | 0.5, for inspection only |
| Stationary root | `(256,300)` | `(256,300)` |
| Moving probes | Separate copies translated at 60px/s | Separate copies translated at 60px/s |

These use the engines' native
[AnimatedSprite2D/SpriteFrames](https://docs.godotengine.org/en/stable/classes/class_animatedsprite2d.html)
and [Phaser animation](https://docs.phaser.io/phaser/concepts/animations) APIs.
The fixed translation speed is an inspection stimulus, not a calibrated gait
speed recommendation. Animation/world-foot synchronization was not solved here.

## Executed checks and observed timing

Godot actually ran `--headless --editor --import`, then a scene-tree runtime
check loading the `.tres` and using AnimatedSprite2D. Twenty imported frame images
were exported back through Godot. A separate non-headless OpenGL check ran in a
hidden/offscreen test window, captured actual viewport frames 0, 10, 19 on dark
and light backgrounds, played moving/stationary copies and exited. These captures
are engine-rendered images, not recomposited source PNG previews.

Phaser actually loaded the PNG in Chromium WebGL, observed three repeats and
60 sequential frame-update events, checked cut rectangles/count/origin, then
captured canvas frames 0, 10 and 19. JavaScript page errors and recorded engine/
load errors were empty. No fallback renderer or synthetic runtime was substituted.

| Check | Actual observation |
| --- | --- |
| Frame count/order | 20; 0..19 then wrap in both engines, including all indices |
| Godot loops / final playback events | 3 / 71 |
| Phaser loops / events | 3 / 60 |
| Godot steady wrap intervals | 833ms, 834ms |
| Phaser measured wrap intervals | 836.4ms, 830.2ms |
| Godot first wrap interval | 700ms, startup catch-up present; not a first-cycle timing PASS |
| Stationary root | Identical in all sampled positions, both engines |
| Moving probe | More than 100px root displacement; timeline/frame metadata retained |
| Visible imported Godot pixels | All 20 frames' alpha and nontransparent RGBA equal original |
| Source sprite copies | Both byte hashes equal the original sprite PNG |
| Captured render images | Three distinct 1024×640 images per engine; nonempty character content on both backgrounds |
| Original candidate files | All 51 before/after file hashes match |

The headless diagnostic's initial image-export work introduced a startup delta:
the first run wrapped after 667ms and included `stop()` resetting the final frame.
That raw result/log was retained. A revised diagnostic flushes process frames and
excludes the explicit stop-reset from the playback event sequence; its first wrap
still occurs at 700ms, while subsequent wraps are 833/834ms. This startup limitation
is retained rather than relabeled as exact 24fps from the first frame. Frame order,
configured speed and steady-state playback were verified; deterministic first-frame
startup under gameplay loading has not been certified.

Godot's actual generated `.png.import` has `process/fix_alpha_border=true`,
`premult_alpha=false`, lossless compression and no mipmaps. Import changed RGB
under alpha=0 in 196,680 pixels across the frame exports; **no alpha or visible
RGBA differences** were found. Original PNG bytes were never changed. Hidden-RGB
normalization is not treated as visible pixel loss or full-byte image equivalence.

## Visual observations and remaining gates

In the sampled actual engine captures, the requested leg-gap white patch and
ground remnant are absent on both backgrounds. White muzzle, tail tip and scarf
remain visually recognizable. A thin bright outline remains visible against the
dark matte; neither renderer establishes a halo-free quality approval.

Root/pivot **configuration and numerical placement** were checked. Anatomical
root motion, support-foot tracking, foot-slide magnitude and temporal edge flicker
were **not measured/approved**. No perfect-pivot or seamless-gameplay claim follows
from a fixed origin or stationary object coordinates. Required human Aseprite
review, gameplay readability, Golden/SOT and production activation remain open.
Asset `review.json` is unchanged, reviewer null, `game_ready=false`.

## Artifacts and rollback

`workspace/motion-engine-import-20261027/` retains:

- `source-preservation.json`, `verification.json`, verification log.
- Official release metadata/ZIP and isolated `tools/godot/` binaries.
- `godot/`: project, sheet, native `.tres`, scripts, actual `.godot` import data,
  imported frame PNGs, runtime and OpenGL render results, three screenshots.
- `phaser/`: copied sheet/library/license, HTML test scene, runtime results,
  three browser screenshots; `run_phaser.cjs` in the parent.
- Initial/final Godot logs and raw first runtime result remain separately retained.

Real runtime/resource/render checks ran; no source/runtime/config/MCP change, new
image generation, alpha correction, budget reservation, model install or SOT
operation occurred. The earlier 720-pass/1-skip software suite is historical and
was not rerun or used as engine-import evidence here.

Tracked changes: this report, README, CHANGELOG and cleanup-report follow-up.
Rollback: revert this documentation commit and stop using these isolated fixtures.
Keep original assets and consumed generation evidence. Optional local portable
tool artifacts are confined to the ignored test folder; no system installation
or existing project needs reversal.
