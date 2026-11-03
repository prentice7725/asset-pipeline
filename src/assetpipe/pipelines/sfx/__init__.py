"""Text-to-SFX candidate generation; listening review is always required."""
import hashlib
import subprocess
from pathlib import Path
import numpy as np
from ..._ported.comfy_bridge.runner import run_workflow
from ...manifests import write


def analyze_audio(path, expected_duration):
    import wave
    with wave.open(str(path), 'rb') as audio:
        rate, channels = audio.getframerate(), audio.getnchannels()
        if audio.getsampwidth() != 2:
            raise ValueError('Audio QA requires exported 16-bit PCM WAV')
        samples = np.frombuffer(audio.readframes(audio.getnframes()), dtype='<i2').reshape(-1, channels).astype(np.float32) / 32768
    duration = len(samples) / rate
    finite = bool(np.isfinite(samples).all())
    peak = float(np.max(np.abs(samples))) if samples.size and finite else None
    rms = float(np.sqrt(np.mean(samples ** 2))) if samples.size and finite else None
    reasons = []
    if not finite or not samples.size:
        reasons.append('Empty or nonfinite audio')
    if rms is None or rms < 1e-6:
        reasons.append('Silent audio')
    if abs(duration - expected_duration) > max(1.0, expected_duration * .1):
        reasons.append('Duration differs from requested length')
    return {'step': 'basic_audio_qa', 'status': 'FAIL' if reasons else 'PASS',
            'sample_rate': rate, 'channels': samples.shape[1], 'duration_seconds': duration,
            'requested_duration_seconds': expected_duration, 'peak': peak, 'rms': rms,
            'clipped_sample_fraction': float(np.mean(np.abs(samples) >= .999)) if finite and samples.size else None,
            'reasons': reasons, 'listening_review': 'REQUIRED'}


def _text_preflight(brief):
    from ...prompts import from_brief
    from ...brief import validate
    validate(brief)
    if brief['output_class'] != 'SFX' or brief['source']['type'] not in {'PROMPT','DOCUMENTS'} or brief['source']['references']:
        raise ValueError('SFX supports text only')
    spec = from_brief(brief)
    if spec.get('textInImage') or spec.get('aspectRatio') or spec.get('negative') or brief.get('negative_prompt') or brief['forbidden_elements']:
        raise ValueError('Visual text/aspect ratio is not supported for SFX')
    return spec


def preflight(brief, *, clip=None):
    from ...audio.sfx import clip_contract
    spec = _text_preflight(brief)
    if 'synth' in brief:
        raise ValueError('SFX_SYNTH_ENGINE_REQUIRED: synth parameters need the explicit rfxgen workflow')
    duration = brief.get('audio', {}).get('duration_seconds', 5)
    metadata = clip_contract(clip if clip is not None else {'duration_seconds':duration},brief['asset_id'])
    if metadata['duration_seconds'] != duration:
        raise ValueError('SFX clip duration differs from Brief')
    return spec, metadata


