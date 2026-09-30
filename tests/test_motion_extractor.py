from __future__ import annotations

import json

from PIL import Image, ImageDraw, ImageFilter


from assetpipe._ported.motion_extractor.extract import extract_motion


def test_extracts_uniform_samples_scores_blur_filters_duplicates_and_aligns(tmp_path):
    source_dir = tmp_path / "sequence"
    source_dir.mkdir()
    base = Image.new("RGB", (160, 160), (244, 240, 229))
    ImageDraw.Draw(base).rectangle((46, 24, 105, 145), fill=(70, 92, 120))
    shifted = Image.new("RGB", base.size, (244, 240, 229))
    shifted.paste(base.crop((0, 0, 152, 160)), (8, 0))
    blurred = base.filter(ImageFilter.GaussianBlur(2.0))
    for index, image in enumerate((base, shifted, shifted.copy(), blurred), start=1):
        image.save(source_dir / f"frame_{index:02d}.png")

    output = tmp_path / "extract"
    report = extract_motion(
        source_dir,
        output,
        sample_fps=12,
        sequence_fps=12,
        blur_soft_min=120,
        blur_reject_min=5,
        near_duplicate_hamming=0,
    )

    assert report["frame_count"] == 4
    assert report["sampled_frame_count"] == 4
    assert report["duration_seconds"] == 0.333333
    assert report["frame_difference"]["mean"] is not None
    assert report["blur_scoring"]["score_summary"]["max"] >= report["blur_scoring"]["score_summary"]["min"]
    assert report["duplicate_filtering"]["exact_duplicates"] == 1
    assert report["selected_candidate_count"] <= 3
    assert report["subject_detection"]["bbox_available_count"] >= 3
    assert report["subject_detection"]["mean_bbox_occupancy"] is not None
    assert report["contact_sheet"] == str(output / "contact_sheet.png")
    assert report["selected_contact_sheet"] == str(output / "selected_contact_sheet.png")
    assert report["visual_usability_review"]["status"] == "PENDING"
    assert (output / "selected_contact_sheet.png").is_file()
    assert (output / "motion_report.md").is_file()
    assert len(list((output / "frames" / "raw").glob("*.png"))) == 4
    assert len(list((output / "frames" / "sampled").glob("*.png"))) == 4
    assert json.loads((output / "motion_report.json").read_text(encoding="utf-8"))["status"] == "EXTRACTION_COMPLETE_REVIEW_REQUIRED"



