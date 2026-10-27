"""Research-only transfer of verified still-source semantics to reference motion."""
import copy
import json

import yaml

from ...prompts import compile_prompt, natural_language_prompt, subject_lead, direction_tail
from ...registry import load_registry
from ...styles import resolve_style, select_recipe
from ...styles.menu import bind_menu
from ...styles.contracts import CONTRACT_FIELDS, contract_digest
from ...router import satisfied


def compile_reference_prompt(brief, workflow, root, parent_path, action):
    # Resolve SOT/menu locks even for legacy sources; never remove style fields.
    bound, menu = bind_menu(brief, root)
    selection = resolve_style(bound, root)
    styled = bool(menu or selection or bound.get('prompt_spec', {}).get('style_contract_id'))
    if not styled:
        result = compile_prompt(brief, workflow, root)
    else:
        profiles = yaml.safe_load((root / 'config/model_profiles.yaml').read_text(encoding='utf-8'))
        profile = profiles['profiles'][workflow['model_profile']]
        if (profile.get('reference_style_mode') != 'source_semantics_v1'
                or profile.get('prompt_adapter') != 'natural_language'):
            raise ValueError('MOTION_SOURCE_STYLE_MODE_UNSUPPORTED')
        if bound.get('override_mode') or bound.get('rescue_approval'):
            raise ValueError('MOTION_SOURCE_STYLE_OVERRIDE_UNSUPPORTED')
        parent = json.loads(parent_path.read_text(encoding='utf-8'))
        recorded = parent.get('workflow', {})
        source = load_registry(root).get(recorded.get('id'))
        if (not source or source['output_class'] != 'NONPIXEL_IMAGE'
                or source.get('status') == 'REJECTED' or source.get('hash') != recorded.get('hash')):
            raise ValueError('MOTION_SOURCE_WORKFLOW_UNVERIFIED')
        compiled = compile_prompt(brief, source, root)
        historical = parent.get('generation', {}).get('compiled_prompt')
        if historical != compiled:
            raise ValueError('MOTION_SOURCE_COMPILATION_CHANGED')
        spec = copy.deepcopy(compiled['prompt_spec'])
        caps = workflow['capabilities']
        selected = select_recipe(selection, source, root, explicit=True) if selection else None
        required = set()
        if selected:
            required.update(selected['definition']['required_capabilities'])
            required.update(selected['recipe'].get('required_capabilities', []))
        if spec.get('textInImage'):
            required.add('text_rendering')
        if spec.get('subject_integrity', {}).get('forbidden_substitutions'):
            required.add('negative_prompt')
        if any(not satisfied(caps, cap) for cap in required):
            raise ValueError('MOTION_SOURCE_CAPABILITY_UNSUPPORTED')
        contract = selected['definition'].get('style_contract') if selected else None
        if spec.get('style_contract_id') and not contract:
            raise ValueError('MOTION_SOURCE_STYLE_CONTRACT_UNRESOLVED')
        exclusions = list(spec.get('negative', []))
        if contract:
            if contract_digest(contract) != compiled['style_contract_compilation']['contract_sha256']:
                raise ValueError('MOTION_SOURCE_STYLE_CONTRACT_CHANGED')
            exclusions += [item['text'] for item in contract['forbidden_style_features']]
        if exclusions and not (caps.get('negative_prompt') or caps.get('negative_prompt_instruction')):
            raise ValueError('MOTION_SOURCE_EXCLUSIONS_UNSUPPORTED')
        # Source pose stays in provenance; only the explicitly requested action changes.
        spec['pose'] = action
        text = natural_language_prompt(bound, spec)
        if compiled['prompt_spec'].get('pose'):
            text += ('\nReference still pose and camera (initial context; animate using the requested motion): '
                     + compiled['prompt_spec']['pose'])
        text += '\nPreserve the reference camera view and framing throughout the requested motion.'
        if spec.get('subject_integrity'):
            text = subject_lead(spec, 'natural_language') + '\n' + text
        text += '\n' + direction_tail(spec)
        if contract:
            text += '\nPreserve the referenced style contract:\n' + '\n'.join(
                key + ': ' + json.dumps(contract[key], ensure_ascii=False) for key in CONTRACT_FIELDS)
            text += '\nRequired style features: ' + '; '.join(item['text'] for item in contract['required_style_features'])
        if exclusions:
            text += '\nDo not introduce: ' + '; '.join(dict.fromkeys(exclusions))
        result = {'schema_version': 1, 'adapter': 'natural_language',
                  'profile_id': workflow['model_profile'], 'reference_style_mode': 'source_semantics_v1',
                  'source_workflow': recorded, 'source_compilation': compiled,
                  'source_style_contract': contract, 'prompt_spec': spec, 'positive': text,
                  'negative': ', '.join(exclusions) if caps.get('negative_prompt') else '',
                  'negative_mode': 'NATIVE' if caps.get('negative_prompt') else 'INSTRUCTION_REVIEW_REQUIRED',
                  'style_transfer_quality': 'NOT_VERIFIED', 'review_state': 'REVIEW_REQUIRED'}
    result['positive'] += '\nRequested motion (explicit): ' + action
    result['positive'] += '\nPreserve the referenced identity, clothing, equipment and silhouette.'
    result['motion_action'] = action
    return result
