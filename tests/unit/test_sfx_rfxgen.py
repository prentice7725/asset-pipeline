"""rfxgen 합성 SFX 오프라인 계약 테스트. 가짜 rfxgen만 쓰며 실제 합성음 품질이나 재생성 동일성을 판정하지 않는다."""
import hashlib
import json
import shutil
import struct
from pathlib import Path

import pytest
import yaml

from assetpipe.audio.rfxgen import RFX_FIELDS, parse_rfx
from assetpipe.audio.sfx import CHECKS, record_review, validate_receipt
from assetpipe.brief import make, validate
from assetpipe.cli import main
from assetpipe.registry import load_registry
from assetpipe.router import route
from tests.unit.test_cli_providers import install_fake

ROOT = Path(__file__).resolve().parents[2]
DEFAULTS = {name: 0.0 for name in RFX_FIELDS[2:]}
DEFAULTS.update(sustainTimeValue=0.1, decayTimeValue=0.2, startFrequencyValue=0.5)


def make_rfx(path, *, seed=1234, wave_type=0, header=b'rFX ', version=200, length=96, **overrides):
    values = {**DEFAULTS, **overrides}
    data = header + struct.pack('<HH', version, length) + struct.pack('<2i22f', seed, wave_type, *[values[n] for n in RFX_FIELDS[2:]])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@pytest.fixture
def lab(tmp_path):
    root = tmp_path / 'root'
    shutil.copytree(ROOT / 'config', root / 'config')
    exe_dir = tmp_path / 'rfxgen_bin'

    class Lab:
        def __init__(self):
            self.root, self.tmp = root, tmp_path

        def tool(self, executable=True, **mode):
            config = yaml.safe_load((ROOT / 'config/pipeline.yaml').read_text(encoding='utf-8'))
            path = install_fake(exe_dir, 'fake_rfxgen.py', 'rfxgen', **mode) if executable else tmp_path / 'missing' / 'rfxgen'
            config['rfxgen'] = {'executable': str(path)}
            (root / 'config/pipeline.yaml').write_text(yaml.safe_dump(config), encoding='utf-8')

        def calls(self):
            log = exe_dir / 'calls.jsonl'
            return [json.loads(line) for line in log.read_text(encoding='utf-8').splitlines()] if log.exists() else []

        def create(self, rfx, name='ui_confirm', *extra):
            out = tmp_path / 'runs' / name
            code = main(['--root', str(root), 'create', '--type', 'sfx', '--asset-id', name,
                         '--prompt', 'short bright UI confirm blip, no music, no voice', '--rfx', str(rfx), '--output', str(out), *extra])
            manifest = json.loads((out / 'run_manifest.json').read_text(encoding='utf-8')) if (out / 'run_manifest.json').exists() else None
            return code, out, manifest

    lab = Lab()
    lab.tool()
    return lab


# ---------- .rfx 형식 ----------

def test_valid_rfx_is_parsed_with_seed_and_wave_type(tmp_path):
    params = parse_rfx(make_rfx(tmp_path / 'a.rfx', seed=77, wave_type=3))
    assert params['randSeed'] == 77 and params['waveType'] == 'NOISE' and params['sustainTimeValue'] == pytest.approx(0.1)


@pytest.mark.parametrize('change', [{'header': b'RIFF'}, {'version': 100}, {'length': 92}, {'wave_type': 7},
                                    {'sustainTimeValue': float('nan')}, 'truncated'])
def test_invalid_rfx_is_rejected_before_rendering(tmp_path, change):
    path = tmp_path / 'bad.rfx'
    if change == 'truncated':
        make_rfx(path)
        path.write_bytes(path.read_bytes()[:-4])
    else:
        make_rfx(path, **change)
    with pytest.raises(ValueError, match='SFX_SYNTH_PARAMS_INVALID'):
        parse_rfx(path)


# ---------- registry / brief / router ----------

def test_registry_keeps_rfxgen_experimental_and_explicit(lab):
    entry = load_registry(lab.root)['sfx_rfxgen']
    assert (entry['engine'], entry['status'], entry['selection'], entry['output_class']) == ('rfxgen', 'EXPERIMENTAL', 'explicit_only', 'SFX')
    path = lab.root / 'config/workflow_registry.yaml'
    original = path.read_text(encoding='utf-8')
    for change in [{'status': 'ACTIVE'}, {'selection': None}, {'backend': {'output_format': '44100,32,1'}},
                   {'backend': {'cli_args': ['--play', 'x.wav']}}, {'output_class': 'BGM'}]:
        values = yaml.safe_load(original)
        values['workflows']['sfx_rfxgen'].update(change)
        path.write_text(yaml.safe_dump(values), encoding='utf-8')
        with pytest.raises(ValueError):
            load_registry(lab.root)
    path.write_text(original, encoding='utf-8')


