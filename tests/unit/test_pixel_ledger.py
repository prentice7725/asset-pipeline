"""Pixel64 채택 시간 장부(P0) 테스트. 생성·편집 없이 기록 계약만 검증한다."""
import json

import pytest
from PIL import Image

from assetpipe.cli import main
from assetpipe.pixel import ledger


def png(path, size=(64, 64), color=(10, 20, 30, 255)):
    Image.new('RGBA', size, color).save(path)
    return path


@pytest.fixture
def book(tmp_path):
    path = tmp_path / 'ledger.json'
    ledger.create(path)
    return path


def add(book, tmp_path, entry_id='archer_a', *, color=(10, 20, 30, 255), path_id='krea2_refiner',
        generation=40.0, postprocess=2.0):
    candidate = png(tmp_path / f'{entry_id}.png', color=color)
    ledger.add_candidate(book, entry_id, candidate, path_id=path_id, brief='front archer',
                         generation_seconds=generation, postprocess_seconds=postprocess, added_by='chang')
    return candidate


def test_new_candidate_is_pending_with_unmeasured_human_time(book, tmp_path):
    add(book, tmp_path)
    entry = ledger.load(book)['entries']['archer_a']
    assert entry['state'] == 'PENDING' and entry['review'] is None
    summary = ledger.summarize(book)['krea2_refiner']
    assert summary['minutes_per_adopted'] is None
    assert 'PENDING_REVIEW' in summary['incomplete_reasons']


def test_create_refuses_to_replace_existing_ledger(book):
    with pytest.raises(FileExistsError):
        ledger.create(book)


def test_candidate_must_be_64px(book, tmp_path):
    with pytest.raises(ValueError, match='PIXEL64_LEDGER_NOT_64PX'):
        ledger.add_candidate(book, 'big', png(tmp_path / 'big.png', size=(128, 128)), path_id='p', brief='b',
                             generation_seconds=1, postprocess_seconds=1, added_by='chang')


def test_duplicate_id_or_image_is_rejected(book, tmp_path):
    add(book, tmp_path)
    with pytest.raises(ValueError, match='PIXEL64_LEDGER_DUPLICATE'):
        add(book, tmp_path)
    same = png(tmp_path / 'copy.png')
    with pytest.raises(ValueError, match='PIXEL64_LEDGER_DUPLICATE'):
        ledger.add_candidate(book, 'archer_copy', same, path_id='krea2_refiner', brief='b',
                             generation_seconds=1, postprocess_seconds=1, added_by='chang')


@pytest.mark.parametrize('seconds', [-1, float('nan'), True, '3'])
def test_machine_time_must_be_a_nonnegative_number_or_none(book, tmp_path, seconds):
    with pytest.raises(ValueError, match='PIXEL64_LEDGER_INVALID'):
        add(book, tmp_path, generation=seconds)


def test_review_is_bound_to_the_same_image_and_recorded_once(book, tmp_path):
    candidate = add(book, tmp_path)
    other = png(tmp_path / 'other.png', color=(1, 1, 1, 255))
    with pytest.raises(ValueError, match='PIXEL64_LEDGER_CANDIDATE_CHANGED'):
        ledger.record_review(book, 'archer_a', other, decision='ADOPTED', edit_minutes=5, reviewer='chang')
    ledger.record_review(book, 'archer_a', candidate, decision='ADOPTED', edit_minutes=5, reviewer='chang')
    with pytest.raises(ValueError, match='PIXEL64_LEDGER_ALREADY_REVIEWED'):
        ledger.record_review(book, 'archer_a', candidate, decision='REJECTED', edit_minutes=1, reviewer='chang')


@pytest.mark.parametrize('decision, minutes', [('APPROVED', 1), ('ADOPTED', -2), ('ADOPTED', None)])
def test_review_needs_known_decision_and_minutes(book, tmp_path, decision, minutes):
    candidate = add(book, tmp_path)
    with pytest.raises(ValueError, match='PIXEL64_LEDGER_INVALID'):
        ledger.record_review(book, 'archer_a', candidate, decision=decision, edit_minutes=minutes, reviewer='chang')


def test_rejected_effort_counts_toward_each_adopted_sprite(book, tmp_path):
    first = add(book, tmp_path, 'a', generation=60, postprocess=0)
    second = add(book, tmp_path, 'b', color=(2, 2, 2, 255), generation=60, postprocess=0)
    ledger.record_review(book, 'a', first, decision='ADOPTED', edit_minutes=10, reviewer='chang')
    ledger.record_review(book, 'b', second, decision='REJECTED', edit_minutes=4, reviewer='chang')
    summary = ledger.summarize(book)['krea2_refiner']
    assert summary['adopted'] == 1 and summary['rejected'] == 1 and summary['adoption_rate'] == 0.5
    # 기계 2분 + 사람 14분 = 16분, 채택 1장
    assert summary['minutes_per_adopted'] == 16.0 and summary['incomplete_reasons'] == []


def test_unmeasured_machine_time_blocks_the_metric(book, tmp_path):
    candidate = add(book, tmp_path, generation=None)
    ledger.record_review(book, 'archer_a', candidate, decision='ADOPTED', edit_minutes=3, reviewer='chang')
    summary = ledger.summarize(book)['krea2_refiner']
    assert summary['minutes_per_adopted'] is None
    assert summary['incomplete_reasons'] == ['MACHINE_TIME_NOT_MEASURED']


def test_no_adopted_sprite_has_no_metric(book, tmp_path):
    candidate = add(book, tmp_path)
    ledger.record_review(book, 'archer_a', candidate, decision='REJECTED', edit_minutes=3, reviewer='chang')
    assert ledger.summarize(book)['krea2_refiner']['incomplete_reasons'] == ['NO_ADOPTED']


def test_tampered_ledger_is_rejected(book, tmp_path):
    add(book, tmp_path)
    data = json.loads(book.read_text(encoding='utf-8'))
    data['entries']['archer_a']['state'] = 'ADOPTED'
    book.write_text(json.dumps(data), encoding='utf-8')
    with pytest.raises(ValueError, match='PIXEL64_LEDGER_INVALID'):
        ledger.load(book)


def test_cli_round_trip(tmp_path, capsys):
    book = tmp_path / 'ledger.json'
    candidate = png(tmp_path / 'c.png')
    base = ['--root', str(tmp_path), 'pixel-ledger']
    assert main(base + ['init', '--ledger', str(book)]) in (0, None)
    main(base + ['add', '--ledger', str(book), '--id', 'c1', '--candidate', str(candidate), '--path-id', 'krea2',
                 '--brief', 'archer', '--generation-seconds', '30', '--postprocess-seconds', '0', '--added-by', 'chang'])
    main(base + ['review', '--ledger', str(book), '--id', 'c1', '--candidate', str(candidate),
                 '--decision', 'ADOPTED', '--edit-minutes', '9.5', '--reviewer', 'chang'])
    capsys.readouterr()
    main(base + ['summary', '--ledger', str(book)])
    summary = json.loads(capsys.readouterr().out)
    assert summary['krea2']['minutes_per_adopted'] == 10.0
