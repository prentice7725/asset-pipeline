from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any

try:
    import cv2
    import numpy as np
except ImportError:  # pragma: no cover - exercised only without the optional motion extra
    cv2 = None
    np = None

from PIL import Image, ImageDraw, ImageFont, ImageOps, UnidentifiedImageError

from ..errors import ConfigurationError, PixelPipelineError


class MotionExtractionError(PixelPipelineError):
    """A motion reference could not be decoded or analyzed."""


_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
_VIDEO_SUFFIXES = {".mp4", ".m4v", ".mov", ".mkv", ".webm", ".avi"}


def _natural_key(path: Path) -> list[Any]:
    return [int(piece) if piece.isdigit() else piece.lower() for piece in re.split(r"(\d+)", path.name)]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _font(size: int) -> ImageFont.ImageFont:
    for candidate in (Path(r"C:\Windows\Fonts\arial.ttf"), Path(r"C:\Windows\Fonts\segoeui.ttf")):
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def _as_rgb(frame: Image.Image) -> Image.Image:
    return frame.convert("RGB")


def _blur_score(image: Image.Image) -> float:
    if cv2 is None or np is None:
        raise MotionExtractionError("Motion extraction requires the optional opencv-python dependency.")
    gray = cv2.cvtColor(np.asarray(image.convert("RGB")), cv2.COLOR_RGB2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def _phash(image: Image.Image) -> int:
    gray = cv2.cvtColor(np.asarray(image.convert("RGB")), cv2.COLOR_RGB2GRAY)
    sample = cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA).astype(np.float32)
    transformed = cv2.dct(sample)[:8, :8]
    values = transformed.flatten()[1:]
    median = float(np.median(values))
    bits = values > median
    output = 0
    for bit in bits:
        output = (output << 1) | int(bit)
    return output


def _detect_subject(image: Image.Image, foreground_threshold: int) -> tuple[dict[str, int] | None, str, tuple[int, int, int]]:
    rgb = np.asarray(image.convert("RGB"))
    height, width = rgb.shape[:2]
    alpha = image.getchannel("A") if image.mode == "RGBA" else None
    if alpha is not None and alpha.getextrema() != (255, 255):
        mask = np.asarray(alpha) > 0
        method = "alpha"
        background = tuple(int(value) for value in rgb[0, 0])
    else:
        border = np.concatenate((rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]), axis=0)
        bg = np.median(border, axis=0)
        delta = rgb.astype(np.float32) - bg.astype(np.float32)
        mask = np.linalg.norm(delta, axis=2) > foreground_threshold
        method = "known_background_difference"
        background = tuple(int(value) for value in bg)
    mask_u8 = (mask.astype(np.uint8) * 255)
    kernel = np.ones((3, 3), dtype=np.uint8)
    cleaned = cv2.morphologyEx(mask_u8, cv2.MORPH_OPEN, kernel)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel)
    count, labels, stats, _centroids = cv2.connectedComponentsWithStats(cleaned, 8)
    if count <= 1:
        return None, method + "_no_foreground", background
    largest_label = max(range(1, count), key=lambda index: int(stats[index, cv2.CC_STAT_AREA]))
    x, y, box_width, box_height, area = (int(value) for value in stats[largest_label])
    occupancy = area / max(1, width * height)
    if area < max(9, round(width * height * 0.001)) or occupancy > 0.97:
        return None, method + "_low_confidence", background
    return {"x": x, "y": y, "width": box_width, "height": box_height}, method, background


def _align_frame(image: Image.Image, bbox: dict[str, int] | None, background: tuple[int, int, int], margin: int = 2) -> tuple[Image.Image, str, list[int]]:
    width, height = image.size
    if bbox is None:
        return image.copy(), "FALLBACK_FULL_FRAME", [0, 0]
    box_width, box_height = bbox["width"], bbox["height"]
    dx = round(width / 2 - (bbox["x"] + box_width / 2))
    dy = height - margin - (bbox["y"] + box_height)
    dx = max(-bbox["x"], min(width - (bbox["x"] + box_width), dx))
    dy = max(-bbox["y"], min(height - (bbox["y"] + box_height), dy))
    fill = (*background, 0) if image.mode == "RGBA" and image.getchannel("A").getextrema()[0] == 0 else (*background, 255) if image.mode == "RGBA" else background
    aligned = Image.new(image.mode, image.size, fill)
    if image.mode == "RGBA":
        aligned.paste(image, (dx, dy), image.getchannel("A"))
    else:
        aligned.paste(image, (dx, dy))
    return aligned, "BOTTOM_CENTER", [dx, dy]


