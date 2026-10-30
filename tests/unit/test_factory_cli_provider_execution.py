"""Factory 1회 실행을 가짜 CLI provider로 끝까지 돌리는 테스트. 실제 생성이나 미술 승인을 대신하지 않는다."""
import hashlib
import json
from pathlib import Path

import pytest

from assetpipe.factory.executor import execute_file
from assetpipe.registry import load_registry
from tests.unit.test_cli_providers import Sandbox, brief


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')
    return path


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@pytest.mark.parametrize('workflow', ['codex_imagegen', 'grok_imagine'])
def test_cli_provider_candidate_completes_with_provider_source_outside_root(tmp_path, monkeypatch, workflow):
    box = Sandbox(tmp_path, monkeypatch)
    jobs = box.root / 'workspace/requests'
    value = brief(workflow)
    value.update(project_id='game_a', asset_id='fox')
    save(jobs / 'brief.json', value)
    request = save(jobs / 'request.json', {'factory_contract_version': 1, 'factory_line': 'NONPIXEL',
        'output_mode': 'IMAGE_ONLY', 'project_id': 'game_a', 'asset_id': 'fox',
        'source': {'kind': 'GENERATE', 'brief_ref': 'brief.json'}, 'image': {'style_source': 'fixture'},
        'authorization': {'generation_budget': 'authorization.json'}})
    entry = load_registry(box.root)[workflow]
    save(jobs / 'authorization.json', {'schema_version': 1, 'type': 'FACTORY_GENERATION_AUTHORIZATION',
        'authorization_id': 'f' * 32, 'project_id': 'game_a', 'asset_id': 'fox',
        'request_sha256': digest(request), 'workflow_id': workflow, 'workflow_sha256': entry['hash'],
        'seed': 7, 'max_requests': 1, 'authorized_by': 'tester', 'reason': 'fake CLI contract'})
    receipt = json.loads(execute_file(request, box.root, authorize_generation=True, seed=7).read_text(encoding='utf-8'))
    run = box.root / 'workspace/factory_budget' / ('f' * 32) / 'run'
    manifest = json.loads((run / 'run_manifest.json').read_text(encoding='utf-8'))
    # provider가 처음 저장한 위치는 설정 루트 밖에 출처로만 남는다.
    sources = [row['source_path'] for row in manifest['generation']['provider']['outputs']]
    assert sources and not any(Path(p).resolve().is_relative_to(box.root.resolve()) for p in sources)
    assert receipt['status'] == 'CANDIDATE_REVIEW_REQUIRED' and receipt['attempts'] == 1
    assert [row['path'] for row in receipt['artifacts']] == manifest['outputs']
    assert all(Path(row['path']).is_relative_to(run) for row in receipt['artifacts'])
    assert len(box.calls(box.codex_dir if workflow == 'codex_imagegen' else box.grok_dir)) == 1


def test_only_provider_source_provenance_is_exempt(tmp_path):
    from assetpipe.factory.provenance import validate_run_manifest
    from assetpipe.paths import RootResolver
    root = tmp_path / 'root'
    root.mkdir()
    resolver = RootResolver([root], base=root)
    outside = str(tmp_path / 'home/.grok/sessions/1.png')
    manifest = {'outputs': [str(root / 'run/a.png')],
                'generation': {'provider': {'outputs': [{'path': str(root / 'run/a.png'), 'source_path': outside}]}}}
    validate_run_manifest(manifest, resolver)
    assert manifest['generation']['provider']['outputs'][0]['source_path'] == outside  # 원본은 바꾸지 않는다.
    for broken in [{**manifest, 'outputs': [outside]}, {**manifest, 'source_manifest': outside},
                   {**manifest, 'generation': {'provider': {'outputs': [{'path': outside}]}}}]:
        with pytest.raises(ValueError, match='outside configured roots'):
            validate_run_manifest(broken, resolver)
