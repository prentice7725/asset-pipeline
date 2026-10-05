"""Validated structured fixture for controlled Anima-family comparisons."""
from __future__ import annotations

from pathlib import Path

import yaml

FIXTURE_ID = 'anima_family_traveler_v1'
REQUIRED_TRAITS = {
    'adult traveler', 'short dark brown hair', 'plain blue knee-length coat',
    'dark trousers', 'dark closed shoes',
}
PART_TEXT = {
    'head': 'head', 'torso': 'torso', 'both arms': 'both arms',
    'both hands': 'both hands', 'both legs': 'both legs', 'both feet': 'both feet',
}


def validate_fixture_contract(fixture: dict) -> dict:
    if fixture.get('id') != FIXTURE_ID or fixture.get('state') != 'SYNTHETIC_NOT_CANON':
        raise ValueError('SYNTHETIC_FIXTURE_IDENTITY_INVALID')
    if fixture.get('output_class') != 'NONPIXEL_IMAGE':
        raise ValueError('SYNTHETIC_FIXTURE_OUTPUT_CLASS_INVALID')
    subject = fixture.get('subject', {})
    if subject.get('count') != 1 or subject.get('class') != 'adult traveler':
        raise ValueError('SYNTHETIC_FIXTURE_SUBJECT_INVALID')
    traits = subject.get('canonical_traits')
    if not isinstance(traits, list) or not REQUIRED_TRAITS.issubset(traits):
        raise ValueError('SYNTHETIC_FIXTURE_REQUIRED_TRAIT_MISSING')
    equipment = fixture.get('equipment')
    if not isinstance(equipment, list) or len(equipment) != 1:
        raise ValueError('SYNTHETIC_FIXTURE_EQUIPMENT_COUNT_INVALID')
    item = equipment[0]
    if (item.get('source_trait') != "exactly one brass compass held in the subject's left hand"
            or item.get('visible_count') != 1 or item.get('subject_side') != 'SUBJECT_LEFT'
            or item.get('relationship') != 'carried' or item['source_trait'] not in traits):
        raise ValueError('SYNTHETIC_FIXTURE_COMPASS_CONTRACT_INVALID')
    if fixture.get('camera', {}).get('view') != 'FRONT':
        raise ValueError('SYNTHETIC_FIXTURE_CAMERA_INVALID')
    framing = fixture.get('framing', {})
    if (framing.get('coverage') != 'HEAD_TO_TOE' or framing.get('feet_fully_visible') is not True
            or framing.get('lower_margin') != 'visible'
            or set(framing.get('required_parts', [])) != set(PART_TEXT)):
        raise ValueError('SYNTHETIC_FIXTURE_FRAMING_INVALID')
    scene = fixture.get('scene', {})
    if scene.get('extra_people') is not False or scene.get('extra_props') is not False:
        raise ValueError('SYNTHETIC_FIXTURE_SCENE_INVALID')
    provenance = fixture.get('provenance', {})
    if provenance.get('classification') != 'DERIVED' or not provenance.get('source'):
        raise ValueError('SYNTHETIC_FIXTURE_PROVENANCE_INVALID')
    return fixture


def load_fixture_contract(root: Path) -> dict:
    path = Path(root) / 'config/style_menu/anima_family_synthetic_fixture_v1.yaml'
    try:
        data = yaml.safe_load(path.read_text(encoding='utf-8'))
        return validate_fixture_contract(data['fixtures'][FIXTURE_ID])
    except (OSError, KeyError, TypeError, yaml.YAMLError) as exc:
        raise ValueError('SYNTHETIC_FIXTURE_CONTRACT_UNAVAILABLE') from exc


def build_anima_family_brief(root: Path, style_id: str, workflow_id: str) -> dict:
    from ..brief import make, validate

    fixture = load_fixture_contract(root)
    camera = {'FRONT': 'front', 'REAR': 'rear'}.get(fixture['camera']['view'])
    if camera is None:
        raise ValueError('SYNTHETIC_FIXTURE_CAMERA_UNSUPPORTED')
    subject = fixture['subject']
    brief = make(asset_id=f'{style_id}_{workflow_id}_r3'.replace('-', '_'),
                 output_class=fixture['output_class'], prompt='synthetic Anima family comparison fixture')
    brief.pop('prompt', None)
    brief['style_id'] = style_id
    brief['identity'] = {'canonical_traits': list(subject['canonical_traits']), 'visual_traits': []}
    silhouette = 'complete head-to-toe human silhouette with both feet visible'
    brief['constraints'].update({'resolution': [512, 768], 'style': None, 'silhouette': silhouette})
    brief['workflow_preferences'] = {'id': workflow_id, 'preset': 'pilot_b1_compatible', 'allow_experimental': True}
    brief['source_notes'] = [{
        'classification': fixture['provenance']['classification'],
        'text': fixture['provenance']['note'], 'source': fixture['provenance']['source'],
    }]
    brief['unspecified_elements'] = ['project identity', 'project lore']
    item = fixture['equipment'][0]
    framing = fixture['framing']
    required_parts = [PART_TEXT[name] for name in framing['required_parts']]
    coverage = 'complete head-to-toe framing'
    feet = 'both feet fully visible with a visible margin below the shoes'
    scene = fixture['scene']
    brief['prompt_spec'] = {
        'subject': f"Exactly one {subject['class']}.",
        'appearance': list(subject['canonical_traits']),
        'pose': f"{fixture['camera']['pose']} in {camera} view",
        'composition': f"{coverage}; keep {', '.join(required_parts)} inside the frame; {feet}",
        'environment': 'No additional characters or props.' if not scene['extra_people'] and not scene['extra_props'] else '',
        'constraints': [silhouette],
        'negative': [],
        'style_contract_id': style_id,
        'subject_integrity': {
            'class': 'full_character', 'identity_source': f"synthetic fixture {fixture['id']}",
            'whole_subject_required': True, 'physically_connected_body': True,
            'mandatory_parts': required_parts, 'camera_view': camera,
            'equipment': [{
                'source_trait': item['source_trait'], 'relationship': item['relationship'],
                'visible_count': item['visible_count'], 'subject_side': item['subject_side'],
            }],
            'forbidden_substitutions': [],
        },
    }
    return validate(brief)
