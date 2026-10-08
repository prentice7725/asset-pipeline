from pathlib import Path
import re
import tomllib

path = Path.home() / '.codex/config.toml'
text = path.read_text(encoding='utf-8')
pattern = r'(\[mcp_servers\.asset_pipeline\]\n)(.*?)(?=\n\[|\Z)'
match = re.search(pattern, text, re.S)
if match is None:
    raise RuntimeError('Registered MCP entry not found')
body = match.group(2)
for key in ['startup_timeout_sec', 'tool_timeout_sec']:
    body = re.sub(rf'^{key}\s*=.*\n?', '', body, flags=re.M)
body = body.rstrip() + '\nstartup_timeout_sec = 30\ntool_timeout_sec = 120\n'
updated = text[:match.start(2)] + body + text[match.end(2):]
tomllib.loads(updated)
path.write_text(updated, encoding='utf-8')
print('Asset Pipeline timeouts configured; TOML parse PASS')
