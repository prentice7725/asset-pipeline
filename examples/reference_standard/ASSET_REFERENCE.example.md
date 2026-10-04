---
standard: asset-reference/v0.1
kind: ASSET_REFERENCE
status: BLOCKED_SOURCE_GAP
project_id: gochachara-godot
asset_id: example_human_soldier_front_idle
asset_type: character
output_class: PIXEL_STATIC
purpose: battle human soldier static candidate
intended_use:
  scene: combat_world
  camera: MEDIUM
  logical_viewport_px: [640, 360]
sources:
  - id: pixel_render_lock
    authority: DRIVE_ACTIVE_SOT
    uri: https://drive.google.com/file/d/1V9xb4vf0r4hRI44UF9Zz6Yc6GuEygHFz/view
    local_path: null
    locator: "#1 / #6 / #11, 2026-10-03 revision"
identity:
  canonical_traits:
    - Human Soldier is an existing battle-asset class
  visual_traits: []
subject_integrity:
  class: full_character
  identity_source: pixel_render_lock
  equipment: []
  camera_view: front
art_direction:
  primary_focus:
    - battle silhouette
  hierarchy:
    - silhouette
    - essential equipment when confirmed
    - tertiary details
  source_classification: DERIVED
delivery:
  final_frame_px: [32, 32]
  final_canvas_px: [32, 32]
  generation_canvas_px: null
  alpha: true
  anchor_px: [16, 28]
  filter: nearest
  frame_alignment: fixed_grid_no_autocrop
  file_format: PNG_RGBA
  world_density_px_per_meter: 16
reference_assets: []
forbidden_elements:
  - unauthorized redesign of canonical identity or equipment
  - unreviewed high-resolution illustration treated as final 32px pixel art
unspecified_elements:
  - approved appearance / clothing
  - approved equipment and count
  - approved palette and silhouette reference
  - direction and action coverage requirements beyond this example frame
acceptance:
  - check actual 32x32 silhouette/critical-readability at native pixel grid
  - verify alpha, frame canvas, and anchor coordinate
  - pass existing Pixel Gate and required human Static Master review
  - do not imply Godot in-game verification from an image QA result
review:
  human_approval: null
  source_verified: false
---
# 32px battle asset example

This is intentionally BLOCKED_SOURCE_GAP. The Source of Truth establishes the 32×32 frame, world density, and anchor, but this file does not claim a confirmed uniform, face, weapon or palette. An agent must read additional project SOT rather than invent them.
