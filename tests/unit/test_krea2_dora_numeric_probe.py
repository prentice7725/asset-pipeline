"""Pinned source execution must fail closed; numerical cases run with Comfy Python."""
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    'krea2_dora_numeric_probe', Path(__file__).parents[2] / 'scripts/krea2_dora_numeric_probe.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def test_source_hash_failure_prevents_any_source_execution(tmp_path):
    (tmp_path / 'version.py').write_text("raise RuntimeError('must not execute')")
    with pytest.raises(ValueError, match='SOURCE_HASH_MISMATCH: version.py'):
        probe.pinned_sources(tmp_path)


def test_missing_pinned_source_is_not_downloaded_or_substituted(tmp_path):
    with pytest.raises(FileNotFoundError):
        probe.pinned_sources(tmp_path)


def test_only_selected_function_body_is_compiled():
    source = "raise RuntimeError('unselected')\nimport absent_dependency\ndef selected():\n    return 7\n"
    namespace = {}
    methods = probe.source_functions(source, 'fixture', None, ['selected'], namespace)
    assert methods['selected']() == 7
    assert 'absent_dependency' not in namespace


def test_missing_source_method_is_rejected():
    with pytest.raises(ValueError, match='UPSTREAM_METHOD_CONTRACT_CHANGED'):
        probe.source_functions('def renamed(): pass', 'fixture', None, ['selected'], {})
