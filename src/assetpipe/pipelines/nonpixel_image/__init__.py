from ...providers import CLI_ENGINES, ProviderError, create_provider
from ...providers.comfyui import ComfyUIProvider
from ...qa import basic_image_qa

def run(brief, workflow, config, directory, manifest, seed):
    from ...portrait_delivery import profile, preflight, process
    delivery = profile(brief, config.root, workflow['id'])
    if delivery:
        preflight(delivery)
    engine = workflow.get('engine', 'comfyui')
    external = engine in CLI_ENGINES
    if not external:
        paths = ComfyUIProvider(config).generate(brief, workflow, directory / '010_generation', seed)
    else:
        try:
            result = create_provider(engine, config).run(brief, workflow, directory / '010_generation', seed)
        except ProviderError as exc:
            # 실패해도 provider 기록(진단·로그·타이밍)은 manifest에 남긴다. 다른 provider로 넘어가지 않는다.
            manifest['generation']['provider'] = exc.record
            raise
        paths = result.outputs
        manifest['generation']['provider'] = result.record
    if not paths:
        raise ValueError('Generation produced no outputs')
    compiled_path = directory / '010_generation' / 'compiled_prompt.json'
    if compiled_path.is_file():
        import json
        compiled = json.loads(compiled_path.read_text(encoding='utf-8'))
        manifest['generation']['compiled_prompt'] = compiled
        if compiled.get('exclusion_review'):
            manifest['exclusion_review'] = compiled['exclusion_review']
    elif delivery:
        raise ValueError('Portrait delivery requires preserved compiled prompt evidence')
    if delivery:
        manifest['generation']['raw_outputs'] = [str(path) for path in paths]
        processed = [process(path, brief['constraints']['resolution'], delivery,
                             directory / '020_delivery' / str(index)) for index, path in enumerate(paths)]
        paths = [row[0] for row in processed]
        manifest['portrait_delivery'] = [row[1] for row in processed]
        manifest['delivery_ready'] = False
    reports = [basic_image_qa(path, brief, external_engine=external) for path in paths]
    manifest['qa_results'].extend(reports)
    failed = [reason for report in reports for reason in report['reasons']]
    if failed:
        manifest['pipeline_steps'].append({'step': 'generation_and_basic_qa', 'status': 'FAIL'})
        # 불충족 결과는 자동 통과시키지 않는다. 원본 후보는 검토를 위해 manifest에 남긴다.
        manifest['generation']['rejected_outputs'] = [str(path) for path in paths]
        raise ValueError(failed[0])
    manifest['pipeline_steps'].append({'step': 'generation_and_basic_qa', 'status': 'PASS'})
    manifest['outputs'] = [str(path) for path in paths]
    manifest['status'] = 'CANDIDATE_READY_REVIEW_REQUIRED'
    return manifest
