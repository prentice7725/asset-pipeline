from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from assetpipe._ported.aseprite_bridge.runner import build_animation_master, build_game_master_revision, build_master, export_static_png, find_aseprite, save_animation_revision

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "tests" / "assets"


def test_executable_discovery_uses_config_then_environment_then_path(tmp_path):
    configured = tmp_path / "configured.exe"
    env_path = tmp_path / "env.exe"
    path_dir = tmp_path / "bin"
    path_dir.mkdir()
    path_exe = path_dir / "Aseprite.exe"
    for path in (configured, env_path, path_exe):
        path.write_bytes(b"fixture")

    assert find_aseprite(str(configured), environ={"ASEPRITE_PATH": str(env_path)}, path_value=str(path_dir)).path == configured.resolve()
    assert find_aseprite(None, environ={"ASEPRITE_PATH": str(env_path)}, path_value=str(path_dir)).path == env_path.resolve()
    assert find_aseprite(None, environ={}, path_value=str(path_dir)).path == path_exe.resolve()


def test_real_aseprite_single_frame_round_trip(tmp_path):
    executable = find_aseprite()
    if executable is None:
        pytest.skip("Aseprite is not installed; real integration is unavailable.")
    report = build_master(
        executable,
        source=ASSETS / "true_pixel_art.png",
        frames=[],
        output_dir=tmp_path / "single",
        project_root=ROOT,
        character_id="test_character",
        tag_name="static",
        pivot="32,60",
    )

    assert report["status"] == "PASS"
    assert report["frames"] == 1
    assert report["pixel_integrity"]["exact_rgba_match"] is True
    assert report["pixel_integrity"]["changed_pixels"] == 0
    assert report["verified_layers"] == ["Pixel"]
    assert report["verified_tags"] == ["static"]
    assert report["verified_slices"] == ["character_pivot"]
    assert report["frame_durations_ms"] == [100]
    export_report = export_static_png(
        executable,
        report["master"],
        tmp_path / "export.png",
        expected_source=ASSETS / "true_pixel_art.png",
    )
    assert export_report["exact_rgba_match"] is True
    assert export_report["changed_pixels"] == 0
    assert export_report["dimensions"] == [64, 64]


def test_real_aseprite_adds_frames_and_exports_json_metadata(tmp_path):
    executable = find_aseprite()
    if executable is None:
        pytest.skip("Aseprite is not installed; real integration is unavailable.")
    report = build_master(
        executable,
        source=ASSETS / "true_pixel_art.png",
        frames=[ASSETS / "downscaled_illustration.png"],
        output_dir=tmp_path / "animated",
        project_root=ROOT,
        character_id="test_character",
        tag_name="walk",
        frame_duration_ms=120,
    )

    assert report["status"] == "PASS"
    assert report["frames"] == 2
    assert report["sprite_sheet_dimensions"] == {"width": 128, "height": 64}
    assert report["verified_layers"] == ["Pixel"]
    assert report["verified_tags"] == ["walk"]
    assert report["frame_durations_ms"] == [120, 120]
    assert report["pixel_integrity"]["exact_rgba_match"] is True
    assert [frame["changed_pixels"] for frame in report["pixel_integrity"]["frames"]] == [0, 0]


def test_real_aseprite_supports_phase6_pixel_master_layer_name(tmp_path):
    executable = find_aseprite()
    if executable is None:
        pytest.skip("Aseprite is not installed; real integration is unavailable.")
    report = build_master(
        executable,
        source=ASSETS / "true_pixel_art.png",
        frames=[],
        output_dir=tmp_path / "phase6",
        project_root=ROOT,
        character_id="test_character",
        tag_name="static",
        pixel_layer_name="PIXEL_MASTER",
    )

    assert report["layer_names"] == ["PIXEL_MASTER"]
    assert report["verified_layers"] == ["PIXEL_MASTER"]
    assert report["pixel_integrity"]["exact_rgba_match"] is True


