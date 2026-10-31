import ctypes
import json
import os
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from threading import Barrier
from threading import Lock
from time import sleep

import pytest

from assetpipe.manifests import write
import assetpipe.manifests as manifests


def test_concurrent_writes_publish_complete_independent_documents(tmp_path, monkeypatch):
    target = tmp_path / 'manifest.json'
    barrier = Barrier(2)
    replace = Path.replace
    temporary_file = manifests.NamedTemporaryFile
    counter_lock = Lock()
    active = 0

    @contextmanager
    def synchronized_staging(**kwargs):
        with temporary_file(**kwargs) as stream:
            yield stream
        barrier.wait(timeout=10)

    def synchronized_replace(source, destination):
        nonlocal active
        with counter_lock:
            active += 1
        try:
            sleep(0.02)  # Expose overlapping publication without relying on OS timing.
            with counter_lock:
                assert active == 1
            return replace(source, destination)
        finally:
            with counter_lock:
                active -= 1

    monkeypatch.setattr(manifests, 'NamedTemporaryFile', synchronized_staging)
    monkeypatch.setattr(Path, 'replace', synchronized_replace)
    values = [{'id': index, 'payload': str(index) * 10000} for index in range(2)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(write, target, value) for value in values]
        for future in futures:
            future.result(timeout=15)
    assert json.loads(target.read_text(encoding='utf-8')) in values
    assert list(tmp_path.iterdir()) == [target]


def test_existing_fixed_tmp_is_not_touched(tmp_path):
    target = tmp_path / 'manifest.json'
    other = tmp_path / 'manifest.json.tmp'
    other.write_bytes(b'other writer evidence')
    write(target, {'label': '검토 필요'})
    assert other.read_bytes() == b'other writer evidence'
    assert json.loads(target.read_text(encoding='utf-8')) == {'label': '검토 필요'}


def test_serialization_failure_creates_no_staging_file(tmp_path):
    target = tmp_path / 'manifest.json'
    target.write_bytes(b'{"old": true}')
    with pytest.raises(TypeError):
        write(target, {'invalid': object()})
    assert target.read_bytes() == b'{"old": true}'
    assert list(tmp_path.iterdir()) == [target]


def test_failed_replace_preserves_old_and_new_without_retry(tmp_path, monkeypatch):
    target = tmp_path / 'manifest.json'
    target.write_bytes(b'{"old": true}')
    calls = []

    def denied(source, destination):
        calls.append((source, destination))
        raise PermissionError('controlled replacement denial')

    monkeypatch.setattr(Path, 'replace', denied)
    with pytest.raises(PermissionError, match='controlled replacement denial'):
        write(target, {'new': True})
    assert len(calls) == 1
    assert calls[0][1] == target
    assert target.read_bytes() == b'{"old": true}'
    assert json.loads(calls[0][0].read_text(encoding='utf-8')) == {'new': True}


@pytest.mark.skipif(os.name != 'nt', reason='Windows share-delete contract')
def test_real_windows_target_lock_fails_closed(tmp_path):
    from ctypes import wintypes

    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD,
                                  wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD,
                                  wintypes.DWORD, wintypes.HANDLE]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    target = tmp_path / 'manifest.json'
    target.write_bytes(b'{"old": true}')
    # Read/write sharing is allowed; delete/rename sharing is deliberately withheld.
    handle = kernel.CreateFileW(str(target), 0x80000000, 3, None, 3, 0x80, None)
    assert handle != ctypes.c_void_p(-1).value, ctypes.get_last_error()
    try:
        with pytest.raises(PermissionError) as error:
            write(target, {'new': True})
        assert error.value.winerror in (5, 32)
        assert target.read_bytes() == b'{"old": true}'
        staged = [path for path in tmp_path.iterdir() if path != target]
        assert len(staged) == 1
        assert json.loads(staged[0].read_text(encoding='utf-8')) == {'new': True}
    finally:
        assert kernel.CloseHandle(handle)


def test_write_new_publishes_once_and_never_replaces(tmp_path):
    # 사람 리뷰처럼 한 번만 기록하는 문서는 완성본으로만 나타나고 기존 기록을 덮어쓰지 않는다.
    from assetpipe.manifests import write_new
    target = tmp_path / 'listening_review.json'
    write_new(target, {'outcome': 'PASS'})
    with pytest.raises(FileExistsError):
        write_new(target, {'outcome': 'REJECT'})
    assert json.loads(target.read_text(encoding='utf-8')) == {'outcome': 'PASS'}
    assert [path.name for path in tmp_path.iterdir()] == ['listening_review.json']
