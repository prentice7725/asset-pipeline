from pathlib import Path
import json
import yaml
from jsonschema import Draft202012Validator
from ..prompts import SCHEMA as PROMPT_SPEC_SCHEMA
from ..art_direction import SCHEMA as ART_DIRECTION_SCHEMA

OUTPUT_CLASSES = ['PIXEL_STATIC', 'PIXEL_ANIMATION', 'NONPIXEL_IMAGE', 'NONPIXEL_ANIMATION', 'SFX']
STRINGS = {'type': 'array', 'items': {'type': 'string'}}
def obj(properties, required=()):
    return {'type': 'object', 'properties': properties, 'required': list(required), 'additionalProperties': False}

SCHEMA = obj({
    'art_direction': ART_DIRECTION_SCHEMA,
    'art_style': {'type': 'string', 'pattern': '^[a-z0-9_]+$'},
    'style_selection_policy': {'enum': ['style_fidelity', 'character_readability']},
    'style_id': {'type': 'string', 'pattern': '^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$'},
    'project_id': {'type': 'string', 'pattern': '^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$'},
    'asset_id': {'type': 'string', 'pattern': '^[A-Za-z0-9_-]+$'},
    'asset_type': {'type': 'string', 'minLength': 1},
    'output_class': {'enum': OUTPUT_CLASSES},
    'purpose': {'type': 'string', 'minLength': 1},
    'source': obj({'type': {'enum': ['PROMPT', 'REFERENCE_IMAGE', 'DOCUMENTS']}, 'paths': STRINGS, 'references': STRINGS}, ['type', 'paths', 'references']),
    'identity': obj({'canonical_traits': STRINGS, 'visual_traits': STRINGS}, ['canonical_traits', 'visual_traits']),
    'constraints': obj({'resolution': {'oneOf': [{'type': 'null'}, {'type': 'array', 'items': {'type': 'integer', 'minimum': 1}, 'minItems': 2, 'maxItems': 2}]}, 'transparency': {'type': ['boolean', 'null']}, 'palette': STRINGS, 'silhouette': {'type': ['string', 'null']}, 'style': {'type': ['string', 'null']}}, ['resolution', 'transparency', 'palette', 'silhouette', 'style']),
    'animation': obj({'action': {'type': ['string', 'null']}, 'frame_target': {'type': ['integer', 'null'], 'minimum': 1}, 'motion_constraints': STRINGS}, ['action', 'frame_target', 'motion_constraints']),
    'workflow_preferences': obj({'id': {'type': ['string', 'null']}, 'model_profile': {'type': 'string', 'minLength': 1}, 'tags': STRINGS, 'preset': {'type': 'string'}, 'allow_experimental': {'type': 'boolean'}}),
    'forbidden_elements': STRINGS, 'unspecified_elements': STRINGS,
    'source_notes': {'type': 'array', 'items': obj({'classification': {'enum': ['EXPLICIT', 'DERIVED', 'UNSPECIFIED']}, 'text': {'type': 'string'}, 'source': {'type': 'string'}}, ['classification', 'text', 'source'])},
    'prompt': {'type': 'string'}, 'negative_prompt': {'type': 'string'}, 'prompt_spec': PROMPT_SPEC_SCHEMA,
    'audio': obj({'duration_seconds': {'type': 'number', 'minimum': 1, 'maximum': 30}}, ['duration_seconds']),
    'production': obj({'static_master': {'type': 'string'}, 'approval_record': {'type': 'string'}, 'motion_reference': {'type': 'string'}, 'source_frames': {'type': 'string'}, 'selection': {'type': 'string'}, 'direct_profile': {'type': 'string'}}),
}, ['asset_id', 'asset_type', 'output_class', 'purpose', 'source', 'identity', 'constraints', 'animation', 'workflow_preferences', 'forbidden_elements', 'unspecified_elements', 'source_notes'])
SCHEMA['$schema'] = 'https://json-schema.org/draft/2020-12/schema'

def validate(brief):
    errors = sorted(Draft202012Validator(SCHEMA).iter_errors(brief), key=lambda e: str(e.path))
    if errors:
        raise ValueError('; '.join(f'{".".join(map(str, e.path)) or "brief"}: {e.message}' for e in errors))
    if 'art_direction' in brief and brief['output_class'] != 'NONPIXEL_IMAGE':
        raise ValueError('Art direction supports NONPIXEL_IMAGE only')
    if brief.get('prompt_spec', {}).get('subject_integrity') or brief.get('prompt_spec', {}).get('art_direction'):
        from ..prompts import from_brief
        if 'art_direction' in brief:
            raise ValueError('Use structured PromptSpec direction or legacy brief focal intent separately')
        from_brief(brief)
    project = brief.get('project_id', 'default')
    if project.upper() in {'CON', 'PRN', 'AUX', 'NUL', *[f'COM{i}' for i in range(10)], *[f'LPT{i}' for i in range(10)]}:
        raise ValueError('project_id cannot be a reserved Windows directory name')
    if brief['output_class'].endswith('ANIMATION') and not brief['animation']['action']:
        raise ValueError('Animation requires an explicit action')
    if brief['source']['type'] != 'PROMPT' and not brief['source']['paths']:
        raise ValueError('Reference/document sources require paths')
    if brief['source']['type'] == 'PROMPT' and not brief.get('prompt', '').strip() and not brief.get('prompt_spec', {}).get('subject', '').strip():
        raise ValueError('Prompt source requires a nonempty prompt')
    return brief

def load(path):
    path = Path(path).resolve()
    brief = validate(yaml.safe_load(path.read_text(encoding='utf-8')))
    for key in ['paths', 'references']:
        brief['source'][key] = [str((path.parent / p).resolve()) for p in brief['source'][key]]
    if brief['source']['type'] == 'DOCUMENTS':
        for note in brief['source_notes']:
            note['source'] = str((path.parent / note['source']).resolve())
    for key in ['static_master', 'approval_record', 'motion_reference', 'source_frames', 'selection']:
        if key in brief.get('production', {}):
            brief['production'][key] = str((path.parent / brief['production'][key]).resolve())
    return brief

def make(*, asset_id, output_class, prompt='', reference=None, action=None):
    return validate({'asset_id': asset_id, 'asset_type': 'character', 'output_class': output_class,
        'purpose': 'game asset candidate', 'source': {'type': 'REFERENCE_IMAGE' if reference else 'PROMPT', 'paths': [str(Path(reference).resolve())] if reference else [], 'references': []},
        'identity': {'canonical_traits': [], 'visual_traits': []},
        'constraints': {'resolution': None, 'transparency': None, 'palette': [], 'silhouette': None, 'style': None},
        'animation': {'action': action, 'frame_target': None, 'motion_constraints': []},
        'workflow_preferences': {}, 'forbidden_elements': [], 'unspecified_elements': ['identity', 'resolution', 'palette', 'silhouette', 'style'],
        'source_notes': [{'classification': 'EXPLICIT', 'text': prompt or 'Provided reference image', 'source': 'user input'}], 'prompt': prompt})
