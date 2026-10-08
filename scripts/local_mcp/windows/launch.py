"""Host-local launcher for the pinned Asset Pipeline MCP runtime."""
from pathlib import Path
import os
import sys

home = Path(__file__).resolve().parent
runtime = home / (home / 'revision.txt').read_text(encoding='utf-8').strip()
paths = [str(runtime / 'src'), str(runtime)]
sys.path[:0] = paths
os.environ['PYTHONPATH'] = os.pathsep.join(paths)
os.chdir(runtime)
sys.argv = ['assetpipe-mcp', '--config', str(home / 'adapter.yaml')]
from integrations.mcp.server import main
main()
