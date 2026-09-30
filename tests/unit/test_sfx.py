import wave
from pathlib import Path
import numpy as np
import pytest
from assetpipe.brief import make, validate
from assetpipe.registry import load_registry
from assetpipe.router import route
from assetpipe.pipelines.sfx import analyze_audio

ROOT = Path(__file__).resolve().parents[2]

def test_comfy_audio_history_is_collected(monkeypatch):
    from assetpipe._ported.comfy_bridge.client import ComfyClient
    client = ComfyClient('http://127.0.0.1:8188')
    artifact = {'filename': 'hit.flac', 'subfolder': 'audio', 'type': 'output'}
    monkeypatch.setattr(client, '_json', lambda *args: {'run': {'status': {'completed': True}, 'outputs': {'57': {'audio': [artifact]}}}})
    assert client.wait_for_outputs('run', ('57',)) == [artifact]

def test_sfx_routes_only_to_audio_workflow():
    brief = make(asset_id='hit', output_class='SFX', prompt='metal hit')
    assert route(brief, load_registry(ROOT))['selected_workflow'] == 'audio_stable_audio_3_medium'
    brief['negative_prompt'] = 'music'
    with pytest.raises(ValueError, match='capabilities'):
        route(brief, load_registry(ROOT))

@pytest.mark.parametrize('duration', [0, 31, float('inf')])
def test_bad_duration_is_rejected(duration):
    brief = make(asset_id='hit', output_class='SFX', prompt='metal hit')
    brief['audio'] = {'duration_seconds': duration}
    with pytest.raises(ValueError):
        validate(brief)

def test_audio_gate_detects_silence_and_duration(tmp_path):
    path = tmp_path / 'audio.wav'
    def save(samples):
        with wave.open(str(path), 'wb') as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(44100)
            f.writeframes(samples.astype('<i2').tobytes())
    save(np.zeros(44100))
    assert analyze_audio(path, 1)['status'] == 'FAIL'
    save(np.sin(np.arange(44100) * .1) * 10000)
    assert analyze_audio(path, 1)['status'] == 'PASS'
    assert analyze_audio(path, 5)['status'] == 'FAIL'
