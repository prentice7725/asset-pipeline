from ..brief import validate

def route(brief, registry):
    validate(brief)
    preferences = brief['workflow_preferences']
    requested = preferences.get('id')
    tags = set(preferences.get('tags', [])) | {brief['asset_type']}
    reusable_motion = bool(brief.get('production', {}).get('motion_reference'))
    required = []
    if not reusable_motion:
        required.append('text_to_audio' if brief['output_class'] == 'SFX' else 'character_reference' if brief['source']['type'] == 'REFERENCE_IMAGE' else 'text_to_image')
    if brief['output_class'] == 'SFX' and brief['source']['type'] == 'REFERENCE_IMAGE':
        raise ValueError('SFX workflow supports text only')
    if brief['constraints']['transparency'] is True and brief['output_class'] == 'NONPIXEL_IMAGE':
        required.append('transparent_output')
    spec = brief.get('prompt_spec', {})
    if spec.get('textInImage'):
        required.append('text_rendering')
    if (brief.get('negative_prompt') or brief['forbidden_elements'] or spec.get('negative')) and brief['output_class'] in {'NONPIXEL_IMAGE', 'PIXEL_STATIC', 'SFX'}:
        required.append('negative_prompt')
    candidates = []
    rejections = {}
    for key, item in registry.items():
        reason = None
        if item['output_class'] != brief['output_class']:
            reason = 'output_class mismatch'
        elif any(not item['capabilities'].get(cap) for cap in required):
            reason = 'required capabilities unavailable: ' + ', '.join(required)
        elif item['status'] == 'REJECTED':
            reason = 'REJECTED workflow'
        elif item['status'] != 'ACTIVE' and key != requested:
            reason = 'automatic routing requires ACTIVE'
        elif item['status'] == 'EXPERIMENTAL' and not preferences.get('allow_experimental'):
            reason = 'EXPERIMENTAL requires explicit opt-in'
        if reason:
            rejections[key] = reason
        else:
            matching = sorted(tags & set(item['tags']))
            candidates.append((key, item, matching))
    if not candidates or (requested and not any(row[0] == requested for row in candidates)):
        raise ValueError(f'No compatible workflow: {rejections.get(requested, rejections)}')
    candidates.sort(key=lambda row: (0 if row[0] == requested else 1, -len(row[2]), -row[1].get('priority', 0), row[0]))
    key, item, matching = candidates[0]
    return {'selected_workflow': key, 'output_class': brief['output_class'], 'matching_tags': matching,
        'selection_reason': 'explicit compatible workflow' if requested else 'ACTIVE capability match, tags, priority',
        'fallback_candidates': [row[0] for row in candidates[1:]], 'rejected_candidates': rejections,
        'execution_mode': 'REUSE_MOTION_REFERENCE' if reusable_motion else 'GENERATE', 'required_capabilities': required}
