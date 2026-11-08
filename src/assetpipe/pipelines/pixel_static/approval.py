"""Explicit human approval backed by a completed static run and immutable hashes."""
import hashlib
import json
from pathlib import Path
from PIL import Image
from ...manifests import now, write
from ...paths import resolve_path, validate_references
from ..._ported.pixel_gate.analyzer import analyze_image
from . import manifest_gate_palette


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
                         allowed_palette=manifest_gate_palette(manifest))
    if gate['status'] != 'PASS':
        raise ValueError('Static Master Pixel Gate did not PASS')
    with Image.open(resolve_path(evidence['candidate'], resolver)) as candidate, Image.open(resolve_path(evidence['export'], resolver)) as exported:
        if candidate.size != exported.size or candidate.convert('RGBA').tobytes() != exported.convert('RGBA').tobytes():
            raise ValueError('Aseprite export differs from validated candidate')
    return manifest, evidence


def write_resolution_review(run_dir, *, resolution, reviewed_by, reason):
    """Record the human resolution selection that export-static requires (size selection only, not art approval)."""
    if not str(reviewed_by).strip() or not str(reason).strip():
        raise ValueError('Reviewer and reason are required')
    run = Path(run_dir).resolve()
    manifest = json.loads((run / 'run_manifest.json').read_text(encoding='utf-8'))
    if manifest.get('output_class') != 'PIXEL_STATIC' or manifest.get('status') != 'RESOLUTION_REVIEW_REQUIRED':
        raise ValueError('Run is not waiting for resolution review')
    report_path = run / '050_resolution/resolution_report.json'
    report = json.loads(report_path.read_text(encoding='utf-8'))
    row = next((r for r in report['candidates'] if r['logical_height'] == int(resolution)), None)
    if row is None or row.get('status') != 'AUTO_PASS_REVIEW_REQUIRED':
        raise ValueError(f'Resolution {resolution} is not a passing candidate in this run')
    review = {'status': 'SELECTED', 'candidate_status': row['status'], 'selected_resolution': int(resolution),
              'reviewed': True, 'reviewed_by': str(reviewed_by).strip(), 'reason': str(reason).strip(),
              'source_report_sha256': digest(report_path), 'recorded_at': now()}
    from ...manifests import write_new
    destination = run / 'resolution_review.json'
    write_new(destination, review)
    return destination


def validate_delivery(export, transparent, *, accept_possible_holes=False):
    """A transparent delivery copy may join a static approval only if it is the approved export with
    its background removed: opaque pixels identical, cleared pixels exactly the found background color."""
    import numpy as np
    transparent = Path(transparent).resolve()
    folder = transparent.parent
    report = json.loads((folder / 'transparent_report.json').read_text(encoding='utf-8'))
    if report.get('kind') != 'PIXEL64_TRANSPARENT_DELIVERY' or Path(report['output']).resolve() != transparent:
        raise ValueError('Transparent delivery report does not describe this file')
    if report['output_sha256'] != digest(transparent):
        raise ValueError('Transparent delivery changed since its report')
    if report['status'] not in ('PASS_REVIEW_REQUIRED', 'ENCLOSED_BACKGROUND_REVIEW_REQUIRED'):
        raise ValueError(f"Transparent delivery status {report['status']} cannot be approved")
    holes = report.get('possible_holes')
    if holes is None:
        # Reports written before hole hints existed cannot say whether a region is a hole.
        holes = len(report['unresolved_enclosed_regions'])
    if holes and not accept_possible_holes:
        raise ValueError(f'{holes} enclosed region(s) look like holes; clear them with --hole or pass --accept-possible-holes')
    roundtrip_path = folder / 'aseprite_roundtrip.json'
    roundtrip = json.loads(roundtrip_path.read_text(encoding='utf-8')) if roundtrip_path.is_file() else {}
    if roundtrip.get('status') != 'PASS':
        raise ValueError('Transparent delivery needs a PASS Aseprite round trip')
    with Image.open(export) as a, Image.open(transparent) as b:
        master, delivered = np.asarray(a.convert('RGBA')), np.asarray(b.convert('RGBA'))
    if master.shape != delivered.shape or not (master[..., 3] == 255).all():
        raise ValueError('Transparent delivery size differs from the approved opaque master')
    opaque = delivered[..., 3] == 255
    background = np.asarray(report['background_rgb_found'], dtype=np.uint8)
    if not (master[opaque][:, :3] == delivered[opaque][:, :3]).all() or not (master[~opaque][:, :3] == background).all():
        raise ValueError('Transparent delivery is not the approved master with only its background removed')
    return {'transparent': str(transparent), 'transparent_sha256': digest(transparent),
            'report': str(folder / 'transparent_report.json'), 'report_sha256': digest(folder / 'transparent_report.json'),
            'hole_seeds': report['hole_seeds'], 'unresolved_enclosed_regions': len(report['unresolved_enclosed_regions']),
            'possible_holes': holes, 'accepted_possible_holes': bool(holes and accept_possible_holes)}


def approve_static(run_dir, *, reviewed_by, reason, aseprite_reviewed, transparent=None, accept_possible_holes=False):
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
    if transparent is not None:
        record['delivery'] = validate_delivery(evidence['export'], transparent, accept_possible_holes=accept_possible_holes)
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
    delivery = record.get('delivery')
    if delivery and (digest(delivery['transparent'], resolver) != delivery['transparent_sha256']
                     or digest(delivery['report'], resolver) != delivery['report_sha256']):
        raise ValueError('Approved transparent delivery changed')
    return record
