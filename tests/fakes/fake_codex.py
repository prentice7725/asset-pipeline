"""테스트 전용 가짜 `codex` CLI. 실제 생성이 아니며 provider 격리·장애 처리 로직을 검증하는 데만 쓴다.

같은 폴더의 mode.json으로 동작을 고르고, 호출 기록은 calls.jsonl에 남긴다.
"""
import json
import os
import pathlib
import sys
import time

from PIL import Image

here = pathlib.Path(__file__).resolve().parent
cfg = json.loads((here / 'mode.json').read_text(encoding='utf-8'))
args = sys.argv[1:]


def record(kind, **extra):
    row = {'kind': kind, 'argv': args, 'cwd': os.getcwd(), 'env': dict(os.environ), **extra}
    with (here / 'calls.jsonl').open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(row) + '\n')


def png(path, size):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new('RGB', tuple(size), (200, 120, 40)).save(path)


if args[:1] == ['--version']:
    print('codex-cli 9.9.9-fake')
elif args[:2] == ['features', 'list']:
    print('image_generation                         stable             ' + ('true' if cfg.get('feature', True) else 'false'))
elif args[:2] == ['login', 'status']:
    print('Logged in using ChatGPT' if cfg.get('logged_in', True) else 'Not logged in')
elif args[:1] == ['exec']:
    prompt = sys.stdin.read()
    record('exec', prompt=prompt)
    mode = cfg.get('mode', 'ok')
    last = pathlib.Path(args[args.index('-o') + 1]) if '-o' in args else None
    home = pathlib.Path(os.environ.get('CODEX_HOME', str(pathlib.Path.home() / '.codex')))
    if mode == 'timeout':
        time.sleep(60)
    elif mode == 'auth_fail':
        print('ERROR: 401 Unauthorized - please log in', file=sys.stderr)
        sys.exit(1)
    elif mode == 'nonzero':
        print('boom', file=sys.stderr)
        sys.exit(2)
    print(json.dumps({'type': 'thread.started', 'thread_id': 'thread_abc123'}))
    if mode == 'leak':
        print('token sk-TESTSECRET1234567890 and Authorization: Bearer abcdefghijklmnop1234')
    if mode in ('ok', 'leak', 'two'):
        old = home / 'generated_images' / 'other_thread' / 'old.png'
        png(old, (8, 8))
        os.utime(old, (time.time() - 3600, time.time() - 3600))
        png(home / 'generated_images' / 'thread_abc123' / 'ig_1.png', cfg.get('size', (64, 64)))
        if mode == 'two':
            png(home / 'generated_images' / 'thread_abc123' / 'ig_2.png', cfg.get('size', (64, 64)))
    print(json.dumps({'type': 'turn.completed', 'usage': {'input_tokens': 10, 'output_tokens': 5}, 'model': 'fake-image-model'}))
    if last:
        last.write_text("I can't help with that request; it violates content policy." if mode == 'refuse' else 'DONE', encoding='utf-8')
else:
    sys.exit(64)
