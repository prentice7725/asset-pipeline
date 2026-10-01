import pytest
from pathlib import Path
from scripts.style_lab import reserve


def test_budget_rejects_excess_before_submission():
    ledger = {'reserved_requests': 0}
    reserve(ledger, 1)
    with pytest.raises(ValueError, match='exhausted'):
        reserve(ledger, 1)
    assert ledger['reserved_requests'] == 1


@pytest.mark.parametrize('limit', [0, 17, -1, True])
def test_initial_budget_bounds(limit):
    ledger = {'reserved_requests': 0}
    with pytest.raises(ValueError):
        reserve(ledger, limit)
    assert ledger['reserved_requests'] == 0


import json
from PIL import Image
from assetpipe.brief import make
from assetpipe.pipelines import revalidate_static_candidate
from assetpipe.prompt_mining import sha256
from scripts import style_lab

ROOT = Path(__file__).resolve().parents[2]


def test_revalidated_source_reaches_review_without_generation_or_approval(tmp_path):
    source = ROOT/'tests/assets/true_pixel_art.png'
    before = sha256(source)
    brief = make(asset_id='revalidate_fixture',output_class='PIXEL_STATIC',prompt='Existing fixture only')
    with Image.open(source) as image:
        brief['constraints']['resolution'] = list(image.size)
    brief['workflow_preferences']['id'] = 'anima_pixelate_x4_vae'
    directory = tmp_path/'static'
    path = revalidate_static_candidate(brief,source,ROOT,directory)
    record = json.loads(path.read_text())
    assert record['status'] == 'RESOLUTION_REVIEW_REQUIRED'
    assert record['generation']['new_requests'] == 0
    assert sha256(source) == before == sha256(directory/'010_existing_candidate/source.png')
    assert record['qa_results'][-2]['status'] == 'PASS'
    assert not (directory/'060_aseprite').exists()
    assert not (directory/'approval_record.json').exists()


def test_revalidated_bad_pixels_keep_export_locked(tmp_path):
    source = ROOT/'tests/assets/downscaled_illustration.png'
    brief = make(asset_id='bad_candidate',output_class='PIXEL_STATIC',prompt='Failure fixture')
    with Image.open(source) as image:
        brief['constraints']['resolution'] = list(image.size)
    with pytest.raises(ValueError,match='Pixel Gate failed'):
        revalidate_static_candidate(brief,source,ROOT,tmp_path/'failed')
    assert not (tmp_path/'failed/050_resolution').exists()
    assert not (tmp_path/'failed/060_aseprite').exists()


def test_missing_models_prevent_dispatch_even_when_static_review_is_held(monkeypatch,tmp_path):
    monkeypatch.setattr(style_lab,'ROOT',tmp_path)
    out=tmp_path/'workspace/style_lab/cohorts/held'
    out.mkdir(parents=True)
    static=out/'static'
    static.mkdir()
    (static/'run_manifest.json').write_text(json.dumps({'output_class':'PIXEL_STATIC','status':'EXPORT_READY_REVIEW_REQUIRED','qa_results':[]}))
    (out/'manifest.json').write_text(json.dumps({'harness_version':2,'historical_regression':{'status':'PASS'},
        'static_integration':{'status':'EXPORT_READY_REVIEW_REQUIRED','run_directory':str(static)},
        'current_animation_e2e':{'status':'NOT_RUN'},'style_experiment':{'status':'NOT_RUN'},'budget':{'limit':12,'reserved_requests':0},'samples':[]}))
    def forbidden(*args,**kwargs):
        raise AssertionError('No dispatch while approval is pending')
    monkeypatch.setattr(style_lab,'create',forbidden)
    monkeypatch.setattr(style_lab,'execute_prepared',forbidden)
    assert style_lab.main(['--cohort',str(out),'--generate']) == 3
    record=json.loads((out/'manifest.json').read_text())
    assert record['status']=='BLOCKED_MODEL_HASHES_REQUIRED'
    assert record['budget']['reserved_requests']==0
    assert record['style_experiment']['status']=='NOT_RUN'


def test_historical_equivalence_does_not_claim_current_e2e(tmp_path):
    result=style_lab.historical_comparison(tmp_path)
    assert result['status']=='UNAVAILABLE'
    assert result['scope']=='HISTORICAL_ARTIFACT_EQUIVALENCE_ONLY'


