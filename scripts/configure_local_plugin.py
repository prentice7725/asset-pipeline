"""Prepare a host-specific plugin copy; never change a running MCP or its engine."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil

DOCS = ['README.md', 'references/AGENT_RECIPE_SELECTION_GUIDE_v1.md',
        'references/STYLE_ROUTING.md', 'references/LOCAL_HOST_SETUP.md',
        'references/ENGINE_RESOURCES.md']
LINK = re.compile(r'\]\(([^)]+)\)')


def files(root):
    result = {}
    for directory, dirs, names in os.walk(root, followlinks=False):
        for name in dirs + names:
            path = Path(directory) / name
            if path.is_symlink() or getattr(path.lstat(), 'st_file_attributes', 0) & 0x400:
                raise ValueError('PLUGIN_REPARSE_POINT_REJECTED')
        for name in names:
            path = Path(directory) / name
            result[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def missing_links(root):
    missing = []
    for file in root.rglob('*.md'):
        for match in LINK.finditer(file.read_text(encoding='utf-8')):
            reference = match[1]
            if reference.startswith(('http://', 'https://', 'mailto:', '#')):
                continue
            target = (file.parent / reference.split('#')[0]).resolve()
            if not target.is_relative_to(root) or not target.is_file():
                missing.append((file.relative_to(root).as_posix(), reference))
    return missing


def prepare(source, output, python, launcher, documentation_root):
    source, output = Path(source).resolve(strict=True), Path(output).resolve()
    python, launcher = Path(python).resolve(strict=True), Path(launcher).resolve(strict=True)
    documentation_root = Path(documentation_root).resolve(strict=True)
    if not python.is_file() or not launcher.is_file() or output == source or source in output.parents:
        raise ValueError('PLUGIN_INSTALL_PATH_INVALID')
    original = files(source)
    manifest = json.loads((source / '.codex-plugin/plugin.json').read_text(encoding='utf-8'))
    if manifest.get('name') != 'asset-pipeline':
        raise ValueError('PLUGIN_IDENTITY_MISMATCH')
    wiring = json.loads((source / '.mcp.json').read_text(encoding='utf-8'))
    if set(wiring.get('mcpServers', {})) != {'asset_pipeline'}:
        raise ValueError('PLUGIN_SERVER_CONTRACT_MISMATCH')
    shutil.copytree(source, output)  # Existing candidate is never overwritten.
    for name in DOCS:
        destination = output / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(documentation_root / name, destination)
    # Historical notes may have been flattened into references/ by a local package.
    # Repair only when the original named document is actually bundled; no placeholders.
    for file in output.rglob('*.md'):
        def repair(match):
            reference = match[1]
            if reference.startswith(('http://', 'https://', 'mailto:', '#')):
                return match[0]
            target = (file.parent / reference.split('#')[0]).resolve()
            if target.is_relative_to(output) and target.is_file():
                return match[0]
            actual = output / 'references' / Path(reference.split('#')[0]).name
            if actual.is_file():
                fragment = '#' + reference.split('#', 1)[1] if '#' in reference else ''
                return '](' + Path(os.path.relpath(actual, file.parent)).as_posix() + fragment + ')'
            return match[0]
        original_text = file.read_text(encoding='utf-8')
        text = LINK.sub(repair, original_text)
        if text != original_text:
            file.write_text(text, encoding='utf-8')
    missing = missing_links(output)
    if missing:
        raise ValueError('PLUGIN_BROKEN_REFERENCES: ' + repr(missing))
    wiring['mcpServers']['asset_pipeline'] = {'command': str(python), 'args': ['-B', str(launcher)]}
    (output / '.mcp.json').write_text(json.dumps(wiring, indent=2) + '\n', encoding='utf-8')
    return {'source': str(source), 'candidate': str(output), 'source_hashes': original,
            'candidate_hashes': files(output), 'wiring': wiring, 'broken_links': 0,
            'restart': 'NOT_RUN', 'generation': 'NOT_RUN', 'creator_validation': 'NOT_RUN'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['source', 'output', 'python', 'launcher']:
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--documentation-root', type=Path, default=Path(__file__).resolve().parents[1] / 'plugin')
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    report = prepare(args.source, args.output, args.python, args.launcher, args.documentation_root)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'candidate': report['candidate'], 'broken_links': 0, 'installed': False}))


if __name__ == '__main__':
    main()