def run(brief, workflow, config, directory, manifest, seed, *, clip=None):
    if workflow.get('engine') == 'rfxgen':
        if clip is not None:
            raise ValueError('SFX_SYNTH_INVALID: clip length comes from the synth parameters')
        return run_synth(brief, workflow, config, directory, manifest)
    from ...paths import RootResolver
    from ...audio.sfx import sha, probe_flac, review_template
    spec, metadata = preflight(brief, clip=clip)
    duration = metadata['duration_seconds']
    directory = Path(directory).resolve(strict=True)
    resolver = RootResolver([directory],base=directory)
    output = resolver(directory / '020_audio',strict=False)
    output.mkdir()  # One invocation only; do not dispatch again into a used run.
    receipt_path = output / 'clip_receipt.json'
    receipt = {'schema_version':1,'type':'SFX_CLIP_RECEIPT','project_id':brief.get('project_id','default'),
               'asset_id':brief['asset_id'],'run_id':directory.name,'clip':metadata,
               'status':'GENERATION_PENDING','game_ready':False,'listening_review':'REQUIRED',
               'artifacts':[],'attempts':1,'fallback':'NONE','workflow':manifest.get('workflow',{})}
    manifest['audio_clip_receipt_path'] = str(receipt_path)
    manifest['game_ready'] = False
    write(receipt_path,receipt)
    prompt = '. '.join([spec['subject'], *spec.get('appearance', []),
        *[spec[k] for k in ('environment', 'mood', 'pose') if spec.get(k)],
        *spec.get('style', []), *spec.get('constraints', [])])
    try:
        scope = hashlib.sha256(str(directory).encode()).hexdigest()[:12]
        paths = run_workflow(config, workflow_name=workflow['workflow_name'], prompt=prompt,
            seed=seed, output_dir=directory / '010_generation', workflow_inputs={'duration_seconds': duration},
            filename_prefix=f'assetpipe/{receipt["project_id"]}/{brief["asset_id"]}/{scope}')
        paths = [resolver(p) for p in paths]
        manifest['outputs'] = [str(p) for p in paths]
        receipt['artifacts'] = [{'role':'ORIGINAL_FLAC','path':str(p),'sha256':sha(p)} for p in paths]
        write(receipt_path,receipt)
        if len(paths) != 1:
            raise ValueError('SFX expects one audio candidate')
        original = probe_flac(paths[0])
        receipt['artifacts'][0]['format'] = original
        generated = resolver(directory/'010_generation/generation.json')
        receipt['generation_evidence'] = {'path':str(generated),'sha256':sha(generated)}
        wav = resolver(output / (metadata['clip_name'] + '.wav'),strict=False)
        subprocess.run(['ffmpeg','-nostdin','-n','-v','error','-i',str(paths[0]),'-c:a','pcm_s16le',str(wav)],
            check=True,capture_output=True,timeout=60)
        manifest['outputs'].append(str(wav))
        receipt['artifacts'].append({'role':'PCM_WAV','path':str(wav),'sha256':sha(wav)})
        report = analyze_audio(wav,duration)
        report['sha256'] = sha(wav)
        if report['sample_rate'] != original['sample_rate'] or report['channels'] != original['channels']:
            report['status'] = 'FAIL';report['reasons'].append('Source sample rate/channels changed')
        qa_path = output / 'audio_qa.json'
        write(qa_path,report)
        receipt['qa'] = {'path':str(qa_path),'sha256':sha(qa_path)}
        receipt['sample_format'] = {k:report[k] for k in ['sample_rate','channels','duration_seconds','requested_duration_seconds','peak','rms','clipped_sample_fraction']}
        manifest['qa_results'].append(report)
        manifest['pipeline_steps'].append({'step':'basic_audio_qa','status':report['status']})
        if report['status'] != 'PASS':
            raise ValueError('Audio QA failed; listening/export approval blocked')
        receipt['status'] = 'AUDIO_CANDIDATE_READY_REVIEW_REQUIRED'
        write(receipt_path,receipt)
        write(output/'listening_review_template.json',review_template(directory))
        manifest['status'] = receipt['status']
    except Exception as exc:
        receipt.update(status='FAILED',error=str(exc))
        manifest['status'] = 'FAILED'
        write(receipt_path,receipt)
        raise


