from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_report(report: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "report.json"
    markdown_path = output_dir / "report.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, markdown_path


def render_markdown(report: dict[str, Any]) -> str:
    resolution = report["resolution"]
    alpha = report["alpha"]
    palette = report["palette"]
    gradient = report["gradient_suspicion"]
    antialias = report["anti_alias_suspicion"]
    silhouette = report["silhouette"]
    lines = [
        "# Pixel Gate Report",
        "",
        f"- **Status:** `{report['status']}`",
        *([f"- **Gate role:** `{report['gate_role']}`"] if report.get("gate_role") else []),
        f"- **Image:** `{report['image']}`",
        f"- **Resolution:** {resolution['width']} × {resolution['height']}",
        f"- **Target match:** {resolution['matches_target']}",
        f"- **Unique colors:** {palette['unique_color_count']} / {palette['max_colors']}",
        f"- **Semi-transparent pixels:** {alpha['semi_transparent_pixels']}",
        f"- **Off-palette pixels:** {palette['off_palette_pixel_count']}",
        f"- **Mean nearest palette distance:** {palette['distance_to_allowed_palette']['mean_nearest_rgb_distance']}",
        f"- **Gradient suspicion:** `{gradient['level']}` (small RGB-step ratio {gradient['small_rgb_step_ratio']})",
        f"- **Anti-alias suspicion:** `{antialias['level']}` ({antialias['suspected_pixels']} suspected pixels)",
        "",
        "## Silhouette",
        "",
        f"- Measurable: {silhouette['measurable']} ({silhouette['method']})",
        f"- Connected components: {silhouette['connected_component_count']}",
        f"- Tiny detached pixels: {silhouette['isolated_pixel_count']}",
        "",
    ]
    for key, heading in (("failure", "Failures"), ("fix", "Potential safe fixes"), ("review", "Review items")):
        reasons = report["reasons"][key]
        if reasons:
            lines.extend([f"## {heading}", ""])
            lines.extend(f"- {reason}" for reason in reasons)
            lines.append("")
    lines.extend(
        [
            "## Interpretation",
            "",
            "This report analyzes the provided Pixel Candidate. It does not certify visual quality or replace review in Aseprite.",
            "Gradient, anti-alias, and detached-cluster checks are heuristic indicators; inspect ambiguous results manually.",
            "",
        ]
    )
    return "\n".join(lines)
