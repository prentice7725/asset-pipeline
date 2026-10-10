"""Request/path validation and delegation only. No production algorithms."""
import copy
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from uuid import uuid4
import yaml
from jsonschema import Draft202012Validator
from assetpipe import api
from assetpipe.brief import load, validate
from assetpipe.manifests import now, write
from assetpipe.paths import RootResolver, ROOTS_ENV

class Adapter:
    def __init__(self, config):
        path = Path(config).resolve()
        values = yaml.safe_load(path.read_text(encoding='utf-8'))
        if not isinstance(values, dict) or set(values) != {'core_root', 'source_roots', 'output_root'}:
            raise ValueError('Config requires only core_root, source_roots, output_root')
        if not isinstance(values['source_roots'], list) or not values['source_roots']:
            raise ValueError('source_roots must be a nonempty list')
        self.root = (path.parent / values['core_root']).resolve(strict=True)
        self.sources = [(path.parent / p).resolve(strict=True) for p in values['source_roots']]
        if any(not p.is_dir() for p in self.sources):
            raise ValueError('Configured source roots must be directories')
        self.output = (path.parent / values['output_root']).resolve()
        self.output.mkdir(parents=True, exist_ok=True)
        self.resolver = RootResolver([*self.sources, self.output], base=self.root)
        self.output_resolver = RootResolver([self.output])
        self._children = {}
        status = json.loads((self.root / 'docs/bootstrap_status.json').read_text(encoding='utf-8'))
        if status.get('status') != 'ASSET_PIPELINE_V0_1_BOOTSTRAP_PASS':
            raise ValueError('Core bootstrap precondition has not passed')

    def source(self, value, *, file=True):
        if not isinstance(value, str) or not value or '\x00' in value:
            raise ValueError('Invalid source path')
        path = self.resolver(value)
        if file and not path.is_file():
            raise ValueError('Expected a regular source file')
        return path

    def output_path(self, value):
        return self.output_resolver(value, strict=False)

    def secure_brief(self, brief):
        brief = validate(copy.deepcopy(brief))
        for key in ['paths', 'references']:
            brief['source'][key] = [str(self.source(p)) for p in brief['source'][key]]
        for key, value in brief.get('production', {}).items():
            if key != 'direct_profile':
                brief['production'][key] = str(self.source(value, file=key != 'source_frames'))
        if brief['source']['type'] == 'DOCUMENTS':
            for note in brief['source_notes']:
                note['source'] = str(self.source(note['source']))
                if note['source'] not in brief['source']['paths']:
                    raise ValueError('Document note refers to an undeclared source')
        return brief

    def capabilities(self):
        return api.capabilities(self.root)

    def build_brief(self, **kwargs):
        project_id = kwargs.pop('project_id', None)
        duration_seconds = kwargs.pop('duration_seconds', None)
        if not kwargs['request_text'].strip():
            raise ValueError('request_text must not be empty')
        if kwargs.get('output_class') is None:
            if kwargs.get('prepared_brief') is None:
                return {'status': 'BLOCKED', 'brief': None, 'review_items': ['Choose an output class before creating the brief']}
            kwargs['output_class'] = kwargs['prepared_brief'].get('output_class')
        kwargs['source_documents'] = [str(self.source(p)) for p in kwargs.get('source_documents', [])]
        if kwargs.get('reference_image'):
            kwargs['reference_image'] = str(self.source(kwargs['reference_image']))
        if kwargs.get('prepared_brief') is not None:
            kwargs['prepared_brief'] = self.secure_brief(kwargs['prepared_brief'])
        brief = api.build_brief(**kwargs)
        if project_id is not None:
            brief['project_id'] = project_id
        if duration_seconds is not None:
            if brief['output_class'] != 'SFX':
                raise ValueError('duration_seconds is only supported for SFX')
            brief['audio'] = {'duration_seconds': duration_seconds}
        return {'status': 'BRIEF_READY', 'brief': self.secure_brief(brief), 'review_items': brief['unspecified_elements']}

    def route(self, brief):
        return api.route_brief(self.secure_brief(brief), self.root, self.resolver)

    def generate(self, *, brief=None, brief_file=None, seed=None):
        if (brief is None) == (brief_file is None):
            raise ValueError('Supply exactly one of brief or brief_file')
        if seed is not None and (type(seed) is not int or not 0 <= seed <= 2**64 - 1):
            raise ValueError('seed must be an unsigned 64-bit integer')
        value = self.secure_brief(load(self.source(brief_file)) if brief_file else brief)
        decision = api.route_brief(value, self.root, self.resolver)
        if decision['status'] == 'BLOCKED':
            return {**decision, 'run_id': None, 'outputs': [], 'review_items': decision['missing_requirements']}
        run_id = uuid4().hex
        project_id = value.get('project_id', 'default')
        project_root = self.output_path(self.output / project_id)
        directory = self.output_path(project_root / 'runs' / value['asset_id'] / run_id)
        request_dir = self.output_path(project_root / 'requests')
        request_dir.mkdir(parents=True, exist_ok=True)
        brief_path = self.output_path(request_dir / f'{run_id}.brief.json')
        receipt_path = self.output_path(request_dir / f'{run_id}.json')
        write(brief_path, value)
        command = [sys.executable, '-m', 'assetpipe', '--root', str(self.root), 'create', '--brief', str(brief_path), '--output', str(directory)]
        if seed is not None:
            command.extend(['--seed', str(seed)])
        receipt = {'run_id': run_id, 'project_id': project_id, 'status': 'STARTING', 'asset_id': value['asset_id'], 'manifest': str(directory / 'run_manifest.json'),
            'brief': str(brief_path), 'created_at': now()}
        write(receipt_path, receipt)
        try:
            log_path = self.output_path(request_dir / f'{run_id}.log')
            with log_path.open('xb') as log:
                child = subprocess.Popen(command, cwd=self.root, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                    shell=False, env={**os.environ, ROOTS_ENV: self.resolver.environment()}, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            self._children[run_id] = child
            receipt.update({'pid': child.pid, 'log': str(log_path)})
            write(receipt_path, receipt)
        except Exception as exc:
            receipt.update({'status': 'FAILED', 'error': str(exc)})
            write(receipt_path, receipt)
            raise
        return {'run_id': run_id, 'project_id': project_id, 'status': 'RUNNING', 'asset_id': value['asset_id'], 'output_class': value['output_class'],
            'workflow_id': decision['selected_workflow'], 'manifest': receipt['manifest'], 'qa': [], 'outputs': [], 'review_items': []}

    def inspect(self, run_id):
        if not isinstance(run_id, str) or not re.fullmatch('[a-f0-9]{32}', run_id):
            raise ValueError('Unknown/invalid run_id')
        matches = list(self.output.glob(f'*/requests/{run_id}.json'))
        legacy = self.output / 'requests' / f'{run_id}.json'
        if legacy.is_file():
            matches.append(legacy)
        if len(matches) != 1:
            raise ValueError('Unknown run_id')
        receipt_path = self.output_path(matches[0])
        receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
        manifest = self.output_path(receipt['manifest'])
        child = self._children.get(run_id)
        if not manifest.exists():
            if receipt.get('status') == 'STARTING' and child is not None:
                poll = getattr(child, 'poll', None)
                exit_code = poll() if callable(poll) else None
                if exit_code is not None:
                    self._children.pop(run_id, None)
                    receipt.update({'status': 'FAILED', 'exit_code': exit_code,
                        'error': f'Generation process exited with code {exit_code} before writing run manifest'})
                    write(receipt_path, receipt)
            return {'run_id': run_id, 'project_id': receipt.get('project_id', 'default'), 'status': receipt['status'], 'manifest': str(manifest), 'outputs': [], 'qa': [], 'review_items': [], 'error': receipt.get('error')}
        if child is not None:
            poll = getattr(child, 'poll', None)
            if callable(poll) and poll() is not None:
                self._children.pop(run_id, None)
        result = api.inspect_manifest(manifest, self.resolver)
        result['outputs'] = [str(self.output_path(p)) for p in result['outputs']]
        return {'run_id': run_id, 'project_id': receipt.get('project_id', 'default'), **result}

    def continue_animation(self, reference, action, output_class, constraints):
        if output_class not in {'PIXEL_ANIMATION', 'NONPIXEL_ANIMATION'}:
            raise ValueError('Animation output class required')
        if re.fullmatch('[a-f0-9]{32}', reference):
            result = self.inspect(reference)
            brief = json.loads(Path(result['manifest']).read_text(encoding='utf-8'))['asset_brief']
        else:
            brief = load(self.source(reference))
        brief = copy.deepcopy(brief)
        previous_output_class = brief['output_class']
        allowed = {'production', 'resolution', 'frame_target', 'motion_constraints'}
        if set(constraints) - allowed:
            raise ValueError('Unknown animation constraint')
        brief['output_class'] = output_class
        if previous_output_class != output_class:
            preferences = brief.setdefault('workflow_preferences', {})
            preferences.pop('id', None)
            preferences.pop('preset', None)
        brief['animation']['action'] = action
        if 'production' in constraints:
            brief['production'] = constraints['production']
        if 'resolution' in constraints:
            brief['constraints']['resolution'] = constraints['resolution']
        for field in ['frame_target', 'motion_constraints']:
            if field in constraints:
                brief['animation'][field] = constraints[field]
        return self.generate(brief=brief)
