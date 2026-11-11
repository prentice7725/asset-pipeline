"""Build README sample images from human-approved results only.

Every source file is checked against the hash its approval/evidence record pins.
Pixel art is scaled with nearest neighbour; nothing is redrawn.
"""
import hashlib
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
WS = ROOT / 'workspace'
OUT = ROOT / 'docs' / 'samples'
OUT.mkdir(parents=True, exist_ok=True)
SCALE = 4
manifest = []


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def collect_pngs(o, acc):
    if isinstance(o, dict):
        if isinstance(o.get('path'), str) and isinstance(o.get('sha256'), str):
            acc[o['path']] = o['sha256']
        for v in o.values():
            collect_pngs(v, acc)
    elif isinstance(o, list):
        for v in o:
            collect_pngs(v, acc)


def record(out, sources, approval, note):
    manifest.append({'sample': out.name, 'bytes': out.stat().st_size, 'sha256': sha(out),
                     'approval_record': str(approval.relative_to(WS.parent)).replace('\\', '/'),
                     'sources': sources, 'note': note})


# --- Pixel64 static masters -------------------------------------------------
STATIC = {
    'pixel64_knight.png': 'pixel64-batch-20261107/knight64/run_seed20261108',
    'pixel64_archer.png': 'pixel64-archer-20261107/run_seed20261107',
    'pixel64_cleric.png': 'pixel64-batch2-20261107/cleric_threequarter64/run_seed20261125',
    'pixel64_sword_knight.png': 'pixel64-swordknight-20261108/run_seed20261136',
    'pixel64_sd_cleric.png': 'pixel64-sdchibi-20261108/run_seed20261139',
    'pixel64_coin.png': 'pixel64-batch2-20261107/coin64/run_seed20261120',
    'pixel64_key.png': 'pixel64-batch2-20261107/key64/run_seed20261121',
}
for name, run in STATIC.items():
    approval = WS / run / 'approval_record.json'
    rec = json.loads(approval.read_text(encoding='utf-8'))
    assert rec['status'] == 'APPROVED_STATIC_MASTER', (run, rec['status'])
    pins = {}
    collect_pngs(rec, pins)
    src = (rec.get('delivery') or {}).get('transparent') or rec['approved_export']
    src_hash = sha(src)
    pinned = [h for p, h in pins.items() if Path(p) == Path(src)]
    flat = json.dumps(rec)
    assert src_hash in flat, f'hash of {src} not pinned in {approval}'
    im = Image.open(src).convert('RGBA')
    if 'transparent' not in src:
        # opaque master: clear the pure white background for display
        # only white connected to the border, so white highlights inside the sprite stay
        px = im.load()
        W, H = im.size
        stack = [(x, y) for x in range(W) for y in (0, H - 1)] + [(x, y) for y in range(H) for x in (0, W - 1)]
        seen = set()
        while stack:
            x, y = stack.pop()
            if (x, y) in seen or not (0 <= x < W and 0 <= y < H):
                continue
            seen.add((x, y))
            if min(px[x, y][:3]) < 245:
                continue
            px[x, y] = (0, 0, 0, 0)
            stack += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    im = im.resize((im.width * SCALE, im.height * SCALE), Image.NEAREST)
    out = OUT / name
    im.save(out, optimize=True)
    record(out, [{'path': str(Path(src).relative_to(WS.parent)).replace('\\', '/'), 'sha256': src_hash}],
           approval, f'{SCALE}x nearest; white background cleared for display' if 'transparent' not in src else f'{SCALE}x nearest')

