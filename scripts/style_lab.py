"""Resumable M2.5 lab: historical comparison, current E2E and cohort are separate."""
import argparse
import copy
import json
import time
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image
from assetpipe.brief import load, make
from assetpipe.api import capabilities
from assetpipe.manifests import write
from assetpipe.pipelines import create, revalidate_static_candidate
from assetpipe.pipelines.pixel_animation import preflight
from assetpipe.pipelines.pixel_static.approval import validate_approval
from assetpipe.prompt_mining import compile_candidate, sha256
from assetpipe.registry import load_registry
from assetpipe._ported.config import load_config
from assetpipe._ported.comfy_bridge.runner import run_workflow
from assetpipe.pipelines.pixel_static import process_candidate
from assetpipe.qa import basic_image_qa
from assetpipe.manifests import now
from assetpipe.styles import digest
from assetpipe._ported.comfy_bridge.client import ComfyClient

ROOT = Path(__file__).resolve().parents[1]


def verify_models_and_nodes(root, model_root, samples):
    """Read installed model bytes and live workflow nodes; never infer a missing hash."""
    model_root=Path(model_root).resolve()
    registry=load_registry(root)
    config=load_config(root/'config/pipeline.yaml')
    client=ComfyClient(config.section('comfyui')['base_url'])
    client.check_connection()
    objects=json.loads(client._request('/object_info'))
    dependencies=set()
    for row in samples:
        workflow=registry[row['workflow_id']]
        graph=json.loads((root/workflow['workflow_file']).read_text(encoding='utf-8'))['api_prompt']
        for node in graph.values():
            if node['class_type'] not in objects:
                raise ValueError('Missing workflow node: '+node['class_type'])
        for folder,names in workflow['models'].items():
            installed=client.list_models(folder)
            for name in names:
                if name not in installed:
                    raise ValueError('Model unavailable from running server: '+name)
                dependencies.add((folder,name))
    models={}
    for folder,name in sorted(dependencies):
        path=(model_root/folder/name).resolve()
        if not path.is_relative_to(model_root) or not path.is_file():
            raise ValueError('Model not found inside verified root: '+str(path))
        before=path.stat()
        digest=hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda:stream.read(8*1024*1024),b''):
                digest.update(block)
        after=path.stat()
        if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):
            raise ValueError('Model changed while hashing: '+str(path))
        models[f'{folder}/{name}']={'sha256':digest.hexdigest(),'path':str(path),
            'size_bytes':after.st_size,'mtime_ns':after.st_mtime_ns,'checked_at':now(),
            'verification':'LOCAL_FILE_BYTES_AND_SERVER_INVENTORY'}
        print('Verified model '+folder+'/'+name,flush=True)
    return models


def reserve(ledger, limit):
    if type(limit) is not int or not 1 <= limit <= 16:
        raise ValueError('Initial budget must be 1..16')
    if ledger['reserved_requests'] >= limit:
        raise ValueError('Generation budget exhausted')
    ledger['reserved_requests'] += 1


def same_rgba(left, right):
    with Image.open(left) as a, Image.open(right) as b:
        return a.size == b.size and a.convert('RGBA').tobytes() == b.convert('RGBA').tobytes()


def historical_comparison(root):
    new = root/'workspace/smokes/pixel_attempt_04/020_direct/040_direct_pixel_frames'
    old = root.parent/'pixel-pipeline/workspace/runs/sword_warrior_001/phase13_step3_direct_walk/attempt_05/040_direct_pixel_frames'
    frames = sorted(new.glob('*.png'))
    if len(frames) != 8 or len(list(old.glob('*.png'))) != 8:
        return {'status':'UNAVAILABLE','scope':'HISTORICAL_ARTIFACT_EQUIVALENCE_ONLY'}
    rows = [{'name':p.name,'new_sha256':sha256(p),'legacy_sha256':sha256(old/p.name),
        'exact_rgba':same_rgba(p,old/p.name)} for p in frames]
    return {'status':'PASS' if all(r['exact_rgba'] for r in rows) else 'FAIL',
        'scope':'HISTORICAL_ARTIFACT_EQUIVALENCE_ONLY','frames':rows,
        'current_e2e_evidence':False}


