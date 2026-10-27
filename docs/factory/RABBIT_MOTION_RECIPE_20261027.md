# Rabbit loop and alpha candidate, 2026-10-27

Branch: `codex/rabbit-motion-recipe-20261027`, base `f2d336f`.
**OFFLINE_CANDIDATE_REVIEW_REQUIRED**. Zero generations, retries or provider calls.

## Source and explicit decisions

The source is the completed [rabbit video package](MOTION_SOURCE_STYLE_20261027.md),
authorization `7df3b4bacfd446518543297da58c50bd`, 56 frames at 24fps.
Its package manifest SHA-256 is
`892b80828120849536e7c85ff308ade70efd15ec2256be888acec2fe64cff8be`.
Original video, source still/manifest, extraction frames and generation evidence
are preserved. This step processes existing aligned frames only.

The fixed v1 white distance 60 was **visually rejected**: the connected mask
removed the rabbit's pale face, satchel and leg interiors. The rejected analysis
sheet is retained; successful background removal was not called quality PASS.
The fox cleanup rectangles/colors were not applied to this white character.

Four source frames (14, 21, 28, 41) were compared at distances 8, 16, 24, 32 and
60. Distance 8 left isolated white noise; 60 erased foreground. The agent selected
32 after visual comparison, then inspected all 28 selected frames over dark
background. Face, ears, satchel, cream legs and clothing remain visible there.
This is agent observation, not a human Aseprite approval or an exhaustive
foreground annotation. Thin bright edge halos remain a review item.

The explicit loop range is **14–41 inclusive: 28 frames, 24fps, 1.166667s**.
It excludes the still-pose start and contains both alternating leg phases.
Endpoint comparisons supported the agent's selection; the CLI never selects a
range or a tolerance automatically. No duplicate deletion, interpolation,
retiming, pivot change, color change or anatomical redesign was performed.
No local cleanup rectangles were needed for this candidate.

## Minimal recipe extension and reuse

Changed code: `src/assetpipe/motion/recipe.py`; tests:
`tests/unit/test_motion_recipe.py`; new published schema:
`schemas/motion_review_recipe.v2.schema.json`.
The v1 schema/file and its fixed distance 60 remain unchanged. V2 accepts an
explicit integer 0..60, narrows the white-distance mask and reuses existing
`pixel.direct.ported.edge_connected`. It retains original RGB, intersects the
new alpha with source alpha, and uses the existing Source/RootResolver, plan
binding, copy/intermediate/report, packing and inspect paths. No verified utility
or legacy `_ported` implementation was rewritten. Production defaults, still/SFX
routes, six MCP tools, Golden/SOT and research activation are unchanged.

Plan/receipt formats remain version 1; the normalized input records recipe
version 2 and the exact tolerance. No implicit fallback or auto retries exist.
Source/code/parameter drift still blocks execution or inspection. Old receipts
remain bound to their historical code digest; they are not rewritten to pretend
that they were created by the new implementation. A fresh v1 replay is the
appropriate equivalence check against current code.

## Actual candidate and evidence

Installed CLI `motion-recipe-plan`, `motion-recipe-apply` and
`motion-recipe-inspect` executed against this source with explicit provenance
roots. Actual result is **ARTIFACT_INTEGRITY_PASS_REVIEW_REQUIRED**.

| Evidence | Value |
| --- | --- |
| Input recipe | v2; frames 14..41; white RGB 255/255/255; distance 32; no cleanup |
| Plan SHA-256 | `56bda3ff062da74ebe26b341d04829e21218ce5ed8dbc258499342748f415805` |
| Candidate manifest SHA-256 | `d060cce9ebc43ce7a26805abdc0b490eb76ede45419c3905029c756ba433015d` |
| RGB preservation | All 28 frames exact |
| Outside declared white distance | All 28 frames RGBA exact |
| Existing transparency | Never made opaque |
| Boundary lower-body RGB MAE | 3.086758 |
| Internal transition lower-body MAE | median 8.114573; maximum 13.962538 |

The pixel metric uses aligned frames composited over RGB 25/30/45 and rows
320..511. It describes image differences, not perceptual quality, foot contact,
loop approval or character identity. A lower boundary difference than the internal
median does not prove a seamless cycle.

Ignored evidence is in `workspace/rabbit-motion-recipe-20261027/`: rejected/all
source contact sheets, threshold comparison, recipe/plan, CLI logs, immutable
`candidate/` with all intermediates/masks/review state, `verification.json`,
dark/checker GIFs and transparent APNG. Previews stay outside the candidate's
hashed artifact inventory. APNG uses source-like millisecond timing; GIF timing
alternates centiseconds. Original video remains preserved.

## Current validation

| Check | Actual result |
| --- | --- |
| Focused recipe tests | 29 passed; 1.82s |
| Full offline pytest | 756 passed, 1 skipped; 586.85s |
| Required editable install `.[dev,motion]` | PASS |
| Installed CLI help and actual plan/apply/inspect | PASS |
| Published schemas vs runtime validators | Both v1 and v2 exact |
| Fresh rabbit v2 CLI replay | All 28 RGBA frames and atlas pixels exact |
| Fresh fox v1 CLI replay | All 20 RGBA frames and atlas pixels match previous candidate |
| Declared source hashes, source still/manifest and pipeline config | 122 files match |
| Transparent APNG roundtrip | All 28 decoded RGBA frames exact |

V2 tests exercise border-connected cream preservation, enclosed white details,
existing partial alpha and invalid version/tolerance bounds before output creation.
Existing recipe tests continue to exercise tamper/source/path/receipt/review gates.
The first fixed-60 image was an analysis rejection, not a passed candidate or a
generation retry. The fresh same-parameter offline replays establish deterministic
equivalence only; they do not retry a generator or confer artistic approval.

Replay receipts and source-hash inventory are retained in `replay-results.json`
and `source-audit.json`. Full output is retained in `pytest-full.log`; the skipped
local migration benchmark lacks local data and is not reported as PASS.

At this candidate stage, engine import was NOT_RUN and human Aseprite review
NOT_APPROVED. Subsequent [actual rabbit engine checks](RABBIT_ENGINE_IMPORT_20261027.md)
verify native import/rendering and preserve the startup/contact review limits.
The existing fox engine evidence does not approve the rabbit output. Foot
contact, boot crossings, slight body motion and thin light edges remain review
items. No Golden approval or game-ready delivery is claimed.

## Rollback

Revert this change to remove optional v2 support, its schema and documentation.
Keep existing v1 operation and all original/candidate/failed-analysis artifacts.
Do not rewrite historical receipts or replay consumed generation authorizations.
No operational or SOT migration needs to be undone.
