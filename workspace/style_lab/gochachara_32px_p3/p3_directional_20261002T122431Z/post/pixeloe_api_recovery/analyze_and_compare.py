"""Run the unchanged Pixel Gate and make native / 4x nearest comparison sheets."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from assetpipe._ported.pixel_gate.analyzer import analyze_image


RUN_ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BASELINE = (
    RUN_ROOT
    / "post"
    / "G01"
    / "south_front"
    / "P1_NN_THEN_MEDIANCUT_32"
    / "32px_opaque_white.png"
)
INPUT_CROP = RUN_ROOT / "post" / "pixelOE_inputs" / "G01_1_south_front.png"
RAW = RUN_ROOT / "generated" / "G01" / "83aacbc7_000.png"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def make_sheet(items: list[tuple[str, Path]], path: Path, scale: int) -> None:
    images = []
    for label, image_path in items:
        with Image.open(image_path) as source:
            image = source.convert("RGB")
        if image.size != (32, 32):
            raise ValueError(f"not a logical 32x32 image: {image_path}={image.size}")
        if scale != 1:
            image = image.resize((32 * scale, 32 * scale), Image.Resampling.NEAREST)
        images.append((label, image))

    font = ImageFont.load_default()
    gap = 8
    margin = 8
    label_h = 18
    panel_w = 32 * scale
    panel_h = 32 * scale
    label_w = max(
        ImageDraw.Draw(Image.new("RGB", (1, 1))).textbbox((0, 0), label, font=font)[2]
        for label, _ in images
    )
    cell_w = max(panel_w, label_w)
    width = margin * 2 + len(images) * cell_w + (len(images) - 1) * gap
    height = margin * 2 + label_h + panel_h
    sheet = Image.new("RGB", (width, height), (238, 238, 238))
    draw = ImageDraw.Draw(sheet)
    for index, (label, image) in enumerate(images):
        x = margin + index * (cell_w + gap)
        draw.text((x, margin), label, fill=(0, 0, 0), font=font)
        sheet.paste(image, (x + (cell_w - panel_w) // 2, margin + label_h))
    sheet.save(path, format="PNG", optimize=False)


def main() -> None:
    candidates = [
        ("P1 NN+MC32", BASELINE),
        ("PixelOE t0", OUT / "pixeloe_t0_32x32.png"),
        ("PixelOE t2", OUT / "pixeloe_t2_32x32.png"),
    ]
    gate_results = []
    for label, image_path in candidates:
        result = analyze_image(
            image_path,
            max_colors=32,
            target_width=32,
            target_height=32,
            gradient_threshold=0.18,
        )
        result["comparison_label"] = label
        result["sha256"] = sha256(image_path)
        result["art_review"] = "PENDING"
        result["approval"] = "NOT_APPROVED"
        gate_path = OUT / ("gate_" + label.lower().replace("+", "_").replace(" ", "_") + ".json")
        gate_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        gate_results.append(
            {
                "label": label,
                "path": str(image_path.relative_to(RUN_ROOT)),
                "sha256": result["sha256"],
                "size": [result["resolution"]["width"], result["resolution"]["height"]],
                "unique_visible_colors": result["palette"]["unique_color_count"],
                "alpha": result["alpha"],
                "gradient_suspicion": result["gradient_suspicion"]["level"],
                "anti_alias_suspicion": result["anti_alias_suspicion"]["level"],
                "silhouette": result["silhouette"],
                "pixel_gate_status": result["status"],
                "pixel_gate_reasons": result["reasons"],
                "art_review": "PENDING",
                "approval": "NOT_APPROVED",
            }
        )

    make_sheet(candidates, OUT / "comparison_native_1x.png", 1)
    make_sheet(candidates, OUT / "comparison_nearest_4x.png", 4)
    sheet_records = []
    for path in (OUT / "comparison_native_1x.png", OUT / "comparison_nearest_4x.png"):
        with Image.open(path) as image:
            sheet_records.append(
                {
                    "path": path.name,
                    "size": list(image.size),
                    "sha256": sha256(path),
                    "panel_pixels": "native logical 32x32" if "native" in path.name else "integer nearest-neighbor 4x; display only",
                }
            )

    report = {
        "experiment": "P3 PixelOE API recovery / one existing G01 south-front crop",
        "source_raw": str(RAW.relative_to(RUN_ROOT)),
        "source_raw_sha256": sha256(RAW),
        "source_crop": str(INPUT_CROP.relative_to(RUN_ROOT)),
        "source_crop_sha256": sha256(INPUT_CROP),
        "new_generation_requests": 0,
        "pixel_gate": {
            "implementation": "assetpipe._ported.pixel_gate.analyzer.analyze_image",
            "unchanged_thresholds": {
                "max_colors": 32,
                "gradient_threshold": 0.18,
                "target_resolution": [32, 32],
            },
            "results": gate_results,
            "technical_pass_is_not_production_success": True,
        },
        "contact_sheets": sheet_records,
        "review": {
            "quality_validation": "FAILED_PENDING_HUMAN_REVIEW",
            "semantic_art_review": "PENDING",
            "static_master_approvals": 0,
            "golden_recipe_approvals": 0,
        },
        "limitations": [
            "The source generation prompt requested a three-view sheet; repeated same-facing characters were observed in the raw output.",
            "PixelOE outputs preserve the source RGB white matte; no alpha was synthesized.",
            "The 4x sheet is display-only and was not used for measurements.",
            "1x identity, equipment readability, semantic fidelity, silhouette quality and matte edge require human review.",
        ],
    }
    (OUT / "comparison_results.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
