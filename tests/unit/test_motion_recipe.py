"""Recipe gates and real image/atlas replay; no network, model or human approvals."""
import copy
import json
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from assetpipe.factory.provenance import fingerprint
from assetpipe.manifests import write
from assetpipe.motion.recipe import plan_recipe, apply_recipe, inspect_recipe
from assetpipe.motion.package import pack_review_atlas


@pytest.fixture
def case(tmp_path):
    package = tmp_path / 'workspace/package'
    package.mkdir(parents=True)
    records = []
    for i in range(4):
        frame = Image.new('RGBA', (64,64), 'white')
        draw = ImageDraw.Draw(frame)
        draw.rectangle((16+i,8,44+i,55), fill='blue')
        draw.rectangle((24+i,16,35+i,28), fill='white')  # Enclosed white detail must survive.
        draw.rectangle((18,58,48,61), fill=(220,200,170))  # Explicit shadow residue.
        frame.putpixel((40,40),(0,0,255,128))  # Existing partial alpha cannot be restored to opaque.
        path = package / f'frame_{i}.png'
        frame.save(path)
        records.append({'source_frame_index':i+1,'path':str(path),'sha256':fingerprint(path),
                        'raw_path':str(path),'raw_sha256':fingerprint(path),'pivot':[32,62],
                        'alignment_offset':[0,0],'alignment_status':'BOTTOM_CENTER'})
    frames = pack_review_atlas(records,[64,64],24,package)
    write(package/'atlas.json',{'fps':'24','frames':frames})
    manifest = package/'run_manifest.json'
    write(manifest,{'type':'OFFLINE_MOTION_PACKAGE','status':'OFFLINE_PACKAGE_REVIEW_REQUIRED',
        'review_state':'REVIEW_REQUIRED','game_ready':False,'plan':{'mapped_output_class':'NONPIXEL_ANIMATION'},
        'probe':{'size':[64,64],'fps':'24','frame_count':4},
        'outputs':[{'path':str(package/name),'sha256':fingerprint(package/name)} for name in ['atlas.json','sprites.png']]})
    recipe={'schema_version':1,'kind':'MOTION_REVIEW_RECIPE','source_manifest':str(manifest),
            'source_sha256':fingerprint(manifest),'selection':{'start_frame':2,'end_frame':3},
            'alpha':{'method':'EDGE_CONNECTED_WHITE','background_rgb':[255,255,255],'tolerance':60,
                     'cleanup':{'regions':[[0,57,64,64]],'rgb_min':[170,145,110]}}}
    path=tmp_path/'recipe.json'
    write(path,recipe)
    return tmp_path,path,recipe,package,tmp_path/'workspace/candidate'


def apply(case):
    root,path,_,_,out=case
    plan=plan_recipe(path,root)
    manifest=apply_recipe(path,plan['plan_sha256'],out,root)
    return plan,manifest


def test_explicit_recipe_preserves_enclosed_white_and_records_pending_review(case):
    root,path,recipe,source,out=case
    before={str(p):fingerprint(p) for p in source.iterdir()}
    plan,manifest=apply(case)
    assert plan==plan_recipe(path,root)
    assert before=={str(p):fingerprint(p) for p in source.iterdir()}
    record=json.loads(manifest.read_text())
    atlas=json.loads((out/'atlas.json').read_text())
    assert [r['original_source_frame_index'] for r in atlas['frames']]==[2,3]
    assert [r['timestamp_seconds'] for r in atlas['frames']]==[0,1/24]
    assert record['generation_requests']==0 and record['game_ready'] is False
    for i in range(2):
        with Image.open(out/f'final/{i:04d}.png') as image:
            assert image.getpixel((0,0))[3]==0
            assert image.getpixel((30,20))==(255,255,255,255)
            assert image.getpixel((25,59))[3]==0
            assert image.getpixel((22,35))==(0,0,255,255)
            assert image.getpixel((40,40))==(0,0,255,128)
        with Image.open(out/f'source/{i:04d}.png') as image, Image.open(out/f'final/{i:04d}.png') as final:
            assert image.convert('RGB').tobytes()==final.convert('RGB').tobytes()
    review=json.loads((out/'review.json').read_text())
    assert review['reviewed_by'] is None and all(v is None for v in review['checks'].values())
    result=inspect_recipe(out,root,expected_sha256=fingerprint(manifest))
    assert result['status']=='ARTIFACT_INTEGRITY_PASS_REVIEW_REQUIRED'
    with pytest.raises(FileExistsError):
        apply_recipe(path,plan['plan_sha256'],out,root)


@pytest.mark.parametrize('change', ['reverse','outside','white','unknown','type','hash','region'])
def test_bad_contract_is_rejected_without_artifacts(case,change):
    root,path,recipe,source,out=case
    if change=='reverse': recipe['selection'].update(start_frame=3,end_frame=2)
    if change=='outside': recipe['selection']['end_frame']=9
    if change=='white': recipe['alpha']['background_rgb']=[0,255,0]
    if change=='unknown': recipe['approval']='APPROVED'
    if change=='type': recipe['selection']['start_frame']=True
    if change=='hash': recipe['source_sha256']='0'*64
    if change=='region': recipe['alpha']['cleanup']['regions']=[[0,0,65,64]]
    write(path,recipe)
    with pytest.raises(ValueError): plan_recipe(path,root)
    assert not out.exists()


