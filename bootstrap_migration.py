"""One-time source-first migration; never modifies the legacy repository."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parent
OLD = ROOT.parent / 'pixel-pipeline'
records = []
def copy(source, destination, replace=None):
    src, dst = OLD / source, ROOT / destination
    dst.parent.mkdir(parents=True, exist_ok=True)
    if replace:
        dst.write_text(src.read_text(encoding='utf-8').replace(*replace), encoding='utf-8')
    else:
        shutil.copy2(src, dst)
    records.append({'source': str(src), 'destination': destination, 'source_sha256': hashlib.sha256(src.read_bytes()).hexdigest(), 'destination_sha256': hashlib.sha256(dst.read_bytes()).hexdigest()})

modules = {'': ['config.py', 'errors.py'], 'comfy_bridge': ['client.py', 'runner.py', 'workflow_loader.py'], 'aseprite_bridge': ['runner.py'], 'pixel_gate': ['analyzer.py', 'refiner.py', 'resolution.py', 'report.py', 'subject_refiner.py'], 'motion_extractor': ['extract.py', 'keyframes.py']}
for folder, files in modules.items():
    for filename in files:
        rel = '/'.join(p for p in [folder, filename] if p)
        copy('src/pixel_pipeline/' + rel, 'src/assetpipe/_ported/' + rel)
    target = ROOT / 'src/assetpipe/_ported' / folder / '__init__.py'
    target.write_text('', encoding='utf-8')
for file in ['build_master.lua', 'build_game_master.lua', 'build_animation_scaffold.lua', 'apply_animation_frames.lua']:
    copy('scripts/aseprite/' + file, 'scripts/aseprite/' + file)
for file in ['baseline_anima_api.json', 'anima_mushroom_courier_production.json', 'anima_tomohi_api.json', 'krea2_turbo_api.json', 'deno_minimax_h3_r2v_8step.json', 'concept_character.json']:
    copy('config/workflows/' + file, 'config/workflows/' + file)
copy('config/pipeline.yaml', 'config/pipeline.yaml')
copy('config/workflow_registry.yaml', 'config/workflow_registry.yaml')
for name in ['test_pixel_analyzer.py', 'test_refiner.py', 'test_subject_refiner.py', 'test_resolution_gate.py', 'test_motion_extractor.py', 'test_motion_keyframes.py', 'test_aseprite_bridge.py', 'test_comfy_workflows.py']:
    copy('tests/' + name, 'tests/' + name, ('pixel_pipeline', 'assetpipe._ported'))
for file in (OLD / 'tests/assets').glob('*.png'):
    copy('tests/assets/' + file.name, 'tests/assets/' + file.name)
for name in ['brief', 'router', 'registry', 'providers/comfyui', 'providers/aseprite', 'pipelines/pixel_static', 'pipelines/pixel_animation', 'pipelines/nonpixel_image', 'pipelines/nonpixel_animation', 'pixel/analyzer', 'pixel/refiner', 'pixel/resolution', 'pixel/direct', 'pixel/recovery', 'motion/extractor', 'motion/keyframes', 'motion/alignment', 'motion/temporal', 'qa', 'manifests', 'cli']:
    directory = ROOT / 'src/assetpipe' / name
    directory.mkdir(parents=True, exist_ok=True)
    (directory / '__init__.py').write_text('', encoding='utf-8')
for name in ['schemas', 'tests/unit', 'tests/integration', 'tests/fixtures', 'examples', 'docs']:
    (ROOT / name).mkdir(parents=True, exist_ok=True)

# Extract the previously executed algorithm, retaining pixel arithmetic verbatim.
# Blue-tunic anchoring is a named, explicit profile, never a universal fallback.
source = OLD / 'workspace/runs/sword_warrior_001/phase13_step3_direct_walk/attempt_05/run_direct_pixelization.py'
text = source.read_text(encoding='utf-8')
imports = text[text.index('from __future__'):text.index('ROOT =')]
helpers = text[text.index('def sha256'):text.index('def main()')]
body = text[text.index('    selection =', text.index('def main()')):text.index('\n\nif __name__')]
body = body.replace('"sword_warrior_001"', 'asset_id')
body = body.replace('    if master.shape[:2] != (128, 128):\n        raise ValueError(f"Approved source master must be 128x128, got {master.shape[1]}x{master.shape[0]}")\n', '')
body = body.replace('    if len(exact_colors) != 32:\n        raise ValueError(f"Expected exact Static Master palette of 32 colors; found {len(exact_colors)}")\n', '    if not 1 <= len(exact_colors) <= 255:\n        raise ValueError("Direct profile requires 1-255 master colors")\n')
body += '\n    return alignment\n'
header = '''def run_direct(*, asset_id, static_master, source_video, source_frames, selection_path, output_dir, canvas=(160, 160), profile):
    if profile != "blue_tunic_white_matte_v1":
        raise ValueError("Only the verified blue_tunic_white_matte_v1 profile is available; supply an explicit compatible profile")
    ROOT = Path(output_dir).resolve()
    ROOT.mkdir(parents=True, exist_ok=False)
    STATIC_MASTER, SOURCE_VIDEO = Path(static_master), Path(source_video)
    SOURCE_FRAMES, SELECTION_PATH = Path(source_frames), Path(selection_path)
    MATTE_DIR, PIXEL_DIR, PREVIEW_DIR = ROOT / "030_matte_crops", ROOT / "040_direct_pixel_frames", ROOT / "060_preview"
    PALETTE_PATH, ALIGNMENT_PATH = ROOT / "static_master_exact_palette.json", ROOT / "alignment_report.json"
    CANVAS = tuple(canvas)
'''
target = ROOT / 'src/assetpipe/pixel/direct/ported.py'
target.write_text(imports + 'ALPHA_BACKGROUND_TOLERANCE = 60\nOUTPUT_FRAME_DURATION_MS = 125\nGIF_FRAME_DURATION_MS = 120\n\n' + helpers + header + body, encoding='utf-8')
records.append({'source': str(source), 'destination': str(target.relative_to(ROOT)), 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(), 'adaptation': 'Function parameters replace run-path globals; master canvas/color-count preconditions generalized; arithmetic unchanged; explicit verified profile required.'})
(ROOT / 'docs/migration_inventory.json').write_text(json.dumps({'legacy_head': None, 'legacy_head_reason': 'Repository has no commits; source hashes identify migration inputs.', 'files': records}, indent=2), encoding='utf-8')
