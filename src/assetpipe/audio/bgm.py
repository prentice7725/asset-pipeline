"""BGM music contract, technical/loop QA, immutable evidence bindings and listening review."""
import json
import math
import re
import subprocess
from pathlib import Path
import numpy as np
from jsonschema import Draft202012Validator
from ..brief import SCHEMA
from ..paths import RootResolver, validate_references
from .sfx import sha, probe_flac, checked_file

MUSIC_CONTRACT = SCHEMA['properties']['bgm']
DEFAULTS = {'duration_seconds': 60, 'instrumental': True, 'lyrics': '', 'loop': True}
CHECKS = ['intended_mood', 'no_unwanted_vocals', 'no_unwanted_noise', 'no_audible_clipping',
          'loop_seam_inaudible', 'game_context_suitable']
# Technical gates only; they never replace listening. Thresholds are recorded in every report.
LIMITS = {'max_clipped_fraction': 0.01, 'seam_window_seconds': 0.25, 'max_seam_jump_ratio': 4.0,
          'max_edge_level_difference_db': 6.0, 'max_edge_drop_below_body_db': 24.0,
          'advisory_loudness_lufs': [-30.0, -8.0]}


def music_contract(brief):
    value = {**DEFAULTS, **brief.get('bgm', {})}
    Draft202012Validator(MUSIC_CONTRACT).validate(value)
    if not math.isfinite(value['duration_seconds']):
        raise ValueError('BGM_CONTRACT_INVALID: duration must be finite')
    if value['instrumental'] == bool(value['lyrics'].strip()):
        raise ValueError('BGM_CONTRACT_INVALID: instrumental requires empty lyrics; vocals require lyrics')
    return value


def style_text(brief, spec, music):
    parts = [spec['subject'], *spec.get('appearance', []), *spec.get('style', []), *spec.get('constraints', [])]
    if music.get('mood'):
        parts.append(f"{music['mood']} mood")
    if music.get('tempo_bpm'):
        parts.append(f"{music['tempo_bpm']} BPM")
    if music['instrumental']:
        parts.append('instrumental only, no vocals, no singing, no speech')
    if music['loop']:
        parts.append('game background music loop, steady energy, no intro, no fade-out ending')
    return ', '.join(p.strip().rstrip('.') for p in parts if p and p.strip())


def integrated_loudness(path):
    """EBU R128 integrated loudness and true peak measured by FFmpeg; no normalization is applied."""
    result = subprocess.run(['ffmpeg', '-nostdin', '-hide_banner', '-nostats', '-i', str(path),
                             '-af', 'ebur128=peak=true:framelog=quiet', '-f', 'null', '-'],
                            check=True, capture_output=True, text=True, timeout=120)
    summary = result.stderr.rsplit('Summary:', 1)[-1]
    found = {k: re.search(pattern, summary) for k, pattern in
             [('integrated_lufs', r'I:\s+(-?[\d.]+|-inf) LUFS'), ('loudness_range_lu', r'LRA:\s+(-?[\d.]+) LU'),
              ('true_peak_dbfs', r'Peak:\s+(-?[\d.]+|-inf) dBFS')]}
    if not all(found.values()):
        raise ValueError('BGM_LOUDNESS_UNAVAILABLE: FFmpeg ebur128 summary not found')
    return {k: float(m.group(1)) for k, m in found.items()}


def _db(numerator, denominator):
    return 20 * math.log10(max(numerator, 1e-12) / max(denominator, 1e-12))


