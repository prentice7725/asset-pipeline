"""M2.6 offline audit plus read-only local inventory. Generation requests: zero."""
import copy
import json
import difflib
from pathlib import Path
from datetime import datetime, timezone

import yaml
from assetpipe.brief import load
from assetpipe.prompt_mining import load_candidates, library, compile_candidate, sha256
from assetpipe.registry import load_registry
from assetpipe._ported.config import load_config
from assetpipe._ported.comfy_bridge.client import ComfyClient
from assetpipe.manifests import write

ROOT = Path(__file__).resolve().parents[1]


def main():
    candidates = load_candidates(ROOT)
    recipes = library(ROOT)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output = ROOT / 'workspace/style_lab/m26' / stamp
    output.mkdir(parents=True)
    config = load_config(ROOT / 'config/pipeline.yaml')
    client = ComfyClient(config.section('comfyui')['base_url'], request_timeout=2)
    inventory = {'status': 'NOT_RUN', 'model_hash_status': 'NOT_VERIFIED', 'folders': {}}
    try:
        stats = client.check_connection()
        inventory['version'] = stats.get('system', {}).get('comfyui_version')
        for folder in ('diffusion_models', 'text_encoders', 'vae', 'loras'):
            inventory['folders'][folder] = client.list_models(folder)
        inventory['status'] = 'LIVE_FILENAME_INVENTORY_ONLY'
    except Exception as exc:
        inventory['status'] = 'UNAVAILABLE'
        inventory['reason'] = str(exc)
    rows = []
    for recipe_id, recipe in recipes.items():
        for category in ('character', 'prop', 'environment'):
            value = load(ROOT / f'examples/prompt_mining/{category}.yaml')
            if recipe['output_class'] == 'PIXEL_STATIC':
                value['output_class'] = 'PIXEL_STATIC'
                # Logical pixel size is unspecified until project review, not inferred from 768.
                value['constraints']['resolution'] = None
            row = {'recipe_id': recipe_id, 'category': category, 'output_class': value['output_class'],
                'local_test_state': 'NOT_RUN', 'pipeline_test_state': 'NOT_RUN', 'game_ready': False}
            write(output / recipe_id / f'{category}_brief.json', value)
            try:
                result = compile_candidate(ROOT, recipe['candidate_id'], value, recipe['workflow_id'])
                write(output / recipe_id / f'{category}_compiled.json', result)
                row['status'] = 'OFFLINE_COMPILED'
                row['compiled_sha256'] = sha256(output / recipe_id / f'{category}_compiled.json')
                canon = value['identity']['canonical_traits'] + value['identity']['visual_traits']
                checks = [trait in result['positive'] for trait in canon]
                if value['constraints']['silhouette']:
                    checks += [value['constraints']['silhouette'] in result['positive']]
                checks += [trait in result['negative'] for trait in value['forbidden_elements']]
                if not all(checks):
                    raise ValueError('Canonical trait preservation failed')
                row['canon_preserved'] = True
            except Exception as exc:
                row['status'] = 'BLOCKED'
                row['reason'] = str(exc)
            dependency_missing = [f'{folder}/{name}' for folder, names in recipe['required_models'].items()
                for name in names if name not in inventory['folders'].get(folder, [])]
            dependency_missing += [f'loras/{name}' for name in recipe['required_loras'] if name not in inventory['folders'].get('loras', [])]
            row['local_installation'] = 'UNAVAILABLE' if inventory['status']=='UNAVAILABLE' else 'MISSING_FILES' if dependency_missing else 'FILENAMES_PRESENT_HASHES_UNVERIFIED'
            row['missing_files'] = dependency_missing
            rows.append(row)
    registry = load_registry(ROOT)
    for candidate in candidates:
        style = candidate['style']['id']
        for category in ('character', 'prop', 'environment'):
            pair = [r for r in rows if r['category'] == category and r['status'] == 'OFFLINE_COMPILED' and recipes[r['recipe_id']]['style_id'] == style and recipes[r['recipe_id']]['workflow_id'] in ('anima_base', 'krea2_base')]
            if len(pair) == 2:
                texts = [(output / r['recipe_id'] / f'{category}_compiled.json').read_text(encoding='utf-8').splitlines(True) for r in pair]
                target = output / 'prompt_diffs' / f'{style}_{category}.diff'
                target.parent.mkdir(exist_ok=True)
                target.write_text(''.join(difflib.unified_diff(*texts, fromfile=pair[0]['recipe_id'], tofile=pair[1]['recipe_id'])), encoding='utf-8')
    m1 = {}
    for id in ('codex_imagegen', 'grok_imagine'):
        file = ROOT / f'workspace/m1_e2e/{id}_evidence.json'
        m1[id] = {'workflow_status': registry[id]['status'], 'evidence_state': 'NOT_AVAILABLE'}
        if file.exists():
            data = json.loads(file.read_text(encoding='utf-8'))
            m1[id].update(evidence_state=data['result'], evidence_sha256=sha256(file), checked_at=data['checked_at'])
    summary = {'status': 'M26_OFFLINE_CANDIDATES_READY_M25_NOT_RUN', 'source_candidates': len(candidates),
        'recipes': len(recipes), 'source_registry_sha256': sha256(ROOT / 'research/prompt_mining/source_registry.yaml'),
        'offline_compiled': sum(r['status']=='OFFLINE_COMPILED' for r in rows),
        'blocked': sum(r['status']=='BLOCKED' for r in rows), 'matrix': rows, 'inventory': inventory,
        'new_generation_requests': 0, 'golden_approved': 0, 'human_review': 'NOT_REVIEWED',
        'm25_state': 'NOT_IMPLEMENTED_NOT_RUN', 'm1_existing_evidence': m1,
        'pixel_regression_record_sha256': sha256(ROOT / 'docs/pixel_regression.json'),
        'pipeline_evidence': 'NO_NEW_RUN_MANIFESTS; previous fixture evidence retained separately',
        'unsupported': ['generalized_animation','tile_seamlessness','ui_game_export'],
        'insufficient_evidence': [r['style']['id'] for r in candidates if r['compatibility']['evidence_coverage']=='INSUFFICIENT_EVIDENCE']}
    write(output / 'report.json', summary)
    write(ROOT / 'workspace/style_lab/m26/latest.json', {'report': str((output / 'report.json').relative_to(ROOT))})
    write(ROOT / 'docs/style/M26_STATUS.json', {**summary, 'artifact_root': output.relative_to(ROOT).as_posix()})
    print(json.dumps({k:v for k,v in summary.items() if k not in {'matrix','inventory'}},ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
