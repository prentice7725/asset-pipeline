from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from assetpipe._ported.errors import ConfigurationError
from assetpipe._ported.motion_extractor.keyframes import plan_keyframes, select_keyframes


def _motion_report(tmp_path: Path) -> Path:
    frames = []
    for index in range(16):
        image = Image.new("RGB", (80, 80), (244, 240, 229))
        draw = ImageDraw.Draw(image)
        draw.rectangle((25, 8, 54, 53), fill=(78, 105, 38))
        gait = index % 8
        if gait in {1, 2, 3}:
            draw.rectangle((24 - (gait % 2), 53, 38, 62), fill=(83, 48, 25))
        else:
            draw.rectangle((40 + (gait % 2), 53, 55, 62), fill=(83, 48, 25))
        path = tmp_path / f"aligned_{index + 1:02d}.png"
        image.save(path)
        frames.append({
            "sample_index": index + 1,
            "source_frame_index": index * 2 + 1,
            "timestamp_seconds": round(index / 12, 6),
            "raw_path": str(path),
            "aligned_path": str(path),
            "subject_bbox": {"x": 25, "y": 8, "width": 30, "height": 55},
            "alignment_offset": [0, 0],
            "blur_score": 70.0 - index,
            "blur_status": "KEEP",
            "selected_candidate": True,
        })
    path = tmp_path / "motion_report.json"
    path.write_text(json.dumps({"source": {"path": "walk.mp4", "sha256": "fixture"}, "duration_seconds": 4 / 3, "sample_fps": 12, "sampled_frame_count": 16, "frames": frames}), encoding="utf-8")
    return path


def test_plan_keyframes_groups_candidates_and_explicit_selection_writes_references(tmp_path):
    report_path = _motion_report(tmp_path)
    plan = plan_keyframes(report_path, tmp_path / "plan")

    assert plan["status"] == "WAITING_FOR_KEYFRAME_REVIEW"
    assert plan["candidate_count"] == 16
    assert plan["cycle_estimate"]["estimated_period_samples"] == 8
    assert [group["phase"] for group in plan["semantic_groups"]] == [
        "CONTACT_A", "DOWN_A", "PASSING_A", "UP_A", "CONTACT_B", "DOWN_B", "PASSING_B", "UP_B"
    ]
    assert all(len(group["candidates"]) == 3 for group in plan["semantic_groups"])
    assert (tmp_path / "plan" / "walk_phase_contact_sheet.png").is_file()

    selection_path = tmp_path / "selection.json"
    selection_path.write_text(json.dumps({"action": "walk", "selection": [
        {"phase": phase, "source_frame": index}
        for index, phase in enumerate(("CONTACT_A", "DOWN_A", "PASSING_A", "UP_A", "CONTACT_B", "DOWN_B", "PASSING_B", "UP_B"), 1)
    ]}), encoding="utf-8")
    selected = select_keyframes(tmp_path / "plan" / "walk_keyframe_plan.json", selection_path, tmp_path / "selected")

    assert selected["status"] == "KEYFRAMES_SELECTED"
    assert selected["frame_count"] == 8
    assert len(list((tmp_path / "selected" / "walk_reference").glob("*.png"))) == 8
    assert (tmp_path / "selected" / "walk_reference_contact_sheet.png").is_file()
    assert json.loads((tmp_path / "selected" / "walk_keyframes.json").read_text(encoding="utf-8"))["selection"][0]["phase"] == "CONTACT_A"


def test_keyframe_selection_rejects_duplicate_source_frames(tmp_path):
    report_path = _motion_report(tmp_path)
    plan_keyframes(report_path, tmp_path / "plan")
    selection_path = tmp_path / "selection.json"
    phases = ("CONTACT_A", "DOWN_A", "PASSING_A", "UP_A", "CONTACT_B", "DOWN_B")
    selection_path.write_text(json.dumps({"action": "walk", "selection": [
        {"phase": phase, "source_frame": 1 if index == 2 else index}
        for index, phase in enumerate(phases, 1)
    ]}), encoding="utf-8")
    with pytest.raises(ConfigurationError, match="must be unique"):
        select_keyframes(tmp_path / "plan" / "walk_keyframe_plan.json", selection_path, tmp_path / "selected")
