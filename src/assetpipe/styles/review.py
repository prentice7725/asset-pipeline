"""Record explicit human Style Contract outcomes without automated visual claims."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def record_style_contract_review(review_file: Path, observed_features: dict, *,
                                 reviewed_by: str, reason: str) -> dict:
    path = Path(review_file).resolve()
    report = json.loads(path.read_text(encoding='utf-8'))
    review = report.get('style_contract_review')
    if not isinstance(review, dict) or review.get('status') not in {'NOT_REVIEWED', 'RECORDED'}:
        raise ValueError('STYLE_REVIEW_TEMPLATE_REQUIRED')
    if not isinstance(reviewed_by, str) or not reviewed_by.strip() or not isinstance(reason, str) or not reason.strip():
        raise ValueError('STYLE_REVIEW_REQUIRES_REVIEWER_AND_REASON')
    if not isinstance(observed_features, dict) or any(type(value) is not bool for value in observed_features.values()):
        raise ValueError('STYLE_REVIEW_OUTCOMES_MUST_BE_BOOLEAN_OBSERVATIONS')
    required = {item['code'] for item in review.get('required_features', [])}
    forbidden = {item['code'] for item in review.get('forbidden_features', [])}
    expected = required | forbidden
    if set(observed_features) != expected:
        raise ValueError('STYLE_REVIEW_OUTCOMES_MUST_COVER_EVERY_CONTRACT_FEATURE')

    failures = []
    for item in review['required_features']:
        present = observed_features[item['code']]
        item['decision'] = 'PASS' if present else 'FAIL'
        if not present:
            failures.append(item['code'])
    for item in review['forbidden_features']:
        present = observed_features[item['code']]
        item['decision'] = 'FAIL' if present else 'PASS'
        if present:
            failures.append(item['code'])
    review.update(status='RECORDED', failure_codes=sorted(failures),
                  human_review={'reviewed_by': reviewed_by.strip(),
                                'reviewed_at': datetime.now(timezone.utc).isoformat(),
                                'reason': reason.strip()},
                  approval_effect='NONE')
    report['style_contract_review'] = review
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report
