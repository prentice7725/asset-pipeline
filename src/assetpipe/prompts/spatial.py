"""Fail-closed mapping of anatomical sides into explicit image coordinates."""
from __future__ import annotations

from .subject_contract import camera_from_source

SIDE_MAP = {
    'front': {'SUBJECT_LEFT': 'IMAGE_RIGHT', 'SUBJECT_RIGHT': 'IMAGE_LEFT'},
    'rear': {'SUBJECT_LEFT': 'IMAGE_LEFT', 'SUBJECT_RIGHT': 'IMAGE_RIGHT'},
}


def compile_spatial_relationships(spec: dict) -> dict:
    integrity = spec.get('subject_integrity', {})
    equipment = integrity.get('equipment', [])
    located = [item for item in equipment if item.get('subject_side')]
    if not located:
        rows = [f"{item['source_trait']} ({item['relationship']}" +
                (f", visible count of {item['visible_count']}" if item.get('visible_count') else '') + ')'
                for item in equipment]
        return {'relationships': rows, 'mappings': []}
    view = integrity.get('camera_view', 'from_source')
    if view == 'from_source':
        view = camera_from_source(spec)
    if view not in SIDE_MAP:
        raise ValueError('SPATIAL_VIEW_UNRESOLVED: anatomical side requires explicit FRONT or REAR view')

    rows, mappings = [], []
    for item in equipment:
        if not item.get('subject_side'):
            rows.append(f"{item['source_trait']} ({item['relationship']}" +
                        (f", visible count of {item['visible_count']}" if item.get('visible_count') else '') + ')')
            continue
        side = item['subject_side']
        if side not in SIDE_MAP[view]:
            raise ValueError('SPATIAL_SIDE_UNSUPPORTED: expected SUBJECT_LEFT or SUBJECT_RIGHT')
        image_side = SIDE_MAP[view][side]
        anatomical = 'left' if side == 'SUBJECT_LEFT' else 'right'
        visible_count = item.get('visible_count')
        count_text = f"visible count of {visible_count}" if visible_count else None
        clauses = [item['relationship']]
        if count_text:
            clauses.append(count_text)
        clauses.append(f"{view.upper()} view maps {side} to {image_side}")
        clauses.append(f"keep it in the subject's anatomical {anatomical} hand at image {image_side.removeprefix('IMAGE_').lower()}")
        rows.append(f"{item['source_trait']} ({'; '.join(clauses)})")
        mappings.append({'source_trait': item['source_trait'], 'camera_view': view.upper(),
                         'subject_side': side, 'image_side': image_side,
                         'relationship': item['relationship'], 'visible_count': visible_count})
    return {'relationships': rows, 'mappings': mappings}
