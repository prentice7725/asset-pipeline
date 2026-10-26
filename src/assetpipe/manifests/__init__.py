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
