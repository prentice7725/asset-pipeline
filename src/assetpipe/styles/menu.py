"""User-selected operational style menu binding; never executes or falls back."""
import copy
from pathlib import Path
import yaml


def bind_menu(brief, root, registry=None):
    result = copy.deepcopy(brief)
    if root is None:
        if result.get('art_style'):
            raise ValueError('Style menu requires configuration root')
        return result, None
    root = Path(root).resolve()
    project = result.get('project_id', 'default')
    from .project import project_sot
    sot, sot_path = project_sot(result, root)
    if not isinstance(sot, dict):
        raise ValueError('Visual SOT must be a mapping')
    asset_bindings = sot.get('asset_model_bindings', {})
    if not isinstance(asset_bindings, dict):
        raise ValueError('Visual SOT asset_model_bindings must be a mapping')
    asset_binding = asset_bindings.get(result['asset_id'], {})
    if not isinstance(asset_binding, dict) or set(asset_binding) - {'model_profile', 'workflow_id', 'hard_model_prohibition'}:
        raise ValueError('Visual SOT asset model binding invalid')
    sot = {**sot, **asset_binding}
    if (sot.get('workflow_id') or sot.get('model_profile')) and not sot.get('source'):
        raise ValueError('Visual SOT model binding requires project source location')
    locked = sot.get('art_style')
    requested = result.get('art_style')
    if locked and not sot.get('source'):
        raise ValueError('Visual SOT requires project source location')
    if locked and requested and locked != requested:
        raise ValueError('Visual SOT art_style lock conflicts with requested style')
    slug = locked or requested
    if not slug:
        return result, None
    if result['output_class'] != 'NONPIXEL_IMAGE':
        raise ValueError('Style menu supports NONPIXEL_IMAGE only')
    data = yaml.safe_load((root / 'config/styles/style_menu_v1.yaml').read_text(encoding='utf-8'))
    item = data['styles'].get(slug)
    if item is None:
        raise ValueError('Unknown art_style: ' + slug)
    style_id = item['style_id']
    if result.get('style_id') not in (None, style_id) or sot.get('style_id') not in (None, style_id):
        raise ValueError('Style menu conflicts with explicit style_id or Visual SOT style lock')
    if sot.get('style_selection_policy') and result.get('style_selection_policy') not in (None, sot['style_selection_policy']):
        raise ValueError('Visual SOT selection policy lock conflicts with requested policy')
    policy = result.get('style_selection_policy') or sot.get('style_selection_policy')
    model = item['primary_model']
    if model == 'unresolved':
        model = item['selection_policy'].get(policy)
        if not model:
            raise ValueError('Unresolved style requires style_selection_policy')
    elif policy:
        raise ValueError('Purpose selection policy only applies to unresolved styles')
    binding = item['bindings'][model]
    original = copy.deepcopy(binding)
    menu_original = copy.deepcopy(binding)
    override = result.get('override_mode')
    approval_evidence, failures = None, []
    selection_source = None
    executor = None
    if override or sot.get('model_profile') or sot.get('workflow_id'):
        from ..registry import load_registry
        from .overrides import authorize_override, executor_context
        registry = registry if registry is not None else load_registry(root)
        if sot.get('model_profile') or sot.get('workflow_id'):
            default_workflow = registry.get(sot.get('workflow_id'))
            if default_workflow is None and not sot.get('workflow_id'):
                defaults = [wf for wf in registry.values() if wf.get('model_profile') == sot.get('model_profile') and wf['output_class'] == 'NONPIXEL_IMAGE']
                default_workflow = defaults[0] if len(defaults) == 1 else None
            original = {'workflow_id': sot.get('workflow_id') or (default_workflow or {}).get('id'),
                        'model_profile': sot.get('model_profile') or (default_workflow or {}).get('model_profile'),
                        'source': 'PROJECT_SOT_MODEL_BINDING'}
        if override:
            approval_evidence, failures = authorize_override(result, root, style_id, original.get('workflow_id'))
            requested_workflow = result.get('workflow_override')
            requested_model = result.get('model_override')
            if sot.get('hard_model_prohibition') is True:
                if approval_evidence['record'].get('sot_exception_source') != sot.get('source') or approval_evidence['record'].get('sot_exception_approved') is not True:
                    raise ValueError('SOT_BINDING_CONFLICT: explicit SOT exception approval required')
            selection_source = 'USER_OVERRIDE' if override == 'USER_MANUAL' else 'APPROVED_SUBJECT_RESCUE'
            executor = executor_context(result)
        else:
            requested_workflow, requested_model = sot.get('workflow_id'), sot.get('model_profile')
            selection_source = 'PROJECT_SOT_MODEL_BINDING'
        # Registry IDs are workflow names. Accepting one as a model silently
        # would confuse model families and execution paths: fail explicitly.
        if requested_model in registry:
            raise ValueError('MODEL_OVERRIDE_IS_WORKFLOW_ALIAS: use workflow_override; model_profile is ' + str(registry[requested_model].get('model_profile')))
        if requested_workflow:
            selected = registry.get(requested_workflow)
            if not selected:
                raise ValueError('Unknown workflow_override: ' + requested_workflow)
            if requested_model and selected.get('model_profile') != requested_model:
                raise ValueError('Override workflow/model profile mismatch')
        else:
            choices = [wf for wf in registry.values() if wf.get('model_profile') == requested_model and wf['output_class'] == 'NONPIXEL_IMAGE']
            if len(choices) != 1:
                raise ValueError('Model override requires an unambiguous explicit workflow_override')
            selected = choices[0]
        if selected['output_class'] != 'NONPIXEL_IMAGE':
            raise ValueError('Override workflow output class mismatch')
        if override == 'SUBJECT_RESCUE' and (
                sot.get('workflow_id') not in (None, selected['id']) or
                sot.get('model_profile') not in (None, selected['model_profile'])):
            raise ValueError('SOT_BINDING_CONFLICT: project model binding precedes rescue; request USER_MANUAL exception')
        binding = {'workflow_id': selected['id'], 'model_profile': selected['model_profile'],
                   'recipe': 'config/styles/model_recipes.yaml#recipes/' + style_id + '/' + selected['id']}
    project_recipe = sot.get('recipes', {}).get(style_id, {}).get(binding['workflow_id'])
    if project_recipe is not None:
        binding['recipe'] = sot_path.relative_to(root).as_posix() + '#recipes/' + style_id + '/' + binding['workflow_id']
    preferences = result['workflow_preferences']
    if preferences.get('id') not in (None, binding['workflow_id']) or preferences.get('model_profile') not in (None, binding['model_profile']):
        raise ValueError('Explicit workflow/model conflicts with style menu binding')
    if not selection_source and preferences.get('allow_experimental') is False and item['allow_experimental'] and model.startswith('anima_'):
        raise ValueError('Explicit experimental refusal conflicts with Anima menu binding')
    preferences.update(id=binding['workflow_id'], model_profile=binding['model_profile'])
    if not selection_source and model.startswith('anima_'):
        preferences['allow_experimental'] = item['allow_experimental']
    result['style_id'] = style_id
    decision = {'art_style': slug, 'style_id': style_id, 'primary_model': model,
                'selection_policy': policy, 'recipe': binding['recipe'],
                'known_limitations': item['known_limitations'], 'review_state': item['review_state'],
                'fallback_policy': 'NONE_AUTOMATIC', 'exemplar': item['exemplar'],
                'source': 'PROJECT_VISUAL_SOT' if locked else 'USER_SELECTED_STYLE_MENU'}
    if project_recipe is not None:
        decision['source_file'] = 'config/styles/style_menu_v1.yaml'
        decision['menu_candidate_id'] = item.get('exemplar', {}).get('candidate_id')
    if selection_source:
        decision['binding_source'] = selection_source
        decision['original_binding'] = original
        decision['selected_binding'] = binding
    if override:
        decision['override'] = {
            'route_decision': selection_source, 'project_id': project,
            'sot_reference': sot.get('source'), 'sot_file': sot_path.relative_to(root).as_posix() if sot else None,
            'sot_model_binding': {key: sot[key] for key in ('model_profile', 'workflow_id', 'hard_model_prohibition') if key in sot},
            'art_style': slug, 'style_id': style_id, 'primary_model': model,
            'menu_primary_model': item['primary_model'],
            'menu_original_binding': menu_original,
            'original': original, 'selected': {**binding, 'provider': selected.get('engine', 'comfyui')},
            'executor': executor, 'subject_domain': result.get('subject_domain'),
            'style_lock': True, 'override_mode': override, 'override_reason': result['override_reason'],
            'approval': approval_evidence, 'failure_evidence': failures,
            'generation_state': 'GENERATION_NOT_RUN', 'review_state': 'REVIEW_REQUIRED',
            'semantic_review': 'NOT_VALIDATED', 'composition_review': 'NOT_VALIDATED',
            'style_review': 'NOT_VALIDATED', 'fallback_policy': 'NONE_AUTOMATIC'}
    return result, decision
