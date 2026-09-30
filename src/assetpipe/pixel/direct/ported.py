from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ALPHA_BACKGROUND_TOLERANCE = 60
OUTPUT_FRAME_DURATION_MS = 125
GIF_FRAME_DURATION_MS = 120

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def alpha_bbox(rgba: np.ndarray) -> tuple[int, int, int, int]:
    ys, xs = np.where(rgba[:, :, 3] > 0)
    if not len(xs):
        raise ValueError("Matte removed the complete character.")
    return int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1)


def edge_connected(mask: np.ndarray) -> np.ndarray:
    """Return 4-connected true pixels reachable from any image border."""
    height, width = mask.shape
    seen = np.zeros((height, width), dtype=bool)
    seeds = [(int(x), 0) for x in np.flatnonzero(mask[0])]
    seeds.extend((int(x), height - 1) for x in np.flatnonzero(mask[-1]))
    seeds.extend((0, int(y)) for y in np.flatnonzero(mask[:, 0]))
    seeds.extend((width - 1, int(y)) for y in np.flatnonzero(mask[:, -1]))
    stack = seeds
    while stack:
        x, y = stack.pop()
        if seen[y, x] or not mask[y, x]:
            continue
        left = x
        while left > 0 and mask[y, left - 1] and not seen[y, left - 1]:
            left -= 1
        right = x
        while right + 1 < width and mask[y, right + 1] and not seen[y, right + 1]:
            right += 1
        seen[y, left : right + 1] = True
        for ny in (y - 1, y + 1):
            if not 0 <= ny < height:
                continue
            nx = left
            while nx <= right:
                if mask[ny, nx] and not seen[ny, nx]:
                    stack.append((nx, ny))
                    nx += 1
                    while nx <= right and mask[ny, nx] and not seen[ny, nx]:
                        nx += 1
                else:
                    nx += 1
    return seen


def white_border_matte(image: Image.Image) -> tuple[Image.Image, dict[str, object]]:
    rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
    distance = np.sqrt(np.sum((rgb.astype(np.int32) - 255) ** 2, axis=2))
    near_white = distance <= ALPHA_BACKGROUND_TOLERANCE
    # The known white background is edge-connected. Flood only that region;
    # enclosed white/silver character details remain foreground.
    background = edge_connected(near_white)
    rgba = np.dstack((rgb, np.where(background, 0, 255).astype(np.uint8)))
    rgba[background, :3] = 0
    bbox = alpha_bbox(rgba)
    result = Image.fromarray(rgba, mode="RGBA")
    report = {
        "method": f"explicit four-connected edge span-fill of RGB pixels within Euclidean distance {ALPHA_BACKGROUND_TOLERANCE} of solid white",
        "background_rgb": [255, 255, 255],
        "background_tolerance_rgb_distance": ALPHA_BACKGROUND_TOLERANCE,
        "foreground_pixels": int(np.count_nonzero(~background)),
        "transparent_pixels": int(np.count_nonzero(background)),
        "alpha_values": [0, 255],
        "bbox_xyxy": list(bbox),
    }
    return result, report


def blue_body_anchor(rgba: np.ndarray, bbox: tuple[int, int, int, int]) -> tuple[float, float, int]:
    x0, y0, x1, y1 = bbox
    width, height = x1 - x0, y1 - y0
    hsv = np.asarray(Image.fromarray(rgba[:, :, :3], mode="RGB").convert("HSV"))
    yy, xx = np.indices(hsv.shape[:2])
    # Derive the torso-equivalent center from blue tunic pixels in the central
    # body zone of this character's own matte. The same ratio is used for the
    # approved Static Master and each motion frame; no Courier coordinates.
    zone = (
        (xx >= x0 + width * 0.32)
        & (xx <= x0 + width * 0.70)
        & (yy >= y0 + height * 0.28)
        & (yy <= y0 + height * 0.70)
        & (hsv[:, :, 0] >= 125)
        & (hsv[:, :, 0] <= 190)
        & (hsv[:, :, 1] > 45)
        & (rgba[:, :, 3] > 0)
    )
    ys, xs = np.where(zone)
    if len(xs) < 20:
        raise ValueError("Could not derive the blue-tunic body center from this character frame.")
    return float(xs.mean()), float(ys.mean()), int(len(xs))