def _perceptual_distance(left: int, right: int) -> int:
    return (left ^ right).bit_count()


def _frame_difference(left: Image.Image, right: Image.Image) -> float:
    left_rgb = np.asarray(left.convert("RGB"), dtype=np.int16)
    right_rgb = np.asarray(right.convert("RGB"), dtype=np.int16)
    return float(np.abs(left_rgb - right_rgb).mean())


def _timestamp_text(seconds: float) -> str:
    return f"{seconds:.3f}s"


def _write_contact_sheet(rows: list[dict[str, Any]], output: Path, columns: int = 5) -> None:
    cell_w, preview_h, footer_h = 240, 230, 72
    cell_h = preview_h + footer_h
    count = max(1, len(rows))
    lines = math.ceil(count / columns)
    sheet = Image.new("RGB", (columns * cell_w, lines * cell_h), (239, 237, 229))
    draw = ImageDraw.Draw(sheet)
    title_font, body_font = _font(15), _font(12)
    if not rows:
        draw.text((12, 12), "No sampled frames were decoded.", fill=(30, 30, 30), font=title_font)
    for index, item in enumerate(rows):
        row, col = divmod(index, columns)
        x, y = col * cell_w, row * cell_h
        draw.rectangle((x, y, x + cell_w - 2, y + cell_h - 2), outline=(150, 145, 135), width=1)
        draw.text((x + 6, y + 4), f"#{item['sample_index']:03d} @ {_timestamp_text(item['timestamp_seconds'])}", fill=(22, 22, 24), font=title_font)
        with Image.open(item["aligned_path"]) as opened:
            preview = opened.convert("RGBA")
        scale = min((cell_w - 12) / preview.width, (preview_h - 32) / preview.height)
        preview = preview.resize((max(1, round(preview.width * scale)), max(1, round(preview.height * scale))), Image.Resampling.NEAREST)
        matte = Image.new("RGB", preview.size, (249, 247, 241))
        matte.paste(preview, mask=preview.getchannel("A"))
        px, py = x + (cell_w - matte.width) // 2, y + 24 + (preview_h - 32 - matte.height) // 2
        sheet.paste(matte, (px, py))
        footer_y = y + preview_h + 2
        draw.text((x + 6, footer_y), f"Blur {item['blur_score']:.1f} | {item['blur_status']}", fill=(32, 76, 35) if item["blur_status"] == "KEEP" else (150, 82, 20), font=body_font)
        draw.text((x + 6, footer_y + 18), f"Duplicate: {item['duplicate_status']}", fill=(52, 52, 54), font=body_font)
        draw.text((x + 6, footer_y + 36), f"Alignment: {item['alignment_status']}", fill=(52, 52, 54), font=body_font)
    sheet.save(output)


def _write_motion_markdown(report: dict[str, Any], output: Path) -> None:
    review = report.get("visual_usability_review", {})
    blur = report.get("blur_scoring", {}).get("score_summary") or {}
    difference = report.get("frame_difference", {})
    subject = report.get("subject_detection", {})

    source = report.get("source", {})
    md = [
        "# Motion Extractor M0 report",
        "",
        f"- Status: `{report.get('status')}`",
        f"- Source: `{source.get('path')}`",
        f"- Source frames: {report.get('frame_count')}",
        f"- Duration: {report.get('duration_seconds')}s at {source.get('fps')}fps",
        f"- Resolution: {source.get('width')}x{source.get('height')}",
        f"- Sampled frames: {report.get('sampled_frame_count')} at {report.get('sample_fps')}fps",
        f"- Remaining candidates: {report.get('selected_candidate_count')} ({report.get('usable_frame_ratio', 0):.1%})",
        f"- Blur score min/median/mean/max: {blur.get('min')}/{blur.get('median')}/{blur.get('mean')}/{blur.get('max')}",
        f"- Blur KEEP/SOFT_REJECT/REJECT: {report.get('blur_scoring', {}).get('counts', {})}",
        f"- Exact/near duplicates: {report.get('duplicate_filtering', {}).get('exact_duplicates')}/{report.get('duplicate_filtering', {}).get('near_duplicates')}",
        f"- Frame difference mean/median/max RGB: {difference.get('mean')}/{difference.get('median')}/{difference.get('max')}",
        f"- Subject bbox mean occupancy: {subject.get('mean_bbox_occupancy')}",
        f"- Normalized bbox center drift mean/max: {subject.get('bbox_drift_from_first_center_mean')}/{subject.get('bbox_drift_from_first_center_max')}",
        f"- Offscreen frames: {len(subject.get('offscreen_frame_indices', []))}",
        f"- Metric usability: `{report.get('motion_frame_usability')}`",
        "",
        "## USABILITY REVIEW",
        "",
        f"- Review status: `{review.get('status', 'PENDING')}`",
        f"- Rating: `{review.get('rating', 'UNREVIEWED')}`",
    ]
    for key, title in (("usable", "Usable"), ("partially_usable", "Partially usable"), ("unusable", "Unusable"), ("main_failure_modes", "Main failure modes")):
        md.extend(["", f"### {title}", ""])
        entries = review.get(key)
        md.extend([f"- {entry}" for entry in entries] if entries else ["- None recorded."])
    md.extend([
        "",
        "Automatic image statistics do not decide pose usefulness or identity fidelity. The visual assessment uses the contact sheets and sampled frames.",
        "",
        f"- Contact sheet: `{report.get('contact_sheet')}`",
        f"- Selected candidate sheet: `{report.get('selected_contact_sheet')}`",
        "",
    ])
    output.write_text("\n".join(md), encoding="utf-8")


