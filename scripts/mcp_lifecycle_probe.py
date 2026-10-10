"""Inspect only a newly owned MCP stdio process; close stdin, never kill it."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

import yaml


def main():
    root = Path(__file__).resolve().parents[1]
    temporary = tempfile.mkdtemp(prefix='assetpipe_lifecycle_')
    config = Path(temporary) / 'adapter.yaml'
    config.write_text(yaml.safe_dump({'core_root': str(root), 'source_roots': [str(root / 'examples')],
        'output_root': str(Path(temporary) / 'outputs')}), encoding='utf-8')
    command = [sys.executable, '-m', 'integrations.mcp.server', '--config', str(config)]
    child = subprocess.Popen(command, cwd=root, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    report = {'probe_pid': child.pid, 'owner_pid': os.getpid(), 'command': command, 'terminated_processes': []}
    if os.name == 'nt':
        query = ('$rows = Get-CimInstance Win32_Process; '
                 '$rows | Where-Object { $_.ProcessId -eq $env:ASSETPIPE_PROBE_PID -or '
                 '$_.ParentProcessId -eq $env:ASSETPIPE_PROBE_PID -or $_.ProcessId -eq $env:ASSETPIPE_OWNER_PID } | '
                 'Select-Object ProcessId,ParentProcessId,CreationDate,SessionId,Name,CommandLine | ConvertTo-Json')
        metadata = subprocess.run(['powershell', '-NoProfile', '-Command', query], capture_output=True, text=True,
            env={**os.environ, 'ASSETPIPE_PROBE_PID': str(child.pid), 'ASSETPIPE_OWNER_PID': str(os.getpid())}, timeout=10)
        report['process_metadata'] = json.loads(metadata.stdout) if metadata.returncode == 0 and metadata.stdout.strip() else metadata.stderr
    messages = [
        {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2024-11-05',
            'capabilities': {}, 'clientInfo': {'name': 'assetpipe-owned-lifecycle-probe', 'version': '1'}}},
        {'jsonrpc': '2.0', 'method': 'notifications/initialized'},
        {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list', 'params': {}},
    ]
    started = time.monotonic()
    try:
        out, err = child.communicate(('\n'.join(json.dumps(m) for m in messages) + '\n').encode(), timeout=15)
        report.update(exit_code=child.returncode, stdout=out.decode(errors='replace'), stderr=err.decode(errors='replace'),
            shutdown='OBSERVED_EXIT_AFTER_STDIN_EOF', seconds=round(time.monotonic() - started, 3))
    except subprocess.TimeoutExpired:
        report.update(shutdown='NOT_OBSERVED_WITHIN_15_SECONDS', still_active=child.poll() is None)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
