"""Offline BGM contract: synthetic calibration audio only; no model calls, queued prompts or real approvals."""
import json
import shutil
import subprocess
import wave
from pathlib import Path
import numpy as np
import pytest
import yaml
from assetpipe.brief import make, validate
from assetpipe.registry import load_registry
from assetpipe.router import route
from assetpipe.audio.bgm import CHECKS, analyze_bgm, music_contract, record_review, seam_check, style_text, validate_receipt
from assetpipe.pipelines import bgm

ROOT = Path(__file__).resolve().parents[2]
RATE = 24000


def music_brief(**settings):
    brief = make(asset_id='forest', output_class='BGM', prompt='calm forest exploration theme, harp and flute')
    if settings:
        brief['bgm'] = {'duration_seconds': 10, **settings}
    return brief


def tone(seconds=10, cycles_per_second=440, fade=False, extra_quarter=False):
    n = int(RATE * seconds) + (RATE // cycles_per_second // 4 if extra_quarter else 0)
    samples = np.sin(2 * np.pi * cycles_per_second * np.arange(n) / RATE) * 8000
    if fade:
        samples *= np.linspace(1, 0, n) ** 4
    return samples


def save_wav(path, samples):
    with wave.open(str(path), 'wb') as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(RATE)
        stream.writeframes(samples.astype('<i2').tobytes())
    return path


@pytest.fixture
def ffmpeg():
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        pytest.skip('Real local FFmpeg/FFprobe required for offline audio encoding checks')


def test_instrumental_loop_is_the_default_contract():
    brief = music_brief()
    assert music_contract(brief) == {'duration_seconds': 60, 'instrumental': True, 'lyrics': '', 'loop': True}
    text = style_text(brief, {'subject': brief['prompt']}, music_contract(brief))
    assert 'no vocals' in text and 'loop' in text


@pytest.mark.parametrize('settings', [{'lyrics': '[Verse]\nla la'}, {'instrumental': False}, {'duration_seconds': 5},
                                      {'duration_seconds': 301}, {'tempo_bpm': 300}, {'mood': ''}, {'unknown': 1}])
def test_invalid_music_settings_are_rejected(settings):
    with pytest.raises(ValueError):
        validate(music_brief(**settings))


def test_vocals_require_explicit_lyrics_and_settings_are_bgm_only():
    assert validate(music_brief(instrumental=False, lyrics='[Chorus]\nhome again'))
    sfx = make(asset_id='hit', output_class='SFX', prompt='metal hit')
    sfx['bgm'] = {'duration_seconds': 10}
    with pytest.raises(ValueError, match='only supported for BGM'):
        validate(sfx)
    brief = music_brief()
    brief['audio'] = {'duration_seconds': 10}
    with pytest.raises(ValueError, match='not the SFX audio contract'):
        validate(brief)


def test_bgm_is_experimental_and_never_auto_routed():
    registry = load_registry(ROOT)
    assert registry['audio_yue2_bgm']['status'] == 'EXPERIMENTAL'
    assert registry['audio_yue2_bgm']['output_class'] == 'BGM'
    brief = music_brief()
    with pytest.raises(ValueError, match='automatic routing requires ACTIVE'):
        route(brief, registry)
    brief['workflow_preferences'].update(id='audio_yue2_bgm')
    with pytest.raises(ValueError, match='EXPERIMENTAL requires explicit opt-in'):
        route(brief, registry)
    brief['workflow_preferences']['allow_experimental'] = True
    assert route(brief, registry)['selected_workflow'] == 'audio_yue2_bgm'
    brief['negative_prompt'] = 'vocals'
    with pytest.raises(ValueError, match='capabilities'):
        route(brief, registry)


def test_bgm_does_not_route_to_sfx_and_sfx_does_not_route_to_bgm():
    registry = load_registry(ROOT)
    sfx = make(asset_id='hit', output_class='SFX', prompt='metal hit')
    assert route(sfx, registry)['selected_workflow'] == 'audio_stable_audio_3_medium'
    brief = music_brief()
    brief['workflow_preferences'].update(id='audio_stable_audio_3_medium', allow_experimental=True)
    with pytest.raises(ValueError, match='output_class mismatch'):
        route(brief, registry)


def test_workflow_matches_captured_comfy_object_info():
    """Validates every node input against the read-only object_info capture from ComfyUI 0.42.4."""
    info = json.loads((ROOT / 'tests/fixtures/comfy_object_info_yue2_bgm.json').read_text(encoding='utf-8'))['nodes']
    workflow = json.loads((ROOT / 'config/workflows/audio_yue2_bgm.json').read_text(encoding='utf-8'))
    graph = workflow['api_prompt']
    for node_id, node in graph.items():
        schema = info[node['class_type']]['inputs']
        required = {k for k, v in schema.items() if v['section'] == 'required'}
        assert required <= set(node['inputs']), node_id
        assert set(node['inputs']) <= set(schema), node_id
        for name, value in node['inputs'].items():
            spec = schema[name]
            if isinstance(value, list):
                source = graph[value[0]]
                assert value[1] < len(info[source['class_type']]['output'])
                continue
            if 'options' in spec:
                assert value in spec['options'], (node_id, name)
            if 'min' in spec:
                assert spec['min'] <= value <= spec['max'], (node_id, name)
    assert {graph[b['node']]['class_type'] for b in workflow['bindings'].values()} == {'YuE2GenerateMusic', 'KSampler', 'SaveAudio'}
    assert workflow['models']['checkpoints'] == ['yue2_3b_int8_convrot.safetensors']
    assert graph['25']['inputs']['lyrics'] == '' and graph['25']['inputs']['abc'] == ''
    # Duration bounds of the Brief fit inside the node limits.
    assert info['YuE2GenerateMusic']['inputs']['max_duration']['max'] >= 300


def test_seam_check_passes_continuous_loop_and_fails_click_or_fade():
    assert seam_check(tone()[:, None] / 32768, RATE)['status'] == 'PASS'
    click = seam_check(tone(extra_quarter=True)[:, None] / 32768, RATE)
    assert click['status'] == 'FAIL' and 'discontinuity' in click['reasons'][0]
    faded = seam_check(tone(fade=True)[:, None] / 32768, RATE)
    assert faded['status'] == 'FAIL' and faded['loop_end_sample'] == RATE * 10


def test_bgm_qa_records_loudness_loop_point_and_blocks_bad_seam(tmp_path, ffmpeg):
    music = music_contract(music_brief())
    music['duration_seconds'] = 10
    report = analyze_bgm(save_wav(tmp_path / 'loop.wav', tone()), music)
    assert report['status'] == 'PASS' and report['loop']['loop_start_sample'] == 0
    assert -30 < report['loudness']['integrated_lufs'] < -8
    assert report['vocals']['detected'] == 'NOT_CHECKED_LISTENING_REQUIRED'
    bad = analyze_bgm(save_wav(tmp_path / 'fade.wav', tone(fade=True)), music)
    assert bad['status'] == 'FAIL'
    one_shot = analyze_bgm(tmp_path / 'fade.wav', {**music, 'loop': False})
    assert one_shot['status'] == 'PASS' and one_shot['loop'] == {'requested': False}
    clipped = analyze_bgm(save_wav(tmp_path / 'clip.wav', np.clip(tone() * 8, -32768, 32767)), music)
    assert 'Clipped sample fraction exceeds limit' in clipped['reasons']


@pytest.fixture
def box(tmp_path, monkeypatch, ffmpeg):
    calls = []
    source = tmp_path / 'fixture.flac'
    def make_source(samples):
        wav = save_wav(tmp_path / 'fixture.wav', samples)
        subprocess.run(['ffmpeg', '-nostdin', '-y', '-v', 'error', '-i', str(wav), '-c:a', 'flac', str(source)], check=True, capture_output=True)
    make_source(tone())
    def fake_workflow(config, **kwargs):
        calls.append(kwargs)
        folder = kwargs['output_dir']
        folder.mkdir()
        target = folder / 'original.flac'
        shutil.copyfile(source, target)
        (folder / 'generation.json').write_text(json.dumps({'status': 'COMPLETED', 'prompt_id': 'SYNTHETIC_FIXTURE_ONLY', 'seed': 1, 'generation_parameters': kwargs['workflow_inputs']}))
        return [target]
    monkeypatch.setattr(bgm, 'run_workflow', fake_workflow)
    def execute(**settings):
        run = tmp_path / 'fixture_project' / 'forest'
        run.mkdir(parents=True)
        brief = music_brief(**{'duration_seconds': 10, **settings})
        brief['project_id'] = 'fixture_project'
        manifest = {'project_id': 'fixture_project', 'asset_id': 'forest', 'output_class': 'BGM', 'game_ready': False, 'outputs': [],
                    'qa_results': [], 'pipeline_steps': [], 'workflow': {'id': 'audio_yue2_bgm', 'hash': 'SYNTHETIC_FIXTURE'}}
        (run / 'run_manifest.json').write_text(json.dumps(manifest))
        bgm.run(brief, {'workflow_name': 'audio_yue2_bgm'}, None, run, manifest, 7)
        return run, brief, manifest
    return execute, calls, make_source, tmp_path


def test_one_attempt_receipt_and_review_template(box):
    execute, calls, _, _ = box
    run, _, manifest = execute()
    path, receipt, _ = validate_receipt(run)
    assert len(calls) == 1 and receipt['attempts'] == 1 and receipt['fallback'] == 'NONE'
    assert calls[0]['workflow_inputs'] == {'duration_seconds': 10, 'lyrics': '', 'sampler_seed': 7}
    assert 'no vocals' in calls[0]['prompt']
    assert receipt['status'] == manifest['status'] == 'AUDIO_CANDIDATE_READY_REVIEW_REQUIRED'
    assert not receipt['game_ready'] and not manifest['game_ready']
    assert receipt['loop_point'] == {'method': 'WHOLE_FILE', 'loop_start_sample': 0, 'loop_end_sample': RATE * 10,
                                     'loop_start_seconds': 0.0, 'loop_end_seconds': 10.0}
    template = json.loads((path.parent / 'listening_review_template.json').read_text())
    assert template['status'] == 'REVIEW_REQUIRED' and template['listened'] is False
    assert set(template['checks']) == set(CHECKS) and all(v is None for v in template['checks'].values())
    with pytest.raises(FileExistsError):
        bgm.run(music_brief(duration_seconds=10), {'workflow_name': 'audio_yue2_bgm'}, None, run, manifest, 7)
    assert len(calls) == 1


def test_non_loop_template_omits_seam_item(box):
    execute, _, _, _ = box
    run, _, _ = execute(loop=False)
    template = json.loads((run / '020_audio/listening_review_template.json').read_text())
    assert 'loop_seam_inaudible' not in template['checks']
    assert validate_receipt(run)[1]['loop_point'] is None


def test_failed_seam_preserves_receipt_and_blocks_review(box):
    execute, calls, make_source, tmp_path = box
    make_source(tone(fade=True))
    with pytest.raises(ValueError, match='QA failed'):
        execute()
    run = tmp_path / 'fixture_project/forest'
    receipt = json.loads((run / '020_audio/bgm_receipt.json').read_text())
    assert receipt['status'] == 'FAILED' and not receipt['game_ready']
    assert not (run / '020_audio/listening_review_template.json').exists()
    assert (run / '010_generation/original.flac').exists()
    with pytest.raises(ValueError, match='not technically passing'):
        validate_receipt(run)
    assert len(calls) == 1


def test_invalid_contract_never_dispatches(box, monkeypatch):
    execute, calls, _, _ = box
    with pytest.raises(ValueError):
        execute(lyrics='[Verse]\nunexpected vocals')
    assert calls == []


def test_listening_review_is_explicit_immutable_and_never_game_ready(box):
    execute, _, _, _ = box
    run, _, _ = execute()
    folder = run / '020_audio'
    review = json.loads((folder / 'listening_review_template.json').read_text())
    review.update(listened=True, reviewed_by='SYNTHETIC_TEST', reason='synthetic hold only', outcome='PASS',
                  checks={key: True for key in CHECKS} | {'no_unwanted_vocals': False})
    with pytest.raises(ValueError, match='explicit listening'):
        record_review(run, review, listened=False)
    with pytest.raises(ValueError, match='conflicts'):
        record_review(run, review, listened=True)
    review['outcome'] = 'HOLD'
    record = json.loads(record_review(run, review, listened=True).read_text())
    assert record['status'] == 'AUDIO_LISTENING_REVIEW_HOLD' and record['game_ready'] is False
    with pytest.raises(FileExistsError):
        record_review(run, review, listened=True)


def test_tampered_wav_blocks_review(box):
    execute, _, _, _ = box
    run, _, _ = execute()
    wav = run / '020_audio/forest.wav'
    wav.write_bytes(wav.read_bytes() + b'changed')
    with pytest.raises(ValueError, match='CHANGED'):
        validate_receipt(run)


def test_cli_builds_bgm_brief_without_generation(monkeypatch, capsys):
    from assetpipe import cli
    captured = {}
    monkeypatch.setattr(cli, 'create', lambda brief, *args: captured.setdefault('brief', brief) and 'manifest')
    assert cli.main(['--root', str(ROOT), 'create', '--type', 'bgm', '--prompt', 'tavern theme', '--duration', '90',
                     '--mood', 'cozy', '--tempo-bpm', '96', '--workflow', 'audio_yue2_bgm', '--allow-experimental']) == 0
    assert captured['brief']['bgm'] == {'duration_seconds': 90, 'mood': 'cozy', 'tempo_bpm': 96}
    assert cli.main(['--root', str(ROOT), 'create', '--type', 'sfx', '--prompt', 'hit', '--no-loop']) == 1
    assert 'only supported for BGM' in capsys.readouterr().err


def test_mcp_duration_extends_existing_field_for_bgm(tmp_path):
    from integrations.mcp.tools.adapter import Adapter
    config = tmp_path / 'adapter.yaml'
    config.write_text(yaml.safe_dump({'core_root': str(ROOT), 'source_roots': [str(ROOT / 'examples')], 'output_root': str(tmp_path / 'out')}))
    result = Adapter(config).build_brief(request_text='boss battle theme, orchestral', output_class='BGM', duration_seconds=120)
    assert result['brief']['output_class'] == 'BGM' and result['brief']['bgm'] == {'duration_seconds': 120}
