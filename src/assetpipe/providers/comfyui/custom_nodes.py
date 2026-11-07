"""Preflight for repository-provided ComfyUI custom nodes a workflow declares it needs.

A workflow JSON may list ``required_custom_nodes`` entries ``{"class": ..., "source": ...}``. Before
any generation the live ComfyUI must expose each class, and the node's published
``source_sha256=`` (the hash of the code ComfyUI loaded) must equal the repository source file.
A missing node or a stale copy (not reinstalled, or not restarted after reinstall) blocks the run.
"""
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import quote

_HASH = re.compile(r'source_sha256=([0-9a-f]{64})')


def requirements(root, workflow_name):
    path = Path(root) / 'config/workflows' / f'{workflow_name}.json'
    if not path.is_file():
        return []
    declared = json.loads(path.read_text(encoding='utf-8')).get('required_custom_nodes') or []
    if not isinstance(declared, list) or not all(isinstance(d, dict) and d.get('class') and d.get('source') for d in declared):
        raise ValueError(f'COMFYUI_CUSTOM_NODE_DECLARATION_INVALID: {workflow_name}')
    return declared


def check(fetch_json, root, declared):
    """Return a list of problems; ``fetch_json(path)`` performs a ComfyUI GET and returns parsed JSON."""
    problems = []
    for item in declared:
        source = (Path(root) / item['source']).resolve()
        if not source.is_relative_to(Path(root).resolve()) or not source.is_file():
            problems.append({'class': item['class'], 'code': 'COMFYUI_CUSTOM_NODE_SOURCE_MISSING', 'source': item['source']})
            continue
        expected = hashlib.sha256(source.read_bytes()).hexdigest()
        try:
            info = fetch_json('/object_info/' + quote(item['class'], safe='')) or {}
        except Exception as exc:  # unreachable server is reported, not retried
            problems.append({'class': item['class'], 'code': 'COMFYUI_CUSTOM_NODE_QUERY_FAILED', 'detail': str(exc)})
            continue
        node = info.get(item['class'])
        if not node:
            problems.append({'class': item['class'], 'code': 'COMFYUI_CUSTOM_NODE_MISSING', 'expected_sha256': expected})
            continue
        match = _HASH.search(node.get('description') or '')
        loaded = match.group(1) if match else None
        if loaded != expected:
            problems.append({'class': item['class'], 'code': 'COMFYUI_CUSTOM_NODE_STALE',
                             'loaded_sha256': loaded, 'expected_sha256': expected})
    return problems


def require(fetch_json, root, workflow_name):
    problems = check(fetch_json, root, requirements(root, workflow_name))
    if problems:
        hint = 'install or update with scripts/install_comfyui_dora.py and restart ComfyUI'
        raise RuntimeError(f"{problems[0]['code']}: {json.dumps(problems)}; {hint}")
