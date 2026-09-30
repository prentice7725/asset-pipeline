from __future__ import annotations

import hashlib
import json
from collections import Counter, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError

from ..errors import PixelPipelineError


class ResolutionGateError(PixelPipelineError):
    """A resolution candidate or its identity feature definition is invalid."""


def _pixel_values(image: Image.Image) -> list[Any]:
    values = image.get_flattened_data() if hasattr(image, "get_flattened_data") else image.getdata()
    return list(values)


def _components(mask: Image.Image) -> int:
    width, height = mask.size
    values = bytearray(1 if item else 0 for item in _pixel_values(mask))
    seen = bytearray(len(values))
    count = 0
    for start, value in enumerate(values):
        if not value or seen[start]:
            continue
        count += 1
        seen[start] = 1
        todo: deque[int] = deque([start])
        while todo:
            index = todo.popleft()
            x, y = index % width, index // width
            for ny in range(max(0, y - 1), min(height, y + 2)):
                for nx in range(max(0, x - 1), min(width, x + 2)):
                    neighbor = ny * width + nx
                    if values[neighbor] and not seen[neighbor]:
                        seen[neighbor] = 1
                        todo.append(neighbor)
    return count


def _bbox(mask: Image.Image) -> dict[str, int] | None:
    bounds = mask.getbbox()
    if bounds is None:
        return None
    return {"x": bounds[0], "y": bounds[1], "width": bounds[2] - bounds[0], "height": bounds[3] - bounds[1]}


def _foreground_mask(image: Image.Image) -> Image.Image:
    alpha = image.getchannel("A")
    if alpha.getextrema() != (255, 255):
        return alpha.point(lambda value: 255 if value else 0)
    rgb = image.convert("RGB")
    width, height = rgb.size
    pixels = list(rgb.getdata())
    border = pixels[:width] + pixels[(height - 1) * width :]
    border += [pixels[y * width] for y in range(1, max(1, height - 1))]
    if width > 1:
        border += [pixels[y * width + width - 1] for y in range(1, max(1, height - 1))]
    background, count = Counter(border).most_common(1)[0]
    if count / len(border) < 0.2:
        return Image.new("L", image.size, 255)
    return Image.frombytes("L", image.size, bytes(0 if pixel == background else 255 for pixel in pixels))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_feature_mask(
    feature: dict[str, Any], source_mask: Image.Image, source_size: tuple[int, int], root: Path
) -> Image.Image:
    feature_id = feature.get("id")
    if not isinstance(feature_id, str) or not feature_id.strip():
        raise ResolutionGateError("Each identity feature needs a non-empty 'id'.")
    if "mask" in feature:
        mask_path = Path(str(feature["mask"]))
        if not mask_path.is_absolute():
            mask_path = root / mask_path
        try:
            with Image.open(mask_path) as opened:
                mask = opened.convert("L")
        except (OSError, UnidentifiedImageError) as exc:
            raise ResolutionGateError(f"Cannot open identity mask '{mask_path}': {exc}") from exc
        if mask.size != source_size:
            raise ResolutionGateError(
                f"Identity mask '{mask_path}' is {mask.width}x{mask.height}; expected {source_size[0]}x{source_size[1]}."
            )
        return mask.point(lambda pixel: 255 if pixel else 0)
    region = feature.get("region")
    if not isinstance(region, (list, tuple)) or len(region) != 4:
        raise ResolutionGateError(f"Identity feature '{feature_id}' needs a 'mask' path or [x, y, width, height] region.")
    try:
        x, y, width, height = (int(item) for item in region)
    except (TypeError, ValueError) as exc:
        raise ResolutionGateError(f"Identity feature '{feature_id}' region values must be integers.") from exc
    if x < 0 or y < 0 or width < 1 or height < 1 or x + width > source_size[0] or y + height > source_size[1]:
        raise ResolutionGateError(f"Identity feature '{feature_id}' region lies outside the source image.")
    region_mask = Image.new("L", source_size, 0)
    region_mask.paste(source_mask.crop((x, y, x + width, y + height)), (x, y))
    return region_mask


