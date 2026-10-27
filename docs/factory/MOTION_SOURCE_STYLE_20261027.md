# Still-source style semantics for motion research, 2026-10-27

Branch: `codex/motion-source-style-20261027`, base `f3478a5`.

## Change and reused contracts

`src/assetpipe/providers/video/prompt.py` adds an explicit
`source_semantics_v1` mapping to the existing natural-language research profile.
It reuses `bind_menu`, project/SOT resolution, the original `compile_prompt`,
style/recipe validation, PromptSpec, spatial relationships and subject/direction
rendering. The generic still compiler and its workflow binding remain unchanged.

A styled parent must identify a registered NONPIXEL_IMAGE source workflow with
the original hash. Recompiling the unchanged source Brief against that workflow
must exactly reproduce its recorded compilation, including menu selection,
profile digest and style fingerprints. Missing historical evidence or drift
blocks the plan. Source and reference files are never rewritten.

The video text renders the validated semantic PromptSpec and all eight structured
style fields plus required/forbidden features. The explicitly requested motion
becomes a derived pose; the original source pose/compilation stays in provenance.
Still-model quality tags, prefixes and defaults are not copied into the video
dialect. This mapping does not invent an approved style/video model recipe.

Source capability requirements also apply to video. Text rendering and native
subject exclusion requirements cannot silently become prose. Instruction-only
exclusions require the video's declared instruction capability and remain
REVIEW_REQUIRED. Model overrides/rescue approvals are unsupported in this mapping.
Style-free historical inputs retain the existing compilation route.

`executor.py` reuses the existing immutable prepared-input, authorization,
single-reservation, single-upload/queue, graph/history correlation and packaging
path. Plan hashes additionally bind the new mapping and shared prompt/style/
art-direction Python sources. Existing style files and workflow/profile bindings
remain covered. The research setting remains disabled by default; production
Factory IMAGE_TO_SPRITE and six MCP tool contracts are unchanged.

## Verification and limitations

Focused source-style tests cover contract/identity preservation, unchanged source,
workflow/history/trait drift, disabled mapping, unsupported exclusions and the
existing menu lock. Existing executor tests cover dispatch/budget/failure gates.
All model dispatches in these tests are synthetic; they are not quality evidence.

The existing rabbit source compiles with its original STYLE-107 and Krea2 source
history intact. Source image/manifest hashes remain those recorded in
[the preceding experiment](MOTION_SECOND_CHARACTER_20261027.md).
The tight ear/sole margins and non-neutral arm pose in that still remain known
discrepancies. Successful compilation does not repair or approve them.

| Current verification | Result |
| --- | --- |
| Required editable install `.[dev,motion]` | PASS |
| Installed `assetpipe --help` | PASS |
| Full offline pytest | 750 passed, 1 skipped; 543.40s |
| Final camera-context focused rerun | 7 passed; 4.65s |
| Existing executor focused tests | 38 passed; zero model generations |

The skipped local migration benchmark lacks local data; it is not a PASS.
The first new fixture incorrectly combined Krea2 with unsupported free-form
negatives and was blocked by the existing source compiler. The corrected fixture
uses the valid STYLE-107 structured exclusion policy; no gate was relaxed.
The final focused rerun covers the explicit source-camera context added during
the full suite. Logs and immutable offline plan are under ignored
`workspace/motion-source-style-20261027/`.

No additional still generation, automatic retry, fallback, Aseprite approval,
Golden promotion or operational activation is allowed. The remaining, already
authorized video attempt is recorded separately below.

## Actual rabbit video and package

**REAL_VIDEO_PACKAGE_E2E_PASS / REVIEW_REQUIRED**, restricted to this source,
workflow and bounded attempt. Still generation remains the preceding single call;
this run adds exactly one video submission, no retry/fallback.

| Evidence | Actual value |
| --- | --- |
| Authorization/reservation | `7df3b4bacfd446518543297da58c50bd` |
| Submitted plan SHA-256 | `de90466783ac50881c8b290da1fcee5bc0ee5a06f5a44210098f24dd2af8c946` |
| Comfy prompt ID | `5eddc2cc-fca4-45c0-9a11-5728f193442a` |
| Parameters | seed 7727; 512×512; 56 frames; 24fps |
| Reference upload / video queue attempts | 1 / 1 |
| Original video SHA-256 | `0eed7ab5961841fd98d43c4fc0b26bfcd157199e5ac250dcb711d0d85fcdac72` |
| Package manifest SHA-256 | `892b80828120849536e7c85ff308ade70efd15ec2256be888acec2fe64cff8be` |
| Independent output hash checks | 5/5 match |
| Raw frames | 56; 512×512; 56 distinct hashes; original order preserved |
| Source image/manifest | Original SHA-256 values unchanged |
| Temporary research configuration | Byte-exact restoration; disabled again |

The existing executor verified all five local model files, exact submitted graph
against execution history and the ID-specific MP4 output. It saved the original
video before using existing extraction/alignment/packing code. Reference history
correlation is not a signed proof of server-resident weights or universal
reference-role semantics; those limitations remain as documented for the executor.

Ignored local evidence: `workspace/motion-source-style-20261027/attempt/`
contains config snapshots, authorization, rebound plan and operator receipt;
`workspace/factory_budget/7df3b4bacfd446518543297da58c50bd/` contains generation
receipt, graph/history, original MP4 and package intermediates/outputs.
`verified-result.json`, `verify.log`, `contact.png` and `preview.gif` are in the
experiment folder. GIF durations alternate centiseconds to approximate 24fps;
the original MP4 remains the timing authority.

Agent visual inspection of contact frames 1, 8, 16, 24, 32, 40, 48 and 56 shows
the white rabbit, both long ears, blue vest, red belt, boots and one shoulder
satchel retained while the legs move. This is sampled visual observation, not
an exhaustive semantic score or human approval. The source's tight margins
remain; boot overlap/shape during crossings and foot contact need motion review.
The full clip starts from the still pose and has no selected seamless cycle.

Rabbit alpha processing, cleanup-region selection, loop recipe, engine import
and human Aseprite review are **NOT_RUN / REVIEW_REQUIRED**. Fox-specific frame
13–32 selection and cleanup coordinates were not reused blindly. No measured
quality improvement, general style/video compatibility, Golden approval or
game-ready status is claimed. The next bounded offline step is to inspect this
clip's cycle and white matte and record a rabbit-specific review recipe.

## Rollback

Revert this change to restore the previous research compilation behavior. Remove
the optional profile mode with the code change. Preserve ignored run artifacts,
originals and authorization/receipt ledgers; never replay a spent authorization.
No production data, SOT or live MCP replacement is part of this change.
