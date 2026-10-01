import json
import shutil
import pytest
from scripts.package_plugin import PLUGIN, validate_package

def test_local_plugin_contract_keeps_creator_validation_separate():
    result = validate_package()
    assert result['status'] == 'PASS'
    assert result['creator_validation'] == 'NOT_RUN_CREATOR_UNAVAILABLE'

def test_codex_and_claude_code_manifests_share_one_package():
    result = validate_package()
    assert result['hosts'] == ['claude_code', 'codex']

def test_manifest_version_drift_between_hosts_is_rejected(tmp_path):
    # 한쪽 호스트 매니페스트만 버전을 올리면 패키지 검증이 실패해야 한다.
    root = tmp_path / 'plugin'
    shutil.copytree(PLUGIN, root)
    path = root / '.claude-plugin/plugin.json'
    manifest = json.loads(path.read_text(encoding='utf-8'))
    manifest['version'] = '9.9.9'
    path.write_text(json.dumps(manifest), encoding='utf-8')
    with pytest.raises(AssertionError):
        validate_package(root)