def synth_brief(rfx, workflow='sfx_rfxgen'):
    brief = make(asset_id='ui_confirm', output_class='SFX', prompt='UI confirm blip')
    brief['synth'] = {'engine': 'rfxgen', 'params_path': str(rfx), 'params_sha256': digest(rfx)}
    brief['workflow_preferences'] = {'id': workflow, 'allow_experimental': True} if workflow else {}
    return brief


def test_synth_brief_is_sfx_only_and_has_no_requested_duration(tmp_path):
    brief = synth_brief(make_rfx(tmp_path / 'a.rfx'))
    validate(brief)
    with pytest.raises(ValueError, match='SFX_SYNTH_INVALID'):
        validate({**brief, 'audio': {'duration_seconds': 1}})
    with pytest.raises(ValueError, match='SFX_SYNTH_INVALID'):
        validate({**brief, 'output_class': 'BGM'})


def test_router_never_mixes_text_and_synth_sfx(tmp_path):
    registry = load_registry(ROOT)
    text = make(asset_id='hit', output_class='SFX', prompt='metal hit')
    assert route(text, registry)['selected_workflow'] == 'audio_stable_audio_3_medium'
    text['workflow_preferences'] = {'id': 'sfx_rfxgen', 'allow_experimental': True}
    with pytest.raises(ValueError):
        route(text, registry)  # 프롬프트만으로는 rfxgen을 쓸 수 없다.
    rfx = make_rfx(tmp_path / 'a.rfx')
    assert route(synth_brief(rfx), registry)['selected_workflow'] == 'sfx_rfxgen'
    with pytest.raises(ValueError):
        route(synth_brief(rfx, workflow=None), registry)  # 명시 없이 자동 선택되지 않는다.


# ---------- 렌더링 ----------

def test_render_records_params_wav_evidence_and_stays_review_required(lab):
    rfx = make_rfx(lab.tmp / 'library/ui_confirm.rfx', seed=4242)
    code, out, manifest = lab.create(rfx)
    assert code == 0 and manifest['status'] == 'AUDIO_CANDIDATE_READY_REVIEW_REQUIRED' and manifest['game_ready'] is False
    assert manifest['workflow']['id'] == 'sfx_rfxgen' and manifest['generation']['synth']['rand_seed'] == 4242
    assert manifest['generation']['seed'] is None and manifest['generation']['synth']['exact_reproduction'] == 'NOT_VERIFIED'
    receipt = json.loads((out / '020_audio/clip_receipt.json').read_text(encoding='utf-8'))
    assert receipt['engine'] == 'rfxgen' and receipt['attempts'] == 1 and receipt['fallback'] == 'NONE'
    assert [a['role'] for a in receipt['artifacts']] == ['SYNTH_PARAMS_RFX', 'PCM_WAV']
    assert receipt['artifacts'][0]['sha256'] == digest(rfx) and receipt['clip']['duration_seconds'] == pytest.approx(0.3, abs=0.01)
    invocation = json.loads((out / '010_generation/rfxgen_invocation.json').read_text(encoding='utf-8'))
    assert invocation['tool_version'] == '5.0' and invocation['returncode'] == 0 and len(invocation['executable_sha256']) == 64
    assert invocation['argv'] == ['<rfxgen>', '--input', 'params.rfx', '--output', 'ui_confirm.wav', '--format', '44100,16,1']
    assert len(lab.calls()) == 1 and Path(lab.calls()[0]['cwd']).resolve() == (out / '010_generation').resolve()
    validate_receipt(out)


def test_listening_review_uses_the_same_explicit_record(lab):
    _, out, _ = lab.create(make_rfx(lab.tmp / 'a.rfx'))
    review = json.loads((out / '020_audio/listening_review_template.json').read_text(encoding='utf-8'))
    review.update(listened=True, reviewed_by='SYNTHETIC_TEST', reason='fixture only', outcome='HOLD', checks={k: False for k in CHECKS})
    record = json.loads(record_review(out, review, listened=True).read_text(encoding='utf-8'))
    assert record['status'] == 'AUDIO_LISTENING_REVIEW_HOLD' and record['game_ready'] is False


@pytest.mark.parametrize('target', ['wav', 'params'])
def test_tampered_render_blocks_listening_review(lab, target):
    _, out, _ = lab.create(make_rfx(lab.tmp / 'a.rfx'))
    path = out / '010_generation' / ('ui_confirm.wav' if target == 'wav' else 'params.rfx')
    path.write_bytes(path.read_bytes() + b'x')
    with pytest.raises(ValueError, match='SFX_EVIDENCE_CHANGED'):
        validate_receipt(out)


