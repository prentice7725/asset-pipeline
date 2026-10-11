"""Offline calibration audio only; no model calls or real approvals."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,shutil,subprocess,wave
from pathlib import Path
import numpy as np
import pytest
from assetpipe.brief import make
from assetpipe.audio.sfx import clip_contract,record_review,validate_receipt,CHECKS
from assetpipe.pipelines import sfx

@pytest.fixture
def calibration(tmp_path):
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        pytest.skip('Real local FFmpeg/FFprobe required for offline audio encoding checks')
    def create(duration=1,silent=False):
        wav=tmp_path/f'fixture_{duration}_{silent}.wav'
        samples=np.zeros(int(24000*duration)) if silent else np.sin(np.arange(int(24000*duration))*.1)*8000
        with wave.open(str(wav),'wb') as stream:
            stream.setnchannels(1);stream.setsampwidth(2);stream.setframerate(24000);stream.writeframes(samples.astype('<i2').tobytes())
        flac=wav.with_suffix('.flac')
        subprocess.run(['ffmpeg','-nostdin','-y','-v','error','-i',str(wav),'-c:a','flac',str(flac)],check=True,capture_output=True)
        return flac
    return create

@pytest.fixture
def box(tmp_path,monkeypatch,calibration):
    calls=[];source=calibration()
    def fake_workflow(config,**kwargs):
        calls.append(kwargs)
        folder=kwargs['output_dir'];folder.mkdir()
        target=folder/'original.flac';shutil.copyfile(source,target)
        (folder/'generation.json').write_text(json.dumps({'status':'COMPLETED','prompt_id':'SYNTHETIC_FIXTURE_ONLY','seed':1,'generation_parameters':kwargs['workflow_inputs']}))
        return [target]
    monkeypatch.setattr(sfx,'run_workflow',fake_workflow)
    def execute(project='fixture_project',name='hit',clip=None):
        run=tmp_path/project/name;run.mkdir(parents=True)
        brief=make(asset_id=name,output_class='SFX',prompt='offline fixture, no music, no voice')
        brief['project_id']=project;brief['audio']={'duration_seconds':1}
        manifest={'project_id':project,'asset_id':name,'output_class':'SFX','game_ready':False,'outputs':[],'qa_results':[],'pipeline_steps':[],'workflow':{'id':'audio_stable_audio_3_medium','hash':'SYNTHETIC_FIXTURE'}}
        (run/'run_manifest.json').write_text(json.dumps(manifest))
        sfx.run(brief,{'workflow_name':'audio_stable_audio_3_medium'},None,run,manifest,1,clip=clip)
        return run,brief,manifest
    return execute,calls,tmp_path,source

@pytest.mark.parametrize('category',['IMPACT','UI_CUE','AMBIENCE'])
def test_category_receipt_and_real_pcm_format(box,category):
    execute,calls,_,_=box
    run,_,manifest=execute(clip={'duration_seconds':1,'category':category,'clip_name':'fixture_clip'})
    path,receipt,_=validate_receipt(run)
    assert receipt['clip']['category']==category and receipt['clip']['no_music'] is True
    assert receipt['sample_format']['sample_rate']==24000 and receipt['sample_format']['channels']==1
    assert len(calls)==1 and receipt['attempts']==1 and receipt['fallback']=='NONE'
    assert receipt['status']==manifest['status']=='AUDIO_CANDIDATE_READY_REVIEW_REQUIRED'
    assert not receipt['game_ready'] and not manifest['game_ready']
    with wave.open(str(run/'020_audio/fixture_clip.wav')) as stream:assert stream.getsampwidth()==2
    template=json.loads((path.parent/'listening_review_template.json').read_text())
    assert template['status']=='REVIEW_REQUIRED' and template['listened'] is False
    assert all(v is None for v in template['checks'].values())
    assert not (path.parent/'listening_review.json').exists()

@pytest.mark.parametrize('bad',[{'category':'MUSIC'},{'clip_name':'../escape'},{'clip_name':'CON'},{'duration_seconds':float('nan')},{'duration_seconds':31},{'no_music':False}])
def test_bad_clip_metadata_never_dispatches(box,bad):
    execute,calls,_,_=box
    with pytest.raises(ValueError):execute(clip={'duration_seconds':1,**bad})
    assert calls==[]

def test_no_retry_into_existing_run(box):
    execute,calls,_,_=box;run,brief,manifest=execute()
    with pytest.raises(FileExistsError):sfx.run(brief,{'workflow_name':'audio_stable_audio_3_medium'},None,run,manifest,1)
    assert len(calls)==1

def test_legacy_underscore_asset_name_remains_compatible(box):
    execute,_,_,_=box;run,_,manifest=execute(name='_legacy_hit')
    assert (run/'020_audio/_legacy_hit.wav').is_file()
    assert manifest['status']=='AUDIO_CANDIDATE_READY_REVIEW_REQUIRED'

def test_project_and_concurrent_name_isolation(box):
    execute,calls,_,_=box
    with ThreadPoolExecutor(4) as pool:
        results=list(pool.map(lambda p:execute(project=p),['project1','project2','project3','project4']))
    prefixes={c['filename_prefix'] for c in calls}
    assert len(prefixes)==4
    assert len({str(r[0]) for r in results})==4
    for run,_,manifest in results:
        assert all(Path(p).is_relative_to(run) for p in manifest['outputs'])
        assert validate_receipt(run)[1]['project_id']==run.parent.name

@pytest.mark.parametrize('mode',['silent','duration','ambiguous','missing','outside','failed_generation'])
def test_failed_clip_preserves_receipt_and_blocks_review(box,calibration,monkeypatch,mode):
    execute,calls,root,source=box
    if mode in ['silent','duration']:
        replacement=calibration(silent=mode=='silent',duration=4 if mode=='duration' else 1)
        shutil.copyfile(replacement,source)
    elif mode in ['ambiguous','missing','outside']:
        original=sfx.run_workflow
        def altered(config,**kwargs):
            paths=original(config,**kwargs)
            if mode=='missing':return []
            if mode=='outside':return [source]
            second=paths[0].with_name('second.flac');shutil.copyfile(paths[0],second);return [paths[0],second]
        monkeypatch.setattr(sfx,'run_workflow',altered)
    else:
        def failure(*args,**kwargs):raise RuntimeError('synthetic dispatch failure')
        monkeypatch.setattr(sfx,'run_workflow',failure)
    with pytest.raises((ValueError,RuntimeError)):execute()
    run=root/'fixture_project/hit'
    receipt=json.loads((run/'020_audio/clip_receipt.json').read_text())
    assert receipt['status']=='FAILED' and not receipt['game_ready']
    assert not (run/'020_audio/listening_review_template.json').exists()
    with pytest.raises(ValueError,match='not technically passing'):validate_receipt(run)
    assert len(calls)<=1
    if mode!='failed_generation':assert (run/'010_generation/original.flac').exists()

@pytest.mark.parametrize('field',['wav','qa','receipt','generation'])
def test_tampered_evidence_blocks_listening_record(box,field):
    execute,_,_,_=box;run,_,_=execute();folder=run/'020_audio'
    files={'wav':folder/'hit.wav','qa':folder/'audio_qa.json','receipt':folder/'clip_receipt.json','generation':run/'010_generation/generation.json'}
    review=json.loads((folder/'listening_review_template.json').read_text())
    review.update(listened=True,reviewed_by='SYNTHETIC_TEST',reason='fixture validation',outcome='HOLD',checks={key:False for key in CHECKS})
    if field=='receipt':
        data=json.loads(files[field].read_text());data['clip']['category']='AMBIENCE';files[field].write_text(json.dumps(data))
    else:files[field].write_bytes(files[field].read_bytes()+b'\nchanged')
    with pytest.raises(ValueError):record_review(run,review,listened=True)
    assert not (folder/'listening_review.json').exists()

def test_explicit_hold_record_cannot_promote_or_overwrite(box):
    execute,_,_,_=box;run,_,_=execute();folder=run/'020_audio'
    review=json.loads((folder/'listening_review_template.json').read_text())
    review.update(listened=True,reviewed_by='SYNTHETIC_TEST',reason='synthetic hold only',outcome='HOLD',checks={key:False for key in CHECKS})
    with pytest.raises(ValueError,match='explicit listening'):record_review(run,review,listened=False)
    review['outcome']='PASS'
    with pytest.raises(ValueError,match='conflicts'):record_review(run,review,listened=True)
    review['outcome']='HOLD'
    record=record_review(run,review,listened=True)
    assert json.loads(record.read_text())['status']=='AUDIO_LISTENING_REVIEW_HOLD'
    assert json.loads(record.read_text())['game_ready'] is False
    with pytest.raises(FileExistsError):record_review(run,review,listened=True)
    assert json.loads((run/'run_manifest.json').read_text())['game_ready'] is False

def test_factory_audio_metadata_remains_offline(tmp_path):
    from assetpipe.factory import plan
    brief=make(asset_id='cue',output_class='SFX',prompt='synthetic UI cue')
    brief['project_id']='fixture';brief['audio']={'duration_seconds':2}
    (tmp_path/'brief.json').write_text(json.dumps(brief))
    request={'factory_contract_version':1,'factory_line':'SFX','output_mode':'AUDIO_ONLY','project_id':'fixture','asset_id':'cue','source':{'kind':'GENERATE','brief_ref':'brief.json'},'audio':{'duration_seconds':2,'category':'UI_CUE','clip_name':'cue'}}
    result=plan(request,tmp_path)
    assert result['audio_contract']['category']=='UI_CUE'
    assert result['dispatches']==result['budget_reservations']==result['provider_allocations']==0
    assert len(result['tasks'])==1 and result['tasks'][0]['kind']=='AUDIO'

def test_project_receipt_cannot_be_relabelled(box):
    execute,_,_,_=box;run,_,_=execute();p=run/'020_audio/clip_receipt.json'
    receipt=json.loads(p.read_text());receipt['project_id']='other_project';p.write_text(json.dumps(receipt))
    with pytest.raises(ValueError,match='project/run binding'):validate_receipt(run)

def test_symlink_original_escape_blocks_before_hash(box,monkeypatch):
    execute,_,root,source=box;run,_,_=execute();p=run/'020_audio/clip_receipt.json'
    link=run/'020_audio/escaped.flac';link.symlink_to(source)
    receipt=json.loads(p.read_text());receipt['artifacts'][0]['path']=str(link);p.write_text(json.dumps(receipt))
    from assetpipe.audio import sfx as receipts
    original=receipts.sha
    def guarded(path):
        assert path.is_relative_to(run)
        return original(path)
    monkeypatch.setattr(receipts,'sha',guarded)
    with pytest.raises(ValueError,match='outside configured roots'):validate_receipt(run)

def test_declared_flac_must_actually_be_flac(box,monkeypatch):
    execute,_,root,source=box
    shutil.copyfile(source.with_suffix('.wav'),source)
    with pytest.raises(ValueError,match='FLAC'):execute()
    receipt=json.loads((root/'fixture_project/hit/020_audio/clip_receipt.json').read_text())
    assert receipt['status']=='FAILED'

def test_existing_inspect_exposes_contained_receipt_only(box):
    from assetpipe.api import inspect_manifest
    from assetpipe.paths import RootResolver
    execute,_,root,source=box;run,_,manifest=execute();p=run/'run_manifest.json'
    p.write_text(json.dumps(manifest))
    assert inspect_manifest(p,RootResolver([root]))['audio_clip_receipt']==str(run/'020_audio/clip_receipt.json')
    manifest['audio_clip_receipt_path']=str(source);p.write_text(json.dumps(manifest))
    with pytest.raises(ValueError,match='inside its run'):inspect_manifest(p,RootResolver([root]))

@pytest.mark.parametrize('asset',['short_impact','ui_cue','ambience'])
def test_committed_example_contracts_have_no_video_tasks(asset):
    from assetpipe.factory import plan_file
    root=Path(__file__).resolve().parents[2]
    result=plan_file(root/f'examples/sfx_{asset}_factory.json',root)
    assert result['dispatches']==result['budget_reservations']==0
    assert [t['kind'] for t in result['tasks']]==['AUDIO']
