from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from PIL import Image, UnidentifiedImageError

from ..errors import PixelPipelineError


class AsepriteError(PixelPipelineError):
    """Aseprite could not be located, invoked, or verified."""


@dataclass(frozen=True)
class AsepriteExecutable:
    path: Path
    source: str


def _pixel_values(image: Image.Image) -> list[Any]:
    values = image.get_flattened_data() if hasattr(image, "get_flattened_data") else image.getdata()
    return list(values)


def find_aseprite(
    configured: str | None = None,
    *,
    environ: dict[str, str] | None = None,
    path_value: str | None = None,
) -> AsepriteExecutable | None:
    env = os.environ if environ is None else environ
    if configured:
        candidate = Path(configured).expanduser()
        if candidate.is_file():
            return AsepriteExecutable(candidate.resolve(), "config")
    env_path = env.get("ASEPRITE_PATH")
    if env_path:
        candidate = Path(env_path).expanduser()
        if candidate.is_file():
            return AsepriteExecutable(candidate.resolve(), "ASEPRITE_PATH")
    for name in ("aseprite", "Aseprite.exe", "aseprite.exe"):
        found = shutil.which(name, path=path_value if path_value is not None else env.get("PATH"))
        if found:
            return AsepriteExecutable(Path(found).resolve(), "PATH")
    roots = [
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Aseprite" / "Aseprite.exe",
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Aseprite" / "Aseprite.exe",
        Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "Programs" / "Aseprite" / "Aseprite.exe",
    ]
    for candidate in roots:
        if candidate.is_file():
            return AsepriteExecutable(candidate.resolve(), "common_install_location")
    return None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run(command: Sequence[str], timeout: int) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, check=False, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AsepriteError(f"Aseprite command failed to launch or timed out: {exc}") from exc


def get_version(executable: AsepriteExecutable, timeout: int = 30) -> str:
    result = _run([str(executable.path), "--version"], timeout)
    if result.returncode != 0:
        raise AsepriteError(f"Aseprite --version exited {result.returncode}: {result.stderr.strip()}")
    return (result.stdout or result.stderr).strip()


def _parse_xy(value: str | None) -> tuple[int, int] | None:
    if value is None:
        return None
    try:
        x, y = (int(part.strip()) for part in value.split(",", maxsplit=1))
    except (TypeError, ValueError) as exc:
        raise AsepriteError("Pivot must be supplied as x,y integers.") from exc
    return x, y


