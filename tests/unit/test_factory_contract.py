"""M3.0 synthetic plans. No external generation or real review records."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from PIL import Image
from jsonschema import Draft202012Validator
from assetpipe.brief import make, SCHEMA as LEGACY_SCHEMA
from assetpipe.factory import plan, plan_file, SCHEMA, validate
from assetpipe.paths import RootResolver

def save(path, value):
    path.write_text(json.dumps(value),encoding='utf-8')
    return path

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

@pytest.fixture
def box(tmp_path, monkeypatch):
    # A planned task must never reach legacy dispatch or dependency probes.
    import assetpipe.pipelines
    import assetpipe.api
    def forbidden(*args, **kwargs):
        raise AssertionError('Dry-run attempted runtime execution')
    monkeypatch.setattr(assetpipe.pipelines,'create',forbidden)
    monkeypatch.setattr(assetpipe.api.ComfyClient,'check_connection',forbidden)
    monkeypatch.setattr(assetpipe.api,'diagnose_providers',forbidden,raising=False)
    def request(line='NONPIXEL',mode='IMAGE_ONLY',kind='GENERATE',count=1):
        value={'factory_contract_version':1,'factory_line':line,'output_mode':mode,
               'project_id':'test_project','asset_id':'synthetic','source':{'kind':kind}}
        if line in ['NONPIXEL','PIXEL64']:
            value['image']={'style_source':'EXPLICIT_UNAPPROVED_TEST_CONTRACT'}
            if line=='PIXEL64': value['image']['logical_size']=[64,64]
        if line=='SFX': value['audio']={'duration_seconds':2}
        if mode=='IMAGE_TO_SPRITE':
            value['motion']={'action':'explicit_test_motion','fps':12,'duration_seconds':1.5,
                             'target_frames':8,'background_policy':'PRESERVE_OR_REVIEW','workflow_id':'unverified_test_only'}
        cls={'NONPIXEL':'NONPIXEL_IMAGE','PIXEL64':'PIXEL_STATIC','SFX':'SFX','REFERENCE_MOTION':'NONPIXEL_IMAGE'}[line]
        if kind=='GENERATE':
            b=make(asset_id='synthetic',output_class=cls,prompt='synthetic contract only')
            b['project_id']='test_project'; b['workflow_preferences']['id']='explicit_fixture_workflow'
            if line=='PIXEL64': b['constraints']['resolution']=[64,64]
            if line=='SFX': b['audio']=deepcopy(value['audio'])
            save(tmp_path/'brief.json',b);value['source']['brief_ref']='brief.json'
        else:
            images=[]
            for i in range(count):
                p=tmp_path/f'image{i}.png'; Image.new('RGB',(64,64),(10+i,30,50)).save(p)
                images.append({'path':p.name,'sha256':sha(p),'role':['IDENTITY_PRIMARY','ALTERNATE_VIEW','POSE_ANCHOR'][i%3]})
                if kind=='EXTERNAL_IMAGES':images[-1].update(ownership='SYNTHETIC_FIXTURE',license='SYNTHETIC_FIXTURE')
            value['source']['images']=images
            if kind=='EXISTING_RUN':
                parent_brief=make(asset_id='old_parent',output_class=cls,prompt='immutable source identity')
                parent_brief['project_id']='test_project'
                parent_brief['identity']['canonical_traits']=['preserve fixture identity']
                parent_brief['workflow_preferences']['id']='explicit_parent_model_workflow'
                if line=='PIXEL64':parent_brief['constraints']['resolution']=[64,64]
                manifest={'run_id':'immutable-parent','asset_id':'old_parent','project_id':'test_project',
                          'output_class':cls,'asset_brief':parent_brief,'status':'CANDIDATE_READY_REVIEW_REQUIRED','outputs':[i['path'] for i in images]}
                p=save(tmp_path/'parent.json',manifest)
                value['source'].update(manifest_ref=p.name,manifest_sha256=sha(p))
        return value
    return tmp_path,request

@pytest.mark.parametrize('line,mode,count,expected',[
    ('NONPIXEL','IMAGE_ONLY',1,'NONPIXEL_IMAGE'),('NONPIXEL','IMAGE_TO_SPRITE',1,'NONPIXEL_ANIMATION'),
    ('PIXEL64','IMAGE_ONLY',1,'PIXEL_STATIC'),('PIXEL64','IMAGE_TO_SPRITE',1,'PIXEL_ANIMATION'),
    ('SFX','AUDIO_ONLY',1,'SFX'),
    *[('REFERENCE_MOTION','IMAGE_TO_SPRITE',n,'NONPIXEL_ANIMATION') for n in (1,2,3)]])
def test_valid_matrix_without_dispatch(box,line,mode,count,expected):
    root,request=box
    value=request(line,mode,'EXTERNAL_IMAGES' if line=='REFERENCE_MOTION' else 'GENERATE',count)
    Draft202012Validator(SCHEMA).validate(value)
    p=save(root/'request.json',value)
    before={f.name:sha(f) for f in root.iterdir() if f.is_file()}
    result=plan_file(p,root)
    assert result['mapped_output_class']==expected and result['status']=='OFFLINE_CONTRACT_PASS'
    assert result['dispatches']==result['budget_reservations']==result['provider_allocations']==0
    assert result['game_ready'] is False and result['review_state']=='NOT_EVALUATED'
    if mode=='IMAGE_TO_SPRITE':
        assert [t['id'] for t in result['tasks']]==['source','motion','frames','sprites']
        assert 'BLOCKED_BACKEND_NOT_VERIFIED' in result['remaining_gates']
        assert result['motion_contract']==value['motion']
        assert result['tasks'][1]['source_binding']['required_before_dispatch'] is True
        assert all(t['run_owner']=='motion' for t in result['tasks'][1:])
        assert [t['new_run'] for t in result['tasks'][1:]]==[True,False,False]
    else:
        assert len(result['tasks'])==1 and result['tasks'][0]['kind'] in ['IMAGE','AUDIO']
        assert result['motion_contract'] is None
    if line=='REFERENCE_MOTION':
        assert len(result['images'])==count
        assert result['tasks'][0]['kind']=='EXISTING_IMAGE'
    else:
        assert result['source_brief']['workflow_preferences']['id']=='explicit_fixture_workflow'
    assert {f.name:sha(f) for f in root.iterdir() if f.is_file()}==before

@pytest.mark.parametrize('line,mode,count',[
    ('NONPIXEL','IMAGE_ONLY',1),('NONPIXEL','IMAGE_TO_SPRITE',1),
    ('PIXEL64','IMAGE_ONLY',1),('PIXEL64','IMAGE_TO_SPRITE',1),
    *[('REFERENCE_MOTION','IMAGE_TO_SPRITE',n) for n in (1,2,3)]])
def test_existing_parent_never_regenerated_or_modified(box,line,mode,count):
    root,request=box;value=request(line,mode,'EXISTING_RUN',count)
    before=sha(root/'parent.json')
    result=plan(value,root)
    assert result['parent']['manifest_sha256']==before
    assert result['parent']['mutation_allowed'] is False
    assert result['parent']['review_state']=='NOT_EVALUATED'
    assert result['tasks'][0]['new_run'] is False
    assert result['source_brief']==json.loads((root/'parent.json').read_text())['asset_brief']
    assert sha(root/'parent.json')==before

@pytest.mark.parametrize('line,mode',[
    ('NONPIXEL','AUDIO_ONLY'),('PIXEL64','AUDIO_ONLY'),('SFX','IMAGE_ONLY'),('REFERENCE_MOTION','IMAGE_ONLY')])
def test_wrong_line_modes_rejected(box,line,mode):
    root,request=box
    value=request();value.update(factory_line=line,output_mode=mode)
    with pytest.raises(ValueError,match='FACTORY_REQUEST_INVALID'):plan(value,root)

@pytest.mark.parametrize('change', ['zero','four','missing_role','duplicate_role','style_only','missing_license','duplicate_path','hash_drift'])
def test_invalid_reference_contract(box,change):
    root,request=box;value=request('REFERENCE_MOTION','IMAGE_TO_SPRITE','EXTERNAL_IMAGES',2)
    images=value['source']['images']
    if change=='zero':images.clear()
    elif change=='four':images.extend(deepcopy(images))
    elif change=='missing_role':images[0].pop('role')
    elif change=='duplicate_role':images[1]['role']=images[0]['role']
    elif change=='style_only':value['source']['images']=[{**images[0],'role':'STYLE_REFERENCE'}]
    elif change=='missing_license':images[0].pop('license')
    elif change=='duplicate_path':images[1].update(path=images[0]['path'],sha256=images[0]['sha256'])
    elif change=='hash_drift':images[0]['sha256']='0'*64
    with pytest.raises(ValueError):plan(value,root)

@pytest.mark.parametrize('change',['version','unknown_field','motion_on_still','missing_motion','32px','brief_project','brief_class','brief_asset','audio_duration'])
def test_fail_closed_contract_and_legacy_mapping(box,change):
    root,request=box
    value=request('SFX','AUDIO_ONLY') if change=='audio_duration' else request('PIXEL64' if change=='32px' else 'NONPIXEL')
    if change=='version':value['factory_contract_version']=2
    elif change=='unknown_field':value['auto_fallback']=True
    elif change=='motion_on_still':value['motion']={'action':'walk'}
    elif change=='missing_motion':value['output_mode']='IMAGE_TO_SPRITE'
    else:
        b=json.loads((root/'brief.json').read_text())
        if change=='32px':b['constraints']['resolution']=[32,32]
        elif change=='brief_project':b['project_id']='other_project'
        elif change=='brief_class':b['output_class']='PIXEL_STATIC'
        elif change=='brief_asset':b['asset_id']='other_asset'
        elif change=='audio_duration':b['audio']['duration_seconds']=3
        save(root/'brief.json',b)
    with pytest.raises(ValueError):plan(value,root)

@pytest.mark.parametrize('location',['brief_ref','image','nested_candidate','nested_evidence','transitive'])
def test_outside_roots_rejected_before_read(box,tmp_path_factory,location,monkeypatch):
    root,request=box;outside=tmp_path_factory.mktemp('outside')
    external=outside/'secret.png';Image.new('RGB',(64,64)).save(external)
    value=request('REFERENCE_MOTION','IMAGE_TO_SPRITE','EXTERNAL_IMAGES') if location=='image' else request()
    if location=='image':value['source']['images'][0].update(path=str(external),sha256=sha(external))
    elif location=='brief_ref':value['source']['brief_ref']=str(save(outside/'brief.json',json.loads((root/'brief.json').read_text())))
    else:
        b=json.loads((root/'brief.json').read_text())
        if location=='nested_candidate':b['unused']={'candidate':str(external)}
        elif location=='nested_evidence':b['unused']={'evidence':[{'path':str(external)}]}
        else:
            save(root/'report.json',{'evidence':[{'export':str(external)}]});b['resolution_report']='report.json'
        save(root/'brief.json',b)
    # No opening or hashing of the escaped file, even if the source is otherwise invalid.
    from assetpipe.factory import provenance
    original=provenance.fingerprint
    def guarded(path):
        assert path.is_relative_to(root)
        return original(path)
    monkeypatch.setattr(provenance,'fingerprint',guarded)
    with pytest.raises(ValueError,match='outside configured roots'):plan(value,root)

@pytest.mark.parametrize('kind',['symlink','junction'])
def test_reparse_escape_and_alias_duplicate(box,tmp_path_factory,kind):
    if kind=='junction' and os.name!='nt':pytest.skip('Windows junction test')
    root,request=box;value=request('REFERENCE_MOTION','IMAGE_TO_SPRITE','EXTERNAL_IMAGES',2)
    outside=tmp_path_factory.mktemp('escape');Image.new('RGB',(64,64)).save(outside/'escape.png')
    alias=root/'alias'
    if kind=='junction':
        result=subprocess.run(['cmd','/c','mklink','/J',str(alias),str(outside)],capture_output=True)
        assert result.returncode==0,result.stderr
    else:alias.symlink_to(outside,target_is_directory=True)
    value['source']['images'][0]['path']='alias/escape.png'
    with pytest.raises(ValueError,match='outside configured roots'):plan(value,root)

@pytest.mark.parametrize('change',['manifest_hash','output','project','output_class','missing_brief','brief_project'])
def test_parent_binding_and_hash_drift(box,change):
    root,request=box;value=request('NONPIXEL','IMAGE_TO_SPRITE','EXISTING_RUN')
    if change=='manifest_hash':value['source']['manifest_sha256']='0'*64
    else:
        p=root/'parent.json';m=json.loads(p.read_text())
        if change=='output':m['outputs']=[]
        elif change=='project':m['project_id']='foreign'
        elif change=='output_class':m['output_class']='NONPIXEL_ANIMATION'
        elif change=='missing_brief':m.pop('asset_brief')
        else:m['asset_brief']['project_id']='foreign'
        save(p,m);value['source']['manifest_sha256']=sha(p)
    with pytest.raises(ValueError):plan(value,root)

def test_schema_export_and_legacy_schema_unchanged():
    root=Path(__file__).resolve().parents[2]
    assert json.loads((root/'schemas/factory_request_v1.schema.json').read_text())==SCHEMA
    assert json.loads((root/'schemas/asset_brief.schema.json').read_text())==LEGACY_SCHEMA
    assert 'factory_contract_version' not in LEGACY_SCHEMA['properties']

@pytest.mark.parametrize('command',['plan','dry-run','inspect'])
def test_cli_presentations_are_read_only(box,command,capsys):
    from assetpipe.cli import main
    root,request=box;p=save(root/'request.json',request())
    before=sha(p)
    assert main(['--root',str(root),'factory',command,'--request',str(p)])==0
    result=json.loads(capsys.readouterr().out)
    assert result['budget_reservations']==0 and len(result['tasks'])==1
    assert sha(p)==before

def test_explicit_extra_root_is_required(box,tmp_path_factory):
    root,request=box;value=request();external=tmp_path_factory.mktemp('allowed')
    path=save(external/'brief.json',json.loads((root/'brief.json').read_text()))
    value['source']['brief_ref']=str(path)
    p=save(root/'request.json',value)
    with pytest.raises(ValueError):plan_file(p,root)
    assert plan_file(p,root,allowed_roots=[root,external])['status']=='OFFLINE_CONTRACT_PASS'

def test_pixel64_parent_cannot_silently_promote_32px_contract(box):
    root,request=box;value=request('PIXEL64','IMAGE_TO_SPRITE','EXISTING_RUN')
    p=root/'parent.json';m=json.loads(p.read_text());m['asset_brief']['constraints']['resolution']=[32,32]
    save(p,m);value['source']['manifest_sha256']=sha(p)
    with pytest.raises(ValueError,match='parent logical output must be 64x64'):plan(value,root)
