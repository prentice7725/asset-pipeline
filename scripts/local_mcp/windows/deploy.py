from pathlib import Path
import zipfile
import yaml

home = Path(__file__).resolve().parent
revision = '12c21092baacfc4c939ebe5eaa1473e063c69551'
runtime = home / revision
runtime.mkdir(exist_ok=True)
with zipfile.ZipFile(home / 'source.zip') as archive:
    for member in archive.infolist():
        if not (runtime / member.filename).resolve().is_relative_to(runtime):
            raise RuntimeError('Unsafe archive path')
    archive.extractall(runtime)
(home / 'adapter.yaml').write_text(yaml.safe_dump({
    'core_root': str(runtime),
    'source_roots': ['C:/workspace'],
    'output_root': 'C:/workspace/asset-pipeline/workspace/plugin_runs',
}), encoding='utf-8')
(home / 'revision.txt').write_text(revision + '\n', encoding='utf-8')
print(runtime)
