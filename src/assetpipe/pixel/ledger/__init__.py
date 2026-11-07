"""Pixel64 채택 시간 장부 (P0).

경로 선택 기준은 '채택된 스프라이트 한 장당 총시간'이다. 총시간은 한 경로의 모든 후보에 든
기계 시간(생성·후처리)과 사람의 Aseprite 수정 시간을 더하고 채택 수로 나눈 값이다.
거절된 후보에 든 시간도 그 경로의 비용에 포함한다.

이 모듈은 이미지를 만들거나 고치지 않는다. 사람 검토 결과(채택/거절과 수정 분)는 사람이
직접 기록해야 하며, 에이전트가 추정하거나 대신 채우지 않는다. 측정이 빠지면 지표를 계산하지
않고 NOT_MEASURED 사유를 남긴다.
"""
import hashlib
import json
import math
import re
from pathlib import Path

from PIL import Image

from ...manifests import now, write, write_new

KIND = 'PIXEL64_SPRITE_LEDGER'
SIZE = (64, 64)
DECISIONS = {'ADOPTED', 'REJECTED'}
ENTRY_ID = re.compile(r'^[a-z0-9][a-z0-9_]{0,63}$')
ENTRY_FIELDS = {'path_id', 'brief', 'candidate_file', 'candidate_sha256', 'machine_seconds',
                'added_by', 'added_at', 'state', 'review'}
REVIEW_FIELDS = {'decision', 'edit_minutes', 'reviewer', 'note', 'reviewed_at'}


def _invalid(detail):
    return ValueError(f'PIXEL64_LEDGER_INVALID: {detail}')


def _sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _amount(value, name, *, optional):
    if value is None and optional:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise _invalid(f'{name} must be a nonnegative number')
    return float(value)


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise _invalid(f'{name} required')
    return value


def _check_entry(entry_id, entry):
    if not ENTRY_ID.fullmatch(entry_id) or not isinstance(entry, dict) or set(entry) != ENTRY_FIELDS:
        raise _invalid(f'bad entry {entry_id!r}')
    for key in ('path_id', 'brief', 'candidate_file', 'candidate_sha256', 'added_by', 'added_at'):
        _text(entry[key], key)
    machine = entry['machine_seconds']
    if not isinstance(machine, dict) or set(machine) != {'generation', 'postprocess'}:
        raise _invalid(f'machine_seconds {entry_id}')
    for key, value in machine.items():
        _amount(value, key, optional=True)
    review = entry['review']
    if entry['state'] == 'PENDING':
        if review is not None:
            raise _invalid(f'pending entry has a review {entry_id}')
        return
    if entry['state'] not in DECISIONS or not isinstance(review, dict) or set(review) != REVIEW_FIELDS:
        raise _invalid(f'state must match a recorded review {entry_id}')
    if review['decision'] != entry['state'] or not isinstance(review['note'], str):
        raise _invalid(f'review decision {entry_id}')
    _amount(review['edit_minutes'], 'edit_minutes', optional=False)
    _text(review['reviewer'], 'reviewer')
    _text(review['reviewed_at'], 'reviewed_at')


