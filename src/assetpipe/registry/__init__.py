from pathlib import Path
import yaml
from .._ported.comfy_bridge.workflow_loader import load_workflow

STATUSES = {'ACTIVE', 'VALIDATED', 'EXPERIMENTAL', 'REJECTED'}
def load_registry(root):
    root = Path(root).resolve()
    value = yaml.safe_load((root / 'config/workflow_registry.yaml').read_text(encoding='utf-8'))
    workflows = value.get('workflows') if isinstance(value, dict) else None
    if not isinstance(workflows, dict) or not workflows:
        raise ValueError('Registry needs a nonempty workflows mapping')
    for key, item in workflows.items():
        if item['status'] not in STATUSES:
            raise ValueError(f'Invalid workflow status: {key}')
        file = (root / item['workflow_file']).resolve()
        if not file.is_relative_to(root / 'config/workflows'):
            raise ValueError(f'Workflow path outside config/workflows: {key}')
        workflow = load_workflow(item['workflow_name'], root / 'config/workflows')
        if workflow.path != file:
            raise ValueError(f'Workflow name/path mismatch: {key}')
        item['hash'] = workflow.sha256
        item['version'] = workflow.version
    return workflows