def seam_check(samples, rate):
    """Whole-file loop point: playback jumps from the last sample back to the first."""
    window = max(1, int(rate * LIMITS['seam_window_seconds']))
    head, tail = samples[:window], samples[-window:]
    rms = lambda x: float(np.sqrt(np.mean(x ** 2))) if x.size else 0.0
    body = rms(samples)
    steps = np.abs(np.diff(samples, axis=0))
    typical = float(np.percentile(steps, 99.9)) if steps.size else 0.0
    jump = float(np.max(np.abs(samples[-1] - samples[0])))
    report = {'method': 'WHOLE_FILE', 'loop_start_sample': 0, 'loop_end_sample': len(samples),
              'loop_start_seconds': 0.0, 'loop_end_seconds': len(samples) / rate,
              'seam_sample_jump': jump, 'typical_step_p999': typical,
              'seam_jump_ratio': jump / max(typical, 1e-6),
              'edge_level_difference_db': _db(rms(tail), rms(head)),
              'head_below_body_db': _db(body, rms(head)), 'tail_below_body_db': _db(body, rms(tail))}
    reasons = []
    if report['seam_jump_ratio'] > LIMITS['max_seam_jump_ratio']:
        reasons.append('Loop seam sample discontinuity (click risk)')
    if abs(report['edge_level_difference_db']) > LIMITS['max_edge_level_difference_db']:
        reasons.append('Loop seam level jump between tail and head')
    if max(report['head_below_body_db'], report['tail_below_body_db']) > LIMITS['max_edge_drop_below_body_db']:
        reasons.append('Loop edge is near-silent (intro/fade gap)')
    return {**report, 'status': 'FAIL' if reasons else 'PASS', 'reasons': reasons, 'listening_review': 'REQUIRED'}


def analyze_bgm(path, music):
    from ..pipelines.sfx import analyze_audio
    import wave
    report = analyze_audio(path, music['duration_seconds'])
    report['step'] = 'bgm_audio_qa'
    report['limits'] = LIMITS
    with wave.open(str(path), 'rb') as audio:
        rate, channels = audio.getframerate(), audio.getnchannels()
        samples = np.frombuffer(audio.readframes(audio.getnframes()), dtype='<i2').reshape(-1, channels).astype(np.float32) / 32768
    report['warnings'] = []
    if report['clipped_sample_fraction'] is not None and report['clipped_sample_fraction'] > LIMITS['max_clipped_fraction']:
        report['reasons'].append('Clipped sample fraction exceeds limit')
    if report['rms'] is not None and report['rms'] >= 1e-6:
        report['loudness'] = integrated_loudness(path)
        low, high = LIMITS['advisory_loudness_lufs']
        if not low <= report['loudness']['integrated_lufs'] <= high:
            report['warnings'].append('Integrated loudness outside advisory range; no normalization applied')
    else:
        report['loudness'] = None
    report['loop'] = {'requested': music['loop']}
    if music['loop'] and samples.size:
        report['loop'] = {'requested': True, **seam_check(samples, rate)}
        if report['loop']['status'] != 'PASS':
            report['reasons'].extend(report['loop']['reasons'])
    report['vocals'] = {'requested': not music['instrumental'], 'detected': 'NOT_CHECKED_LISTENING_REQUIRED'}
    report['status'] = 'FAIL' if report['reasons'] else 'PASS'
    return report


def validate_receipt(run, resolver=None):
    run = Path(run).resolve(strict=True)
    resolver = resolver or RootResolver([run], base=run)
    receipt_path = checked_file(run / '020_audio/bgm_receipt.json', resolver)
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    validate_references(receipt, resolver)
    if receipt.get('status') != 'AUDIO_CANDIDATE_READY_REVIEW_REQUIRED' or receipt.get('game_ready') is not False:
        raise ValueError('BGM_LISTENING_BLOCKED: candidate is not technically passing')
    if not receipt_path.is_relative_to(run):
        raise ValueError('BGM_EVIDENCE_INVALID: receipt is outside its run')
    manifest = json.loads(checked_file(run / 'run_manifest.json', resolver).read_text(encoding='utf-8'))
    if manifest.get('output_class') != 'BGM' or any(manifest.get(k) != receipt.get(k) for k in ['project_id', 'asset_id']):
        raise ValueError('BGM_EVIDENCE_INVALID: project/run binding differs')
    music = music_contract({'bgm': receipt['music']})
    for item in receipt['artifacts'] + [receipt['qa'], receipt['generation_evidence']]:
        path = checked_file(item['path'], resolver)
        if not path.is_relative_to(run) or sha(path) != item['sha256']:
            raise ValueError('BGM_EVIDENCE_CHANGED')
    originals = [i for i in receipt['artifacts'] if i['role'] == 'ORIGINAL_FLAC']
    waves = [i for i in receipt['artifacts'] if i['role'] == 'PCM_WAV']
    if len(originals) != 1 or len(waves) != 1:
        raise ValueError('BGM_EVIDENCE_INVALID: ambiguous clip')
    actual = analyze_bgm(checked_file(waves[0]['path'], resolver), music)
    recorded = json.loads(checked_file(receipt['qa']['path'], resolver).read_text(encoding='utf-8'))
    if actual['status'] != 'PASS' or any(recorded.get(k) != json.loads(json.dumps(v)) for k, v in actual.items()):
        raise ValueError('BGM_LISTENING_BLOCKED: audio QA differs')
    metadata = probe_flac(checked_file(originals[0]['path'], resolver))
    if metadata['sample_rate'] != actual['sample_rate'] or metadata['channels'] != actual['channels']:
        raise ValueError('BGM_LISTENING_BLOCKED: sample format drift')
    return receipt_path, receipt, sha(receipt_path)


