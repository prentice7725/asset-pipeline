"""Structured, model-neutral Style Contracts and explicit model-dialect compilation."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import yaml

CONTRACT_FIELDS = (
    'medium', 'palette', 'linework', 'shading', 'lighting', 'background',
    'texture', 'value_structure',
)
FEATURE_CODE = re.compile(r'^[A-Z][A-Z0-9_]{2,79}$')


def contract_digest(contract: dict) -> str:
    return hashlib.sha256(json.dumps(contract, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def validate_style_contract(contract: dict, expected_id: str | None = None) -> dict:
    required = {
        'id', 'version', *CONTRACT_FIELDS, 'required_style_features',
        'forbidden_style_features', 'priority', 'source', 'evidence',
    }
    if not isinstance(contract, dict) or set(contract) != required:
        raise ValueError('STYLE_CONTRACT_SCHEMA_INVALID: required fields or properties differ')
    if not isinstance(contract['id'], str) or not FEATURE_CODE.fullmatch(contract['id'].replace('-', '_')):
        raise ValueError('STYLE_CONTRACT_ID_INVALID')
    if expected_id and contract['id'] != expected_id:
        raise ValueError('STYLE_CONTRACT_ID_MISMATCH')
    if not isinstance(contract['version'], str) or not contract['version'].strip():
        raise ValueError('STYLE_CONTRACT_VERSION_INVALID')
    if type(contract['priority']) is not int or not 1 <= contract['priority'] <= 100:
        raise ValueError('STYLE_CONTRACT_PRIORITY_INVALID')
    for field in CONTRACT_FIELDS:
        value = contract[field]
        if (not isinstance(value, list) or not value
                or any(not isinstance(item, str) or not item.strip() for item in value)):
            raise ValueError('STYLE_CONTRACT_FIELD_INVALID: ' + field)
    codes = []
    for field in ('required_style_features', 'forbidden_style_features'):
        features = contract[field]
        if not isinstance(features, list) or not features:
            raise ValueError('STYLE_CONTRACT_FEATURES_INVALID: ' + field)
        for feature in features:
            if (not isinstance(feature, dict) or set(feature) != {'code', 'text'}
                    or not isinstance(feature['code'], str)
                    or not FEATURE_CODE.fullmatch(feature['code'])
                    or not isinstance(feature['text'], str) or not feature['text'].strip()):
                raise ValueError('STYLE_CONTRACT_FEATURE_INVALID: ' + field)
            codes.append(feature['code'])
    if len(codes) != len(set(codes)):
        raise ValueError('STYLE_CONTRACT_FEATURE_CODE_DUPLICATE')
    source = contract['source']
    source_fields = {'provider', 'entry_id', 'revision', 'card_url', 'preview_url', 'catalog_path'}
    if (not isinstance(source, dict) or set(source) != source_fields
            or source['provider'] != 'KREA_STYLE_EXPLORER'
            or not all(isinstance(source[key], str) and source[key].strip()
                       for key in source_fields)):
        raise ValueError('STYLE_CONTRACT_SOURCE_INVALID')
    evidence = contract['evidence']
    if not isinstance(evidence, list) or not evidence:
        raise ValueError('STYLE_CONTRACT_EVIDENCE_INVALID')
    for item in evidence:
        if (not isinstance(item, dict) or set(item) != {'path', 'role', 'original_sha256s'}
                or not isinstance(item['path'], str) or not item['path'].strip()
                or not isinstance(item['role'], str) or not item['role'].strip()
                or not isinstance(item['original_sha256s'], dict)):
            raise ValueError('STYLE_CONTRACT_EVIDENCE_INVALID')
        if any(not re.fullmatch(r'[a-f0-9]{64}', value)
               for value in item['original_sha256s'].values()):
            raise ValueError('STYLE_CONTRACT_EVIDENCE_HASH_INVALID')
    return contract


def load_style_contract(root: Path, style_id: str) -> dict:
    path = Path(root) / 'config/styles/catalog.yaml'
    try:
        catalog = yaml.safe_load(path.read_text(encoding='utf-8'))
        style = catalog['styles'][style_id]
        contract = style['style_contract']
    except (OSError, KeyError, TypeError, yaml.YAMLError) as exc:
        raise ValueError(f'Unknown or invalid Style Contract: {style_id}') from exc
    return validate_style_contract(contract, style_id)


def compile_anima_style_contract(contract: dict, *, adapter: str, dialect: str,
                                 model_profile: str, workflow_id: str) -> dict:
    """Render contract fields through the explicitly declared Anima caption dialect."""
    validate_style_contract(contract)
    if adapter != 'anima_hybrid' or dialect != 'anima_hybrid_v3':
        raise ValueError('STYLE_DIALECT_UNSUPPORTED: Style Contract has no compiler for this model profile')
    labels = {
        'medium': 'Medium', 'palette': 'Palette', 'linework': 'Linework',
        'shading': 'Shading', 'lighting': 'Lighting', 'background': 'Background',
        'texture': 'Texture', 'value_structure': 'Value structure',
    }
    parts = [f"{labels[field]}: {'; '.join(contract[field])}" for field in CONTRACT_FIELDS]
    required = 'Required style features: ' + '; '.join(item['text'] for item in contract['required_style_features'])
    if contract['priority'] >= 80:
        parts.insert(0, required)
    else:
        parts.append(required)
    return {
        'contract_id': contract['id'],
        'contract_version': contract['version'],
        'contract_sha256': contract_digest(contract),
        'priority': contract['priority'],
        'model_profile': model_profile,
        'workflow_id': workflow_id,
        'adapter': adapter,
        'dialect': dialect,
        'caption': '. '.join(parts) + '.',
        'forbidden_negative_terms': [item['text'] for item in contract['forbidden_style_features']],
        'source': contract['source'],
        'evidence': contract['evidence'],
    }



def compile_krea_style_contract(contract: dict, *, adapter: str, dialect: str,
                                model_profile: str, workflow_id: str) -> dict:
    """Compile structured style as Krea prose; exclusions are instructions, not native negatives."""
    validate_style_contract(contract)
    if adapter != 'krea2' or dialect != 'krea_contract_v1':
        raise ValueError('STYLE_DIALECT_UNSUPPORTED')
    parts = ['; '.join(contract[field]) for field in CONTRACT_FIELDS]
    parts.append('Required visual features: ' + '; '.join(v['text'] for v in contract['required_style_features']))
    parts.append('Exclude these visual features: ' + '; '.join(v['text'] for v in contract['forbidden_style_features']))
    return {'contract_id': contract['id'], 'contract_version': contract['version'],
            'contract_sha256': contract_digest(contract), 'priority': contract['priority'],
            'model_profile': model_profile, 'workflow_id': workflow_id,
            'adapter': adapter, 'dialect': dialect, 'caption': '. '.join(parts) + '.',
            'forbidden_negative_terms': [], 'exclusion_mode': 'POSITIVE_TEXT_INSTRUCTION',
            'source': contract['source'], 'evidence': contract['evidence']}


def style_contract_review_template(contract: dict) -> dict:
    validate_style_contract(contract)
    return {
        'contract_id': contract['id'],
        'contract_version': contract['version'],
        'contract_sha256': contract_digest(contract),
        'status': 'NOT_REVIEWED',
        'required_features': [
            {'code': item['code'], 'description': item['text'], 'expected_presence': 'PRESENT', 'decision': 'NOT_REVIEWED'}
            for item in contract['required_style_features']
        ],
        'forbidden_features': [
            {'code': item['code'], 'description': item['text'], 'expected_presence': 'ABSENT', 'decision': 'NOT_REVIEWED'}
            for item in contract['forbidden_style_features']
        ],
        'failure_codes': [],
        'approval_effect': 'NONE',
    }
