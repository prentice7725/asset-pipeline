"""Synthetic security contracts: no external generation or human approval."""
import json
import os
from pathlib import Path
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
import subprocess

import pytest
from PIL import Image

from assetpipe.paths import RootResolver, ROOTS_ENV, resolve_path
from assetpipe.pipelines.pixel_static.approval import digest, validate_run, validate_approval
from assetpipe.providers.cli_runner import snapshot_images, new_images
from assetpipe.providers.codex_cli import CodexCliProvider
from assetpipe.providers.grok_cli import GrokCliProvider
from assetpipe.providers.base import ProviderFailed


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')
    return path


@pytest.fixture
def provenance(tmp_path):
    root = tmp_path / 'allowed'
    root.mkdir()
    image = root / 'export.png'
    fixture = Path(__file__).parents[1] / 'assets/true_pixel_art.png'
    image.write_bytes(fixture.read_bytes())
    with Image.open(image) as opened:
        width, height = opened.size
    master = root / 'master.aseprite'
    master.write_bytes(b'SYNTHETIC provenance test only')
    report = put(root / '050_resolution/resolution_report.json', {'candidates': [{
        'logical_height': height, 'width': width, 'height': height,
        'status': 'AUTO_PASS_REVIEW_REQUIRED', 'image': str(image), 'sha256': digest(image)}]})
    review = put(root / 'review.json', {'status': 'SELECTED', 'candidate_status': 'AUTO_PASS_REVIEW_REQUIRED',
        'reviewed': True, 'reviewed_by': 'SYNTHETIC', 'reason': 'test data, no human approval',
        'source_report_sha256': digest(report), 'selected_resolution': height})
    evidence = {'resolution_report_sha256': digest(report)}
    for key, path in [('resolution_review', review), ('candidate', image), ('export', image), ('aseprite_master', master)]:
        evidence[key], evidence[key + '_sha256'] = str(path), digest(path)
    manifest = put(root / 'run_manifest.json', {'asset_id': 'synthetic', 'output_class': 'PIXEL_STATIC',
        'status': 'EXPORT_READY_REVIEW_REQUIRED', 'static_validation': evidence,
        'asset_brief': {'constraints': {'palette': []}}})
    record = put(root / 'synthetic_record.json', {'status': 'APPROVED_STATIC_MASTER', 'asset_id': 'synthetic',
        'approved_export': str(image), 'approved_export_sha256': digest(image), 'source_manifest': str(manifest),
        'source_manifest_sha256': digest(manifest), 'aseprite_reviewed': True, 'reviewed_by': 'SYNTHETIC',
        'reason': 'serialized test input only; no approval operation called'})
    return root, manifest, record, image, RootResolver([root])


def test_valid_provenance_and_pixel_gate_unchanged(provenance):
    root, manifest, record, image, resolver = provenance
    assert validate_run(manifest, resolver) == validate_run(manifest)
    assert validate_approval(image, record, resolver)['reviewed_by'] == 'SYNTHETIC'
    assert not list(root.glob('approval_record.json'))


@pytest.mark.parametrize('location', ['source_manifest', 'candidate', 'export', 'aseprite_master',
                                     'resolution_review', 'report_row', 'nested_reference'])
def test_transitive_escape_rejected_before_hash(provenance, tmp_path, location):
    root, manifest, record, image, resolver = provenance
    outside = tmp_path / 'outside.png'
    outside.write_bytes(image.read_bytes())
    if location == 'source_manifest':
        data = json.loads(record.read_text())
        data['source_manifest'] = str(outside)
        put(record, data)
    else:
        data = json.loads(manifest.read_text())
        if location == 'report_row':
            report = root / '050_resolution/resolution_report.json'
            report_data = json.loads(report.read_text())
            report_data['candidates'].append({'image': str(outside)})
            put(report, report_data)
            data['static_validation']['resolution_report_sha256'] = digest(report)
            review = root / 'review.json'
            review_data = json.loads(review.read_text())
            review_data['source_report_sha256'] = digest(report)
            put(review, review_data)
            data['static_validation']['resolution_review_sha256'] = digest(review)
        elif location == 'nested_reference':
            data['asset_brief']['source'] = {'references': [str(outside)]}
        else:
            data['static_validation'][location] = str(outside)
        put(manifest, data)
        record_data = json.loads(record.read_text())
        record_data['source_manifest_sha256'] = digest(manifest)
        put(record, record_data)
    with pytest.raises(ValueError, match='outside'):
        validate_approval(image, record, resolver)