def review_checks(receipt):
    # A non-looping cue has no seam to judge; every other item always needs a human answer.
    return [c for c in CHECKS if c != 'loop_seam_inaudible' or receipt['music']['loop']]


def review_template(run):
    path, receipt, fingerprint = validate_receipt(run)
    return {'schema_version': 1, 'type': 'BGM_LISTENING_REVIEW', 'status': 'REVIEW_REQUIRED',
            'project_id': receipt['project_id'], 'asset_id': receipt['asset_id'],
            'receipt_sha256': fingerprint, 'listened': False, 'reviewed_by': '', 'reason': '',
            'outcome': 'HOLD', 'checks': {key: None for key in review_checks(receipt)}, 'game_ready': False}


def record_review(run, review, *, listened, resolver=None):
    """Only an explicit human submission; no SOT/master/provider promotion."""
    path, receipt, fingerprint = validate_receipt(run, resolver)
    fields = {'schema_version', 'type', 'status', 'project_id', 'asset_id', 'receipt_sha256',
              'listened', 'reviewed_by', 'reason', 'outcome', 'checks', 'game_ready'}
    if set(review) != fields or review['schema_version'] != 1 or review['type'] != 'BGM_LISTENING_REVIEW':
        raise ValueError('BGM_REVIEW_INVALID: unexpected contract')
    if not listened or review['listened'] is not True:
        raise ValueError('BGM_REVIEW_INVALID: explicit listening required')
    if review['receipt_sha256'] != fingerprint or any(review[k] != receipt[k] for k in ['project_id', 'asset_id']):
        raise ValueError('BGM_EVIDENCE_CHANGED: review binding differs')
    if not all(isinstance(review[k], str) and review[k].strip() for k in ['reviewed_by', 'reason']):
        raise ValueError('BGM_REVIEW_INVALID: reviewer and reason required')
    if review['status'] != 'REVIEW_REQUIRED' or review['game_ready'] is not False:
        raise ValueError('BGM_REVIEW_INVALID: approval cannot be supplied')
    checks = review['checks']
    if not isinstance(checks, dict) or set(checks) != set(review_checks(receipt)) or any(type(v) is not bool for v in checks.values()):
        raise ValueError('BGM_REVIEW_INVALID: every checklist item requires true/false')
    if review['outcome'] not in ['PASS', 'HOLD', 'REJECT'] or (review['outcome'] == 'PASS' and not all(checks.values())):
        raise ValueError('BGM_REVIEW_INVALID: outcome conflicts with observations')
    from ..manifests import now
    record = {**review, 'status': 'AUDIO_LISTENING_REVIEW_' + review['outcome'], 'recorded_at': now(), 'game_ready': False}
    target = path.parent / 'listening_review.json'
    # An existing review is immutable; changes require a separately named audit process.
    with target.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(record, indent=2, ensure_ascii=False) + '\n')
    return target
