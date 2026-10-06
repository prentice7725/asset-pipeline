"""Shared, file-backed style resolution; knowledge is never an approval."""
import copy
import hashlib
import json
from pathlib import Path

import yaml

from .contracts import load_style_contract, validate_style_contract

STATES = {'UNTESTED', 'TESTED', 'APPROVED', 'REJECTED'}
FIELDS = ('expression', 'colors', 'linework', 'shading', 'texture')


def read(path):
    try:
        value = yaml.safe_load(Path(path).read_text(encoding='utf-8'))
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f'Style file unavailable or invalid: {path}: {exc}') from exc
    if not isinstance(value, dict):
        raise ValueError(f'Style file must be a mapping: {path}')
    return value


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def style_digest(style):
    # Approval/definition revisions invalidate earlier automatic-use evidence too.
    return digest(style)


def approval(item):
    record = item.get('human_approval', {})
    if not isinstance(record, dict) or record.get('approved') is not True or not all(
        isinstance(record.get(k), str) and record[k].strip() for k in ('reviewed_by', 'reason', 'reviewed_at')
    ):
        raise ValueError('APPROVED requires an explicit human_approval record')


def evidence(item, root, style_id, workflow_id):
    try:
        return _evidence(item, root, style_id, workflow_id)
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError('Style generation evidence unavailable or invalid: ' + str(exc)) from exc


def _evidence(item, root, style_id, workflow_id):
    relative = item.get('evidence')
    if not isinstance(relative, str):
        raise ValueError('TESTED/APPROVED recipe requires real-generation evidence')
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError('Style evidence must stay within repository root')
    record = json.loads(path.read_text(encoding='utf-8'))
    if (record.get('result') != 'STYLE_COMBINATION_TESTED' or record.get('style_id') != style_id
            or record.get('workflow_id') != workflow_id or record.get('recipe_version') != item['version']
            or record.get('style_sha256') != item['style_sha256']):
        raise ValueError('Style evidence identity/version mismatch')
    manifest_path = (root / record['run_manifest']).resolve()
    if not manifest_path.is_relative_to(root):
        raise ValueError('Style manifest must stay within repository root')
    raw = manifest_path.read_bytes()
    manifest = json.loads(raw)
    if hashlib.sha256(raw).hexdigest() != record.get('run_manifest_sha256'):
        raise ValueError('Style manifest hash mismatch')
    if (manifest.get('workflow', {}).get('id') != workflow_id
            or manifest.get('status') != 'CANDIDATE_READY_REVIEW_REQUIRED'
            or manifest.get('style_selection', {}).get('style_id') != style_id
            or manifest.get('style_selection', {}).get('recipe_version') != item['version']
            or manifest.get('style_selection', {}).get('style_sha256') != item['style_sha256']
            or not manifest.get('qa_results') or any(r['status'] != 'PASS' for r in manifest['qa_results'])):
        raise ValueError('Style evidence requires a completed generation and passing QA')
    # State/approval/evidence metadata can change after a comparison, but prompt
    # recipe content must still match the exact recipe recorded by that run.
    recorded_hash = manifest['style_selection'].get('recipe_sha256')
    revisions = [item]
    for state in ('UNTESTED', 'TESTED'):
        previous = {k: v for k, v in item.items() if k != 'human_approval'}
        previous['status'] = state
        revisions.append(previous)
        revisions.append({k: v for k, v in previous.items() if k != 'evidence'})
    if recorded_hash not in {digest(revision) for revision in revisions}:
        raise ValueError('Style recipe content differs from real-generation evidence')
    outputs = record.get('outputs', [])
    if not outputs:
        raise ValueError('Style evidence requires generated outputs')
    for output in outputs:
        file = (root / output['path']).resolve()
        if (not file.is_relative_to(root) or str(file) not in manifest.get('outputs', [])
                or hashlib.sha256(file.read_bytes()).hexdigest() != output['sha256']):
            raise ValueError('Style output hash mismatch')
    return relative


