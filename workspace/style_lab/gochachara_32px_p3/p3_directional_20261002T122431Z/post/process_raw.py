from __future__ import annotations
import hashlib, json
from collections import Counter
from pathlib import Path
from typing import Any
import numpy as np
from PIL import Image, ImageOps
from assetpipe._ported.pixel_gate.analyzer import analyze_image, _connected_components

RUN = Path(__file__).resolve().parents[1]
POST = RUN / "post"
RAW = RUN / "generated"
PALETTE_CAPS = (16, 32)
VIEW_NAMES = ("south_front", "west_profile", "north_back")
RAW_NAMES = {
    "G01": "83aacbc7_000.png",
    "G02": "3c3a69b0_000.png",
    "G03": "95363562_000.png",
    "G04": "54ca7920_000.png",
}
PROMPT_IDS = {
    "G01": "83aacbc7-3b11-4386-9a13-8d2dd4656681",
    "G02": "3c3a69b0-5ab6-4aa1-8317-d48930662cb7",
    "G03": "95363562-5653-4e5d-ac07-90b0db56a35d",
    "G04": "54ca7920-e2fe-4822-99c9-e62d3970bdf2",
}

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def near_white_background_alpha(rgb: Image.Image) -> Image.Image:
    arr = np.asarray(rgb.convert("RGB"))
    candidate = np.all(arr >= 235, axis=2)
    h, w = candidate.shape
    outside = np.zeros((h, w), dtype=bool)
    stack: list[tuple[int, int]] = []
    for x in range(w):
        if candidate[0, x]: outside[0, x] = True; stack.append((x, 0))
        if candidate[h - 1, x] and not outside[h - 1, x]: outside[h - 1, x] = True; stack.append((x, h - 1))
    for y in range(h):
        if candidate[y, 0] and not outside[y, 0]: outside[y, 0] = True; stack.append((0, y))
        if candidate[y, w - 1] and not outside[y, w - 1]: outside[y, w - 1] = True; stack.append((w - 1, y))
    while stack:
        x, y = stack.pop()
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= nx < w and 0 <= ny < h and candidate[ny, nx] and not outside[ny, nx]:
                outside[ny, nx] = True
                stack.append((nx, ny))
    alpha = np.where(outside, 0, 255).astype(np.uint8)
    return Image.fromarray(alpha, mode="L")

def component_regions(raw: Image.Image) -> list[dict[str, Any]]:
    a = np.asarray(raw.convert("RGB"))
    foreground = a.min(axis=2) < 235
    comps = _connected_components(bytearray(foreground.ravel().astype(np.uint8)), raw.width, raw.height)
    comps = [c for c in comps if c["area"] >= 500]
    comps.sort(key=lambda c: (c["min_y"], c["min_x"]))
    if len(comps) != 3:
        raise RuntimeError(f"Expected exactly 3 main sprite regions; found {len(comps)}.")
    regions = []
    for i, c in enumerate(comps):
        pad = 4
        box = (
            max(0, c["min_x"] - pad), max(0, c["min_y"] - pad),
            min(raw.width, c["max_x"] + 1 + pad), min(raw.height, c["max_y"] + 1 + pad)
        )
        regions.append({"view_index": i + 1, "requested_view": VIEW_NAMES[i], "bbox": list(box), "area_threshold235": c["area"]})
    return regions

def fit_cell(rgb_crop: Image.Image, mask_crop: Image.Image) -> tuple[Image.Image, Image.Image]:
    rgb = rgb_crop.convert("RGB")
    alpha = mask_crop.convert("L")
    fitted = ImageOps.contain(rgb, (224, 224), method=Image.Resampling.NEAREST)
    fitted_alpha = alpha.resize(fitted.size, Image.Resampling.NEAREST)
    canvas = Image.new("RGB", (256, 256), (255, 255, 255))
    mask_canvas = Image.new("L", (256, 256), 0)
    offset = ((256 - fitted.width) // 2, (256 - fitted.height) // 2)
    canvas.paste(fitted, offset)
    mask_canvas.paste(fitted_alpha, offset)
    return canvas, mask_canvas

def metrics(path: Path, mask32: Image.Image, method: str, palette_cap: int | None, mode: str) -> dict[str, Any]:
    gate = analyze_image(path, max_colors=32, target_width=32, target_height=32)
    a = np.asarray(mask32.convert("L")) > 0
    components = _connected_components(bytearray(a.ravel().astype(np.uint8)), 32, 32)
    tiny = [c for c in components[1:] if c["area"] <= 2]
    rgb = Image.open(path).convert("RGB")
    visible = np.asarray(rgb).reshape(-1, 3)
    colors = np.unique(visible, axis=0)
    foreground_pixels = int(a.sum())
    exposed4 = 0
    isolated4 = 0
    for y in range(32):
        for x in range(32):
            if not a[y, x]:
                continue
            n = sum(0 <= nx < 32 and 0 <= ny < 32 and bool(a[ny, nx])
                    for nx, ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)))
            exposed4 += 4 - n
            isolated4 += n == 0
    return {
        "method": method, "palette_cap": palette_cap, "background_mode": mode,
        "path": str(path), "sha256": sha(path), "size": [32, 32],
        "alpha_mode": Image.open(path).mode,
        "unique_rgb_colors": int(len(colors)),
        "foreground_pixels_from_sidecar_mask": foreground_pixels,
        "cluster_8_connected_count": len(components),
        "cluster_largest_ratio": round((components[0]["area"] / foreground_pixels), 6) if components and foreground_pixels else None,
        "detached_cluster_area_le2_count": len(tiny),
        "detached_cluster_pixels_le2": sum(c["area"] for c in tiny),
        "four_neighbor_exposed_edges": exposed4,
        "four_neighbor_isolated_foreground_pixels": isolated4,
        "pixel_gate": gate,
        "art_review": "PENDING",
        "semantic_review": "PENDING"
    }

