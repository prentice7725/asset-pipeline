"""Record measured v0.1 acceptance evidence. No production approvals are inferred."""
from pathlib import Path
import hashlib
import json
import sys
import subprocess
import yaml
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from assetpipe.manifests import now, write

root = Path(__file__).resolve().parents[1]
pixel_run = root / 'workspace/smokes/pixel_attempt_05'
nonpixel_run = root / 'workspace/smokes/nonpixel'
pixel = json.loads((pixel_run / 'run_manifest.json').read_text(encoding='utf-8'))
nonpixel = json.loads((nonpixel_run / 'run_manifest.json').read_text(encoding='utf-8'))
regression = json.loads((root / 'docs/pixel_regression.json').read_text(encoding='utf-8'))
document = json.loads((root / 'workspace/smokes/document_route.json').read_text(encoding='utf-8'))
assert pixel['status'] == 'EXPORT_READY_REVIEW_REQUIRED'
assert nonpixel['status'] == 'CANDIDATE_READY_REVIEW_REQUIRED'
assert regression['status'] == 'PASS'
assert document['selected_workflow'] == 'anima_base'
result = subprocess.run([str(root / '.venv/Scripts/python.exe'), '-m', 'pytest', '-q'], cwd=root, capture_output=True, text=True)
write(root / 'docs/test_report.json', {'command': '.venv/Scripts/python.exe -m pytest -q', 'exit_code': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr, 'timestamp': now()})
assert result.returncode == 0, result.stdout
inventory_path = root / 'docs/migration_inventory.json'
inventory = json.loads(inventory_path.read_text(encoding='utf-8'))
source_drift = []
for row in inventory['files']:
    source = (root / row['source']).resolve()
    current_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    if current_hash != row['source_sha256']:
        # Source registry is concurrently maintained outside this migration.
        # Algorithm drift still blocks completion; do not overwrite external changes.
        assert source == root.parent / 'pixel-pipeline/config/workflow_registry.yaml', source
        source_drift.append({'source': str(source), 'copied_snapshot_sha256': row['source_sha256'], 'current_sha256': current_hash, 'note': 'Registry changed outside migration; current installed workflow graphs independently verified. Legacy registry not overwritten.'})
    destination = root / row['destination']
    row['final_destination_sha256'] = hashlib.sha256(destination.read_bytes()).hexdigest()
inventory['test_adaptations'] = ['Changed package import paths', 'Excluded legacy character-orchestrator manifest attachment test; new run manifests have dedicated coverage', 'Copied generic palette fixture required by refiner regression']
inventory['direct_adaptations'] = ['Removed path-derived globals; explicit parameters', 'Preview helpers derive canvas from frames', 'Named verified profile; no implicit identity anchoring', 'Preserved FFmpeg RGB conversion after OpenCV migration defect', 'Preserved pixel arithmetic; eight frame RGBA regression exact']
inventory['ported_algorithm_source_hashes_unchanged'] = True
inventory['external_registry_changes_detected'] = source_drift
write(inventory_path, inventory)
preflight = json.loads((root / 'docs/provider_preflight.json').read_text(encoding='utf-8'))
assert all(row['status'] == 'PASS' for row in preflight['workflows'])
gates = {name: {'status': 'PASS', 'evidence': evidence} for name, evidence in {
    'Repository bootstrap': 'Editable install and assetpipe --help; Git initialized',
    'Workflow Registry': 'docs/provider_preflight.json; actual ComfyUI object_info model/node names',
    'Asset Brief schema': 'schemas/asset_brief.schema.json; validation tests',
    'Router': 'tests/unit/test_assetpipe.py; status/capability/tag/priority/rejection tests',
    'ComfyUI Provider': str(nonpixel_run / '010_generation/generation.json'),
    'Aseprite Provider': str(pixel_run / '040_aseprite/aseprite_report.json'),
    'PIXEL_STATIC wiring': 'tests/integration/test_static_wiring.py; existing candidate fixture, real Aseprite, resolution-review lock and failed-gate stop',
    'PIXEL_ANIMATION wiring': str(pixel_run / 'run_manifest.json'),
    'NONPIXEL_IMAGE wiring': str(nonpixel_run / 'run_manifest.json'),
    'Document to Asset Brief smoke': 'workspace/smokes/document_brief.json; workspace/smokes/document_route.json',
    'Pixel E2E smoke': 'docs/pixel_regression.json; eight exact legacy RGBA frames, Pixel Gate and actual Aseprite export',
    'Non-pixel E2E smoke': str(nonpixel_run / 'run_manifest.json'),
    'Tests': 'docs/test_report.json',
    'README': 'README.md',
}.items()}
write(root / 'docs/bootstrap_status.json', {'status': 'ASSET_PIPELINE_V0_1_BOOTSTRAP_PASS', 'completed_at': now(), 'gates': gates,
    'limitations': ['NONPIXEL_ANIMATION is SUPPORTED_EXPERIMENTAL contract only', 'Direct animation profile currently supports eight reviewed blue-tunic/white-background walk frames; no universal anchoring claim', 'Pixel animation v0.1 consumes existing reviewed motion; new motion-generation requests require prepared provider inputs and are not auto-dispatched', 'Static wiring uses an established fixture for gate/export validation; no additional pixel generation was run', 'Exports and generated images remain review-required, game_ready=false', 'No old run artifacts were imported; benchmark inputs reference the preserved legacy source', 'Legacy repository has no HEAD commit; migration records source file hashes'],
    'migration_defects_resolved': ['Preview helper canvas globals', 'OpenCV vs FFmpeg decode RGB mismatch'],
    'failed_attempts_preserved': ['workspace/smokes/pixel', 'workspace/smokes/pixel_attempt_02', 'workspace/smokes/pixel_attempt_03'],
    'stop_rule': 'v0.1 complete; no additional features added'})
print(result.stdout.strip())
print('ASSET_PIPELINE_V0_1_BOOTSTRAP_PASS')
