"""Real Anima/Krea2 comparison from one immutable Brief; never approves styles."""
import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image
from assetpipe.brief import load
from assetpipe.manifests import write
from assetpipe.pipelines import create
from assetpipe.registry import load_registry
from assetpipe.styles import digest
from assetpipe.providers.comfyui import ComfyUIProvider
from assetpipe._ported.config import load_config

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--brief', type=Path, default=ROOT / 'examples/m2_style_compare.yaml')
    parser.add_argument('--seed', type=int, default=7725)
    parser.add_argument('--output', type=Path, default=ROOT / 'workspace/m2/comparisons')
    args = parser.parse_args(argv)
    brief = load(args.brief)
    if not brief.get('style_id') or brief['output_class'] != 'NONPIXEL_IMAGE':
        parser.error('Comparison requires style_id and NONPIXEL_IMAGE')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    directory = args.output.resolve() / stamp
    if not directory.is_relative_to(ROOT):
        parser.error('Evidence output must be inside repository root')
    directory.mkdir(parents=True)
    write(directory / 'source_brief.json', brief)
    diagnosis = ComfyUIProvider(load_config(ROOT / 'config/pipeline.yaml')).diagnose()
    report = {'status': 'RUNNING', 'source_brief_sha256': digest(brief), 'seed': args.seed,
        'diagnosis': diagnosis.as_dict(), 'samples': {}, 'human_visual_review': 'REQUIRED',
        'quality_scores': 'NOT_MEASURED', 'model_preference': 'NOT_ESTABLISHED'}
    if diagnosis.status != 'AVAILABLE':
        report['status'] = 'BLOCKED'
        write(directory / 'report.json', report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 3
    registry = load_registry(ROOT)
    config = load_config(ROOT / 'config/pipeline.yaml')
    from assetpipe._ported.comfy_bridge.client import ComfyClient
    client = ComfyClient(config.section('comfyui')['base_url'])
    for workflow_id in ('anima_base', 'krea2_base'):
        print('Generating ' + workflow_id, flush=True)
        value = copy.deepcopy(brief)
        value['workflow_preferences']['id'] = workflow_id
        run_dir = directory / workflow_id
        try:
            for folder, names in registry[workflow_id]['models'].items():
                installed = client.list_models(folder)
                missing = [name for name in names if name not in installed]
                if missing:
                    raise ValueError(f'Models unavailable in {folder}: {missing}')
            path = create(value, ROOT, run_dir, args.seed)
            manifest = json.loads(path.read_text(encoding='utf-8'))
            if manifest['status'] != 'CANDIDATE_READY_REVIEW_REQUIRED' or not manifest['qa_results'] or any(r['status'] != 'PASS' for r in manifest['qa_results']):
                raise ValueError('Generation/QA did not pass')
            outputs = []
            for filename in manifest['outputs']:
                file = Path(filename)
                with Image.open(file) as image:
                    image.load()
                    outputs.append({'path': file.relative_to(ROOT).as_posix(), 'sha256': sha(file), 'resolution': list(image.size)})
            if not outputs:
                raise ValueError('No generated output')
            evidence = {'result': 'STYLE_COMBINATION_TESTED', 'style_id': brief['style_id'], 'workflow_id': workflow_id,
                'style_sha256': manifest['style_selection']['style_sha256'],
                'recipe_version': manifest['style_selection']['recipe_version'], 'run_manifest': path.relative_to(ROOT).as_posix(),
                'run_manifest_sha256': sha(path), 'outputs': outputs, 'human_visual_review': 'REQUIRED'}
            write(directory / f'{workflow_id}_evidence.json', evidence)
            report['samples'][workflow_id] = evidence
        except Exception as exc:
            report['samples'][workflow_id] = {'result': 'FAILED', 'error': str(exc),
                'run_manifest': (run_dir / 'run_manifest.json').relative_to(ROOT).as_posix()}
        write(directory / 'report.json', report)
    report['status'] = 'REAL_COMPARISON_GENERATED_REVIEW_REQUIRED' if all(r['result'] == 'STYLE_COMBINATION_TESTED' for r in report['samples'].values()) else 'INCOMPLETE'
    write(directory / 'report.json', report)
    write(args.output / 'latest.json', {'report': (directory / 'report.json').relative_to(ROOT).as_posix()})
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['status'] == 'REAL_COMPARISON_GENERATED_REVIEW_REQUIRED' else 4


if __name__ == '__main__':
    raise SystemExit(main())
