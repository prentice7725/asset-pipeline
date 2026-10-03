"""Offline research boundary. External text is data, never executable instructions."""
import copy
import hashlib
import json
import re
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from ..brief import validate
from ..prompts import from_brief, compile_spec, workflow_values
from ..registry import load_registry
from ..router import route
from ..styles import FIELDS, resolve_style, digest, style_digest

NAI = re.compile(r'[{}\[\]]|(?:[-+]?\d+(?:\.\d+)?)\s*::|::')
INSTRUCTION = re.compile(r'https?://|(?:ignore|override)\s+(?:all|previous|system)|\b(?:powershell|subprocess|curl|wget|exec|shell|api[_ -]?key|token)\b|(?:run|call|execute|read|write)\s+(?:a |the |any )?(?:tool|command|file|script)', re.I)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_candidates(root, path=None):
    root = Path(root).resolve()
    schema = json.loads((root / 'schemas/prompt-mining-candidate.schema.json').read_text(encoding='utf-8'))
    validator = Draft202012Validator(schema)
    sources = yaml.safe_load((root / 'research/prompt_mining/source_registry.yaml').read_text(encoding='utf-8'))['sources']
    path = Path(path) if path else root / 'research/prompt_mining/candidates.jsonl'
    rows, ids = [], set()
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        validator.validate(row)
        supporting = row['source']['supporting_source_ids']
        if any(key not in sources for key in supporting):
            raise ValueError('Unknown supporting source')
        if not any(all(row['source'][field] == sources[key][field] for field in ('url', 'author', 'origin')) for key in supporting):
            raise ValueError('Primary source provenance mismatch')
        if row['id'] in ids:
            raise ValueError('Duplicate candidate id: ' + row['id'])
        ids.add(row['id'])
        # M2.6 deliberately has no promotion/evidence-writing endpoint.
        if row['validation']['golden_approved'] or row['validation']['human_review'] != 'NOT_REVIEWED':
            raise ValueError('M2.6 candidate records cannot self-approve')
        if row['validation']['local_test_state'] != 'NOT_RUN' or row['validation']['pipeline_test_state'] != 'NOT_RUN':
            raise ValueError('Local claims require a future evidence-backed validation milestone')
        if not row['source']['source_model_version'] and row['source']['generation_metadata'] != 'MISSING':
            raise ValueError('Unknown model version must use MISSING metadata')
        rows.append(row)
    return rows


def safe_descriptors(values):
    if any(NAI.search(v) for v in values):
        raise ValueError('MODEL_DIALECT_MISMATCH: NovelAI emphasis is not portable')
    if any(INSTRUCTION.search(v) or any(ord(c) < 32 for c in v) for v in values):
        raise ValueError('UNTRUSTED_INSTRUCTION: descriptor contains executable or URL instructions')


def library(root):
    root = Path(root).resolve()
    recipes = {}
    for path in sorted((root / 'config/styles/recipes').glob('*.yaml')):
        data = yaml.safe_load(path.read_text(encoding='utf-8'))
        if data.get('schema_version') != 1:
            raise ValueError('Unsupported mining recipe version')
        for key, recipe in data.get('recipes', {}).items():
            if key in recipes:
                raise ValueError('Duplicate mining recipe id: ' + key)
            if recipe.get('state') != 'NORMALIZED' or recipe.get('offline_only') is not True:
                raise ValueError('Mining recipes must remain offline NORMALIZED candidates')
            if recipe.get('approved_for') or recipe.get('production_state') != 'NOT_RUN':
                raise ValueError('Mining recipes cannot claim production approval')
            safe_descriptors(recipe.get('tags', []) + recipe.get('phrases', []))
            recipes[key] = {**recipe, 'recipe_file': path.relative_to(root).as_posix()}
    return recipes


