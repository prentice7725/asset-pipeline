from ..base import AVAILABLE, UNAVAILABLE, Diagnosis, ImageProvider, ProviderRun
from ..._ported.comfy_bridge.runner import run_workflow
from ..._ported.comfy_bridge.client import ComfyClient

class ComfyUIProvider(ImageProvider):
    engine = 'comfyui'
    provider_id = 'comfyui'

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

    # 공통 인터페이스. 기존 generate()의 동작과 시그니처는 그대로 두고 그 위에 얹는다.
    def diagnose(self, entry=None):
        url = self.config.section('comfyui').get('base_url', 'http://127.0.0.1:8188')
        try:
            stats = ComfyClient(url, request_timeout=2).check_connection()
        except Exception as exc:
            return Diagnosis(self.engine, self.engine, UNAVAILABLE, [f'ComfyUI is not reachable: {exc}'], {'base_url': url, 'block_code': 'COMFYUI_UNREACHABLE'})
        return Diagnosis(self.engine, self.engine, AVAILABLE, [], {'base_url': url, 'version': stats.get('system', {}).get('comfyui_version'), 'generation_probe': 'NOT_RUN'})

    def run(self, brief, entry, output, seed):
        paths = self.generate(brief, entry, output, seed)
        return ProviderRun(list(paths), {'provider_id': entry.get('id', self.engine), 'engine': self.engine, 'status': 'COMPLETED',
            'reproducibility': {'seed': 'SUPPORTED', 'seed_requested': seed, 'seed_applied': True}})
