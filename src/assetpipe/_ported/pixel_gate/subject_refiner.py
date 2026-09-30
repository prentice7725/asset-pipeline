from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from PIL import Image, ImageChops, ImageDraw

from .analyzer import analyze_image


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _flatten(image: Image.Image) -> list[tuple[int, int, int, int]]:
    pixels = image.get_flattened_data() if hasattr(image, "get_flattened_data") else image.getdata()
    return list(pixels)


def _hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def _rgb(value: str) -> tuple[int, int, int]:
    text = value.removeprefix("#")
    if len(text) == 8:
        text = text[:6]
    if len(text) != 6:
        raise ValueError(f"Palette color {value!r} must be #RRGGBB or #RRGGBBAA.")
    return tuple(int(text[index : index + 2], 16) for index in (0, 2, 4))  # type: ignore[return-value]


def _lab(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    linear = []
    for channel in rgb:
        value = channel / 255.0
        linear.append(((value + 0.055) / 1.055) ** 2.4 if value > 0.04045 else value / 12.92)
    red, green, blue = linear
    x = (red * 0.4124564 + green * 0.3575761 + blue * 0.1804375) / 0.95047
    y = red * 0.2126729 + green * 0.7151522 + blue * 0.0721750
    z = (red * 0.0193339 + green * 0.1191920 + blue * 0.9503041) / 1.08883
    epsilon = 216 / 24389
    kappa = 24389 / 27

    def transform(value: float) -> float:
        return value ** (1 / 3) if value > epsilon else (kappa * value + 16) / 116

    fx, fy, fz = transform(x), transform(y), transform(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def _lab_distance_squared(left: tuple[float, float, float], right: tuple[float, float, float]) -> float:
    return sum((a - b) ** 2 for a, b in zip(left, right))


def delta_e76(left: tuple[int, int, int], right: tuple[int, int, int]) -> float:
    """CIE76 distance after the same sRGB-to-CIELAB conversion used by projection."""
    return math.sqrt(_lab_distance_squared(_lab(left), _lab(right)))


def _weighted_quantile(values: list[tuple[float, int]], quantile: float) -> float:
    total = sum(count for _, count in values)
    if not total:
        return 0.0
    threshold = max(1, math.ceil(total * quantile))
    cumulative = 0
    for value, count in sorted(values):
        cumulative += count
        if cumulative >= threshold:
            return value
    return max(value for value, _ in values)


def _delta_e_summary(
    foreground: Counter[tuple[int, int, int]], palette: list[tuple[int, int, int]]
) -> dict[str, float]:
    distances = [
        (min(delta_e76(color, candidate) for candidate in palette), count)
        for color, count in foreground.items()
    ]
    total = sum(count for _, count in distances)
    mean = sum(distance * count for distance, count in distances) / max(1, total)
    return {
        "mean_foreground_deltaE": round(mean, 6),
        "median_foreground_deltaE": round(_weighted_quantile(distances, 0.5), 6),
        "p95_foreground_deltaE": round(_weighted_quantile(distances, 0.95), 6),
        "max_foreground_deltaE": round(max((distance for distance, _ in distances), default=0.0), 6),
    }


def _infer_background(pixels: list[tuple[int, int, int, int]], width: int, height: int) -> tuple[int, int, int, int]:
    border = pixels[:width] + pixels[(height - 1) * width : height * width]
    for y in range(1, max(1, height - 1)):
        border.append(pixels[y * width])
        if width > 1:
            border.append(pixels[y * width + width - 1])
    if not border:
        raise ValueError("Cannot infer a background color from an empty image border.")
    background, count = Counter(border).most_common(1)[0]
    if count / len(border) < 0.2:
        raise ValueError("No stable border background color was found; subject normalization stopped safely.")
    return background


def _background_mask(
    pixels: list[tuple[int, int, int, int]], width: int, height: int, background: tuple[int, int, int, int], tolerance: int
) -> bytearray:
    if tolerance < 0 or tolerance > 64:
        raise ValueError("Background tolerance must be between 0 and 64 RGB levels.")
    limit = tolerance * tolerance
    eligible = bytearray(
        1 if pixel[3] == 0 or sum((pixel[channel] - background[channel]) ** 2 for channel in range(3)) <= limit else 0
        for pixel in pixels
    )
    # Every exact match of the modal border color is matte, including enclosed holes.
    # Near-color matte pixels are included only when connected to the image edge.
    mask = bytearray(
        1 if pixel[3] == 0 or pixel[:3] == background[:3] else 0
        for pixel in pixels
    )
    queue: deque[int] = deque()
    for x in range(width):
        for y in (0, height - 1):
            index = y * width + x
            if eligible[index] and not mask[index]:
                mask[index] = 1
                queue.append(index)
    for y in range(1, max(1, height - 1)):
        for x in (0, width - 1):
            index = y * width + x
            if eligible[index] and not mask[index]:
                mask[index] = 1
                queue.append(index)
    while queue:
        index = queue.popleft()
        x, y = index % width, index // width
        for neighbor in (
            index - 1 if x > 0 else -1,
            index + 1 if x + 1 < width else -1,
            index - width if y > 0 else -1,
            index + width if y + 1 < height else -1,
        ):
            if neighbor >= 0 and eligible[neighbor] and not mask[neighbor]:
                mask[neighbor] = 1
                queue.append(neighbor)
    if sum(mask) < width * height * 0.2:
        raise ValueError("Border-connected background covers less than 20% of the image; normalization stopped safely.")
    return mask


def _bbox(mask: bytearray, width: int, height: int) -> tuple[int, int, int, int]:
    xs: list[int] = []
    ys: list[int] = []
    for index, is_background in enumerate(mask):
        if not is_background:
            xs.append(index % width)
            ys.append(index // width)
    if not xs:
        raise ValueError("No foreground subject was detected.")
    return min(xs), min(ys), max(xs) + 1, max(ys) + 1


def extract_master_foreground_palette(
    master_export: str | Path,
    *,
    background_tolerance: int = 0,
) -> dict[str, Any]:
    source_path = Path(master_export).expanduser().resolve()
    if not source_path.is_file():
        raise ValueError(f"Phase 6 master export does not exist: {source_path}")
    with Image.open(source_path) as opened:
        opened.seek(0)
        image = opened.convert("RGBA")
    pixels = _flatten(image)
    background = _infer_background(pixels, image.width, image.height)
    background_mask = _background_mask(pixels, image.width, image.height, background, background_tolerance)
    foreground_colors = sorted({_hex(pixel[:3]) for pixel, is_background in zip(pixels, background_mask) if not is_background and pixel[3] > 0})
    if not foreground_colors:
        raise ValueError("The Phase 6 master export has no visible foreground palette.")
    bounds = _bbox(background_mask, image.width, image.height)
    left, top, right, bottom = bounds
    return {
        "schema_version": 1,
        "name": "mushroom_courier_master_palette",
        "description": "Exact visible foreground colors extracted from the passing Mushroom Courier Phase 6 Static Pixel Master export. Background is excluded.",
        "source_master_export": str(source_path),
        "source_sha256": _sha256(source_path),
        "source_dimensions": [image.width, image.height],
        "background_color_excluded": _hex(background[:3]),
        "background_tolerance": background_tolerance,
        "foreground_bounding_box": {"x": left, "y": top, "width": right - left, "height": bottom - top},
        "target_occupancy": round((bottom - top) / image.height, 8),
        "bottom_center_anchor": [round((left + right) / 2 / image.width, 8), round(bottom / image.height, 8)],
        "color_count": len(foreground_colors),
        "colors": foreground_colors,
    }


def separate_candidate_foreground(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    background_tolerance: int = 0,
) -> dict[str, Any]:
    """Separate a candidate's border matte without assuming a registered master exists."""
    source_path = Path(input_path).expanduser().resolve()
    destination = Path(output_dir).expanduser().resolve()
    if not source_path.is_file():
        raise ValueError(f"Candidate image does not exist: {source_path}")
    if destination.exists():
        raise ValueError(f"Foreground separation output directory already exists; choose a new path: {destination}")
    with Image.open(source_path) as opened:
        opened.seek(0)
        source = opened.convert("RGBA")
    pixels = _flatten(source)
    background = _infer_background(pixels, source.width, source.height)
    background_mask = _background_mask(pixels, source.width, source.height, background, background_tolerance)
    foreground = source.copy()
    foreground_pixels = foreground.load()
    for index, is_background in enumerate(background_mask):
        if is_background:
            foreground_pixels[index % source.width, index // source.width] = (0, 0, 0, 0)
    bounds = _bbox(background_mask, source.width, source.height)
    left, top, right, bottom = bounds
    destination.mkdir(parents=True)
    # Keep a byte-for-byte copy of the original source before deriving any transparent view.
    preserved = destination / "candidate_preserved.png"
    preserved.write_bytes(source_path.read_bytes())
    foreground_path = destination / "foreground_only.png"
    foreground.save(foreground_path)
    matte = Image.new("RGBA", source.size, (0, 0, 0, 0))
    matte_pixels = matte.load()
    for index, is_background in enumerate(background_mask):
        if is_background:
            matte_pixels[index % source.width, index // source.width] = pixels[index]
    matte_path = destination / "background_matte.png"
    matte.save(matte_path)
    mask_path = destination / "foreground_mask.png"
    Image.frombytes("L", source.size, bytes(255 if not value else 0 for value in background_mask)).save(mask_path)
    report = {
        "schema_version": 1,
        "status": "BACKGROUND_SEPARATED_NO_MASTER",
        "pipeline_role": "BACKGROUND_SEPARATION_BOOTSTRAP",
        "input": str(source_path),
        "input_sha256": _sha256(source_path),
        "background": {
            "segmentation": "4-connected border flood fill from modal border color",
            "tolerance_rgb": background_tolerance,
            "source_color": _hex(background[:3]),
            "source_alpha": background[3],
            "background_pixels_excluded_from_foreground_analysis": True,
        },
        "foreground": {
            "pixel_count": sum(not value for value in background_mask),
            "bounding_box_xyxy": [left, top, right, bottom],
            "bounding_box_width": right - left,
            "bounding_box_height": bottom - top,
        },
        "master_palette_state": "SKIPPED_NO_APPROVED_STATIC_MASTER",
        "occupancy_normalization_state": "SKIPPED_NO_APPROVED_STATIC_MASTER",
        "artifacts": {
            "candidate_preserved": str(preserved),
            "foreground_only": str(foreground_path),
            "background_matte": str(matte_path),
            "foreground_mask": str(mask_path),
        },
        "source_preserved": True,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    (destination / "foreground_separation_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return report


def refine_subject_image(
    input_path: str | Path,
    reference_export: str | Path,
    output_dir: str | Path,
    *,
    profile_name: str,
    palette_name: str = "mushroom_courier_master_palette",
    palette_colors: Iterable[str],
    background_tolerance: int = 0,
    alpha_threshold: int = 128,
    max_colors: int = 32,
    gradient_threshold: float = 0.18,
) -> dict[str, Any]:
    source_path = Path(input_path).expanduser().resolve()
    reference_path = Path(reference_export).expanduser().resolve()
    destination = Path(output_dir).expanduser().resolve()
    if not source_path.is_file() or not reference_path.is_file():
        raise ValueError("Both the existing candidate and approved master export must exist.")
    if destination.exists():
        raise ValueError(f"Subject-refine output directory already exists; choose a new path: {destination}")
    if not 0 <= alpha_threshold <= 255:
        raise ValueError("Alpha threshold must be between 0 and 255.")
    palette_rgb = [_rgb(color) for color in palette_colors]
    if not palette_rgb or len(set(palette_rgb)) != len(palette_rgb):
        raise ValueError("The registered master foreground palette must contain unique colors.")
    palette_hex = [_hex(color) for color in palette_rgb]

    with Image.open(source_path) as opened:
        opened.seek(0)
        source = opened.convert("RGBA")
    with Image.open(reference_path) as opened:
        opened.seek(0)
        reference = opened.convert("RGBA")
    source_pixels = _flatten(source)
    reference_pixels = _flatten(reference)
    source_background = _infer_background(source_pixels, source.width, source.height)
    source_background_mask = _background_mask(source_pixels, source.width, source.height, source_background, background_tolerance)
    reference_background = _infer_background(reference_pixels, reference.width, reference.height)
    reference_background_mask = _background_mask(
        reference_pixels, reference.width, reference.height, reference_background, background_tolerance
    )
    source_bounds = _bbox(source_background_mask, source.width, source.height)
    reference_bounds = _bbox(reference_background_mask, reference.width, reference.height)
    ref_left, ref_top, ref_right, ref_bottom = reference_bounds
    target_occupancy = (ref_bottom - ref_top) / reference.height
    anchor_x_ratio = ((ref_left + ref_right) / 2) / reference.width
    anchor_y_ratio = ref_bottom / reference.height

    # Refuse to repaint a genuinely textured backdrop when the subject is moved.
    source_background_colors = {
        pixel[:3] for pixel, is_background in zip(source_pixels, source_background_mask) if is_background and pixel[3] > 0
    }
    background_drift = max(
        (
            math.sqrt(sum((color[channel] - source_background[channel]) ** 2 for channel in range(3)))
            for color in source_background_colors
        ),
        default=0.0,
    )
    if background_drift > max(2, background_tolerance):
        raise ValueError(
            f"Background varies by RGB distance {background_drift:.2f}; moving the subject would require unsafe background reconstruction."
        )

    src_left, src_top, src_right, src_bottom = source_bounds
    source_box_width, source_box_height = src_right - src_left, src_bottom - src_top
    target_height = max(1, round(source.height * target_occupancy))
    scale = target_height / source_box_height
    target_width = max(1, round(source_box_width * scale))
    target_left = round(source.width * anchor_x_ratio - target_width / 2)
    target_bottom = round(source.height * anchor_y_ratio)
    target_top = target_bottom - target_height
    if target_left < 0 or target_top < 0 or target_left + target_width > source.width or target_bottom > source.height:
        raise ValueError("Master occupancy and anchor place the subject outside the candidate canvas.")

    patch = Image.new("RGBA", (source_box_width, source_box_height), (0, 0, 0, 0))
    patch_pixels = patch.load()
    for y in range(source_box_height):
        for x in range(source_box_width):
            source_index = (src_top + y) * source.width + src_left + x
            if not source_background_mask[source_index]:
                pixel = source_pixels[source_index]
                alpha = 0 if pixel[3] < alpha_threshold else 255
                if alpha:
                    patch_pixels[x, y] = (pixel[0], pixel[1], pixel[2], alpha)
    normalized_patch = patch.resize((target_width, target_height), Image.Resampling.NEAREST)

    # The selected cohort has a flat, border-connected background. Its original color is
    # retained; only pixels formerly occupied by foreground are cleared before placement.
    normalized = source.copy()
    normalized_pixels = normalized.load()
    bg_rgba = (source_background[0], source_background[1], source_background[2], source_background[3])
    for index, is_background in enumerate(source_background_mask):
        if not is_background:
            normalized_pixels[index % source.width, index // source.width] = bg_rgba
    normalized.alpha_composite(normalized_patch, (target_left, target_top))
    normalized_pixels_list = _flatten(normalized)
    normalized_bg_mask = _background_mask(
        normalized_pixels_list, normalized.width, normalized.height, source_background, background_tolerance
    )

    # Project only opaque subject pixels, using the approved palette and perceptual CIE76
    # distance. Background pixels are never candidates in the palette lookup.
    lab_palette = [_lab(color) for color in palette_rgb]
    foreground_before = Counter(
        pixel[:3] for pixel, is_background in zip(normalized_pixels_list, normalized_bg_mask)
        if not is_background and pixel[3] > 0
    )
    foreground_pixel_count_before_projection = sum(foreground_before.values())
    exact_palette_match_count_before_projection = sum(
        count for color, count in foreground_before.items() if color in set(palette_rgb)
    )
    delta_e_metrics = _delta_e_summary(foreground_before, palette_rgb)
    color_lookup: dict[tuple[int, int, int], tuple[int, int, int]] = {}
    for color in foreground_before:
        color_lab = _lab(color)
        color_lookup[color] = min(
            palette_rgb,
            key=lambda allowed, values=lab_palette, lab_value=color_lab: _lab_distance_squared(
                lab_value, values[palette_rgb.index(allowed)]
            ),
        )
    refined = normalized.copy()
    refined_pixels = refined.load()
    normalized_flat = _flatten(normalized)
    changed_foreground_pixels = 0
    for index, pixel in enumerate(normalized_flat):
        if normalized_bg_mask[index] or pixel[3] == 0:
            continue
        mapped = color_lookup[pixel[:3]]
        changed_foreground_pixels += int(mapped != pixel[:3])
        refined_pixels[index % refined.width, index // refined.width] = (*mapped, pixel[3])
    refined_flat = _flatten(refined)
    refined_bg_mask = _background_mask(refined_flat, refined.width, refined.height, source_background, background_tolerance)
    foreground_after = Counter(
        pixel[:3] for pixel, is_background in zip(refined_flat, refined_bg_mask)
        if not is_background and pixel[3] > 0
    )
    background_changed_pixels = 0
    changed_background_denominator = sum(refined_bg_mask)
    foreground_denominator = sum(not value for value in refined_bg_mask)
    source_flat = source_pixels
    full_changed_pixels = sum(left != right for left, right in zip(source_flat, refined_flat))
    total_pixels = source.width * source.height
    destination.mkdir(parents=True)
    normalized.save(destination / "normalized_pre_palette.png")
    refined.save(destination / "refined.png")
    Image.frombytes("L", source.size, bytes(0 if value else 255 for value in normalized_bg_mask)).save(destination / "foreground_mask.png")
    source_foreground = source.copy()
    source_foreground_pixels = source_foreground.load()
    for index, is_background in enumerate(source_background_mask):
        if is_background:
            source_foreground_pixels[index % source.width, index // source.width] = (0, 0, 0, 0)
    source_foreground.save(destination / "foreground_source.png")
    source_matte = Image.new("RGBA", source.size, (0, 0, 0, 0))
    source_matte_pixels = source_matte.load()
    for index, is_background in enumerate(source_background_mask):
        if is_background:
            source_matte_pixels[index % source.width, index // source.width] = source_pixels[index]
    source_matte.save(destination / "background_matte.png")
    refined_foreground = refined.copy()
    refined_foreground_pixels = refined_foreground.load()
    for index, is_background in enumerate(refined_bg_mask):
        if is_background:
            refined_foreground_pixels[index % refined.width, index // refined.width] = (0, 0, 0, 0)
    refined_foreground.save(destination / "foreground_refined.png")
    diff = ImageChops.difference(source.convert("RGB"), refined.convert("RGB"))
    diff = diff.convert("RGB")
    diff.save(destination / "diff.png")
    after_analysis = analyze_image(
        destination / "foreground_refined.png",
        max_colors=max_colors,
        allowed_palette=[*palette_hex, _hex(source_background[:3])],
        target_width=source.width,
        target_height=source.height,
        gradient_threshold=gradient_threshold,
    )
    left, top, right, bottom = _bbox(refined_bg_mask, refined.width, refined.height)
    foreground_palette_match_pixels = sum(count for color, count in foreground_after.items() if color in set(palette_rgb))
    report = {
        "schema_version": 1,
        "status": "SAFE_SUBJECT_REFINE_COMPLETED",
        "pipeline_role": "BACKGROUND_SEPARATION_SUBJECT_NORMALIZATION_MASTER_PALETTE_REFINE",
        "input": str(source_path),
        "input_sha256": _sha256(source_path),
        "reference_master_export": str(reference_path),
        "reference_master_sha256": _sha256(reference_path),
        "profile": profile_name,
        "palette_name": palette_name,
        "palette_projection": "nearest_CIE76_in_sRGB_to_CIELAB",
        "palette_colors": palette_hex,
        "background": {
            "segmentation": "4-connected border flood fill from modal border color",
            "tolerance_rgb": background_tolerance,
            "source_color": _hex(source_background[:3]),
            "source_alpha": source_background[3],
            "max_background_color_drift": round(background_drift, 4),
            "background_pixels_excluded_from_palette": True,
        },
        "subject_normalization": {
            "source_bbox_xyxy": [src_left, src_top, src_right, src_bottom],
            "source_bbox_width": source_box_width,
            "source_bbox_height": source_box_height,
            "reference_bbox_xyxy": [ref_left, ref_top, ref_right, ref_bottom],
            "reference_canvas": [reference.width, reference.height],
            "target_occupancy": round(target_occupancy, 8),
            "target_anchor_bottom_center_ratio": [round(anchor_x_ratio, 8), round(anchor_y_ratio, 8)],
            "scale": round(scale, 8),
            "resized_bbox": [target_left, target_top, target_left + target_width, target_bottom],
            "resize_filter": "NEAREST",
            "aspect_ratio_before": round(source_box_width / source_box_height, 8),
            "aspect_ratio_after": round(target_width / target_height, 8),
            "canvas_preserved": [source.width, source.height],
            "alpha_threshold": alpha_threshold,
        },
        "foreground_palette_statistics": {
            "before_unique_colors": len(foreground_before),
            "after_unique_colors": len(foreground_after),
            "after_colors": sorted(_hex(color) for color in foreground_after),
            "palette_identity_pixel_ratio": round(foreground_palette_match_pixels / max(1, sum(foreground_after.values())), 8),
            "exact_palette_match_ratio_before_projection": round(
                exact_palette_match_count_before_projection / max(1, foreground_pixel_count_before_projection), 8
            ),
            **delta_e_metrics,
        },
        "changes": {
            "foreground_changed_pixels": changed_foreground_pixels,
            "foreground_changed_ratio": round(changed_foreground_pixels / max(1, foreground_denominator), 8),
            "foreground_changed_ratio_role": "DIAGNOSTIC_ONLY",
            "foreground_pixel_count_after_normalization": foreground_denominator,
            "background_changed_pixels": background_changed_pixels,
            "background_changed_ratio": round(background_changed_pixels / max(1, changed_background_denominator), 8),
            "background_pixel_count_after_normalization": changed_background_denominator,
            "full_canvas_changed_pixels": full_changed_pixels,
            "full_canvas_changed_ratio": round(full_changed_pixels / max(1, total_pixels), 8),
            "full_canvas_changed_ratio_role": "DIAGNOSTIC_ONLY",
        },
        "after_analysis": after_analysis,
        "artifacts": {
            "normalized_pre_palette": str(destination / "normalized_pre_palette.png"),
            "refined": str(destination / "refined.png"),
            "foreground_mask": str(destination / "foreground_mask.png"),
            "foreground_source": str(destination / "foreground_source.png"),
            "foreground_refined": str(destination / "foreground_refined.png"),
            "background_matte": str(destination / "background_matte.png"),
            "diff": str(destination / "diff.png"),
        },
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    (destination / "subject_refine_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report_lines = [
        "# Background-separated subject refinement",
        "",
        f"- Status: `{report['status']}`",
        f"- Foreground palette: `{report['palette_name']}` ({len(palette_hex)} registered colors)",
        f"- Background: `{report['background']['source_color']}`; excluded from palette projection",
        f"- Target occupancy from Phase 6 master: {target_occupancy:.4f}",
        f"- Bottom-center anchor: {anchor_x_ratio:.4f}, {anchor_y_ratio:.4f}",
        f"- Subject scale: {scale:.4f}; aspect ratio {source_box_width / source_box_height:.4f} → {target_width / target_height:.4f}",
        f"- Foreground changed: {changed_foreground_pixels}/{foreground_denominator} ({report['changes']['foreground_changed_ratio']:.2%})",
        f"- Background changed by palette projection: {background_changed_pixels}/{changed_background_denominator} ({report['changes']['background_changed_ratio']:.2%})",
        f"- Full-canvas changed ratio (diagnostic): {report['changes']['full_canvas_changed_ratio']:.2%}",
        f"- Re-analysis status: `{after_analysis['status']}`",
        "",
        "Foreground is 4-connected border-segmented. The source background color is retained, subject geometry is uniformly nearest-neighbor scaled, and only foreground colors are projected.",
        "",
    ]
    (destination / "subject_refine_report.md").write_text("\n".join(report_lines), encoding="utf-8")
    return report
