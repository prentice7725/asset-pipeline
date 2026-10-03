"""Opt-in focal composition intent, with conservative source conflict handling."""
import copy
import hashlib
import json

SCHEMA = {
    'type': 'object', 'additionalProperties': False,
    'required': ['version', 'authority', 'source', 'primary_focus'],
    'properties': {
        'version': {'const': 1},
        'authority': {'const': 'EXPLICIT_BRIEF'},
        'source': {'type': 'string', 'minLength': 1},
        'primary_focus': {'type': 'array', 'minItems': 1, 'uniqueItems': True,
                          'items': {'type': 'string', 'minLength': 1}},
    },
}


def apply_intent(brief, spec, selection):
    intent = brief.get('art_direction')
    if intent is None:
        return spec, None
    if brief['output_class'] != 'NONPIXEL_IMAGE':
        raise ValueError('Art direction supports NONPIXEL_IMAGE only')
    from jsonschema import Draft202012Validator
    Draft202012Validator(SCHEMA).validate(intent)
    known = brief['identity']['canonical_traits'] + brief['identity']['visual_traits']
    known += spec.get('appearance', []) + [spec['subject']]
    if any(target not in known for target in intent['primary_focus']):
        raise ValueError('ART_DIRECTION_CONFLICT_REVIEW_REQUIRED: focus must exactly match an existing canonical or visual trait or subject')
    # A free-text composition or a project style lock can encode its own focal hierarchy.
    # Do not guess compatibility or silently override these sources.
    if spec.get('composition') or spec.get('style') or spec.get('styleSources') or selection:
        raise ValueError('ART_DIRECTION_CONFLICT_REVIEW_REQUIRED: existing composition or style requires explicit reconciliation in the source brief')
    result = copy.deepcopy(spec)
    result['composition'] = ('Give visual priority to ' + '; '.join(intent['primary_focus']) +
        '. Preserve every required identity trait, silhouette, equipment detail and narrative clue; '
        'visual priority does not authorize removing or redesigning any required feature')
    record = copy.deepcopy(intent)
    record['sha256'] = hashlib.sha256(json.dumps(intent, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    record['status'] = 'INTENT_ONLY_REVIEW_REQUIRED'
    return result, record