def test_real_aseprite_builds_transparent_master_and_walk_scaffold_with_export_exclusion(tmp_path):
    executable = find_aseprite()
    if executable is None:
        pytest.skip("Aseprite is not installed; real integration is unavailable.")
    pixel = Image.new("RGBA", (160, 160), (255, 253, 240, 0))
    ImageDraw.Draw(pixel).rectangle((58, 20, 101, 139), fill=(185, 60, 35, 255))
    pixel_path = tmp_path / "game_master.png"
    pixel.save(pixel_path)
    background = Image.new("RGBA", (160, 160), (255, 253, 240, 255))
    ImageDraw.Draw(background).rectangle((58, 20, 101, 139), fill=(185, 60, 35, 255))
    background_path = tmp_path / "background_reference.png"
    background.save(background_path)
    game_master = build_game_master_revision(
        executable,
        pixel_png=pixel_path,
        background_png=background_path,
        output_dir=tmp_path / "static_revision",
        project_root=ROOT,
        character_id="test_character",
    )
    assert game_master["status"] == "PASS"
    assert game_master["default_visible_layers"] == ["PIXEL_MASTER"]
    assert {"PIXEL_MASTER", "BACKGROUND_REFERENCE"}.issubset(set(game_master["layer_names"]))
    assert game_master["pixel_integrity"]["exact_rgba_match"] is True

    references = []
    for index in range(8):
        image = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
        ImageDraw.Draw(image).rectangle((50 + index, 30, 104, 140), fill=(60, 130, 210, 220))
        path = tmp_path / f"reference_{index + 1}.png"
        image.save(path)
        references.append(path)
    report = build_animation_master(
        executable,
        pixel_png=game_master["export"],
        reference_pngs=references,
        output_dir=tmp_path / "animation",
        project_root=ROOT,
        character_id="test_character",
        frame_duration_ms=90,
        pivot=(80, 139),
        reference_opacity=128,
    )
    assert report["status"] == "ANIMATION_SCAFFOLD_READY"
    assert report["frame_count"] == 8
    assert report["tag"] == {"name": "walk", "from": 1, "to": 8, "direction": "forward"}
    assert report["verified_layers"] == ["PIXEL_ANIMATION", "REFERENCE_WALK"]
    assert report["frame_durations_ms"] == [90] * 8
    assert report["pixel_integrity"]["exact_match"] is True
    assert report["reference_integrity"]["exact_match"] is True
    assert report["game_export"]["reference_layer_excluded"] is True


def test_real_aseprite_saves_new_revision_and_preserves_reference_layer(tmp_path):
    executable = find_aseprite()
    if executable is None:
        pytest.skip("Aseprite is not installed; real integration is unavailable.")
    pixel = Image.new("RGBA", (160, 160), (255, 253, 240, 0))
    ImageDraw.Draw(pixel).rectangle((58, 20, 101, 139), fill=(185, 60, 35, 255))
    pixel_path = tmp_path / "pixel.png"
    pixel.save(pixel_path)
    references = []
    for index in range(8):
        reference = Image.new("RGBA", (160, 160), (255, 253, 240, 0))
        ImageDraw.Draw(reference).rectangle((48 + index, 24, 108, 140), fill=(60, 130, 210, 180))
        path = tmp_path / f"reference_{index}.png"
        reference.save(path)
        references.append(path)
    scaffold = build_animation_master(
        executable,
        pixel_png=pixel_path,
        reference_pngs=references,
        output_dir=tmp_path / "scaffold",
        project_root=ROOT,
        character_id="test_character",
        frame_duration_ms=90,
        pivot=(80, 139),
        reference_opacity=128,
    )
    frames = []
    for index in range(8):
        image = pixel.copy()
        ImageDraw.Draw(image).rectangle((58 + (index % 2), 130, 74 + (index % 2), 139), fill=(185, 60, 35, 255))
        path = tmp_path / f"edited_{index}.png"
        image.save(path)
        frames.append(path)
    output_master = tmp_path / "revision" / "test_character_animation_codex_r01.aseprite"
    report = save_animation_revision(
        executable,
        base_master=scaffold["master"],
        frame_pngs=frames,
        output_master=output_master,
        project_root=ROOT,
        frame_duration_ms=90,
        expected_references=references,
    )
    assert report["status"] == "ASEPRITE_REVISION_PASS"
    assert report["frame_count"] == 8
    assert report["frame_durations_ms"] == [90] * 8
    assert report["pixel_roundtrip_exact"] is True
    assert report["reference_roundtrip_exact"] is True
    assert {"PIXEL_ANIMATION", "REFERENCE_WALK"}.issubset(set(report["layers"]))
    assert "walk" in report["tags"]
    assert "character_pivot" in report["slices"]