def _feature_metrics(feature: dict[str, Any], mask: Image.Image, target_size: tuple[int, int]) -> dict[str, Any]:
    source_area = sum(1 for value in _pixel_values(mask) if value)
    scaled_expected_area = source_area * (target_size[0] / mask.width) * (target_size[1] / mask.height)
    target_feature = mask.resize(target_size, Image.Resampling.NEAREST)
    observed_area = sum(1 for value in _pixel_values(target_feature) if value)
    preservation = min(1.0, observed_area / scaled_expected_area) if scaled_expected_area else 0.0
    return {
        "id": feature["id"],
        "importance": str(feature.get("importance", "high")).lower(),
        "source_area": source_area,
        "expected_scaled_area": round(scaled_expected_area, 4),
        "candidate_area": observed_area,
        "area_preservation": round(preservation, 6),
        "disappeared": source_area > 0 and observed_area == 0,
    }


def _candidate_metrics(
    source: Image.Image,
    source_mask: Image.Image,
    candidate: Image.Image,
    candidate_mask: Image.Image,
    features: list[dict[str, Any]],
    thresholds: dict[str, float],
) -> dict[str, Any]:
    source_size, candidate_size = source.size, candidate.size
    restored_mask = candidate_mask.resize(source_size, Image.Resampling.NEAREST)
    source_bits = source_mask.tobytes()
    restored_bits = restored_mask.tobytes()
    intersection = sum(1 for left, right in zip(source_bits, restored_bits) if left and right)
    union = sum(1 for left, right in zip(source_bits, restored_bits) if left or right)
    silhouette_iou = intersection / union if union else 1.0
    source_components = _components(source_mask)
    candidate_components = _components(candidate_mask)
    component_preservation = min(1.0, candidate_components / source_components) if source_components else 1.0
    source_bbox, candidate_bbox = _bbox(source_mask), _bbox(candidate_mask)
    bbox_change: dict[str, Any] | None = None
    if source_bbox and candidate_bbox:
        scaled = {
            "x": source_bbox["x"] * candidate_size[0] / source_size[0],
            "y": source_bbox["y"] * candidate_size[1] / source_size[1],
            "width": source_bbox["width"] * candidate_size[0] / source_size[0],
            "height": source_bbox["height"] * candidate_size[1] / source_size[1],
        }
        bbox_change = {
            key: round(candidate_bbox[key] - scaled[key], 4)
            for key in ("x", "y", "width", "height")
        }
    source_foreground = sum(1 for value in _pixel_values(source_mask) if value)
    candidate_foreground = sum(1 for value in _pixel_values(candidate_mask) if value)
    source_occupancy = source_foreground / (source_size[0] * source_size[1])
    candidate_occupancy = candidate_foreground / (candidate_size[0] * candidate_size[1])
    source_colors = {rgb for rgb, alpha in zip(_pixel_values(source.convert("RGB")), _pixel_values(source.getchannel("A"))) if alpha}
    candidate_colors = {rgb for rgb, alpha in zip(_pixel_values(candidate.convert("RGB")), _pixel_values(candidate.getchannel("A"))) if alpha}
    palette_retention = min(1.0, len(candidate_colors) / len(source_colors)) if source_colors else 1.0
    feature_results = [_feature_metrics(feature, mask, candidate_size) for feature, mask in features]
    reasons: list[str] = []
    if silhouette_iou < thresholds["silhouette_min_iou"]:
        reasons.append(f"silhouette IoU {silhouette_iou:.3f} is below {thresholds['silhouette_min_iou']:.3f}")
    if component_preservation < thresholds["component_min_preservation"]:
        reasons.append(
            f"connected-component preservation {component_preservation:.3f} is below {thresholds['component_min_preservation']:.3f}"
        )
    critical_lost = [feature["id"] for feature in feature_results if feature["importance"] == "critical" and feature["disappeared"]]
    if critical_lost:
        reasons.extend(f"critical feature '{feature_id}' disappeared" for feature_id in critical_lost)
    if palette_retention < thresholds["palette_min_retention"]:
        reasons.append(f"palette retention {palette_retention:.3f} is below {thresholds['palette_min_retention']:.3f}")
    return {
        "width": candidate_size[0],
        "height": candidate_size[1],
        "status": "AUTO_FAIL" if reasons else "AUTO_PASS_REVIEW_REQUIRED",
        "automatic_status": "AUTO_FAIL" if reasons else "AUTO_PASS_REVIEW_REQUIRED",
        "silhouette_preservation_iou": round(silhouette_iou, 6),
        "connected_components": {"source": source_components, "candidate": candidate_components, "preservation": round(component_preservation, 6)},
        "feature_area_preservation": feature_results,
        "small_feature_disappearance": [feature["id"] for feature in feature_results if feature["disappeared"]],
        "palette_collapse": {
            "source_unique_colors": len(source_colors),
            "candidate_unique_colors": len(candidate_colors),
            "retention": round(palette_retention, 6),
            "collapsed_color_count": max(0, len(source_colors) - len(candidate_colors)),
        },
        "bounding_box": {"source": source_bbox, "candidate": candidate_bbox, "change_from_scaled_source": bbox_change},
        "foreground_occupancy": {"source": round(source_occupancy, 6), "candidate": round(candidate_occupancy, 6), "change": round(candidate_occupancy - source_occupancy, 6)},
        "reasons": reasons,
    }


