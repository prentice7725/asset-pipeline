from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from PIL import Image

from .analyzer import analyze_image


def _pixels(image: Image.Image) -> list[tuple[int, int, int, int]]:
    values = image.get_flattened_data() if hasattr(image, "get_flattened_data") else image.getdata()
    return list(values)


def _rgb(color: str) -> tuple[int, int, int]:
    value = color.removeprefix("#")
    if len(value) == 8:
        value = value[:6]
    if len(value) != 6:
        raise ValueError(f"Palette color '{color}' must be #RRGGBB or #RRGGBBAA.")
    try:
        return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))  # type: ignore[return-value]
    except ValueError as exc:
        raise ValueError(f"Invalid palette color '{color}'.") from exc


def _distance(left: tuple[int, int, int], right: tuple[int, int, int]) -> int:
    return sum((a - b) ** 2 for a, b in zip(left, right))


def _changed_pixels(before: Image.Image, after: Image.Image) -> int:
    width, height = max(before.width, after.width), max(before.height, after.height)
    left = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    right = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    left.alpha_composite(before.convert("RGBA"), (0, 0))
    right.alpha_composite(after.convert("RGBA"), (0, 0))
    left_pixels, right_pixels = _pixels(left), _pixels(right)
    return sum(
        1
        for first, second in zip(left_pixels, right_pixels)
        if first[3] != second[3] or (first[3] > 0 and second[3] > 0 and first[:3] != second[:3])
    )


def _operation(
    name: str,
    before: Image.Image,
    after: Image.Image,
    *,
    applied: bool,
    parameters: dict[str, Any] | None = None,
    changed_pixels: int | None = None,
) -> dict[str, Any]:
    return {
        "operation": name,
        "applied": applied,
        "changed_pixels": changed_pixels if changed_pixels is not None else (_changed_pixels(before, after) if applied else 0),
        "canvas_before": [before.width, before.height],
        "canvas_after": [after.width, after.height],
        "parameters": parameters or {},
    }


def _nearest_palette(image: Image.Image, colors: Iterable[str]) -> tuple[Image.Image, int]:
    palette = [_rgb(color) for color in colors]
    if not palette:
        raise ValueError("Palette projection requires at least one allowed color.")
    source = image.convert("RGBA")
    source_pixels = _pixels(source)
    counts = Counter(pixel[:3] for pixel in source_pixels if pixel[3] > 0)
    projected = {
        color: min(palette, key=lambda allowed: (_distance(color, allowed), palette.index(allowed)))
        for color in counts
    }
    data = [
        (*projected[pixel[:3]], pixel[3]) if pixel[3] > 0 else pixel
        for pixel in source_pixels
    ]
    output = Image.new("RGBA", source.size)
    output.putdata(data)
    changed = sum(count for color, count in counts.items() if projected[color] != color)
    return output, changed


def _trim_transparent(image: Image.Image) -> tuple[Image.Image, bool, list[int] | None]:
    if image.getchannel("A").getextrema() == (255, 255):
        return image.copy(), False, None
    bounds = image.getchannel("A").getbbox()
    if bounds is None:
        raise ValueError("Cannot trim an entirely transparent image.")
    trimmed = image.crop(bounds)
    return trimmed, bounds != (0, 0, image.width, image.height), list(bounds)


def _pad_canvas(image: Image.Image, width: int, height: int, anchor: str) -> tuple[Image.Image, bool, list[int]]:
    if width < image.width or height < image.height:
        raise ValueError(
            f"Canvas pad size {width}x{height} is smaller than the current image {image.width}x{image.height}; cropping is not allowed."
        )
    if anchor not in {"center", "bottom-anchor"}:
        raise ValueError("Canvas anchor must be 'center' or 'bottom-anchor'.")
    x = (width - image.width) // 2
    y = (height - image.height) // 2 if anchor == "center" else height - image.height
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    canvas.alpha_composite(image.convert("RGBA"), (x, y))
    return canvas, canvas.size != image.size or (x != 0 or y != 0), [x, y]


