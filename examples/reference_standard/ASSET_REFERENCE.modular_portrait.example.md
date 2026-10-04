---
standard: asset-reference/v0.1
kind: ASSET_REFERENCE
status: BLOCKED_SOURCE_GAP
project_id: isekai-immigration
asset_id: example_actor_head_base
asset_type: modular_portrait_part
output_class: NONPIXEL_IMAGE
purpose: transparent head_base part of one actor modular bust
intended_use:
  scene: examiner_office_portrait
  render_role: portrait_part
sources:
  - id: modular_portrait_master
    authority: DRIVE_ACTIVE_SOT
    uri: https://drive.google.com/file/d/18CHZY_PP93CwHPZ6lQltWFiB00m2bPHw/view
    local_path: null
    locator: "#4 / #5 / #12 / QC, v0.1"
identity:
  canonical_traits: []
  visual_traits: []
art_direction:
  primary_focus:
    - actor identity consistency across modular combinations
  hierarchy:
    - stable face structure
    - clean neck/collar seam
    - low noise in nonfocal surfaces
  source_classification: DERIVED
delivery:
  final_canvas_px: [1212, 1300]
  generation_canvas_px: null
  alpha: true
  layer_slot: head_base
  canvas_alignment: shared_absolute_canvas
  underpaint_bleed_px: 12
  file_format: PNG_RGBA
  anchor_names:
    - head_center
    - neck_center
    - shoulder_left
    - shoulder_right
layer_plan:
  required_slot_content:
    - skin and ears
    - nose and face outline
    - neck through inside of collar
  explicitly_separate:
    - expression
    - hair_back
    - hair_front
reference_assets: []
forbidden_elements:
  - placing independent expression features inside head_base
  - opaque white or checkerboard in place of genuine transparent alpha
  - independent auto-crop or scaling of this modular part
unspecified_elements:
  - actor identity and approved base reference
  - part-specific exact anchor coordinates
  - project style lock verification in current SOT
acceptance:
  - check genuine 1212x1300 RGBA transparency
  - check shared canvas and 12px underpaint seam rules
  - check clean composite with expression and hair layers
  - check face identity stability after costume/expression replacement
  - do not treat single-part QA as owner-approved Golden Actor
review:
  human_approval: null
  source_verified: false
---
# Modular portrait example

Illustrates the same contract as the 32px combat example without applying pixel-grid/nearest-neighbor rules to a nonpixel modular portrait. BLOCKED_SOURCE_GAP until identity and reference details are verified in current project SOT. This document does not create or approve a new actor.
