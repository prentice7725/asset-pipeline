import shutil
import subprocess
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
LIMIT = 1024 * 1024
# 이미 추적 중인 1MB 초과 파일. 새 대용량 파일은 git 밖에 둔다.
LARGE_ALLOWLIST: set[str] = set()
# 2026-10-28 이력에서 제거한 외부 보관 증거. 다시 추적하지 않는다.
EXTERNAL_EVIDENCE = 'research/style_catalog/style_menu_v1/evidence/'
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


# 2026-11-11: 과거 실험 이미지를 추적에서 뺐다. JSON 기록만 남긴다.
REMOVED_IMAGE_PREFIXES = ('workspace/', 'research/style_catalog/style_menu_v1/previews/')
IMAGE_SUFFIXES = ('.png', '.jpg', '.jpeg', '.webp', '.gif')


def test_removed_experiment_images_stay_out_of_git():
    names = [name for name in tracked_files() if name.startswith(REMOVED_IMAGE_PREFIXES)]
    assert [name for name in names if name.lower().endswith(IMAGE_SUFFIXES)] == []


def test_external_evidence_stays_out_of_git():
    assert [name for name in tracked_files() if name.startswith(EXTERNAL_EVIDENCE)] == []
