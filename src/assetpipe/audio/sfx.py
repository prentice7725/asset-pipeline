"""SFX clip metadata, immutable evidence bindings and listening review."""
import hashlib
import json
import math
import subprocess
from pathlib import Path
from jsonschema import Draft202012Validator
from ..brief import obj
from ..paths import RootResolver, validate_references

# Separate metadata contract; the advertised legacy Brief remains unchanged.
AUDIO_CONTRACT = obj({
    'duration_seconds': {'type':'number','minimum':1,'maximum':30},
    'category': {'enum':['IMPACT','UI_CUE','AMBIENCE','UNSPECIFIED']},
    'clip_name': {'type':'string','pattern':'^[A-Za-z0-9_-]{1,250}$'},
    'no_music': {'const':True,'type':'boolean'}, 'no_voice': {'const':True,'type':'boolean'}
}, ['duration_seconds'])
CHECKS = ['intent_matches','no_unwanted_music','no_unwanted_voice','no_unwanted_noise',
          'no_audible_clipping','onset_and_tail_suitable','game_context_suitable']

def clip_contract(value, asset_id):
    errors=list(Draft202012Validator(AUDIO_CONTRACT).iter_errors(value))
    if errors or not math.isfinite(value.get('duration_seconds',float('nan'))):
        raise ValueError('SFX_CLIP_CONTRACT_INVALID')
    result={'category':'UNSPECIFIED','clip_name':asset_id,'no_music':True,'no_voice':True,**value}
    name=result['clip_name'].upper()
    if name in {'CON','PRN','AUX','NUL',*[f'COM{i}' for i in range(10)],*[f'LPT{i}' for i in range(10)]}:
        raise ValueError('SFX_CLIP_CONTRACT_INVALID: reserved filename')
    Draft202012Validator(AUDIO_CONTRACT).validate(result)
    return result

def sha(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest()

def probe_flac(path):
    result=subprocess.run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)],
                          check=True,capture_output=True,text=True,timeout=30)
    data=json.loads(result.stdout);streams=data.get('streams',[])
    if len(streams)!=1 or streams[0].get('codec_type')!='audio' or streams[0].get('codec_name')!='flac':
        raise ValueError('SFX_ORIGINAL_FORMAT_INVALID: one FLAC audio stream required')
    stream=streams[0]
    if int(stream['sample_rate'])<=0 or int(stream['channels'])<=0:
        raise ValueError('SFX_ORIGINAL_FORMAT_INVALID: invalid rate or channels')
    return {'codec':'flac','sample_rate':int(stream['sample_rate']),'channels':int(stream['channels']),
            'bits_per_raw_sample':stream.get('bits_per_raw_sample')}

def checked_file(value, resolver):
    path=resolver(value)
    if not path.is_file(): raise ValueError('SFX_EVIDENCE_INVALID: expected file')
    return path