def build_master(
    executable: AsepriteExecutable,
    *,
    source: str | Path,
    frames: Sequence[str | Path],
    output_dir: str | Path,
    project_root: str | Path,
    character_id: str,
    tag_name: str = "static",
    pixel_layer_name: str = "Pixel",
    frame_duration_ms: int = 100,
    pivot: str | None = None,
    timeout: int = 120,
) -> dict[str, Any]:
    source_path = Path(source).expanduser().resolve()
    frame_paths = [Path(frame).expanduser().resolve() for frame in frames]
    output = Path(output_dir).expanduser().resolve()
    lua_path = Path(project_root).resolve() / "scripts" / "aseprite" / "build_master.lua"
    if not source_path.is_file():
        raise AsepriteError(f"Source PNG does not exist: {source_path}")
    if not lua_path.is_file():
        raise AsepriteError(f"Aseprite Lua helper is missing: {lua_path}")
    if output.exists():
        raise AsepriteError(f"Aseprite output directory already exists: {output}")
    if not character_id.strip() or not tag_name.strip() or not pixel_layer_name.strip():
        raise AsepriteError("Character ID, tag name and pixel layer name must not be empty.")
    if frame_duration_ms < 1:
        raise AsepriteError("Frame duration must be a positive number of milliseconds.")
    output.mkdir(parents=True)
    master_path = output / "master.aseprite"
    sheet_path = output / "sheet.png"
    sheet_json_path = output / "sheet.json"
    command = [str(executable.path), "--batch", str(source_path)]
    script_params = [
        ("layer_name", pixel_layer_name),
        ("tag_name", tag_name),
        ("frame_duration_ms", str(frame_duration_ms)),
    ]
    for index, frame_path in enumerate(frame_paths, start=2):
        if not frame_path.is_file():
            raise AsepriteError(f"Additional frame PNG does not exist: {frame_path}")
        script_params.append((f"frame_{index}", str(frame_path)))
    pivot_xy = _parse_xy(pivot)
    if pivot_xy is not None:
        script_params.extend((("pivot_x", str(pivot_xy[0])), ("pivot_y", str(pivot_xy[1]))))
    for name, value in script_params:
        command.extend(("--script-param", f"{name}={value}"))
    command.extend(("--script", str(lua_path), "--save-as", str(master_path)))
    build_result = _run(command, timeout)
    if build_result.returncode != 0 or not master_path.is_file():
        raise AsepriteError(
            f"Aseprite master build failed (exit {build_result.returncode}).\n"
            f"stdout: {build_result.stdout.strip()}\nstderr: {build_result.stderr.strip()}"
        )
    layer_result = _run([str(executable.path), "--batch", "--list-layers", str(master_path)], timeout)
    tag_result = _run([str(executable.path), "--batch", "--list-tags", str(master_path)], timeout)
    if layer_result.returncode != 0 or pixel_layer_name not in layer_result.stdout.splitlines():
        raise AsepriteError(f"Aseprite master is missing the required {pixel_layer_name} layer: {layer_result.stdout.strip()}")
    if tag_result.returncode != 0 or tag_name not in tag_result.stdout.splitlines():
        raise AsepriteError(f"Aseprite master is missing tag '{tag_name}': {tag_result.stdout.strip()}")
    slice_result = None
    if pivot_xy is not None:
        slice_result = _run([str(executable.path), "--batch", "--list-slices", str(master_path)], timeout)
        if slice_result.returncode != 0 or "character_pivot" not in slice_result.stdout.splitlines():
            raise AsepriteError(f"Aseprite master is missing the configured character_pivot slice: {slice_result.stdout.strip()}")
    export_command = [
        str(executable.path), "--batch", str(master_path),
        "--sheet", str(sheet_path), "--sheet-type", "horizontal", "--data", str(sheet_json_path),
    ]
    export_result = _run(export_command, timeout)
    if export_result.returncode != 0 or not sheet_path.is_file() or not sheet_json_path.is_file():
        raise AsepriteError(
            f"Aseprite sprite-sheet export failed (exit {export_result.returncode}).\n"
            f"stdout: {export_result.stdout.strip()}\nstderr: {export_result.stderr.strip()}"
        )
    try:
        with Image.open(source_path) as source_image:
            original = source_image.convert("RGBA")
        with Image.open(sheet_path) as exported_image:
            exported = exported_image.convert("RGBA")
        sheet_data = json.loads(sheet_json_path.read_text(encoding="utf-8"))
    except (OSError, UnidentifiedImageError, json.JSONDecodeError) as exc:
        raise AsepriteError(f"Could not decode Aseprite round-trip output: {exc}") from exc
    expected_count = 1 + len(frame_paths)
    if isinstance(sheet_data, dict) and isinstance(sheet_data.get("frames"), (dict, list)):
        exported_frames = list(sheet_data["frames"].values()) if isinstance(sheet_data["frames"], dict) else sheet_data["frames"]
        exported_count = len(exported_frames)
    else:
        raise AsepriteError("Aseprite JSON export did not contain a frames object/list.")
    expected_width = original.width * expected_count
    if exported_count != expected_count or exported.size != (expected_width, original.height):
        raise AsepriteError(
            f"Sprite sheet dimensions/frame count mismatch: got {exported.width}x{exported.height} with {exported_count} frames; "
            f"expected {expected_width}x{original.height} with {expected_count} frames."
        )
    frame_durations = [int(item.get("duration", -1)) for item in exported_frames]
    if any(duration != frame_duration_ms for duration in frame_durations):
        raise AsepriteError(f"Aseprite frame durations do not match the requested {frame_duration_ms}ms: {frame_durations}")
    frame_integrity = []
    for index, source_frame in enumerate([source_path, *frame_paths]):
        try:
            with Image.open(source_frame) as image:
                expected = image.convert("RGBA")
        except (OSError, UnidentifiedImageError) as exc:
            raise AsepriteError(f"Cannot decode source frame '{source_frame}': {exc}") from exc
        x0 = index * original.width
        actual = exported.crop((x0, 0, x0 + original.width, original.height))
        expected_pixels = _pixel_values(expected)
        actual_pixels = _pixel_values(actual)
        diff = sum(1 for left, right in zip(expected_pixels, actual_pixels) if left != right)
        frame_integrity.append({"frame": index + 1, "source": str(source_frame), "changed_pixels": diff, "exact_rgba_match": diff == 0})
    diff = sum(item["changed_pixels"] for item in frame_integrity)
    if diff:
        raise AsepriteError(f"Aseprite round trip changed {diff} pixels across exported frames; expected exact RGBA integrity.")
    version = get_version(executable, timeout=min(timeout, 30))
    report = {
        "schema_version": 1,
        "status": "PASS",
        "aseprite_path": str(executable.path),
        "aseprite_discovery_source": executable.source,
        "aseprite_version": version,
        "character_id": character_id,
        "source_png": str(source_path),
        "source_sha256": _sha256(source_path),
        "source_dimensions": {"width": original.width, "height": original.height},
        "master": str(master_path),
        "master_sha256": _sha256(master_path),
        "layer_names": [pixel_layer_name],
        "tag": {"name": tag_name, "from": 1, "to": expected_count, "direction": "forward"},
        "pivot": {"x": pivot_xy[0], "y": pivot_xy[1]} if pivot_xy is not None else None,
        "frame_duration_ms": frame_duration_ms,
        "frame_durations_ms": frame_durations,
        "frames": expected_count,
        "sprite_sheet": str(sheet_path),
        "sprite_sheet_dimensions": {"width": exported.width, "height": exported.height},
        "json_metadata": str(sheet_json_path),
        "pixel_integrity": {"comparison": "each source PNG vs corresponding exported frame", "changed_pixels": diff, "exact_rgba_match": diff == 0, "frames": frame_integrity},
        "verified_layers": layer_result.stdout.splitlines(),
        "verified_tags": tag_result.stdout.splitlines(),
        "verified_slices": slice_result.stdout.splitlines() if slice_result is not None else [],
        "stdout": {"build": build_result.stdout.strip(), "export": export_result.stdout.strip()},
        "stderr": {"build": build_result.stderr.strip(), "export": export_result.stderr.strip()},
    }
    report_path = output / "aseprite_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def export_static_png(
    executable: AsepriteExecutable,
    master: str | Path,
    destination: str | Path,
    *,
    expected_source: str | Path,
    timeout: int = 120,
) -> dict[str, Any]:
    master_path = Path(master).expanduser().resolve()
    output_path = Path(destination).expanduser().resolve()
    expected_path = Path(expected_source).expanduser().resolve()
    if not master_path.is_file():
        raise AsepriteError(f"Aseprite master does not exist: {master_path}")
    if not expected_path.is_file():
        raise AsepriteError(f"Expected source PNG does not exist: {expected_path}")
    if output_path.exists():
        raise AsepriteError(f"Static export already exists; refusing to overwrite it: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result = _run([str(executable.path), "--batch", str(master_path), "--save-as", str(output_path)], timeout)
    if result.returncode != 0 or not output_path.is_file():
        raise AsepriteError(
            f"Aseprite PNG export failed (exit {result.returncode}).\n"
            f"stdout: {result.stdout.strip()}\nstderr: {result.stderr.strip()}"
        )
    try:
        with Image.open(expected_path) as opened:
            expected = opened.convert("RGBA")
        with Image.open(output_path) as opened:
            exported = opened.convert("RGBA")
    except (OSError, UnidentifiedImageError) as exc:
        raise AsepriteError(f"Aseprite export is not a readable PNG: {exc}") from exc
    if exported.size != expected.size:
        raise AsepriteError(f"Aseprite export dimensions changed: expected {expected.size}, got {exported.size}.")
    expected_pixels = _pixel_values(expected)
    exported_pixels = _pixel_values(exported)
    changed = sum(1 for before, after in zip(expected_pixels, exported_pixels) if before != after)
    if changed:
        raise AsepriteError(f"Aseprite static PNG export changed {changed} pixels; exact RGBA match was required.")
    alpha = _pixel_values(exported.getchannel("A"))
    alpha_counts = Counter(alpha)
    return {
        "status": "PASS",
        "master": str(master_path),
        "expected_source": str(expected_path),
        "export_png": str(output_path),
        "sha256": _sha256(output_path),
        "dimensions": [exported.width, exported.height],
        "changed_pixels": changed,
        "exact_rgba_match": True,
        "alpha": {
            "unique_values": sorted(alpha_counts),
            "transparent_pixels": alpha_counts.get(0, 0),
            "opaque_pixels": alpha_counts.get(255, 0),
            "semi_transparent_pixels": sum(value for alpha_value, value in alpha_counts.items() if alpha_value not in (0, 255)),
        },
        "unique_visible_colors": len({pixel[:3] for pixel in _pixel_values(exported) if pixel[3] > 0}),
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def build_game_master_revision(
    executable: AsepriteExecutable,
    *,
    pixel_png: str | Path,
    background_png: str | Path,
    output_dir: str | Path,
    project_root: str | Path,
    character_id: str,
    background_opacity: int = 96,
    timeout: int = 120,
) -> dict[str, Any]:
    pixel_path = Path(pixel_png).expanduser().resolve()
    background_path = Path(background_png).expanduser().resolve()
    output = Path(output_dir).expanduser().resolve()
    script = Path(project_root).resolve() / "scripts" / "aseprite" / "build_game_master.lua"
    for path in (pixel_path, background_path, script):
        if not path.is_file():
            raise AsepriteError(f"Game master input/helper does not exist: {path}")
    if output.exists():
        raise AsepriteError(f"Game master output directory already exists: {output}")
    if not 0 <= background_opacity <= 255:
        raise AsepriteError("background_opacity must be in the range 0..255.")
    output.mkdir(parents=True)
    master = output / f"{character_id}_game_master.aseprite"
    export = output / "GAME_MASTER_EXPORT.png"
    command = [str(executable.path), "--batch", str(pixel_path), "--script-param", "pixel_layer_name=PIXEL_MASTER", "--script-param", "background_layer_name=BACKGROUND_REFERENCE", "--script-param", f"background_path={background_path}", "--script-param", f"background_opacity={background_opacity}", "--script", str(script), "--save-as", str(master)]
    built = _run(command, timeout)
    if built.returncode != 0 or not master.is_file():
        raise AsepriteError(f"Aseprite transparent game master build failed (exit {built.returncode}).\nstdout: {built.stdout.strip()}\nstderr: {built.stderr.strip()}")
    layer_result = _run([str(executable.path), "--batch", "--list-layers", str(master)], timeout)
    all_layer_result = _run([str(executable.path), "--batch", "--all-layers", "--list-layers", str(master)], timeout)
    if layer_result.returncode != 0 or layer_result.stdout.splitlines() != ["PIXEL_MASTER"]:
        raise AsepriteError(f"Game export layer list must contain only PIXEL_MASTER by default: {layer_result.stdout.strip()}")
    if all_layer_result.returncode != 0 or not {"PIXEL_MASTER", "BACKGROUND_REFERENCE"}.issubset(set(all_layer_result.stdout.splitlines())):
        raise AsepriteError(f"Game master revision is missing its background reference layer: {all_layer_result.stdout.strip()}")
    exported = _run([str(executable.path), "--batch", str(master), "--layer", "PIXEL_MASTER", "--save-as", str(export)], timeout)
    if exported.returncode != 0 or not export.is_file():
        raise AsepriteError(f"Could not export PIXEL_MASTER as a game PNG (exit {exported.returncode}).\n{exported.stderr.strip()}")
    try:
        with Image.open(pixel_path) as opened:
            expected = opened.convert("RGBA")
        with Image.open(export) as opened:
            actual = opened.convert("RGBA")
    except (OSError, UnidentifiedImageError) as exc:
        raise AsepriteError(f"Game master export is not a readable PNG: {exc}") from exc
    changed = sum(left != right for left, right in zip(_pixel_values(expected), _pixel_values(actual)))
    if expected.size != actual.size or changed:
        raise AsepriteError(f"PIXEL_MASTER export changed from its transparent source ({changed} pixel channels).")
    return {
        "status": "PASS",
        "master": str(master),
        "master_sha256": _sha256(master),
        "pixel_source": str(pixel_path),
        "background_reference_source": str(background_path),
        "export": str(export),
        "dimensions": [actual.width, actual.height],
        "layer_names": all_layer_result.stdout.splitlines(),
        "default_visible_layers": layer_result.stdout.splitlines(),
        "game_export_layer": "PIXEL_MASTER",
        "background_reference_visibility": "hidden by default; excluded by explicit PIXEL_MASTER export",
        "pixel_integrity": {"changed_pixels": changed, "exact_rgba_match": changed == 0},
        "background_reference_opacity": background_opacity,
        "aseprite_version": get_version(executable, timeout=min(timeout, 30)),
    }


def build_animation_master(
    executable: AsepriteExecutable,
    *,
    pixel_png: str | Path,
    reference_pngs: Sequence[str | Path],
    output_dir: str | Path,
    project_root: str | Path,
    character_id: str,
    frame_duration_ms: int,
    pivot: tuple[int, int],
    reference_opacity: int = 128,
    timeout: int = 120,
) -> dict[str, Any]:
    pixel_path = Path(pixel_png).expanduser().resolve()
    references = [Path(path).expanduser().resolve() for path in reference_pngs]
    output = Path(output_dir).expanduser().resolve()
    script = Path(project_root).resolve() / "scripts" / "aseprite" / "build_animation_scaffold.lua"
    if not pixel_path.is_file() or not script.is_file() or not references:
        raise AsepriteError("Animation scaffold needs a transparent PIXEL_MASTER PNG, reference images, and its Lua helper.")
    if output.exists():
        raise AsepriteError(f"Animation scaffold output already exists: {output}")
    if not 6 <= len(references) <= 8:
        raise AsepriteError("Walk animation scaffold needs 6–8 explicitly selected reference frames.")
    if frame_duration_ms < 1 or not 0 <= reference_opacity <= 255:
        raise AsepriteError("Frame duration and reference opacity are outside their valid ranges.")
    output.mkdir(parents=True)
    master = output / f"{character_id}_animation.aseprite"
    pixel_sheet, pixel_json = output / "walk_pixel_export.png", output / "walk_pixel_export.json"
    reference_sheet, reference_json = output / "walk_reference_export.png", output / "walk_reference_export.json"
    preview_sheet, preview_json = output / "walk_scaffold_preview.png", output / "walk_scaffold_preview.json"
    command = [str(executable.path), "--batch", str(pixel_path), "--script-param", "pixel_layer_name=PIXEL_ANIMATION", "--script-param", "reference_layer_name=REFERENCE_WALK", "--script-param", "tag_name=walk", "--script-param", f"pixel_png={pixel_path}", "--script-param", f"frame_duration_ms={frame_duration_ms}", "--script-param", f"pivot_x={pivot[0]}", "--script-param", f"pivot_y={pivot[1]}", "--script-param", f"reference_opacity={reference_opacity}"]
    for index, path in enumerate(references, start=1):
        if not path.is_file():
            raise AsepriteError(f"Animation reference frame does not exist: {path}")
        command.extend(("--script-param", f"reference_{index}={path}"))
    command.extend(("--script", str(script), "--save-as", str(master)))
    built = _run(command, timeout)
    if built.returncode != 0 or not master.is_file():
        raise AsepriteError(f"Aseprite animation scaffold build failed (exit {built.returncode}).\nstdout: {built.stdout.strip()}\nstderr: {built.stderr.strip()}")
    list_layers = _run([str(executable.path), "--batch", "--list-layers", str(master)], timeout)
    list_tags = _run([str(executable.path), "--batch", "--list-tags", str(master)], timeout)
    list_slices = _run([str(executable.path), "--batch", "--list-slices", str(master)], timeout)
    required_layers = {"PIXEL_ANIMATION", "REFERENCE_WALK"}
    if list_layers.returncode or not required_layers.issubset(set(list_layers.stdout.splitlines())):
        raise AsepriteError(f"Animation master does not contain the required layers: {list_layers.stdout.strip()}")
    if list_tags.returncode or "walk" not in list_tags.stdout.splitlines():
        raise AsepriteError(f"Animation master is missing its walk tag: {list_tags.stdout.strip()}")
    if list_slices.returncode or "character_pivot" not in list_slices.stdout.splitlines():
        raise AsepriteError(f"Animation master is missing its fixed character pivot: {list_slices.stdout.strip()}")

    def export_layer(layer: str, sheet_path: Path, data_path: Path, *, all_layers: bool = False) -> subprocess.CompletedProcess[str]:
        args = [str(executable.path), "--batch", str(master), "--tag", "walk"]
        args.extend(["--all-layers"] if all_layers else ["--layer", layer])
        args.extend(["--sheet", str(sheet_path), "--sheet-type", "horizontal", "--data", str(data_path), "--format", "json-array"])
        result = _run(args, timeout)
        if result.returncode != 0 or not sheet_path.is_file() or not data_path.is_file():
            raise AsepriteError(f"Aseprite {layer} export failed (exit {result.returncode}): {result.stderr.strip()}")
        return result

    preview_export = export_layer("all layers", preview_sheet, preview_json, all_layers=True)
    with Image.open(pixel_path) as opened:
        pixel_size = opened.size
    with Image.open(pixel_path) as opened:
        expected_pixel = opened.convert("RGBA")
    pixel_frames: list[Image.Image] = []
    reference_frames: list[Image.Image] = []
    pixel_commands: list[str] = []
    reference_commands: list[str] = []
    pixel_diffs: list[int] = []
    ref_diffs: list[int] = []
    frame_root = output / "aseprite_frame_exports"
    pixel_frame_root = frame_root / "pixel_animation"
    reference_frame_root = frame_root / "reference_walk"
    pixel_frame_root.mkdir(parents=True)
    reference_frame_root.mkdir(parents=True)
    for index, reference_path in enumerate(references, start=1):
        pixel_png = pixel_frame_root / f"frame_{index:02d}.png"
        # Aseprite 1.3 CLI frame-range indices are zero-based, while Python's loop is one-based.
        cli_frame_index = index - 1
        pixel_command = [str(executable.path), "--batch", str(master), "--frame-range", f"{cli_frame_index},{cli_frame_index}", "--ignore-layer", "REFERENCE_WALK", "--save-as", str(pixel_png)]
        pixel_result = _run(pixel_command, timeout)
        if pixel_result.returncode != 0 or not pixel_png.is_file():
            raise AsepriteError(f"Aseprite game export failed on frame {index}: {pixel_result.stderr.strip()}")
        with Image.open(pixel_png) as opened:
            actual_pixel = opened.convert("RGBA")
        if actual_pixel.size != pixel_size:
            raise AsepriteError(f"Aseprite game export frame {index} has the wrong size: {actual_pixel.size} != {pixel_size}.")
        pixel_frames.append(actual_pixel)
        pixel_diff = sum(a != b for a, b in zip(_pixel_values(expected_pixel), _pixel_values(actual_pixel)))
        pixel_diffs.append(pixel_diff)
        pixel_commands.append(pixel_result.stdout.strip())

        reference_png = reference_frame_root / f"frame_{index:02d}.png"
        reference_command = [str(executable.path), "--batch", str(master), "--frame-range", f"{cli_frame_index},{cli_frame_index}", "--ignore-layer", "PIXEL_ANIMATION", "--save-as", str(reference_png)]
        reference_result = _run(reference_command, timeout)
        if reference_result.returncode != 0 or not reference_png.is_file():
            raise AsepriteError(f"Aseprite reference QA export failed on frame {index}: {reference_result.stderr.strip()}")
        with Image.open(reference_png) as opened:
            actual_reference = opened.convert("RGBA")
        with Image.open(reference_path) as opened:
            expected = opened.convert("RGBA")
        alpha = expected.getchannel("A").point(lambda value: round(value * reference_opacity / 255))
        expected.putalpha(alpha)
        reference_frames.append(actual_reference)
        ref_diffs.append(sum(a != b for a, b in zip(_pixel_values(expected), _pixel_values(actual_reference))))
        reference_commands.append(reference_result.stdout.strip())
    if any(ref_diffs):
        raise AsepriteError(f"Reference frames were not imported at their corresponding frames: {ref_diffs}")
    if any(pixel_diffs):
        raise AsepriteError(f"PIXEL_ANIMATION was contaminated or altered; per-frame pixel differences: {pixel_diffs}")
    pixel_sheet_image = Image.new("RGBA", (pixel_size[0] * len(pixel_frames), pixel_size[1]), (0, 0, 0, 0))
    reference_sheet_image = Image.new("RGBA", (pixel_size[0] * len(reference_frames), pixel_size[1]), (0, 0, 0, 0))
    records = []
    for index, (pixel_frame, reference_frame) in enumerate(zip(pixel_frames, reference_frames)):
        x = index * pixel_size[0]
        pixel_sheet_image.alpha_composite(pixel_frame, (x, 0))
        reference_sheet_image.alpha_composite(reference_frame, (x, 0))
        frame_record = {"filename": f"{master.stem}_{index + 1:02d}.png", "frame": {"x": x, "y": 0, "w": pixel_size[0], "h": pixel_size[1]}, "rotated": False, "trimmed": False, "duration": frame_duration_ms}
        records.append(frame_record)
    pixel_sheet_image.save(pixel_sheet)
    reference_sheet_image.save(reference_sheet)
    pixel_sheet_data = {"frames": records, "meta": {"image": pixel_sheet.name, "format": "RGBA8888", "size": {"w": pixel_sheet_image.width, "h": pixel_sheet_image.height}}}
    reference_sheet_data = {"frames": [{**item, "filename": f"reference_{index + 1:02d}.png"} for index, item in enumerate(records)], "meta": {"image": reference_sheet.name, "format": "RGBA8888", "size": {"w": reference_sheet_image.width, "h": reference_sheet_image.height}}}
    pixel_json.write_text(json.dumps(pixel_sheet_data, indent=2) + "\n", encoding="utf-8")
    reference_json.write_text(json.dumps(reference_sheet_data, indent=2) + "\n", encoding="utf-8")
    preview_data = json.loads(preview_json.read_text(encoding="utf-8"))
    preview_records = preview_data.get("frames", [])
    if not isinstance(preview_records, list) or len(preview_records) != len(references):
        raise AsepriteError("Aseprite preview metadata does not contain the expected tagged frame count.")
    durations = [int(item.get("duration", -1)) for item in preview_records]
    if durations != [frame_duration_ms] * len(references):
        raise AsepriteError(f"Animation frame duration mismatch: {durations}")
    report = {
        "schema_version": 1,
        "status": "ANIMATION_SCAFFOLD_READY",
        "character_id": character_id,
        "aseprite_path": str(executable.path),
        "aseprite_version": get_version(executable, timeout=min(timeout, 30)),
        "master": str(master),
        "master_sha256": _sha256(master),
        "source_pixel_png": str(pixel_path),
        "canvas": {"width": expected_pixel.width, "height": expected_pixel.height},
        "frame_count": len(references),
        "tag": {"name": "walk", "from": 1, "to": len(references), "direction": "forward"},
        "layers": {"pixel": "PIXEL_ANIMATION", "reference": "REFERENCE_WALK", "reference_opacity": reference_opacity, "reference_visible": True, "reference_excluded_from_game_export_by": "per-frame Aseprite CLI export with --ignore-layer REFERENCE_WALK"},
        "pivot": {"type": "bottom_center", "x": pivot[0], "y": pivot[1], "slice": "character_pivot"},
        "frame_duration_ms": frame_duration_ms,
        "frame_durations_ms": durations,
        "pixel_integrity": {"source": str(pixel_path), "per_frame_changed_pixels": pixel_diffs, "changed_pixels": sum(pixel_diffs), "exact_match": all(value == 0 for value in pixel_diffs)},
        "reference_integrity": {"sources": [str(path) for path in references], "per_frame_changed_pixels_after_layer_opacity": ref_diffs, "exact_match": all(value == 0 for value in ref_diffs)},
        "game_export": {"path": str(pixel_sheet), "metadata": str(pixel_json), "frames": len(pixel_frames), "aseprite_exported_frame_directory": str(pixel_frame_root), "reference_layer_excluded": True, "purpose": "Aseprite CLI integrity and reference-exclusion QA; PIXEL_ANIMATION still contains static copies.", "final_game_animation": False},
        "reference_export_qa": {"path": str(reference_sheet), "metadata": str(reference_json)},
        "scaffold_preview": {"path": str(preview_sheet), "metadata": str(preview_json)},
        "verified_layers": list_layers.stdout.splitlines(),
        "verified_tags": list_tags.stdout.splitlines(),
        "verified_slices": list_slices.stdout.splitlines(),
        "commands": {"game_export_frames": pixel_commands, "reference_export_frames": reference_commands, "preview": preview_export.stdout.strip()},
    }
    (output / "animation_scaffold_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def render_animation_frame(
    executable: AsepriteExecutable,
    *,
    master: str | Path,
    frame_index: int,
    output_png: str | Path,
    timeout: int = 120,
) -> dict[str, Any]:
    """Render one zero-based animation frame with the motion-reference layer excluded."""
    source = Path(master).expanduser().resolve()
    output = Path(output_png).expanduser().resolve()
    if not source.is_file():
        raise AsepriteError(f"Aseprite master does not exist: {source}")
    if frame_index < 0:
        raise AsepriteError("Frame index must be zero-based and non-negative.")
    output.parent.mkdir(parents=True, exist_ok=True)
    result = _run(
        [str(executable.path), "--batch", str(source), "--frame-range", f"{frame_index},{frame_index}", "--ignore-layer", "REFERENCE_WALK", "--save-as", str(output)],
        timeout,
    )
    if result.returncode != 0 or not output.is_file():
        raise AsepriteError(f"Aseprite failed to render frame {frame_index}: {result.stderr.strip()}")
    try:
        with Image.open(output) as image:
            rendered = image.convert("RGBA")
    except (OSError, UnidentifiedImageError) as exc:
        raise AsepriteError(f"Aseprite output is not a readable PNG: {output}") from exc
    if rendered.size != (160, 160):
        raise AsepriteError(f"Rendered frame {frame_index} has unexpected dimensions: {rendered.size}.")
    return {"frame_index": frame_index, "path": str(output), "dimensions": list(rendered.size), "aseprite_stdout": result.stdout.strip()}


def save_animation_revision(
    executable: AsepriteExecutable,
    *,
    base_master: str | Path,
    frame_pngs: Sequence[str | Path],
    output_master: str | Path,
    project_root: str | Path,
    frame_duration_ms: int = 90,
    expected_references: Sequence[str | Path] | None = None,
    timeout: int = 120,
) -> dict[str, Any]:
    """Replace only PIXEL_ANIMATION cels on a copy of an existing scaffold, preserving its metadata."""
    base = Path(base_master).expanduser().resolve()
    frames = [Path(frame).expanduser().resolve() for frame in frame_pngs]
    references = [Path(path).expanduser().resolve() for path in expected_references or []]
    output = Path(output_master).expanduser().resolve()
    script = Path(project_root).resolve() / "scripts" / "aseprite" / "apply_animation_frames.lua"
    if not base.is_file() or not script.is_file() or len(frames) != 8:
        raise AsepriteError("Animation revision needs a base Aseprite scaffold, its Lua helper, and exactly eight rendered PNG frames.")
    if output.exists():
        raise AsepriteError(f"Refusing to overwrite an Aseprite revision: {output}")
    if expected_references is not None and len(references) != 8:
        raise AsepriteError("Reference integrity verification requires all eight walk references.")
    if frame_duration_ms != 90:
        raise AsepriteError("Phase 11 walk revision must preserve the validated 90ms frame timing.")
    for index, path in enumerate(frames):
        if not path.is_file():
            raise AsepriteError(f"Edited animation frame {index} does not exist: {path}")
        with Image.open(path) as opened:
            if opened.size != (160, 160):
                raise AsepriteError(f"Edited frame {index} has the wrong canvas: {opened.size}.")
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [str(executable.path), "--batch", str(base), "--script-param", "pixel_layer_name=PIXEL_ANIMATION", "--script-param", "frame_count=8"]
    for index, path in enumerate(frames, start=1):
        command.extend(("--script-param", f"frame_{index}={path}"))
    command.extend(("--script", str(script), "--save-as", str(output)))
    built = _run(command, timeout)
    if built.returncode != 0 or not output.is_file():
        raise AsepriteError(f"Aseprite revision save failed (exit {built.returncode}).\nstdout: {built.stdout.strip()}\nstderr: {built.stderr.strip()}")

    layers = _run([str(executable.path), "--batch", "--list-layers", str(output)], timeout)
    tags = _run([str(executable.path), "--batch", "--list-tags", str(output)], timeout)
    slices = _run([str(executable.path), "--batch", "--list-slices", str(output)], timeout)
    if layers.returncode or not {"PIXEL_ANIMATION", "REFERENCE_WALK"}.issubset(set(layers.stdout.splitlines())):
        raise AsepriteError(f"Saved revision did not preserve its animation layers: {layers.stdout.strip()}")
    if tags.returncode or "walk" not in tags.stdout.splitlines():
        raise AsepriteError(f"Saved revision did not preserve the walk tag: {tags.stdout.strip()}")
    if slices.returncode or "character_pivot" not in slices.stdout.splitlines():
        raise AsepriteError(f"Saved revision did not preserve the character pivot: {slices.stdout.strip()}")

    export_root = output.parent / "aseprite_frame_exports"
    pixel_root = export_root / "pixel_animation"
    reference_root = export_root / "reference_walk"
    pixel_root.mkdir(parents=True, exist_ok=True)
    reference_root.mkdir(parents=True, exist_ok=True)
    pixel_diffs: list[int] = []
    reference_diffs: list[int] = []
    render_records: list[dict[str, Any]] = []
    for index, expected_path in enumerate(frames):
        pixel_export = pixel_root / f"walk_{index:02d}.png"
        actual = render_animation_frame(executable, master=output, frame_index=index, output_png=pixel_export, timeout=timeout)
        with Image.open(expected_path) as source_image:
            expected = source_image.convert("RGBA")
        with Image.open(pixel_export) as rendered_image:
            rendered = rendered_image.convert("RGBA")
        pixel_diff = sum(a != b for a, b in zip(_pixel_values(expected), _pixel_values(rendered)))
        pixel_diffs.append(pixel_diff)
        frame_record: dict[str, Any] = {"frame": index, "pixel_export": str(pixel_export), "pixel_changed_channels": pixel_diff, "pixel_exact_match": pixel_diff == 0}
        if references:
            reference_export = reference_root / f"walk_{index:02d}.png"
            reference_result = _run([str(executable.path), "--batch", str(output), "--frame-range", f"{index},{index}", "--ignore-layer", "PIXEL_ANIMATION", "--save-as", str(reference_export)], timeout)
            if reference_result.returncode != 0 or not reference_export.is_file():
                raise AsepriteError(f"Aseprite failed to preserve reference frame {index}: {reference_result.stderr.strip()}")
            with Image.open(references[index]) as reference_image:
                expected_reference = reference_image.convert("RGBA")
            alpha = expected_reference.getchannel("A").point(lambda value: round(value * 128 / 255))
            expected_reference.putalpha(alpha)
            with Image.open(reference_export) as actual_reference_image:
                actual_reference = actual_reference_image.convert("RGBA")
            reference_diff = sum(a != b for a, b in zip(_pixel_values(expected_reference), _pixel_values(actual_reference)))
            reference_diffs.append(reference_diff)
            frame_record.update({"reference_export": str(reference_export), "reference_changed_channels": reference_diff, "reference_exact_match": reference_diff == 0})
        render_records.append(frame_record)
        if pixel_diff:
            raise AsepriteError(f"Aseprite pixel cel round-trip differs on frame {index}: {pixel_diff} channels.")
        if references and reference_diffs[-1]:
            raise AsepriteError(f"Aseprite reference cel changed on frame {index}: {reference_diffs[-1]} channels.")

    sheet_path = output.parent / "walk_pixel_export.png"
    data_path = output.parent / "walk_pixel_export.json"
    sheet_result = _run([str(executable.path), "--batch", str(output), "--tag", "walk", "--layer", "PIXEL_ANIMATION", "--sheet", str(sheet_path), "--sheet-type", "horizontal", "--data", str(data_path), "--format", "json-array"], timeout)
    if sheet_result.returncode or not sheet_path.is_file() or not data_path.is_file():
        raise AsepriteError(f"Aseprite sprite-sheet export failed: {sheet_result.stderr.strip()}")
    metadata = json.loads(data_path.read_text(encoding="utf-8"))
    exported_records = metadata.get("frames", [])
    durations = [int(row.get("duration", -1)) for row in exported_records]
    if len(exported_records) != 8 or durations != [frame_duration_ms] * 8:
        raise AsepriteError(f"Saved walk tag does not contain eight {frame_duration_ms}ms frames: {durations}")
    return {
        "status": "ASEPRITE_REVISION_PASS",
        "base_master": str(base),
        "master": str(output),
        "master_sha256": _sha256(output),
        "frame_count": 8,
        "frame_duration_ms": frame_duration_ms,
        "frame_durations_ms": durations,
        "tag": "walk",
        "layers": layers.stdout.splitlines(),
        "tags": tags.stdout.splitlines(),
        "slices": slices.stdout.splitlines(),
        "pixel_roundtrip_exact": all(value == 0 for value in pixel_diffs),
        "pixel_frame_diffs": pixel_diffs,
        "reference_roundtrip_exact": all(value == 0 for value in reference_diffs) if references else None,
        "reference_frame_diffs": reference_diffs,
        "frame_exports": render_records,
        "sprite_sheet": str(sheet_path),
        "sprite_sheet_metadata": str(data_path),
        "aseprite_version": get_version(executable, timeout=min(timeout, 30)),
        "commands": {"save": built.stdout.strip(), "export": sheet_result.stdout.strip()},
    }
