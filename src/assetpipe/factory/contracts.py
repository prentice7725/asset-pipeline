"""Versioned offline orchestration envelope, independent of the legacy Brief."""
from copy import deepcopy
from jsonschema import Draft202012Validator
from ..brief import obj, SCHEMA as BRIEF_SCHEMA
from ..audio.sfx import AUDIO_CONTRACT

ROLES = ['IDENTITY_PRIMARY', 'ALTERNATE_VIEW', 'POSE_ANCHOR', 'START_FRAME', 'END_FRAME', 'STYLE_REFERENCE']
TEXT = {'type': 'string', 'minLength': 1}
HASH = {'type': 'string', 'pattern': '^[a-f0-9]{64}$'}
IDENTIFIER = {'type': 'string', 'pattern': '^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$'}
IMAGE = obj({'path': TEXT, 'sha256': HASH, 'role': {'enum': ROLES},
             'ownership': TEXT, 'license': TEXT}, ['path', 'sha256', 'role'])
SOURCE = obj({'kind': {'enum': ['GENERATE', 'EXISTING_RUN', 'EXTERNAL_IMAGES']},
              'brief_ref': TEXT, 'manifest_ref': TEXT, 'manifest_sha256': HASH,
              'images': {'type': 'array', 'items': IMAGE, 'maxItems': 3}}, ['kind'])
MOTION = obj({'action': TEXT, 'fps': {'type': 'number', 'exclusiveMinimum': 0},
              'duration_seconds': {'type': 'number', 'exclusiveMinimum': 0},
              'target_frames': {'type': 'integer', 'minimum': 1},
              'background_policy': {'enum': ['PRESERVE_OR_REVIEW', 'EXPLICIT_ALPHA_REVIEW']},
              'workflow_id': TEXT}, ['action', 'fps', 'duration_seconds', 'target_frames', 'background_policy'])
SCHEMA = obj({'factory_contract_version': {'const': 1, 'type': 'integer'},
              'factory_line': {'enum': ['NONPIXEL', 'REFERENCE_MOTION', 'SFX', 'PIXEL64']},
              'output_mode': {'enum': ['IMAGE_ONLY', 'IMAGE_TO_SPRITE', 'AUDIO_ONLY']},
              'project_id': IDENTIFIER, 'asset_id': IDENTIFIER, 'source': SOURCE,
              'image': obj({'style_source': TEXT, 'logical_size': {'const': [64, 64]}}, ['style_source']),
              'motion': {'oneOf': [{'type': 'null'}, MOTION]},
              'audio': {'oneOf': [{'type': 'null'}, AUDIO_CONTRACT]},
              'authorization': obj({'generation_budget': TEXT, 'approval_source': TEXT})},
             ['factory_contract_version', 'factory_line', 'output_mode', 'project_id', 'asset_id', 'source'])
SCHEMA['$schema'] = 'https://json-schema.org/draft/2020-12/schema'
SCHEMA['$id'] = 'urn:assetpipe:factory-request:1'

def rule(condition, properties):
    return {'if': {'properties': condition, 'required': list(condition)}, 'then': properties}

SCHEMA['allOf'] = [
    rule({'factory_line': {'enum': ['NONPIXEL', 'PIXEL64']}},
         {'properties': {'output_mode': {'enum': ['IMAGE_ONLY', 'IMAGE_TO_SPRITE']},
                         'source': {'properties': {'kind': {'enum': ['GENERATE', 'EXISTING_RUN']}}}}, 'required': ['image']}),
    rule({'factory_line': {'const': 'REFERENCE_MOTION'}},
         {'properties': {'output_mode': {'const': 'IMAGE_TO_SPRITE'},
                         'source': {'properties': {'kind': {'enum': ['EXISTING_RUN', 'EXTERNAL_IMAGES']}, 'images': {'minItems': 1}}, 'required': ['images']}}}),
    rule({'factory_line': {'const': 'SFX'}},
         {'properties': {'output_mode': {'const': 'AUDIO_ONLY'}, 'image': False,
                         'audio': AUDIO_CONTRACT,
                         'source': {'properties': {'kind': {'const': 'GENERATE'}}}}, 'required': ['audio']}),
    rule({'factory_line': {'const': 'PIXEL64'}}, {'properties': {'image': {'required': ['logical_size']}}}),
    rule({'output_mode': {'enum': ['IMAGE_ONLY', 'AUDIO_ONLY']}}, {'properties': {'motion': {'type': 'null'}}}),
    rule({'output_mode': {'const': 'IMAGE_TO_SPRITE'}}, {'properties': {'motion': MOTION}, 'required': ['motion']}),
    rule({'factory_line': {'enum': ['NONPIXEL', 'PIXEL64']}, 'output_mode': {'enum': ['IMAGE_ONLY', 'IMAGE_TO_SPRITE']}},
         {'properties': {'audio': {'type': 'null'}}}),
    rule({'factory_line': {'const': 'REFERENCE_MOTION'}}, {'properties': {'audio': {'type': 'null'}, 'image': False}}),
]
for kind in ['GENERATE', 'EXISTING_RUN', 'EXTERNAL_IMAGES']:
    required = {'GENERATE': ['brief_ref'], 'EXISTING_RUN': ['manifest_ref', 'manifest_sha256', 'images'], 'EXTERNAL_IMAGES': ['images']}[kind]
    forbidden = {'GENERATE': ['manifest_ref', 'manifest_sha256', 'images'], 'EXISTING_RUN': ['brief_ref'], 'EXTERNAL_IMAGES': ['brief_ref', 'manifest_ref', 'manifest_sha256']}[kind]
    SCHEMA['allOf'].append(rule({'source': {'properties': {'kind': {'const': kind}}, 'required': ['kind']}},
        {'properties': {'source': {'required': required, 'properties': {key: False for key in forbidden}}}}))
SCHEMA['allOf'].append(rule({'source': {'properties': {'kind': {'const': 'EXTERNAL_IMAGES'}}, 'required': ['kind']}},
    {'properties': {'source': {'properties': {'images': {'items': {'required': ['ownership', 'license']}}}}}}))

def validate(request):
    errors = sorted(Draft202012Validator(SCHEMA).iter_errors(request), key=lambda e: str(e.path))
    if errors:
        raise ValueError('FACTORY_REQUEST_INVALID: ' + '; '.join(f'{list(e.path)}: {e.message}' for e in errors))
    for key in ['project_id', 'asset_id']:
        name = request[key].upper()
        if name in {'CON','PRN','AUX','NUL', *[f'COM{i}' for i in range(10)], *[f'LPT{i}' for i in range(10)]}:
            raise ValueError('FACTORY_REQUEST_INVALID: reserved Windows identifier')
    images = request['source'].get('images', [])
    if request['source']['kind'] == 'EXISTING_RUN' and request['factory_line'] != 'REFERENCE_MOTION' and len(images) != 1:
        raise ValueError('FACTORY_REQUEST_INVALID: still continuation requires exactly one image')
    if len({i['role'] for i in images}) != len(images) or (images and all(i['role'] == 'STYLE_REFERENCE' for i in images)):
        raise ValueError('FACTORY_REQUEST_INVALID: duplicate or unanchored image roles')
    return deepcopy(request)

def brief_schema():
    """Export for parity checks only; never extend the legacy schema."""
    return deepcopy(BRIEF_SCHEMA)
