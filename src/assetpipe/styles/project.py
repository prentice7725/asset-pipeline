"""Resolve source-backed project contracts without applying portrait rules globally."""
import copy
from pathlib import Path
import yaml


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
        value = {**value, **scope}
    if value.get('style_id') and not value.get('source'):
        raise ValueError('Visual SOT requires the project source location')
    return copy.deepcopy(value), path
