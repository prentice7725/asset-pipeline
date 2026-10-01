import hashlib
import json
from pathlib import Path
import yaml
from .._ported.comfy_bridge.workflow_loader import load_workflow

STATUSES = {'ACTIVE', 'VALIDATED', 'EXPERIMENTAL', 'REJECTED'}
CLI_ENGINES = {'codex_cli', 'grok_cli'}
CLI_TOOLS = {'codex_cli': {'image_gen'}, 'grok_cli': {'image_gen', 'image_edit'}}
AUTH_MODES = {'codex_cli': {'cli_login'}, 'grok_cli': {'cli_login', 'env_api_key'}}
# 격리·승인 정책을 약화시키는 인자는 registry에서 지정할 수 없다.
FORBIDDEN_CLI_ARGS = {'--always-approve', '--dangerously-bypass-approvals-and-sandbox', '--dangerously-bypass-hook-trust', '--yolo',
    '--full-auto', '-c', '--config', '--profile', '-C', '--cd', '--cwd', '--add-dir', '--worktree', '-w', '-s', '--sandbox',
    '--tools', '--prompt-file', '--prompt-json', '-p', '--single', '--output-format', '-o', '--output-last-message'}
FORBIDDEN_CLI_VALUES = {'danger-full-access', 'bypassPermissions'}
ENV_NAME_PATTERN = r'^[A-Z][A-Z0-9_]{0,63}$'

class WorkflowRegistry(dict):
    """Retains the config root without adding keys to the workflow contract."""
    def __init__(self, values, root):
        super().__init__(values)
        self.root = root

def _validate_cli_args(key, args):
    if not isinstance(args, list) or any(not isinstance(a, str) for a in args):
        raise ValueError(f'backend.cli_args must be a list of strings: {key}')
    for arg in args:
        name, _, value = arg.partition('=')
        if name in FORBIDDEN_CLI_ARGS or arg in FORBIDDEN_CLI_VALUES or value in FORBIDDEN_CLI_VALUES:
            raise ValueError(f'backend.cli_args contains a forbidden isolation/approval option ({arg}): {key}')

def _normalize_cli_entry(key, item, root, registry_version):
    import re
    engine = item['engine']
    if item.get('workflow_file') or item.get('workflow_name'):
        raise ValueError(f'CLI provider entries must not declare a ComfyUI workflow: {key}')
    if item['output_class'] != 'NONPIXEL_IMAGE':
        raise ValueError(f'CLI provider entries support NONPIXEL_IMAGE only: {key}')
    if item.get('selection') not in (None, 'explicit_only'):
        raise ValueError(f'Invalid selection mode: {key}')
    raw = item.get('backend')
    if not isinstance(raw, dict):
        raise ValueError(f'CLI provider entries require a backend mapping: {key}')
    backend = dict(raw)
    backend.setdefault('tool', 'image_gen')
    if engine == 'grok_cli':
        backend.setdefault('edit_tool', 'image_edit')
    for field in ('tool', 'edit_tool'):
        if field in backend and backend[field] not in CLI_TOOLS[engine]:
            raise ValueError(f'Unsupported backend.{field} for {engine}: {key}')
    model = backend.setdefault('model', None)
    if model is not None and not isinstance(model, str):
        raise ValueError(f'backend.model must be a string or null: {key}')
    timeout = backend.setdefault('timeout_seconds', 600)
    if type(timeout) is not int or not 10 <= timeout <= 3600:
        raise ValueError(f'backend.timeout_seconds must be an integer between 10 and 3600: {key}')
    outputs = backend.setdefault('max_outputs', 1)
    if type(outputs) is not int or not 1 <= outputs <= 4:
        raise ValueError(f'backend.max_outputs must be an integer between 1 and 4: {key}')
    auth = backend.setdefault('auth', {'mode': 'cli_login', 'env': []})
    if not isinstance(auth, dict) or auth.get('mode', 'cli_login') not in AUTH_MODES[engine]:
        raise ValueError(f'Unsupported backend.auth.mode for {engine}: {key}')
    auth.setdefault('mode', 'cli_login')
    auth.setdefault('env', [])
    if not isinstance(auth['env'], list) or any(not isinstance(n, str) or not re.fullmatch(ENV_NAME_PATTERN, n) for n in auth['env']):
        raise ValueError(f'backend.auth.env must list environment variable names only: {key}')
    if auth['mode'] == 'cli_login' and auth['env']:
        raise ValueError(f'backend.auth.env is only valid with env_api_key: {key}')
    _validate_cli_args(key, backend.setdefault('cli_args', []))
    item['backend'] = backend
    item.setdefault('models', {})
    item['version'] = item.get('version') or registry_version
    item['hash'] = hashlib.sha256(json.dumps({'engine': engine, 'backend': backend, 'capabilities': item.get('capabilities', {})}, sort_keys=True).encode('utf-8')).hexdigest()
    # 실제 생성이 검증되지 않은 provider는 자동 라우팅 대상(ACTIVE)이 될 수 없다.
    if item['status'] == 'ACTIVE':
        validation = item.get('validation') or {}
        evidence = validation.get('evidence')
        verified = False
        if validation.get('status') == 'REAL_GENERATION_VERIFIED' and isinstance(evidence, str) and (root / evidence).is_file():
            try:
                record = json.loads((root / evidence).read_text(encoding='utf-8'))
                verified = record.get('provider_id') == key and record.get('result') == 'REAL_GENERATION_VERIFIED'
            except ValueError:
                verified = False
        if not verified:
            raise ValueError(f'CLI provider cannot be ACTIVE without real-generation evidence: {key}')

def load_registry(root):
    root = Path(root).resolve()
    value = yaml.safe_load((root / 'config/workflow_registry.yaml').read_text(encoding='utf-8'))
    workflows = value.get('workflows') if isinstance(value, dict) else None
    if not isinstance(workflows, dict) or not workflows:
        raise ValueError('Registry needs a nonempty workflows mapping')
    for key, item in workflows.items():
        if item['status'] not in STATUSES:
            raise ValueError(f'Invalid workflow status: {key}')
        engine = item.get('engine', 'comfyui')
        item['id'] = key
        if engine in CLI_ENGINES:
            _normalize_cli_entry(key, item, root, value.get('registry_version'))
            continue
        if engine != 'comfyui':
            raise ValueError(f'Unsupported engine: {key}')
        file = (root / item['workflow_file']).resolve()
        if not file.is_relative_to(root / 'config/workflows'):
            raise ValueError(f'Workflow path outside config/workflows: {key}')
        workflow = load_workflow(item['workflow_name'], root / 'config/workflows')
        if workflow.path != file:
            raise ValueError(f'Workflow name/path mismatch: {key}')
        item['hash'] = workflow.sha256
        item['version'] = workflow.version
        # 기존 평면 키를 엔진별 backend 구조로도 노출한다. 기존 키는 그대로 유지한다.
        item.setdefault('backend', {'workflow_file': item['workflow_file'], 'workflow_name': item['workflow_name']})
    return WorkflowRegistry(workflows, root)