def compile_candidate(root, candidate_id, brief, workflow_id, *, candidates=None):
    root = Path(root).resolve()
    validate(brief)
    candidates = candidates if candidates is not None else load_candidates(root)
    candidate = next((r for r in candidates if r['id'] == candidate_id), None)
    if candidate is None:
        raise ValueError('Unknown candidate id: ' + candidate_id)
    if candidate['compatibility']['portability'] != 'CANDIDATE' or candidate['compatibility']['blockers']:
        raise ValueError('Candidate portability is blocked')
    if not candidate['style']['subject_independent']:
        raise ValueError('Subject-dependent source cannot supply style canon')
    if brief['source']['type'] == 'DOCUMENTS' and not brief['identity']['canonical_traits']:
        raise ValueError('Source-backed canonical traits are required; UNSPECIFIED facts cannot be inferred')
    registry = load_registry(root)
    if workflow_id not in registry:
        raise ValueError('Unregistered workflow: ' + workflow_id)
    workflow = registry[workflow_id]
    if workflow.get('engine', 'comfyui') != 'comfyui':
        raise ValueError('External CLI experiments require a separate explicit budget; offline local recipes only')
    if brief['output_class'] not in {'PIXEL_STATIC', 'NONPIXEL_IMAGE'}:
        raise ValueError('NOT_SUPPORTED: mining does not verify animations, UI export or tile integration')
    selected = copy.deepcopy(brief)
    if selected.get('style_id') not in (None, candidate['style']['id']):
        raise ValueError('Brief style_id conflicts with candidate')
    # Reuse M2 project precedence/locks even for offline pixel intent.
    intent = {**selected, 'style_id': candidate['style']['id'], 'output_class': 'NONPIXEL_IMAGE'}
    style = resolve_style(intent, root)
    recipes = [r for r in library(root).values() if r['style_id'] == style['style_id'] and r['workflow_id'] == workflow_id]
    if len(recipes) != 1:
        raise ValueError('No unique compatible offline recipe')
    recipe = recipes[0]
    if recipe['style_sha256'] != style['style_sha256']:
        raise ValueError('Recipe no longer matches project/catalog style definition')
    if recipe['candidate_id'] != candidate_id:
        raise ValueError('Candidate/recipe binding mismatch')
    if recipe['output_class'] != brief['output_class']:
        raise ValueError('Recipe/output class mismatch')
    actual = workflow.get('models', {})
    if recipe['required_models'] != {k: v for k, v in actual.items() if k != 'loras'} or recipe['required_loras'] != actual.get('loras', []):
        raise ValueError('MODEL_DEPENDENCY_MISMATCH: no downloads or substitutions attempted')
    selected.pop('style_id', None)  # Style is merged as data into the existing PromptSpec compiler.
    preferences = selected['workflow_preferences']
    if preferences.get('id') not in (None, workflow_id) or preferences.get('model_profile') not in (None, workflow.get('model_profile')):
        raise ValueError('Explicit model/workflow conflict')
    preferences['id'] = workflow_id
    decision = route(selected, dict(registry))  # Existing capability gate; no model dispatch.
    definition = style['definition']
    descriptors = [v for field in FIELDS for v in definition[field]] + recipe['phrases']
    safe_descriptors(descriptors + definition['forbidden_elements'])
    spec = from_brief(selected)
    # Reject foreign weighting syntax rather than silently changing canonical text.
    texts = [spec['subject'], *[v for k in ('appearance', 'style', 'constraints', 'negative') for v in spec.get(k, [])]]
    safe_descriptors(texts)
    spec['style'] = list(dict.fromkeys(spec.get('style', []) + descriptors))
    spec['negative'] = list(dict.fromkeys(spec.get('negative', []) + definition['forbidden_elements']))
    if recipe['tags']:
        if workflow.get('model_profile') not in {'anima-base', 'anima-tomohi', 'anima-pixel'}:
            raise ValueError('Foreign model tags cannot pass to natural-language adapters')
        spec['style'] += [tag.lower().replace('_', ' ') for tag in recipe['tags']]
    result = compile_spec(selected, workflow, root, spec, preserve_case=True, style_context=style)
    result['workflow_inputs'] = workflow_values(result, workflow, selected)
    result['mining'] = {'candidate_id': candidate_id, 'candidate_sha256': digest(candidate),
        'style_id': style['style_id'], 'style_sha256': style['style_sha256'], 'style_source': style['selection_source'],
        'recipe_id': next(k for k, v in library(root).items() if v == recipe), 'recipe_version': recipe['version'],
        'recipe_file': recipe['recipe_file'], 'recipe_sha256': digest(recipe), 'workflow_id': workflow_id,
        'workflow_sha256': workflow['hash'], 'model_variant': recipe['model_variant'],
        'source': candidate['source'], 'state': 'NORMALIZED', 'local_test_state': 'NOT_RUN',
        'pipeline_test_state': 'NOT_RUN', 'human_review': 'NOT_REVIEWED', 'golden_approved': False,
        'game_ready': False, 'generation_requests': 0, 'route': decision,
        'source_reproduction': 'NOT_CLAIMED', 'model_hash_status': 'NOT_VERIFIED'}
    return result


