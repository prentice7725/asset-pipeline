"""테스트 전용 가짜 `grok` CLI. 실제 생성이 아니며 provider 격리·장애 처리 로직을 검증하는 데만 쓴다."""
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


if args[:1] == ['--version']:
    print('grok 9.9.9-fake (abcdef)')
elif args[:1] == ['models']:
    print('You are not authenticated.' if not cfg.get('logged_in', True) else '* grok-fake (default)')
elif '--prompt-file' in args:
    prompt = pathlib.Path(args[args.index('--prompt-file') + 1]).read_text(encoding='utf-8')
    record('run', prompt=prompt)
    mode = cfg.get('mode', 'ok')
    home = pathlib.Path(os.environ.get('GROK_HOME') or (pathlib.Path.home() / '.grok'))
    if mode == 'timeout':
        time.sleep(60)
    if mode == 'auth_fail':
        print(json.dumps({'type': 'error', 'message': 'Not signed in. Set XAI_API_KEY'}))
        sys.exit(1)
    if mode == 'refuse':
        print(json.dumps({'type': 'result', 'result': "I can't generate that image because it violates content policy."}))
        sys.exit(0)
    if mode == 'no_output':
        print(json.dumps({'type': 'result', 'result': 'DONE'}))
        sys.exit(0)
    image = home / 'sessions' / 'sess-1' / 'images' / '1.jpg'
    image.parent.mkdir(parents=True, exist_ok=True)
    Image.new('RGB', tuple(cfg.get('size', (64, 64))), (30, 90, 200)).save(image, 'JPEG')
    print(json.dumps({'type': 'result', 'session_id': 'sess-1', 'model': 'grok-fake', 'usage': {'input_tokens': 7, 'output_tokens': 3}, 'result': f'saved {image}'}))
else:
    sys.exit(64)
