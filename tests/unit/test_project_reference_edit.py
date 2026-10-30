"""Project reference-edit coordinator and provider handoff; fake generation only."""
import hashlib
import json
from pathlib import Path

from PIL import Image
import pytest
import yaml

from assetpipe.factory.variant import plan_variant, run_variant
from assetpipe.pipelines import create
from assetpipe.prompts import compile_prompt
from tests.unit.test_cli_providers import Sandbox
from tests.unit.test_project_portrait import portrait


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value),encoding='utf-8')
    return path


@pytest.fixture(params=['grok_imagine','codex_imagegen'])
def project_lab(tmp_path,monkeypatch,request):
    import assetpipe.portrait_delivery as delivery
    from assetpipe.providers.comfyui import ComfyUIProvider
    box=Sandbox(tmp_path,monkeypatch)
    sot_path=box.root/'config/styles/projects/isekai_examiner/visual_sot.yaml'
    sot=yaml.safe_load(sot_path.read_text(encoding='utf-8'))
    policy=sot['asset_class_contracts']['character_portrait']['delivery_profile']
    policy.update(model_path=str(box.root/'models/pinned.onnx'),model_roots=[str(box.root/'models')])
    sot_path.write_text(yaml.safe_dump(sot,allow_unicode=True),encoding='utf-8')
    monkeypatch.setattr(delivery,'preflight',lambda value: None)
    def generated(self,brief,workflow,directory,seed):
        directory.mkdir(parents=True)
        save(directory/'compiled_prompt.json',compile_prompt(brief,workflow,box.root))
        source=directory/'source.png'; Image.new('RGB',(64,64),'white').save(source)
        return [source]
    monkeypatch.setattr(ComfyUIProvider,'generate',generated)
    def processed(source,resolution,value,directory):
        assert value['operation']=='LOCAL_MASK_UNIFORM_CONTAIN'
        directory.mkdir(parents=True)
        image=Image.new('RGBA',tuple(resolution),(20,40,60,255)); image.putpixel((0,0),(0,0,0,0))
        path=directory/'portrait.png'; image.save(path)
        return path,{'human_review':'REVIEW_REQUIRED','source':str(source),'source_sha256':digest(source),
                     'output_sha256':digest(path),'crop':False}
    monkeypatch.setattr(delivery,'process',processed)
    base=create(portrait(),box.root,box.root/'workspace/base',None)
    data=json.loads(Path(base).read_text())
    image=Path(data['outputs'][0])
    job={'schema_version':1,'kind':'FACTORY_IDENTITY_VARIANT_JOB','project_id':'isekai_examiner',
         'asset_id':'human_surprised','base':{'manifest_ref':str(base),'manifest_sha256':digest(base),
             'image':{'path':str(image),'sha256':digest(image)},'selected_by':'unit-test human choice',
             'reason':'synthetic contract fixture; no real art approval'},
         'variation':{'kind':'EXPRESSION','target':'surprised'},'provider':{'workflow_id':request.param}}
    box.job=save(box.root/'workspace/job.json',job)
    box.base_image=image
    box.editor=request.param
    box.grok(); box.codex()
    (tmp_path/'grok_home').mkdir(exist_ok=True)
    (tmp_path/'codex_home').mkdir(exist_ok=True)
    box.allowed=[box.root,tmp_path/'grok_home',tmp_path/'codex_home']
    return box


@pytest.mark.parametrize('changed_sot',[False,True])
def test_project_variant_pins_contract_and_preserves_selected_rgba(project_lab,changed_sot):
    box=project_lab
    editor_dir=box.grok_dir if box.editor=='grok_imagine' else box.codex_dir
    plan=plan_variant(box.job,box.root,allowed_roots=box.allowed)
    assert plan['project_reference_edit']['reference_input']=='EXACT_RGBA'
    auth=save(box.root/'workspace/auth.json',{'schema_version':1,'type':'IDENTITY_VARIANT_AUTHORIZATION',
        'authorization_id':'b'*32,'project_id':'isekai_examiner','asset_id':'human_surprised',
        'plan_sha256':plan['plan_sha256'],'workflow_id':plan['workflow']['id'],
        'workflow_sha256':plan['workflow']['hash'],'max_requests':1,'authorized_by':'test','reason':'fake E2E'})
    if changed_sot:
        sot=box.root/'config/styles/projects/isekai_examiner/visual_sot.yaml'
        sot.write_text(sot.read_text(encoding='utf-8')+'\n# changed after plan\n',encoding='utf-8')
        with pytest.raises(ValueError,match='PLAN_CHANGED'):
            run_variant(box.job,plan['plan_sha256'],auth,box.root,authorize_generation=True,allowed_roots=box.allowed)
        assert not (box.root/'workspace/factory_budget'/('b'*32)).exists()
        assert box.calls(editor_dir)==[]
        return
    receipt=run_variant(box.job,plan['plan_sha256'],auth,box.root,authorize_generation=True,allowed_roots=box.allowed)
    result=json.loads(receipt.read_text())
    assert result['status']=='CANDIDATE_REVIEW_REQUIRED' and result['game_ready'] is False
    manifest=json.loads(Path(result['manifest_path']).read_text())
    provider=manifest['generation']['provider']
    assert provider['tool']==plan['workflow']['edit_tool'] and provider['reference']['sha256']==digest(box.base_image)
    assert provider['reference']['contract']=='EXACT_RGBA_UNCHANGED'
    assert len(box.calls(editor_dir))==1
    assert manifest['generation']['raw_outputs']!=manifest['outputs']
    assert manifest['qa_results'][0]['resolution']==[1212,1300]
    with pytest.raises(ValueError,match='ALREADY_RESERVED'):
        run_variant(box.job,plan['plan_sha256'],auth,box.root,authorize_generation=True,allowed_roots=box.allowed)
    assert len(box.calls(editor_dir))==1
