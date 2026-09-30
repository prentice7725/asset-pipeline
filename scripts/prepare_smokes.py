from pathlib import Path
import json
import shutil
import sys
import yaml
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from assetpipe.brief import make, SCHEMA
from assetpipe.manifests import write
from assetpipe._ported.comfy_bridge.client import ComfyClient
from assetpipe._ported.aseprite_bridge.runner import find_aseprite, get_version

root = Path(__file__).resolve().parents[1]
legacy = root.parent / 'pixel-pipeline'
write(root / 'schemas/asset_brief.schema.json', SCHEMA)
# Use the checked-in bootstrap directive; no private attachment is required.
doc = root / 'tests/fixtures/character_test.md'
doc.write_text('# Scout fixture\n\n- fantasy scout\n- short brown hair\n- blue cloak\n- light armor\n- dagger\n- no heavy armor\n', encoding='utf-8')
brief = make(asset_id='scout_document_fixture', output_class='NONPIXEL_IMAGE', prompt='fantasy scout, short brown hair, blue cloak, light armor, dagger')
brief['source'] = {'type': 'DOCUMENTS', 'paths': ['../tests/fixtures/character_test.md'], 'references': []}
brief['identity']['canonical_traits'] = ['fantasy scout', 'short brown hair', 'blue cloak', 'light armor', 'dagger']
brief['forbidden_elements'] = ['heavy armor']
brief['source_notes'] = [{'classification': 'EXPLICIT', 'text': line, 'source': str(doc)} for line in brief['identity']['canonical_traits'] + ['no heavy armor']]
brief['workflow_preferences'] = {'id': 'anima_base', 'tags': ['character', 'fantasy']}
brief['unspecified_elements'] = ['face details', 'resolution', 'palette', 'silhouette']
(root / 'examples/character_test_brief.yaml').write_text(yaml.safe_dump(brief, sort_keys=False), encoding='utf-8')
brief = make(asset_id='sword_warrior_benchmark', output_class='PIXEL_ANIMATION', reference=legacy / 'workspace/runs/sword_warrior_001/phase13_static_master/approved/static_master_export.png', action='walk')
brief['constraints']['resolution'] = [160, 160]
brief['animation']['frame_target'] = 8
brief['production'] = {
    'static_master': str(legacy / 'workspace/runs/sword_warrior_001/phase13_static_master/approved/static_master_export.png'),
    'approval_record': str(legacy / 'workspace/runs/sword_warrior_001/phase13_static_master/approved/approval_record.json'),
    'motion_reference': str(legacy / 'workspace/runs/sword_warrior_001/phase13_walk_reference/attempt_02/010_generation/001_minimax_h3_walk_00002.mp4'),
    'selection': str(legacy / 'workspace/runs/sword_warrior_001/phase13_step3_direct_walk/attempt_05/semantic_frame_selection.json'),
    'direct_profile': 'blue_tunic_white_matte_v1',
}
(root / 'examples/pixel_animation_smoke.yaml').write_text(yaml.safe_dump(brief, sort_keys=False), encoding='utf-8')
registry_path = root / 'config/workflow_registry.yaml'
registry = yaml.safe_load(registry_path.read_text(encoding='utf-8'))
registry['workflows'] = {k: v for k, v in registry['workflows'].items() if k != 'krea2_darkbrush'}
# Experimental nonpixel animation is contract-only, never an automatically selected generator.
registry['workflows']['nonpixel_motion_contract'] = {
    'output_class': 'NONPIXEL_ANIMATION', 'engine': 'comfyui', 'workflow_file': 'config/workflows/deno_minimax_h3_r2v_8step.json',
    'workflow_name': 'deno_minimax_h3_r2v_8step', 'status': 'EXPERIMENTAL', 'priority': 0, 'tags': ['character', 'animation'],
    'models': registry['workflows']['minimax_character_motion_reference']['models'],
    'capabilities': {'character_reference': True, 'text_to_image': False}, 'support': 'SUPPORTED_EXPERIMENTAL',
}
client = ComfyClient('http://127.0.0.1:8188')
stats = client.check_connection()
objects = json.loads(client._request('/object_info'))
checks = []
for key, item in registry['workflows'].items():
    graph = json.loads((root / item['workflow_file']).read_text(encoding='utf-8'))['api_prompt']
    missing = []
    for node in graph.values():
        info = objects.get(node['class_type'])
        if info is None:
            missing.append('node:' + node['class_type'])
            continue
        definitions = {**info.get('input', {}).get('required', {}), **info.get('input', {}).get('optional', {})}
        for name, value in node['inputs'].items():
            spec = definitions.get(name)
            if isinstance(value, str) and name.endswith(('_name', '_file')) and spec and isinstance(spec[0], list) and value not in spec[0]:
                missing.append(name + ':' + value)
    checks.append({'workflow': key, 'status': 'PASS' if not missing else 'FAIL', 'missing': missing})
    if missing and item['status'] == 'ACTIVE':
        item['status'] = 'REJECTED'
    item['installation_check'] = {'status': 'PASS' if not missing else 'FAIL', 'missing': missing}
registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding='utf-8')
aseprite = find_aseprite()
write(root / 'docs/provider_preflight.json', {'comfyui': stats['system']['comfyui_version'], 'aseprite': get_version(aseprite), 'aseprite_path': str(aseprite.path), 'workflows': checks})
print(json.dumps(checks, indent=2))
