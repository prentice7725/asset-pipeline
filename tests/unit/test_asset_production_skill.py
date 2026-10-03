"""Offline contract test for the shared agent-led prompt production skill.

Fixed agent-stage records exercise the source → plan → prompt → review →
correction → compiled candidate contract. They do not evaluate a live LLM or
submit image generation requests.
"""
import copy
import json
from pathlib import Path
import shutil

import pytest
import yaml

from assetpipe.api import route_brief
from assetpipe.brief import make
from assetpipe.prompts import compile_prompt
from assetpipe.registry import load_registry

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / 'plugin/skills/asset-production/SKILL.md'
CONTRACT = ROOT / 'plugin/references/AGENT_PROMPT_WORKFLOW.md'
SOT = ROOT / 'tests/fixtures/agent_prompt_workflow/project_visual_sot.md'


def fixture_root(tmp_path):
    root = tmp_path / 'engine'
    shutil.copytree(ROOT / 'config', root / 'config')
    project = root / 'config/styles/projects/agent_skill_fixture'
    project.mkdir(parents=True)
    (project / 'visual_sot.yaml').write_text(yaml.safe_dump({
        'style_id': 'anime-cel',
        'source': str(SOT.resolve()),
    }, sort_keys=False), encoding='utf-8')
    return root


def make_brief(workflow_id):
    brief = make(asset_id='agent_prompt_skill_fixture', output_class='NONPIXEL_IMAGE',
                 prompt='Fantasy scout in a forest gate scene')
    brief.update({
        'project_id': 'agent_skill_fixture',
        'source': {'type': 'DOCUMENTS', 'paths': [str(SOT.resolve())], 'references': []},
        'identity': {
            'canonical_traits': ['blue tunic', 'visible insignia', 'six front belt pouches'],
            'visual_traits': ['weathered wooden gate', 'small red warning flag attached to the gate'],
        },
        'source_notes': [
            {'classification': 'EXPLICIT', 'text': 'Fantasy scout with the three listed required traits.', 'source': str(SOT.resolve())},
            {'classification': 'EXPLICIT', 'text': 'Six pouches are worn on the front belt; front-view standing pose.', 'source': str(SOT.resolve())},
            {'classification': 'EXPLICIT', 'text': 'The warning flag stays attached to the wooden gate.', 'source': str(SOT.resolve())},
            {'classification': 'UNSPECIFIED', 'text': 'Face expression, exact height and unlisted accessories.', 'source': str(SOT.resolve())},
        ],
        'workflow_preferences': {'id': workflow_id},
        'unspecified_elements': ['face expression', 'exact height', 'unlisted accessories'],
        'prompt_spec': {
            'subject': 'Fantasy scout',
            'pose': 'walking away from the gate',
            'composition': 'Rear view; carry the six front belt pouches in both hands.',
            'environment': 'The source-defined gate and attached red warning flag remain visible.',
            'subject_integrity': {
                'class': 'full_character',
                'identity_source': str(SOT.resolve()),
                'whole_subject_required': True,
                'physically_connected_body': True,
                'mandatory_parts': ['head', 'torso', 'left arm', 'right arm', 'left leg', 'right leg'],
                'camera_view': 'front',
                'equipment': [
                    {'source_trait': 'blue tunic', 'relationship': 'worn'},
                    {'source_trait': 'six front belt pouches', 'relationship': 'worn', 'visible_count': 6, 'location': 'front'},
                ],
            },
        },
    })
    return brief


