"""Resolve source-backed project contracts without applying portrait rules globally."""
import copy
from pathlib import Path
import yaml


# Reference input kinds and the exact fields each one fixes. EXACT_RGBA belongs to classes whose
# delivery masks a uniform backdrop locally (portraits); EXACT_RGB to opaque classes (walls, layers),
# whose edited output is only resized back to the reference canvas when the aspect ratio already matches.
INPUTS = {'EXACT_RGBA': {'reference_input': 'EXACT_RGBA', 'source_background': 'UNIFORM_NEUTRAL'},
          'EXACT_RGB': {'reference_input': 'EXACT_RGB', 'source_background': 'OPAQUE_REFERENCE',
                        'delivery': 'LOCAL_RESIZE_SAME_ASPECT'}}


def _reference_edits(value):
    """Validate explicit editor contracts; keep legacy single-editor SOTs valid."""
    legacy = 'reference_edit_contract' in value
    multiple = 'reference_edit_contracts' in value
    if legacy and multiple:
        raise ValueError('PROJECT_REFERENCE_EDIT_CONTRACT_AMBIGUOUS')
    if not legacy and not multiple:
        return {}
    if legacy:
        item = value['reference_edit_contract']
        if not isinstance(item, dict) or not isinstance(item.get('workflow_id'), str):
            raise ValueError('PROJECT_REFERENCE_EDIT_CONTRACT_INVALID')
        contracts = {item.get('workflow_id'): item}
    else:
        contracts = value['reference_edit_contracts']
    fields = {'workflow_id', 'model_profile', 'reference_input', 'source_background',
              'resolution', 'human_review_required'}
    models = {'grok_imagine': 'grok-imagine', 'codex_imagegen': 'codex-imagegen'}
    if not isinstance(contracts, dict) or not contracts:
        raise ValueError('PROJECT_REFERENCE_EDIT_CONTRACT_INVALID')
    for key, edit in contracts.items():
        fixed = (INPUTS.get(edit['reference_input'])
                 if isinstance(edit, dict) and isinstance(edit.get('reference_input'), str) else None)
        if (key not in models or fixed is None or set(edit) != fields | set(fixed)
                or any(edit[k] != v for k, v in fixed.items())
                or edit['workflow_id'] != key or edit['model_profile'] != models[key]
                or not isinstance(edit['resolution'], list) or len(edit['resolution']) != 2
                or any(type(v) is not int or v <= 0 for v in edit['resolution'])
                or edit['human_review_required'] is not True):
            raise ValueError('PROJECT_REFERENCE_EDIT_CONTRACT_INVALID')
    return contracts


def project_sot(brief, root):
    path = Path(root) / 'config/styles/projects' / brief.get('project_id', 'default') / 'visual_sot.yaml'
    if brief['output_class'] != 'NONPIXEL_IMAGE':
        return {}, path
    if not path.exists():
        if brief.get('project_contract_required'):
            raise ValueError('PROJECT_SOT_UNREGISTERED: ' + brief['project_id'])
        return {}, path
    value = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    if not isinstance(value, dict):
        raise ValueError('Visual SOT must be a mapping')
    scopes = value.get('asset_class_contracts', {})
    if not isinstance(scopes, dict):
        raise ValueError('Visual SOT asset_class_contracts must be a mapping')
    if scopes:
        scope = scopes.get(brief['asset_type'])
        if not isinstance(scope, dict):
            raise ValueError('PROJECT_ASSET_CONTRACT_UNREGISTERED: ' + brief['asset_type'])
        value = {**value, **scope, '_scoped': True}
    if value.get('style_id') and not value.get('source'):
        raise ValueError('Visual SOT requires the project source location')
    value = copy.deepcopy(value)
    edit = _reference_edits(value).get(brief['workflow_preferences'].get('id'))
    if edit is not None:
        if (brief.get('project_contract_required') is True
                and brief['source']['type'] == 'REFERENCE_IMAGE'
                and brief['workflow_preferences'].get('id') == edit['workflow_id']):
            # Every class takes its delivery from its own contract; RGBA edits need the class mask profile.
            masked = edit['reference_input'] == 'EXACT_RGBA'
            if (len(brief['source']['paths']) != 1 or brief['source'].get('references')
                    or brief['constraints']['resolution'] != edit['resolution']
                    or brief['constraints']['transparency'] is not masked
                    or not value.get('source')
                    or bool(value.get('delivery_profile')) is not masked
                    or masked and value['delivery_profile'].get('operation') != 'LOCAL_MASK_UNIFORM_CONTAIN'
                    or not isinstance(value.get('exclusion_policy'), dict)
                    or value['exclusion_policy'].get('mode') != 'POSITIVE_TEXT_INSTRUCTION_REVIEW_REQUIRED'
                    or value['exclusion_policy'].get('human_review_required') is not True):
                raise ValueError('PROJECT_REFERENCE_EDIT_INPUT_CONFLICT')
            value['_reference_edit'] = {**edit, 'style_id': value.get('style_id'),
                                        'base_workflow_id': value.get('workflow_id')}
            value.update(workflow_id=edit['workflow_id'], model_profile=edit['model_profile'])
            if masked:
                value['delivery_profile'].update(workflow_id=edit['workflow_id'], reference_input='EXACT_RGBA',
                                                 source_background_policy=edit['source_background'])
            else:
                value['delivery_profile'] = {'workflow_id': edit['workflow_id'], 'operation': edit['delivery'],
                                             'reference_input': 'EXACT_RGB', 'human_review_required': True}
            value['exclusion_policy']['workflow_id'] = edit['workflow_id']
    return value, path
