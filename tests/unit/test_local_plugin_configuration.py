"""Offline package/wiring tests; no generator, real approval or operational server."""
import json
from pathlib import Path
import sys

import pytest
from scripts.configure_local_plugin import files, missing_links, prepare

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def fixture(tmp_path):
    source = tmp_path/'installed'
    (source/'.codex-plugin').mkdir(parents=True)
    (source/'.codex-plugin/plugin.json').write_text(json.dumps({'name':'asset-pipeline'}))
    (source/'.mcp.json').write_text(json.dumps({'mcpServers':{'asset_pipeline':{'command':'assetpipe-mcp','args':[]}}}))
    (source/'references').mkdir()
    (source/'references/HISTORY.md').write_text('Historical data; no approval')
    (source/'references/local_note.md').write_text('[history](research/HISTORY.md)')
    launcher = tmp_path/'launch.py';launcher.write_text('# Synthetic path fixture; never executed')
    return source,tmp_path/'candidate',launcher


def test_local_wiring_and_historical_links_preserve_source(fixture):
    source,candidate,launcher = fixture
    before = files(source)
    report = prepare(source,candidate,sys.executable,launcher,ROOT/'plugin')
    assert files(source) == before
    wiring = report['wiring']['mcpServers']['asset_pipeline']
    assert wiring == {'command':str(Path(sys.executable).resolve()),'args':['-B',str(launcher.resolve())]}
    assert not missing_links(candidate)
    assert (candidate/'references/HISTORY.md').read_text() == 'Historical data; no approval'
    assert report['restart'] == report['generation'] == report['creator_validation'] == 'NOT_RUN'


def test_unknown_link_is_not_hidden_or_fabricated(fixture):
    source,candidate,launcher = fixture
    (source/'references/local_note.md').write_text('[missing](unknown/nonexistent.md)')
    with pytest.raises(ValueError,match='BROKEN_REFERENCES'):
        prepare(source,candidate,sys.executable,launcher,ROOT/'plugin')
    assert not (candidate/'references/nonexistent.md').exists()


def test_existing_candidate_is_not_overwritten(fixture):
    source,candidate,launcher = fixture
    candidate.mkdir();(candidate/'keep').write_text('preserve')
    with pytest.raises(FileExistsError):prepare(source,candidate,sys.executable,launcher,ROOT/'plugin')
    assert (candidate/'keep').read_text() == 'preserve'


def test_external_document_link_is_rejected_even_if_present(fixture,tmp_path):
    source,candidate,launcher = fixture
    external = tmp_path/'external.md';external.write_text('not bundled')
    (source/'references/local_note.md').write_text('[external]('+str(external)+')')
    with pytest.raises(ValueError,match='BROKEN_REFERENCES'):
        prepare(source,candidate,sys.executable,launcher,ROOT/'plugin')


def test_other_plugin_identity_is_rejected(fixture):
    source,candidate,launcher = fixture
    (source/'.codex-plugin/plugin.json').write_text('{"name":"other"}')
    with pytest.raises(ValueError,match='IDENTITY_MISMATCH'):
        prepare(source,candidate,sys.executable,launcher,ROOT/'plugin')


def test_canonical_package_has_no_broken_document_links():
    assert not missing_links((ROOT/'plugin').resolve())
