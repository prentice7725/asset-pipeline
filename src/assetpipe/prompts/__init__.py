"""Canonical visual requirements compiled without inventing identity details."""
import copy
import hashlib
import json
import re
from pathlib import Path
import yaml
from jsonschema import Draft202012Validator
from .subject_contract import INTEGRITY_SCHEMA, DIRECTION_SCHEMA, validate_contract, prepare_spec, subject_lead, direction_tail

LIST = {'type': 'array', 'items': {'type': 'string', 'minLength': 1}}
SCHEMA = {
    '$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object',
    'additionalProperties': False, 'required': ['subject'],
    'properties': {
        'subject_integrity': INTEGRITY_SCHEMA,
        'art_direction': DIRECTION_SCHEMA,
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
    validate_contract(spec, check_style=False)
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
    # Brief-level semantic constraints remain canonical even when PromptSpec is supplied.
    style = brief['constraints'].get('style')
    if style:
        spec['style'] = list(dict.fromkeys(spec.get('style', []) + [style]))
    silhouette = brief['constraints'].get('silhouette')
    if silhouette:
        spec['constraints'] = list(dict.fromkeys(spec.get('constraints', []) + [silhouette]))
    # Canon and forbidden requirements cannot disappear when the spec is provided.
    spec['appearance'] = list(dict.fromkeys(spec.get('appearance', []) + brief['identity']['canonical_traits'] + brief['identity']['visual_traits']))
    negative = list(brief['forbidden_elements'])
    if brief.get('negative_prompt'):
        negative.append(brief['negative_prompt'])
    spec['negative'] = list(dict.fromkeys(spec.get('negative', []) + negative))
    validate_contract(spec, brief, check_style=False)
    return validate_spec(spec)


def natural_language_prompt(brief, spec):
    """CLI 이미지 도구용 자연어 프롬프트. 정본·시각 특징·스타일·실루엣·금지 요소를 항목별로 모두 보존한다."""
    equipment_traits = {item['source_trait'].casefold() for item in equipment}
    canonical = [v for v in brief['identity']['canonical_traits'] if v.casefold() not in equipment_traits]
    silhouette = brief['constraints'].get('silhouette')
    appearance = [v for v in spec.get('appearance', [])
                  if v not in brief['identity']['canonical_traits'] and v.casefold() not in equipment_traits]
    other = [v for v in spec.get('constraints', []) if v != silhouette]
    rows = [('Subject', [spec['subject']]),
            ('Canonical traits (keep exactly as written; do not change, add to, or reinterpret)', canonical),
            ('Visual traits', appearance),
            ('Style', spec.get('style', []) + [r['description'] for r in spec.get('styleSources', [])]),
            ('Silhouette (keep this overall shape)', [silhouette] if silhouette else []),
            ('Other constraints', other)]
    rows += [(label, [spec[key]]) for label, key in (('Pose', 'pose'), ('Composition', 'composition'), ('Environment', 'environment'), ('Lighting', 'lighting'), ('Mood', 'mood')) if spec.get(key)]
    if spec.get('aspectRatio'):
        rows.append(('Aspect ratio', [spec['aspectRatio']]))
    if spec.get('textInImage'):
        rows.append(('Text to render in the image', [json.dumps(t, ensure_ascii=False) for t in spec['textInImage']]))
    if equipment:
        rows.append(('Equipment relationships (preserve the source-defined relationship and count)',
                     [f"{item['source_trait']} ({item['relationship']}" +
                      (f", visible count of {item['visible_count']}" if item.get('visible_count') else '') + ')'
                      for item in equipment]))
    lines = [f'{label}: ' + '; '.join(dict.fromkeys(values)) for label, values in rows if values]
    if spec.get('negative'):
        lines.append('Strictly do not include any of the following: ' + '; '.join(dict.fromkeys(spec['negative'])) + '.')
    return '\n'.join(lines)



def anima_hybrid_prompt(spec, profile):
    """Official-guidance Anima layout: quality/meta tags followed by a detailed caption.

    PromptSpec remains model-neutral. This compiler formats the same canonical facts
    without requiring per-style hand-authored final prompts.
    """
    prefix = profile.get('positive_prefix', [])
    if not isinstance(prefix, list) or any(not isinstance(v, str) or not v.strip() for v in prefix):
        raise ValueError('Anima positive_prefix must be a list of nonempty strings')
    sentences = [f"Depict {spec['subject'].rstrip('. ')}."]
    equipment = spec.get('subject_integrity', {}).get('equipment', [])
    equipment_traits = {item['source_trait'].casefold() for item in equipment}
    subject_text = spec['subject'].casefold()
    appearance = [
        value for value in spec.get('appearance', [])
        if value.casefold() not in equipment_traits and value.casefold() not in subject_text
    ]
    rows = (
        ('Appearance', appearance),
        ('Pose', [spec['pose']] if spec.get('pose') else []),
        ('Composition', [spec['composition']] if spec.get('composition') else []),
        ('Environment', [spec['environment']] if spec.get('environment') else []),
        ('Lighting', [spec['lighting']] if spec.get('lighting') else []),
        ('Mood', [spec['mood']] if spec.get('mood') else []),
        ('Style direction', spec.get('style', []) + [row['description'] for row in spec.get('styleSources', [])]),
        ('Constraints', spec.get('constraints', [])),
    )
    for label, values in rows:
        values = list(dict.fromkeys(v.strip() for v in values if isinstance(v, str) and v.strip()))
        if values:
            sentences.append(f"{label}: " + '; '.join(values) + '.')
    if len(sentences) < 2:
        sentences.append('Preserve the described subject faithfully and do not invent unspecified identity details.')
    caption = ' '.join(sentences)
    return (', '.join(prefix) + '. ' if prefix else '') + caption


def compile_prompt(brief, workflow, root):
    from ..styles import resolve_style, select_recipe, apply_style, public_selection
    spec = from_brief(brief)
    selection = resolve_style(brief, root)
    explicit = brief['workflow_preferences'].get('id') == workflow['id'] or brief['workflow_preferences'].get('model_profile') == workflow.get('model_profile')
    selection = select_recipe(selection, workflow, root, explicit=explicit)
    spec = validate_spec(apply_style(spec, selection))
    from ..art_direction import apply_intent
    spec, intent = apply_intent(brief, spec, selection)
    result = compile_spec(brief, workflow, root, spec, preserve_case=bool(selection), style_context=selection)
    if intent:
        result['art_direction'] = intent
    if selection:
        result['style_selection'] = public_selection(selection)
    return result


def compile_spec(brief, workflow, root, spec, *, preserve_case=False, style_context=None):
    """Shared dialect compiler for validated offline specs; performs no routing or generation."""
    profiles = yaml.safe_load((Path(root) / 'config/model_profiles.yaml').read_text(encoding='utf-8'))
    profile_id = workflow.get('model_profile')
    if profile_id not in profiles['profiles']:
        raise ValueError('Workflow must declare a configured model_profile')
    profile = profiles['profiles'][profile_id]
    spec = validate_spec(spec)
    caps = workflow['capabilities']
    spec = prepare_spec(spec, brief, caps, style_context)
    adapter = profile['prompt_adapter']
    native_negative = bool(caps.get('negative_prompt'))
    equipment = spec.get('subject_integrity', {}).get('equipment', [])
    # Model-profile defaults are part of the model dialect, not project canon.
    profile_negative = profile.get('negative_prefix', [])
    if not isinstance(profile_negative, list) or any(not isinstance(v, str) or not v.strip() for v in profile_negative):
        raise ValueError('Model negative_prefix must be a list of nonempty strings')
    contract_negative_guards = []
    if native_negative and any(item.get('visible_count') == 1 for item in equipment):
        contract_negative_guards = ['duplicate required equipment', 'extra copies of required equipment']
    negative_items = list(dict.fromkeys(profile_negative + spec.get('negative', []) + contract_negative_guards))
    # 자연어 금지 지시는 프롬프트 안의 문장일 뿐 모델이 보장하지 않으므로, 네이티브 negative prompt와 구분한다.
    instructed_negative = adapter == 'natural_language' and bool(caps.get('negative_prompt_instruction'))
    if negative_items and not (native_negative or instructed_negative):
        raise ValueError('Selected workflow does not support negative prompts')
    if spec.get('textInImage') and not caps.get('text_rendering'):
        raise ValueError('Selected workflow has no validated text rendering capability')
    equipment = spec.get('subject_integrity', {}).get('equipment', [])
    equipment_traits = {item['source_trait'].casefold() for item in equipment}
    appearance = [value for value in spec.get('appearance', [])
                  if value.casefold() not in equipment_traits]
    fields = [spec['subject'], *appearance]
    fields += [spec[key] for key in ('pose', 'composition', 'environment', 'lighting', 'mood') if spec.get(key)]
    fields += spec.get('style', []) + [row['description'] for row in spec.get('styleSources', [])] + spec.get('constraints', [])
    fields = list(dict.fromkeys(fields))
    if adapter == 'natural_language':
        positive = natural_language_prompt(brief, spec)
    elif adapter == 'anima':
        positive = ', '.join(profile.get('positive_prefix', []) + (fields if preserve_case else [value.lower() for value in fields]))
    elif adapter == 'anima_hybrid':
        positive = anima_hybrid_prompt(spec, profile)
    elif adapter == 'krea2':
        positive = '. '.join(value.rstrip('. ') for value in fields) + '.'
    else:
        raise ValueError('Prompt adapter is not installed: ' + adapter)
    if spec.get('subject_integrity'):
        if adapter == 'anima_hybrid':
            integrity = spec['subject_integrity']
            guards = []
            if integrity.get('physically_connected_body'):
                guards.append('Keep the body physically connected')
            if integrity.get('whole_subject_required'):
                guards.append('keep the whole character in frame from head to toe')
            if integrity.get('mandatory_parts'):
                guards.append('keep these required body parts present and connected: ' + ', '.join(integrity['mandatory_parts']))
            guards.append('preserve the source-defined camera view')
            positive += '\nSubject integrity: ' + '; '.join(guards) + '.'
        else:
            lead = subject_lead(spec, adapter)
            positive = lead + '\n' + positive
        if adapter != 'natural_language' and equipment:
            positive += '\nEquipment relationships (preserve the source-defined relationship and count): ' + '; '.join(
                f"{item['source_trait']} ({item['relationship']}" +
                (f", visible count of {item['visible_count']}" if item.get('visible_count') else '') + ')'
                for item in equipment) + '.'
        tail = direction_tail(spec)
        if tail:
            positive += '\n' + tail
    if spec.get('textInImage') and adapter != 'natural_language':
        positive += ' Text in the image: ' + ', '.join(json.dumps(t, ensure_ascii=False) for t in spec['textInImage']) + '.'
    negative_mode = 'NONE' if not negative_items else 'NATURAL_LANGUAGE_INSTRUCTION' if instructed_negative else 'NATIVE'
    result = {'schema_version': 1, 'adapter': adapter, 'profile_id': profile_id,
            'profile_sha256': hashlib.sha256(json.dumps(profile, sort_keys=True).encode()).hexdigest(),
            'prompt_spec': spec, 'positive': positive, 'negative': '' if instructed_negative else ', '.join(negative_items),
            'negative_mode': negative_mode, 'negative_instruction': list(negative_items) if instructed_negative else [],
            'contract_negative_guards': contract_negative_guards,
            'compiler_revision': 'anima_hybrid_v2' if adapter == 'anima_hybrid' else 'legacy',
            'aspect_ratio': spec.get('aspectRatio'), 'defaults': profile.get('defaults', {})}
    if spec.get('subject_integrity'):
        result['subject_contract_review'] = {'semantic': 'NOT_VALIDATED', 'composition': 'NOT_VALIDATED',
            'art': 'NOT_VALIDATED', 'human_review': 'REVIEW_REQUIRED',
            'identity_source': spec['subject_integrity']['identity_source'],
            'style_fingerprint_binding': spec.get('art_direction', {}).get('style_sha256'),
            'approval_effect': 'NONE'}
        from .subject_contract import assessment_limits
        result['subject_contract_review']['assessment_limits'] = assessment_limits(spec)
    return result


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
