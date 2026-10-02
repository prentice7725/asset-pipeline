"""Verify P3 raw provenance and PixelOE recovery artifacts without modifying them."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image


RUN_ROOT = Path(__file__).resolve().parents[2]
RECOVERY = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    root_report = json.loads((RUN_ROOT / "report.json").read_text(encoding="utf-8"))
    run_manifest = json.loads((RUN_ROOT / "run.json").read_text(encoding="utf-8"))
    preserved_raw = []
    for sample in root_report["samples"]:
        manifest_path = RUN_ROOT / "generated" / sample["id"] / "generation.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        raw_path = manifest_path.parent / manifest["raw_png"]
        actual = sha256(raw_path)
        expected = sample["raw_sha256"]
        if actual != expected or actual != manifest["raw_sha256"]:
            raise RuntimeError(f"raw provenance mismatch: {sample['id']}: {actual}")
        preserved_raw.append(
            {
                "sample": sample["id"],
                "path": str(raw_path.relative_to(RUN_ROOT)),
                "sha256": actual,
                "size": manifest["raw_size"],
                "mode": manifest["raw_mode"],
            }
        )

    source = RUN_ROOT / "post" / "pixelOE_inputs" / "G01_1_south_front.png"
    baseline = (
        RUN_ROOT
        / "post"
        / "G01"
        / "south_front"
        / "P1_NN_THEN_MEDIANCUT_32"
        / "32px_opaque_white.png"
    )
    if sha256(source) != "c2d2b8f01210d8e80bc90057431318dcc2aab7fe703fc65c6d0182e2d02cbb65":
        raise RuntimeError("preserved source crop hash mismatch")
    if sha256(baseline) != "3f5fac38ac12d0d5f04fbbfcaa3cf3f809768b0ce2d0d27dec2210225747ee73":
        raise RuntimeError("existing NN+palette baseline hash mismatch")

    parsed_json = []
    for path in sorted(RECOVERY.glob("*.json")):
        json.loads(path.read_text(encoding="utf-8"))
        parsed_json.append(path.name)

    outputs = []
    for name, expected_hash in (
        ("pixeloe_t0_32x32.png", "8ef33d9879a6964269a93744e1886a1fe377c49ea3befd084bb76622f03b64b1"),
        ("pixeloe_t2_32x32.png", "94cedea5efcb7bac8e64eecf6ce0a4fd36c3924d153a9e24e9f6c1598041943f"),
    ):
        path = RECOVERY / name
        if sha256(path) != expected_hash:
            raise RuntimeError(f"PixelOE output hash mismatch: {name}")
        with Image.open(path) as image:
            if image.size != (32, 32) or image.format != "PNG":
                raise RuntimeError(f"PixelOE output format mismatch: {name}")
            outputs.append(
                {
                    "path": name,
                    "size": list(image.size),
                    "format": image.format,
                    "mode": image.mode,
                    "sha256": sha256(path),
                }
            )

    if run_manifest["generation_requests_submitted"] != 4:
        raise RuntimeError("historical generation manifest unexpectedly changed")
    result = {
        "status": "PASS_READ_ONLY_PRESERVATION_AND_ARTIFACT_INTEGRITY",
        "new_generation_requests": 0,
        "historical_generation_requests": run_manifest["generation_requests_submitted"],
        "preserved_raw_images": preserved_raw,
        "preserved_crop": {"path": str(source.relative_to(RUN_ROOT)), "sha256": sha256(source)},
        "preserved_baseline": {"path": str(baseline.relative_to(RUN_ROOT)), "sha256": sha256(baseline)},
        "parsed_recovery_json": parsed_json,
        "verified_pixelOE_outputs": outputs,
        "original_run_manifest_values_unchanged": True,
    }
    (RECOVERY / "preservation_verification.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