def nearest_palette(rgb: np.ndarray, palette_array: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    pixels = rgb.reshape(-1, 3).astype(np.int32)
    palette = palette_array.astype(np.int32)
    indices = np.empty(len(pixels), dtype=np.uint8)
    for offset in range(0, len(pixels), 4096):
        batch = pixels[offset : offset + 4096]
        distances = ((batch[:, None, :] - palette[None, :, :]) ** 2).sum(axis=2)
        indices[offset : offset + len(batch)] = np.argmin(distances, axis=1).astype(np.uint8)
    mapped = palette_array[indices].reshape(rgb.shape)
    deltas = np.sqrt(np.sum((rgb.astype(np.int16) - mapped.astype(np.int16)) ** 2, axis=-1))
    return mapped, deltas


def write_sheet(frames: list[Image.Image], labels: list[str], path: Path, *, scale: int = 1) -> None:
    CANVAS = frames[0].size
    tile_w, tile_h = CANVAS[0] * scale, CANVAS[1] * scale
    label_h = 24
    cols, rows = 4, math.ceil(len(frames) / 4)
    sheet = Image.new("RGBA", (cols * tile_w, rows * (tile_h + label_h)), (96, 96, 96, 255))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 12 if scale == 1 else 18)
    except OSError:
        font = ImageFont.load_default()
    for index, (frame, label) in enumerate(zip(frames, labels)):
        display = frame.resize((tile_w, tile_h), Image.Resampling.NEAREST) if scale != 1 else frame.copy()
        px, py = (index % cols) * tile_w, (index // cols) * (tile_h + label_h)
        sheet.alpha_composite(display, (px, py))
        draw.text((px + 4, py + tile_h + 3), label, font=font, fill=(255, 255, 255, 255))
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)


def write_global_palette_gif(frames: list[Image.Image], path: Path, colors: list[tuple[int, int, int]]) -> dict[str, object]:
    CANVAS = frames[0].size
    color_index = {color: index for index, color in enumerate(colors)}
    palette_bytes = [channel for color in colors for channel in color]
    palette_bytes.extend([0] * (768 - len(palette_bytes)))
    palette_bytes[255 * 3 : 255 * 3 + 3] = [0, 0, 0]  # transparent slot is never an opaque color
    indexed: list[Image.Image] = []
    transparent_counts: list[int] = []
    for frame in frames:
        rgba = np.asarray(frame.convert("RGBA"))
        pixels = np.full((CANVAS[1], CANVAS[0]), 255, dtype=np.uint8)
        alpha = rgba[:, :, 3] > 0
        rgb = rgba[:, :, :3]
        for color, index in color_index.items():
            pixels[alpha & np.all(rgb == np.asarray(color, dtype=np.uint8), axis=2)] = index
        pal = Image.fromarray(pixels, mode="P")
        pal.putpalette(palette_bytes)
        indexed.append(pal)
        transparent_counts.append(int(np.count_nonzero(~alpha)))
    path.parent.mkdir(parents=True, exist_ok=True)
    indexed[0].save(
        path,
        save_all=True,
        append_images=indexed[1:],
        duration=GIF_FRAME_DURATION_MS,
        loop=0,
        optimize=False,
        disposal=2,
        transparency=255,
    )
    with Image.open(path) as check:
        decoded = 0
        for _frame in range(getattr(check, "n_frames", 1)):
            check.seek(_frame)
            decoded += 1
            if check.info.get("transparency") not in (255, None):
                raise ValueError("GIF did not preserve the reserved transparency index.")
    return {
        "frames": decoded,
        "duration_ms_each": GIF_FRAME_DURATION_MS,
        "duration_resolution_ms": 10,
        "source_aseprite_duration_ms": OUTPUT_FRAME_DURATION_MS,
        "cycle_duration_ms": decoded * GIF_FRAME_DURATION_MS,
        "transparency_index": 255,
        "transparent_pixels_per_frame": transparent_counts,
    }


