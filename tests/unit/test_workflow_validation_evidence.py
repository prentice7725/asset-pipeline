"""A ComfyUI workflow is VALIDATED only while its evidence matches the current graph and node source."""
import copy
import hashlib
import json

import pytest

from assetpipe.brief import make
from assetpipe.registry import load_registry, workflow_evidence_problem
from assetpipe.router import route
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _setup(tmp_path, **changes):
    node = tmp_path / 'node.py'
    node.write_text('node', encoding='utf-8')
    record = {'kind': 'COMFYUI_WORKFLOW_VALIDATION', 'workflow_id': 'wf', 'result': 'REAL_GENERATION_VERIFIED',
              'workflow_sha256': 'abc', 'custom_node_sources': {'node.py': hashlib.sha256(b'node').hexdigest()},
              'approved_static_masters': [{'id': 'coin'}]}
    record.update(changes)
    (tmp_path / 'evidence.json').write_text(json.dumps(record), encoding='utf-8')
    return {'hash': 'abc', 'output_class': 'PIXEL_STATIC',
            'validation': {'status': 'REAL_GENERATION_VERIFIED', 'evidence_record': 'evidence.json'}}


def test_matching_evidence_allows_validated(tmp_path):
    assert workflow_evidence_problem('wf', _setup(tmp_path), tmp_path.resolve()) is None


@pytest.mark.parametrize('changes, message', [
    ({'workflow_sha256': 'old'}, 'graph changed'),
    ({'workflow_id': 'other'}, 'does not verify'),
    ({'custom_node_sources': {'node.py': '0' * 64}}, 'custom node source changed'),
    ({'approved_static_masters': []}, 'approved static master'),
])
def test_stale_or_incomplete_evidence_is_rejected(tmp_path, changes, message):
    assert message in workflow_evidence_problem('wf', _setup(tmp_path, **changes), tmp_path.resolve())


def test_missing_or_outside_evidence_is_rejected(tmp_path):
    item = _setup(tmp_path)
    item['validation']['evidence_record'] = '../evidence.json'
    assert 'evidence_record' in workflow_evidence_problem('wf', item, (tmp_path / 'sub').resolve())
    item['validation'] = {'status': 'EXPERIMENTAL_LOADER_AB'}
    assert 'REAL_GENERATION_VERIFIED' in workflow_evidence_problem('wf', item, tmp_path.resolve())


def test_root_without_evidence_demotes_only_that_entry(tmp_path):
    import shutil
    shutil.copytree(ROOT / 'config', tmp_path / 'config')
    registry = load_registry(tmp_path)
    entry = registry['krea2_pixel64']
    assert entry['status'] == 'EXPERIMENTAL' and entry['evidence_check']['status'] == 'DEMOTED_TO_EXPERIMENTAL'
    assert registry['krea2_base']['status'] == 'ACTIVE'


def test_repository_evidence_matches_krea2_pixel64():
    entry = load_registry(ROOT)['krea2_pixel64']
    assert entry['evidence_check'] == {'status': 'PASS'}
    record = json.loads((ROOT / entry['validation']['evidence_record']).read_text(encoding='utf-8'))
    assert record['workflow_sha256'] == entry['hash'] and record['human_review']['adopted'] >= 1
    assert all(m['status'] == 'APPROVED_STATIC_MASTER' for m in record['approved_static_masters'])


def test_validated_pixel64_routes_by_id_without_experimental_opt_in():
    value = make(asset_id='coin', output_class='PIXEL_STATIC', prompt='gold coin')
    value['workflow_preferences'] = {'id': 'krea2_pixel64'}
    assert route(value, load_registry(ROOT))['selected_workflow'] == 'krea2_pixel64'
    value['workflow_preferences'] = {'id': 'krea2_pixel64_stock'}
    with pytest.raises(ValueError):
        route(value, load_registry(ROOT))
    value['workflow_preferences'] = {}
    decision = route(copy.deepcopy(value), load_registry(ROOT))
    assert decision['selected_workflow'] != 'krea2_pixel64'
