# M2.5 real execution blocker

2026-10-01: origin/main and HEAD agree at 94606ea. ComfyUI 0.38.1, Aseprite 1.3.18.6 and FFmpeg are available. Initial experiment authorization permits at most 16 local generations; planned first cohort has 12 (8 pixel, 4 nonpixel).

Actual production entry-point execution of examples/pixel_animation_smoke.yaml stopped before frame extraction: Static master approval lacks pipeline provenance and Aseprite review. The old fixture approval fails the current immutable static-run evidence contract. No algorithm or legacy file was changed. Historical eight-frame exact comparison is separate evidence and does not establish this new full-pipeline run passed.

New generation requests: 0. Pixel static E2E, nonpixel E2E and Golden approval: NOT_RUN. The directive requires stopping after regression failure; no further cohort was submitted. scripts/style_lab.py preserves this failure, guards a maximum initial budget of 16, reserves requests durably before dispatch, and forbids implicit retries/fallback. Candidate recipes remain offline research; future explicit experiments embed their PromptSpec without promoting production defaults.

To resume, supply or produce a current validated static export with its passing resolution report, explicit reviewer selection, exact Aseprite roundtrip and human Aseprite approval. Bind that approval to its manifest and export hashes. Do not merely add missing fields to the old record. Once a valid approval exists, update the benchmark fixture reference, rerun the actual animation regression, and only then run the planned generation cohort. New character animation remains unsupported by the blue-tunic profile.

M2.5 INFRA READY is not claimed: the initial harness is present, but full classification, model-hash evidence, role QA and measured cohort remain unfinished while the blocker exists.
