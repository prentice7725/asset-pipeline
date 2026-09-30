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
    route_parser = commands.add_parser('route')
    route_parser.add_argument('--brief', type=Path, required=True)
    route_parser.add_argument('--output', type=Path, default=Path('route_decision.json'))
    run = commands.add_parser('create')
    run.add_argument('--brief', type=Path)
    run.add_argument('--type', choices=['pixel-static', 'pixel-animation', 'nonpixel-image', 'nonpixel-animation'])
    run.add_argument('--prompt', default='')
    run.add_argument('--reference', type=Path)
    run.add_argument('--action')
    run.add_argument('--asset-id', default='asset')
    run.add_argument('--workflow')
    run.add_argument('--preset')
    run.add_argument('--seed', type=int)
    run.add_argument('--output', type=Path)
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
    args = parser.parse_args(argv)
    try:
        if args.command == 'brief':
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
        elif args.command == 'route':
            decision = route(load(args.brief), load_registry(args.root))
            write(args.output, decision)
            print(json.dumps(decision, indent=2))
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
        else:
            if args.brief and (args.type or args.prompt or args.reference or args.action):
                raise ValueError('Use a prepared brief or direct input flags separately')
            if not args.brief and not args.type:
                raise ValueError('--type is required for direct input')
            brief = load(args.brief) if args.brief else make(asset_id=args.asset_id, output_class=args.type.upper().replace('-', '_'), prompt=args.prompt, reference=args.reference, action=args.action)
            if args.workflow:
                brief['workflow_preferences']['id'] = args.workflow
            if args.preset:
                brief['workflow_preferences']['preset'] = args.preset
            print(create(brief, args.root, args.output, args.seed))
        return 0
    except Exception as exc:
        print(f'assetpipe: {exc}', file=__import__('sys').stderr)
        return 1
