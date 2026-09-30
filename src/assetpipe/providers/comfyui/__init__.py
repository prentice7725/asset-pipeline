from ..._ported.comfy_bridge.runner import run_workflow
from ..._ported.comfy_bridge.client import ComfyClient

class ComfyUIProvider:
    def __init__(self, config):
        self.config = config

    def generate(self, brief, workflow, output, seed):
        preset = brief['workflow_preferences'].get('preset', workflow.get('default_preset'))
        if preset not in workflow.get('presets', {}):
            raise ValueError(f'Unknown workflow preset: {preset}')
        values = {**workflow.get('presets', {}).get(preset, {}), **workflow.get('workflow_inputs', {})}
        if brief['constraints']['resolution']:
            values['width'], values['height'] = brief['constraints']['resolution']
        prompt = brief.get('prompt') or ', '.join(brief['identity']['canonical_traits'] + brief['identity']['visual_traits'])
        if not prompt.strip():
            raise ValueError('Prepared brief must supply prompt or explicit visual traits')
        prompt = ', '.join(filter(None, [workflow.get('prompt_prefix'), prompt]))
        from pathlib import Path
        reference = Path(brief['source']['paths'][0]) if brief['source']['type'] == 'REFERENCE_IMAGE' else None
        return run_workflow(self.config, workflow_name=workflow['workflow_name'], prompt=prompt, negative_prompt=brief.get('negative_prompt', ', '.join(brief['forbidden_elements'])), seed=seed, input_image=reference, output_dir=output, workflow_inputs=values, filename_prefix=f'assetpipe/{brief["asset_id"]}')
