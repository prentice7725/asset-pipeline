from ..brief import validate

def satisfied(capabilities, capability):
    # negative_prompt는 네이티브 지원이고, negative_prompt_instruction은 자연어 금지 지시다.
    # 자연어 지시는 보장되지 않는 방식이므로 둘을 구분해 기록하되 라우팅에서는 둘 중 하나면 충족으로 본다.
    if capability == 'negative_prompt':
        return bool(capabilities.get('negative_prompt') or capabilities.get('negative_prompt_instruction'))
    return bool(capabilities.get(capability))

def route(brief, registry, root=None):
    validate(brief)
    from ..styles import resolve_style, select_recipe, public_selection
    root = root or getattr(registry, 'root', None)
    if brief.get('style_id') and root is None:
        raise ValueError('Style routing requires a configuration root')
    style = resolve_style(brief, root) if root is not None else None
    preferences = brief['workflow_preferences']
    requested = preferences.get('id')
    model = preferences.get('model_profile')
    explicit_ids = {key for key, item in registry.items() if (key == requested if requested else model and item.get('model_profile') == model)}
    if requested and model and registry.get(requested, {}).get('model_profile') != model:
        raise ValueError('Explicit workflow conflicts with requested model_profile')
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
    if brief['constraints']['resolution'] and brief['output_class'] == 'NONPIXEL_IMAGE':
        # 정확한 해상도를 보장하지 못하는 provider로 보내면 과금 후 QA에서 반드시 실패하므로 미리 차단한다.
        required.append('exact_resolution')
    candidates = []
    rejections = {}
    recipes = {}
    for key, item in registry.items():
        reason = None
        if item['output_class'] != brief['output_class']:
            reason = 'output_class mismatch'
        elif any(not satisfied(item['capabilities'], cap) for cap in required):
            reason = 'required capabilities unavailable: ' + ', '.join(required)
        elif item['status'] == 'REJECTED':
            reason = 'REJECTED workflow'
        elif model and item.get('model_profile') != model:
            reason = 'requested model_profile mismatch'
        elif item.get('selection') == 'explicit_only' and key not in explicit_ids:
            reason = 'explicit_only workflow must be requested by id'
        elif item['status'] != 'ACTIVE' and key not in explicit_ids:
            reason = 'automatic routing requires ACTIVE'
        elif item['status'] == 'EXPERIMENTAL' and not preferences.get('allow_experimental'):
            reason = 'EXPERIMENTAL requires explicit opt-in'
        if reason is None and style:
            try:
                recipes[key] = select_recipe(style, item, root, explicit=key in explicit_ids)
            except ValueError as exc:
                reason = str(exc)
        if reason:
            rejections[key] = reason
        else:
            matching = sorted(tags & set(item['tags']))
            candidates.append((key, item, matching))
    if not candidates or (requested and not any(row[0] == requested for row in candidates)):
        raise ValueError(f'No compatible workflow: {rejections.get(requested, rejections)}')
    candidates.sort(key=lambda row: (0 if row[0] == requested else 1, -len(row[2]), -row[1].get('priority', 0), row[0]))
    key, item, matching = candidates[0]
    decision = {'selected_workflow': key, 'output_class': brief['output_class'], 'matching_tags': matching,
        'selection_reason': 'explicit compatible workflow' if requested else 'ACTIVE capability match, tags, priority',
        'fallback_candidates': [row[0] for row in candidates[1:]], 'rejected_candidates': rejections,
        'execution_mode': 'REUSE_MOTION_REFERENCE' if reusable_motion else 'GENERATE', 'required_capabilities': required}
    if style:
        decision['style_selection'] = public_selection(recipes[key])
        decision['selection_reason'] = recipes[key]['reason'] + '; style priority: Visual SOT > approved project Style Pack > common catalog > model defaults'
    return decision