def compatible_integration(brief, root):
    # Current approval is mandatory FIRST. Conservative scope: exact established fixture only.
    preflight(brief)
    canonical = load(root/'examples/pixel_animation_smoke.yaml')
    if brief['production']['direct_profile'] != 'blue_tunic_white_matte_v1':
        raise ValueError('UNSUPPORTED direct profile')
    if not same_rgba(brief['production']['static_master'],canonical['production']['static_master']):
        raise ValueError('UNSUPPORTED: different master requires separately verified profile compatibility')
    for key in ('motion_reference','selection'):
        if sha256(brief['production'][key]) != sha256(canonical['production'][key]):
            raise ValueError('UNSUPPORTED: motion/selection differs from verified profile evidence')
    return {'status':'VERIFIED_EXACT_FIXTURE_SCOPE','master_sha256':sha256(brief['production']['static_master']),
        'profile':'blue_tunic_white_matte_v1','generalized_animation':False}


def prepare(root, out):
    rows=[]
    for style,workflow in [(s,'anima_pixelate_x4_vae') for s in ('clean_anime_cel','storybook_gouache','painterly_fantasy','limited_palette_pixel')] + [('clean_anime_cel','anima_base'),('storybook_gouache','krea2_base')]:
        for role in ('character','prop'):
            brief=load(root/f'examples/prompt_mining/{role}.yaml')
            if workflow=='anima_pixelate_x4_vae':
                brief['output_class']='PIXEL_STATIC'
                brief['constraints']['resolution']=None
            compiled=compile_candidate(root,'mined_'+style,brief,workflow)
            name=f'{style}_{workflow}_{role}'
            prepared=out/'prepared'/f'{name}.json'
            write(prepared,{'brief':brief,'compiled':compiled})
            rows.append({'id':name,'style_id':style,'asset_role':role,'workflow_id':workflow,
                'seed':7725,'prepared':str(prepared.relative_to(root)),'prepared_sha256':sha256(prepared),
                'status':'PREPARED','human_review':'REQUIRED','game_ready':False,
                'logical_canvas':'UNSPECIFIED','camera':'UNSPECIFIED','role_qa':'ROLE_QA_UNVERIFIED',
                'palette_policy':{'kind':'color_budget','max_colors':32} if workflow=='anima_pixelate_x4_vae' else None})
    return rows


def publish(root,out,report):
    report['artifact_root']=out.relative_to(root).as_posix()
    write(out/'manifest.json',report)
    write(root/'docs/style/M25_STATUS.json',report)
    write(root/'workspace/style_lab/m25_latest.json',{'manifest':str((out/'manifest.json').relative_to(root))})


def current_static_state(path):
    directory=Path(path).resolve()
    manifest=directory/'run_manifest.json'
    data=json.loads(manifest.read_text(encoding='utf-8'))
    if data.get('output_class')!='PIXEL_STATIC':
        raise ValueError('Current integration requires PIXEL_STATIC run')
    state={'status':data['status'],'manifest':str(manifest),'manifest_sha256':sha256(manifest),
        'qa_results':data['qa_results'],'human_review':'REQUIRED','game_ready':False}
    held=directory/'human_aseprite_review.json'
    if held.is_file():
        review=json.loads(held.read_text(encoding='utf-8'))
        if review.get('aseprite_reviewed') is False:
            state['human_review']='HELD_NOT_REVIEWED'
    if data['status']=='EXPORT_READY_REVIEW_REQUIRED' and (directory/'approval_record.json').is_file():
        evidence=data['static_validation']
        validate_approval(evidence['export'],directory/'approval_record.json')
        state.update(status='APPROVED_STATIC_MASTER',approval=str(directory/'approval_record.json'),
            approval_sha256=sha256(directory/'approval_record.json'))
    return state


