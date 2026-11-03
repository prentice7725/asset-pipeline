"""rfxgen 합성 SFX: 사람이 만든 .rfx 파라미터를 WAV로 렌더링하는 오프라인 경로.

프리셋 무작위 생성(--generate)은 파라미터가 남지 않아 재생성할 수 없으므로 쓰지 않는다.
.rfx에는 난수 시드가 들어 있지만, 같은 WAV가 다시 나오는지는 실제 실행 근거로만 확정한다.
"""
import math
import re
import shutil
import struct
import subprocess
from pathlib import Path

# rfxgen v5 .rfx: "rFX " + version(200) + length(96) + WaveParams(int 2개, float 22개), 리틀엔디언.
RFX_SIZE = 104
RFX_FIELDS = ['randSeed', 'waveTypeValue', 'attackTimeValue', 'sustainTimeValue', 'sustainPunchValue',
              'decayTimeValue', 'startFrequencyValue', 'minFrequencyValue', 'slideValue', 'deltaSlideValue',
              'vibratoDepthValue', 'vibratoSpeedValue', 'changeAmountValue', 'changeSpeedValue',
              'squareDutyValue', 'dutySweepValue', 'repeatSpeedValue', 'phaserOffsetValue', 'phaserSweepValue',
              'lpfCutoffValue', 'lpfCutoffSweepValue', 'lpfResonanceValue', 'hpfCutoffValue', 'hpfCutoffSweepValue']
WAVE_TYPES = ['SQUARE', 'SAWTOOTH', 'SINE', 'NOISE']
# 합성 효과음은 짧다. 텍스트 SFX의 1–30초 계약 대신 이 범위를 쓴다.
MIN_SECONDS, MAX_SECONDS = 0.02, 10.0


def parse_rfx(path):
    """잘못된 파일을 rfxgen에 넘기면 경고만 내고 빈 파라미터로 렌더링하므로, 먼저 직접 검사한다."""
    data = Path(path).read_bytes()
    if len(data) != RFX_SIZE or data[:4] != b'rFX ':
        raise ValueError('SFX_SYNTH_PARAMS_INVALID: not an rfxgen v5 .rfx file')
    version, length = struct.unpack_from('<HH', data, 4)
    if version != 200 or length != 96:
        raise ValueError('SFX_SYNTH_PARAMS_INVALID: unsupported .rfx version or length')
    values = struct.unpack_from('<2i22f', data, 8)
    params = dict(zip(RFX_FIELDS, values))
    if not 0 <= params['waveTypeValue'] < len(WAVE_TYPES):
        raise ValueError('SFX_SYNTH_PARAMS_INVALID: unknown wave type')
    if not all(math.isfinite(v) for v in values[2:]):
        raise ValueError('SFX_SYNTH_PARAMS_INVALID: nonfinite parameter')
    params['waveType'] = WAVE_TYPES[params['waveTypeValue']]
    return params


def find_executable(config):
    """설정의 executable(없으면 PATH의 rfxgen). 찾지 못하면 생성 없이 UNAVAILABLE로 멈춘다."""
    configured = config.section('rfxgen').get('executable')
    if configured:
        path = Path(configured).expanduser()
        if path.is_file():
            return path.resolve()
        raise ValueError('RFXGEN_UNAVAILABLE: configured rfxgen executable does not exist')
    found = shutil.which('rfxgen')
    if not found:
        raise ValueError('RFXGEN_UNAVAILABLE: rfxgen was not found; set rfxgen.executable in config/pipeline.yaml')
    return Path(found).resolve()


def _run(command, *, cwd, timeout):
    try:
        # rfxgen 로그에 사용자 경로(한글 포함)가 들어가므로 UTF-8로 읽고 깨진 바이트는 대체한다.
        return subprocess.run(command, cwd=str(cwd), capture_output=True, text=True, encoding='utf-8',
                              errors='replace', timeout=timeout, shell=False, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired as exc:
        raise ValueError(f'RFXGEN_TIMEOUT: rfxgen did not finish within {timeout}s; no retry') from exc
    except OSError as exc:
        raise ValueError(f'RFXGEN_NOT_RUNNABLE: {exc}') from exc


def tool_version(executable, *, cwd):
    """--help 첫 줄의 버전 표기만 기록한다. 읽지 못하면 None으로 둔다(추정하지 않음)."""
    try:
        result = _run([str(executable), '--help'], cwd=cwd, timeout=10)
    except ValueError:
        return None
    match = re.search(r'\bv(\d+(?:\.\d+)+)\b', result.stdout + '\n' + result.stderr)
    return match.group(1) if match else None


def render(executable, params, wav, *, output_format, timeout):
    """한 번만 실행한다. 재시도나 다른 엔진으로의 대체는 없다."""
    if wav.exists():
        raise ValueError('RFXGEN_OUTPUT_EXISTS: refusing to overwrite an existing render')
    # 파라미터와 WAV를 같은 폴더에 두고 이름만 넘긴다. 긴 경로·비ASCII 경로를 인자로 넘기지 않기 위해서다.
    if params.parent != wav.parent:
        raise ValueError('RFXGEN_LAYOUT_INVALID: parameters and render must share one folder')
    command = [str(executable), '--input', params.name, '--output', wav.name, '--format', output_format]
    result = _run(command, cwd=wav.parent, timeout=timeout)
    record = {'argv': ['<rfxgen>', *command[1:]], 'returncode': result.returncode,
              'stdout': result.stdout[-4000:], 'stderr': result.stderr[-4000:]}
    if result.returncode != 0:
        raise ValueError(f'RFXGEN_EXIT_NONZERO: rfxgen exited with {result.returncode}')
    if not wav.is_file():
        raise ValueError('RFXGEN_OUTPUT_MISSING: rfxgen finished without writing the WAV')
    return record