def test_unsupported_master_is_blocked_after_current_approval_preflight(monkeypatch,tmp_path):
    canonical=tmp_path/'canonical.png'
    other=tmp_path/'other.png'
    Image.new('RGBA',(4,4),(0,0,255,255)).save(canonical)
    Image.new('RGBA',(4,4),(255,0,0,255)).save(other)
    reference={'production':{'static_master':str(canonical)}}
    called=[]
    monkeypatch.setattr(style_lab,'preflight',lambda brief: called.append(True))
    monkeypatch.setattr(style_lab,'load',lambda path: reference)
    brief={'production':{'static_master':str(other),'direct_profile':'blue_tunic_white_matte_v1'}}
    with pytest.raises(ValueError,match='different master'):
        style_lab.compatible_integration(brief,tmp_path)
    assert called==[True]


@pytest.mark.parametrize('kind',['PIXEL_STATIC','NONPIXEL_IMAGE'])
def test_static_experiments_dispatch_without_animation_approval_once(monkeypatch,tmp_path,kind):
    monkeypatch.setattr(style_lab,'ROOT',tmp_path)
    out=tmp_path/'workspace/style_lab/cohorts/independent'
    out.mkdir(parents=True)
    prepared=out/'prepared.json'
    prepared.write_text(json.dumps({'brief':{'output_class':kind},'compiled':{}}))
    row={'id':'fixture','workflow_id':'fixture','seed':1,'status':'PREPARED','prepared':str(prepared.relative_to(tmp_path)),'prepared_sha256':sha256(prepared)}
    (out/'manifest.json').write_text(json.dumps({'harness_version':2,'historical_regression':{'status':'PASS'},
        'static_integration':{'status':'EXPORT_READY_REVIEW_REQUIRED','human_review':'HELD_NOT_REVIEWED'},
        'current_animation_e2e':{'status':'NOT_RUN'},'style_experiment':{'status':'NOT_RUN'},
        'budget':{'limit':12,'reserved_requests':0},'samples':[row]}))
    monkeypatch.setattr(style_lab,'verify_models_and_nodes',lambda *args: {'fixture':'fixture-only'})
    calls=[]
    def dispatch(root,directory,saved,seed,models):
        record=json.loads((out/'manifest.json').read_text())
        assert record['samples'][0]['status']=='RESERVED'
        assert record['budget']['reserved_requests']==1
        calls.append(True)
        directory.mkdir(parents=True)
        (directory/'run_manifest.json').write_text(json.dumps({'status':'FAILED','generation':{'comfy_prompt_id':'fixture-only'},'qa_results':[],'outputs':[]}))
        raise ValueError('Fixture failure; no retry')
    monkeypatch.setattr(style_lab,'execute_prepared',dispatch)
    monkeypatch.setattr(style_lab,'create',lambda *args: pytest.fail('Animation must stay gated'))
    argv=['--cohort',str(out),'--generate','--model-root',str(tmp_path)]
    assert style_lab.main(argv)==0
    assert style_lab.main(argv)==0
    record=json.loads((out/'manifest.json').read_text())
    assert calls==[True]
    assert record['budget']['reserved_requests']==1
    assert record['samples'][0]['status']=='FAILED'
    assert record['current_animation_e2e']['status']=='NOT_RUN'
    assert not list(out.rglob('approval_record.json'))


def test_compiled_output_folder_is_not_created_before_workflow_submission(monkeypatch,tmp_path):
    source=ROOT/'tests/assets/true_pixel_art.png'
    brief=style_lab.load(ROOT/'examples/prompt_mining/character.yaml')
    brief['output_class']='PIXEL_STATIC'
    brief['constraints']['resolution']=None
    compiled=style_lab.compile_candidate(ROOT,'mined_clean_anime_cel',brief,'anima_pixelate_x4_vae')
    def runner(config,**kwargs):
        target=kwargs['output_dir']
        assert not target.exists()
        assert kwargs['prompt']==compiled['positive']
        target.mkdir()
        return [source]
    monkeypatch.setattr(style_lab,'run_workflow',runner)
    path=style_lab.execute_prepared(ROOT,tmp_path/'run',{'brief':brief,'compiled':compiled},1,{})
    assert (path.parent/'010_generation/compiled_prompt.json').is_file()
    assert json.loads(path.read_text())['game_ready'] is False
