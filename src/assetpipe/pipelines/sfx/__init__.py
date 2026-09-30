"""Text-to-SFX candidate generation; listening review is always required."""
import hashlib
import subprocess
from pathlib import Path
import numpy as np
from ..._ported.comfy_bridge.runner import run_workflow
from ...manifests import write


def analyze_audio(path, expected_duration):
    import wave
    with wave.open(str(path), 'rb') as audio:
        rate, channels = audio.getframerate(), audio.getnchannels()
        if audio.getsampwidth() != 2:
            raise ValueError('Audio QA requires exported 16-bit PCM WAV')
        samples = np.frombuffer(audio.readframes(audio.getnframes()), dtype='<i2').reshape(-1, channels).astype(np.float32) / 32768
    duration = len(samples) / rate
    finite = bool(np.isfinite(samples).all())
    peak = float(np.max(np.abs(samples))) if samples.size and finite else None
    rms = float(np.sqrt(np.mean(samples ** 2))) if samples.size and finite else None
    reasons = []
    if not finite or not samples.size:
        reasons.append('Empty or nonfinite audio')
    if rms is None or rms < 1e-6:
        reasons.append('Silent audio')
    if abs(duration - expected_duration) > max(1.0, expected_duration * .1):
        reasons.append('Duration differs from requested length')
    return {'step': 'basic_audio_qa', 'status': 'FAIL' if reasons else 'PASS',
            'sample_rate': rate, 'channels': samples.shape[1], 'duration_seconds': duration,
            'requested_duration_seconds': expected_duration, 'peak': peak, 'rms': rms,
            'clipped_sample_fraction': float(np.mean(np.abs(samples) >= .999)) if finite and samples.size else None,
            'reasons': reasons, 'listening_review': 'REQUIRED'}


def run(brief, workflow, config, directory, manifest, seed):
    from ...prompts import from_brief
    spec = from_brief(brief)
    if spec.get('textInImage') or spec.get('aspectRatio'):
        raise ValueError('Visual text/aspect ratio is not supported for SFX')
    duration = brief.get('audio', {}).get('duration_seconds', 5)
    prompt = '. '.join([spec['subject'], *spec.get('appearance', []),
        *[spec[k] for k in ('environment', 'mood', 'pose') if spec.get(k)],
        *spec.get('style', []), *spec.get('constraints', [])])
    paths = run_workflow(config, workflow_name=workflow['workflow_name'], prompt=prompt,
        seed=seed, output_dir=directory / '010_generation', workflow_inputs={'duration_seconds': duration},
        filename_prefix=f'assetpipe/{brief["asset_id"]}')
    manifest['outputs'] = [str(p) for p in paths]
    if len(paths) != 1:
        raise ValueError('SFX expects one audio candidate')
    output = directory / '020_audio'
    output.mkdir()
    wav = output / (brief['asset_id'] + '.wav')
    subprocess.run(['ffmpeg', '-v', 'error', '-i', str(paths[0]), '-c:a', 'pcm_s16le', str(wav)],
        check=True, capture_output=True, timeout=60)
    manifest['outputs'].append(str(wav))
    report = analyze_audio(wav, duration)
    report['sha256'] = hashlib.sha256(wav.read_bytes()).hexdigest()
    write(output / 'audio_qa.json', report)
    manifest['qa_results'].append(report)
    manifest['pipeline_steps'].append({'step': 'basic_audio_qa', 'status': report['status']})
    if report['status'] != 'PASS':
        raise ValueError('Audio QA failed; listening/export approval blocked')
    manifest['status'] = 'AUDIO_CANDIDATE_READY_REVIEW_REQUIRED'
