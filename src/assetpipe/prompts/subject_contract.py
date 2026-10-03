"""Explicit subject contracts for the existing compiler; no image validation."""
import copy
import re

CLASSES = ['full_character', 'costume_item', 'prop', 'environment']
TEXT = {'type': 'string', 'minLength': 1}
STRINGS = {'type': 'array', 'uniqueItems': True, 'items': TEXT}
INTEGRITY_SCHEMA = {
    'type': 'object', 'additionalProperties': False,
    'required': ['class', 'identity_source'],
    'properties': {
        'class': {'enum': CLASSES}, 'identity_source': TEXT,
        'whole_subject_required': {'type': 'boolean'},
        'physically_connected_body': {'type': 'boolean'},
        'mandatory_parts': STRINGS,
        'camera_view': {'enum': ['from_source', 'front', 'rear', 'left', 'right']},
        'equipment': {'type': 'array', 'items': {
            'type': 'object', 'additionalProperties': False,
            'required': ['source_trait', 'relationship'],
            'properties': {'source_trait': TEXT, 'relationship': {'enum': ['worn', 'carried']},
                'visible_count': {'type': 'integer', 'minimum': 1},
                'location': {'enum': ['unspecified', 'front', 'rear', 'left', 'right']}}
        }},
        'forbidden_substitutions': STRINGS,
    },
}
DIRECTION_SCHEMA = {
    'type': 'object', 'additionalProperties': False,
    'required': ['focal_target', 'source'],
    'properties': {
        'focal_target': {'enum': CLASSES}, 'source': TEXT,
        'style_sha256': {'type': 'string', 'pattern': '^[a-f0-9]{64}$'},
        'value_grouping': {'const': 'large_coherent_masses'},
        'shadow_grouping': {'const': 'broad_connected_shadows'},
        'background_texture': {'const': 'subordinate'},
        'subject_texture': {'const': 'selective_detail'},
        'silhouette_contrast': {'const': 'strong'},
        'preserve_scene_landmarks': {'const': True},
    },
}


def camera_from_source(spec):
    text = ' '.join(spec.get(k, '') for k in ('pose', 'composition'))
    text += ' ' + ' '.join(spec.get('constraints', []))
    patterns = {'front': r'\b(?:front view|front-facing)\b',
                'rear': r'\b(?:rear view|back view|rear-facing|from behind)\b',
                'left': r'\bleft side view\b', 'right': r'\bright side view\b'}
    views = [view for view, pattern in patterns.items() if re.search(pattern, text, re.I)]
    if len(views) > 1:
        raise ValueError('BRIEF_COMPOSITION_CONFLICT: incompatible source camera views')
    return views[0] if views else None


def validate_contract(spec, brief=None, style_context=None, *, check_style=True):
    integrity, direction = spec.get('subject_integrity'), spec.get('art_direction')
    if not integrity and not direction:
        return
    if direction and not integrity:
        raise ValueError('Art direction requires an explicit subject_integrity contract')
    if brief and brief['output_class'] != 'NONPIXEL_IMAGE':
        raise ValueError('Subject-first contracts support NONPIXEL_IMAGE only')
    kind = integrity['class']
    if brief and brief['asset_type'] == 'character' and kind != 'full_character':
        raise ValueError('SUBJECT_CLASS_CONFLICT: character cannot become costume_item or another subject class')
    if kind == 'full_character':
        if integrity.get('whole_subject_required') is not True or integrity.get('physically_connected_body') is not True:
            raise ValueError('Full character requires explicit whole-subject and connected-body locks')
    elif integrity.get('physically_connected_body') or integrity.get('mandatory_parts'):
        raise ValueError('SUBJECT_CLASS_CONFLICT: non-character subject cannot acquire body requirements')
    source_view = camera_from_source(spec)
    view = integrity.get('camera_view', 'from_source')
    if view != 'from_source' and source_view != view:
        raise ValueError('BRIEF_COMPOSITION_CONFLICT: explicit camera must match the source pose/composition/constraints')
    view = source_view if view == 'from_source' else view
    sources = [spec['subject'], *spec.get('appearance', []), *spec.get('constraints', [])]
    if brief:
        sources += brief['identity']['canonical_traits'] + brief['identity']['visual_traits']
    numbers = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6,
               'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10, 'eleven': 11, 'twelve': 12}
    for item in integrity.get('equipment', []):
        trait = item['source_trait']
        if brief is not None and trait not in sources:
            raise ValueError('SUBJECT_SOURCE_CONFLICT: equipment must cite an exact source trait')
        count = item.get('visible_count')
        if count:
            matches = re.findall(r'\b(?:\d+|' + '|'.join(numbers) + r')\b', trait.lower())
            counts = [int(v) if v.isdigit() else numbers[v] for v in matches]
            if counts != [count]:
                raise ValueError('SUBJECT_SOURCE_CONFLICT: visible count must match an unambiguous explicit source count')
            location = item.get('location', 'unspecified')
            if location != 'unspecified' and not re.search(r'\b' + location + r'\b', trait, re.I):
                raise ValueError('SUBJECT_SOURCE_CONFLICT: equipment location must be explicit in its source trait')
            if (view, location) in {('front', 'rear'), ('rear', 'front'), ('left', 'right'), ('right', 'left')}:
                raise ValueError('BRIEF_COMPOSITION_CONFLICT: camera cannot show the required equipment count at its declared location')
    if direction:
        if direction['focal_target'] != kind:
            raise ValueError('SUBJECT_CLASS_CONFLICT: art direction cannot change the subject class')
        if not check_style:
            return
        if style_context:
            if style_context.get('locked'):
                raise ValueError('ART_DIRECTION_CONFLICT_REVIEW_REQUIRED: locked Visual SOT requires source reconciliation')
            if direction.get('style_sha256') != style_context['style_sha256']:
                raise ValueError('ART_DIRECTION_CONFLICT_REVIEW_REQUIRED: direction must bind the selected style fingerprint')
        elif direction.get('style_sha256'):
            raise ValueError('ART_DIRECTION_CONFLICT_REVIEW_REQUIRED: no resolved style for the declared fingerprint')