def run_synth(brief, workflow, config, directory, manifest):
    """고정한 .rfx 한 개를 rfxgen으로 한 번 렌더링한다. 프롬프트는 의도 기록일 뿐 생성에 쓰지 않는다."""
    import shutil
    from ...paths import RootResolver
    from ...audio import rfxgen
    from ...audio.sfx import sha, clip_contract, review_template
    _text_preflight(brief)
    synth = brief.get('synth')
    if not synth:
        raise ValueError('SFX_SYNTH_PARAMS_REQUIRED: rfxgen renders an explicit .rfx; it does not interpret prompts')
    source = Path(synth['params_path'])
    if not source.is_file() or sha(source) != synth['params_sha256']:
        raise ValueError('SFX_SYNTH_PARAMS_CHANGED: .rfx is missing or its hash differs from the Brief')
    params = rfxgen.parse_rfx(source)
    library = None
    if synth.get('library_id'):
        # 라이브러리 프리셋은 등록된 파일·해시와 정확히 같아야 한다. 승인 상태는 렌더링 시점 값을 기록만 한다.
        from ...audio.rfx_library import resolve
        entry = resolve(config.root, synth['library_id'])
        if entry['sha256'] != synth['params_sha256'] or entry['path'].resolve() != source.resolve():
            raise ValueError('SFX_LIBRARY_MISMATCH: Brief parameters differ from the library entry')
        library = {'id': synth['library_id'], 'state_at_render': entry['state'], 'category': entry['category']}
    executable = rfxgen.find_executable(config)  # 실행 파일이 없으면 출력 폴더를 만들기 전에 멈춘다.
    backend = workflow['backend']
    directory = Path(directory).resolve(strict=True)
    resolver = RootResolver([directory], base=directory)
    generation = resolver(directory / '010_generation', strict=False)
    output = resolver(directory / '020_audio', strict=False)
    generation.mkdir()
    output.mkdir()  # One invocation only; do not dispatch again into a used run.
    receipt_path = output / 'clip_receipt.json'
    clip_name = clip_contract({'duration_seconds': 1}, brief['asset_id'], synth=True)['clip_name']
    receipt = {'schema_version': 1, 'type': 'SFX_CLIP_RECEIPT', 'engine': 'rfxgen',
               'project_id': brief.get('project_id', 'default'), 'asset_id': brief['asset_id'], 'run_id': directory.name,
               'clip': None, 'status': 'GENERATION_PENDING', 'game_ready': False, 'listening_review': 'REQUIRED',
               'artifacts': [], 'attempts': 1, 'fallback': 'NONE', 'workflow': manifest.get('workflow', {}),
               'synth': {'engine': 'rfxgen', 'params_sha256': synth['params_sha256'], 'params_origin': str(source),  # 출처 기록. run 밖 경로라 다시 읽지 않는다.
                         'output_format': backend['output_format'], 'parameters': params,
                         'exact_reproduction': 'NOT_VERIFIED', 'library': library}}
    manifest['audio_clip_receipt_path'] = str(receipt_path)
    manifest['game_ready'] = False
    manifest['generation']['synth'] = {'engine': 'rfxgen', 'params_sha256': synth['params_sha256'],
                                       'rand_seed': params['randSeed'], 'exact_reproduction': 'NOT_VERIFIED'}
    write(receipt_path, receipt)
    try:
        params_copy = generation / 'params.rfx'
        shutil.copyfile(source, params_copy)
        if sha(params_copy) != synth['params_sha256']:
            raise ValueError('SFX_SYNTH_PARAMS_CHANGED: copied .rfx differs from the Brief')
        receipt['artifacts'].append({'role': 'SYNTH_PARAMS_RFX', 'path': str(params_copy), 'sha256': sha(params_copy)})
        wav = resolver(generation / (clip_name + '.wav'), strict=False)
        invocation = {'executable_sha256': sha(executable), 'tool_version': rfxgen.tool_version(executable, cwd=generation),
                      'output_format': backend['output_format'], 'timeout_seconds': backend['timeout_seconds'],
                      'attempts': 1, 'retry': 'NONE', 'fallback': 'NONE'}
        evidence = generation / 'rfxgen_invocation.json'
        try:
            invocation.update(rfxgen.render(executable, params_copy, wav,
                                            output_format=backend['output_format'], timeout=backend['timeout_seconds']))
        finally:
            write(evidence, invocation)
            receipt['generation_evidence'] = {'path': str(evidence), 'sha256': sha(evidence)}
            write(receipt_path, receipt)
        manifest['outputs'] = [str(params_copy), str(wav)]
        receipt['artifacts'].append({'role': 'PCM_WAV', 'path': str(wav), 'sha256': sha(wav)})
        import wave
        with wave.open(str(wav), 'rb') as audio:
            measured = audio.getnframes() / audio.getframerate()
        report = analyze_audio(wav, measured)  # 길이는 파라미터가 정하므로 측정값을 기준으로 기록한다.
        rate, _, channels = (int(v) for v in backend['output_format'].split(','))
        if report['sample_rate'] != rate or report['channels'] != channels:
            report['status'] = 'FAIL'; report['reasons'].append('Rendered sample rate/channels differ from the requested format')
        try:
            receipt['clip'] = clip_contract({'duration_seconds': measured, 'category': 'UNSPECIFIED'}, brief['asset_id'], synth=True)
        except ValueError:
            report['status'] = 'FAIL'; report['reasons'].append('Synth length outside 0.02-10 seconds')
        report['sha256'] = sha(wav)
        qa_path = output / 'audio_qa.json'
        write(qa_path, report)
        receipt['qa'] = {'path': str(qa_path), 'sha256': sha(qa_path)}
        receipt['sample_format'] = {k: report[k] for k in ['sample_rate', 'channels', 'duration_seconds', 'peak', 'rms', 'clipped_sample_fraction']}
        manifest['qa_results'].append(report)
        manifest['pipeline_steps'].append({'step': 'basic_audio_qa', 'status': report['status']})
        if report['status'] != 'PASS':
            raise ValueError('Audio QA failed; listening/export approval blocked')
        receipt['status'] = 'AUDIO_CANDIDATE_READY_REVIEW_REQUIRED'
        write(receipt_path, receipt)
        write(output / 'listening_review_template.json', review_template(directory))
        manifest['status'] = receipt['status']
    except Exception as exc:
        receipt.update(status='FAILED', error=str(exc))
        manifest['status'] = 'FAILED'
        write(receipt_path, receipt)
        raise
