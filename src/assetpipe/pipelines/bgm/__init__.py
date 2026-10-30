"""Text-to-BGM candidate generation; one attempt, listening review is always required."""
import hashlib
import subprocess
from pathlib import Path
from ..._ported.comfy_bridge.runner import run_workflow
from ...manifests import write


def preflight(brief):
    from ...prompts import from_brief
    from ...brief import validate
    from ...audio.bgm import music_contract
    validate(brief)
    if brief['output_class'] != 'BGM' or brief['source']['type'] not in {'PROMPT', 'DOCUMENTS'} or brief['source']['references']:
        raise ValueError('BGM supports text only')
    spec = from_brief(brief)
    if spec.get('textInImage') or spec.get('aspectRatio') or spec.get('negative') or brief.get('negative_prompt') or brief['forbidden_elements']:
        raise ValueError('Visual text, aspect ratio and negative prompts are not supported for BGM')
    return spec, music_contract(brief)


def run(brief, workflow, config, directory, manifest, seed):
    from ...paths import RootResolver
    from ...audio.bgm import sha, probe_flac, review_template, analyze_bgm, style_text
    spec, music = preflight(brief)
    directory = Path(directory).resolve(strict=True)
    resolver = RootResolver([directory], base=directory)
    output = resolver(directory / '020_audio', strict=False)
    output.mkdir()  # One invocation only; do not dispatch again into a used run.
    receipt_path = output / 'bgm_receipt.json'
    receipt = {'schema_version': 1, 'type': 'BGM_RECEIPT', 'project_id': brief.get('project_id', 'default'),
               'asset_id': brief['asset_id'], 'run_id': directory.name, 'music': music,
               'status': 'GENERATION_PENDING', 'game_ready': False, 'listening_review': 'REQUIRED',
               'artifacts': [], 'attempts': 1, 'fallback': 'NONE', 'workflow': manifest.get('workflow', {})}
    manifest['audio_clip_receipt_path'] = str(receipt_path)
    manifest['game_ready'] = False
    write(receipt_path, receipt)
    try:
        scope = hashlib.sha256(str(directory).encode()).hexdigest()[:12]
        paths = run_workflow(config, workflow_name=workflow['workflow_name'], prompt=style_text(brief, spec, music),
            seed=seed, output_dir=directory / '010_generation',
            workflow_inputs={'duration_seconds': music['duration_seconds'], 'lyrics': music['lyrics'], 'sampler_seed': seed},
            filename_prefix=f'assetpipe/{receipt["project_id"]}/{brief["asset_id"]}/{scope}')
        paths = [resolver(p) for p in paths]
        manifest['outputs'] = [str(p) for p in paths]
        receipt['artifacts'] = [{'role': 'ORIGINAL_FLAC', 'path': str(p), 'sha256': sha(p)} for p in paths]
        write(receipt_path, receipt)
        if len(paths) != 1:
            raise ValueError('BGM expects one audio candidate')
        original = probe_flac(paths[0])
        receipt['artifacts'][0]['format'] = original
        generated = resolver(directory / '010_generation/generation.json')
        receipt['generation_evidence'] = {'path': str(generated), 'sha256': sha(generated)}
        wav = resolver(output / (brief['asset_id'] + '.wav'), strict=False)
        subprocess.run(['ffmpeg', '-nostdin', '-n', '-v', 'error', '-i', str(paths[0]), '-c:a', 'pcm_s16le', str(wav)],
            check=True, capture_output=True, timeout=120)
        manifest['outputs'].append(str(wav))
        receipt['artifacts'].append({'role': 'PCM_WAV', 'path': str(wav), 'sha256': sha(wav)})
        report = analyze_bgm(wav, music)
        report['sha256'] = sha(wav)
        if report['sample_rate'] != original['sample_rate'] or report['channels'] != original['channels']:
            report['status'] = 'FAIL'
            report['reasons'].append('Source sample rate/channels changed')
        qa_path = output / 'audio_qa.json'
        write(qa_path, report)
        receipt['qa'] = {'path': str(qa_path), 'sha256': sha(qa_path)}
        receipt['sample_format'] = {k: report[k] for k in ['sample_rate', 'channels', 'duration_seconds', 'requested_duration_seconds', 'peak', 'rms', 'clipped_sample_fraction']}
        receipt['loop_point'] = {k: v for k, v in report['loop'].items() if k.startswith('loop_') or k == 'method'} if music['loop'] else None
        manifest['qa_results'].append(report)
        manifest['pipeline_steps'].append({'step': 'bgm_audio_qa', 'status': report['status']})
        if report['status'] != 'PASS':
            raise ValueError('BGM audio QA failed; listening/export approval blocked')
        receipt['status'] = 'AUDIO_CANDIDATE_READY_REVIEW_REQUIRED'
        write(receipt_path, receipt)
        write(output / 'listening_review_template.json', review_template(directory))
        manifest['status'] = receipt['status']
    except Exception as exc:
        receipt.update(status='FAILED', error=str(exc))
        manifest['status'] = 'FAILED'
        write(receipt_path, receipt)
        raise
