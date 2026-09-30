from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from assetpipe._ported.pixel_gate.subject_refiner import (
    delta_e76,
    extract_master_foreground_palette,
    refine_subject_image,
    separate_candidate_foreground,
)


def _make_candidate(path: Path) -> None:
    image = Image.new("RGBA", (40, 40), (255, 255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((12, 4, 26, 32), fill=(255, 0, 0, 255))
    draw.rectangle((16, 12, 22, 18), fill=(245, 20, 10, 255))
    image.save(path)


def _make_master(path: Path) -> list[str]:
    image = Image.new("RGBA", (40, 40), (255, 255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((14, 5, 25, 34), fill=(255, 0, 0, 255))
    draw.rectangle((18, 13, 21, 19), fill=(128, 0, 0, 255))
    image.save(path)
    return ["#FF0000", "#800000"]


def test_background_pixels_are_excluded_from_refinement_metrics_and_projection(tmp_path: Path) -> None:
    source = tmp_path / "candidate.png"
    master = tmp_path / "master.png"
    _make_candidate(source)
    palette = _make_master(master)
    original = source.read_bytes()

    report = refine_subject_image(source, master, tmp_path / "refine", profile_name="fixture", palette_colors=palette)

    assert source.read_bytes() == original
    assert report["changes"]["background_changed_pixels"] == 0
    assert report["changes"]["background_pixel_count_after_normalization"] > 0
    assert report["changes"]["foreground_pixel_count_after_normalization"] < 40 * 40
    assert report["background"]["background_pixels_excluded_from_palette"] is True
    with Image.open(report["artifacts"]["foreground_refined"]) as refined:
        assert refined.getpixel((0, 0))[3] == 0
        foreground_colors = {pixel[:3] for pixel in refined.get_flattened_data() if pixel[3]}
    assert foreground_colors <= {(255, 0, 0), (128, 0, 0)}


def test_occupancy_anchor_and_isotropic_nearest_normalization(tmp_path: Path) -> None:
    source = tmp_path / "candidate.png"
    master = tmp_path / "master.png"
    _make_candidate(source)
    palette = _make_master(master)

    report = refine_subject_image(source, master, tmp_path / "refine", profile_name="fixture", palette_colors=palette)
    normalized = report["subject_normalization"]
    reference = normalized["reference_bbox_xyxy"]
    left, _top, right, bottom = reference
    expected_anchor = [((left + right) / 2) / 40, bottom / 40]
    assert normalized["target_anchor_bottom_center_ratio"] == pytest.approx(expected_anchor)
    assert normalized["resize_filter"] == "NEAREST"
    target_height = normalized["resized_bbox"][3] - normalized["resized_bbox"][1]
    assert normalized["aspect_ratio_after"] == pytest.approx(normalized["aspect_ratio_before"], abs=1 / target_height)

    x1, y1, x2, y2 = normalized["resized_bbox"]
    assert ((x1 + x2) / 2) / 40 == pytest.approx(expected_anchor[0], abs=1 / 40)
    assert y2 / 40 == pytest.approx(expected_anchor[1], abs=1 / 40)


def test_master_palette_extraction_and_palette_lock(tmp_path: Path) -> None:
    master = Image.new("RGBA", (20, 20), (255, 255, 255, 255))
    colors = [tuple(int(color[index:index + 2], 16) for index in (1, 3, 5)) for color in [
        f"#{value:06X}" for value in range(17)
    ]]
    for index, color in enumerate(colors):
        master.putpixel((2 + index, 4), (*color, 255))
    master_path = tmp_path / "master.png"
    master.save(master_path)
    extracted = extract_master_foreground_palette(master_path)
    assert extracted["color_count"] == 17
    assert extracted["background_color_excluded"] == "#FFFFFF"
    assert len(extracted["colors"]) == 17

    source = tmp_path / "candidate.png"
    _make_candidate(source)
    palette = _make_master(tmp_path / "palette_master.png")
    report = refine_subject_image(
        source,
        tmp_path / "palette_master.png",
        tmp_path / "locked",
        profile_name="fixture",
        palette_colors=palette,
    )
    with Image.open(report["artifacts"]["foreground_refined"]) as refined:
        assert {pixel[:3] for pixel in refined.get_flattened_data() if pixel[3]} <= {(255, 0, 0), (128, 0, 0)}


def test_delta_e_metrics_use_cie76_and_are_reported_for_foreground(tmp_path: Path) -> None:
    assert delta_e76((0, 0, 0), (255, 255, 255)) == pytest.approx(100.0, abs=0.05)
    source = tmp_path / "candidate.png"
    master = tmp_path / "master.png"
    _make_candidate(source)
    palette = _make_master(master)
    report = refine_subject_image(source, master, tmp_path / "refine", profile_name="fixture", palette_colors=palette)
    metrics = report["foreground_palette_statistics"]
    assert 0 < metrics["exact_palette_match_ratio_before_projection"] < 1
    for metric in (
        "mean_foreground_deltaE",
        "median_foreground_deltaE",
        "p95_foreground_deltaE",
        "max_foreground_deltaE",
    ):
        assert metrics[metric] >= 0
    assert metrics["max_foreground_deltaE"] > 0


def test_bootstrap_separation_does_not_assume_master_palette(tmp_path: Path) -> None:
    source = tmp_path / "candidate.png"
    _make_candidate(source)
    report = separate_candidate_foreground(source, tmp_path / "separated")
    assert report["status"] == "BACKGROUND_SEPARATED_NO_MASTER"
    assert report["master_palette_state"] == "SKIPPED_NO_APPROVED_STATIC_MASTER"
    assert report["occupancy_normalization_state"] == "SKIPPED_NO_APPROVED_STATIC_MASTER"
    assert Path(report["artifacts"]["candidate_preserved"]).is_file()
    with Image.open(report["artifacts"]["foreground_only"]) as foreground:
        assert foreground.getpixel((0, 0))[3] == 0
    saved = json.loads((tmp_path / "separated" / "foreground_separation_report.json").read_text(encoding="utf-8"))
    assert saved["source_preserved"] is True