def run_direct(*, asset_id, static_master, source_video, source_frames, selection_path, output_dir, canvas=(160, 160), profile):
    if profile != "blue_tunic_white_matte_v1":
        raise ValueError("Only the verified blue_tunic_white_matte_v1 profile is available; supply an explicit compatible profile")
    ROOT = Path(output_dir).resolve()
    ROOT.mkdir(parents=True, exist_ok=False)
    STATIC_MASTER, SOURCE_VIDEO = Path(static_master), Path(source_video)
    SOURCE_FRAMES, SELECTION_PATH = Path(source_frames), Path(selection_path)
    MATTE_DIR, PIXEL_DIR, PREVIEW_DIR = ROOT / "030_matte_crops", ROOT / "040_direct_pixel_frames", ROOT / "060_preview"
    PALETTE_PATH, ALIGNMENT_PATH = ROOT / "static_master_exact_palette.json", ROOT / "alignment_report.json"
    CANVAS = tuple(canvas)
    selection = json.loads(SELECTION_PATH.read_text(encoding="utf-8"))
    rows = selection["selection"]
    if len(rows) != 8:
        raise ValueError(f"Expected eight selected frames; got {len(rows)}")
    source_paths = [SOURCE_FRAMES / f"frame_{int(row['source_frame']):04d}.png" for row in rows]
    for path in [SOURCE_VIDEO, STATIC_MASTER, SELECTION_PATH, *source_paths]:
        if not path.is_file():
            raise FileNotFoundError(path)

    with Image.open(STATIC_MASTER) as opened:
        master = np.asarray(opened.convert("RGBA"))
    master_bbox = alpha_bbox(master)
    master_visible = master[:, :, 3] > 0
    exact_colors = sorted({tuple(int(v) for v in pixel) for pixel in master[:, :, :3][master_visible]})
    if not 1 <= len(exact_colors) <= 255:
        raise ValueError("Direct profile requires 1-255 master colors")
    PALETTE_PATH.write_text(
        json.dumps({"schema_version": 1, "character_id": asset_id, "status": "EXACT_APPROVED_STATIC_MASTER_PALETTE", "source_master": str(STATIC_MASTER), "source_sha256": sha256(STATIC_MASTER), "alpha_excluded": True, "colors": ["#%02X%02X%02X" % color for color in exact_colors]}, indent=2) + "\n",
        encoding="utf-8",
    )

    mats: list[Image.Image] = []
    crops: list[Image.Image] = []
    mat_reports: list[dict[str, object]] = []
    master_anchor = blue_body_anchor(master, master_bbox)
    for row, path in zip(rows, source_paths):
        with Image.open(path) as opened:
            matte, matte_report = white_border_matte(opened)
        rgba = np.asarray(matte)
        bbox = alpha_bbox(rgba)
        bx0, by0, bx1, by1 = bbox
        anchor_x, anchor_y, anchor_count = blue_body_anchor(rgba, bbox)
        crop = matte.crop(bbox)
        mats.append(matte)
        crops.append(crop)
        mat_reports.append({
            "phase": row["phase"],
            "source_frame": row["source_frame"],
            "timestamp_seconds": row["timestamp_seconds"],
            "source_sha256": sha256(path),
            **matte_report,
            "crop_xyxy": list(bbox),
            "crop_size": [bx1 - bx0, by1 - by0],
            "derived_tunic_center_xy": [anchor_x, anchor_y],
            "tunic_color_sample_count": anchor_count,
            "bottom_contact_edge_y": by1,
            "crop_path": str(MATTE_DIR / f"{row['phase'].lower()}.png"),
        })

    target_height = round((master_bbox[3] - master_bbox[1]) * CANVAS[1] / master.shape[0])
    source_heights = [int(record["crop_size"][1]) for record in mat_reports]
    shared_scale = target_height / float(np.median(source_heights))
    master_blue_x, master_blue_y, master_blue_count = master_anchor
    target_anchor_x = master_blue_x * CANVAS[0] / master.shape[1]
    target_baseline_edge = (master_bbox[3]) * CANVAS[1] / master.shape[0]
    palette_array = np.asarray(exact_colors, dtype=np.uint8)
    output_frames: list[Image.Image] = []
    alignment_rows: list[dict[str, object]] = []
    MATTE_DIR.mkdir(parents=True, exist_ok=True)
    PIXEL_DIR.mkdir(parents=True, exist_ok=True)

    for row, matte, crop, record in zip(rows, mats, crops, mat_reports):
        phase = str(row["phase"])
        crop_rgba = np.asarray(crop.convert("RGBA"))
        x0, y0, x1, y1 = (int(v) for v in record["crop_xyxy"])
        scale_w = max(1, round(crop.width * shared_scale))
        scale_h = max(1, round(crop.height * shared_scale))
        premultiplied = crop.convert("RGBa")
        resized = premultiplied.resize((scale_w, scale_h), Image.Resampling.LANCZOS).convert("RGBA")
        resized_arr = np.asarray(resized).copy()
        resized_arr[:, :, 3] = np.where(resized_arr[:, :, 3] >= 128, 255, 0).astype(np.uint8)
        resized_arr[resized_arr[:, :, 3] == 0, :3] = 0

        source_anchor_x = float(record["derived_tunic_center_xy"][0])
        source_baseline_edge = float(record["bottom_contact_edge_y"])
        left = round(target_anchor_x - (source_anchor_x - x0) * shared_scale)
        top = round(target_baseline_edge - (source_baseline_edge - y0) * shared_scale)
        if left < 0 or top < 0 or left + scale_w > CANVAS[0] or top + scale_h > CANVAS[1]:
            raise ValueError(f"{phase} would clip on the {CANVAS[0]}x{CANVAS[1]} canvas: offset={(left, top)}, scaled={(scale_w, scale_h)}")

        canvas = np.zeros((CANVAS[1], CANVAS[0], 4), dtype=np.uint8)
        canvas[top : top + scale_h, left : left + scale_w] = resized_arr
        visible = canvas[:, :, 3] > 0
        projected, distances = nearest_palette(canvas[:, :, :3][visible], palette_array)
        canvas[:, :, :3][visible] = projected
        canvas[:, :, 3] = np.where(visible, 255, 0).astype(np.uint8)
        canvas[~visible, :3] = 0
        result = Image.fromarray(canvas, mode="RGBA")
        output_path = PIXEL_DIR / f"{phase.lower()}.png"
        result.save(output_path)
        output_frames.append(result)
        matte_path = MATTE_DIR / f"{phase.lower()}.png"
        matte.save(matte_path)
        crop_path = MATTE_DIR / f"{phase.lower()}_crop.png"
        crop.save(crop_path)
        nonzero = np.asarray(result)[:, :, 3] > 0
        ys, xs = np.where(nonzero)
        alignment_rows.append({
            "phase": phase,
            "source_frame": row["source_frame"],
            "timestamp_seconds": row["timestamp_seconds"],
            "source_crop_xyxy": [x0, y0, x1, y1],
            "source_tunic_center_xy": [source_anchor_x, float(record["derived_tunic_center_xy"][1])],
            "master_tunic_center_xy": [master_blue_x, master_blue_y],
            "target_tunic_center_x": round(target_anchor_x, 4),
            "source_bottom_contact_edge_y": source_baseline_edge,
            "target_bottom_contact_edge_y": round(target_baseline_edge, 4),
            "shared_uniform_scale": round(shared_scale, 8),
            "resized_crop_wh": [scale_w, scale_h],
            "placement_xy": [left, top],
            "output_bbox_xywh": [int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)],
            "palette_projection_max_rgb_distance": round(float(distances.max()) if len(distances) else 0.0, 4),
            "palette_projection_mean_rgb_distance": round(float(distances.mean()) if len(distances) else 0.0, 4),
            "opaque_pixels": int(visible.sum()),
            "used_colors": len({tuple(int(v) for v in p) for p in canvas[:, :, :3][visible]}),
            "manual_style_repaint": False,
            "final_path": str(output_path),
        })

    MATTE_DIR.mkdir(parents=True, exist_ok=True)
    labels = [f"{row['phase']}  src {row['source_frame']}" for row in rows]
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    write_sheet(output_frames, labels, PREVIEW_DIR / "contact_sheet.png", scale=1)
    write_sheet(output_frames, labels, PREVIEW_DIR / "contact_sheet_4x.png", scale=4)
    apng_path = PREVIEW_DIR / "direct_walk_preview.apng"
    output_frames[0].save(
        apng_path,
        format="PNG",
        save_all=True,
        append_images=output_frames[1:],
        duration=OUTPUT_FRAME_DURATION_MS,
        loop=0,
        disposal=0,
        blend=0,
    )
    gif_report = write_global_palette_gif(output_frames, PREVIEW_DIR / "direct_walk_preview.gif", exact_colors)

    alignment = {
        "schema_version": 1,
        "status": "DIRECT_PIXELIZATION_COMPLETE_PIXEL_GATE_PENDING",
        "character_id": asset_id,
        "canvas": list(CANVAS),
        "source_video": str(SOURCE_VIDEO),
        "source_video_sha256": sha256(SOURCE_VIDEO),
        "approved_static_master": str(STATIC_MASTER),
        "approved_static_master_sha256": sha256(STATIC_MASTER),
        "static_master_geometry": {
            "canvas": [int(master.shape[1]), int(master.shape[0])],
            "alpha_bbox_xywh": [master_bbox[0], master_bbox[1], master_bbox[2] - master_bbox[0], master_bbox[3] - master_bbox[1]],
            "bottom_contact_edge_y": master_bbox[3],
            "derived_blue_tunic_center_xy": [round(master_blue_x, 4), round(master_blue_y, 4)],
            "blue_sample_count": master_blue_count,
        },
        "shared_scale_derivation": {
            "target_character_height_px": target_height,
            "median_selected_source_crop_height_px": float(np.median(source_heights)),
            "shared_uniform_scale": round(shared_scale, 8),
            "resampler": "premultiplied-alpha Lanczos for one downsample, then binary alpha and exact palette projection; no per-frame scale adjustment",
        },
        "matte": {"method": "edge-connected white flood fill", "tolerance_rgb_euclidean": ALPHA_BACKGROUND_TOLERANCE},
        "palette": {"status": "EXACT_APPROVED_STATIC_MASTER_PALETTE", "color_count": len(exact_colors), "source": str(PALETTE_PATH), "projection": "nearest RGB, no dithering"},
        "frames": alignment_rows,
        "preview": {
            "contact_sheet": str(PREVIEW_DIR / "contact_sheet.png"),
            "contact_sheet_4x_nearest": str(PREVIEW_DIR / "contact_sheet_4x.png"),
            "apng": str(apng_path),
            "apng_duration_ms_each": OUTPUT_FRAME_DURATION_MS,
            "gif": str(PREVIEW_DIR / "direct_walk_preview.gif"),
            "gif_report": gif_report,
        },
        "cleanup": {"identity_or_pose_redraw": False, "operations": ["white-background matte", "shared-scale/anchor placement", "binary alpha", "exact Static Master palette projection"], "note": "No unsafe silhouette, equipment, or pose changes were applied. The direct motion remains source-video-derived."},
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    ALIGNMENT_PATH.write_text(json.dumps(alignment, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": alignment["status"], "frames": len(output_frames), "palette_colors": len(exact_colors), "scale": round(shared_scale, 8), "mean_rgb_projection_error": round(float(np.mean([frame["palette_projection_mean_rgb_distance"] for frame in alignment_rows])), 4), "gif": gif_report, "alignment_report": str(ALIGNMENT_PATH)}, indent=2, ensure_ascii=False))

    return alignment