def load(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if (not isinstance(data, dict) or set(data) != {'schema_version', 'kind', 'entries'}
            or data['schema_version'] != 1 or data['kind'] != KIND or not isinstance(data['entries'], dict)):
        raise _invalid('unexpected ledger contract')
    hashes = set()
    for entry_id, entry in data['entries'].items():
        _check_entry(entry_id, entry)
        if entry['candidate_sha256'] in hashes:
            raise _invalid(f'duplicate candidate image {entry_id}')
        hashes.add(entry['candidate_sha256'])
    return data


def create(path):
    """빈 장부를 만든다. 이미 있으면 덮어쓰지 않는다(FileExistsError)."""
    if Path(path).exists():
        raise FileExistsError(f'PIXEL64_LEDGER_EXISTS: {path}')
    write_new(path, {'schema_version': 1, 'kind': KIND, 'entries': {}})
    return load(path)


def add_candidate(path, entry_id, candidate, *, path_id, brief, generation_seconds, postprocess_seconds, added_by):
    """64x64 후보 한 장을 PENDING으로 등록한다. 기계 시간을 모르면 None(NOT_MEASURED)으로 둔다."""
    data = load(path)
    if not isinstance(entry_id, str) or not ENTRY_ID.fullmatch(entry_id):
        raise _invalid(f'bad entry id {entry_id!r}')
    candidate = Path(candidate)
    with Image.open(candidate) as image:
        if image.size != SIZE:
            raise ValueError(f'PIXEL64_LEDGER_NOT_64PX: {candidate} is {image.size[0]}x{image.size[1]}')
    digest = _sha(candidate)
    if entry_id in data['entries'] or any(e['candidate_sha256'] == digest for e in data['entries'].values()):
        raise ValueError(f'PIXEL64_LEDGER_DUPLICATE: {entry_id} or the same image is already recorded')
    data['entries'][entry_id] = {
        'path_id': _text(path_id, 'path_id'), 'brief': _text(brief, 'brief'),
        'candidate_file': str(candidate), 'candidate_sha256': digest,
        'machine_seconds': {'generation': _amount(generation_seconds, 'generation_seconds', optional=True),
                            'postprocess': _amount(postprocess_seconds, 'postprocess_seconds', optional=True)},
        'added_by': _text(added_by, 'added_by'), 'added_at': now(), 'state': 'PENDING', 'review': None}
    write(path, data)
    return data['entries'][entry_id]


def record_review(path, entry_id, candidate, *, decision, edit_minutes, reviewer, note=''):
    """사람의 검토 결과를 한 번만 기록한다. 후보 파일은 등록 때와 같은 이미지여야 한다.

    edit_minutes는 사람이 Aseprite에서 이 후보에 쓴 시간(분)이다. 거절한 후보도 쓴 시간을 적는다.
    """
    data = load(path)
    entry = data['entries'].get(entry_id)
    if entry is None:
        raise ValueError(f'PIXEL64_LEDGER_UNKNOWN: {entry_id}')
    if entry['state'] != 'PENDING':
        raise ValueError(f'PIXEL64_LEDGER_ALREADY_REVIEWED: {entry_id} is {entry["state"]}')
    if decision not in DECISIONS:
        raise _invalid(f'decision must be one of {sorted(DECISIONS)}')
    if not isinstance(note, str):
        raise _invalid('note must be text')
    minutes = _amount(edit_minutes, 'edit_minutes', optional=False)
    if _sha(candidate) != entry['candidate_sha256']:
        raise ValueError(f'PIXEL64_LEDGER_CANDIDATE_CHANGED: {candidate} differs from the registered image')
    entry['state'] = decision
    entry['review'] = {'decision': decision, 'edit_minutes': minutes, 'reviewer': _text(reviewer, 'reviewer'),
                       'note': note, 'reviewed_at': now()}
    write(path, data)
    return entry


def summarize(path):
    """경로별 채택률과 채택 한 장당 총시간(분). 측정이 빠지면 값 대신 사유를 남긴다."""
    groups = {}
    for entry in load(path)['entries'].values():
        groups.setdefault(entry['path_id'], []).append(entry)
    result = {}
    for path_id, entries in sorted(groups.items()):
        count = {state: sum(e['state'] == state for e in entries) for state in ('ADOPTED', 'REJECTED', 'PENDING')}
        machine = [v for e in entries for v in e['machine_seconds'].values()]
        human = sum(e['review']['edit_minutes'] for e in entries if e['review'])
        reasons = []
        if count['PENDING']:
            reasons.append('PENDING_REVIEW')
        if any(v is None for v in machine):
            reasons.append('MACHINE_TIME_NOT_MEASURED')
        if not count['ADOPTED']:
            reasons.append('NO_ADOPTED')
        total = sum(v for v in machine if v is not None) / 60 + human
        decided = count['ADOPTED'] + count['REJECTED']
        result[path_id] = {
            'candidates': len(entries), 'adopted': count['ADOPTED'], 'rejected': count['REJECTED'],
            'pending': count['PENDING'], 'adoption_rate': count['ADOPTED'] / decided if decided else None,
            'human_edit_minutes': human,
            'minutes_per_adopted': None if reasons else round(total / count['ADOPTED'], 3),
            'incomplete_reasons': reasons}
    return result
