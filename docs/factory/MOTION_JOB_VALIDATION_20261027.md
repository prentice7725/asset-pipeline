# Factory motion job integration validation, 2026-10-27

Branch: `codex/factory-motion-integration-20261027`, base `7c46b1f`.
**OFFLINE_INTEGRATION_AND_REAL_EXISTING_VIDEO_REPLAY_PASS / REVIEW_REQUIRED**.
New real video generation and production activation: **NOT_RUN**.

## Change and reuse

Changed implementation: `src/assetpipe/factory/motion.py` (thin stages),
`src/assetpipe/motion/exports.py` (native resource formatting), additive Factory
subcommands in `src/assetpipe/cli/__init__.py`. New job schema/example and tests
extend `test_motion_package.py` and `test_motion_executor.py`.

Existing Factory contracts/planner/provenance, RootResolver, manifest writer,
FFmpeg decode/extraction/alignment/packing, v1/v2 recipe plan/apply/inspect and
video execution plan/single-attempt budget executor are reused. The generic
`factory execute` source was not changed: it still blocks IMAGE_TO_SPRITE.
No ported algorithm, still/SFX workflow, six MCP schema, style compiler, Golden
approval, model/node installation or production config was changed.

The shared job has EXISTING_VIDEO replay and explicitly authorized prepared-video
branches. Both converge on the same recipe and engine resources. The authorizing
file is pinned and the existing video ledger owns the one attempt; the coordinator
does not reserve another budget or silently regenerate/retry a source.

## Actual replay through installed CLI

Both existing original 56-frame/24fps videos were processed using
`factory motion-plan`, `motion-run`, `motion-inspect`. No provider was called and
the real `workspace/factory_budget` ID set stayed unchanged.

| Evidence | Fox | Rabbit |
| --- | --- | --- |
| Existing generation ID | `2c301ac05cce430495f2be6f9448a246` | `7df3b4bacfd446518543297da58c50bd` |
| Explicit recipe | v1; 13..32; distance 60 and previously reviewed local cleanup | v2; 14..41; distance 32; no cleanup |
| Final frame count | 20 | 28 |
| Existing candidate comparison | All RGBA frames, pivot and source order exact | All RGBA frames, pivot and source order exact |
| Native export sprite SHA-256 | `c463819877db5cca5ba31dfdf29df54828ee3213a974b8602b2ffe933e06a38f` | `55ac5b9550597a1a66762044298976a0f125a86dcb09747fe508b8b6658a24d5` |
| Job plan SHA-256 | `82e26305343bebd3ce04401318a34a34adf9549cbec948177dc292c03aaf8f5f` | `e690a06c1a3432c8539dc3cc8074bb2ec7256d5efce9f7dd439776aba40025c1` |
| Job receipt SHA-256 | `6eec13f5593fb12cf9e44f5cff69fd2d5c2e69773bfa2ce9dc965eb92237d58a` | `0e3a8413375232151a54ae1f6f09c923a73604d696ae4446d0f84858aff238db` |
| Generation requests this replay | 0 | 0 |

Inspection returned FACTORY_MOTION_INTEGRITY_PASS_REVIEW_REQUIRED for both.
Historical generation receipts, containing original parameters, were preserved
byte-exact as opaque evidence. They are not fresh authorization or a new proof of
reference-role semantics. All **725 protected source/candidate/evidence files**
matched before/after. No quality improvement is claimed from exact reproduction.

## Actual engine resource consumption

Fresh isolated projects loaded the exports directly. Existing Godot 4.7.2 native
SpriteFrames accepted sibling-relative `sprites.png` paths. The previously
verified startup probe was reused with the actual frame count; actual OpenGL
rendering began at frame 0. Fox observed four loops, rabbit three. All 20/28
imported alpha channels and visible RGBA matched; expected hidden-RGB border
normalization changed 196,680 / 232,226 pixels under transparency only.

Actual Phaser 4.2.1 / Chromium 153.0.8010.12 WebGL loaded the native atlas,
animation JSON and origin. Each asset observed three loops with correct frame
count/order, cut rectangles and pivot, without page/engine/load errors.
The initial fixture used an explicit texture alias; a final direct-key check
consumed the exported `motion` key and animation JSON unchanged for both assets.
Its separate results and the initial alias evidence are retained.

The Phaser test server was loopback-only/ephemeral and closed with Chromium;
Godot exited after each test. No game/editor project was changed. Native import
does not approve foot contact, first-frame scheduling in a real game, thin edge
halos or human/Aseprite review. Production engine quality remains a separate gate.

## Software gates and encountered failures

Focused tests cover real FFmpeg replay, source equality, downstream failure stops,
exact inventory tampering, stale plan/video/alpha gates, outside-workspace outputs
and rejecting a foreign output before reading it. Generation uses a fake Comfy
client plus real local video packaging to verify the original one-request ledger,
no-consent zero dispatch, disabled backend and prepared/request mismatch.
They are not real model generation evidence.

The first focused suite had 64 passes/one failure: a broad external-JSON validator
incorrectly treated internal compiler-code metadata as data-root access. Internal
receipts now use expected-hash reads and validate each dereferenced data link;
allowed roots were not widened. A separate tamper-setup test encountered Windows
atomic-publication WinError 5; intentional corruption now uses a direct test-only
write. The production manifest writer was not changed and no retry added. These
initial failures are retained and not relabeled as PASS.

| Current software check | Result |
| --- | --- |
| Required editable install `.[dev,motion]` | PASS |
| Installed top-level and Factory help | PASS; four additive Factory subcommands |
| Full offline pytest | 772 passed, 1 skipped; 655.45s |
| Generation wrapper focused tests | 4 passed, 38 deselected; 8.77s |
| Final stronger input-gate rerun | 5 passed, 22 deselected; 10.46s |
| Published job schema | Matches runtime validator |

The final focused rerun verifies exact expected error types/codes strengthened
while the full suite was running. The skipped local migration benchmark lacks
local data and is not a PASS. The initial partial counts and historical suites
are not substituted for this current full result.

## Evidence, remaining blocks and rollback

Ignored `workspace/fmi27/` retains two job inputs, CLI logs, original preservation
hashes, replay results, complete `fox/` and `rabbit/` runs, immutable package/recipe
intermediates, native exports and isolated real engine projects/logs/readbacks.
`replay-results.json`, `native-results.json`, `direct-phaser-results.json` and
`protected-sources.json` distinguish each evidence boundary.

Remaining: separately budgeted real generation through this new coordinator,
2/3-reference capability, external-only sources, Pixel64 motion, human Aseprite,
Golden/SOT, production activation and any live MCP replacement. None is implied
by the offline integration or old generation receipts. Default research disabled
and ordinary Factory motion blocking remain intact.

Rollback: revert this commit's additive CLI/job/export modules, schema/example,
tests/docs. Existing standalone motion and static/SFX paths remain available.
Preserve new/old originals, intermediates, failures and consumed authorization
directories. No provider/config activation or SOT migration needs reversal.
