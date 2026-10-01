"""Build a local plugin ZIP only after real M0 MCP smokes have passed."""
from pathlib import Path
import hashlib
import json
import re
import zipfile
from jsonschema import Draft202012Validator
from assetpipe.manifests import write

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugin'
TOOLS = {'asset_capabilities', 'asset_build_brief', 'asset_route', 'asset_generate', 'asset_continue_animation', 'asset_inspect_run'}
# 호스트별 매니페스트. 두 호스트 모두 같은 skills/와 .mcp.json을 공유한다.
MANIFESTS = {'codex': '.codex-plugin/plugin.json', 'claude_code': '.claude-plugin/plugin.json'}
MARKETPLACE = ROOT / '.claude-plugin/marketplace.json'

def _validate_manifest(root, relative):
    manifest = json.loads((root / relative).read_text(encoding='utf-8'))
    assert manifest['name'] == 'asset-pipeline'
    assert isinstance(manifest['version'], str) and manifest['description']
    for field in ['skills', 'mcpServers']:
        path = manifest[field]
        assert path.startswith('./') and '..' not in Path(path).parts
        target = (root / path).resolve()
        assert target.is_relative_to(root) and target.exists()
    return manifest

def _validate_marketplace(root, version):
    # Claude Code 마켓플레이스 항목이 이 플러그인 폴더와 버전을 가리키는지 확인한다.
    if root != PLUGIN.resolve():
        return
    marketplace = json.loads(MARKETPLACE.read_text(encoding='utf-8'))
    entries = [p for p in marketplace['plugins'] if p['name'] == 'asset-pipeline']
    assert len(entries) == 1
    assert (ROOT / entries[0]['source']).resolve() == root
    assert entries[0].get('version', version) == version

def validate_package(root=PLUGIN):
    root = Path(root).resolve()
    manifests = {host: _validate_manifest(root, path) for host, path in MANIFESTS.items()}
    manifest = manifests['codex']
    # 호스트 간 이름·버전·공유 경로가 어긋나지 않도록 고정한다.
    for other in manifests.values():
        assert {k: other[k] for k in ['name', 'version', 'skills', 'mcpServers']} == {k: manifest[k] for k in ['name', 'version', 'skills', 'mcpServers']}
    _validate_marketplace(root, manifest['version'])
    mcp = json.loads((root / manifest['mcpServers']).read_text(encoding='utf-8'))
    assert set(mcp['mcpServers']) == {'asset_pipeline'}
    wiring = mcp['mcpServers']['asset_pipeline']
    assert wiring == {'command': 'assetpipe-mcp', 'args': []}
    for skill in (root / manifest['skills']).glob('*/SKILL.md'):
        text = skill.read_text(encoding='utf-8')
        assert text.startswith('---\n')
        for link in re.findall(r'\]\(([^)]+)\)', text):
            target = (skill.parent / link).resolve()
            assert target.is_relative_to(root) and target.is_file(), link
    assert not list(root.rglob('*.py')), 'Production/adapter code must not be copied into plugin'
    assert not any(p.suffix.lower() in {'.png', '.mp4', '.aseprite'} for p in root.rglob('*'))
    return {'status': 'PASS', 'validation_type': 'LOCAL_COMPATIBILITY_LAYOUT', 'hosts': sorted(MANIFESTS), 'creator_validation': 'NOT_RUN_CREATOR_UNAVAILABLE'}

def main():
    pointer = json.loads((ROOT / 'workspace/plugin_m0/latest.json').read_text(encoding='utf-8'))
    evidence = json.loads(Path(pointer['report']).read_text(encoding='utf-8'))
    assert set(evidence['smokes']) == {'A', 'B', 'C', 'D'}
    assert all(item['status'] == 'PASS' for item in evidence['smokes'].values())
    schemas = list((ROOT / 'integrations/mcp/schemas').glob('*.json'))
    assert {p.stem for p in schemas} == TOOLS
    for path in schemas:
        Draft202012Validator.check_schema(json.loads(path.read_text(encoding='utf-8')))
    result = validate_package()
    output = ROOT / 'workspace/plugin_m0/package'
    output.mkdir(parents=True, exist_ok=True)
    destination = output / 'asset-pipeline-plugin-m0.zip'
    with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(PLUGIN.rglob('*')):
            if path.is_file():
                archive.write(path, 'asset-pipeline/' + path.relative_to(PLUGIN).as_posix())
    with zipfile.ZipFile(destination) as archive:
        assert all(name.startswith('asset-pipeline/') for name in archive.namelist())
        for relative in MANIFESTS.values():
            assert f'asset-pipeline/{relative}' in archive.namelist()
    result.update({'archive': str(destination), 'sha256': hashlib.sha256(destination.read_bytes()).hexdigest(), 'public_submission': False})
    write(output / 'validation.json', result)
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