def test_approved_export_must_identify_validated_export(provenance):
    root, manifest, record, image, resolver = provenance
    duplicate = root / 'duplicate.png'
    duplicate.write_bytes(image.read_bytes())
    data = json.loads(record.read_text())
    data['approved_export'] = str(duplicate)
    put(record, data)
    with pytest.raises(ValueError, match='different validated export'):
        validate_approval(image, record, resolver)


def test_policy_survives_child_environment(provenance, monkeypatch):
    root, manifest, record, image, resolver = provenance
    monkeypatch.setenv(ROOTS_ENV, resolver.environment())
    assert resolve_path(image) == image
    with pytest.raises(ValueError, match='outside'):
        resolve_path(root.parent / 'outside', strict=False)


def link_directory(link, target, kind):
    if kind == 'junction':
        if os.name != 'nt':
            pytest.skip('Windows junction test')
        result = subprocess.run(['powershell', '-NoProfile', '-Command',
            'New-Item -ItemType Junction -Path $env:ASSETPIPE_TEST_LINK -Target $env:ASSETPIPE_TEST_TARGET'],
            env={**os.environ, 'ASSETPIPE_TEST_LINK': str(link), 'ASSETPIPE_TEST_TARGET': str(target)}, capture_output=True)
        if result.returncode:
            pytest.fail(result.stderr.decode(errors='replace'))
    else:
        try:
            link.symlink_to(target, target_is_directory=True)
        except OSError as exc:
            pytest.skip(f'Symlink privilege unavailable: {exc}')


@pytest.mark.parametrize('kind', ['symlink', 'junction'])
def test_resolver_and_scanned_images_reject_link_escape(tmp_path, kind):
    root, outside = tmp_path / 'root', tmp_path / 'outside'
    root.mkdir(); outside.mkdir()
    Image.new('RGB', (8, 8)).save(outside / 'secret.png')
    link_directory(root / 'escape', outside, kind)
    resolver = RootResolver([root])
    with pytest.raises(ValueError, match='outside'):
        resolver(root / 'escape/secret.png')
    assert new_images([root], {}) == []
    assert snapshot_images([root]) == {}


@pytest.mark.parametrize('engine', ['codex', 'grok'])
@pytest.mark.parametrize('mode', ['same', 'other_only', 'missing_id', 'explicit_other', 'two', 'missing', 'reused'])
def test_harvest_correlation(tmp_path, engine, mode):
    home, work = tmp_path / 'home', tmp_path / 'private_job'
    work.mkdir(); home.mkdir()
    parent = home / ('generated_images' if engine == 'codex' else 'sessions')
    parent.mkdir()
    session = 'session_123'
    path = parent / session / 'image.png'
    before = {}
    if mode == 'reused':
        path.parent.mkdir()
        Image.new('RGB', (8, 8)).save(path)
        before = snapshot_images([home])
    if mode not in ('missing',):
        if mode in ('other_only', 'explicit_other'):
            path = parent / 'other_session' / 'image.png'
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new('RGB', (8, 8)).save(path)
        if mode == 'reused':
            os.utime(path, ns=(path.stat().st_atime_ns, before[str(path)] + 1_000_000_000))
    values = [] if mode == 'missing_id' else [{'session_id': session}]
    if mode == 'explicit_other':
        values[0]['path'] = str(path)
    if mode == 'two':
        Image.new('RGB', (8, 8)).save(path.parent / 'second.png')
    provider = object.__new__(CodexCliProvider if engine == 'codex' else GrokCliProvider)
    result = SimpleNamespace(stdout=json.dumps(values))
    parsed = {'session_id': None if mode == 'missing_id' else session, 'values': values}
    state = {'roots': [home / 'generated_images' if engine == 'codex' else home], 'before': before}
    if mode in ('explicit_other', 'reused'):
        with pytest.raises(ProviderFailed) as exc:
            provider.harvest(result, parsed, SimpleNamespace(work=work), {}, state)
        assert exc.value.code == 'OUTPUT_UNCORRELATED'
    else:
        found = provider.harvest(result, parsed, SimpleNamespace(work=work), {}, state)
        assert len(found) == (1 if mode == 'same' else 2 if mode == 'two' else 0)


