"""rfxgen 승인 프리셋 라이브러리.

사람이 GUI에서 만든 .rfx를 후보(CANDIDATE)로 등록하고, 그 파라미터로 렌더링한 실행에
사람의 청취 기록(PASS)이 있을 때만 승인(APPROVED)한다. 이 모듈은 소리를 만들거나 듣지 않으며,
.rfx를 생성·수정하지 않는다. 승인은 파라미터를 재사용해도 된다는 뜻이고, 새로 렌더링한 결과는
여전히 청취 검토가 필요하다(game_ready는 항상 false).
"""
import json
import re
import shutil
from pathlib import Path

from ..manifests import now, write
from .rfxgen import parse_rfx
from .sfx import sha

LIBRARY_DIR = Path('config/sfx_library')
CATEGORIES = ['UI_CLICK', 'UI_CONFIRM', 'UI_CANCEL', 'UI_WARNING', 'LASER', 'HIT', 'PICKUP',
              'JUMP', 'EXPLOSION', 'POWERUP', 'OTHER']
STATES = {'CANDIDATE', 'APPROVED'}
ENTRY_ID = re.compile(r'^[a-z0-9][a-z0-9_]{0,63}$')
APPROVAL_FIELDS = {'run_id', 'receipt_sha256', 'review_sha256', 'reviewed_by', 'reviewed_at', 'reason', 'recorded_at'}


def _paths(root):
    folder = (Path(root).resolve() / LIBRARY_DIR)
    return folder, folder / 'library.json'


def load(root):
    """목록과 파일을 함께 검사한다. 파일이 바뀌었거나 승인 근거가 빠지면 라이브러리 전체를 거부한다."""
    folder, index = _paths(root)
    data = json.loads(index.read_text(encoding='utf-8'))
    if set(data) != {'schema_version', 'entries'} or data['schema_version'] != 1 or not isinstance(data['entries'], dict):
        raise ValueError('SFX_LIBRARY_INVALID: unexpected library contract')
    for entry_id, entry in data['entries'].items():
        _check_entry(folder, entry_id, entry)
    return data


def _check_entry(folder, entry_id, entry):
    base = {'category', 'file', 'sha256', 'description', 'added_by', 'added_at', 'state'}
    if not ENTRY_ID.fullmatch(entry_id) or not isinstance(entry, dict):
        raise ValueError(f'SFX_LIBRARY_INVALID: bad entry id {entry_id!r}')
    expected = base | ({'approval'} if entry.get('state') == 'APPROVED' else set())
    if set(entry) != expected or entry['state'] not in STATES or entry['category'] not in CATEGORIES:
        raise ValueError(f'SFX_LIBRARY_INVALID: bad entry fields {entry_id}')
    if entry['file'] != f'{entry_id}.rfx':
        raise ValueError(f'SFX_LIBRARY_INVALID: file name must match the entry id {entry_id}')
    path = folder / entry['file']
    if not path.is_file() or path.resolve().parent != folder.resolve() or sha(path) != entry['sha256']:
        raise ValueError(f'SFX_LIBRARY_CHANGED: {entry_id}.rfx is missing or differs from the library hash')
    parse_rfx(path)
    if not all(isinstance(entry[k], str) and entry[k].strip() for k in ['description', 'added_by']):
        raise ValueError(f'SFX_LIBRARY_INVALID: description and added_by required {entry_id}')
    if entry['state'] == 'APPROVED':
        approval = entry['approval']
        if not isinstance(approval, dict) or set(approval) != APPROVAL_FIELDS or not all(
                isinstance(approval[k], str) and approval[k].strip() for k in APPROVAL_FIELDS):
            raise ValueError(f'SFX_LIBRARY_INVALID: approval needs the listening record binding {entry_id}')


def resolve(root, entry_id):
    """create에서 쓸 경로·해시·상태. 후보도 렌더링할 수 있어야 청취 검토를 받을 수 있다."""
    folder, _ = _paths(root)
    entry = load(root)['entries'].get(entry_id)
    if entry is None:
        raise ValueError(f'SFX_LIBRARY_UNKNOWN: {entry_id}')
    return {'path': folder / entry['file'], 'sha256': entry['sha256'], 'state': entry['state'], 'category': entry['category']}


def add_candidate(root, entry_id, rfx, *, category, description, added_by):
    """사람이 만든 .rfx를 그대로 복사해 후보로 등록한다. 같은 id는 덮어쓰지 않는다."""
    folder, index = _paths(root)
    data = load(root)
    if not ENTRY_ID.fullmatch(entry_id) or category not in CATEGORIES:
        raise ValueError('SFX_LIBRARY_INVALID: id must be lowercase snake_case and category known')
    if entry_id in data['entries']:
        raise ValueError(f'SFX_LIBRARY_EXISTS: {entry_id}; register changed parameters under a new id')
    if not all(isinstance(v, str) and v.strip() for v in [description, added_by]):
        raise ValueError('SFX_LIBRARY_INVALID: description and added_by required')
    source = Path(rfx).resolve(strict=True)
    parse_rfx(source)
    target = folder / f'{entry_id}.rfx'
    if target.exists():
        raise ValueError(f'SFX_LIBRARY_EXISTS: {target.name} already present')
    shutil.copyfile(source, target)
    if sha(target) != sha(source):
        target.unlink()
        raise ValueError('SFX_LIBRARY_CHANGED: copied .rfx differs from the source')
    data['entries'][entry_id] = {'category': category, 'file': target.name, 'sha256': sha(target),
                                 'description': description.strip(), 'added_by': added_by.strip(),
                                 'added_at': now(), 'state': 'CANDIDATE'}
    write(index, data)
    return data['entries'][entry_id]


def approve(root, entry_id, run, *, resolver=None):
    """그 후보의 파라미터로 렌더링한 실행에 PASS 청취 기록이 있을 때만 승인한다. 자동 판정은 없다."""
    from .sfx import validate_receipt
    folder, index = _paths(root)
    data = load(root)
    entry = data['entries'].get(entry_id)
    if entry is None:
        raise ValueError(f'SFX_LIBRARY_UNKNOWN: {entry_id}')
    if entry['state'] != 'CANDIDATE':
        raise ValueError(f'SFX_LIBRARY_ALREADY_APPROVED: {entry_id}')
    receipt_path, receipt, receipt_sha = validate_receipt(run, resolver)
    if receipt.get('engine') != 'rfxgen' or receipt['synth']['params_sha256'] != entry['sha256']:
        raise ValueError('SFX_LIBRARY_RUN_MISMATCH: run did not render this library entry')
    review_path = receipt_path.parent / 'listening_review.json'
    if not review_path.is_file():
        raise ValueError('SFX_LIBRARY_REVIEW_REQUIRED: record a listening review with sfx-review first')
    review = json.loads(review_path.read_text(encoding='utf-8'))
    if (review.get('status') != 'AUDIO_LISTENING_REVIEW_PASS' or review.get('listened') is not True
            or review.get('receipt_sha256') != receipt_sha or review.get('game_ready') is not False
            or not isinstance(review.get('checks'), dict) or not review['checks']
            or not all(v is True for v in review['checks'].values())):
        raise ValueError('SFX_LIBRARY_REVIEW_NOT_PASS: approval needs an explicit PASS listening record for this render')
    entry['state'] = 'APPROVED'
    entry['approval'] = {'run_id': receipt['run_id'], 'receipt_sha256': receipt_sha, 'review_sha256': sha(review_path),
                         'reviewed_by': review['reviewed_by'], 'reviewed_at': review['recorded_at'],
                         'reason': review['reason'], 'recorded_at': now()}
    write(index, data)
    return entry
