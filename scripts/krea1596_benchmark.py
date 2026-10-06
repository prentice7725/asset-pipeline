"""Reserved, sequential 216-call nonpixel benchmark; no retry or fallback."""
from __future__ import annotations
import argparse,hashlib,json,time,sys
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
WORKFLOWS=('anima_base_rebuilt','anima_turbo','krea2_base')
SEEDS=(7725,7726,7727)
COHORT='KREA1596_24X3X3_20261006'
def save(path,value):
 path.parent.mkdir(parents=True,exist_ok=True)
 temporary=path.with_suffix(path.suffix+'.tmp')
 temporary.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8');temporary.replace(path)
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def plan(root=ROOT):
 from assetpipe.prompts import compile_prompt,workflow_values
 from assetpipe.prompts.synthetic_fixture import build_anima_family_brief
 from assetpipe.registry import load_registry
 from scripts.anima_family_pipeline import inspect
 inspect(root)
 registry=load_registry(root)
 spec=yaml.safe_load((root/'config/style_menu/krea1596_benchmark_v1.yaml').read_text())
 assert spec['generation_budget']==216 and tuple(spec['seeds'])==SEEDS
 assert len(spec['candidates'])==24 and len({c['candidate_id'] for c in spec['candidates']})==24
 jobs=[]
 for workflow_id in WORKFLOWS:
  workflow=registry[workflow_id]
  if workflow['models'].get('loras') or workflow.get('workflow_inputs',{}).get('enable_lora',False): raise ValueError('LoRA prohibited')
  for c in spec['candidates']:
   for seed in SEEDS:
    brief=build_anima_family_brief(root,c['style_contract_id'],workflow_id)
    brief['asset_id']=f"{c['candidate_id']}_{workflow_id}_s{seed}".replace('-','_')
    if workflow_id=='krea2_base':brief['workflow_preferences']['preset']='character_portrait'
    compiled=compile_prompt(brief,workflow,root);values=workflow_values(compiled,workflow,brief)
    assert (values['width'],values['height'])==(512,768)
    jobs.append({'job_id':brief['asset_id'],'candidate_id':c['candidate_id'],'workflow_id':workflow_id,'seed':seed,'brief':brief,'compiled_prompt':compiled,'parameters':values,'retry_budget':0})
 return {'cohort':COHORT,'status':'PREPARED_NOT_EXECUTED','generation_budget':216,'seeds':list(SEEDS),'jobs':jobs,'review':'REVIEW_REQUIRED','golden_approval':False,'repeatability':'NOT_MEASURED','variation_consistency':'THREE_SEEDS_PLANNED','note':'Equal integer seeds across models do not establish equal noise. Three distinct seeds measure seed robustness; exact same-seed repeatability is NOT_MEASURED.'}
def preflight(root,models_root):
 from assetpipe.registry import load_registry
 from assetpipe._ported.comfy_bridge.client import ComfyClient
 registry=load_registry(root);client=ComfyClient('http://127.0.0.1:8188')
 stats=client.check_connection();q=client._json('/queue')
 if q['queue_running'] or q['queue_pending']:raise ValueError('Queue must be empty')
 info=client._json('/object_info');models={}
 for w in WORKFLOWS:
  workflow=registry[w];graph=json.loads((root/workflow['workflow_file']).read_text())['api_prompt']
  for n in graph.values():
   if n['class_type'] not in info:raise ValueError('Missing node '+n['class_type'])
  for folder,names in workflow['models'].items():
   if folder=='loras':continue
   live=client._json('/models/'+folder)
   for name in names:
    p=models_root/folder/name
    if name not in live or not p.is_file():raise ValueError('Missing installed model '+name)
    if name not in models:models[name]={'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
 historical=root/'workspace/style_menu/experiments/ANIMA_FAMILY_R3_20261005/model_preflight.json'
 old=json.loads(historical.read_text())['model_files']
 for name,item in old.items():
  if models[name]['sha256']!=item['sha256']:raise ValueError('R3 model hash changed: '+name)
 return {'status':'PASS','stats':stats,'queue':q,'models':models,'historical_anima_hashes':'MATCH_R3','retry_budget':0,'golden_approval':False}
def execute(root,plan_path,models_root,out):
 from assetpipe.pipelines import create
 data=json.loads(plan_path.read_text());expected=plan(root)
 if data!=expected:raise ValueError('Plan differs from current compiler/configuration')
 live=preflight(root,models_root)
 out.mkdir(parents=True,exist_ok=False)
 save(out/'preflight.json',live);save(out/'plan.json',data)
 ledger={'cohort':COHORT,'reserved_calls':216,'attempted_calls':0,'completed_calls':0,'failed_calls':0,'retry_budget':0,'authorization':'User authorized 24 candidates x 3 models x 3 common seeds; 216 maximum calls','status':'RESERVED_BEFORE_DISPATCH'}
 save(out/'reservation.json',ledger);results=[]
 for job in data['jobs']:
  ledger['attempted_calls']+=1;ledger['current_job']=job['job_id'];save(out/'reservation.json',ledger)
  started=time.monotonic();run=out/'runs'/job['job_id']
  try:
   manifest_path=create(job['brief'],root,output=run,seed=job['seed'])
   manifest=json.loads(Path(manifest_path).read_text())
   originals=[{'path':str(p),'sha256':sha(p)} for p in run.rglob('*.png')]
   if len(originals)!=1:raise ValueError('Expected exactly one original PNG')
   if manifest['status']!='CANDIDATE_READY_REVIEW_REQUIRED':raise ValueError('Pipeline QA did not pass')
   actual=json.loads((run/'010_generation/compiled_prompt.json').read_text())
   if actual['positive']!=job['compiled_prompt']['positive']:raise ValueError('Execution prompt differs from plan')
   ledger['completed_calls']+=1
   result={'job_id':job['job_id'],'candidate_id':job['candidate_id'],'workflow_id':job['workflow_id'],'seed':job['seed'],'status':'REVIEW_REQUIRED','originals':originals,'manifest':str(manifest_path),'seconds':round(time.monotonic()-started,3)}
  except Exception as exc:
   ledger['failed_calls']+=1;ledger['status']='BLOCKED_FAILED_GATE'
   result={'job_id':job['job_id'],'status':'FAILED','error':str(exc),'run_dir':str(run),'originals':[{'path':str(p),'sha256':sha(p)} for p in run.rglob('*.png')]}
  results.append(result);save(out/'results.json',{'cohort':COHORT,'status':ledger['status'],'results':results,'golden_approval':False});save(out/'reservation.json',ledger)
  print(f"{ledger['attempted_calls']}/216 {job['job_id']} {result['status']}",flush=True)
  if ledger['failed_calls']:return 3
 ledger['status']='COMPLETED_REVIEW_REQUIRED';save(out/'reservation.json',ledger)
 save(out/'results.json',{'cohort':COHORT,'status':ledger['status'],'results':results,'golden_approval':False})
 return 0
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['plan','preflight','execute']);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--plan',type=Path);parser.add_argument('--models-root',type=Path);a=parser.parse_args()
 if a.command=='plan':save(a.output,plan());print('216 cells prepared; generation 0');return 0
 if a.command=='preflight':save(a.output,preflight(ROOT,a.models_root));print('Live/hash preflight PASS');return 0
 if a.plan is None or a.models_root is None:parser.error('execute requires plan and models-root')
 return execute(ROOT,a.plan,a.models_root,a.output)
if __name__=='__main__':raise SystemExit(main())