def main() -> None:
    if (POST / "offline_prepared.json").exists():
        raise SystemExit("Refusing to overwrite existing prepared outputs.")
    manifest = []
    input_root = POST / "pixelOE_inputs"
    input_root.mkdir(parents=True, exist_ok=False)
    for gid, filename in RAW_NAMES.items():
        raw_path = RAW / gid / filename
        raw = Image.open(raw_path).convert("RGB")
        regions = component_regions(raw)
        for region in regions:
            view = region["requested_view"]
            x0, y0, x1, y1 = region["bbox"]
            crop = raw.crop((x0, y0, x1, y1))
            alpha = near_white_background_alpha(crop)
            cell, cell_alpha = fit_cell(crop, alpha)
            stem = f"{gid}_{region['view_index']}_{view}"
            rgb_input = input_root / f"{stem}.png"
            alpha_input = input_root / f"{stem}_alpha.png"
            cell.save(rgb_input)
            cell_alpha.save(alpha_input)
            region_record = {
                "generation_id": gid,
                "requested_view_slot": view,
                "source_raw": str(raw_path.relative_to(RUN)).replace("\\", "/"),
                "source_sha256": sha(raw_path),
                "source_bbox_xyxy": region["bbox"],
                "source_component_area_threshold235": region["area_threshold235"],
                "cell_256_rgb": str(rgb_input.relative_to(RUN)).replace("\\", "/"),
                "cell_256_rgb_sha256": sha(rgb_input),
                "cell_256_alpha_mask": str(alpha_input.relative_to(RUN)).replace("\\", "/"),
                "cell_256_alpha_mask_sha256": sha(alpha_input),
                "background_mask_method": "edge-connected 4-neighbor flood fill of pixels with all RGB channels >=235; heuristic sidecar only",
                "ratio_policy": "aspect ratio preserved; contain to 224x224; centered in 256x256; no crop",
                "requested_direction_observed": "not yet assessed"
            }
            # 1) nearest-neighbor downscale then median cut
            nearest_rgb = cell.resize((32, 32), Image.Resampling.NEAREST)
            nearest_alpha = cell_alpha.resize((32, 32), Image.Resampling.NEAREST)
            for cap in PALETTE_CAPS:
                # Path A: NN first, then MedianCut.
                a_rgb = nearest_rgb.quantize(colors=cap, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).convert("RGB")
                # Path B: MedianCut on 256px cell first, then NN.
                b_high = cell.quantize(colors=cap, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).convert("RGB")
                b_rgb = b_high.resize((32, 32), Image.Resampling.NEAREST)
                for method, result_rgb in (
                    (f"P1_NN_THEN_MEDIANCUT_{cap}", a_rgb),
                    (f"P1_MEDIANCUT_{cap}_THEN_NN", b_rgb),
                ):
                    dest = POST / gid / view / method
                    dest.mkdir(parents=True, exist_ok=False)
                    for mode in ("opaque_white", "binary_alpha"):
                        out = dest / f"32px_{mode}.png"
                        if mode == "opaque_white":
                            result_rgb.save(out)
                        else:
                            rgba = result_rgb.convert("RGBA")
                            rgba.putalpha(nearest_alpha)
                            rgba.save(out)
                        q = metrics(out, nearest_alpha, method, cap, mode)
                        q.update(region_record)
                        q["realized_color_cap_compliant"] = q["unique_rgb_colors"] <= cap
                        (dest / f"qa_{mode}.json").write_text(json.dumps(q, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                        manifest.append(q)
            manifest.append({
                **region_record,
                "method": "P2_OE_CONTRAST_0",
                "status": "NOT_AVAILABLE",
                "reason": "Live PixelOEPixelize+ schema sets thickness minimum to 1; thickness 0 is outside its accepted input range.",
                "art_review": "PENDING"
            })
    out = POST / "offline_prepared.json"
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "outputs": len([x for x in manifest if x.get("pixel_gate")]),
        "p2_unavailable": len([x for x in manifest if x.get("method") == "P2_OE_CONTRAST_0"]),
        "pixelOE_input_images": len(list(input_root.glob("*_*.png"))),
        "report": str(out)
    }, indent=2))

if __name__ == "__main__":
    main()

