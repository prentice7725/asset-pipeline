"""Reproduce PixelOE via the installed official Torch API on one preserved P3 crop."""

from __future__ import annotations

import hashlib
import json
import platform
import time
from importlib import metadata
from pathlib import Path

import torch
from PIL import Image
from pixeloe.torch.pixelize import pixelize
from pixeloe.torch.utils import pre_resize, to_numpy


RUN_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = Path(__file__).resolve().parent
RAW_PATH = RUN_ROOT / "generated" / "G01" / "83aacbc7_000.png"
INPUT_PATH = RUN_ROOT / "post" / "pixelOE_inputs" / "G01_1_south_front.png"
EXPECTED_RAW_SHA256 = "3ad21be81240b861db9c839268d349b3c6f7f3eb1ea39752858a0981f072f7b8"
EXPECTED_INPUT_SHA256 = "c2d2b8f01210d8e80bc90057431318dcc2aab7fe703fc65c6d0182e2d02cbb65"
TARGET_SIZE = 32
PATCH_SIZE = 16


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    raw_sha = sha256(RAW_PATH)
    input_sha = sha256(INPUT_PATH)
    if raw_sha != EXPECTED_RAW_SHA256:
        raise RuntimeError(f"raw source hash mismatch: {raw_sha}")
    if input_sha != EXPECTED_INPUT_SHA256:
        raise RuntimeError(f"input crop hash mismatch: {input_sha}")
    if not torch.cuda.is_available():
        raise RuntimeError("The actual ComfyUI venv reports CUDA unavailable")

    package_version = metadata.version("pixeloe")
    api_source = Path(pixelize.__code__.co_filename).resolve()
    with Image.open(INPUT_PATH) as opened:
        source = opened.convert("RGB")
    if source.size != (256, 256):
        raise RuntimeError(f"unexpected crop dimensions: {source.size}")

    # Match PixelOEPixelize+'s target_size=32 / patch_size=16 contract.
    # The official helper preserves aspect ratio and uses bicubic pre-resize.
    tensor = pre_resize(source, target_size=TARGET_SIZE, patch_size=PATCH_SIZE)
    tensor = tensor.to(device="cuda", dtype=torch.float32)
    torch.cuda.synchronize()

    outputs = []
    for thickness in (0, 2):
        started = time.perf_counter()
        result = pixelize(
            tensor,
            pixel_size=PATCH_SIZE,
            thickness=thickness,
            mode="contrast",
            do_color_match=True,
            do_quant=False,
            no_post_upscale=True,
            backend="torch",
        )
        torch.cuda.synchronize()
        elapsed = time.perf_counter() - started
        image = Image.fromarray(to_numpy(result)[0]).convert("RGB")
        if image.size != (TARGET_SIZE, TARGET_SIZE):
            raise RuntimeError(f"thickness={thickness} returned {image.size}")
        output_path = OUTPUT_DIR / f"pixeloe_t{thickness}_32x32.png"
        image.save(output_path, format="PNG", optimize=False)
        rgb = list(
            image.get_flattened_data()
            if hasattr(image, "get_flattened_data")
            else image.getdata()
        )
        not_exact_white = [
            (x, y)
            for y in range(image.height)
            for x in range(image.width)
            if image.getpixel((x, y)) != (255, 255, 255)
        ]
        border = (
            [image.getpixel((x, 0)) for x in range(image.width)]
            + [image.getpixel((x, image.height - 1)) for x in range(image.width)]
            + [image.getpixel((0, y)) for y in range(1, image.height - 1)]
            + [image.getpixel((image.width - 1, y)) for y in range(1, image.height - 1)]
        )
        outputs.append(
            {
                "thickness": thickness,
                "status": "EXECUTED",
                "path": output_path.name,
                "sha256": sha256(output_path),
                "format": image.format or "PNG",
                "size": list(image.size),
                "mode": image.mode,
                "alpha": "absent; source crop is RGB on opaque white",
                "unique_rgb_colors": len(set(rgb)),
                "pixels_not_exact_rgb_white": len(not_exact_white),
                "unique_rgb_colors_on_outer_border": len(set(border)),
                "pure_white_count_is_not_a_silhouette_measure": True,
                "elapsed_seconds": round(elapsed, 6),
            }
        )

    result = {
        "experiment": "P3 PixelOE API recovery; one existing human-archer south/front crop",
        "status": "TRANSFORM_EXECUTION_PASS; quality_validation_failed; human_review_pending",
        "new_image_generation_requests": 0,
        "source": {
            "generated_raw": "generated/G01/83aacbc7_000.png",
            "generated_raw_sha256": raw_sha,
            "derived_input": "post/pixelOE_inputs/G01_1_south_front.png",
            "derived_input_sha256": input_sha,
            "derived_input_size": [256, 256],
            "lineage_bbox_xyxy_in_raw": [106, 3, 176, 133],
            "crop_policy": "aspect ratio preserved; contain to 224x224; centered in 256x256; no crop",
            "input_color_mode": "RGB; no alpha channel; opaque white background",
        },
        "runtime": {
            "python": platform.python_version(),
            "python_executable": str(Path(__import__("sys").executable).resolve()),
            "torch": torch.__version__,
            "torch_cuda": torch.version.cuda,
            "cuda_device": torch.cuda.get_device_name(0),
            "pixeloe_version": package_version,
            "pixeloe_api": "pixeloe.torch.pixelize.pixelize",
            "pixeloe_api_source": str(api_source),
            "pixeloe_api_source_sha256": sha256(api_source),
            "backend": "torch on CUDA; Slang backend explicitly bypassed",
        },
        "parameters": {
            "target_size": TARGET_SIZE,
            "patch_size": PATCH_SIZE,
            "pre_resize": "official pre_resize; bicubic; target_size=32; patch_size=16",
            "downscale_mode": "contrast",
            "color_matching": True,
            "quantization": False,
            "upscale": False,
            "pixel_size": PATCH_SIZE,
            "thickness_values": [0, 2],
            "output_size": [32, 32],
            "output_background": "opaque white inherited from RGB input; no alpha synthesis",
            "stochastic_seed": "not_applicable; deterministic image-processing path",
        },
        "outputs": outputs,
        "approval": {
            "pixel_gate_is_technical_only": True,
            "semantic_art_review": "PENDING",
            "static_master_approved": False,
            "golden_recipe_approved": False,
        },
    }
    report_path = OUTPUT_DIR / "pixeloe_execution.json"
    report_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
