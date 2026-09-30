from PIL import Image
from ...providers.comfyui import ComfyUIProvider

def run(brief, workflow, config, directory, manifest, seed):
    paths = ComfyUIProvider(config).generate(brief, workflow, directory / '010_generation', seed)
    if not paths:
        raise ValueError('Generation produced no outputs')
    reports = []
    for path in paths:
        with Image.open(path) as image:
            image.load()
            if image.width < 1 or image.height < 1:
                raise ValueError('Invalid image dimensions')
            expected = brief['constraints']['resolution']
            if expected and list(image.size) != expected:
                raise ValueError('Image resolution differs from brief')
            if brief['constraints']['transparency'] is True and image.convert('RGBA').getchannel('A').getextrema()[0] == 255:
                raise ValueError('Requested transparent image is fully opaque')
            reports.append({'step': 'basic_image_qa', 'status': 'PASS', 'path': str(path), 'resolution': list(image.size)})
    manifest['qa_results'].extend(reports)
    manifest['pipeline_steps'].append({'step': 'generation_and_basic_qa', 'status': 'PASS'})
    manifest['outputs'] = [str(path) for path in paths]
    manifest['status'] = 'CANDIDATE_READY_REVIEW_REQUIRED'
    return manifest