def normalize_civitai(items, versions):
    """Normalize saved public API responses; no network, image fetch or raw-prompt storage."""
    accepted, excluded, seen = [], [], set()
    for item in items:
        if not isinstance(item, dict):
            excluded.append({'image_id': None, 'reasons': ['INVALID_IMAGE_RECORD']})
            continue
        blockers = []
        image_id = item.get('id')
        if type(image_id) is not int or image_id <= 0:
            excluded.append({'image_id': image_id, 'reasons': ['INVALID_IMAGE_ID']})
            continue
        if item.get('nsfw') is not False or item.get('nsfwLevel') not in ('None', None) or item.get('browsingLevel', 1) != 1:
            excluded.append({'image_id': image_id, 'reasons': ['SFW_NOT_CONFIRMED']})
            continue
        meta = item.get('meta')
        if not isinstance(meta, dict) or not isinstance(meta.get('prompt'), str) or not meta['prompt'].strip():
            excluded.append({'image_id': image_id, 'reasons': ['METADATA_MISSING']})
            continue
        prompt = meta['prompt']
        if INSTRUCTION.search(prompt):
            blockers.append('UNTRUSTED_INSTRUCTION')
        if NAI.search(prompt):
            blockers.append('FOREIGN_WEIGHTING_SYNTAX_REVIEW_REQUIRED')
        resources = meta.get('civitaiResources')
        ids = item.get('modelVersionIds')
        if not isinstance(resources, list) or not resources or not isinstance(ids, list) or any(type(i) is not int or i <= 0 for i in ids):
            excluded.append({'image_id': image_id, 'reasons': ['RESOURCE_METADATA_MISSING'] + blockers})
            continue
        graph = []
        checkpoints = 0
        for resource in resources:
            if not isinstance(resource, dict):
                blockers.append('INVALID_RESOURCE')
                continue
            version_id = resource.get('modelVersionId')
            kind = resource.get('type')
            version = versions.get(str(version_id))
            if type(version_id) is not int or version_id <= 0 or version_id not in ids:
                blockers.append('RESOURCE_VERSION_MISMATCH')
                continue
            if not isinstance(version, dict) or version.get('id') != version_id or type(version.get('modelId')) is not int or version['modelId'] <= 0:
                blockers.append('MODEL_VERSION_UNRESOLVED')
                continue
            model = version.get('model', {})
            if not isinstance(model, dict):
                blockers.append('INVALID_MODEL_METADATA')
                continue
            version_kind = model.get('type', version.get('type', ''))
            if kind not in {'checkpoint', 'lora'} or not isinstance(version_kind, str) or version_kind.lower() != kind:
                blockers.append('RESOURCE_TYPE_MISMATCH')
                continue
            if not isinstance(version.get('baseModel'), str) or version['baseModel'] != item.get('baseModel'):
                blockers.append('FOREIGN_MODEL_RESOURCE')
            if version.get('availability') not in (None, 'Public'):
                blockers.append('RESOURCE_NOT_PUBLIC')
            if model.get('id', version['modelId']) != version['modelId']:
                blockers.append('MODEL_ID_MISMATCH')
            if kind == 'checkpoint':
                checkpoints += 1
            files = version.get('files', [])
            if not isinstance(files, list):
                files = []
            hashes = set()
            for file in files:
                metadata = file.get('hashes') if isinstance(file, dict) else None
                value = metadata.get('SHA256') if isinstance(metadata, dict) else None
                if isinstance(value, str):
                    hashes.add(value.lower())
            hashes = sorted(hashes)
            hashes = [h for h in hashes if re.fullmatch('[0-9a-f]{64}', h)]
            if not hashes:
                blockers.append('MODEL_HASH_MISSING')
            graph.append({'model_id': version['modelId'], 'version_id': version_id, 'type': kind,
                'base_model': version.get('baseModel'), 'model_hashes': hashes,
                'weight': resource.get('weight'), 'license_review': 'REVIEW_REQUIRED'})
        if set(ids) != {r['version_id'] for r in graph}:
            blockers.append('RESOURCE_GRAPH_INCOMPLETE')
        if checkpoints != 1:
            blockers.append('CHECKPOINT_NOT_UNIQUE')
        if blockers:
            excluded.append({'image_id': image_id, 'reasons': sorted(set(blockers))})
            continue
        fingerprint = digest({'prompt': ' '.join(prompt.split()), 'resources': sorted(graph, key=lambda r: (r['version_id'], r['type']))})
        if fingerprint in seen:
            excluded.append({'image_id': image_id, 'reasons': ['DUPLICATE_PROMPT_AND_RESOURCE_VERSIONS']})
            continue
        seen.add(fingerprint)
        accepted.append({'image_id': image_id, 'source_url': f'https://civitai.com/images/{image_id}',
            'author': item.get('username') if isinstance(item.get('username'), str) else None,
            'source_model_family': item.get('baseModel'), 'metadata_state': 'VERIFIED_IMAGE_META',
            'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest(), 'dedup_sha256': fingerprint,
            'dependencies': graph, 'rights_review': 'REVIEW_REQUIRED', 'research_state': 'DISCOVERED',
            'local_test_state': 'NOT_RUN', 'golden_approved': False})
    return {'accepted': accepted, 'excluded': excluded, 'raw_prompts_stored': False, 'images_downloaded': 0}
