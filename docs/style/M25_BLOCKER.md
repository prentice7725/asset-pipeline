# M2.5 independent experiment results — 2026-10-01

Base main: b92b654. Current cohort: workspace/style_lab/cohorts/20261001T131720658569Z. Its original 12 PREPARED samples, seed 7725, M2.6 recipes and unused budget were reused; no replacement cohort or duplicate generation was created.

## Independent path states

Historical eight-frame artifact RGBA equivalence: PASS, historical comparison only. Current PIXEL_ANIMATION E2E: NOT_RUN; no approved compatible Static Master exists. PIXEL_STATIC and NONPIXEL_IMAGE experiments now use their own model/workflow preflight and output-specific QA, independent of animation approval. Approval.py and exact direct-profile scope were not weakened.

Actual generation: 12/12 requests, 12 unique ComfyUI prompt IDs, 12 original PNGs. Durable cohort reservation was written before every dispatch. No retry, fallback, extra request or automatic approval. Local currency cost and GPU energy remain NOT_MEASURED; generation and total timings are retained per sample.

NONPIXEL_IMAGE: 4/4 basic image QA PASS, all CANDIDATE_READY_REVIEW_REQUIRED. This checks technical image constraints, not semantic or artistic quality. In particular the clean-anime character contains two views although its Brief asks for one character; this agent visual observation requires human review and is not a canon PASS.

PIXEL_STATIC: 0/8 Pixel Gate PASS. All eight raw images were generated, but color budgets exceeded 32 and gradient suspicion failed. Original PNGs, analyzer/refiner/gate reports and hashes are preserved. Safe refiner did not change palettes or logical size. Resolution Gate and Aseprite were not reached for these failed candidates. No failed candidate may be approved as a Static Master without a separately authorized successful path.

## Model evidence

Running ComfyUI command line references inst-1789908464528.yaml, which configures C:/Users/seung/AppData/Local/Comfy-Desktop/ComfyUI-Shared/models as the default shared model root. SHA256 was computed from actual bytes for six checkpoint/text-encoder/VAE files, crosschecked with live server inventory and node availability. No duplicate dependency files exist in the installation-local models folder. The cohort stores model hashes, paths, sizes and timestamps; generation.json stores actual workflow hash, prompt/spec/parameters and prompt ID. These local hashes do not claim reproduction of external source examples or verified source-model versions. The experiment workflows use no LoRA; none was added or downloaded.

## Legacy review remains unapproved

The existing sword_warrior 128x128 image remains LEGACY_REGRESSION_FIXTURE. Its technical run remains EXPORT_READY_REVIEW_REQUIRED. The user's 128x128 resolution selection and actual Aseprite RGBA roundtrip PASS are retained, but human_aseprite_review.json still records approval hold. The later human art review explicitly does not approve it as a Static Master: excess detail, disorganized clusters, unclear body/equipment boundaries and animation structure concerns. This feedback is separately preserved in human_art_review.json. No approval_record.json exists; no Golden or project Visual SOT promotion occurred.

Only actual human Aseprite review and formal approval of a compatible Static Master may unlock animation. The existing blue_tunic_white_matte_v1 scope is not generalized to these new characters. New Static Master candidates require a gallery-based human visual review before further approval steps; technical failure cannot be bypassed by visual approval.

## Review artifacts

comparison.json and comparison.md contain technical status, palette/alpha metrics, error reasons, timing and postprocessing estimates separately from art review. previews/pixel_candidates_native_1x.png shows original pixels at native 1x in the saved file (viewers may scale the display). previews/nonpixel_candidates_preview.png is a thumbnail contact sheet; inspect original PNGs for detail. New candidates remain NOT_REVIEWED on readability, silhouette, color clusters, outline, equipment separation, transparent boundary and postprocessing cost. No quality scores or model preference are fabricated.

Regression tests: 207 passed, 0 failures/errors/skips; regression_independent.xml is retained. Golden Recipe count: 0. Tile/UI role QA and in-game fit remain unverified. Next work must follow actual human art feedback and explicit additional experiment authorization; this initial 12-request budget is exhausted.
