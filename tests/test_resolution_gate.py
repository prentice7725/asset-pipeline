from __future__ import annotations

import json

import pytest
from PIL import Image, ImageDraw

from assetpipe._ported.pixel_gate.resolution import ResolutionGateError, record_resolution_review, run_resolution_gate


def make_resolution_fixture(directory):
    directory.mkdir(parents=True, exist_ok=True)
    source_path = directory / "resolution_source.png"
    mask_path = directory / "identity_mark_mask.png"
    image = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((48, 32, 207, 223), fill=(30, 42, 62, 255))
    draw.rectangle((72, 48, 183, 192), fill=(82, 118, 156, 255))
    draw.point((80, 50), fill=(244, 190, 70, 255))
    mask = Image.new("L", image.size, 0)
    ImageDraw.Draw(mask).point((80, 50), fill=255)
    image.save(source_path)
    mask.save(mask_path)
    return source_path, mask_path


def test_resolution_gate_emits_nearest_candidates_and_measures_feature_loss(tmp_path):
    source_path, mask_path = make_resolution_fixture(tmp_path / "fixtures")
    profile = {
        "logical_height_candidates": [128, 160, 192, 256],
        "resolution_gate": {"silhouette_min_iou": 0.9, "component_min_preservation": 0.8, "palette_min_retention": 0.5},
        "identity_features": [{"id": "insignia", "importance": "critical", "mask": str(mask_path)}],
    }
    output = tmp_path / "gate"
    report = run_resolution_gate(
        source_path,
        output,
        profile_name="test",
        profile=profile,
        project_root=tmp_path,
    )

    assert [item["logical_height"] for item in report["candidates"]] == [128, 160, 192, 256]
    assert {item["status"] for item in report["candidates"]} <= {"AUTO_FAIL", "AUTO_PASS_REVIEW_REQUIRED"}
    assert report["selected_resolution"] is None
    assert report["reviewed"] is False
    assert report["recommended_minimum_for_review"] is not None
    assert report["candidates"][0]["feature_area_preservation"][0]["disappeared"] is True
    assert report["candidates"][0]["status"] == "AUTO_FAIL"
    for height in (128, 160, 192, 256):
        with Image.open(output / f"candidate_{height}.png") as candidate:
            assert candidate.height == height
            assert candidate.width == height
    assert (output / "resolution_report.md").is_file()
    assert json.loads((output / "resolution_report.json").read_text(encoding="utf-8"))["selected_resolution"] is None


def test_resolution_review_records_explicit_choice_without_mutating_gate_report(tmp_path):
    source_path, _ = make_resolution_fixture(tmp_path / "fixtures")
    report = run_resolution_gate(
        source_path,
        tmp_path / "gate",
        profile_name="test",
        profile={"logical_height_candidates": [128, 160]},
        project_root=tmp_path,
    )
    source_report = tmp_path / "gate" / "resolution_report.json"
    original_bytes = source_report.read_bytes()
    review_path = record_resolution_review(
        source_report,
        selected_height=160,
        reason="Face and emblem retain readable pixel clusters at this size.",
        reviewed_by="artist",
        override_auto_fail=True,
    )

    review = json.loads(review_path.read_text(encoding="utf-8"))
    assert review["status"] == "SELECTED"
    assert review["selected_resolution"] == 160
    assert review["reviewed"] is True
    assert review["reviewed_by"] == "artist"
    assert review["selected_resolution"] == 160
    assert review["automatic_status"] in {"AUTO_FAIL", "AUTO_PASS_REVIEW_REQUIRED"}
    assert review["review_status"] in {"MANUAL_OVERRIDE_PASS", "MANUAL_REVIEW_PASS"}
    assert source_report.read_bytes() == original_bytes


def test_auto_fail_override_preserves_automatic_failure_and_requires_reason(tmp_path):
    source_path, _ = make_resolution_fixture(tmp_path / "fixtures")
    output = tmp_path / "gate"
    run_resolution_gate(
        source_path,
        output,
        profile_name="test",
        profile={"logical_height_candidates": [128, 160]},
        project_root=tmp_path,
    )
    report_path = output / "resolution_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["candidates"][0]["status"] = "AUTO_FAIL"
    report["candidates"][0]["automatic_status"] = "AUTO_FAIL"
    report_path.write_text(json.dumps(report), encoding="utf-8")

    with pytest.raises(ResolutionGateError, match="reason"):
        record_resolution_review(report_path, selected_height=128, reason=" ")
    with pytest.raises(ResolutionGateError, match="AUTO_FAIL"):
        record_resolution_review(
            report_path,
            selected_height=128,
            reason="The feature is visually preserved.",
        )

    review_path = record_resolution_review(
        report_path,
        selected_height=128,
        reason="No visually observed loss of cap spots, face, tunic, satchel or clasp.",
        override_auto_fail=True,
    )
    review = json.loads(review_path.read_text(encoding="utf-8"))
    assert review["automatic_status"] == "AUTO_FAIL"
    assert review["review_status"] == "MANUAL_OVERRIDE_PASS"
    assert review["selected_resolution"] == 128
    assert review["reason"]
