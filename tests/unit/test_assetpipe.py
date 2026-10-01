import copy
import json
from pathlib import Path
import pytest
from PIL import Image
from assetpipe.brief import make, validate, load
from assetpipe.registry import load_registry
from assetpipe.router import route
from assetpipe.pipelines import create
from assetpipe.pipelines.pixel_static import export_reviewed
from assetpipe._ported.config import load_config

ROOT = Path(__file__).resolve().parents[2]

def brief():
    return make(asset_id='test', output_class='NONPIXEL_IMAGE', prompt='fantasy scout')

def test_validation_rejects_missing_contract_and_unsafe_id():
    value = brief()
    value['asset_id'] = '../escape'
    with pytest.raises(ValueError):
        validate(value)
    value = brief()
    del value['source_notes']
    with pytest.raises(ValueError):
        validate(value)

def test_animation_requires_action():
    with pytest.raises(ValueError, match='action'):
        make(asset_id='test', output_class='PIXEL_ANIMATION', reference='test.png')

def test_document_notes_preserve_unspecified_traits():
    value = load(ROOT / 'examples/character_test_brief.yaml')
    assert 'face details' in value['unspecified_elements']
    assert value['identity']['canonical_traits'] == ['fantasy scout', 'short brown hair', 'blue cloak', 'light armor', 'dagger']
    assert all(n['classification'] == 'EXPLICIT' for n in value['source_notes'])

def test_router_status_and_priority_and_tags():
    value = brief()
    registry = load_registry(ROOT)
    decision = route(value, registry)
    assert decision['selected_workflow'] == 'krea2_base'
    value['workflow_preferences']['tags'] = ['anime', 'general', 'portrait']
    assert route(value, registry)['selected_workflow'] == 'anima_base'
    registry['anima_base']['status'] = 'VALIDATED'
    assert route(value, registry)['selected_workflow'] == 'krea2_base'
    value['workflow_preferences']['id'] = 'anima_base'
    assert route(value, registry)['selected_workflow'] == 'anima_base'
    registry['anima_base']['status'] = 'REJECTED'
    with pytest.raises(ValueError):
        route(value, registry)

def test_reference_capability_is_never_ignored():
    value = make(asset_id='test', output_class='NONPIXEL_IMAGE', reference='character.png')
    with pytest.raises(ValueError, match='capabilities'):
        route(value, load_registry(ROOT))

def test_experimental_requires_explicit_opt_in():
    value = brief()
    value['workflow_preferences']['id'] = 'tomohi_character'
    with pytest.raises(ValueError, match='opt-in'):
        route(value, load_registry(ROOT))
    value['workflow_preferences']['allow_experimental'] = True
    assert route(value, load_registry(ROOT))['selected_workflow'] == 'tomohi_character'

def test_failed_routing_preserves_manifest_without_provider_call(tmp_path):
    value = brief()
    value['workflow_preferences']['id'] = 'missing'
    destination = tmp_path / 'failure'
    with pytest.raises(ValueError):
        create(value, ROOT, destination)
    manifest = json.loads((destination / 'run_manifest.json').read_text())
    assert manifest['status'] == 'FAILED'
    assert manifest['outputs'] == []
    with pytest.raises(FileExistsError):
        create(value, ROOT, destination)

def test_create_uses_same_document_preflight_as_mcp(tmp_path):
    value = brief()
    source = ROOT / 'tests/fixtures/character_test.md'
    value['source'] = {'type': 'DOCUMENTS', 'paths': [str(source)], 'references': []}
    value['source_notes'] = [{'classification': 'UNSPECIFIED', 'text': 'canon not extracted', 'source': str(source)}]
    value['identity']['canonical_traits'] = []
    destination = tmp_path / 'document_failure'
    with pytest.raises(ValueError, match='Source-backed canonical traits'):
        create(value, ROOT, destination)
    manifest = json.loads((destination / 'run_manifest.json').read_text())
    assert manifest['status'] == 'FAILED'
    assert not (destination / '010_generation').exists()


def test_negative_constraints_require_provider_capability():
    value = brief()
    value['forbidden_elements'] = ['heavy armor']
    value['workflow_preferences']['id'] = 'krea2_base'
    with pytest.raises(ValueError, match='capabilities'):
        route(value, load_registry(ROOT))

def test_static_review_cannot_be_bypassed(tmp_path):
    review = tmp_path / 'review.json'
    review.write_text(json.dumps({'status': 'SELECTED', 'reviewed': True}))
    with pytest.raises(ValueError, match='review'):
        export_reviewed(load_config(ROOT / 'config/pipeline.yaml'), tmp_path, review, {'status': 'RESOLUTION_REVIEW_REQUIRED'})

def test_bad_master_approval_stops_before_motion_decode(tmp_path):
    value = load(ROOT / 'examples/pixel_animation_smoke.yaml')
    master = tmp_path / 'master.png'
    Image.new('RGBA', (8, 8), (0, 0, 255, 255)).save(master)
    value['production']['static_master'] = str(master)
    record = tmp_path / 'approval.json'
    record.write_text(json.dumps({'status': 'APPROVED_STATIC_MASTER', 'approved_export_sha256': 'wrong'}))
    value['production']['approval_record'] = str(record)
    with pytest.raises(ValueError, match='approval/hash'):
        create(value, ROOT, tmp_path / 'run')
    assert not (tmp_path / 'run/010_source_frames').exists()

def test_ported_modules_have_no_runtime_dependency_on_legacy():
    for path in (ROOT / 'src/assetpipe/_ported').rglob('*.py'):
        assert 'from pixel_pipeline' not in path.read_text(encoding='utf-8')

def test_direct_frames_are_identical_to_verified_legacy():
    new = ROOT / 'workspace/smokes/pixel_attempt_04/020_direct/040_direct_pixel_frames'
    old = ROOT.parent / 'pixel-pipeline/workspace/runs/sword_warrior_001/phase13_step3_direct_walk/attempt_05/040_direct_pixel_frames'
    if not new.exists() or not old.exists():
        pytest.skip('Local migration benchmark data unavailable')
    paths = list(new.glob('*.png'))
    assert len(paths) == 8
    for path in paths:
        with Image.open(path) as a, Image.open(old / path.name) as b:
            assert a.convert('RGBA').tobytes() == b.convert('RGBA').tobytes()
