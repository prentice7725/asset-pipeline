from __future__ import annotations

from collections import Counter, deque
from pathlib import Path
from typing import Any, Iterable

from PIL import Image, UnidentifiedImageError

from ..errors import PixelPipelineError


class ImageAnalysisError(PixelPipelineError):
    """An image could not be decoded or inspected."""


def _parse_color(value: str) -> tuple[int, int, int]:
    text = value.removeprefix("#")
    if len(text) == 8:
        text = text[:6]
    if len(text) != 6:
        raise ValueError(f"Palette color '{value}' must be #RRGGBB or #RRGGBBAA.")
    try:
        return tuple(int(text[index : index + 2], 16) for index in (0, 2, 4))  # type: ignore[return-value]
    except ValueError as exc:
        raise ValueError(f"Invalid palette color '{value}'.") from exc


def _color_distance(left: tuple[int, int, int], right: tuple[int, int, int]) -> float:
    return sum((a - b) ** 2 for a, b in zip(left, right)) ** 0.5


def _luminance(color: tuple[int, int, int]) -> float:
    return 0.2126 * color[0] + 0.7152 * color[1] + 0.0722 * color[2]


def _background_color(pixels: list[tuple[int, int, int, int]], width: int, height: int) -> tuple[int, int, int, int] | None:
    border: list[tuple[int, int, int, int]] = []
    border.extend(pixels[0:width])
    border.extend(pixels[(height - 1) * width : height * width])
    for y in range(1, max(1, height - 1)):
        border.append(pixels[y * width])
        if width > 1:
            border.append(pixels[y * width + width - 1])
    if not border:
        return None
    color, count = Counter(border).most_common(1)[0]
    return color if count / len(border) >= 0.2 else None


def _connected_components(mask: bytearray, width: int, height: int) -> list[dict[str, int]]:
    seen = bytearray(len(mask))
    components: list[dict[str, int]] = []
    for start, is_foreground in enumerate(mask):
        if not is_foreground or seen[start]:
            continue
        seen[start] = 1
        queue: deque[int] = deque([start])
        count = 0
        min_x = max_x = start % width
        min_y = max_y = start // width
        while queue:
            index = queue.popleft()
            x, y = index % width, index // width
            count += 1
            min_x, max_x = min(min_x, x), max(max_x, x)
            min_y, max_y = min(min_y, y), max(max_y, y)
            for ny in range(max(0, y - 1), min(height, y + 2)):
                row = ny * width
                for nx in range(max(0, x - 1), min(width, x + 2)):
                    neighbor = row + nx
                    if mask[neighbor] and not seen[neighbor]:
                        seen[neighbor] = 1
                        queue.append(neighbor)
        components.append({"area": count, "min_x": min_x, "min_y": min_y, "max_x": max_x, "max_y": max_y})
    components.sort(key=lambda item: item["area"], reverse=True)
    return components


def _silhouette(
    pixels: list[tuple[int, int, int, int]], width: int, height: int
) -> dict[str, Any]:
    has_transparency = any(alpha == 0 for _, _, _, alpha in pixels)
    inferred_background = None if has_transparency else _background_color(pixels, width, height)
    if has_transparency:
        mask = bytearray(1 if rgba[3] > 0 else 0 for rgba in pixels)
        method = "alpha"
    elif inferred_background is not None:
        mask = bytearray(1 if rgba != inferred_background else 0 for rgba in pixels)
        method = "border_color_inference"
    else:
        return {
            "measurable": False,
            "method": "unavailable",
            "foreground_pixels": None,
            "connected_component_count": None,
            "isolated_component_count": None,
            "isolated_pixel_count": None,
            "bounding_box": None,
        }

    foreground_count = sum(mask)
    components = _connected_components(mask, width, height) if foreground_count else []
    largest = components[0] if components else None
    bounds = (
        {
            "x": largest["min_x"],
            "y": largest["min_y"],
            "width": largest["max_x"] - largest["min_x"] + 1,
            "height": largest["max_y"] - largest["min_y"] + 1,
        }
        if largest
        else None
    )
    tiny_components = [component for component in components[1:] if component["area"] <= 2]
    return {
        "measurable": True,
        "method": method,
        "foreground_pixels": foreground_count,
        "connected_component_count": len(components),
        "largest_component_ratio": (largest["area"] / foreground_count) if largest and foreground_count else 0,
        "isolated_component_count": len(tiny_components),
        "isolated_pixel_count": sum(component["area"] for component in tiny_components),
        "bounding_box": bounds,
    }


