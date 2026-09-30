from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import cv2
    import numpy as np
except ImportError:  # pragma: no cover - optional motion extra
    cv2 = None
    np = None
from PIL import Image, ImageDraw, ImageFont

from ..errors import ConfigurationError


WALK_PHASES = (
    "CONTACT_A",
    "DOWN_A",
    "PASSING_A",
    "UP_A",
    "CONTACT_B",
    "DOWN_B",
    "PASSING_B",
    "UP_B",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_motion_dependencies() -> None:
    if cv2 is None or np is None:
        raise ConfigurationError("Keyframe planning requires OpenCV; install the optional 'motion' extra.")


def _read_rgb(path: str | Path) -> np.ndarray:
    with Image.open(path) as image:
        return np.asarray(image.convert("RGB"))


def _frame_mask(frame: np.ndarray) -> tuple[np.ndarray, tuple[float, float, float]]:
    border = np.concatenate((frame[0], frame[-1], frame[:, 0], frame[:, -1]), axis=0)
    background = np.median(border, axis=0)
    distance = np.linalg.norm(frame.astype(np.float32) - background, axis=2)
    return (distance > 28), tuple(float(v) for v in background)


def _metrics(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    masks: list[np.ndarray] = []
    rgbs: list[np.ndarray] = []
    for row in rows:
        rgb = _read_rgb(row["aligned_path"])
        mask, _background = _frame_mask(rgb)
        masks.append(mask)
        rgbs.append(rgb)
        bbox = row.get("subject_bbox") or {}
        dx, dy = row.get("alignment_offset", [0, 0])
        x, y = int(bbox.get("x", 0)) + int(dx), int(bbox.get("y", 0)) + int(dy)
        width, height = int(bbox.get("width", 0)), int(bbox.get("height", 0))
        center_x, center_y = x + width / 2, y + height / 2
        foot_y = y + height
        left_area = right_area = 0
        leg_motion = arm_motion = 0.0
        foreground_motion = 0.0
        if width > 0 and height > 0:
            x0, x1 = max(0, x), min(mask.shape[1], x + width)
            y0, y1 = max(0, y), min(mask.shape[0], y + height)
            subject = mask[y0:y1, x0:x1]
            split = max(1, subject.shape[1] // 2)
            left_area = int(subject[:, :split].sum())
            right_area = int(subject[:, split:].sum())
            if len(masks) > 1:
                previous = masks[-2][y0:y1, x0:x1]
                foreground_motion = float(np.mean(subject != previous)) if subject.size else 0.0
                leg_y = max(0, round(subject.shape[0] * 0.58))
                arm_y0, arm_y1 = round(subject.shape[0] * 0.20), round(subject.shape[0] * 0.66)
                leg_motion = float(np.mean(subject[leg_y:, :] != previous[leg_y:, :])) if subject[leg_y:, :].size else 0.0
                arm_motion = float(np.mean(subject[arm_y0:arm_y1, :] != previous[arm_y0:arm_y1, :])) if subject[arm_y0:arm_y1, :].size else 0.0
        previous_rgb = None
        next_rgb = None
        if len(rgbs) > 1:
            if len(results) > 0:
                previous_rgb = float(np.abs(rgb.astype(np.int16) - rgbs[-2].astype(np.int16)).mean())
            # Filled after all RGB frames are read.
        results.append({
            "sample_index": int(row["sample_index"]),
            "source_frame_index": int(row["source_frame_index"]),
            "timestamp_seconds": float(row["timestamp_seconds"]),
            "aligned_path": str(Path(row["aligned_path"]).resolve()),
            "raw_path": str(Path(row["raw_path"]).resolve()),
            "subject_bbox_source": bbox,
            "alignment_offset": [int(dx), int(dy)],
            "subject_bbox_aligned": {"x": x, "y": y, "width": width, "height": height},
            "subject_center": [round(center_x, 3), round(center_y, 3)],
            "foot_baseline_y": foot_y,
            "silhouette_extent": {"left_half_pixels": left_area, "right_half_pixels": right_area},
            "body_vertical_displacement": None,
            "foreground_mask_difference_previous": round(foreground_motion, 6),
            "leg_region_motion_proxy": round(leg_motion, 6),
            "arm_region_motion_proxy": round(arm_motion, 6),
            "previous_frame_difference_rgb": round(previous_rgb, 6) if previous_rgb is not None else None,
            "next_frame_difference_rgb": next_rgb,
            "blur_score": float(row["blur_score"]),
            "blur_status": row["blur_status"],
        })
    if results:
        baseline = results[0]["subject_center"][1]
        for index, item in enumerate(results):
            item["body_vertical_displacement"] = round(item["subject_center"][1] - baseline, 3)
            if index + 1 < len(results):
                item["next_frame_difference_rgb"] = round(
                    float(np.abs(rgbs[index].astype(np.int16) - rgbs[index + 1].astype(np.int16)).mean()), 6
                )
    return results


def _cycle_period(rows: list[dict[str, Any]]) -> tuple[float | None, list[dict[str, float | int]]]:
    if len(rows) < 8:
        return None, []
    features: list[np.ndarray] = []
    for row in rows:
        image = Image.open(row["aligned_path"]).convert("RGB")
        bbox = row.get("subject_bbox") or {}
        dx, dy = row.get("alignment_offset", [0, 0])
        x, y = int(bbox.get("x", 0)) + int(dx), int(bbox.get("y", 0)) + int(dy)
        w, h = int(bbox.get("width", 0)), int(bbox.get("height", 0))
        if w <= 0 or h <= 0:
            crop = image
        else:
            crop = image.crop((max(0, x), max(0, y), min(image.width, x + w), min(image.height, y + h)))
        features.append(np.asarray(crop.resize((48, 84), Image.Resampling.BILINEAR), dtype=np.int16))
    lag_scores = []
    for lag in range(3, len(rows) // 2 + 1):
        values = [float(np.abs(features[i] - features[i + lag]).mean()) for i in range(len(rows) - lag)]
        lag_scores.append({"lag_samples": lag, "mean_rgb_difference": round(sum(values) / len(values), 6)})
    best = min(lag_scores, key=lambda item: float(item["mean_rgb_difference"]))
    return float(best["lag_samples"]), lag_scores


def _font(size: int) -> ImageFont.ImageFont:
    for path in (Path(r"C:\Windows\Fonts\arial.ttf"), Path(r"C:\Windows\Fonts\segoeui.ttf")):
        if path.is_file():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def _write_phase_sheet(groups: list[dict[str, Any]], path: Path) -> None:
    cell_w, preview_h, footer_h = 224, 172, 56
    cell_h = preview_h + footer_h
    sheet = Image.new("RGB", (cell_w * 3, cell_h * len(groups)), (238, 236, 229))
    draw = ImageDraw.Draw(sheet)
    title_font, body_font = _font(15), _font(12)
    for phase_index, group in enumerate(groups):
        y0 = phase_index * cell_h
        draw.text((8, y0 + 3), group["phase"], fill=(22, 22, 24), font=title_font)
        for rank, candidate in enumerate(group["candidates"][:3]):
            x0 = rank * cell_w
            image = Image.open(candidate["aligned_path"]).convert("RGBA")
            image.thumbnail((cell_w - 10, preview_h - 26), Image.Resampling.NEAREST)
            matte = Image.new("RGB", image.size, (250, 248, 241))
            matte.paste(image, mask=image.getchannel("A"))
            px = x0 + (cell_w - matte.width) // 2
            py = y0 + 22 + (preview_h - 25 - matte.height) // 2
            sheet.paste(matte, (px, py))
            draw.text((x0 + 6, y0 + preview_h), f"#{candidate['sample_index']:03d}  {candidate['timestamp_seconds']:.3f}s  score {candidate['score']:.1f}", fill=(28, 28, 30), font=body_font)
            draw.text((x0 + 6, y0 + preview_h + 19), f"blur {candidate['blur_score']:.1f} | Δ {candidate['phase_distance_samples']:.2f} samples", fill=(65, 65, 68), font=body_font)
            draw.rectangle((x0, y0, x0 + cell_w - 2, y0 + cell_h - 2), outline=(160, 155, 145), width=1)
    sheet.save(path)


def plan_keyframes(report_path: str | Path, output_dir: str | Path, *, action: str = "walk", top_k: int = 3) -> dict[str, Any]:
    _require_motion_dependencies()
    source_report = Path(report_path).expanduser().resolve()
    output = Path(output_dir).expanduser().resolve()
    if action != "walk":
        raise ConfigurationError("Phase 9 currently accepts walk only; idle remains locked until walk Phase 9–10 completes.")
    if top_k < 1 or top_k > 8:
        raise ConfigurationError("top_k must be between 1 and 8.")
    if output.exists():
        raise ConfigurationError(f"Keyframe plan output already exists; refusing to overwrite: {output}")
    report = json.loads(source_report.read_text(encoding="utf-8"))
    rows = [item for item in report.get("frames", []) if item.get("selected_candidate") and item.get("aligned_path")]
    if len(rows) < 6:
        raise ConfigurationError(f"Walk keyframe planning needs at least 6 usable candidates; found {len(rows)}.")
    rows.sort(key=lambda row: int(row["sample_index"]))
    frame_metrics = _metrics(rows)
    period_samples, period_scores = _cycle_period(rows)
    sample_fps = float(report.get("sample_fps") or 12.0)
    period_seconds = period_samples / sample_fps if period_samples else None
    duration = float(report.get("duration_seconds") or rows[-1]["timestamp_seconds"])
    cycle_reference = period_seconds or duration
    first_time = float(rows[0]["timestamp_seconds"])
    groups: list[dict[str, Any]] = []
    for phase_index, phase in enumerate(WALK_PHASES):
        target_fraction = phase_index / len(WALK_PHASES)
        target_time = first_time + target_fraction * cycle_reference
        scored: list[dict[str, Any]] = []
        for row, metrics in zip(rows, frame_metrics):
            timestamp = float(row["timestamp_seconds"])
            if period_seconds:
                relative = (timestamp - first_time) % period_seconds
                delta = abs(relative - target_fraction * period_seconds)
                delta = min(delta, period_seconds - delta)
                distance_samples = delta * sample_fps
            else:
                distance_samples = abs(timestamp - target_time) * sample_fps
            # Phase fit dominates; sharpness and motion support tie-breaking only.
            phase_fit = max(0.0, 1.0 - distance_samples / max(1.0, (period_samples or len(rows)) / 4))
            sharpness = min(1.0, max(0.0, float(row["blur_score"]) / 60.0))
            motion = min(1.0, float(metrics["foreground_mask_difference_previous"]) * 8.0)
            score = 82.0 * phase_fit + 10.0 * sharpness + 8.0 * motion
            scored.append({
                **metrics,
                "aligned_path": str(Path(row["aligned_path"]).resolve()),
                "raw_path": str(Path(row["raw_path"]).resolve()),
                "source_frame_index": int(row["source_frame_index"]),
                "phase_distance_samples": round(distance_samples, 4),
                "score": round(score, 4),
                "target_fraction": target_fraction,
                "target_timestamp_seconds": round(target_time, 6),
            })
        ranked = sorted(scored, key=lambda item: (-item["score"], item["phase_distance_samples"], -item["blur_score"]))
        groups.append({"phase": phase, "target_fraction": target_fraction, "candidates": ranked[:top_k]})
    output.mkdir(parents=True)
    sheet_path = output / "walk_phase_contact_sheet.png"
    _write_phase_sheet(groups, sheet_path)
    template = {
        "action": action,
        "frame_count": 8,
        "selection": [
            {"phase": group["phase"], "source_frame": group["candidates"][0]["sample_index"]}
            for group in groups
        ],
        "source_frame_field": "1-based sample_index from motion_report.json frames",
    }
    template_path = output / "walk_selection_template.json"
    template_path.write_text(json.dumps(template, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    plan = {
        "schema_version": 1,
        "status": "WAITING_FOR_KEYFRAME_REVIEW",
        "action": action,
        "source_report": str(source_report),
        "source_report_sha256": _sha256(source_report),
        "source_video": report.get("source", {}).get("path"),
        "source_video_sha256": report.get("source", {}).get("sha256"),
        "candidate_count": len(rows),
        "sampled_frame_count": report.get("sampled_frame_count"),
        "sample_fps": sample_fps,
        "duration_seconds": duration,
        "cycle_estimate": {
            "method": "minimum mean RGB difference across aligned subject crops, lags 3..N/2",
            "estimated_period_samples": period_samples,
            "estimated_period_seconds": round(period_seconds, 6) if period_seconds else None,
            "lag_scores": period_scores,
            "is_semantic_ground_truth": False,
        },
        "candidate_metrics": frame_metrics,
        "semantic_groups": groups,
        "review": {"status": "PENDING", "reviewer": None, "reviewed_at_utc": None},
        "contact_sheet": str(sheet_path),
        "selection_template": str(template_path),
    }
    path = output / "walk_keyframe_plan.json"
    path.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return plan


def select_keyframes(
    plan_path: str | Path,
    selection_path: str | Path,
    output_dir: str | Path,
    *,
    reviewer: str = "Codex visual review",
    review_notes: list[str] | None = None,
    quality_review: dict[str, Any] | None = None,
) -> dict[str, Any]:
    plan_file = Path(plan_path).expanduser().resolve()
    selection_file = Path(selection_path).expanduser().resolve()
    output = Path(output_dir).expanduser().resolve()
    plan = json.loads(plan_file.read_text(encoding="utf-8"))
    if plan.get("status") != "WAITING_FOR_KEYFRAME_REVIEW":
        raise ConfigurationError("Keyframe selection requires a plan in WAITING_FOR_KEYFRAME_REVIEW state.")
    selection_doc = json.loads(selection_file.read_text(encoding="utf-8"))
    if selection_doc.get("action") != plan.get("action"):
        raise ConfigurationError("Selection action does not match the keyframe plan.")
    chosen = selection_doc.get("selection")
    if not isinstance(chosen, list) or not 6 <= len(chosen) <= 8:
        raise ConfigurationError("An explicit walk selection must contain 6–8 semantic keyframes.")
    phase_order = {phase: index for index, phase in enumerate(WALK_PHASES)}
    if any(not isinstance(item, dict) or item.get("phase") not in phase_order for item in chosen):
        raise ConfigurationError("Every selected keyframe must name one of the defined walk semantic phases.")
    if [phase_order[item["phase"]] for item in chosen] != sorted(phase_order[item["phase"]] for item in chosen):
        raise ConfigurationError("Selected keyframes must be in walk semantic order.")
    if len({item["phase"] for item in chosen}) != len(chosen):
        raise ConfigurationError("A semantic phase may be selected only once.")
    if len({int(item.get("source_frame", -1)) for item in chosen}) != len(chosen):
        raise ConfigurationError("Selected candidate frames must be unique.")
    candidates = {int(row["sample_index"]): row for row in plan["candidate_metrics"]}
    grouped = {group["phase"]: group["candidates"] for group in plan["semantic_groups"]}
    for item in chosen:
        sample_index = int(item["source_frame"])
        if sample_index not in candidates:
            raise ConfigurationError(f"Selected sample_index {sample_index} is not a Phase 8 candidate.")
        if item["phase"] not in grouped:
            raise ConfigurationError(f"No ranked candidate group exists for phase {item['phase']}.")
        row = candidates[sample_index]
        if row.get("blur_status") == "REJECT":
            raise ConfigurationError(f"Hard-rejected frame {sample_index} cannot be selected.")
        if not Path(row["aligned_path"]).is_file():
            raise ConfigurationError(f"Selected candidate image is missing: {row['aligned_path']}")
    if output.exists():
        raise ConfigurationError(f"Selected keyframe output already exists; refusing to overwrite: {output}")
    output.mkdir(parents=True)
    reference_dir = output / "walk_reference"
    reference_dir.mkdir()
    rows_out: list[dict[str, Any]] = []
    for index, item in enumerate(chosen):
        phase = item["phase"]
        sample_index = int(item["source_frame"])
        source = candidates[sample_index]
        path = Path(source["aligned_path"])
        filename = f"{index:02d}_{phase.lower()}.png"
        destination = reference_dir / filename
        shutil.copy2(path, destination)
        candidate = next((candidate for candidate in grouped[phase] if candidate["sample_index"] == sample_index), None)
        rows_out.append({
            "order": index,
            "phase": phase,
            "sample_index": sample_index,
            "source_video_frame_index": source["source_frame_index"],
            "timestamp_seconds": source["timestamp_seconds"],
            "subject_bbox_aligned": source["subject_bbox_aligned"],
            "source_aligned_frame": str(path),
            "reference_png": str(destination),
            "sha256": _sha256(destination),
            "rank_for_phase": next((rank + 1 for rank, ranked in enumerate(grouped[phase]) if ranked["sample_index"] == sample_index), None),
            "score_for_phase": candidate["score"] if candidate else None,
            "blur_score": source["blur_score"],
            "motion_metrics": {key: source[key] for key in ("subject_center", "foot_baseline_y", "body_vertical_displacement", "foreground_mask_difference_previous", "leg_region_motion_proxy", "arm_region_motion_proxy")},
        })
    sheet = Image.new("RGB", (len(rows_out) * 190, 240), (242, 239, 230))
    draw = ImageDraw.Draw(sheet)
    font = _font(12)
    for row in rows_out:
        image = Image.open(row["reference_png"]).convert("RGBA")
        image.thumbnail((180, 190), Image.Resampling.NEAREST)
        matte = Image.new("RGB", image.size, (250, 248, 241))
        matte.paste(image, mask=image.getchannel("A"))
        x = row["order"] * 190 + (190 - matte.width) // 2
        sheet.paste(matte, (x, 4))
        draw.text((row["order"] * 190 + 5, 202), f"{row['order']:02d} {row['phase']}", fill=(20, 20, 20), font=font)
        draw.text((row["order"] * 190 + 5, 220), f"#{row['sample_index']:03d} {row['timestamp_seconds']:.3f}s", fill=(45, 45, 45), font=font)
    contact_sheet = output / "walk_reference_contact_sheet.png"
    sheet.save(contact_sheet)
    selected = {
        "schema_version": 1,
        "status": "KEYFRAMES_SELECTED",
        "action": plan["action"],
        "source_report": plan["source_report"],
        "source_report_sha256": plan["source_report_sha256"],
        "cycle_estimate": plan["cycle_estimate"],
        "frame_count": len(rows_out),
        "review": {
            "status": "COMPLETED",
            "reviewer": reviewer,
            "reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
            "notes": review_notes or [],
            "automated_semantic_labels_are_reference_bins_not_pose_truth": True,
        },
        "quality_review": quality_review or {},
        "selection": rows_out,
        "contact_sheet": str(contact_sheet),
        "references_directory": str(reference_dir),
    }
    result_path = output / "walk_keyframes.json"
    result_path.write_text(json.dumps(selected, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    plan["status"] = "KEYFRAMES_SELECTED"
    plan["review"] = selected["review"]
    plan["selected_keyframes"] = str(result_path)
    plan_file.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return selected
