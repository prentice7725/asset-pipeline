from pathlib import Path

from assetpipe._ported.pixel_gate.analyzer import analyze_image
from assetpipe._ported.pixel_gate.report import write_report

ASSETS = Path(__file__).resolve().parent / "assets"


def test_true_pixel_art_passes_pixel_gate() -> None:
    report = analyze_image(ASSETS / "true_pixel_art.png", max_colors=32, target_width=64, target_height=64)
    assert report["status"] == "PASS"
    assert report["palette"]["unique_color_count"] <= 32
    assert report["alpha"]["semi_transparent_pixels"] == 0
    assert report["gradient_suspicion"]["level"] != "HIGH"


def test_smoothed_downscaled_illustration_fails_pixel_gate() -> None:
    report = analyze_image(ASSETS / "downscaled_illustration.png", max_colors=32, target_width=64, target_height=64)
    assert report["status"] == "FAIL"
    assert report["palette"]["unique_color_count"] > 32
    assert report["gradient_suspicion"]["level"] == "HIGH"
    assert report["anti_alias_suspicion"]["level"] == "HIGH"


def test_target_resolution_and_palette_violations_are_reported() -> None:
    report = analyze_image(
        ASSETS / "true_pixel_art.png",
        max_colors=32,
        allowed_palette=["#FFFFFF"],
        target_width=32,
        target_height=32,
    )
    assert report["status"] == "FAIL"
    assert report["resolution"]["matches_target"] is False
    assert report["palette"]["off_palette_pixel_count"] > 0


def test_reports_write_json_and_markdown(tmp_path: Path) -> None:
    report = analyze_image(ASSETS / "true_pixel_art.png", max_colors=32, target_width=64, target_height=64)
    json_path, markdown_path = write_report(report, tmp_path / "report")
    assert '"status": "PASS"' in json_path.read_text(encoding="utf-8")
    assert "# Pixel Gate Report" in markdown_path.read_text(encoding="utf-8")
