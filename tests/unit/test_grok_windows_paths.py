"""Synthetic Windows path-budget and invocation-ownership regressions."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import quote

import pytest
from PIL import Image
from assetpipe.providers.base import ProviderFailed
from assetpipe.providers.cli_runner import JobDir, canonical_path
from assetpipe.providers.grok_cli import GrokCliProvider
from test_cli_providers import box, brief

@pytest.mark.skipif(os.name != 'nt', reason='Windows 8.3 and path-budget contract')
@pytest.mark.parametrize('mode', ['cli_login','env_api_key'])
def test_long_windows_job_path_still_has_one_correlated_output(box, monkeypatch, mode):
    box.jobs = box.tmp / ('long_configured_job_root_' + 'x'*65)
    box.providers['grok_cli']['job_root'] = str(box.jobs)
    box.save()
    if mode=='env_api_key':
        monkeypatch.setenv('XAI_API_KEY','xai-TESTKEY1234567890')
        box.edit_registry('grok_imagine',lambda e:e['backend'].update(auth={'mode':mode,'env':['XAI_API_KEY']}))
    manifest,error,out=box.attempt(brief('grok_imagine'))
    assert error is None and manifest['status']=='CANDIDATE_READY_REVIEW_REQUIRED'
    call=box.calls(box.grok_dir)[0]
    argv=call['argv']; cwd=argv[argv.index('--cwd')+1]
    session=argv[argv.index('--session-id')+1]
    parent=Path(call['env']['ASSETPIPE_GROK_SESSION_PARENT'])
    assert parent.name==quote(cwd,safe='')
    assert len(str(parent/session/'images'/'1.png'))<260
    assert len(manifest['generation']['provider']['outputs'])==1
    assert manifest['generation']['provider']['retry']['attempts']==1
    assert manifest['generation']['provider']['retry']['fallback']=='NONE'


@pytest.mark.parametrize('mode', ['cli_login','env_api_key'])
def test_concurrent_grok_jobs_have_distinct_directories_and_session_ids(tmp_path, monkeypatch, mode):
    home=tmp_path/'home'; home.mkdir(); monkeypatch.setenv('GROK_HOME',str(home))
    provider=object.__new__(GrokCliProvider)
    jobs=[JobDir('grok_cli',tmp_path/'jobs') for _ in range(4)]
    def collect(job):
        env=provider.child_env({'mode':mode},job)
        session=env['ASSETPIPE_GROK_SESSION_ID']; parent=Path(env['ASSETPIPE_GROK_SESSION_PARENT'])
        image=parent/session/'images/image.png'; image.parent.mkdir(parents=True)
        Image.new('RGB',(8,8)).save(image)
        state={'roots':provider.snapshot_roots(env),'before':{}}
        parsed={'session_id':session,'values':[{'session_id':session,'path':str(image)}]}
        found=provider.harvest(SimpleNamespace(stdout=json.dumps(parsed['values'])),parsed,job,env,state)
        assert len(found)==1 and canonical_path(found[0])==canonical_path(image)
        with pytest.raises(ProviderFailed) as error:
            provider.harvest(SimpleNamespace(stdout=''),{'session_id':'foreign','values':[{'session_id':'foreign'}]},job,env,state)
        assert error.value.code=='OUTPUT_UNCORRELATED'
        return str(parent),session,str(canonical_path(found[0]))
    try:
        with ThreadPoolExecutor(4) as pool: results=list(pool.map(collect,jobs))
        assert all(len({row[i] for row in results})==4 for i in range(3))
    finally:
        for job in jobs: job.cleanup()


@pytest.mark.skipif(os.name != 'nt', reason='Windows 8.3 unavailable path-budget contract')
def test_unshortenable_windows_path_blocks_before_dispatch(tmp_path, monkeypatch):
    from assetpipe.providers import grok_cli
    home=tmp_path/'home'; home.mkdir(); monkeypatch.setenv('GROK_HOME',str(home))
    monkeypatch.setattr(grok_cli,'cli_directory',lambda p:str(Path(p).resolve(strict=True)))
    provider=object.__new__(GrokCliProvider)
    job=JobDir('grok_cli',tmp_path/('deep_'+'x'*75))
    try:
        with pytest.raises(ProviderFailed) as error: provider.child_env({'mode':'env_api_key'},job)
        assert error.value.code=='SESSION_PATH_TOO_LONG'
    finally: job.cleanup()