def assessment_limits(spec):
    """Record unassessed visibility/prose without certifying image semantics."""
    view = camera_from_source(spec)
    counted = [item for item in spec['subject_integrity'].get('equipment', []) if item.get('visible_count')]
    return {
        'recognized_source_camera': view,
        'camera_assessment': 'RECOGNIZED_PATTERN_ONLY' if view else 'SOURCE_VIEW_UNASSESSED',
        'view_visibility': 'VIEW_VISIBILITY_REVIEW_REQUIRED' if counted else 'NOT_ASSESSED',
        'visibility_reason': 'Counts do not prove visibility; unspecified placement, occlusion and camera geometry require image review.',
        'prose_conflicts': 'UNASSESSED_OUTSIDE_EXPLICIT_PATTERNS',
        'certifies_conflict_absence': False,
    }


def prepare_spec(spec, brief, caps, style_context=None):
    validate_contract(spec, brief, style_context)
    if 'subject_integrity' not in spec:
        return spec
    original = brief.get('prompt_spec', {})
    if original.get('subject_integrity') != spec['subject_integrity'] or original.get('art_direction') != spec.get('art_direction'):
        raise ValueError('SUBJECT_SOURCE_CONFLICT: recipe cannot rewrite subject or direction contracts')
    if any(trait not in spec.get('appearance', []) for trait in
           brief['identity']['canonical_traits'] + brief['identity']['visual_traits']):
        raise ValueError('SUBJECT_SOURCE_CONFLICT: recipe removed canonical or visual traits')
    silhouette = brief['constraints'].get('silhouette')
    if silhouette and silhouette not in spec.get('constraints', []):
        raise ValueError('SUBJECT_SOURCE_CONFLICT: recipe removed source silhouette')
    style = brief['constraints'].get('style')
    if style and style not in spec.get('style', []):
        raise ValueError('SUBJECT_SOURCE_CONFLICT: recipe removed source style')
    forbidden = brief['forbidden_elements'] + original.get('negative', [])
    if brief.get('negative_prompt'):
        forbidden += [brief['negative_prompt']]
    if any(trait not in spec.get('negative', []) for trait in forbidden):
        raise ValueError('SUBJECT_SOURCE_CONFLICT: recipe removed forbidden requirements')
    spec = copy.deepcopy(spec)
    substitutes = spec['subject_integrity'].get('forbidden_substitutions', [])
    if substitutes and not caps.get('negative_prompt'):
        raise ValueError('Subject forbidden substitutions require native negative prompt support')
    spec['negative'] = list(dict.fromkeys(spec.get('negative', []) + substitutes))
    return spec


def subject_lead(spec, adapter):
    integrity = spec['subject_integrity']
    kind = integrity['class']
    if kind == 'full_character':
        lead = f"Depict the complete character described here: {spec['subject']}. Keep its body physically connected"
        if integrity.get('whole_subject_required'):
            lead += ' and the whole character in frame'
        lead += '.'
        if adapter == 'anima':
            lead += ' Full body, complete character.'
    else:
        lead = f"Depict the {kind.replace('_', ' ')} described here: {spec['subject']}."
        if integrity.get('whole_subject_required'):
            lead += ' Show the whole subject.'
    if integrity.get('mandatory_parts'):
        lead += ' Keep these source-required parts present and connected: ' + ', '.join(integrity['mandatory_parts']) + '.'
    if spec.get('pose'):
        lead += ' Source action and pose: ' + spec['pose'].rstrip('. ') + '.'
    lead += ' Preserve the source-defined camera view.'
    return lead


def direction_tail(spec):
    direction = spec.get('art_direction')
    if not direction:
        return ''
    kind = direction['focal_target'].replace('_', ' ')
    text = f'Make the entire {kind} the primary focal subject'
    if direction['focal_target'] == 'full_character':
        text += '; show equipment as part of the worn or carried outfit'
    text += '.'
    phrases = {'value_grouping': 'Use large coherent local-color and value masses.',
               'shadow_grouping': 'Group shading into broad connected shadow shapes.',
               'subject_texture': 'Reserve selective detail for the subject.',
               'background_texture': 'Subordinate incidental background textures to the subject while retaining required scene context.',
               'silhouette_contrast': 'Keep the subject silhouette clearly separated from the background.',
               'preserve_scene_landmarks': 'Preserve every source-required scene landmark and narrative clue.'}
    for key, phrase in phrases.items():
        if direction.get(key):
            text += ' ' + phrase
    return text
