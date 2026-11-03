"""테스트 전용 가짜 `rfxgen` CLI. 실제 합성음이 아니며 렌더링 계약·장애 처리만 검증한다.

.rfx를 읽어 sustain+decay 길이의 사인파 WAV를 쓴다. 같은 폴더의 mode.json으로 동작을 고르고,
호출 기록은 calls.jsonl에 남긴다.
"""
import json
import math
import os
import pathlib
import struct
import sys
import wave

here = pathlib.Path(__file__).resolve().parent
cfg = json.loads((here / 'mode.json').read_text(encoding='utf-8'))
args = sys.argv[1:]

if args[:1] in (['--help'], ['-h']):
    print('rFXGen v5.0 - fake for tests')
    sys.exit(0)
with (here / 'calls.jsonl').open('a', encoding='utf-8') as stream:
    stream.write(json.dumps({'argv': args, 'cwd': os.getcwd()}) + '\n')
options = dict(zip(args[::2], args[1::2]))
mode = cfg.get('mode', 'ok')
if mode == 'nonzero':
    print('boom', file=sys.stderr)
    sys.exit(3)
if mode == 'no_output':
    sys.exit(0)
data = pathlib.Path(options['--input']).read_bytes()
values = struct.unpack_from('<2i22f', data, 8)
seconds = 12.0 if mode == 'long' else max(0.05, values[3] + values[5])
rate, bits, channels = (int(v) for v in options['--format'].split(','))
if mode == 'wrong_format':
    rate = 22050 if rate == 44100 else 44100
frames = int(rate * seconds)
amplitude = 0 if mode == 'silent' else 12000
with wave.open(options['--output'], 'wb') as audio:
    audio.setnchannels(channels)
    audio.setsampwidth(bits // 8)
    audio.setframerate(rate)
    samples = b''.join(struct.pack('<h', int(amplitude * math.sin(i * 0.05))) * channels for i in range(frames))
    audio.writeframes(samples)
