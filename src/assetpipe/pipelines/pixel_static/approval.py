"""Explicit human approval backed by a completed static run and immutable hashes."""
import hashlib
import json
from pathlib import Path
from PIL import Image
from ...manifests import now, write
from ...paths import resolve_path, validate_references
from ..._ported.pixel_gate.analyzer import analyze_image


def digest(path, resolver=None):
    return hashlib.sha256(resolve_path(path, resolver).read_bytes()).hexdigest()


def validate_run(manifest_path, resolver=None):
    path = resolve_path(manifest_path, resolver)
    manifest = json.loads(path.read_text(encoding='utf-8'))
    validate_references(manifest, resolver)
    if manifest.get('output_class') != 'PIXEL_STATIC' or manifest.get('status') != 'EXPORT_READY_REVIEW_REQUIRED':
        raise ValueError('Static approval requires a passing, reviewed static export')
    evidence = manifest.get('static_validation')
    if not evidence:
        raise ValueError('Static approval requires pipeline validation evidence; rerun reviewed export')
    report = resolve_path(path.parent / '050_resolution/resolution_report.json', resolver)
    evidence = dict(evidence)
    for key in ('resolution_review', 'candidate', 'export', 'aseprite_master'):
        evidence[key] = str(resolve_path(evidence[key], resolver))
    if digest(report, resolver) != evidence['resolution_report_sha256']:
        raise ValueError('Static resolution report changed')
    for key in ('resolution_review', 'candidate', 'export', 'aseprite_master'):
        if digest(evidence[key], resolver) != evidence[key + '_sha256']:
            raise ValueError('Static validation evidence changed: ' + key)
    review = json.loads(resolve_path(evidence['resolution_review'], resolver).read_text(encoding='utf-8'))
    validate_references(review, resolver)
    if (review.get('status') != 'SELECTED' or review.get('candidate_status') != 'AUTO_PASS_REVIEW_REQUIRED'
            or not review.get('reviewed') or not review.get('reviewed_by') or not review.get('reason')
            or review.get('source_report_sha256') != digest(report, resolver)):
        raise ValueError('Passing resolution review required')
    report_data = json.loads(report.read_text(encoding='utf-8'))
    validate_references(report_data, resolver)
    rows = report_data['candidates']
    for candidate_row in rows:
        candidate_row['image'] = str(resolve_path(candidate_row['image'], resolver))
    row = next(r for r in rows if r['logical_height'] == review['selected_resolution'])
    if row.get('status') != 'AUTO_PASS_REVIEW_REQUIRED':
        raise ValueError('Selected resolution candidate did not pass')
    if Path(row['image']).resolve() != Path(evidence['candidate']).resolve() or row['sha256'] != digest(evidence['candidate'], resolver):
        raise ValueError('Selected resolution candidate does not match export evidence')
    gate = analyze_image(resolve_path(evidence['export'], resolver), target_width=row['width'], target_height=row['height'],
                         allowed_palette=manifest['asset_brief']['constraints']['palette'] or None)
    if gate['status'] != 'PASS':
        raise ValueError('Static Master Pixel Gate did not PASS')
    with Image.open(resolve_path(evidence['candidate'], resolver)) as candidate, Image.open(resolve_path(evidence['export'], resolver)) as exported:
        if candidate.size != exported.size or candidate.convert('RGBA').tobytes() != exported.convert('RGBA').tobytes():
            raise ValueError('Aseprite export differs from validated candidate')
    return manifest, evidence


def approve_static(run_dir, *, reviewed_by, reason, aseprite_reviewed):
    if not aseprite_reviewed or not reviewed_by.strip() or not reason.strip():
        raise ValueError('Explicit Aseprite review, reviewer and reason are required')
    path = Path(run_dir).resolve() / 'run_manifest.json'
    manifest, evidence = validate_run(path)
    destination = path.parent / 'approval_record.json'
    record = {
        'schema_version': 1, 'status': 'APPROVED_STATIC_MASTER', 'asset_id': manifest['asset_id'],
        'approved_export': evidence['export'], 'approved_export_sha256': evidence['export_sha256'],
        'source_manifest': str(path), 'source_manifest_sha256': digest(path),
        'aseprite_reviewed': True, 'reviewed_by': reviewed_by.strip(), 'reason': reason.strip(), 'approved_at': now(),
    }
    write(destination, record)
    return destination


def validate_approval(master, approval_path, resolver=None):
    master = resolve_path(master, resolver)
    approval_path = resolve_path(approval_path, resolver)
    record = json.loads(approval_path.read_text(encoding='utf-8'))
    validate_references(record, resolver)
    if record.get('status') != 'APPROVED_STATIC_MASTER' or record.get('approved_export_sha256') != digest(master, resolver):
        raise ValueError('Static master approval/hash gate failed')
    if not record.get('source_manifest') or not record.get('aseprite_reviewed') or not record.get('reviewed_by') or not record.get('reason'):
        raise ValueError('Static master approval lacks pipeline provenance and Aseprite review')
    if digest(record['source_manifest'], resolver) != record.get('source_manifest_sha256'):
        raise ValueError('Approved static manifest changed')
    manifest, evidence = validate_run(record['source_manifest'], resolver)
    approved_export = resolve_path(record.get('approved_export', ''), resolver)
    if (record.get('asset_id') != manifest['asset_id'] or master != Path(evidence['export'])
            or approved_export != master or record['approved_export_sha256'] != evidence['export_sha256']):
        raise ValueError('Static master approval references a different validated export')
    return record
