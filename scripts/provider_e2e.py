"""NONPIXEL provider(codex_imagegen, grok_imagine)의 실제 이미지 생성(E2E)을 1장 검증한다.

주의: 실제 CLI를 호출하므로 로그인된 계정의 사용량이 소모되거나 과금될 수 있다.
--confirm-paid-request 없이는 어떤 요청도 보내지 않는다. 성공 증거는 workspace/m1_e2e/ 아래에 JSON으로 남기며,
registry 상태(ACTIVE 승격)는 자동으로 바꾸지 않는다. 승격 절차는 README의 "ACTIVE 승격 조건"을 따른다.
"""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from assetpipe.brief import load
from assetpipe.manifests import write
from assetpipe.pipelines import create
from assetpipe.providers import create_provider
from assetpipe.providers.base import AVAILABLE
from assetpipe.registry import load_registry
from assetpipe._ported.config import load_config

ROOT = Path(__file__).resolve().parents[1]
PROVIDERS = ('codex_imagegen', 'grok_imagine')


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--provider', required=True, choices=PROVIDERS)
    parser.add_argument('--confirm-paid-request', action='store_true', help='실제 생성 요청 1회를 보내는 것에 동의')
    parser.add_argument('--output', type=Path, default=ROOT / 'workspace/m1_e2e')
    args = parser.parse_args(argv)
    if not args.confirm_paid_request:
        print('중단: 실제 생성 요청이 계정 사용량을 소모할 수 있습니다. 동의하면 --confirm-paid-request를 추가하세요. 요청은 보내지 않았습니다.', file=sys.stderr)
        return 2
    config = load_config(ROOT / 'config/pipeline.yaml')
    entry = load_registry(ROOT)[args.provider]
    diagnosis = create_provider(entry['engine'], config).diagnose(entry)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    evidence_path = args.output / f'{args.provider}_evidence.json'
    evidence = {'provider_id': args.provider, 'engine': entry['engine'], 'checked_at': stamp, 'diagnosis': diagnosis.as_dict(),
                'human_visual_review': 'REQUIRED', 'scope': 'text_to_image 1장. image_edit 경로는 포함하지 않는다.'}
    if diagnosis.status != AVAILABLE:
        evidence['result'] = 'NOT_RUN_' + diagnosis.status
        write(evidence_path, evidence)
        print(json.dumps(evidence, indent=2, ensure_ascii=False))
        return 3
    brief = load(ROOT / 'examples/m1_provider_smoke.yaml')
    brief['workflow_preferences'] = {'id': args.provider, 'allow_experimental': True}
    run_dir = args.output / args.provider / stamp
    try:
        manifest_path = create(brief, ROOT, run_dir)
    except Exception as exc:
        manifest = json.loads((run_dir / 'run_manifest.json').read_text(encoding='utf-8')) if (run_dir / 'run_manifest.json').exists() else {}
        evidence.update({'result': 'FAILED', 'error': str(exc), 'error_code': manifest.get('error_code'), 'run_manifest': str(run_dir / 'run_manifest.json')})
        write(evidence_path, evidence)
        print(json.dumps(evidence, indent=2, ensure_ascii=False))
        return 4
    manifest = json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    record = manifest['generation']['provider']
    outputs = [Path(p) for p in manifest['outputs']]
    checks = {'status_is_review_required': manifest['status'] == 'CANDIDATE_READY_REVIEW_REQUIRED', 'game_ready_false': manifest['game_ready'] is False,
              'provider_completed': record['status'] == 'COMPLETED', 'one_output_exists': len(outputs) == 1 and outputs[0].is_file(),
              'qa_all_pass': bool(manifest['qa_results']) and all(r['status'] == 'PASS' for r in manifest['qa_results'])}
    image = {}
    if checks['one_output_exists']:
        with Image.open(outputs[0]) as opened:
            opened.load()
            image = {'path': str(outputs[0]), 'sha256': sha256(outputs[0]), 'bytes': outputs[0].stat().st_size, 'resolution': list(opened.size), 'format': opened.format}
    evidence.update({'result': 'REAL_GENERATION_VERIFIED' if all(checks.values()) else 'FAILED_CHECKS', 'checks': checks, 'image': image,
        'run_manifest': str(manifest_path), 'run_manifest_sha256': sha256(manifest_path), 'cli_version': record.get('cli_version'),
        'tool': record.get('tool'), 'auth': record.get('auth'), 'duration_seconds': record.get('duration_seconds'), 'usage_support': record.get('usage_support')})
    write(evidence_path, evidence)
    print(json.dumps(evidence, indent=2, ensure_ascii=False))
    return 0 if evidence['result'] == 'REAL_GENERATION_VERIFIED' else 5


if __name__ == '__main__':
    raise SystemExit(main())