@pytest.mark.parametrize(('workflow_id', 'adapter'), [
    ('anima_base', 'anima'),
    ('krea2_base', 'krea2'),
])
def test_sot_plan_prompt_independent_review_correction_and_compiled_candidate(tmp_path, workflow_id, adapter):
    root = fixture_root(tmp_path)
    brief = make_brief(workflow_id)
    source_facts = SOT.read_text(encoding='utf-8')

    # Agent Art Director plan cites source facts and separates derived layout from canon.
    plan = {
        'version': 1,
        'status': 'READY',
        'sources': [
            {'path': str(SOT), 'location': 'Canonical subject facts', 'fact': 'blue tunic, visible insignia, six front belt pouches', 'classification': 'EXPLICIT'},
            {'path': str(SOT), 'location': 'Scene facts', 'fact': 'the flag remains attached to the gate', 'classification': 'EXPLICIT'},
        ],
        'workflow_id': workflow_id,
        'model_profile': 'anima-base' if adapter == 'anima' else 'krea2',
        'composition': {
            'focal_subject': 'Fantasy scout',
            'hierarchy': {'items': ['scout', 'wooden gate and attached flag'], 'classification': 'DERIVED'},
            'camera': {'choice': 'front view', 'classification': 'EXPLICIT'},
            'pose': {'choice': 'standing', 'classification': 'EXPLICIT'},
            'relationships': [{'subject': 'scout', 'relation': 'stands in front of', 'other': 'wooden gate', 'classification': 'DERIVED'}],
        },
        'detail_allocation': {
            'primary': {'items': ['scout silhouette and required traits'], 'classification': 'DERIVED'},
            'secondary': {'items': ['gate and attached flag'], 'classification': 'DERIVED'},
            'background': {'items': ['restrained scene texture'], 'classification': 'DERIVED'},
        },
        'unresolved': ['face expression', 'exact height', 'unlisted accessories'],
    }
    assert 'Style lock' in source_facts and 'Unspecified' in source_facts
    initial_route = route_brief(brief, root)
    assert initial_route['status'] == 'BLOCKED'
    assert 'BRIEF_COMPOSITION_CONFLICT' in initial_route['reason']

    # A separate reviewer pass catches source mismatches without trusting the author's summary.
    first_review = {
        'version': 1,
        'stage': 'PREGEN_PROMPT_REVIEW',
        'status': 'NEEDS_REVISION',
        'revision_attempt': 0,
        'checks': {'subject': 'PASS', 'pose': 'FAIL', 'camera': 'FAIL', 'equipment': 'FAIL', 'style_consistency': 'PASS', 'spatial_relationships': 'PASS'},
        'findings': [
            {'severity': 'BLOCKING', 'dimension': 'pose', 'source_evidence': f'{SOT}#Canonical subject facts: standing', 'prompt_evidence': 'PromptSpec.pose: walking away', 'discrepancy': 'Pose contradicts the explicit source.', 'suggested_fix': 'Use a standing pose.'},
            {'severity': 'BLOCKING', 'dimension': 'camera', 'source_evidence': f'{SOT}#Canonical subject facts: front view', 'prompt_evidence': 'PromptSpec.composition: rear view', 'discrepancy': 'Camera contradicts the explicit source and lock.', 'suggested_fix': 'Use the front view.'},
            {'severity': 'BLOCKING', 'dimension': 'equipment', 'source_evidence': f'{SOT}#Canonical subject facts: pouches worn on front belt', 'prompt_evidence': 'PromptSpec.composition: carry the pouches in both hands', 'discrepancy': 'Worn equipment was changed into carried equipment.', 'suggested_fix': 'Keep the six pouches worn on the front belt.'},
        ],
        'unresolved': [],
        'generation_requests': 0,
    }
    assert {row['dimension'] for row in first_review['findings']} == {'pose', 'camera', 'equipment'}
    assert plan['workflow_id'] == brief['workflow_preferences']['id']

    # One prompt-only correction; identity, source notes, SOT lock and model stay fixed.
    corrected = copy.deepcopy(brief)
    corrected['prompt_spec']['pose'] = 'standing in a front view beside the gate'
    corrected['prompt_spec']['composition'] = (
        'Front view. Keep the scout as the primary focal subject, standing before the gate; '
        'retain the red warning flag attached to the gate in the supporting background. '
        'Keep the required worn gear visible on the primary figure.'
    )
    second_review = {
        'version': 1,
        'stage': 'PREGEN_PROMPT_REVIEW',
        'status': 'PASS',
        'revision_attempt': 1,
        'checks': {'subject': 'PASS', 'pose': 'PASS', 'camera': 'PASS', 'equipment': 'PASS', 'style_consistency': 'PASS', 'spatial_relationships': 'PASS'},
        'findings': [],
        'unresolved': ['face expression', 'exact height', 'unlisted accessories'],
        'generation_requests': 0,
    }

    # Deterministic validation is the gate before candidate status; it must not call generation.
    decision = route_brief(corrected, root)
    assert decision['status'] == 'ROUTED'
    compiled = compile_prompt(corrected, load_registry(root)[workflow_id], root)
    assert compiled['adapter'] == adapter
    assert compiled['style_selection']['style_id'] == 'anime-cel'
    assert compiled['positive'].count('blue tunic') == 1
    assert compiled['positive'].count('six front belt pouches') == 1
    assert 'chibi' not in compiled['positive'].casefold()
    assert corrected['identity'] == brief['identity']
    assert corrected['source_notes'] == brief['source_notes']
    assert corrected['workflow_preferences'] == brief['workflow_preferences']
    assert second_review['status'] == 'PASS' and second_review['revision_attempt'] <= 2
    assert first_review['generation_requests'] == second_review['generation_requests'] == 0
    assert not (tmp_path / 'run_manifest.json').exists()

    prompt_candidate = {
        'status': 'PROMPT_CANDIDATE_VALIDATED',
        'plan': plan,
        'review_history': [first_review, second_review],
        'compiled_prompt': compiled,
        'generation_requests': 0,
    }
    serialized_candidate = json.loads(json.dumps(prompt_candidate, ensure_ascii=False))
    assert serialized_candidate['status'] == 'PROMPT_CANDIDATE_VALIDATED'
    assert serialized_candidate['review_history'][0]['status'] == 'NEEDS_REVISION'
    assert serialized_candidate['review_history'][1]['findings'] == []
    # Compiler review domains remain unvalidated; prompt review cannot certify an image.
    assert compiled['subject_contract_review']['semantic'] == 'NOT_VALIDATED'


def test_asset_production_skill_links_shared_contract_and_preserves_existing_tools():
    skill = SKILL.read_text(encoding='utf-8')
    contract = ' '.join(CONTRACT.read_text(encoding='utf-8').split())
    assert 'AGENT_PROMPT_WORKFLOW.md' in skill
    for phrase in ('ArtDirectorPlan', 'PromptReview', 'Anima', 'Krea2', 'at most **two**',
                   'Do not call `asset_generate` during review or revision',
                   'If a blocking finding remains after attempt two, return `BLOCKED`',
                   'Golden Assets', 'POSTGEN_IMAGE_REVIEW', 'six MCP tools'):
        assert phrase in contract
    schemas = sorted(p.stem for p in (ROOT / 'integrations/mcp/schemas').glob('*.json'))
    assert schemas == ['asset_build_brief', 'asset_capabilities', 'asset_continue_animation',
                       'asset_generate', 'asset_inspect_run', 'asset_route']