@pytest.mark.parametrize('change',['recipe','frame','atlas','implementation_digest'])
def test_drift_invalidates_plan_before_output_creation(case,change):
    root,path,recipe,source,out=case
    plan=plan_recipe(path,root)
    if change=='recipe':
        recipe['selection']['start_frame']=1;write(path,recipe)
    if change=='frame': (source/'frame_1.png').write_bytes(b'drift')
    if change=='atlas': (source/'atlas.json').write_bytes(b'{}')
    digest='0'*64 if change=='implementation_digest' else plan['plan_sha256']
    with pytest.raises(ValueError): apply_recipe(path,digest,out,root)
    assert not out.exists()


@pytest.mark.parametrize('change',['delete','tamper','extra','review','manifest'])
def test_inspection_rejects_artifact_or_review_changes(case,change):
    root,path,recipe,source,out=case
    _,manifest=apply(case)
    digest=fingerprint(manifest)
    if change=='delete': (out/'sprites.png').unlink()
    if change=='tamper': (out/'masks/0000.png').write_bytes(b'drift')
    if change=='extra': (out/'surprise.json').write_text('{}')
    if change=='review': write(out/'review.json',{'status':'APPROVED'})
    if change=='manifest': write(manifest,{})
    with pytest.raises((ValueError,FileNotFoundError)):
        inspect_recipe(out,root,expected_sha256=digest)


def test_failed_transform_retains_intermediates_without_advancing(case):
    root,path,recipe,source,out=case
    recipe['alpha']['cleanup']={'regions':[[0,0,64,64]],'rgb_min':[0,0,0]}
    write(path,recipe)
    plan=plan_recipe(path,root)
    with pytest.raises(ValueError,match='EMPTY_FOREGROUND'):
        apply_recipe(path,plan['plan_sha256'],out,root)
    record=json.loads((out/'recipe_manifest.json').read_text())
    assert record['status']=='FAILED'
    assert (out/'masked/0000.png').exists() and not (out/'sprites.png').exists()
    with pytest.raises(ValueError,match='RUN_BLOCKED'):
        inspect_recipe(out,root,expected_sha256=fingerprint(out/'recipe_manifest.json'))


def test_preserve_alpha_and_output_boundaries(case):
    root,path,recipe,source,out=case
    recipe['alpha']={'method':'PRESERVE'};write(path,recipe)
    plan=plan_recipe(path,root)
    for target in [root/'src/forbidden',root/'workspace',source]:
        with pytest.raises((ValueError,FileExistsError)):
            apply_recipe(path,plan['plan_sha256'],target,root)
    apply_recipe(path,plan['plan_sha256'],out,root)
    with Image.open(out/'source/0000.png') as before, Image.open(out/'masked/0000.png') as after:
        assert before.convert('RGBA').tobytes()==after.convert('RGBA').tobytes()


def test_roots_and_source_status_are_not_bypassed(case,tmp_path):
    root,path,recipe,source,out=case
    with pytest.raises(ValueError): plan_recipe(path,root,allowed_roots=[])
    manifest=Path(recipe['source_manifest'])
    value=json.loads(manifest.read_text());value['status']='FAILED';write(manifest,value)
    recipe['source_sha256']=fingerprint(manifest);write(path,recipe)
    with pytest.raises(ValueError,match='SOURCE_BLOCKED'): plan_recipe(path,root)


def test_source_drift_during_transform_stops_candidate(case,monkeypatch):
    import assetpipe.motion.recipe as module
    root,path,_,source,out=case
    plan=plan_recipe(path,root)
    original=module.white_border_matte
    def drift(image):
        result=original(image)
        (source/'frame_1.png').write_bytes(b'changed during transform')
        return result
    monkeypatch.setattr(module,'white_border_matte',drift)
    with pytest.raises(ValueError): apply_recipe(path,plan['plan_sha256'],out,root)
    assert json.loads((out/'recipe_manifest.json').read_text())['status']=='FAILED'
    assert (out/'source/0000.png').exists()


def test_source_document_root_escape_is_rejected(case,tmp_path_factory):
    root,path,recipe,source,out=case
    outside=tmp_path_factory.mktemp('outside')/'manifest.json'
    write(outside,{})
    recipe['source_manifest']=str(outside);recipe['source_sha256']=fingerprint(outside)
    write(path,recipe)
    with pytest.raises(ValueError,match='outside configured roots'): plan_recipe(path,root)
    assert not out.exists()


def test_relative_recipe_references_keep_original_base_on_inspection(case):
    root,path,recipe,source,out=case
    recipe['source_manifest']='workspace/package/run_manifest.json';write(path,recipe)
    plan,manifest=apply(case)
    assert fingerprint(out/'recipe-input.json')==fingerprint(path)
    assert plan['recipe']['source_manifest']==str(source/'run_manifest.json')
    assert inspect_recipe(out,root,expected_sha256=fingerprint(manifest))['game_ready'] is False
