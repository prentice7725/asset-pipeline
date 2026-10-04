---
standard: asset-reference/v0.1
kind: PROJECT_PROFILE
status: EXAMPLE_ONLY
project_id: gochachara-godot
sources:
  - id: pixel_render_lock
    authority: DRIVE_ACTIVE_SOT
    uri: https://drive.google.com/file/d/1V9xb4vf0r4hRI44UF9Zz6Yc6GuEygHFz/view
    local_path: null
    locator: "#11 / r2026-10-03"
  - id: uiux_display
    authority: DRIVE_ACTIVE_SOT
    uri: https://drive.google.com/file/d/1bYu1pfGRxGHUaLawZtRMWUQOLxV3n2Ga/view
    local_path: null
    locator: "Display Master v1.0"
visual_sot:
  source_id: pixel_render_lock
  style_lock_path: null
  approval_evidence: null
renderer:
  engine: Godot 4 .NET
  target: desktop
display_contract:
  root_ui_design_px: [1280, 720]
  combat_world_logical_px: [640, 360]
  world_density_px_per_meter: 16
output_policies:
  battle_humanoid:
    output_class: PIXEL_STATIC
    final_frame_px: [32, 32]
    alpha: true
    anchor_px: [16, 28]
    filter: nearest
    camera_scales: [0.5, 1, 2]
    runtime_verified: false
  environment_tile:
    output_class: PIXEL_STATIC
    final_frame_px: [16, 16]
    alpha: null
    filter: nearest
approval_evidence: null
---
# Project profile example

This is an EXAMPLE, not an ACTIVE project SOT or production-ready Style Pack.
The canonical numbers above are cited from the referenced Drive design documents.
Before generation, read the current sources, populate verified local_path entries under MCP source_roots, recheck version/authority, and confirm any asset-specific identity details.
Do not convert the current unspecified style into an invented style.