def test_concurrent_sessions_do_not_cross_collect(tmp_path):
    root = tmp_path / 'images'; root.mkdir()
    provider = object.__new__(CodexCliProvider)
    for session in ('job_a123', 'job_b123'):
        (root / session).mkdir()
        Image.new('RGB', (8, 8)).save(root / session / 'image.png')
    def harvest(session):
        work = tmp_path / session; work.mkdir()
        return provider.harvest(SimpleNamespace(stdout=''), {'session_id': session, 'values': [{'thread_id': session}]},
            SimpleNamespace(work=work), {}, {'roots': [root], 'before': {}})
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(harvest, ['job_a123', 'job_b123']))
    assert results == [[root / 'job_a123/image.png'], [root / 'job_b123/image.png']]


@pytest.mark.parametrize('engine', ['codex', 'grok'])
def test_explicit_and_scanned_session_symlinks_fail_closed(tmp_path, engine):
    home, work, outside = tmp_path / 'home', tmp_path / 'job', tmp_path / 'outside'
    home.mkdir(); work.mkdir(); outside.mkdir()
    parent = home / ('generated_images' if engine == 'codex' else 'sessions')
    parent.mkdir()
    Image.new('RGB', (8, 8)).save(outside / 'image.png')
    link_directory(parent / 'session_123', outside, 'symlink')
    provider = object.__new__(CodexCliProvider if engine == 'codex' else GrokCliProvider)
    values = [{'session_id': 'session_123', 'path': str(parent / 'session_123/image.png')}]
    with pytest.raises(ProviderFailed) as exc:
        provider.harvest(SimpleNamespace(stdout=''), {'session_id': 'session_123', 'values': values},
            SimpleNamespace(work=work), {}, {'roots': [home / 'generated_images' if engine == 'codex' else home], 'before': {}})
    assert exc.value.code == 'OUTPUT_UNCORRELATED'


def test_adapter_propagates_policy_to_route_and_child(tmp_path, monkeypatch):
    import yaml
    from assetpipe import api
    from assetpipe.brief import make
    from integrations.mcp.tools.adapter import Adapter
    root = Path(__file__).resolve().parents[2]
    config = tmp_path / 'adapter.yaml'
    config.write_text(yaml.safe_dump({'core_root': str(root), 'source_roots': [str(tmp_path)],
        'output_root': str(tmp_path / 'outputs')}))
    adapter = Adapter(config)
    captured = {}
    def route(brief, core, resolver=None):
        assert resolver is adapter.resolver
        return {'status': 'ROUTED', 'selected_workflow': 'synthetic'}
    def popen(*args, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(pid=123)
    monkeypatch.setattr(api, 'route_brief', route)
    monkeypatch.setattr(subprocess, 'Popen', popen)
    adapter.generate(brief=make(asset_id='synthetic', output_class='NONPIXEL_IMAGE', prompt='offline'))
    policy = json.loads(captured['env'][ROOTS_ENV])
    assert policy['roots'] == [str(p) for p in adapter.resolver.roots]


def test_hash_and_pixel_failures_still_block(provenance, monkeypatch):
    from assetpipe.pipelines.pixel_static import approval
    root, manifest, record, image, resolver = provenance
    monkeypatch.setattr(approval, 'analyze_image', lambda *args, **kwargs: {'status': 'FAIL'})
    with pytest.raises(ValueError, match='Pixel Gate'):
        validate_run(manifest, resolver)
    image.write_bytes(b'changed')
    with pytest.raises(ValueError, match='approval/hash'):
        validate_approval(image, record, resolver)