def test_changed_params_or_missing_tool_stop_before_any_render(lab):
    rfx = make_rfx(lab.tmp / 'a.rfx')
    brief_hash_mismatch = lab.tmp / 'b.rfx'
    make_rfx(brief_hash_mismatch)
    out = lab.tmp / 'runs/changed'
    brief = synth_brief(brief_hash_mismatch)
    make_rfx(brief_hash_mismatch, seed=999)  # Brief를 만든 뒤 파일이 바뀜
    (lab.tmp / 'changed.json').write_text(json.dumps(brief), encoding='utf-8')
    assert main(['--root', str(lab.root), 'create', '--brief', str(lab.tmp / 'changed.json'), '--output', str(out)]) == 1
    assert 'SFX_SYNTH_PARAMS_CHANGED' in json.loads((out / 'run_manifest.json').read_text(encoding='utf-8'))['error']
    assert not (out / '010_generation').exists() and lab.calls() == []
    lab.tool(executable=False)
    code, out, manifest = lab.create(rfx, 'no_tool')
    assert code == 1 and 'RFXGEN_UNAVAILABLE' in manifest['error'] and not (out / '010_generation').exists()


@pytest.mark.parametrize('mode, code', [('nonzero', 'RFXGEN_EXIT_NONZERO'), ('no_output', 'RFXGEN_OUTPUT_MISSING'),
                                        ('silent', 'Audio QA failed'), ('long', 'Audio QA failed'),
                                        ('wrong_format', 'Audio QA failed')])
def test_failures_are_recorded_once_and_never_reviewable(lab, mode, code):
    lab.tool(mode=mode)
    _, out, manifest = lab.create(make_rfx(lab.tmp / 'a.rfx'), mode)
    assert manifest['status'] == 'FAILED' and code in manifest['error'] and len(lab.calls()) == 1
    receipt = json.loads((out / '020_audio/clip_receipt.json').read_text(encoding='utf-8'))
    assert receipt['status'] == 'FAILED' and (out / '010_generation/rfxgen_invocation.json').is_file()
    assert not (out / '020_audio/listening_review_template.json').exists()
    with pytest.raises(ValueError):
        validate_receipt(out)


def test_rfx_option_rejects_duration_and_other_output_types(lab):
    rfx = make_rfx(lab.tmp / 'a.rfx')
    assert main(['--root', str(lab.root), 'create', '--type', 'sfx', '--asset-id', 'x', '--prompt', 'p',
                 '--rfx', str(rfx), '--duration', '2', '--output', str(lab.tmp / 'runs/x')]) == 1
    assert main(['--root', str(lab.root), 'create', '--type', 'bgm', '--asset-id', 'y', '--prompt', 'p',
                 '--rfx', str(rfx), '--output', str(lab.tmp / 'runs/y')]) == 1
    assert lab.calls() == []


# ---------- 승인 프리셋 라이브러리 ----------

from assetpipe.audio import rfx_library


def test_committed_library_is_valid_and_starts_without_approvals():
    data = rfx_library.load(ROOT)
    assert data['schema_version'] == 1 and all(e['state'] != 'APPROVED' or e.get('approval') for e in data['entries'].values())


def register(lab, entry_id='ui_confirm', **params):
    rfx = make_rfx(lab.tmp / 'gui' / f'{entry_id}.rfx', **params)
    return rfx_library.add_candidate(lab.root, entry_id, rfx, category='UI_CONFIRM',
                                     description='Short bright confirm blip', added_by='SYNTHETIC_TEST')


def render_preset(lab, entry_id='ui_confirm', name=None):
    out = lab.tmp / 'runs' / (name or entry_id)
    code = main(['--root', str(lab.root), 'create', '--type', 'sfx', '--asset-id', name or entry_id,
                 '--prompt', 'library render', '--rfx-preset', entry_id, '--output', str(out)])
    return code, out


def listen(out, outcome, checks):
    review = json.loads((out / '020_audio/listening_review_template.json').read_text(encoding='utf-8'))
    review.update(listened=True, reviewed_by='SYNTHETIC_TEST', reason='fixture only', outcome=outcome,
                  checks={k: checks for k in CHECKS})
    record_review(out, review, listened=True)


