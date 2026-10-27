# Fox walk loop candidate — 2026-10-27

Branch: `codex/motion-loop-candidate-20261027`, base `87129b0`.
**LOSSLESS_DERIVED_CANDIDATE / REVIEW_REQUIRED**. No new generation or human approval.

This follows the [advisory review](MOTION_ADVISORY_REVIEW_20261026.md) by making one
separate interior-cycle candidate from the existing real video. It does not replace
the original 56-frame package or fix alpha, headroom, anatomical pivots or engine
integration.

## Selection and exact source mapping

Selected **original source frames 13..32 inclusive**, all 20 frames in order.
At 24fps this is ~0.833333 seconds. The original half-open time range is
**[0.5, 1.333333333...) seconds**; the last selected source-frame timestamp is
31/24 seconds. Candidate index 0 corresponds to source frame 13, candidate index
19 to source frame 32. No frames within the window were dropped or duplicated.

The existing 20-sample cycle proxy informed a bounded comparison of 140 interior
windows, lengths 18..22 frames. Comparisons measured full-canvas aligned RGB
endpoint differences; no hard quality threshold or automated semantic approval.
The 13..32 window had the smallest endpoint difference in those trials. A contact
sheet of all 20 proposed frames was then inspected: alternating leg movement is
visible and the startup standing section is excluded. This is an agent-selected
candidate, not a human-approved walk-phase or foot-contact selection.

`selection.json` records, per candidate frame, the original 1-based frame number,
original/candidate timestamp, raw/aligned source paths and hashes, copied raw file
and derived raw/aligned hashes. It binds the original execution receipt/hash,
prompt ID, consumed authorization, source video and source atlas hash.
The original generation prompt ID remains
`de264d36-a8ad-4e26-ad36-8d1e958df782`; no new prompt was submitted.

## Reused path and outputs

The existing semantic `select_keyframes` API requires 6–8 named phases and review
metadata. It was not used to mislabel a dense 20-frame trim or invent approval.
No verified algorithm was rewritten.

The selected original **raw** PNGs were copied with exact byte-hash checks, then
encoded with real FFmpeg **FFV1 lossless / bgr0** into `selected.avi`. The existing
`assetpipe.motion.package.package_video` reused its Factory/root/provenance checks,
FFprobe timing checks, decoder, extractor/alignment and sprite packer. The derived
packaging-only request declares 20 frames / 20÷24 seconds explicitly. No automatic
resampling, interpolation, color/alpha editing or pose reconstruction occurred.
Audio is omitted from the derived clip; the original MP4 remains intact.

Twenty frames is valid for this offline package. It is **not** a supported 17k+5
length for the research generation adapter, and this packaging request must not
be treated as a new I2V execution plan or authorization.

| Item | Actual result |
| --- | --- |
| Original source video SHA-256 | `2b705e1330dfcf5259541142dc18044f3d4832b6e7d42e83b089e09dcf34fd4d` |
| Selected FFV1 AVI SHA-256 | `0feb9935461ff79a5e43e35a3cd8f13d0a9f1103063f530cb832313b29c63cf8` |
| Selection/lineage JSON SHA-256 | `82ce49ce1c2dbeebb86b305034f0d3950a3176528c19d520e0d9ffba27fc9a0c` |
| New package manifest SHA-256 | `b608f6fb701c02dba730ca54d0d19f0e98272baae2321e286bc5296c8db41829` |
| Sprite PNG SHA-256 | `f945f345fa1f2e9f610bbf9d256feeaafe92f6908018e9587c860a7202e93c28` |
| Atlas JSON SHA-256 | `78b4cf408b0448e3396d9defdec3e6bbf7bfe0c3a6a0efc7b52bc50d5b772a62` |
| FFprobe result | 512×512; CFR 24fps; 20 frames; ~0.833333 seconds |
| Sprite atlas | 4096×1536; 20 occupied 512px cells in an 8-column grid |
| Pixel preservation | All 20 raw and 20 aligned frames equal the selected original pixels |
| Alignment / pivot | Same offsets and `(256,510)` convention as original selected frames |
| Atlas verification | All 20 cells equal their aligned frames; recorded output hashes match |
| Human review | Reviewer null; all `review.json` checks null; `game_ready=false` |

The child atlas's `source_frame_index` is local to the derived 20-frame clip.
Use `selection.json` to map to the original 56-frame run; do not mistake local
frame 1 for original frame 1. The generation-stage receipt remains the original
research run; this candidate's `generation_status=NOT_RUN` is correct for trimming.

## Measured boundary change and remaining work

Aligned last→first full-canvas RGB MAE changes from **20.848200** for the original
56-frame wrap to **3.807761** for this candidate. The candidate's adjacent median
is **8.893935**, maximum **17.221129** (0..255 channel-difference units, background
included). This is a measured endpoint change, not a quality percentage or proof
of continuous velocity, correct left/right walk phases or a seamless game loop.
Normal-speed human playback review is still required before accepting the trim.

Original flagged top contacts at source **18,19,20,27,28,29** remain in this window
(local frames **6,7,8,15,16,17**). No ear reconstruction or headroom correction was
performed. Source tail, equipment and silhouette pixels are preserved exactly.
All occupied frame alpha remains 255; unused atlas cells are empty, not evidence
of character transparency. Foot slide/anatomical pivot stability, required Aseprite
review and Godot/Phaser import remain unverified. No game-ready/Golden/SOT promotion.

## Artifacts, verification and rollback

Artifacts relative to this independent worktree:
`workspace/motion-loop-candidate-20261027/` contains trial comparisons, proposed
contact sheet, dated scripts/logs, and `candidate_13_32/` containing:

- `selection.json`, `encoding.json`, `packaging-request.json`, `selected_raw/`.
- `selected.avi` and reused `package/` with preserved lossless clip, decoded/raw/
  aligned frames, `sprites.png`, `atlas.json`, motion report and review template.
- `preview.gif`, `seam.png`, `verification.json`.

GIF preview contains all 20 frames at approximately 24fps, total 830ms due to GIF
10ms granularity versus the authoritative 833.333ms. Palette quantization applies
only to that preview; use PNG/FFV1/atlas timing as the source of truth.

Real FFmpeg/FFprobe and the offline package ran successfully. After decoding and
re-extraction, raw and aligned pixel equality, all atlas cells, source/output
hashes, timing, pivot/offset equality and untouched review state were verified.
Before/after hashes of the original 119 protected run files, original static
image/manifest and pipeline configuration matched. No model/network request,
new budget reservation or configuration enablement occurred.

Runtime/CLI/MCP/config code is unchanged. The previous software regression result
of 720 passed / 1 skipped at `3d974fa` is historical, not a newly rerun test here.
Current evidence is real lossless encoding/decoding/packing and preservation
verification. No new artistic quality score or approval is claimed.

Tracked changes: this report, README, CHANGELOG and the advisory-report follow-up.
Rollback: revert the documentation commit and stop using this candidate. Retain
the derived artifacts for provenance alongside the original video, unmodified
56-frame package and consumed generation reservation. No production default changed.
