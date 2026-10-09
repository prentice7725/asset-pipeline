"""Source-scoped instruction handling; never certifies semantic compliance."""

MODE = 'POSITIVE_TEXT_INSTRUCTION_REVIEW_REQUIRED'


def instruction_review_allowed(brief, selection, workflow_id):
    policy = (selection or {}).get('_exclusion_policy', {})
    return (brief.get('project_contract_required') is True
            and brief.get('output_class') == 'NONPIXEL_IMAGE'
            and policy.get('mode') == MODE
            and policy.get('workflow_id') == workflow_id
            and policy.get('human_review_required') is True)


def review_template(items):
    return {'mode': MODE, 'status': 'REVIEW_REQUIRED', 'approval_effect': 'NONE',
            'native_negative_supported': False, 'delivery_ready': False,
            'checks': [{'requirement': item, 'decision': 'NOT_REVIEWED', 'notes': ''}
                       for item in items],
            'human_review': {'reviewed_by': None, 'reviewed_at': None}}