def _edge_metrics(
    pixels: list[tuple[int, int, int, int]],
    width: int,
    height: int,
    max_colors: int,
    gradient_threshold: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    small_steps = 0
    differing_edges = 0
    edge_pixels = 0
    suspected_aa_pixels = 0
    counts = Counter(rgb for r, g, b, alpha in pixels if alpha > 0 for rgb in [(r, g, b)])
    small_color_limit = max(2, len(pixels) // 500)

    for y in range(height):
        row = y * width
        for x in range(width):
            index = row + x
            r, g, b, alpha = pixels[index]
            if alpha == 0:
                continue
            color = (r, g, b)
            neighbors: list[tuple[int, int, int]] = []
            if x + 1 < width and pixels[index + 1][3] > 0:
                neighbors.append(pixels[index + 1][:3])
            if y + 1 < height and pixels[index + width][3] > 0:
                neighbors.append(pixels[index + width][:3])
            for other in neighbors:
                distance = _color_distance(color, other)
                if distance > 0:
                    differing_edges += 1
                    if distance <= 24:
                        small_steps += 1

            local: list[tuple[int, int, int]] = []
            if x > 0 and pixels[index - 1][3] > 0:
                local.append(pixels[index - 1][:3])
            if x + 1 < width and pixels[index + 1][3] > 0:
                local.append(pixels[index + 1][:3])
            if y > 0 and pixels[index - width][3] > 0:
                local.append(pixels[index - width][:3])
            if y + 1 < height and pixels[index + width][3] > 0:
                local.append(pixels[index + width][:3])
            distinct_local = set(local)
            if len(distinct_local) >= 2 and len(distinct_local) != 1:
                luminances = sorted(_luminance(item) for item in distinct_local)
                low, high = luminances[0], luminances[-1]
                current_luminance = _luminance(color)
                if high - low >= 48:
                    edge_pixels += 1
                    if counts[color] <= small_color_limit and low + 4 < current_luminance < high - 4:
                        suspected_aa_pixels += 1

    smooth_ratio = small_steps / differing_edges if differing_edges else 0.0
    if len(counts) > max_colors * 4 and smooth_ratio >= gradient_threshold:
        gradient_level = "HIGH"
    elif len(counts) > max_colors and smooth_ratio >= gradient_threshold * (2 / 3):
        gradient_level = "MEDIUM"
    else:
        gradient_level = "LOW"
    gradient = {
        "level": gradient_level,
        "unique_visible_colors": len(counts),
        "small_rgb_step_ratio": round(smooth_ratio, 6),
        "small_rgb_step_edges": small_steps,
        "differing_edges": differing_edges,
        "small_step_distance_threshold": 24,
    }

    aa_ratio = suspected_aa_pixels / edge_pixels if edge_pixels else 0.0
    if aa_ratio >= 0.20 and suspected_aa_pixels >= 12:
        aa_level = "HIGH"
    elif aa_ratio >= 0.08 and suspected_aa_pixels >= 4:
        aa_level = "MEDIUM"
    else:
        aa_level = "LOW"
    antialias = {
        "level": aa_level,
        "suspected_pixels": suspected_aa_pixels,
        "edge_pixels_examined": edge_pixels,
        "suspected_edge_pixel_ratio": round(aa_ratio, 6),
        "method": "rare intermediate colors on high-contrast local edges; heuristic",
    }
    return gradient, antialias


def analyze_image(
    image_path: str | Path,
    *,
    max_colors: int = 32,
    allowed_palette: Iterable[str] | None = None,
    target_width: int | None = None,
    target_height: int | None = None,
    gradient_threshold: float = 0.18,
) -> dict[str, Any]:
    path = Path(image_path).expanduser().resolve()
    if max_colors < 1:
        raise ValueError("max_colors must be at least 1.")
    if (target_width is None) != (target_height is None):
        raise ValueError("target_width and target_height must be provided together.")
    try:
        with Image.open(path) as source:
            source.seek(0)
            image = source.convert("RGBA")
    except (OSError, UnidentifiedImageError) as exc:
        raise ImageAnalysisError(f"Cannot open image '{path}': {exc}") from exc

    width, height = image.size
    pixel_data = image.get_flattened_data() if hasattr(image, "get_flattened_data") else image.getdata()
    pixels = list(pixel_data)
    visible_pixels = [rgba for rgba in pixels if rgba[3] > 0]
    colors = Counter(rgba[:3] for rgba in visible_pixels)
    alpha_counts = Counter(rgba[3] for rgba in pixels)
    semi_transparent = sum(count for alpha, count in alpha_counts.items() if alpha not in (0, 255))
    unique_colors = len(colors)
    palette = {_parse_color(color) for color in allowed_palette} if allowed_palette is not None else None
    if palette is not None and not palette:
        raise ValueError("Allowed palette must contain at least one color.")
    off_palette = sum(
        count for (red, green, blue), count in colors.items() if palette is not None and (red, green, blue) not in palette
    ) if palette is not None else 0
    off_palette_ratio = off_palette / len(visible_pixels) if visible_pixels else 0.0
    budget_excess = max(0, unique_colors - max_colors)
    gradient, antialias = _edge_metrics(pixels, width, height, max_colors, gradient_threshold)

    if palette is not None and colors:
        nearest_distances = [
            min(_color_distance(rgb, allowed) for allowed in palette)
            for rgb in colors
        ]
        weighted_distance = sum(
            min(_color_distance((red, green, blue), allowed) for allowed in palette) * count
            for (red, green, blue), count in colors.items()
        ) / max(1, len(visible_pixels))
        palette_distance: dict[str, float | int | None] = {
            "mean_nearest_rgb_distance": round(weighted_distance, 4),
            "max_nearest_rgb_distance": round(max(nearest_distances), 4),
        }
    else:
        palette_distance = {"mean_nearest_rgb_distance": None, "max_nearest_rgb_distance": None}

    resolution_matches = (width == target_width and height == target_height) if target_width is not None else None
    silhouette = _silhouette(pixels, width, height)
    failure_reasons: list[str] = []
    fix_reasons: list[str] = []
    review_reasons: list[str] = []
    if resolution_matches is False:
        failure_reasons.append(f"resolution mismatch: got {width}x{height}, expected {target_width}x{target_height}")
    if palette is not None and off_palette:
        if off_palette_ratio >= 0.01:
            failure_reasons.append(f"{off_palette} visible pixels are outside the configured palette")
        else:
            fix_reasons.append(f"{off_palette} visible pixels are outside the configured palette")
    elif palette is None and budget_excess:
        message = f"unique colors exceed the configured budget ({unique_colors} > {max_colors})"
        if gradient["level"] == "HIGH":
            failure_reasons.append(message)
        else:
            fix_reasons.append(message)
    if semi_transparent:
        message = f"{semi_transparent} pixels have non-binary alpha"
        if semi_transparent / max(1, len(pixels)) > 0.01:
            failure_reasons.append(message)
        else:
            fix_reasons.append(message)
    if gradient["level"] == "HIGH":
        failure_reasons.append("high gradient suspicion from dense small RGB steps")
    if antialias["level"] == "HIGH":
        failure_reasons.append("high anti-alias suspicion on high-contrast edges")
    if silhouette["measurable"] and silhouette.get("isolated_pixel_count", 0) > max(4, round(silhouette["foreground_pixels"] * 0.005)):
        review_reasons.append("multiple tiny detached silhouette clusters need visual review")
    if not silhouette["measurable"]:
        review_reasons.append("silhouette could not be isolated from alpha or a uniform border color")
    if resolution_matches is None:
        review_reasons.append("no target resolution was supplied")

    if failure_reasons:
        status = "FAIL"
    elif fix_reasons:
        status = "PASS_WITH_FIX"
    elif review_reasons:
        status = "REVIEW_REQUIRED"
    else:
        status = "PASS"
    return {
        "status": status,
        "image": str(path),
        "resolution": {
            "width": width,
            "height": height,
            "target_width": target_width,
            "target_height": target_height,
            "matches_target": resolution_matches,
            "interpolation_evidence": gradient["level"],
        },
        "alpha": {
            "policy": "binary",
            "transparent_pixels": alpha_counts.get(0, 0),
            "opaque_pixels": alpha_counts.get(255, 0),
            "semi_transparent_pixels": semi_transparent,
            "unique_alpha_values": sorted(alpha_counts),
        },
        "palette": {
            "unique_color_count": unique_colors,
            "max_colors": max_colors,
            "color_budget_excess": budget_excess,
            "allowed_palette": [f"#{r:02X}{g:02X}{b:02X}" for r, g, b in sorted(palette)] if palette is not None else None,
            "off_palette_pixel_count": off_palette,
            "off_palette_pixel_ratio": round(off_palette_ratio, 6),
            "distance_to_allowed_palette": palette_distance,
        },
        "gradient_suspicion": gradient,
        "anti_alias_suspicion": antialias,
        "silhouette": silhouette,
        "reasons": {"failure": failure_reasons, "fix": fix_reasons, "review": review_reasons},
    }
