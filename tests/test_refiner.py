import json
from pathlib import Path

from PIL import Image

from assetpipe._ported.pixel_gate.refiner import refine_image

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "tests" / "assets"


def test_normal_true_pixel_art_is_unchanged(tmp_path: Path) -> None:
    output = tmp_path / "true-art"
    report = refine_image(
        ASSETS / "true_pixel_art.png",
        output,
        profile="default",
        analyzer_max_colors=32,
        analyzer_target_size=(64, 64),
    )
    assert report["status"] == "PASS"
    assert report["changed_pixel_count"] == 0
    assert report["input_sha256"] == report["output_sha256"]
    assert report["operations"][0]["applied"] is False
    assert all((output / name).is_file() for name in ("input.png", "refined.png", "diff.png", "refine_report.json", "refine_report.md"))


def test_downscaled_illustration_palette_projection_never_certifies_true_art(tmp_path: Path) -> None:
    palette = json.loads((ROOT / "config" / "palettes" / "character_basic.json").read_text(encoding="utf-8"))["colors"]
    report = refine_image(
        ASSETS / "downscaled_illustration.png",
        tmp_path / "downscaled",
        profile="default",
        palette=palette,
        analyzer_max_colors=32,
        analyzer_target_size=(64, 64),
    )
    assert report["palette_pixels_changed"] > 0
    assert report["changed_pixel_count"] > 0
    assert report["after_analysis"]["palette"]["unique_color_count"] <= len(palette)
    assert report["status"] in {"REVIEW_REQUIRED", "FAIL"}
    assert report["status"] != "PASS"


def test_binary_alpha_threshold_and_rgb_mode_are_preserved_when_possible(tmp_path: Path) -> None:
    rgb_path = tmp_path / "opaque.png"
    Image.new("RGB", (8, 8), (20, 40, 60)).save(rgb_path)
    report = refine_image(rgb_path, tmp_path / "opaque-out", profile="default")
    assert report["alpha_pixels_changed"] == 0
    assert Image.open(report["output"]).mode == "RGB"

    rgba_path = tmp_path / "semi.png"
    rgba = Image.new("RGBA", (8, 8), (20, 40, 60, 255))
    rgba.putpixel((3, 3), (20, 40, 60, 127))
    rgba.save(rgba_path)
    alpha_report = refine_image(rgba_path, tmp_path / "semi-out", profile="default", alpha_threshold=128)
    assert alpha_report["alpha_pixels_changed"] == 1
    assert Image.open(alpha_report["output"]).getpixel((3, 3))[3] == 0


def test_nearest_resize_trim_and_bottom_anchor_pad(tmp_path: Path) -> None:
    report = refine_image(
        ASSETS / "true_pixel_art.png",
        tmp_path / "resize-pad",
        profile="default",
        resize=(32, 32),
        canvas=(40, 50),
        anchor="bottom-anchor",
    )
    assert report["resize"] == {"before": [64, 64], "after": [32, 32], "filter": "NEAREST"}
    assert report["canvas"]["after"] == [40, 50]
    assert report["operations"][1]["parameters"]["filter"] == "NEAREST"
    assert report["operations"][2]["parameters"]["paste_offset"] == [4, 18]


def test_only_explicit_isolated_pixel_coordinates_are_considered(tmp_path: Path) -> None:
    source = Image.new("RGBA", (9, 9), (40, 100, 70, 255))
    source.putpixel((4, 4), (255, 0, 0, 255))
    source_path = tmp_path / "speck.png"
    source.save(source_path)
    report = refine_image(
        source_path,
        tmp_path / "speck-out",
        profile="default",
        isolated_pixel_coordinates=[(4, 4)],
    )
    assert report["cleanup_decisions"][0]["removed"] is True
    assert Image.open(report["output"]).getpixel((4, 4)) == (40, 100, 70, 255)
    assert report["changed_pixel_count"] == 1


def test_transparent_trim_and_center_pad_are_recorded(tmp_path: Path) -> None:
    source = Image.new("RGBA", (12, 10), (0, 0, 0, 0))
    for y in range(2, 7):
        for x in range(3, 9):
            source.putpixel((x, y), (220, 40, 60, 255))
    source_path = tmp_path / "trim.png"
    source.save(source_path)
    report = refine_image(
        source_path,
        tmp_path / "trim-out",
        profile="default",
        trim=True,
        canvas=(10, 9),
        anchor="center",
    )
    assert report["operations"][1]["parameters"]["bounds_before_crop"] == [3, 2, 9, 7]
    assert report["operations"][2]["parameters"]["paste_offset"] == [2, 2]
    assert report["canvas"]["after"] == [10, 9]