def run_resolution_gate(
    image_path: str | Path,
    output_dir: str | Path,
    *,
    profile_name: str,
    profile: dict[str, Any],
    project_root: str | Path,
    candidates: list[int] | None = None,
    extra_features: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    source_path = Path(image_path).expanduser().resolve()
    output = Path(output_dir).expanduser().resolve()
    if output.exists():
        raise ResolutionGateError(f"Resolution Gate output directory already exists: {output}")
    try:
        with Image.open(source_path) as opened:
            source = opened.convert("RGBA")
    except (OSError, UnidentifiedImageError) as exc:
        raise ResolutionGateError(f"Cannot open source image '{source_path}': {exc}") from exc
    width, height = source.size
    if width < 1 or height < 1:
        raise ResolutionGateError("Source image dimensions must be positive.")
    source_mask = _foreground_mask(source)
    features_cfg = profile.get("identity_features", [])
    if not isinstance(features_cfg, list):
        raise ResolutionGateError("Profile identity_features must be a list.")
    feature_defs = [*features_cfg, *(extra_features or [])]
    features = [(item, _resolve_feature_mask(item, source_mask, source.size, Path(project_root).resolve())) for item in feature_defs]
    empty_features = [feature["id"] for feature, mask in features if not any(_pixel_values(mask))]
    if empty_features:
        raise ResolutionGateError(f"Identity features contain no pixels in the source: {', '.join(empty_features)}")
    heights = candidates if candidates is not None else profile.get("logical_height_candidates", [128, 160, 192, 256])
    if not isinstance(heights, list) or not heights or any(not isinstance(value, int) or value < 1 for value in heights):
        raise ResolutionGateError("Resolution candidates must be a non-empty list of positive integer heights.")
    if len(set(heights)) != len(heights):
        raise ResolutionGateError("Resolution candidate heights must be unique.")
    gate_cfg = profile.get("resolution_gate", {})
    if not isinstance(gate_cfg, dict):
        raise ResolutionGateError("Profile resolution_gate must be a mapping.")
    thresholds = {
        "silhouette_min_iou": float(gate_cfg.get("silhouette_min_iou", 0.90)),
        "component_min_preservation": float(gate_cfg.get("component_min_preservation", 0.80)),
        "palette_min_retention": float(gate_cfg.get("palette_min_retention", 0.50)),
    }
    for key, value in thresholds.items():
        if not 0 <= value <= 1:
            raise ResolutionGateError(f"Threshold '{key}' must be between 0 and 1.")
    output.mkdir(parents=True)
    candidate_reports = []
    for target_height in heights:
        target_width = max(1, round(width * target_height / height))
        resized = source.resize((target_width, target_height), Image.Resampling.NEAREST)
        resized_mask = source_mask.resize((target_width, target_height), Image.Resampling.NEAREST)
        image_path_out = output / f"candidate_{target_height}.png"
        resized.save(image_path_out)
        candidate_reports.append({
            **_candidate_metrics(source, source_mask, resized, resized_mask, features, thresholds),
            "logical_height": target_height,
            "image": str(image_path_out),
            "sha256": _sha256(image_path_out),
        })
    accepted = [item["logical_height"] for item in candidate_reports if item["status"] == "AUTO_PASS_REVIEW_REQUIRED"]
    report = {
        "schema_version": 1,
        "status": "ANALYSIS_COMPLETE_REVIEW_REQUIRED",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {"path": str(source_path), "sha256": _sha256(source_path), "width": width, "height": height},
        "profile": profile_name,
        "thresholds": thresholds,
        "features": [{"id": feature["id"], "importance": str(feature.get("importance", "high")).lower(), "definition": "mask" if "mask" in feature else "region", "source_area": sum(1 for value in _pixel_values(mask) if value)} for feature, mask in features],
        "recommended_minimum_for_review": min(accepted) if accepted else None,
        "selected_resolution": None,
        "reviewed": False,
        "candidates": candidate_reports,
    }
    json_path = output / "resolution_report.json"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = ["# Resolution Gate report", "", f"- Status: `{report['status']}`", f"- Source: `{source_path}` ({width}x{height})", f"- Profile: `{profile_name}`", f"- Recommended minimum for review: `{report['recommended_minimum_for_review']}`", "- Selection: not selected; explicit human/orchestrator review is required.", "", "## Candidates", ""]
    for item in candidate_reports:
        lines += [f"### {item['logical_height']} px — `{item['status']}`", "", f"- Canvas: {item['width']}x{item['height']}", f"- Silhouette IoU: {item['silhouette_preservation_iou']:.3f}", f"- Components: {item['connected_components']['candidate']}/{item['connected_components']['source']} (preservation {item['connected_components']['preservation']:.3f})", f"- Palette: {item['palette_collapse']['candidate_unique_colors']}/{item['palette_collapse']['source_unique_colors']} colors retained ({item['palette_collapse']['retention']:.3f})", f"- Foreground occupancy: {item['foreground_occupancy']['candidate']:.3f} (source {item['foreground_occupancy']['source']:.3f})", f"- Lost features: {', '.join(item['small_feature_disappearance']) or 'none'}", f"- Reasons: {', '.join(item['reasons']) or 'none'}", f"- Image: `{item['image']}`", ""]
    (output / "resolution_report.md").write_text("\n".join(lines), encoding="utf-8")
    return report


def record_resolution_review(
    report_path: str | Path,
    *,
    selected_height: int,
    reason: str,
    reviewed_by: str | None = None,
    override_auto_fail: bool = False,
) -> Path:
    source_report = Path(report_path).expanduser().resolve()
    try:
        report = json.loads(source_report.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ResolutionGateError(f"Cannot read Resolution Gate report '{source_report}': {exc}") from exc
    candidates = {item.get("logical_height") for item in report.get("candidates", [])}
    if selected_height not in candidates:
        raise ResolutionGateError(f"Selected height {selected_height} is not present in the report candidates: {sorted(candidates)}")
    if not reason.strip():
        raise ResolutionGateError("A non-empty review reason is required to record an explicit selection.")
    candidate = next(item for item in report["candidates"] if item.get("logical_height") == selected_height)
    automatic_status = candidate.get("automatic_status", candidate.get("status"))
    if automatic_status not in {"AUTO_FAIL", "AUTO_PASS_REVIEW_REQUIRED"}:
        raise ResolutionGateError(f"Candidate has an unknown automatic status: {automatic_status!r}.")
    if automatic_status == "AUTO_FAIL" and not override_auto_fail:
        raise ResolutionGateError("This candidate is AUTO_FAIL; an explicit override flag and a non-empty review reason are required.")
    reviewed = {
        "schema_version": 1,
        "status": "SELECTED",
        "automatic_status": automatic_status,
        "review_status": "MANUAL_OVERRIDE_PASS" if automatic_status == "AUTO_FAIL" else "MANUAL_REVIEW_PASS",
        "selected_resolution": selected_height,
        "reviewed": True,
        "reason": reason.strip(),
        "reviewed_by": reviewed_by,
        "reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_report": str(source_report),
        "source_report_sha256": _sha256(source_report),
        "candidate_status": automatic_status,
        "override_auto_fail": automatic_status == "AUTO_FAIL",
    }
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    output = source_report.with_name(f"resolution_review_{stamp}.json")
    output.write_text(json.dumps(reviewed, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output
