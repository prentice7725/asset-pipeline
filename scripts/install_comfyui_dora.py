"""Install or update the assetpipe ai-toolkit DoRA node into a local ComfyUI, then optionally restart.

    .venv/Scripts/python scripts/install_comfyui_dora.py --comfyui-root <ComfyUI folder with custom_nodes> [--update] [--restart]

The node is copied byte for byte (no edits). An existing different copy is replaced only with --update,
and the old file is kept next to it as __init__.py.replaced-<sha8>. --restart asks ComfyUI-Manager to
reboot and then waits until ComfyUI reports the repository hash (the same check `create` runs);
without --restart the result says a restart is still required.
"""
import argparse
import hashlib
import json
import shutil
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from assetpipe.providers.comfyui.custom_nodes import check  # noqa: E402

SOURCE = 'integrations/comfyui_dora/__init__.py'
CLASS = 'AssetpipeAIToolkitDoRALoader'
FOLDER = 'assetpipe_aitoolkit_dora'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fetcher(base_url):
    def fetch(path):
        with urllib.request.urlopen(base_url + '/api' + path, timeout=5) as response:
            return json.loads(response.read())
    return fetch


def install(comfyui_root, update):
    custom_nodes = Path(comfyui_root) / 'custom_nodes'
    if not custom_nodes.is_dir():
        raise SystemExit(f'COMFYUI_CUSTOM_NODES_NOT_FOUND: {custom_nodes}')
    source = ROOT / SOURCE
    target = custom_nodes / FOLDER / '__init__.py'
    expected = sha(source)
    if target.is_file():
        current = sha(target)
        if current == expected:
            return {'install': 'UP_TO_DATE', 'target': str(target), 'sha256': expected}
        if not update:
            raise SystemExit(f'COMFYUI_DORA_INSTALLED_COPY_DIFFERS: {target} ({current[:8]}); rerun with --update')
        backup = target.with_name(f'__init__.py.replaced-{current[:8]}')
        if not backup.exists():
            shutil.copy2(target, backup)
        shutil.copyfile(source, target)
        return {'install': 'UPDATED', 'target': str(target), 'sha256': expected, 'previous_sha256': current, 'backup': str(backup)}
    target.parent.mkdir(exist_ok=True)
    shutil.copyfile(source, target)
    return {'install': 'INSTALLED', 'target': str(target), 'sha256': expected}


def restart(base_url, timeout):
    request = urllib.request.Request(base_url + '/api/v2/manager/reboot', data=b'{}', method='POST',
                                     headers={'Content-Type': 'application/json'})
    try:
        urllib.request.urlopen(request, timeout=10)
    except Exception:  # the server drops the connection while rebooting
        pass
    declared = [{'class': CLASS, 'source': SOURCE}]
    deadline = time.time() + timeout
    problems = None
    time.sleep(5)
    while time.time() < deadline:
        problems = check(fetcher(base_url), ROOT, declared)
        if not problems:
            return {'restart': 'VERIFIED_LOADED'}
        time.sleep(3)
    return {'restart': 'NOT_VERIFIED', 'problems': problems}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--comfyui-root', required=True, type=Path)
    parser.add_argument('--update', action='store_true')
    parser.add_argument('--restart', action='store_true')
    parser.add_argument('--base-url', default='http://127.0.0.1:8188')
    parser.add_argument('--timeout', type=float, default=240)
    args = parser.parse_args()
    result = install(args.comfyui_root, args.update)
    if args.restart:
        result.update(restart(args.base_url, args.timeout))
    else:
        problems = check(fetcher(args.base_url), ROOT, [{'class': CLASS, 'source': SOURCE}])
        result['loaded'] = 'MATCHES_REPOSITORY' if not problems else 'RESTART_REQUIRED'
        if problems:
            result['problems'] = problems
    print(json.dumps(result, indent=1))
    if result.get('restart') == 'NOT_VERIFIED':
        sys.exit(1)


if __name__ == '__main__':
    main()
