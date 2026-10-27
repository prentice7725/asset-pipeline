import argparse
import json
from pathlib import Path
from ..brief import load, make, SCHEMA
from ..registry import load_registry
from ..router import route
from ..pipelines import create
from ..manifests import write, now

def main(argv=None):
    parser = argparse.ArgumentParser(prog='assetpipe', description='Workflow-driven game asset production; review gates are mandatory')
    parser.add_argument('--root', type=Path, default=Path.cwd(), help='Repository/config root')
    commands = parser.add_subparsers(dest='command', required=True)
    motion_package = commands.add_parser('motion-package', help='Package an existing nonpixel video for research review; no generation')
    motion_package.add_argument('--request', required=True, type=Path)
    motion_package.add_argument('--video', required=True, type=Path)
    motion_package.add_argument('--video-sha256', required=True)
    motion_package.add_argument('--output', required=True, type=Path)
    motion_package.add_argument('--allowed-root', action='append', type=Path)
    for name in ['motion-recipe-plan', 'motion-recipe-apply', 'motion-recipe-inspect']:
        recipe = commands.add_parser(name, help='Explicit offline motion candidate recipe; no generation or approval')
        recipe.add_argument('--allowed-root', action='append', type=Path)
        if name == 'motion-recipe-inspect':
            recipe.add_argument('--run', required=True, type=Path)
            recipe.add_argument('--manifest-sha256', required=True)
        else:
            recipe.add_argument('--recipe', required=True, type=Path)
        if name == 'motion-recipe-apply':
            recipe.add_argument('--plan-sha256', required=True)
            recipe.add_argument('--output', required=True, type=Path)
    for name in ['motion-preflight', 'motion-prepare', 'motion-inspect']:
        motion = commands.add_parser(name, help='Read-only video gates or frozen research inputs; never generates')
        motion.add_argument('--allowed-root', action='append', type=Path)
        if name == 'motion-inspect':
            motion.add_argument('--run', required=True, type=Path)
        else:
            motion.add_argument('--request', required=True, type=Path)
        if name == 'motion-preflight':
            motion.add_argument('--inspect-installation', action='store_true')
        if name == 'motion-prepare':
            motion.add_argument('--output', required=True, type=Path)
    for name in ['motion-execution-plan', 'motion-execute']:
        execution = commands.add_parser(name, help='Explicit one-reference research probe plan or one authorized generation attempt')
        execution.add_argument('--run', required=True, type=Path)
        execution.add_argument('--seed', required=True, type=int)
        execution.add_argument('--width', required=True, type=int)
        execution.add_argument('--height', required=True, type=int)
        execution.add_argument('--allowed-root', action='append', type=Path)
        if name == 'motion-execute':
            execution.add_argument('--authorization', required=True, type=Path)
            execution.add_argument('--authorize-generation', required=True, action='store_true')
    audio_review = commands.add_parser('sfx-review',help='Record explicit listening observations; no generation or game approval')
    audio_review.add_argument('--run',required=True,type=Path)
    audio_review.add_argument('--review',required=True,type=Path)
    audio_review.add_argument('--listened',required=True,action='store_true')
    knowledge = commands.add_parser('knowledge', help='Offline model/style/evidence lookup; never generates or approves')
    knowledge.add_argument('--model-id', help='Known model variant key')
    knowledge.add_argument('--style-id', help='Known style key')
    knowledge.add_argument('--output', type=Path, help='Optional JSON report path; stdout by default')
    knowledge.add_argument('--models-root', type=Path, help='Only scan dependencies under this explicit ComfyUI models/ directory')
    knowledge.add_argument('--hash-models', action='store_true', help='Stream full SHA256 for present declared weights; slower')
    knowledge.add_argument('--discover-unregistered', action='store_true', help='Opt-in scan of unknown model-like filenames; no hashes')
    visual = commands.add_parser('visual-review', help='Create advisory previews for an existing technically passing candidate; no generation or approval')
    visual.add_argument('--run', required=True, type=Path)
    visual.add_argument('--image', type=Path, help='Select one output when the manifest has multiple outputs')
    visual.add_argument('--display-size', nargs=2, type=int, metavar=('WIDTH', 'HEIGHT'))
    visual.add_argument('--matte', nargs=3, type=int, default=(255, 255, 255), metavar=('R', 'G', 'B'))
    style_review = commands.add_parser('style-review', help='Record human Style Contract observations and failure codes; never approves')
    style_review.add_argument('--review-file', required=True, type=Path, help='visual_review.json containing the generated Style Contract checklist')
    style_review.add_argument('--observed-features', required=True, type=Path, help='JSON object mapping every feature code to true/false observed in the image')
    style_review.add_argument('--reviewed-by', required=True)
    style_review.add_argument('--reason', required=True)
    factory = commands.add_parser('factory', help='Factory plans, still/audio execution and explicit staged motion jobs')
    factory_commands = factory.add_subparsers(dest='factory_command', required=True)
    for name in ['plan', 'dry-run', 'inspect']:
        presentation = factory_commands.add_parser(name, help='Validate inputs and print a read-only factory plan')
        presentation.add_argument('--request', required=True, type=Path)
        presentation.add_argument('--allowed-root', action='append', type=Path, help='Explicit source roots; repository root is the default')
    execution = factory_commands.add_parser('execute', help='One authorized still/audio attempt; no motion, retry or approval')
    execution.add_argument('--request', required=True, type=Path)
    execution.add_argument('--seed', required=True, type=int)
    execution.add_argument('--authorize-generation', required=True, action='store_true')
    execution.add_argument('--allowed-root', action='append', type=Path)
    for name in ['motion-plan', 'motion-run', 'motion-inspect', 'motion-prepare']:
        stage = factory_commands.add_parser(name, help='Explicit motion stages; no default activation or automatic retry')
        stage.add_argument('--allowed-root', action='append', type=Path)
        if name == 'motion-prepare':
            stage.add_argument('--request', required=True, type=Path)
            stage.add_argument('--output', required=True, type=Path)
        elif name == 'motion-inspect':
            stage.add_argument('--run', required=True, type=Path)
            stage.add_argument('--manifest-sha256', required=True)
        else:
            stage.add_argument('--job', required=True, type=Path)
        if name == 'motion-run':
            stage.add_argument('--plan-sha256', required=True)
            stage.add_argument('--output', required=True, type=Path)
            stage.add_argument('--authorization', type=Path)
            stage.add_argument('--authorize-generation', action='store_true')
    route_parser = commands.add_parser('route')
    route_parser.add_argument('--brief', type=Path, required=True)
    route_parser.add_argument('--output', type=Path, default=Path('route_decision.json'))
    rescue = commands.add_parser('rescue-plan', help='Propose at most three subject rescue candidates; never generates')
    rescue.add_argument('--brief', type=Path, required=True)
    rescue.add_argument('--output', type=Path, required=True)
    rescue.add_argument('--inspect-installation', action='store_true', help='Read live ComfyUI node/model inventories; no generation')
    prompt_parser = commands.add_parser('compile-prompt', help='Compile canonical PromptSpec for the selected workflow without generating')
    prompt_parser.add_argument('--brief', required=True, type=Path)
    prompt_parser.add_argument('--output', required=True, type=Path)
    run = commands.add_parser('create')
    run.add_argument('--brief', type=Path)
    run.add_argument('--type', choices=['pixel-static', 'pixel-animation', 'nonpixel-image', 'nonpixel-animation', 'sfx'])
    run.add_argument('--duration', type=float, help='SFX duration in seconds (1–30; default 5)')
    run.add_argument('--prompt', default='')
    run.add_argument('--reference', type=Path)
    run.add_argument('--action')
    run.add_argument('--asset-id')
    run.add_argument('--project', help='Project folder ID; otherwise use brief project_id or default')
    run.add_argument('--workflow')
    run.add_argument('--style-id', help='Style Catalog/Project Style Pack ID (NONPIXEL_IMAGE)')
    run.add_argument('--model-profile', help='Explicit configured model profile')
    run.add_argument('--preset')
    run.add_argument('--seed', type=int, help='ComfyUI only; CLI providers (codex_cli, grok_cli) record seed as unsupported')
    run.add_argument('--allow-experimental', action='store_true', help='Allow an EXPERIMENTAL workflow that was requested explicitly by --workflow')
    run.add_argument('--output', type=Path)
    run.add_argument('--motion-job', type=Path, help='Explicit NONPIXEL_ANIMATION Factory job; no prompt-based video routing')
    run.add_argument('--motion-plan-sha256', help='Expected hash from factory motion-plan')
    run.add_argument('--allowed-root', action='append', type=Path, help='Explicit motion job source roots only')
    run.add_argument('--authorization', type=Path, help='Existing single-attempt video authorization; motion job only')
    run.add_argument('--authorize-generation', action='store_true', help='Consent for prepared video job only; replay rejects it')
    providers = commands.add_parser('providers', help='Diagnose generation providers without any paid request')
    providers.add_argument('--provider', choices=['comfyui', 'codex_cli', 'grok_cli'], action='append', help='Limit diagnosis to these providers (default: all)')
    providers.add_argument('--output', type=Path)
    brief_parser = commands.add_parser('brief')
    briefs = brief_parser.add_subparsers(dest='brief_command', required=True)
    schema = briefs.add_parser('schema')
    schema.add_argument('--output', type=Path, default=Path('schemas/asset_brief.schema.json'))
    docs = briefs.add_parser('from-docs', help='Validate a Codex-prepared brief against its source paths; no automatic canon inference')
    docs.add_argument('sources', nargs='+', type=Path)
    docs.add_argument('--prepared', required=True, type=Path)
    docs.add_argument('--output', required=True, type=Path)
    resume = commands.add_parser('export-static')
    resume.add_argument('--run', required=True, type=Path)
    resume.add_argument('--resolution-review', required=True, type=Path)
    approve = commands.add_parser('approve-static', help='Approve only a validated static export after explicit Aseprite review')
    approve.add_argument('--run', required=True, type=Path)
    approve.add_argument('--reviewed-by', required=True)
    approve.add_argument('--reason', required=True)
    approve.add_argument('--aseprite-reviewed', action='store_true', required=True)
    mining = commands.add_parser('mining', help='Offline prompt research; no generation, downloads or approval')
    mining_commands = mining.add_subparsers(dest='mining_command', required=True)
    mining_validate = mining_commands.add_parser('validate')
    mining_validate.add_argument('--candidates', type=Path)
    mining_validate.add_argument('--output', type=Path, required=True)
    mining_compile = mining_commands.add_parser('compile')
    mining_compile.add_argument('--candidate-id', required=True)
    mining_compile.add_argument('--brief', type=Path, required=True)
    mining_compile.add_argument('--workflow', required=True)
    mining_compile.add_argument('--output', type=Path, required=True)
    ingest = mining_commands.add_parser('ingest-civitai', help='Validate saved public API JSON; no network calls')
    ingest.add_argument('--input', type=Path, required=True)
    ingest.add_argument('--versions', type=Path, required=True)
    ingest.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command in {'motion-recipe-plan', 'motion-recipe-apply', 'motion-recipe-inspect'}:
            from ..motion.recipe import plan_recipe, apply_recipe, inspect_recipe
            from ..factory.provenance import fingerprint
            if args.command == 'motion-recipe-plan':
                result = plan_recipe(args.recipe, args.root, allowed_roots=args.allowed_root)
            elif args.command == 'motion-recipe-apply':
                path = apply_recipe(args.recipe, args.plan_sha256, args.output, args.root,
                                    allowed_roots=args.allowed_root)
                result = {'manifest_path': str(path), 'manifest_sha256': fingerprint(path),
                          'review_state': 'REVIEW_REQUIRED', 'game_ready': False}
            else:
                result = inspect_recipe(args.run, args.root, expected_sha256=args.manifest_sha256,
                                        allowed_roots=args.allowed_root)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.command in {'motion-execution-plan', 'motion-execute'}:
            from ..providers.video.executor import execution_plan, execute_prepared
            options = dict(seed=args.seed, width=args.width, height=args.height, allowed_roots=args.allowed_root)
            if args.command == 'motion-execution-plan':
                result = execution_plan(args.run, args.root, **options)
            else:
                result = {'execution_receipt_path': str(execute_prepared(
                    args.run, args.authorization, args.root,
                    authorize_generation=args.authorize_generation, **options))}
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.command in {'motion-preflight', 'motion-prepare', 'motion-inspect'}:
            from ..providers.video import preflight_file, prepare_file, inspect_prepared
            if args.command == 'motion-preflight':
                result = preflight_file(args.request, args.root, allowed_roots=args.allowed_root,
                                        inspect_installation=args.inspect_installation)
            elif args.command == 'motion-prepare':
                result = {'prepared_path': str(prepare_file(args.request, args.output, args.root,
                                                           allowed_roots=args.allowed_root))}
            else:
                result = inspect_prepared(args.run, args.root, allowed_roots=args.allowed_root)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.command == 'motion-package':
            from ..motion.package import package_video
            print(package_video(args.request, args.video, args.video_sha256, args.output,
                                args.root, allowed_roots=args.allowed_root))
        elif args.command == 'sfx-review':
            from ..paths import RootResolver
            from ..audio.sfx import record_review
            resolver = RootResolver([args.root],base=args.root)
            run = resolver(args.run)
            review = json.loads(resolver(args.review).read_text(encoding='utf-8'))
            print(record_review(run,review,listened=args.listened,resolver=resolver))
        elif args.command == 'factory':
            from ..api import factory_plan, factory_execute
            if args.factory_command.startswith('motion-'):
                from ..factory.motion import plan_job, run_job, inspect_job
                from ..factory.provenance import fingerprint
                if args.factory_command == 'motion-plan':
                    result = plan_job(args.job, args.root, allowed_roots=args.allowed_root)
                elif args.factory_command == 'motion-inspect':
                    result = inspect_job(args.run, args.manifest_sha256, args.root, allowed_roots=args.allowed_root)
                else:
                    if args.factory_command == 'motion-prepare':
                        from ..providers.video import prepare_file
                        path = prepare_file(args.request, args.output, args.root, allowed_roots=args.allowed_root)
                    else:
                        path = run_job(args.job, args.plan_sha256, args.output, args.root,
                            authorization=args.authorization, authorize_generation=args.authorize_generation,
                            allowed_roots=args.allowed_root)
                    result = {'manifest_path': str(path), 'manifest_sha256': fingerprint(path),
                              'review_state': 'REVIEW_REQUIRED', 'game_ready': False}
                print(json.dumps(result, indent=2, ensure_ascii=False))
            elif args.factory_command == 'execute':
                print(factory_execute(args.request, args.root, authorize_generation=args.authorize_generation,
                                      seed=args.seed, allowed_roots=args.allowed_root))
            else:
                print(json.dumps(factory_plan(args.request, args.root, allowed_roots=args.allowed_root), indent=2, ensure_ascii=False))
        elif args.command == 'rescue-plan':
            from ..styles.overrides import propose_rescue
            write(args.output, propose_rescue(load(args.brief), args.root, inspect_installation=args.inspect_installation))
            print(args.output)
        elif args.command == 'knowledge':
            from ..knowledge import build_snapshot, inspect, scan_expected_weights
            if (args.hash_models or args.discover_unregistered) and not args.models_root:
                raise ValueError('--hash-models/--discover-unregistered require explicit --models-root')
            result = inspect(build_snapshot(args.root), args.model_id, args.style_id)
            if args.models_root:
                result['local_weight_scan'] = scan_expected_weights(args.root, args.models_root, hash_files=args.hash_models, discover_unregistered=args.discover_unregistered)
            if args.output:
                write(args.output, result)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.command == 'visual-review':
            from ..visual_review import build_review
            print(build_review(args.run, image=args.image, display_size=args.display_size, matte=args.matte))
        elif args.command == 'style-review':
            from ..styles.review import record_style_contract_review
            outcomes = json.loads(args.observed_features.read_text(encoding='utf-8'))
            result = record_style_contract_review(args.review_file, outcomes,
                                                  reviewed_by=args.reviewed_by, reason=args.reason)
            write(args.review_file, result)
            print(args.review_file)
        elif args.command == 'mining':
            from ..prompt_mining import load_candidates, library, compile_candidate, normalize_civitai
            if args.mining_command == 'validate':
                candidates = load_candidates(args.root, args.candidates)
                recipes = library(args.root)
                report = {'status': 'OFFLINE_SCHEMA_VALID', 'candidates': len(candidates), 'recipes': len(recipes),
                    'generation_requests': 0, 'golden_approved': 0}
            elif args.mining_command == 'compile':
                report = compile_candidate(args.root, args.candidate_id, load(args.brief), args.workflow)
            else:
                saved = json.loads(args.input.read_text(encoding='utf-8'))
                versions = json.loads(args.versions.read_text(encoding='utf-8'))
                if not isinstance(saved, dict) or not isinstance(saved.get('items'), list) or not isinstance(versions, dict):
                    raise ValueError('Saved public API responses must be objects with items and version-id mappings')
                report = normalize_civitai(saved['items'], versions)
            write(args.output, report)
            print(args.output)
        elif args.command == 'brief':
            if args.brief_command == 'schema':
                write(args.output, SCHEMA)
            else:
                brief = load(args.prepared)
                sources = {str(p.resolve()) for p in args.sources}
                if any(not p.is_file() for p in args.sources) or brief['source']['type'] != 'DOCUMENTS' or set(brief['source']['paths']) != sources:
                    raise ValueError('Prepared document brief must identify exactly the existing supplied sources')
                for note in brief['source_notes']:
                    if note['source'] not in sources:
                        raise ValueError('Every document source note must identify an existing supplied source')
                write(args.output, brief)
        elif args.command == 'compile-prompt':
            from ..prompts import compile_prompt, workflow_values
            brief = load(args.brief)
            registry = load_registry(args.root)
            workflow = registry[route(brief, registry)['selected_workflow']]
            compiled = compile_prompt(brief, workflow, args.root)
            if workflow.get('engine', 'comfyui') == 'comfyui':
                compiled['workflow_inputs'] = workflow_values(compiled, workflow, brief)
                compiled['workflow_name'] = workflow['workflow_name']
            else:
                compiled.update({'workflow_inputs': {}, 'workflow_name': None, 'engine': workflow['engine']})
            write(args.output, compiled)
            print(args.output)
        elif args.command == 'providers':
            from ..providers import ENGINES, diagnose_providers
            from .._ported.config import load_config
            report = diagnose_providers(load_config(args.root / 'config/pipeline.yaml'), tuple(args.provider or ENGINES))
            if args.output:
                write(args.output, report)
            print(json.dumps(report, indent=2, ensure_ascii=False))
        elif args.command == 'route':
            decision = route(load(args.brief), load_registry(args.root))
            write(args.output, decision)
            print(json.dumps(decision, indent=2))
        elif args.command == 'approve-static':
            from ..pipelines.pixel_static.approval import approve_static
            print(approve_static(args.run, reviewed_by=args.reviewed_by, reason=args.reason, aseprite_reviewed=args.aseprite_reviewed))
        elif args.command == 'export-static':
            from ..pipelines.pixel_static import export_reviewed
            from .._ported.config import load_config
            manifest_path = args.run.resolve() / 'run_manifest.json'
            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
            try:
                export_reviewed(load_config(args.root / 'config/pipeline.yaml'), args.run, args.resolution_review, manifest)
                manifest['timestamps']['reviewed_export'] = now()
            except Exception as exc:
                manifest['pipeline_steps'].append({'step': 'reviewed_static_export', 'status': 'FAILED', 'error': str(exc), 'timestamp': now()})
                raise
            finally:
                write(manifest_path, manifest)
            print(manifest_path)
        elif args.command == 'create' and args.motion_job is not None:
            if args.type != 'nonpixel-animation':
                raise ValueError('--motion-job requires --type nonpixel-animation')
            if (any(value is not None for value in [args.brief, args.reference, args.action,
                    args.asset_id, args.project, args.workflow, args.style_id, args.model_profile,
                    args.preset, args.seed, args.duration]) or args.prompt or args.allow_experimental):
                raise ValueError('Motion inputs and settings must come from the pinned job; direct overrides are unsupported')
            from ..paths import RootResolver
            resolver = RootResolver(args.allowed_root or [args.root], base=args.root)
            print(create(None, args.root, args.output, resolver=resolver,
                motion_job=args.motion_job, motion_plan_sha256=args.motion_plan_sha256,
                authorization=args.authorization, authorize_generation=args.authorize_generation))
        else:
            if args.motion_plan_sha256 is not None or args.authorization is not None or args.authorize_generation or args.allowed_root:
                raise ValueError('Motion options require --motion-job')
            if args.brief and (args.type or args.prompt or args.reference or args.action):
                raise ValueError('Use a prepared brief or direct input flags separately')
            if not args.brief and not args.type:
                raise ValueError('--type is required for direct input')
            brief = load(args.brief) if args.brief else make(asset_id=args.asset_id or 'asset', output_class=args.type.upper().replace('-', '_'), prompt=args.prompt, reference=args.reference, action=args.action)
            if args.workflow:
                brief['workflow_preferences']['id'] = args.workflow
            if args.style_id:
                brief['style_id'] = args.style_id
            if args.model_profile:
                brief['workflow_preferences']['model_profile'] = args.model_profile
            if args.project:
                brief['project_id'] = args.project
            if args.duration is not None:
                if brief['output_class'] != 'SFX':
                    raise ValueError('--duration is only supported for SFX')
                brief['audio'] = {'duration_seconds': args.duration}
            if args.preset:
                brief['workflow_preferences']['preset'] = args.preset
            if args.allow_experimental:
                brief['workflow_preferences']['allow_experimental'] = True
            print(create(brief, args.root, args.output, args.seed))
        return 0
    except Exception as exc:
        print(f'assetpipe: {exc}', file=__import__('sys').stderr)
        return 1
