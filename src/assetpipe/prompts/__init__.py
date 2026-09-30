"""Canonical visual requirements compiled without inventing identity details."""
import copy
import hashlib
import json
import re
from pathlib import Path
import yaml
from jsonschema import Draft202012Validator

LIST = {'type': 'array', 'items': {'type': 'string', 'minLength': 1}}
SCHEMA = {
    '$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object',
    'additionalProperties': False, 'required': ['subject'],
    'properties': {
        **{key: {'type': 'string', 'minLength': 1} for key in ('subject', 'pose', 'composition', 'environment', 'lighting', 'mood')},
        **{key: LIST for key in ('appearance', 'style', 'constraints', 'negative', 'textInImage')},
        'aspectRatio': {'type': 'string', 'pattern': '^[1-9][0-9]*:[1-9][0-9]*$'},
        'styleSources': {'type': 'array', 'items': {
            'type': 'object', 'additionalProperties': False, 'required': ['url', 'description'],
            'properties': {'url': {'type': 'string', 'pattern': '^https?://'}, 'description': {'type': 'string', 'minLength': 1}}
        }},
    },
}


def validate_spec(spec):
    Draft202012Validator(SCHEMA).validate(spec)
    if not spec['subject'].strip():
        raise ValueError('PromptSpec subject must not be empty')
    return spec


def from_brief(brief):
    if 'prompt_spec' in brief:
        spec = copy.deepcopy(validate_spec(brief['prompt_spec']))
    else:
        subject = brief.get('prompt') or ', '.join(brief['identity']['canonical_traits'])
        spec = {'subject': subject, 'appearance': list(brief['identity']['visual_traits'])}
        if brief['constraints'].get('style'):
            spec['style'] = [brief['constraints']['style']]
        if brief['constraints'].get('silhouette'):
            spec['constraints'] = [brief['constraints']['silhouette']]
    # Canon and forbidden requirements cannot disappear when the spec is provided.
    spec['appearance'] = list(dict.fromkeys(spec.get('appearance', []) + brief['identity']['canonical_traits'] + brief['identity']['visual_traits']))
    negative = list(brief['forbidden_elements'])
    if brief.get('negative_prompt'):
        negative.append(brief['negative_prompt'])
    spec['negative'] = list(dict.fromkeys(spec.get('negative', []) + negative))
    return validate_spec(spec)


def compile_prompt(brief, workflow, root):
    profiles = yaml.safe_load((Path(root) / 'config/model_profiles.yaml').read_text(encoding='utf-8'))
    profile_id = workflow.get('model_profile')
    if profile_id not in profiles['profiles']:
        raise ValueError('Workflow must declare a configured model_profile')
    profile = profiles['profiles'][profile_id]
    spec = from_brief(brief)
    caps = workflow['capabilities']
    if spec.get('negative') and not caps.get('negative_prompt'):
        raise ValueError('Selected workflow does not support negative prompts')
    if spec.get('textInImage') and not caps.get('text_rendering'):
        raise ValueError('Selected workflow has no validated text rendering capability')
    fields = [spec['subject'], *spec.get('appearance', [])]
    fields += [spec[key] for key in ('pose', 'composition', 'environment', 'lighting', 'mood') if spec.get(key)]
    fields += spec.get('style', []) + [row['description'] for row in spec.get('styleSources', [])] + spec.get('constraints', [])
    fields = list(dict.fromkeys(fields))
    adapter = profile['prompt_adapter']
    if adapter == 'anima':
        positive = ', '.join(profile.get('positive_prefix', []) + [value.lower() for value in fields])
    elif adapter == 'krea2':
        positive = '. '.join(value.rstrip('. ') for value in fields) + '.'
    else:
        raise ValueError('Prompt adapter is not installed: ' + adapter)
    if spec.get('textInImage'):
        positive += ' Text in the image: ' + ', '.join(json.dumps(t, ensure_ascii=False) for t in spec['textInImage']) + '.'
    return {'schema_version': 1, 'adapter': adapter, 'profile_id': profile_id,
            'profile_sha256': hashlib.sha256(json.dumps(profile, sort_keys=True).encode()).hexdigest(),
            'prompt_spec': spec, 'positive': positive, 'negative': ', '.join(spec.get('negative', [])),
            'aspect_ratio': spec.get('aspectRatio'), 'defaults': profile.get('defaults', {})}


def workflow_values(compiled, workflow, brief):
    preset = brief['workflow_preferences'].get('preset', workflow.get('default_preset'))
    if preset not in workflow.get('presets', {}):
        raise ValueError('Unknown workflow preset: ' + str(preset))
    values = {**compiled['defaults'], **workflow['presets'][preset], **workflow.get('workflow_inputs', {})}
    resolution = brief['constraints']['resolution']
    ratio = compiled['aspect_ratio']
    if resolution:
        if ratio:
            w, h = map(int, ratio.split(':'))
            if resolution[0] * h != resolution[1] * w:
                raise ValueError('PromptSpec aspect ratio conflicts with explicit resolution')
        values['width'], values['height'] = resolution
    elif ratio:
        w, h = map(int, ratio.split(':'))
        base = min(values['width'], values['height'])
        unit = max(8, (base // min(w, h) // 8) * 8)
        values['width'], values['height'] = unit * w, unit * h
        if max(values['width'], values['height']) > 2048:
            raise ValueError('Aspect ratio exceeds configured generation size limit; supply resolution')
    return values
