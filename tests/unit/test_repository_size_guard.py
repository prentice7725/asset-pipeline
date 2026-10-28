import shutil
import subprocess
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
LIMIT = 1024 * 1024
# 2026-10-27 기준 이미 추적 중인 1MB 초과 증거. 새 대용량 파일은 git 밖에 둔다.
LARGE_ALLOWLIST = {
    'research/style_catalog/style_menu_v1/evidence/plan.json',
    'research/style_catalog/style_menu_v1/evidence/run_records.zip',
    'workspace/style_menu/experiments/ANIMA_FAMILY_R2_20261005/comparison_card.png',
}
# workspace/는 .gitignore 대상이다. 과거에 강제 추가된 실행 결과 외에는 추적하지 않는다.
WORKSPACE_PREFIXES = ('workspace/style_lab/gochachara_32px_p3/', 'workspace/style_menu/')


def tracked_files():
    if shutil.which('git') is None or not (ROOT / '.git').exists():
        pytest.skip('git checkout unavailable')
    output = subprocess.run(['git', 'ls-files', '-z'], cwd=ROOT, check=True, capture_output=True).stdout
    return [name for name in output.decode('utf-8').split('\0') if name]


def test_no_new_large_tracked_files():
    large = {name for name in tracked_files() if (ROOT / name).is_file() and (ROOT / name).stat().st_size > LIMIT}
    assert large <= LARGE_ALLOWLIST, sorted(large - LARGE_ALLOWLIST)


def test_workspace_outputs_are_not_newly_tracked():
    unexpected = [name for name in tracked_files() if name.startswith('workspace/') and not name.startswith(WORKSPACE_PREFIXES)]
    assert unexpected == []
