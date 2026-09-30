from ..._ported.comfy_bridge.runner import run_workflow
from ..._ported.comfy_bridge.client import ComfyClient

class ComfyUIProvider:
    def __init__(self, config):
        self.config = config

    def generate(self, brief, workflow, output, seed):
        from ...prompts import compile_prompt, workflow_values
        from ...manifests import write
        compiled = compile_prompt(brief, workflow, self.config.root)
        values = workflow_values(compiled, workflow, brief)
        from pathlib import Path
        reference = Path(brief['source']['paths'][0]) if brief['source']['type'] == 'REFERENCE_IMAGE' else None
        try:
            return run_workflow(self.config, workflow_name=workflow['workflow_name'], prompt=compiled['positive'], negative_prompt=compiled['negative'], seed=seed, input_image=reference, output_dir=output, workflow_inputs=values, filename_prefix=f'assetpipe/{brief["asset_id"]}')
        finally:
            write(output / 'compiled_prompt.json', compiled)