def execute_prepared(root, directory, saved, seed, model_hashes):
    """Use the validated research compilation verbatim and the existing production gates."""
    brief, compiled = saved['brief'], saved['compiled']
    current = compile_candidate(root, compiled['mining']['candidate_id'], brief, compiled['mining']['workflow_id'])
    if digest(current) != digest(compiled):
        raise ValueError('Candidate, canon, recipe or workflow changed since preparation')
    workflow = load_registry(root)[compiled['mining']['workflow_id']]
    config = load_config(root/'config/pipeline.yaml')
    directory.mkdir(parents=True, exist_ok=False)
    path = directory/'run_manifest.json'
    manifest = {'schema_version':1,'asset_id':brief['asset_id'],'asset_brief':brief,
        'input_type':brief['source']['type'],'output_class':brief['output_class'],
        'workflow':{'id':compiled['mining']['workflow_id'],'hash':workflow['hash'],
            'version':workflow['version'],'model':workflow['models']},
        'style_lab_selection':compiled['mining'],'model_hashes':model_hashes,
        'generation':{'seed':seed,'compiled_prompt':compiled,'comfy_prompt_id':None},
        'pipeline_steps':[],'qa_results':[],'outputs':[],
        'timestamps':{'started':now()},'status':'RUNNING','game_ready':False}
    write(path, manifest)
    write(directory/'route_decision.json', {**compiled['mining']['route'],
        'style_lab_selection':compiled['mining'],'execution_scope':'EXPLICIT_UNAPPROVED_RESEARCH_EXPERIMENT'})
    try:
        generated = directory/'010_generation'
        write(directory/'compiled_preflight.json', compiled)
        paths = run_workflow(config,workflow_name=workflow['workflow_name'],
            prompt=compiled['positive'],negative_prompt=compiled['negative'],seed=seed,
            output_dir=generated,workflow_inputs=compiled['workflow_inputs'],
            filename_prefix='assetpipe/style_lab/'+directory.name)
        if brief['output_class']=='PIXEL_STATIC':
            if len(paths)!=1:
                raise ValueError('Static pipeline expects one image candidate')
            process_candidate(paths[0],brief,config,directory,manifest)
        else:
            if not paths:
                raise ValueError('No generated output')
            reports=[basic_image_qa(p,brief) for p in paths]
            manifest['qa_results']=reports
            manifest['outputs']=[str(p) for p in paths]
            if any(r['status']!='PASS' for r in reports):
                raise ValueError('Basic image QA failed')
            manifest['pipeline_steps'].append({'step':'generation_and_basic_qa','status':'PASS'})
            manifest['status']='CANDIDATE_READY_REVIEW_REQUIRED'
    except Exception as exc:
        manifest.update(status='FAILED',error=str(exc))
        raise
    finally:
        generated=directory/'010_generation'
        write(generated/'compiled_prompt.json', compiled)
        generation=generated/'generation.json'
        if generation.exists():
            record=json.loads(generation.read_text(encoding='utf-8'))
            manifest['generation'].update(comfy_prompt_id=record['prompt_id'],
                parameters=record['generation_parameters'],prompt=record['prompt'],
                negative_prompt=record['negative_prompt'])
        manifest['timestamps']['finished']=now()
        write(path,manifest)
    return path


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cohort',type=Path,help='Resume an existing cohort; never resets its budget')
    parser.add_argument('--static-candidate',type=Path,help='Import an existing PNG into unchanged static gates; no generation')
    parser.add_argument('--static-run',type=Path,help='Current static run with real review/approval evidence')
    parser.add_argument('--integration-brief',type=Path,help='Current approved master and explicitly compatible motion; no default old approval')
    parser.add_argument('--model-root',type=Path,help='Installed ComfyUI models folder; exact hashes required for generation')
    parser.add_argument('--generate',action='store_true')
    parser.add_argument('--max-generations',type=int,default=12)
    args=parser.parse_args(argv)
    if type(args.max_generations) is not int or not 12 <= args.max_generations <= 16:
        parser.error('The first 12-sample cohort requires a budget of 12..16')
    out=args.cohort.resolve() if args.cohort else ROOT/'workspace/style_lab/cohorts'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    if not out.is_relative_to(ROOT/'workspace/style_lab/cohorts'):
        parser.error('Cohort must be under workspace/style_lab/cohorts')
    if args.cohort:
        report=json.loads((out/'manifest.json').read_text(encoding='utf-8'))
        if report.get('harness_version')!=2:
            parser.error('Previous harness cohorts are immutable history; start a new cohort')
        if report['budget']['limit']!=args.max_generations:
            parser.error('Cannot change a persisted cohort budget')
    else:
        out.mkdir(parents=True,exist_ok=False)
        report={'milestone':'M2.5','harness_version':2,'capabilities':capabilities(ROOT),
            'historical_regression':historical_comparison(ROOT),'static_integration':{'status':'NOT_RUN'},
            'current_animation_e2e':{'status':'NOT_RUN'},'style_experiment':{'status':'NOT_RUN'},
            'budget':{'limit':args.max_generations,'reserved_requests':0},'generation_requests':0,
            'golden_approved':0,'human_review':'REQUIRED','game_ready':False,
            'in_game_review':'IN_GAME_REVIEW_PENDING','new_style_animation':'UNSUPPORTED'}
        report['samples']=prepare(ROOT,out)
    publish(ROOT,out,report)
    if report['historical_regression']['status']!='PASS':
        report['status']='BLOCKED_HISTORICAL_REGRESSION';publish(ROOT,out,report);return 3
    if args.static_candidate:
        if 'run_directory' in report['static_integration']:
            parser.error('Static candidate already imported; use --cohort and --static-run')
        source=args.static_candidate.resolve()
        with Image.open(source) as image:
            size=list(image.size)
        brief=make(asset_id='m25_existing_candidate_revalidation',output_class='PIXEL_STATIC',prompt='Existing benchmark PNG revalidation; no new generation')
        brief['constraints']['resolution']=size
        brief['workflow_preferences']['id']='anima_pixelate_x4_vae'
        brief['source']['references']=[str(source)]
        write(out/'static_brief.json',brief)
        report['static_integration']['run_directory']=str(out/'static_revalidation')
        publish(ROOT,out,report)
        try:
            revalidate_static_candidate(brief,source,ROOT,out/'static_revalidation')
        except Exception as exc:
            report['static_integration']['error']=str(exc)
    static=args.static_run or report['static_integration'].get('run_directory')
    if static:
        report['static_integration']={**report['static_integration'],**current_static_state(static),'run_directory':str(Path(static).resolve())}
    # Static-image experiments are independent of approved-master animation.
    if args.integration_brief:
        if report['static_integration']['status']!='APPROVED_STATIC_MASTER':
            report['current_animation_e2e']={'status':'BLOCKED','error':'Current Static Master approval is required'}
        else:
            try:
                brief=load(args.integration_brief)
                if Path(brief['production']['approval_record']).resolve()!=Path(report['static_integration']['approval']).resolve():
                    raise ValueError('Integration brief approval must match the current static run')
                scope=compatible_integration(brief,ROOT)
                if report['current_animation_e2e']['status']!='PASS':
                    if (out/'current_animation_e2e').exists():
                        raise ValueError('Previous animation attempt exists; no automatic retry')
                    path=create(brief,ROOT,out/'current_animation_e2e',7725)
                    data=json.loads(path.read_text())
                    direct=out/'current_animation_e2e/020_direct/040_direct_pixel_frames'
                    if data['status']!='EXPORT_READY_REVIEW_REQUIRED' or len(list(direct.glob('*.png')))!=8 or not data['qa_results'][-1]['pixel_integrity']['exact_rgba_match']:
                        raise ValueError('Current animation export/gates did not pass')
                    report['current_animation_e2e']={'status':'PASS','scope':scope,'manifest':str(path),
                        'manifest_sha256':sha256(path),'human_review':'REQUIRED','game_ready':False,
                        'integration_brief_sha256':sha256(args.integration_brief)}
                elif report['current_animation_e2e']['integration_brief_sha256']!=sha256(args.integration_brief):
                    raise ValueError('Integration brief changed')
            except Exception as exc:
                report['current_animation_e2e']={'status':'BLOCKED','error':str(exc)}
    elif report['current_animation_e2e']['status']!='PASS':
        report['current_animation_e2e']={'status':'NOT_RUN','blocker':'CURRENT_STATIC_MASTER_APPROVAL_PENDING'}
    if not args.generate:
        report['status']='STATIC_EXPERIMENT_PREPARED_ANIMATION_SEPARATE';publish(ROOT,out,report);return 0
    if not args.model_root:
        report['status']='BLOCKED_MODEL_HASHES_REQUIRED';publish(ROOT,out,report);return 3
    try:
        models=verify_models_and_nodes(ROOT,args.model_root,report['samples'])
    except Exception as exc:
        report.update(status='BLOCKED_MODEL_OR_WORKFLOW_PREFLIGHT',model_hash_status='UNVERIFIED')
        report['style_experiment']={'status':'BLOCKED_PREFLIGHT','error':str(exc)}
        publish(ROOT,out,report);return 3
    report['model_hashes']=models
    report['model_hash_status']='VERIFIED_LOCAL_FILES'
    report['style_experiment']['status']='RUNNING'
    for row in report['samples']:
        if row['status']!='PREPARED':
            continue # Reserved/failed requests are NEVER implicitly retried.
        if sha256(ROOT/row['prepared'])!=row['prepared_sha256']:
            raise ValueError('Prepared recipe changed')
        saved=json.loads((ROOT/row['prepared']).read_text())
        brief,compiled=saved['brief'],saved['compiled']
        reserve(report['budget'],report['budget']['limit'])
        row['status']='RESERVED'
        publish(ROOT,out,report)
        start=time.monotonic();directory=out/'runs'/row['id']
        try:
            execute_prepared(ROOT,directory,saved,row['seed'],models)
        except Exception as exc:
            row['error']=str(exc)
        row['elapsed_seconds']=time.monotonic()-start
        row['cost']={'billing':'LOCAL_COMFYUI','currency_cost':'NOT_MEASURED','gpu_energy':'NOT_MEASURED'}
        path=directory/'run_manifest.json'
        if not path.exists():
            row['status']='FAILED_NO_MANIFEST';publish(ROOT,out,report);continue
        manifest=json.loads(path.read_text())
        row.update(status=manifest['status'],manifest=str(path.relative_to(ROOT)),manifest_sha256=sha256(path),qa_results=manifest['qa_results'],outputs=manifest['outputs'],
            generation_submitted=bool(manifest['generation'].get('comfy_prompt_id')),
            aseprite_status='NOT_RUN_REVIEW_REQUIRED',resolution_status=manifest['status'],human_review='REQUIRED')
        original=directory/'010_generation'
        row['original_pngs']=[{'path':str(p.relative_to(ROOT)),'sha256':sha256(p)} for p in original.glob('*.png')]
        report['generation_requests']=sum(bool(r.get('generation_submitted')) for r in report['samples'])
        publish(ROOT,out,report);print(row['id']+': '+row['status'],flush=True)
    report['style_experiment']['status']='INCOMPLETE_NO_AUTOMATIC_RETRY' if any(r['status']=='RESERVED' for r in report['samples']) else 'EXECUTED_REVIEW_REQUIRED'
    report['status']='EXPERIMENT_COMPLETE_REVIEW_REQUIRED'
    publish(ROOT,out,report);print(out,flush=True);return 0


if __name__=='__main__':
    raise SystemExit(main())