def extract_motion(
    source: str | Path,
    output_dir: str | Path,
    *,
    sample_fps: float = 12.0,
    sequence_fps: float = 24.0,
    blur_soft_min: float = 60.0,
    blur_reject_min: float = 18.0,
    near_duplicate_hamming: int = 4,
    foreground_threshold: int = 28,
) -> dict[str, Any]:
    if cv2 is None or np is None:
        raise MotionExtractionError("Motion extraction requires opencv-python; install the optional 'motion' extra.")
    source_path = Path(source).expanduser().resolve()
    output = Path(output_dir).expanduser().resolve()
    if not source_path.exists():
        raise MotionExtractionError(f"Motion reference does not exist: {source_path}")
    if output.exists():
        raise MotionExtractionError(f"Motion extraction output already exists: {output}")
    if sample_fps <= 0 or sequence_fps <= 0:
        raise ConfigurationError("sample_fps and sequence_fps must be positive.")
    if blur_reject_min < 0 or blur_soft_min < blur_reject_min:
        raise ConfigurationError("Blur thresholds must satisfy 0 <= reject <= soft_min.")
    image_paths = sorted((path for path in source_path.iterdir() if path.suffix.lower() in _IMAGE_SUFFIXES), key=_natural_key) if source_path.is_dir() else []
    sequence_mode = bool(image_paths)
    if len(image_paths) > 10000:
        raise MotionExtractionError("Motion image sequence exceeds the 10,000-frame safety limit.")
    video_capture = None
    source_fps = sequence_fps
    decoded: list[tuple[Image.Image, float, int]] = []
    source_width = source_height = 0
    if sequence_mode:
        for index, path in enumerate(image_paths):
            try:
                with Image.open(path) as opened:
                    frame = ImageOps.exif_transpose(opened).convert("RGBA" if "A" in opened.getbands() else "RGB")
            except (OSError, UnidentifiedImageError) as exc:
                raise MotionExtractionError(f"Cannot decode sequence frame '{path}': {exc}") from exc
            if index == 0:
                source_width, source_height = frame.size
            if frame.size != (source_width, source_height):
                raise MotionExtractionError(f"Image sequence frame '{path}' is {frame.size}; expected {(source_width, source_height)}.")
            decoded.append((frame, index / sequence_fps, index))
        source_fps = sequence_fps
    elif source_path.suffix.lower() in _VIDEO_SUFFIXES:
        video_capture = cv2.VideoCapture(str(source_path))
        if not video_capture.isOpened():
            raise MotionExtractionError(f"OpenCV could not decode video '{source_path}'.")
        source_fps = float(video_capture.get(cv2.CAP_PROP_FPS) or 0.0) or sequence_fps
        frame_index = 0
        while True:
            ok, bgr = video_capture.read()
            if not ok:
                break
            if len(decoded) >= 10000:
                video_capture.release()
                raise MotionExtractionError("Motion reference exceeds the 10,000-frame safety limit.")
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            frame = Image.fromarray(rgb, "RGB")
            if frame_index == 0:
                source_width, source_height = frame.size
            decoded.append((frame, frame_index / source_fps, frame_index))
            frame_index += 1
        video_capture.release()
        if not decoded:
            raise MotionExtractionError(f"Video decoder returned no frames for '{source_path}'.")
    else:
        raise MotionExtractionError("Input must be an MP4/video file or a directory containing image frames.")
    if not decoded:
        raise MotionExtractionError("Image sequence contains no supported images.")
    frame_count = len(decoded)
    duration = frame_count / source_fps

    raw_dir = output / "frames" / "raw"
    sampled_dir = output / "frames" / "sampled"
    aligned_dir = output / "frames" / "aligned"
    selected_dir = output / "frames" / "selected"
    for directory in (raw_dir, sampled_dir, aligned_dir, selected_dir):
        directory.mkdir(parents=True, exist_ok=True)
    raw_paths: list[Path] = []
    for image, timestamp, frame_no in decoded:
        raw_path = raw_dir / f"frame_{frame_no + 1:06d}_t{round(timestamp * 1000):08d}ms.png"
        image.save(raw_path)
        raw_paths.append(raw_path)

    sample_indices: list[int] = []
    time_index = 0
    while True:
        timestamp = time_index / sample_fps
        if timestamp >= duration or not decoded:
            break
        source_index = min(frame_count - 1, int(round(timestamp * source_fps)))
        if not sample_indices or source_index != sample_indices[-1]:
            sample_indices.append(source_index)
        time_index += 1
    if sample_indices and sample_indices[-1] != frame_count - 1 and duration - decoded[sample_indices[-1]][1] <= 0.5 / sample_fps:
        sample_indices.append(frame_count - 1)

    sampled_rows: list[dict[str, Any]] = []
    prior_phash: int | None = None
    prior_exact_hash: str | None = None
    prior_sample_image: Image.Image | None = None
    for sample_index, source_index in enumerate(sample_indices, start=1):
        image, timestamp, decoded_index = decoded[source_index]
        if image.mode not in {"RGB", "RGBA"}:
            image = image.convert("RGBA") if "A" in image.getbands() else image.convert("RGB")
        raw_bytes = image.tobytes()
        exact_hash = hashlib.sha256(raw_bytes).hexdigest()
        image_phash = _phash(image)
        blur = _blur_score(image)
        frame_difference = _frame_difference(prior_sample_image, image) if prior_sample_image is not None else None
        blur_status = "REJECT" if blur < blur_reject_min else "SOFT_REJECT" if blur < blur_soft_min else "KEEP"
        if prior_exact_hash == exact_hash:
            duplicate_status = "EXACT_DUPLICATE"
        elif prior_phash is not None and _perceptual_distance(prior_phash, image_phash) <= near_duplicate_hamming:
            duplicate_status = "NEAR_DUPLICATE"
        else:
            duplicate_status = "UNIQUE"
        bbox, method, background = _detect_subject(image, foreground_threshold)
        aligned, alignment_status, offset = _align_frame(image, bbox, background)
        sampled_path = sampled_dir / f"sample_{sample_index:04d}_from_{decoded_index + 1:06d}.png"
        aligned_path = aligned_dir / f"sample_{sample_index:04d}_from_{decoded_index + 1:06d}.png"
        selected_path = selected_dir / f"sample_{sample_index:04d}_from_{decoded_index + 1:06d}.png"
        image.save(sampled_path)
        aligned.save(aligned_path)
        selected = duplicate_status == "UNIQUE" and blur_status != "REJECT"
        if selected:
            aligned.save(selected_path)
        sampled_rows.append({
            "sample_index": sample_index,
            "source_frame_index": decoded_index + 1,
            "timestamp_seconds": round(timestamp, 6),
            "raw_path": str(raw_paths[decoded_index]),
            "sampled_path": str(sampled_path),
            "aligned_path": str(aligned_path),
            "selected_path": str(selected_path) if selected else None,
            "blur_score": round(blur, 6),
            "blur_status": blur_status,
            "frame_difference_mean_absolute_rgb": round(frame_difference, 6) if frame_difference is not None else None,
            "duplicate_status": duplicate_status,
            "phash": f"{image_phash:016x}",
            "subject_bbox": bbox,
            "subject_detection_method": method,
            "alignment_status": alignment_status,
            "alignment_offset": offset,
            "selected_candidate": selected,
        })
        prior_phash = image_phash
        prior_exact_hash = exact_hash
        prior_sample_image = image

    valid_boxes = [row["subject_bbox"] for row in sampled_rows if row["subject_bbox"] is not None]
    centers = [(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2) for box in valid_boxes]
    diagonal = math.hypot(source_width, source_height) or 1
    base_center = centers[0] if centers else (source_width / 2, source_height / 2)
    center_drift = [math.hypot(center[0] - base_center[0], center[1] - base_center[1]) / diagonal for center in centers]
    bbox_occupancy = [box["width"] * box["height"] / max(1, source_width * source_height) for box in valid_boxes]
    exact_duplicates = sum(row["duplicate_status"] == "EXACT_DUPLICATE" for row in sampled_rows)
    near_duplicates = sum(row["duplicate_status"] == "NEAR_DUPLICATE" for row in sampled_rows)
    blur_counts = Counter(row["blur_status"] for row in sampled_rows)
    blur_scores = [row["blur_score"] for row in sampled_rows]
    frame_differences = [row["frame_difference_mean_absolute_rgb"] for row in sampled_rows if row["frame_difference_mean_absolute_rgb"] is not None]
    selected_rows = [row for row in sampled_rows if row["selected_candidate"]]
    offscreen = [row["sample_index"] for row in sampled_rows if row["subject_bbox"] and (
        row["subject_bbox"]["x"] <= 0 or row["subject_bbox"]["y"] <= 0
        or row["subject_bbox"]["x"] + row["subject_bbox"]["width"] >= source_width
        or row["subject_bbox"]["y"] + row["subject_bbox"]["height"] >= source_height
    )]
    usable_ratio = len(selected_rows) / len(sampled_rows) if sampled_rows else 0.0
    mean_occupancy = sum(bbox_occupancy) / len(bbox_occupancy) if bbox_occupancy else None
    avg_center_drift = sum(center_drift) / len(center_drift) if center_drift else None
    max_center_drift = max(center_drift) if center_drift else None
    usability = "PARTIALLY_USABLE_REVIEW_REQUIRED" if len(selected_rows) >= 8 and not offscreen else "LIMITED_REVIEW_REQUIRED"
    report = {
        "schema_version": 1,
        "status": "EXTRACTION_COMPLETE_REVIEW_REQUIRED",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "path": str(source_path),
            "sha256": _sha256(source_path) if source_path.is_file() else None,
            "frame_sha256": [_sha256(path) for path in image_paths] if sequence_mode else None,
            "kind": "image_sequence" if sequence_mode else "video",
            "fps": round(source_fps, 6),
            "width": source_width,
            "height": source_height,
        },
        "frame_count": frame_count,
        "duration_seconds": round(duration, 6),
        "sample_fps": sample_fps,
        "sampled_frame_count": len(sampled_rows),
        "blur_scoring": {"method": "variance_of_laplacian", "soft_reject_below": blur_soft_min, "reject_below": blur_reject_min, "counts": dict(blur_counts), "score_summary": {"min": round(min(blur_scores), 6), "mean": round(sum(blur_scores) / len(blur_scores), 6), "median": round(median(blur_scores), 6), "max": round(max(blur_scores), 6)} if blur_scores else None},
        "frame_difference": {"method": "mean_absolute_rgb_difference_on_adjacent_sampled_frames", "scale": "0-255", "mean": round(sum(frame_differences) / len(frame_differences), 6) if frame_differences else None, "median": round(median(frame_differences), 6) if frame_differences else None, "max": round(max(frame_differences), 6) if frame_differences else None},
        "duplicate_filtering": {"method": "adjacent exact SHA-256 and perceptual hash", "near_duplicate_hamming_threshold": near_duplicate_hamming, "exact_duplicates": exact_duplicates, "near_duplicates": near_duplicates},
        "selected_candidate_count": len(selected_rows),
        "usable_frame_ratio": round(usable_ratio, 6),
        "subject_detection": {"method": "alpha mask then border-background difference", "foreground_threshold": foreground_threshold, "bbox_available_count": len(valid_boxes), "mean_bbox_occupancy": round(mean_occupancy, 6) if mean_occupancy is not None else None, "bbox_drift_from_first_center_mean": round(avg_center_drift, 6) if avg_center_drift is not None else None, "bbox_drift_from_first_center_max": round(max_center_drift, 6) if max_center_drift is not None else None, "offscreen_frame_indices": offscreen},
        "alignment": {"method": "bottom-center with frame bounds; full-frame fallback when subject detection is unavailable", "aligned_frames_dir": str(aligned_dir)},
        "motion_frame_usability": usability,
        "usability_note": "Automatic image statistics do not judge pose usefulness or identity fidelity; inspect the contact sheet and selected frames.",
        "visual_usability_review": {"status": "PENDING", "rating": "UNREVIEWED", "usable": [], "partially_usable": [], "unusable": [], "main_failure_modes": []},
        "frames": sampled_rows,
        "output_dirs": {"raw": str(raw_dir), "sampled": str(sampled_dir), "aligned": str(aligned_dir), "selected": str(selected_dir)},
    }
    _write_contact_sheet(sampled_rows, output / "contact_sheet.png")
    report["contact_sheet"] = str(output / "contact_sheet.png")
    _write_contact_sheet(selected_rows, output / "selected_contact_sheet.png")
    report["selected_contact_sheet"] = str(output / "selected_contact_sheet.png")
    (output / "motion_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _write_motion_markdown(report, output / "motion_report.md")
    return report
