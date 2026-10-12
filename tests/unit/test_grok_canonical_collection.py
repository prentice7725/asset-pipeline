"""Synthetic Grok 1.0.50 canonical-cwd/relative-text fixtures; zero generation."""
import json
import os
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import quote

import pytest
from PIL import Image
from assetpipe.providers.base import ProviderFailed
from assetpipe.providers.cli_runner import JobDir, canonical_path, image_paths_in, snapshot_images
from assetpipe.providers.grok_cli import GrokCliProvider


@pytest.mark.parametrize('text', ['images/1.jpg', 'some sentence.images/1.jpg', 'relative/images/1.png',
                                  'https://example.invalid/image.jpg'])
def test_relative_or_url_fragments_are_not_absolute_paths(text):
    assert image_paths_in([{'text':text}],text) == []


@pytest.mark.parametrize('path', ['C:/allowed/image.png','/allowed/image.jpg'])
def test_real_absolute_paths_remain_references(path):
    assert len(image_paths_in([{'path':path}],path)) == 1


@pytest.fixture
def setup(tmp_path, monkeypatch):
    home=tmp_path/'home';home.mkdir();monkeypatch.setenv('GROK_HOME',str(home))
    provider=object.__new__(GrokCliProvider)
    job=JobDir('grok_cli',tmp_path/'jobs')
    env=provider.child_env({'mode':'cli_login'},job)
    roots=provider.snapshot_roots(env)
    state={'roots':roots,'before':snapshot_images(roots)}
    session=env['ASSETPIPE_GROK_SESSION_ID']
    # POSIX has one cwd spelling; Windows uses independently derived 8.3/full roots.
    parent=Path(env.get('ASSETPIPE_GROK_CANONICAL_SESSION_PARENT',env['ASSETPIPE_GROK_SESSION_PARENT']))
    native=str(canonical_path(job.work,strict=True));prefix=chr(92)*2+'?'+chr(92)
    if native.startswith(prefix):native=native[4:]
    assert parent.name==quote(native,safe='')
    try:yield provider,job,env,state,session,parent
    finally:job.cleanup()


def collect(setup, text='I will generate the requested image.images/1.jpg', reported=None):
    provider,job,env,state,session,parent=setup
    parsed={'session_id':reported or session,'values':[{'sessionId':reported or session,'text':text}]}
    return provider.harvest(SimpleNamespace(stdout=json.dumps(parsed['values'])),parsed,job,env,state)


def test_grok_canonical_cwd_relative_text_collects_one_real_file(setup):
    provider,job,env,state,session,parent=setup
    image=parent/session/'images/1.jpg';image.parent.mkdir(parents=True)
    Image.new('RGB',(8,8)).save(image)
    assert [canonical_path(p) for p in collect(setup)] == [canonical_path(image)]
    assert len(state['correlated_roots']) == 1+len(state['roots'])


def test_other_session_only_remains_missing(setup):
    provider,job,env,state,session,parent=setup
    image=parent/'foreign_session/images/1.jpg';image.parent.mkdir(parents=True)
    Image.new('RGB',(8,8)).save(image)
    assert collect(setup) == []
    with pytest.raises(ProviderFailed,match='different invocation session'):
        collect(setup,reported='foreign_session')


def test_no_reported_session_cannot_collect_session_store(setup):
    provider,job,env,state,session,parent=setup
    image=parent/session/'images/1.jpg';image.parent.mkdir(parents=True)
    Image.new('RGB',(8,8)).save(image)
    found=provider.harvest(SimpleNamespace(stdout='images/1.jpg'),{'values':[{'text':'images/1.jpg'}]},job,env,state)
    assert found == []


@pytest.mark.parametrize('target', ['canonical','legacy'])
def test_same_root_sibling_session_alias_is_rejected(setup,target):
    import subprocess
    provider,job,env,state,session,parent=setup
    if target=='legacy':parent=state['roots'][0]
    sibling=parent/'foreign';sibling.mkdir()
    Image.new('RGB',(8,8)).save(sibling/'image.png')
    alias=parent/session
    if os.name=='nt':subprocess.run(['cmd','/c','mklink','/J',str(alias),str(sibling)],check=True,capture_output=True)
    else:alias.symlink_to(sibling,target_is_directory=True)
    with pytest.raises(ProviderFailed,match='alias'):collect(setup)


def test_explicit_external_path_is_still_rejected(setup,tmp_path):
    image=tmp_path/'outside.jpg';Image.new('RGB',(8,8)).save(image)
    with pytest.raises(ProviderFailed,match='containment'):collect(setup,text=str(image))


def test_parsed_and_nested_session_conflict_fails_closed(setup):
    provider,job,env,state,session,parent=setup
    with pytest.raises(ProviderFailed,match='Conflicting session'):
        provider.harvest(SimpleNamespace(stdout=''),{'session_id':session,'values':[{'sessionId':'foreign'}]},job,env,state)