def validate_style(style, style_id=None):
    if style.get('status') not in STATES or not isinstance(style.get('version'), str):
        raise ValueError('Style requires version and validation status')
    for field in (*FIELDS, 'forbidden_elements', 'required_capabilities', 'sources'):
        if not isinstance(style.get(field), list):
            raise ValueError('Style requires a list: ' + field)
    for field in (*FIELDS, 'forbidden_elements', 'required_capabilities'):
        if any(not isinstance(v, str) or not v.strip() for v in style[field]):
            raise ValueError('Style descriptors must be nonempty strings')
    for source in style['sources']:
        if not isinstance(source, dict) or not all(isinstance(source.get(k), str) and source[k] for k in ('url', 'description')):
            raise ValueError('Style source requires url and description')
    if 'style_contract' in style:
        validate_style_contract(style['style_contract'], style_id)
    if style['status'] == 'APPROVED':
        approval(style)


def resolve_style(brief, root):
    if brief['output_class'] != 'NONPIXEL_IMAGE':
        if brief.get('style_id'):
            raise ValueError('Style Intelligence currently supports NONPIXEL_IMAGE only')
        return None  # Project nonpixel defaults must not alter PIXEL/SFX routes.
    root = Path(root).resolve()
    catalog_path = root / 'config/styles/catalog.yaml'
    project = root / 'config/styles/projects' / brief.get('project_id', 'default')
    sot_path, pack_path = project / 'visual_sot.yaml', project / 'style_pack.yaml'
    sot = read(sot_path) if sot_path.exists() else {}
    pack = read(pack_path) if pack_path.exists() else {}
    if pack:
        if pack.get('status') != 'APPROVED':
            raise ValueError('Project Style Pack must be APPROVED')
        approval(pack)
    requested = brief.get('style_id')
    locked = sot.get('style_id')
    if locked and requested and locked != requested:
        raise ValueError(f'Project Visual SOT style lock conflicts with style_id: {locked}')
    chosen = locked or requested or pack.get('default_style_id')
    if locked and (not isinstance(sot.get('source'), str) or not sot['source'].strip()):
        raise ValueError('Visual SOT requires the project source location')
    if not chosen:
        return None  # Preserve all legacy routes and model defaults.
    if brief['output_class'] != 'NONPIXEL_IMAGE':
        raise ValueError('Style Intelligence currently supports NONPIXEL_IMAGE only')
    catalog = read(catalog_path)
    styles = catalog.get('styles', {})
    pack_styles = pack.get('styles', {})
    source = 'PROJECT_VISUAL_SOT' if locked else 'PROJECT_STYLE_PACK' if chosen in pack_styles or (not requested and pack.get('default_style_id')) else 'COMMON_STYLE_CATALOG'
    style = copy.deepcopy(sot.get('style') if locked and sot.get('style') else pack_styles.get(chosen, styles.get(chosen)))
    if not isinstance(style, dict):
        raise ValueError('Unknown style_id: ' + str(chosen))
    validate_style(style, chosen)
    if style['status'] == 'REJECTED':
        raise ValueError('REJECTED style: ' + chosen)
    selection_path = sot_path if source == 'PROJECT_VISUAL_SOT' else pack_path if source == 'PROJECT_STYLE_PACK' else catalog_path
    return {'style_id': chosen, 'selection_source': source, 'selection_file': selection_path.relative_to(root).as_posix(),
            'style_version': style['version'], 'style_sha256': style_digest(style), 'style_status': style['status'],
            'sources': style['sources'], 'definition': style, 'locked': bool(locked),
            '_project_recipes': pack.get('recipes', {}), '_pack_file': pack_path.relative_to(root).as_posix()}


