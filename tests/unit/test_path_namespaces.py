"""Windows representation aliases must neither race nor loosen root boundaries."""
import os
from pathlib import Path, PurePosixPath, PureWindowsPath

import pytest

from assetpipe.paths import RootResolver, _namespace_key


@pytest.mark.parametrize('extended,ordinary', [
    (r'\\?\C:\allowed\child', r'C:\allowed\child'),
    (r'\\?\c:\allowed\missing\child', r'c:\allowed\missing\child'),
    (r'\\?\UNC\server\share\allowed\child', r'\\server\share\allowed\child'),
])
def test_known_resolved_aliases_have_same_policy_key(extended, ordinary):
    assert _namespace_key(PureWindowsPath(extended)) == PureWindowsPath(ordinary)


@pytest.mark.parametrize('text', [
    r'\\?\GLOBALROOT\Device\HarddiskVolume1\allowed',
    r'\\?\Volume{00000000-0000-0000-0000-000000000000}\allowed',
    r'\\.\C:\allowed', r'\\?\C:\allowed\child.', r'\\?\C:\allowed\child ',
    r'\\?\C:\allowed\NUL.txt', r'\\?\C:\allowed\file:stream',
    r'\\?\C:\allowed\COM¹.txt', r'\\?\C:\allowed\CONIN$',
    r'\\?\C:\allowed\..\outside', r'\\?\UNC\server\share.\child',
])
def test_non_equivalent_namespaces_are_not_stripped(text):
    path = PureWindowsPath(text)
    assert _namespace_key(path) == path


def test_posix_names_are_unchanged():
    path = PurePosixPath('/allowed/\\\\?\\C:\\child')
    assert _namespace_key(path) == path


@pytest.mark.skipif(os.name != 'nt', reason='Windows filesystem namespace')
@pytest.mark.parametrize('prefixed_root', [False, True])
def test_resolver_preserves_configured_namespace_and_rejects_siblings(tmp_path, prefixed_root):
    root, outside = tmp_path / 'allowed', tmp_path / 'allowed_sibling'
    root.mkdir(); outside.mkdir()
    file = root / 'inside.txt'
    file.write_text('inside')
    configured = Path('\\\\?\\' + str(root)) if prefixed_root else root
    resolver = RootResolver([configured], base=configured)
    for value in [file, Path('\\\\?\\' + str(file))]:
        result = resolver(value)
        assert result == configured / file.name
        assert result.read_text() == 'inside'
    for value in [outside, Path('\\\\?\\' + str(outside))]:
        with pytest.raises(ValueError, match='outside configured roots'):
            resolver(value)


@pytest.mark.skipif(os.name != 'nt', reason='Windows filesystem namespace')
def test_previously_allowed_spelling_is_preserved_with_overlapping_roots(tmp_path):
    inner = tmp_path / 'inner'
    inner.mkdir()
    file = inner / 'inside.txt'
    file.write_text('inside')
    extended_root = Path('\\\\?\\' + str(inner))
    resolver = RootResolver([tmp_path, extended_root], base=extended_root)
    extended_file = extended_root / file.name
    assert resolver(extended_file) == extended_file
    assert resolver(file) == file
