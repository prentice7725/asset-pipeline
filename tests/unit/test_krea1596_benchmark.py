import copy
from pathlib import Path
import pytest
from assetpipe.prompts import compile_prompt,workflow_values
from assetpipe.prompts.synthetic_fixture import build_anima_family_brief
from assetpipe.registry import load_registry
from assetpipe.styles.contracts import compile_krea_style_contract,load_style_contract
ROOT=Path(__file__).resolve().parents[2]
@pytest.mark.parametrize('workflow_id',['anima_base_rebuilt','anima_turbo','krea2_base'])
def test_candidate_contract_preserves_fixture_and_compiles_all_models(workflow_id):
 registry=load_registry(ROOT);brief=build_anima_family_brief(ROOT,'STYLE-101',workflow_id)
 if workflow_id=='krea2_base':brief['workflow_preferences']['preset']='character_portrait'
 compiled=compile_prompt(brief,registry[workflow_id],ROOT)
 values=workflow_values(compiled,registry[workflow_id],brief)
 assert (values['width'],values['height'])==(512,768)
 for text in ['plain blue knee-length coat','dark trousers','dark closed shoes','nocturnal city']:
  assert text in compiled['positive']
 assert compiled['style_contract_review']['approval_effect']=='NONE'
 assert compiled['spatial_relationships'][0]['image_side']=='IMAGE_RIGHT'
 if workflow_id=='krea2_base':
  assert compiled['negative_mode']=='NONE' and not compiled['negative']
  assert 'Exclude these visual features:' in compiled['positive']
  assert compiled['style_contract_compilation']['exclusion_mode']=='POSITIVE_TEXT_INSTRUCTION'
@pytest.mark.parametrize('index',range(101,125))
def test_all_candidate_contracts_have_traceable_sources(index):
 contract=load_style_contract(ROOT,f'STYLE-{index}')
 assert contract['source']['revision']=='eb690aa57bc6974af6b4b3b8c5a780195bcadf78'
 assert len(contract['required_style_features'])==3
 assert contract['evidence'][0]['original_sha256s']['classification']
def test_krea_structured_dialect_fails_closed_on_unknown_dialect():
 with pytest.raises(ValueError,match='STYLE_DIALECT_UNSUPPORTED'):
  compile_krea_style_contract(load_style_contract(ROOT,'STYLE-101'),adapter='krea2',dialect='unknown',model_profile='krea2',workflow_id='krea2_base')
