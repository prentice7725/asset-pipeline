from ..brief import validate
from importlib.metadata import PackageNotFoundError


class RoutingBlocked(ValueError):
    def __init__(self, message, *, required, missing, rejections, style=None, constraints=None, menu=None):
        super().__init__(message)
        self.details = {'required_capabilities': required, 'missing_capabilities': missing,
                        'rejected_candidates': rejections}
        if constraints:
            self.details['constraint_issues'] = constraints
        if style:
            from ..styles import public_selection
            self.details['style_selection'] = public_selection(style)
        if menu:
            self.details['style_menu'] = menu

def satisfied(capabilities, capability):
    # negative_prompt는 네이티브 지원이고, negative_prompt_instruction은 자연어 금지 지시다.
    # 자연어 지시는 보장되지 않는 방식이므로 둘을 구분해 기록하되 라우팅에서는 둘 중 하나면 충족으로 본다.
    if capability == 'negative_prompt':
        return bool(capabilities.get('negative_prompt') or capabilities.get('negative_prompt_instruction'))
    return bool(capabilities.get(capability))

def route(brief, registry, root=None):
    validate(brief)
    root = root or getattr(registry, 'root', None)
    from ..styles.menu import bind_menu
    brief, menu_decision = bind_menu(brief, root, registry)
    return _route_bound(brief, registry, root, menu_decision)


def _route_bound(brief, registry, root, menu_decision=None):
    """Shared capability/recipe checks for already bound Briefs and offline plans."""
    from ..styles import resolve_style, select_recipe, public_selection
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
    subject_spec = None
    if spec.get('subject_integrity') or spec.get('art_direction'):
        from ..prompts import from_brief
        subject_spec = from_brief(brief)
    if spec.get('textInImage'):
        required.append('text_rendering')
    if (brief.get('negative_prompt') or brief['forbidden_elements'] or spec.get('negative')) and brief['output_class'] in {'NONPIXEL_IMAGE', 'PIXEL_STATIC', 'SFX'}:
        required.append('negative_prompt')
    if spec.get('subject_integrity', {}).get('forbidden_substitutions'):
        required.append('native_subject_negative')
    if brief['constraints']['resolution'] and brief['output_class'] == 'NONPIXEL_IMAGE':
        # 정확한 해상도를 보장하지 못하는 provider로 보내면 과금 후 QA에서 반드시 실패하므로 미리 차단한다.
        required.append('exact_resolution')
    candidates = []
    rejections = {}
    missing_by_workflow = {}
    constraints_by_workflow = {}
    recipes = {}
    for key, item in registry.items():
        from ..prompts.exclusion_policy import instruction_review_allowed
        instruction_review = instruction_review_allowed(brief, style, key)
        from ..portrait_delivery import profile, preflight
        delivery = profile(brief, root, key) if root is not None else None
        delivery_error = None
        if delivery:
            try:
                preflight(delivery)
            except (ValueError, OSError, PackageNotFoundError) as exc:
                delivery_error = str(exc)
        unavailable = [cap for cap in required if not (item['capabilities'].get('negative_prompt')
                       if cap == 'native_subject_negative' else satisfied(item['capabilities'], cap))
                       and not (instruction_review and cap in {'negative_prompt', 'native_subject_negative'})
                       and not (delivery and not delivery_error and cap == 'transparent_output')]
        missing_by_workflow[key] = unavailable
        resolution = brief['constraints']['resolution']
        multiple = item.get('delivery_resolution_multiple')
        constraints_by_workflow[key] = []
        if resolution and multiple and any(value % multiple for value in resolution) and not (delivery and not delivery_error):
            constraints_by_workflow[key].append({'code': 'DELIVERY_RESOLUTION_UNSUPPORTED',
                'requested_resolution': resolution, 'required_multiple': multiple,
                'reason': 'Current workflow cannot deliver exact dimensions without a separately validated size conversion'})
        reason = None
        if delivery_error:
            reason = 'PORTRAIT_DELIVERY_UNAVAILABLE: ' + delivery_error
        elif item['output_class'] != brief['output_class']:
            reason = 'output_class mismatch'
        elif unavailable:
            reason = 'required capabilities unavailable: ' + ', '.join(unavailable)
            if constraints_by_workflow[key]:
                reason += '; DELIVERY_RESOLUTION_UNSUPPORTED'
        elif constraints_by_workflow[key]:
            reason = 'DELIVERY_RESOLUTION_UNSUPPORTED: exact dimensions require multiples of ' + str(multiple)
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
        raise RoutingBlocked(f'No compatible workflow: {rejections.get(requested, rejections)}',
                             required=required, missing=missing_by_workflow.get(requested, []),
                             rejections=rejections, style=style, constraints=constraints_by_workflow.get(requested),
                             menu=menu_decision)
    candidates.sort(key=lambda row: (0 if row[0] == requested else 1, -len(row[2]), -row[1].get('priority', 0), row[0]))
    key, item, matching = candidates[0]
    from ..portrait_delivery import profile as delivery_profile
    selected_delivery = delivery_profile(brief, root, key) if root is not None else None
    if subject_spec is not None and root is not None:
        from ..prompts import compile_spec
        from ..styles import apply_style
        selected_style = recipes.get(key)
        compile_spec(brief, item, root, apply_style(subject_spec, selected_style), style_context=selected_style)
    intent = None
    if 'art_direction' in brief:
        from ..art_direction import apply_intent
        from ..prompts import from_brief
        from ..styles import apply_style
        selected_style = recipes.get(key)
        _, intent = apply_intent(brief, apply_style(from_brief(brief), selected_style), selected_style)
    decision = {'selected_workflow': key, 'output_class': brief['output_class'], 'matching_tags': matching,
        'selection_reason': 'explicit compatible workflow' if requested else 'ACTIVE capability match, tags, priority',
        'fallback_candidates': [row[0] for row in candidates[1:]], 'rejected_candidates': rejections,
        'execution_mode': 'REUSE_MOTION_REFERENCE' if reusable_motion else 'GENERATE', 'required_capabilities': required}
    if instruction_review_allowed(brief, style, key):
        decision['exclusion_handling'] = {'mode': 'POSITIVE_TEXT_INSTRUCTION_REVIEW_REQUIRED',
            'native_negative_supported': bool(item['capabilities'].get('negative_prompt')),
            'human_review': 'REVIEW_REQUIRED', 'delivery_ready': False}
    if selected_delivery:
        decision['delivery_handling'] = {'operation': selected_delivery['operation'],
            'native_transparency_supported': bool(item['capabilities'].get('transparent_output')),
            'resolution': brief['constraints']['resolution'], 'human_review': 'REVIEW_REQUIRED'}
    if style:
        decision['style_selection'] = public_selection(recipes[key])
        decision['selection_reason'] = recipes[key]['reason'] + '; style priority: Visual SOT > approved project Style Pack > common catalog > model defaults'
    if intent:
        decision['art_direction'] = intent
    if menu_decision:
        decision['style_menu'] = menu_decision
        decision['fallback_candidates'] = []
        if menu_decision.get('override'):
            decision['override'] = menu_decision['override']
            decision['override']['style_sha256'] = decision['style_selection']['style_sha256']
            decision['override']['recipe'] = decision['style_selection']
            decision['override']['rejected_routes'] = rejections
            decision['selection_reason'] = decision['override']['route_decision'] + '; explicit approved run-scoped override'
    return decision
