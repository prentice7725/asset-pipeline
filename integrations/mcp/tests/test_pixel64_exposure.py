"""Pixel64 through the six MCP tools: discoverable, routable by id, and inspect reports the human steps left."""
import json
from pathlib import Path
import subprocess

import numpy as np
import pytest
import yaml
from PIL import Image

from assetpipe import api
from assetpipe.pixel.transparent import make_transparent
from integrations.mcp.tools.adapter import Adapter

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def adapter(tmp_path):
    config = tmp_path / 'adapter.yaml'
    config.write_text(yaml.safe_dump({'core_root': str(ROOT), 'source_roots': [str(ROOT / 'examples')], 'output_root': str(tmp_path / 'outputs')}))
    return Adapter(config)


def test_capabilities_list_validated_pixel64(monkeypatch):
    class Offline:
        def __init__(self, *a, **k): pass
        def check_connection(self): raise OSError('offline')
    monkeypatch.setattr(api, 'ComfyClient', Offline)
    result = api.capabilities(ROOT)
    entry = result['validated_workflows']['krea2_pixel64']
    assert entry['output_class'] == 'PIXEL_STATIC' and entry['selection'] == 'explicit_only'
    assert entry['evidence_check'] == {'status': 'PASS'} and 'sprite64' in entry['presets']
    assert 'krea2_pixel64' not in result['active_workflows']
    assert any('krea2_pixel64' in line for line in result['limitations'])


def test_build_brief_and_generate_by_workflow_id_without_experimental_flag(adapter, monkeypatch):
    built = adapter.build_brief(request_text='gold coin with a star emblem', output_class='PIXEL_STATIC',
                                asset_id='coin64', workflow_id='krea2_pixel64')
    assert built['status'] == 'BRIEF_READY'
    assert adapter.route(built['brief'])['selected_workflow'] == 'krea2_pixel64'
    launched = []

    class Child:
        pid = 1
        def poll(self): return None
    monkeypatch.setattr(subprocess, 'Popen', lambda command, **k: launched.append(command) or Child())
    result = adapter.generate(brief=built['brief'], seed=20261120)
    assert result['status'] == 'RUNNING' and result['workflow_id'] == 'krea2_pixel64'
    assert launched[0][launched[0].index('create') + 1:][:1] == ['--brief'] and launched[0][-2:] == ['--seed', '20261120']


def test_transparent_summary_reads_hole_count_from_the_run_report(tmp_path):
    image = np.full((64, 64, 3), 252, dtype=np.uint8)
    image[10:54, 10:54] = (20, 20, 20)
    image[14:18, 14:18] = 252
    sheet = tmp_path / 'sheet.png'
    Image.fromarray(image, 'RGB').save(sheet)
    report = make_transparent(sheet, tmp_path / '070_transparent', created_by='test')
    manifest = {'transparent_delivery': {'status': report['status'], 'output': report['output'], 'review': 'HUMAN_REQUIRED'}}
    summary = api.transparent_summary(manifest)
    assert summary['status'] == 'ENCLOSED_BACKGROUND_REVIEW_REQUIRED'
    assert summary['possible_holes'] == 1 and summary['unresolved_enclosed_regions'] == 1
    assert api.transparent_summary({}) is None


def test_static_approval_summary_reports_invalid_records(tmp_path):
    (tmp_path / 'run_manifest.json').write_text('{}', encoding='utf-8')
    assert api.static_approval_summary(tmp_path / 'run_manifest.json') is None
    (tmp_path / 'approval_record.json').write_text(json.dumps({'status': 'APPROVED_STATIC_MASTER', 'approved_export': str(tmp_path / 'missing.png')}), encoding='utf-8')
    summary = api.static_approval_summary(tmp_path / 'run_manifest.json')
    assert summary['valid'] is False and summary['error']
