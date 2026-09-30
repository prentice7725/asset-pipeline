"""Explicit human approval backed by a completed static run and immutable hashes."""
import hashlib
import json
from pathlib import Path
from PIL import Image
from ...manifests import now, write
from ..._ported.pixel_gate.analyzer import analyze_image


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_run(manifest_path):
    path = Path(manifest_path).resolve()
    manifest = json.loads(path.read_text(encoding='utf-8'))
    if manifest.get('output_class') != 'PIXEL_STATIC' or manifest.get('status') != 'EXPORT_READY_REVIEW_REQUIRED':
        raise ValueError('Static approval requires a passing, reviewed static export')
    evidence = manifest.get('static_validation')
    if not evidence:
        raise ValueError('Static approval requires pipeline validation evidence; rerun reviewed export')
    report = path.parent / '050_resolution/resolution_report.json'
    if digest(report) != evidence['resolution_report_sha256']:
        raise ValueError('Static resolution report changed')
    for key in ('resolution_review', 'candidate', 'export', 'aseprite_master'):
        if digest(evidence[key]) != evidence[key + '_sha256']:
            raise ValueError('Static validation evidence changed: ' + key)
    review = json.loads(Path(evidence['resolution_review']).read_text(encoding='utf-8'))
    if (review.get('status') != 'SELECTED' or review.get('candidate_status') != 'AUTO_PASS_REVIEW_REQUIRED'
            or not review.get('reviewed') or not review.get('reviewed_by') or not review.get('reason')
            or review.get('source_report_sha256') != digest(report)):
        raise ValueError('Passing resolution review required')
    rows = json.loads(report.read_text(encoding='utf-8'))['candidates']
    row = next(r for r in rows if r['logical_height'] == review['selected_resolution'])
    if row.get('status') != 'AUTO_PASS_REVIEW_REQUIRED':
        raise ValueError('Selected resolution candidate did not pass')
    if Path(row['image']).resolve() != Path(evidence['candidate']).resolve() or row['sha256'] != digest(evidence['candidate']):
        raise ValueError('Selected resolution candidate does not match export evidence')
    gate = analyze_image(evidence['export'], target_width=row['width'], target_height=row['height'],
                         allowed_palette=manifest['asset_brief']['constraints']['palette'] or None)
    if gate['status'] != 'PASS':
        raise ValueError('Static Master Pixel Gate did not PASS')
    with Image.open(evidence['candidate']) as candidate, Image.open(evidence['export']) as exported:
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


def validate_approval(master, approval_path):
    record = json.loads(Path(approval_path).read_text(encoding='utf-8'))
    if record.get('status') != 'APPROVED_STATIC_MASTER' or record.get('approved_export_sha256') != digest(master):
        raise ValueError('Static master approval/hash gate failed')
    if not record.get('source_manifest') or not record.get('aseprite_reviewed') or not record.get('reviewed_by') or not record.get('reason'):
        raise ValueError('Static master approval lacks pipeline provenance and Aseprite review')
    if digest(record['source_manifest']) != record.get('source_manifest_sha256'):
        raise ValueError('Approved static manifest changed')
    manifest, evidence = validate_run(record['source_manifest'])
    if record.get('asset_id') != manifest['asset_id'] or Path(master).resolve() != Path(evidence['export']).resolve():
        raise ValueError('Static master approval references a different validated export')
    return record