def test_register_copies_human_rfx_as_candidate_and_never_overwrites(lab):
    entry = register(lab)
    stored = lab.root / 'config/sfx_library/ui_confirm.rfx'
    assert entry['state'] == 'CANDIDATE' and entry['sha256'] == digest(stored) and 'approval' not in entry
    with pytest.raises(ValueError, match='SFX_LIBRARY_EXISTS'):
        register(lab)
    bad = lab.tmp / 'bad.rfx'
    bad.write_bytes(b'not an rfx')
    for kwargs in [{'rfx': bad, 'category': 'UI_CLICK'}, {'rfx': stored, 'category': 'MUSIC'}]:
        with pytest.raises(ValueError):
            rfx_library.add_candidate(lab.root, 'other', kwargs['rfx'], category=kwargs['category'],
                                      description='d', added_by='t')
    assert set(rfx_library.load(lab.root)['entries']) == {'ui_confirm'}


def test_preset_render_records_library_state_and_approval_needs_pass_review(lab):
    register(lab, seed=11)
    code, out = render_preset(lab)
    receipt = json.loads((out / '020_audio/clip_receipt.json').read_text(encoding='utf-8'))
    assert code == 0 and receipt['synth']['library'] == {'id': 'ui_confirm', 'state_at_render': 'CANDIDATE', 'category': 'UI_CONFIRM'}
    with pytest.raises(ValueError, match='SFX_LIBRARY_REVIEW_REQUIRED'):
        rfx_library.approve(lab.root, 'ui_confirm', out)
    listen(out, 'HOLD', False)
    with pytest.raises(ValueError, match='SFX_LIBRARY_REVIEW_NOT_PASS'):
        rfx_library.approve(lab.root, 'ui_confirm', out)
    _, passed = render_preset(lab, name='ui_confirm_second')
    listen(passed, 'PASS', True)
    entry = rfx_library.approve(lab.root, 'ui_confirm', passed)
    assert entry['state'] == 'APPROVED' and entry['approval']['run_id'] == 'ui_confirm_second'
    assert entry['approval']['reviewed_by'] == 'SYNTHETIC_TEST'
    assert rfx_library.load(lab.root)['entries']['ui_confirm']['state'] == 'APPROVED'
    with pytest.raises(ValueError, match='ALREADY_APPROVED'):
        rfx_library.approve(lab.root, 'ui_confirm', passed)
    # 승인 뒤에 새로 렌더링한 결과도 여전히 청취 검토 대상이다.
    _, again = render_preset(lab, name='ui_confirm_third')
    manifest = json.loads((again / 'run_manifest.json').read_text(encoding='utf-8'))
    assert manifest['status'] == 'AUDIO_CANDIDATE_READY_REVIEW_REQUIRED' and manifest['game_ready'] is False


def test_approval_rejects_a_run_of_different_parameters(lab):
    register(lab)
    _, out, _ = lab.create(make_rfx(lab.tmp / 'other.rfx', seed=99), 'other_params')
    listen(out, 'PASS', True)
    with pytest.raises(ValueError, match='SFX_LIBRARY_RUN_MISMATCH'):
        rfx_library.approve(lab.root, 'ui_confirm', out)


def test_tampered_library_blocks_loading_and_rendering(lab):
    register(lab)
    index = lab.root / 'config/sfx_library/library.json'
    original = index.read_text(encoding='utf-8')
    data = json.loads(original)
    data['entries']['ui_confirm']['state'] = 'APPROVED'  # 청취 근거 없이 승인으로 바꿈
    index.write_text(json.dumps(data), encoding='utf-8')
    with pytest.raises(ValueError, match='SFX_LIBRARY_INVALID'):
        rfx_library.load(lab.root)
    index.write_text(original, encoding='utf-8')
    stored = lab.root / 'config/sfx_library/ui_confirm.rfx'
    make_rfx(stored, seed=5)  # 등록 뒤 파라미터가 바뀜
    with pytest.raises(ValueError, match='SFX_LIBRARY_CHANGED'):
        rfx_library.load(lab.root)
    code, out = render_preset(lab)
    assert code == 1 and lab.calls() == []


def test_library_cli_lists_and_registers_without_rendering(lab, capsys):
    rfx = make_rfx(lab.tmp / 'gui/laser_small.rfx')
    assert main(['--root', str(lab.root), 'sfx-library', 'add', '--id', 'laser_small', '--rfx', str(rfx),
                 '--category', 'LASER', '--description', 'Small retro laser', '--added-by', 'SYNTHETIC_TEST']) == 0
    assert main(['--root', str(lab.root), 'sfx-library', 'list']) == 0
    listed = json.loads(capsys.readouterr().out.split('\n}\n', 1)[1])
    assert listed['entries']['laser_small']['state'] == 'CANDIDATE' and lab.calls() == []
    assert main(['--root', str(lab.root), 'sfx-library', 'approve', '--id', 'laser_small',
                 '--run', str(lab.tmp / 'runs/none')]) == 1