def select_recipe(selection, workflow, root, explicit=False):
    if selection is None:
        return None
    root = Path(root).resolve()
    data = read(root / 'config/styles/model_recipes.yaml')
    local = selection.get('_project_recipes', {}).get(selection['style_id'], {}).get(workflow['id'])
    recipe = local if local is not None else data.get('recipes', {}).get(selection['style_id'], {}).get(workflow['id'])
    if not isinstance(recipe, dict):
        raise ValueError('No style-compatible recipe for ' + workflow['id'])
    if recipe.get('status') not in STATES or not isinstance(recipe.get('version'), str):
        raise ValueError('Recipe requires version and validation status')
    if recipe['status'] == 'REJECTED':
        raise ValueError('REJECTED style/model combination')
    if recipe.get('style_sha256') != selection['style_sha256']:
        raise ValueError('Recipe style fingerprint mismatch')
    if recipe.get('model_profile') != workflow.get('model_profile'):
        raise ValueError('Recipe model profile mismatch')
    if recipe['status'] in {'TESTED', 'APPROVED'}:
        evidence(recipe, root, selection['style_id'], workflow['id'])
    if recipe['status'] == 'APPROVED':
        approval(recipe)
    if not explicit and (recipe['status'] != 'APPROVED' or selection['style_status'] != 'APPROVED'):
        raise ValueError('Automatic style routing requires human APPROVED style and recipe; select a workflow explicitly for comparison')
    style = selection['definition']
    required = set(style['required_capabilities']) | set(recipe.get('required_capabilities', []))
    contract_forbids = style.get('style_contract', {}).get('forbidden_style_features', [])
    contract_native = contract_forbids and not (workflow['id'] == 'krea2_base' and recipe.get('exclusion_mode') == 'POSITIVE_TEXT_INSTRUCTION')
    if style['forbidden_elements'] or recipe.get('negative', []) or contract_native:
        required.add('negative_prompt')
    from ..router import satisfied
    missing = [cap for cap in sorted(required) if not satisfied(workflow['capabilities'], cap)]
    if missing:
        raise ValueError('Style requires unavailable capabilities: ' + ', '.join(missing))
    for field in ('positive', 'negative'):
        if not isinstance(recipe.get(field), list) or any(not isinstance(v, str) for v in recipe[field]):
            raise ValueError('Recipe prompt fields must be string lists')
    return {**{k: v for k, v in selection.items() if k != 'definition' and not k.startswith('_')}, 'recipe_version': recipe['version'],
            'recipe_status': recipe['status'], 'recipe_sha256': digest(recipe), 'workflow_id': workflow['id'],
            'recipe_sources': recipe.get('sources', []), 'evidence': recipe.get('evidence'),
            'recipe_file': selection['_pack_file'] if local is not None else 'config/styles/model_recipes.yaml',
            'reason': 'explicit compatible workflow' if explicit else 'human-approved compatible style/model combination',
            'definition': style, 'recipe': copy.deepcopy(recipe)}


def public_selection(selection):
    return {k: v for k, v in selection.items() if k not in {'definition', 'recipe'}} if selection else None


def apply_style(spec, selection):
    if not selection:
        return spec
    spec = copy.deepcopy(spec)
    style, recipe = selection['definition'], selection['recipe']
    if 'style_contract' in style:
        if recipe['positive'] or recipe['negative']:
            raise ValueError('STYLE_CONTRACT_CONFLICT: contract recipes cannot add unstructured style strings')
        contract_id = style['style_contract']['id']
        if spec.get('style_contract_id') not in (None, contract_id):
            raise ValueError('STYLE_CONTRACT_CONFLICT: PromptSpec and selected style disagree')
        if spec.get('style') or spec.get('styleSources'):
            raise ValueError('STYLE_CONTRACT_CONFLICT: free-text style cannot be mixed with a structured contract')
        spec['style_contract_id'] = contract_id
        return spec
    descriptors = [v for field in FIELDS for v in style[field]] + recipe['positive']
    spec['style'] = list(dict.fromkeys(spec.get('style', []) + descriptors))
    spec['negative'] = list(dict.fromkeys(spec.get('negative', []) + style['forbidden_elements'] + recipe['negative']))
    # Source descriptions are provenance, not extra visual instructions.
    return spec