def validate_receipt(run, resolver=None):
    run=Path(run).resolve(strict=True)
    resolver=resolver or RootResolver([run],base=run)
    receipt_path=checked_file(run/'020_audio/clip_receipt.json',resolver)
    receipt=json.loads(receipt_path.read_text(encoding='utf-8'))
    validate_references(receipt,resolver)
    if receipt.get('status')!='AUDIO_CANDIDATE_READY_REVIEW_REQUIRED' or receipt.get('game_ready') is not False:
        raise ValueError('SFX_LISTENING_BLOCKED: candidate is not technically passing')
    if not receipt_path.is_relative_to(run):
        raise ValueError('SFX_EVIDENCE_INVALID: receipt is outside its run')
    manifest=json.loads(checked_file(run/'run_manifest.json',resolver).read_text(encoding='utf-8'))
    if manifest.get('output_class')!='SFX' or any(manifest.get(k)!=receipt.get(k) for k in ['project_id','asset_id']):
        raise ValueError('SFX_EVIDENCE_INVALID: project/run binding differs')
    clip_contract(receipt['clip'],receipt['asset_id'])
    for item in receipt['artifacts']+[receipt['qa'],receipt['generation_evidence']]:
        path=checked_file(item['path'],resolver)
        if not path.is_relative_to(run) or sha(path)!=item['sha256']:
            raise ValueError('SFX_EVIDENCE_CHANGED')
    originals=[i for i in receipt['artifacts'] if i['role']=='ORIGINAL_FLAC']
    waves=[i for i in receipt['artifacts'] if i['role']=='PCM_WAV']
    if len(originals)!=1 or len(waves)!=1: raise ValueError('SFX_EVIDENCE_INVALID: ambiguous clip')
    from ..pipelines.sfx import analyze_audio
    actual=analyze_audio(checked_file(waves[0]['path'],resolver),receipt['clip']['duration_seconds'])
    recorded=json.loads(checked_file(receipt['qa']['path'],resolver).read_text(encoding='utf-8'))
    if actual['status']!='PASS' or any(recorded.get(k)!=v for k,v in actual.items()):
        raise ValueError('SFX_LISTENING_BLOCKED: audio QA differs')
    metadata=probe_flac(checked_file(originals[0]['path'],resolver))
    if metadata['sample_rate']!=actual['sample_rate'] or metadata['channels']!=actual['channels']:
        raise ValueError('SFX_LISTENING_BLOCKED: sample format drift')
    return receipt_path,receipt,sha(receipt_path)

def review_template(run):
    path,receipt,fingerprint=validate_receipt(run)
    return {'schema_version':1,'type':'AUDIO_LISTENING_REVIEW','status':'REVIEW_REQUIRED',
            'project_id':receipt['project_id'],'asset_id':receipt['asset_id'],
            'receipt_sha256':fingerprint,'listened':False,'reviewed_by':'','reason':'',
            'outcome':'HOLD','checks':{key:None for key in CHECKS},'game_ready':False}

def record_review(run, review, *, listened, resolver=None):
    """Only an explicit human submission; no SOT/master/provider promotion."""
    path,receipt,fingerprint=validate_receipt(run,resolver)
    fields={'schema_version','type','status','project_id','asset_id','receipt_sha256',
            'listened','reviewed_by','reason','outcome','checks','game_ready'}
    if set(review)!=fields or review['schema_version']!=1 or review['type']!='AUDIO_LISTENING_REVIEW':
        raise ValueError('SFX_REVIEW_INVALID: unexpected contract')
    if not listened or review['listened'] is not True:
        raise ValueError('SFX_REVIEW_INVALID: explicit listening required')
    if review['receipt_sha256']!=fingerprint or any(review[k]!=receipt[k] for k in ['project_id','asset_id']):
        raise ValueError('SFX_EVIDENCE_CHANGED: review binding differs')
    if not all(isinstance(review[k],str) and review[k].strip() for k in ['reviewed_by','reason']):
        raise ValueError('SFX_REVIEW_INVALID: reviewer and reason required')
    if review['status']!='REVIEW_REQUIRED' or review['game_ready'] is not False:
        raise ValueError('SFX_REVIEW_INVALID: approval cannot be supplied')
    checks=review['checks']
    if not isinstance(checks,dict) or set(checks)!=set(CHECKS) or any(type(v) is not bool for v in checks.values()):
        raise ValueError('SFX_REVIEW_INVALID: every checklist item requires true/false')
    if review['outcome'] not in ['PASS','HOLD','REJECT'] or (review['outcome']=='PASS' and not all(checks.values())):
        raise ValueError('SFX_REVIEW_INVALID: outcome conflicts with observations')
    from ..manifests import now
    record={**review,'status':'AUDIO_LISTENING_REVIEW_'+review['outcome'],'recorded_at':now(),'game_ready':False}
    target=path.parent/'listening_review.json'
    # An existing review is immutable; changes require a separately named audit process.
    from ..manifests import write_new
    return write_new(target,record)
