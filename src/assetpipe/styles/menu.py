"""User-selected operational style menu binding; never executes or falls back."""
import copy
from pathlib import Path
import yaml


def bind_menu(brief, root):
    result = copy.deepcopy(brief)
    if root is None:
        if result.get('art_style'):
            raise ValueError('Style menu requires configuration root')
        return result, None
    root = Path(root).resolve()
    project = result.get('project_id', 'default')
    sot_path = root / 'config/styles/projects' / project / 'visual_sot.yaml'
    sot = yaml.safe_load(sot_path.read_text(encoding='utf-8')) or {} if sot_path.exists() else {}
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
    preferences = result['workflow_preferences']
    if preferences.get('id') not in (None, binding['workflow_id']) or preferences.get('model_profile') not in (None, binding['model_profile']):
        raise ValueError('Explicit workflow/model conflicts with style menu binding')
    if preferences.get('allow_experimental') is False and item['allow_experimental'] and model.startswith('anima_'):
        raise ValueError('Explicit experimental refusal conflicts with Anima menu binding')
    preferences.update(id=binding['workflow_id'], model_profile=binding['model_profile'])
    if model.startswith('anima_'):
        preferences['allow_experimental'] = item['allow_experimental']
    result['style_id'] = style_id
    decision = {'art_style': slug, 'style_id': style_id, 'primary_model': model,
                'selection_policy': policy, 'recipe': binding['recipe'],
                'known_limitations': item['known_limitations'], 'review_state': item['review_state'],
                'fallback_policy': 'NONE_AUTOMATIC', 'exemplar': item['exemplar'],
                'source': 'PROJECT_VISUAL_SOT' if locked else 'USER_SELECTED_STYLE_MENU'}
    return result, decision
