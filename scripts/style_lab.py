"""M2.5 explicit local experiment; no promotion, retries or provider fallback."""
import argparse
import copy
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image
from assetpipe.brief import load
from assetpipe.api import capabilities
from assetpipe.manifests import write
from assetpipe.pipelines import create
from assetpipe.prompt_mining import compile_candidate, sha256

ROOT = Path(__file__).resolve().parents[1]


def reserve(ledger, limit):
    if type(limit) is not int or not 1 <= limit <= 16:
        raise ValueError('Initial budget must be 1..16')
    if ledger['reserved_requests'] >= limit:
        raise ValueError('Generation budget exhausted')
    ledger['reserved_requests'] += 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generate', action='store_true', help='Explicitly authorize the configured local batch')
    parser.add_argument('--max-generations', type=int, default=12)
    args = parser.parse_args()
    if not 1 <= args.max_generations <= 16:
        parser.error('Initial budget must be 1..16')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out = ROOT / 'workspace/style_lab/cohorts' / stamp
    out.mkdir(parents=True)
    report = {'milestone':'M2.5','capabilities':capabilities(ROOT), 'samples':[],
        'budget':{'limit':args.max_generations,'reserved_requests':0}, 'human_review':'REQUIRED',
        'game_ready':False,'golden_approved':0,'in_game_review':'IN_GAME_REVIEW_PENDING',
        'role_qa':{'tile':'ROLE_QA_UNVERIFIED','ui_icon':'ROLE_QA_UNVERIFIED'},
        'new_style_animation':'UNSUPPORTED', 'model_hash_status':'NOT_VERIFIED',
        'source_reproduction':'NOT_CLAIMED'}
    write(out/'manifest.json',report)
    # An independently approved existing fixture; no generation or new human approval.
    try:
        animation = create(load(ROOT/'examples/pixel_animation_smoke.yaml'),ROOT,out/'animation_regression',7725)
        data = json.loads(animation.read_text())
        export = data['qa_results'][-1]
        assert export['pixel_integrity']['exact_rgba_match']
        assert len(list((out/'animation_regression/020_direct/040_direct_pixel_frames').glob('*.png'))) == 8
        legacy = ROOT.parent/'pixel-pipeline/workspace/runs/sword_warrior_001/phase13_step3_direct_walk/attempt_05/040_direct_pixel_frames'
        for frame in (out/'animation_regression/020_direct/040_direct_pixel_frames').glob('*.png'):
            with Image.open(frame) as a, Image.open(legacy/frame.name) as b:
                assert a.convert('RGBA').tobytes() == b.convert('RGBA').tobytes()
        report['animation_regression']={'status':'PASS','manifest':str(animation.relative_to(ROOT)), 'exact_legacy_rgba':True,'frames':8,'human_review':'REQUIRED'}
    except Exception as exc:
        report['animation_regression']={'status':'FAILED','error':str(exc)}
        report['status']='BLOCKED_REGRESSION_PREFLIGHT_FAILED'
        report['artifact_root']=str(out.relative_to(ROOT))
        write(out/'manifest.json',report)
        write(ROOT/'docs/style/M25_STATUS.json',report)
        write(ROOT/'workspace/style_lab/m25_latest.json',{'manifest':str((out/'manifest.json').relative_to(ROOT))})
        raise
    for style,workflow in [(s,'anima_pixelate_x4_vae') for s in ('clean_anime_cel','storybook_gouache','painterly_fantasy','limited_palette_pixel')] + [('clean_anime_cel','anima_base'),('storybook_gouache','krea2_base')]:
        for role in ('character','prop'):
            brief = load(ROOT/f'examples/prompt_mining/{role}.yaml')
            if workflow == 'anima_pixelate_x4_vae':
                brief['output_class']='PIXEL_STATIC'
                brief['constraints']['resolution']=None
            compiled = compile_candidate(ROOT,'mined_'+style,brief,workflow)
            name = f'{style}_{workflow}_{role}'
            write(out/'prepared'/f'{name}.json',compiled)
            row = {'style_id':style,'asset_role':role,'camera':'UNSPECIFIED',
                'logical_canvas':'UNSPECIFIED','palette_policy':{'kind':'color_budget','max_colors':32} if brief['output_class']=='PIXEL_STATIC' else None,
                'seed':7725,'recipe':compiled['mining'],'status':'PREPARED','human_review':'REQUIRED','game_ready':False}
            report['samples'].append(row)
            if args.generate:
                reserve(report['budget'],args.max_generations)
                write(out/'manifest.json',report) # Durable reservation BEFORE possible submission.
                execution = copy.deepcopy(brief)
                execution.pop('style_id',None)
                execution['prompt_spec']=compiled['prompt_spec']
                execution['workflow_preferences']['id']=workflow
                start = time.monotonic()
                directory=out/'runs'/name
                try:
                    create(execution,ROOT,directory,7725)
                except Exception as exc:
                    row['error']=str(exc)
                row['elapsed_seconds']=time.monotonic()-start
                manifest = json.loads((directory/'run_manifest.json').read_text())
                # Research provenance does not create approved runtime style routing.
                manifest['style_lab_selection']=compiled['mining']
                write(directory/'run_manifest.json',manifest)
                row['status']=manifest['status']
                row['manifest']=str((directory/'run_manifest.json').relative_to(ROOT))
                row['manifest_sha256']=sha256(directory/'run_manifest.json')
                row['qa_results']=manifest['qa_results']
                row['outputs']=manifest['outputs']
                row['generation_submitted']=bool(manifest['generation'].get('comfy_prompt_id'))
                row['failure_category']='pixel_gate' if manifest['status']=='FAILED' and 'Pixel Gate' in manifest.get('error','') else 'generation_or_other' if manifest['status']=='FAILED' else None
                write(out/'manifest.json',report)
                print(name+': '+row['status'],flush=True)
    report['status']='EXPERIMENT_COMPLETE_REVIEW_REQUIRED' if args.generate else 'INFRA_PREPARED'
    write(out/'manifest.json',report)
    write(ROOT/'workspace/style_lab/m25_latest.json',{'manifest':str((out/'manifest.json').relative_to(ROOT))})
    target=ROOT/'docs/style/M25_STATUS.json'
    write(target,{**report,'artifact_root':str(out.relative_to(ROOT))})
    print(str(out),flush=True)


if __name__ == '__main__':
    main()
