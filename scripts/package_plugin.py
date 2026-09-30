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

def validate_package(root=PLUGIN):
    root = Path(root).resolve()
    manifest = json.loads((root / '.codex-plugin/plugin.json').read_text(encoding='utf-8'))
    assert manifest['name'] == 'asset-pipeline'
    assert isinstance(manifest['version'], str) and manifest['description']
    for field in ['skills', 'mcpServers']:
        path = manifest[field]
        assert path.startswith('./') and '..' not in Path(path).parts
        target = (root / path).resolve()
        assert target.is_relative_to(root) and target.exists()
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
    return {'status': 'PASS', 'validation_type': 'LOCAL_COMPATIBILITY_LAYOUT', 'creator_validation': 'NOT_RUN_CREATOR_UNAVAILABLE'}

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
        assert 'asset-pipeline/.codex-plugin/plugin.json' in archive.namelist()
    result.update({'archive': str(destination), 'sha256': hashlib.sha256(destination.read_bytes()).hexdigest(), 'public_submission': False})
    write(output / 'validation.json', result)
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
