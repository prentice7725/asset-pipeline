from datetime import datetime, timezone
from pathlib import Path
import json
from tempfile import NamedTemporaryFile
from threading import Lock


_publication_lock = Lock()

def now():
    return datetime.now(timezone.utc).isoformat()

def write(path, value):
    """Publish one complete JSON document; retain staging evidence on failure.

    Concurrent publications are last-successful-replace-wins, not a transaction
    for read/modify/write operations. Replacement errors propagate without retry.
    """
    serialized = json.dumps(value, indent=2, ensure_ascii=False) + '\n'
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents another writer or a stale .json.tmp from
    # supplying our staging file. Same-directory placement preserves replace.
    with NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                            prefix=f'.{path.name}.', suffix='.tmp', delete=False) as stream:
        tmp = Path(stream.name)
        stream.write(serialized)
    # Close our handle before Windows rename; preserve the staged document if
    # another process denies replacement. Never overwrite the target in place.
    # Windows can deny simultaneous renames even with independent sources.
    # Serialize this process's short publication step; this is not a retry or
    # cross-process transaction. JSON serialization and staging remain concurrent.
    with _publication_lock:
        tmp.replace(path)


def write_new(path, value):
    """Publish one complete JSON document only if the target does not exist yet.

    The document is staged next to the target and hard-linked into place, so a
    crash never leaves a truncated record and an existing record is never replaced.
    """
    serialized = json.dumps(value, indent=2, ensure_ascii=False) + '\n'
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                            prefix=f'.{path.name}.', suffix='.tmp', delete=False) as stream:
        tmp = Path(stream.name)
        stream.write(serialized)
    try:
        path.hardlink_to(tmp)  # 대상이 이미 있으면 FileExistsError로 거부한다.
    except FileExistsError:
        raise
    except OSError:
        # 하드 링크를 지원하지 않는 파일 시스템에서는 배타적 생성으로 덮어쓰기만 막는다.
        with path.open('x', encoding='utf-8') as stream:
            stream.write(serialized)
    finally:
        tmp.unlink()
    return path