# --- Pixel64 animations -------------------------------------------------------
ANIM = {
    'pixel64_knight_walk.gif': 'knight64/walk_seed20261126_r4',
    'pixel64_cleric_walk.gif': 'cleric64/walk_seed20261127_r3',
    'pixel64_sd_cleric_walk.gif': 'sdcleric64/walk_seed20261142_polish',
    'pixel64_sword_knight_attack.gif': 'swordknight64/attack_seed20261137/build_r2',
}
for name, rel in ANIM.items():
    run = WS / 'pixel64-motion-20261108' / rel
    approval = run / 'animation_approval.json'
    rec = json.loads(approval.read_text(encoding='utf-8'))
    assert rec['status'] == 'APPROVED_PIXEL64_ANIMATION', (rel, rec['status'])
    frames = rec['frames']
    for f in frames:
        assert sha(f['path']) == f['sha256'], f['path']
    durations = None
    anim_json = run / '050_engine' / 'phaser-animation.json'
    if anim_json.exists():
        data = json.loads(anim_json.read_text(encoding='utf-8'))
        found = []

        def walk(o):
            if isinstance(o, dict):
                if 'duration' in o and isinstance(o['duration'], (int, float)) and o['duration'] >= 40:
                    found.append(int(o['duration']))
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
        walk(data)
        if len(found) == len(frames):
            durations = found
    if durations is None:
        durations = [round(1000 / rec['fps'])] * len(frames)
    loop = 'attack' not in name
    imgs = []
    for f in frames:
        im = Image.open(f['path']).convert('RGBA')
        im = im.resize((im.width * SCALE, im.height * SCALE), Image.NEAREST)
        # light backdrop so the sprite reads on both GitHub themes
        bg = Image.new('RGBA', im.size, (236, 236, 236, 255))
        bg.alpha_composite(im)
        imgs.append(bg.convert('RGB').quantize(colors=128, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE))
    if not loop:
        durations = durations[:-1] + [durations[-1] + 600]  # pause before the GIF repeats
    out = OUT / name
    imgs[0].save(out, save_all=True, append_images=imgs[1:], duration=durations, loop=0, disposal=2, optimize=True)
    record(out, [{'path': str(Path(f['path']).relative_to(WS.parent)).replace('\\', '/'), 'sha256': f['sha256']} for f in frames],
           approval, f'{SCALE}x nearest on #ececec, {rec["fps"]} fps, durations {durations}' + ('' if loop else ' (plays once in game; GIF adds a pause and repeats)'))

# --- Identity variants (user accepted identity preservation; not final art approval)
VARIANTS = [
    ('variant_base.png', 'cafbb34ff7924de3a31afef888ed90d6', 'docs/factory/PROJECT_REFERENCE_EDIT_EVIDENCE_20261030.json'),
    ('variant_expression_grok.png', '48adc226d31e4f5ea933c39bd9e3fa77', 'docs/factory/PROJECT_REFERENCE_EDIT_EVIDENCE_20261030.json'),
    ('variant_expression_codex.png', '9eccb362c3cc40ba82b8b7d43480220b', 'docs/factory/CODEX_PROJECT_REFERENCE_EDIT_EVIDENCE_20261030.json'),
    ('variant_pose_codex.png', 'e665026801ed4ecb9ef98eb79640fb26', 'docs/factory/CODEX_PROJECT_POSE_EVIDENCE_20261030.json'),
]
for name, job, evidence in VARIANTS:
    src = WS / 'factory_budget' / job / 'run' / '020_delivery' / '0' / 'portrait.png'
    h = sha(src)
    ev = (WS.parent / evidence)
    assert h in ev.read_text(encoding='utf-8'), f'{src} hash not in {evidence}'
    im = Image.open(src).convert('RGBA')
    w = 300
    im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
    out = OUT / name
    im.save(out, optimize=True)
    manifest.append({'sample': name, 'bytes': out.stat().st_size, 'sha256': sha(out), 'evidence': evidence,
                     'sources': [{'path': str(src.relative_to(WS.parent)).replace('\\', '/'), 'sha256': h}],
                     'note': 'resized to 300px wide; identity preservation accepted by the user, not final art approval'})

(OUT / 'samples.json').write_text(json.dumps({'schema_version': 1, 'samples': manifest}, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
for m in manifest:
    print(f"{m['sample']:34} {m['bytes']:>8}")
print('total', sum(m['bytes'] for m in manifest))