def _remove_explicit_isolated_pixels(
    image: Image.Image, coordinates: Iterable[tuple[int, int]]
) -> tuple[Image.Image, int, list[dict[str, Any]]]:
    output = image.convert("RGBA").copy()
    pixels = output.load()
    changed = 0
    decisions: list[dict[str, Any]] = []
    for x, y in coordinates:
        if not (0 <= x < output.width and 0 <= y < output.height):
            raise ValueError(f"Isolated-pixel coordinate ({x}, {y}) is outside the {output.width}x{output.height} image.")
        if x == 0 or y == 0 or x == output.width - 1 or y == output.height - 1:
            decisions.append({"x": x, "y": y, "removed": False, "reason": "border pixels are never auto-removed"})
            continue
        neighbors = [pixels[nx, ny] for ny in range(y - 1, y + 2) for nx in range(x - 1, x + 2) if (nx, ny) != (x, y)]
        common = Counter(neighbors).most_common(1)[0]
        same_color_count = sum(1 for color in neighbors if color == common[0])
        is_isolated = (
            same_color_count == 8
            and pixels[x, y] != common[0]
            and pixels[x, y][3] > 0
            and common[0][3] > 0
        )
        if is_isolated:
            pixels[x, y] = common[0]
            changed += 1
            decisions.append({"x": x, "y": y, "removed": True, "replacement_rgba": list(common[0])})
        else:
            decisions.append({"x": x, "y": y, "removed": False, "reason": "not an isolated pixel with eight identical opaque neighbors"})
    return output, changed, decisions


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Safe Refine Report",
        "",
        f"- **Status:** `{report['status']}`",
        f"- **Status reason:** {report['status_reason']}",
        f"- **Profile:** `{report['profile']}`",
        f"- **Input SHA-256:** `{report['input_sha256']}`",
        f"- **Output SHA-256:** `{report['output_sha256']}`",
        f"- **Changed pixels:** {report['changed_pixel_count']}",
        f"- **Alpha pixels changed:** {report['alpha_pixels_changed']}",
        f"- **Palette pixels changed:** {report['palette_pixels_changed']}",
        f"- **Canvas:** {report['canvas']['before']} → {report['canvas']['after']}",
        f"- **Resize:** {report['resize']['before']} → {report['resize']['after']}",
        "",
        "## Operations",
        "",
    ]
    for operation in report["operations"]:
        lines.append(
            f"- `{operation['operation']}`: applied={operation['applied']}, "
            f"changed_pixels={operation['changed_pixels']}, parameters={operation['parameters']}"
        )
    lines.extend(
        [
            "",
            "## Analyzer comparison",
            "",
            f"- Before: `{report['before_analysis']['status']}`",
            f"- After: `{report['after_analysis']['status']}`",
            "",
            "A refinement result is not certified as True Pixel Art because its color count decreased. Review the after-analysis and the image in Aseprite.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def refine_image(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    profile: str,
    alpha_threshold: int = 128,
    palette: Iterable[str] | None = None,
    resize: tuple[int, int] | None = None,
    trim: bool = False,
    canvas: tuple[int, int] | None = None,
    anchor: str = "center",
    isolated_pixel_coordinates: Iterable[tuple[int, int]] = (),
    analyzer_max_colors: int = 32,
    analyzer_target_size: tuple[int, int] | None = None,
    gradient_threshold: float = 0.18,
) -> dict[str, Any]:
    source_path = Path(input_path).expanduser().resolve()
    destination_dir = Path(output_dir).expanduser().resolve()
    if not source_path.is_file():
        raise ValueError(f"Input image does not exist: {source_path}")
    if destination_dir.exists():
        raise ValueError(f"Refine output directory already exists; choose a new path: {destination_dir}")
    if not 0 <= alpha_threshold <= 255:
        raise ValueError("alpha_threshold must be between 0 and 255.")
    if resize is not None and (resize[0] < 1 or resize[1] < 1):
        raise ValueError("Resize dimensions must be positive integers.")
    if canvas is not None and (canvas[0] < 1 or canvas[1] < 1):
        raise ValueError("Canvas dimensions must be positive integers.")
    palette_colors = list(palette) if palette is not None else None

    try:
        with Image.open(source_path) as opened:
            opened.seek(0)
            image = opened.convert("RGBA")
            preserve_alpha = opened.mode in {"RGBA", "LA", "PA"} or "transparency" in opened.info
    except OSError as exc:
        raise ValueError(f"Cannot read image '{source_path}': {exc}") from exc

    original_rgba = image.copy()
    input_size = [image.width, image.height]
    resize_size_before = input_size.copy()
    resize_size_after = input_size.copy()
    operations: list[dict[str, Any]] = []

    # Binary alpha is only applied to images with alpha information.
    before = image.copy()
    alpha_changes = 0
    if preserve_alpha:
        source_pixels = _pixels(image)
        output_pixels = []
        for red, green, blue, alpha in source_pixels:
            converted_alpha = 0 if alpha < alpha_threshold else 255
            alpha_changes += int(alpha != converted_alpha)
            output_pixels.append((red, green, blue, converted_alpha))
        image.putdata(output_pixels)
    operations.append(
        _operation(
            "binary_alpha",
            before,
            image,
            applied=preserve_alpha and alpha_changes > 0,
            parameters={"threshold": alpha_threshold, "alpha_channel_preserved_if_present": preserve_alpha},
            changed_pixels=alpha_changes,
        )
    )

    palette_changes = 0
    if palette_colors is not None:
        before = image.copy()
        image, palette_changes = _nearest_palette(image, palette_colors)
        operations.append(
            _operation(
                "palette_projection",
                before,
                image,
                applied=palette_changes > 0,
                parameters={"distance": "squared_euclidean_rgb", "allowed_colors": palette_colors},
                changed_pixels=palette_changes,
            )
        )

    if resize is not None:
        before = image.copy()
        resized = image.resize(resize, Image.Resampling.NEAREST)
        applied = resized.size != image.size
        image = resized
        resize_size_after = [image.width, image.height]
        operations.append(
            _operation(
                "nearest_neighbor_resize",
                before,
                image,
                applied=applied,
                parameters={"filter": "NEAREST", "width": resize[0], "height": resize[1]},
            )
        )

    if trim:
        before = image.copy()
        image, applied, trim_bounds = _trim_transparent(image)
        operations.append(
            _operation(
                "trim_transparent_canvas",
                before,
                image,
                applied=applied,
                parameters={"bounds_before_crop": trim_bounds},
            )
        )

    if canvas is not None:
        before = image.copy()
        image, applied, offset = _pad_canvas(image, canvas[0], canvas[1], anchor)
        preserve_alpha = True
        operations.append(
            _operation(
                "pad_canvas",
                before,
                image,
                applied=applied,
                parameters={"width": canvas[0], "height": canvas[1], "anchor": anchor, "paste_offset": offset},
            )
        )

    cleanup_decisions: list[dict[str, Any]] = []
    cleanup_coordinates = list(isolated_pixel_coordinates)
    if cleanup_coordinates:
        before = image.copy()
        image, cleanup_changes, cleanup_decisions = _remove_explicit_isolated_pixels(image, cleanup_coordinates)
        operations.append(
            _operation(
                "explicit_isolated_pixel_cleanup",
                before,
                image,
                applied=cleanup_changes > 0,
                parameters={"coordinates": [list(coord) for coord in cleanup_coordinates], "decisions": cleanup_decisions},
                changed_pixels=cleanup_changes,
            )
        )

    if not preserve_alpha:
        image = image.convert("RGB")
    destination_dir.mkdir(parents=True, exist_ok=False)
    input_snapshot = destination_dir / "input.png"
    refined_path = destination_dir / "refined.png"
    diff_path = destination_dir / "diff.png"
    if preserve_alpha:
        original_rgba.save(input_snapshot, format="PNG")
        image.convert("RGBA").save(refined_path, format="PNG")
    else:
        original_rgba.convert("RGB").save(input_snapshot, format="PNG")
        image.convert("RGB").save(refined_path, format="PNG")
    output_rgba = image.convert("RGBA")
    width, height = max(original_rgba.width, output_rgba.width), max(original_rgba.height, output_rgba.height)
    before_canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    after_canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    before_canvas.alpha_composite(original_rgba, (0, 0))
    after_canvas.alpha_composite(output_rgba, (0, 0))
    diff_pixels = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    difference = diff_pixels.load()
    before_pixels, after_pixels = _pixels(before_canvas), _pixels(after_canvas)
    changed_pixel_count = 0
    alpha_pixels_changed = 0
    for index, (before_pixel, after_pixel) in enumerate(zip(before_pixels, after_pixels)):
        if before_pixel[3] != after_pixel[3]:
            alpha_pixels_changed += 1
        if before_pixel[3] != after_pixel[3] or (
            before_pixel[3] > 0 and after_pixel[3] > 0 and before_pixel[:3] != after_pixel[:3]
        ):
            changed_pixel_count += 1
            difference[index % width, index // width] = (255, 32, 32, 255)
    diff_pixels.save(diff_path, format="PNG")

    before_analysis = analyze_image(
        input_snapshot,
        max_colors=analyzer_max_colors,
        allowed_palette=palette_colors,
        target_width=analyzer_target_size[0] if analyzer_target_size else None,
        target_height=analyzer_target_size[1] if analyzer_target_size else None,
        gradient_threshold=gradient_threshold,
    )
    after_analysis = analyze_image(
        refined_path,
        max_colors=analyzer_max_colors,
        allowed_palette=palette_colors,
        target_width=analyzer_target_size[0] if analyzer_target_size else None,
        target_height=analyzer_target_size[1] if analyzer_target_size else None,
        gradient_threshold=gradient_threshold,
    )
    if after_analysis["status"] == "FAIL":
        final_status = "FAIL"
        status_reason = "Unresolved Analyzer failures remain after refinement."
    elif changed_pixel_count > 0 or after_analysis["status"] in {"PASS_WITH_FIX", "REVIEW_REQUIRED"}:
        final_status = "REVIEW_REQUIRED"
        status_reason = (
            "Pixels changed; manual visual review is required even though the post-refine Analyzer did not fail."
            if changed_pixel_count > 0
            else "The post-refine Analyzer requires review."
        )
    else:
        final_status = "PASS"
        status_reason = "No pixels changed and the post-refine Analyzer passed."

    report: dict[str, Any] = {
        "status": final_status,
        "status_reason": status_reason,
        "profile": profile,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "input": str(source_path),
        "input_snapshot": str(input_snapshot),
        "output": str(refined_path),
        "diff": str(diff_path),
        "input_sha256": _sha256(source_path),
        "output_sha256": _sha256(refined_path),
        "operations": operations,
        "changed_pixel_count": changed_pixel_count,
        "alpha_pixels_changed": alpha_pixels_changed,
        "palette_pixels_changed": palette_changes,
        "canvas": {"before": input_size, "after": [output_rgba.width, output_rgba.height]},
        "resize": {
            "before": resize_size_before,
            "after": resize_size_after,
            "filter": "NEAREST" if resize is not None else None,
        },
        "before_analysis": before_analysis,
        "after_analysis": after_analysis,
        "cleanup_decisions": cleanup_decisions,
        "files": {"input": str(input_snapshot), "refined": str(refined_path), "diff": str(diff_path)},
    }
    json_path = destination_dir / "refine_report.json"
    md_path = destination_dir / "refine_report.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _write_markdown(report, md_path)
    return report
