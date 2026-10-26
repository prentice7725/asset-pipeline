# Fox motion advisory review — 2026-10-26

Branch: `codex/motion-advisory-review-20261026`, base `1594087`.
Scope: review the existing [one-request research result](MOTION_REAL_E2E_20261026.md).
**ADVISORY_FIXES_REQUIRED / HUMAN_REVIEW_REQUIRED**. Zero generations and no asset
correction, alpha extraction, frame selection, engine import or human approval.

## Findings and correction order

All 56 raw frames were inspected in two chronological contact sheets, with
enlarged top-border details and a last/first-frame comparison. Raw/aligned
side-by-side animation is supplied for human motion/pivot review. Static frame
inspection does not establish foot contact or full-speed animation approval.

| Order | Finding and evidence | Recommended next work |
| --- | --- | --- |
| 1 | The last frame is mid-step; frame 1 returns to a standing pose. The full 56-frame clip does not have an established seamless walk boundary. | Review a complete interior left/right walk cycle, then create a separate trimmed candidate with explicit source indices/timing. Inspect the new seam at normal speed before acceptance. Do not remove frames solely by perceptual similarity or invent intermediate poses. No trimming was performed here. |
| 2 | Existing subject detection reports top-border contact in 12/56 frames; enlarged views put the ear tip at the top edge. | Review those source pixels for clipping and required headroom. Padding/repositioning may prevent further clipping but cannot reconstruct any already missing ear pixels. Do not redraw identity/silhouette automatically. No missing anatomy is asserted solely from the bounding box. |
| 3 | Exported pivot is fixed `(256,510)` after bounding-box alignment. The box includes the asymmetric tail; it is not an anatomical root or support-foot tracker. | Inspect the side-by-side preview and agree on the intended body/root/contact anchor. Compare a separate pivot candidate in-engine before accepting it. A fixed metadata pivot is not proof that the feet do not slide. |
| 4 | Orange fur, red scarf, scout clothing, backpack, tail and overall silhouette remain visually recognizable across inspected frames. Hands mostly remain at the hips while the legs step. | Preserve the current design. Human review should decide whether this stylized movement fits the requested game; natural arm swing is an art-direction choice, not a demonstrated technical defect. No numeric identity score or human identity approval is claimed. |
| 5 | Video/frame alpha remains fully opaque. | Review background removal only after retaining the original and identifying the motion/cycle candidate. White muzzle, tail tip and highlights require care; no transparency was generated or approved in this review. |

Recommendation: hold direct game-loop use pending seam, headroom and anchor review.
This is an advisory disposition, not a failed generation or change to the
technical E2E PASS. Original `review.json` remains untouched, `REVIEW_REQUIRED`,
reviewer null, every check null. `game_ready=false` remains unchanged.

## Measurements and their limits

All frame numbers below are **1-based** source/sample indices. Their time is
`(index-1)/24` seconds; the earlier E2E preview used 0-based image labels.

Top-border contacts: **9, 10, 18, 19, 20, 27, 28, 29, 38, 47, 48, 49**.
These are `subject_bbox.y=0` flags from the existing extractor, not twelve proven
anatomical losses. Other frames have top bbox y between 2 and 10 pixels. No flag
was suppressed or changed to a pass.

| Diagnostic | Actual value | Interpretation |
| --- | --- | --- |
| Alignment dx / dy | 40..46 / 14..16 pixels | Recorded translations; not measured anatomical jitter |
| Largest adjacent dx / dy change | 3 / 1 pixels | Alignment changes can affect perceived motion; not a foot-slide estimate |
| Exported pivot | `(256,510)` | Existing canvas/bbox convention, requires review |
| Raw adjacent full-canvas RGB MAE median / max | 8.207792 / 15.228038 | Pixel-change measurements, 0..255 scale, background included |
| Raw last→first RGB MAE | 19.830325 | Larger than any measured raw adjacent step; supports inspecting the visibly different endpoint pose |
| Aligned adjacent RGB MAE median / max | 8.893935 / 17.221129 | Same diagnostic after existing alignment |
| Aligned last→first RGB MAE | 20.848200 | Not an animation quality score or approval threshold |
| Existing cycle proxy, full 56 frames | 20 samples ≈0.833333 seconds | Minimum mean RGB crop difference over lags 3..28; not semantic phase/left-right truth or an approved crop |
| Existing blur flags | 56 KEEP | Sharpness only; does not approve the motion |
| Existing near-duplicate flags | 47; 9 selected candidates | Coarse perceptual similarity; all 56 frames retained |
| Existing automatic usability state | `LIMITED_REVIEW_REQUIRED` | Retained; not converted into an art PASS |

The existing ported `_metrics` and `_cycle_period` functions were reused on all
56 chronological frames without altering the extraction report or selection flags.
`foot_baseline_y` in those metrics is a **bbox-bottom proxy**, not tracked ground
contact. Loop difference is calculated separately on raw/aligned full RGB canvases;
no learned quality model, arbitrary acceptance cutoff or automatic cycle selection.
Foot sliding, root stability and manual correction time remain **NOT_MEASURED**.
No quality improvement is claimed because no correction was made.

## Evidence and validation

Ignored artifacts relative to this worktree:
`workspace/motion-advisory-review-20261026/evidence/` contains:

- `all-frames-1.png`, `all-frames-2.png`: every raw frame in order.
- `loop-seam.png`: raw/aligned frames 55, 56, 1, 2 for direct seam comparison.
- `boundary-details.png`: enlarged top-border inspection crops, not asset edits.
- `raw-vs-aligned.gif`: all 56 frames, raw versus aligned, exported pivot marked
  in red. GIF palette quantization and 10ms timing granularity make this a preview
  only (2330ms versus the MP4's ~2333.333ms); original MP4/PNGs remain authoritative.
- `existing-metric-proxies.json`, `review-metrics.json`: method/lag outputs,
  measured differences, source indices, preservation hashes and explicit limits.

The dated `review_existing.py` and `review.log` are in the parent artifact directory.
Source video SHA-256 remains
`2b705e1330dfcf5259541142dc18044f3d4832b6e7d42e83b089e09dcf34fd4d`.
Before/after hashes of **119 protected files** match: execution receipt, original
video, extraction/package/review manifests, atlas PNG/JSON and all 56 raw plus
56 aligned frames. Each frame was also checked against its recorded atlas hash.
The original static source image/manifest and disabled research configuration
were independently rechecked against their preserved pre-execution snapshots.

No runtime/configuration code changes occurred. The previous full software suite
was 720 passed / 1 skipped at `3d974fa`; it is historical and was not rerun for
this review. Current validation comprises source/frame hash checks, preserved
review state and read-only diagnostic execution; it is not human Aseprite review.
No generation, network submission, new budget reservation, SOT/Golden change,
provider activation or engine test occurred.

Changed tracked files: this report, README, CHANGELOG and a follow-up link in the
real E2E report. Rollback: revert the documentation commit. Preserve original
artifacts, consumed authorization/budget records and these advisory diagnostics.
Any later corrections must create separate candidates and retain source mappings;
they must not silently replace this run or claim human approval.
