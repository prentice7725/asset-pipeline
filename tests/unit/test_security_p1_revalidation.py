"""Offline Windows case/reparse regressions; no generation or approval."""
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from assetpipe.paths import RootResolver
from assetpipe.providers.base import ProviderFailed
from assetpipe.providers.codex_cli import CodexCliProvider
from assetpipe.providers.grok_cli import GrokCliProvider
from assetpipe.providers.cli_runner import new_images, snapshot_images
from test_security_hardening import link_directory, provider_roots

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='Windows case and reparse point contracts')


def setup(tmp_path, engine):
    home, work = tmp_path / 'home', tmp_path / 'job'
    home.mkdir(); work.mkdir()
    parent = home / ('generated_images' if engine == 'codex' else 'sessions')
    parent.mkdir()
    provider = object.__new__(CodexCliProvider if engine == 'codex' else GrokCliProvider)
    return provider, home, work, parent


def collect(provider, home, work, parent, session, path=None, before=None):
    value = {'session_id': session}
    if path is not None:
        value['path'] = str(path)
    return provider.harvest(SimpleNamespace(stdout=json.dumps(value)),
        {'session_id': session, 'values': [value]}, SimpleNamespace(work=work), {},
        {'roots': provider_roots(provider, home, parent), 'before': before or {}})


@pytest.mark.parametrize('engine', ['codex', 'grok'])
@pytest.mark.parametrize('kind', ['symlink', 'junction'])
def test_case_variant_sibling_alias_is_rejected(tmp_path, engine, kind):
    provider, home, work, parent = setup(tmp_path, engine)
    other = parent / 'OtherSession'; other.mkdir()
    Image.new('RGB', (8, 8)).save(other / 'foreign.png')
    link_directory(parent / 'ReportedSession', other, kind)
    with pytest.raises(ProviderFailed) as error:
        collect(provider, home, work, Path(str(parent).upper()), 'REPORTEDSESSION',
                Path(str(parent / 'ReportedSession/foreign.png').upper()))
    assert error.value.code == 'OUTPUT_UNCORRELATED'


@pytest.mark.parametrize('engine', ['codex', 'grok'])
@pytest.mark.parametrize('kind', ['symlink', 'junction'])
@pytest.mark.parametrize('target_kind', ['sibling', 'outside'])
def test_nested_reparse_cannot_cross_session_boundary(tmp_path, engine, kind, target_kind):
    provider, home, work, parent = setup(tmp_path, engine)
    target = (parent if target_kind == 'sibling' else tmp_path) / 'OtherSession'
    target.mkdir(); Image.new('RGB', (8, 8)).save(target / 'foreign.png')
    session = parent / 'ReportedSession'; session.mkdir()
    # A two-hop reparse chain, including an intermediate Windows junction.
    link_directory(tmp_path / 'middle', target, 'junction')
    link_directory(session / 'nested', tmp_path / 'middle', kind)
    assert collect(provider, home, work, parent, 'ReportedSession') == []
    with pytest.raises(ProviderFailed) as error:
        collect(provider, home, work, parent, 'ReportedSession', session / 'nested/foreign.png')
    assert error.value.code == 'OUTPUT_UNCORRELATED'


@pytest.mark.parametrize('engine', ['codex', 'grok'])
@pytest.mark.parametrize('explicit', [False, True])
def test_normal_session_with_case_variants_still_collects(tmp_path, engine, explicit):
    provider, home, work, parent = setup(tmp_path, engine)
    session = parent / 'RealSession'; session.mkdir()
    image = session / 'image.png'; Image.new('RGB', (8, 8)).save(image)
    path = Path(str(image).upper()) if explicit else None
    found = collect(provider, home, work, Path(str(parent).upper()), 'REALSESSION', path)
    assert found == [image.resolve()]
    resolver = RootResolver([Path(str(parent).upper())])
    assert resolver(Path(str(image).upper())) == image.resolve()


@pytest.mark.parametrize('engine', ['codex', 'grok'])
@pytest.mark.parametrize('kind', ['symlink', 'junction'])
def test_internal_same_session_reparse_remains_valid(tmp_path, engine, kind):
    provider, home, work, parent = setup(tmp_path, engine)
    session = parent / 'RealSession'; session.mkdir()
    target = session / 'images'; target.mkdir()
    image = target / 'image.png'; Image.new('RGB', (8, 8)).save(image)
    link_directory(session / 'link', target, kind)
    assert collect(provider, home, work, parent, 'RealSession', session / 'link/image.png') == [image.resolve()]


@pytest.mark.parametrize('kind', ['symlink', 'junction'])
def test_nested_root_escape_case_variant_fails_closed(tmp_path, kind):
    root, outside = tmp_path / 'allowed', tmp_path / 'outside'
    root.mkdir(); outside.mkdir()
    image = outside / 'secret.png'; Image.new('RGB', (8, 8)).save(image)
    link_directory(tmp_path / 'middle', outside, 'junction')
    link_directory(root / 'nested', tmp_path / 'middle', kind)
    with pytest.raises(ValueError, match='outside'):
        RootResolver([Path(str(root).upper())])(Path(str(root / 'nested/secret.png').upper()))
    assert new_images([root], {}) == []
    assert snapshot_images([root]) == {}
