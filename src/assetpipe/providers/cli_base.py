"""CLI 기반 이미지 provider(codex_cli, grok_cli)가 공유하는 실행 템플릿.

진단 → 과금 전 사전 차단 → 격리 실행(1회, 재시도 없음) → 원본 보존 → 장애 분류 순서를 고정한다.
CLI별 차이(인증 확인, argv, 결과물 위치)는 하위 클래스의 훅에서만 다룬다.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any

from .base import (AVAILABLE, BLOCKED, UNAVAILABLE, Diagnosis, ImageProvider, ProviderBlocked, ProviderError,
                   ProviderFailed, ProviderRun)
from .cli_runner import (CliResult, JobDir, Redactor, assert_not_nested, build_env, find_first, is_within,
                         iter_json_values, now_iso, preserve_outputs, probe, resolve_executable, run_cli, sha256_file,
                         sha256_text, snapshot_images)

AUTH_FAILURE = re.compile(r'not (?:logged|signed) in|not authenticated|unauthori[sz]ed|\b401\b|invalid (?:api )?key|login required|please (?:log|sign) ?in', re.IGNORECASE)
REFUSAL = re.compile(r"can(?:no|')t (?:help|assist|generate|create|comply|do that)|cannot (?:help|assist|generate|create|comply)|unable to (?:generate|create|comply)|content policy|safety (?:policy|system|filter)|\bviolates?\b|\brefus", re.IGNORECASE)
PROBE_TIMEOUT_SECONDS = 10


class CliImageProvider(ImageProvider):
    executable_name: str
    # 자식에게 일괄 적용하는 환경(예: 외부 도구 연동 비활성화). 값은 비밀이 아니다.
    isolation_env: dict[str, str] = {}
    auth_modes = ('cli_login', 'env_api_key')

    def __init__(self, config):
        self.config = config
        self.settings = config.section('providers').get(self.engine, {}) or {}

    # ----- 하위 클래스가 구현하는 훅 -----
    def version_argv(self, exe: str) -> list[str]:
        return [exe, '--version']

    def check_auth(self, exe: str, env: dict[str, str], auth: dict, diagnosis: Diagnosis) -> None:
        """인증 상태를 과금 없이 확인해 diagnosis를 갱신한다."""
        raise NotImplementedError

    def check_features(self, exe: str, env: dict[str, str], diagnosis: Diagnosis) -> None:
        """이미지 도구 사용 가능 여부를 확인해 diagnosis를 갱신한다."""

    def wrap_prompt(self, spec_text: str, tool: str, aspect_ratio: str | None, reference: Path | None) -> str:
        raise NotImplementedError

    def build_argv(self, exe: str, job: JobDir, backend: dict, tool: str, reference: Path | None) -> tuple[list[str], str | None, dict]:
        """(argv, stdin 텍스트, 부가 정보)를 돌려준다. 프롬프트는 argv에 넣지 않는다."""
        raise NotImplementedError

    def child_env(self, auth: dict, job: JobDir) -> dict[str, str]:
        return dict(self.isolation_env)

    def parse_events(self, result: CliResult) -> dict[str, Any]:
        """stdout/stderr에서 요청 ID·모델·사용량·세션 정보를 지원되는 범위에서만 꺼낸다."""
        values = list(iter_json_values(result.stdout))
        usage = find_first(values, ('usage', 'token_usage'), (dict,))
        return {'request_id': find_first(values, ('request_id', 'requestId', 'x_request_id')),
                'session_id': find_first(values, ('thread_id', 'session_id', 'sessionId', 'conversation_id')),
                'reported_model': find_first(values, ('model', 'model_id')), 'usage': usage, 'values': values}

    def snapshot_roots(self, env: dict[str, str]) -> list[Path]:
        """생성 이미지가 저장될 수 있는 폴더. 실행 전후 비교로 이번 요청의 결과만 가려내는 데 쓴다."""
        raise NotImplementedError

    def harvest(self, result: CliResult, parsed: dict, job: JobDir, env: dict[str, str], state: dict) -> list[Path]:
        """state={'roots': [...], 'before': {...}}. 실행 전에 없었거나 갱신된 이미지만 돌려준다."""
        raise NotImplementedError

    def last_message(self, result: CliResult, job: JobDir) -> str:
        return result.stdout[-2000:]

    # ----- 공통 로직 -----
    def provider_label(self, entry: dict | None) -> str:
        return self.engine

    def _backend(self, entry: dict | None) -> dict:
        return (entry or {}).get('backend', {}) or {}

    def _auth(self, entry: dict | None) -> dict:
        auth = dict(self._backend(entry).get('auth') or {'mode': 'cli_login'})
        auth.setdefault('mode', 'cli_login')
        auth.setdefault('env', [])
        return auth

    def _env(self, auth: dict, job: JobDir | None = None) -> tuple[dict[str, str], list[str]]:
        pass_env = list(self.settings.get('pass_env', [])) + (list(auth.get('env', [])) if auth['mode'] == 'env_api_key' else [])
        env, names = build_env(pass_env, self.child_env(auth, job) if job else dict(self.isolation_env))
        return env, names

    def _executable(self) -> str | None:
        return resolve_executable(self.settings.get('executable'), self.executable_name)

    def diagnose(self, entry: dict | None = None) -> Diagnosis:
        diagnosis = Diagnosis(self.engine, self.engine, AVAILABLE)
        diagnosis.details.update({'generation_probe': 'NOT_RUN', 'note': 'Real generation is confirmed only by the E2E check'})
        try:
            auth = self._auth(entry)
            diagnosis.details['auth_mode'] = auth['mode']
            exe = self._executable()
            if not exe:
                diagnosis.status = UNAVAILABLE
                diagnosis.reasons.append(f'{self.executable_name} executable not found (PATH or providers.{self.engine}.executable)')
                diagnosis.details['block_code'] = 'EXECUTABLE_NOT_FOUND'
                return diagnosis
            diagnosis.details['executable'] = exe
            env, _names = self._env(auth)
            version = probe(self.version_argv(exe), env=env, timeout=PROBE_TIMEOUT_SECONDS)
            text = (version.stdout or version.stderr).strip()
            if version.returncode != 0 or not text:
                diagnosis.status = UNAVAILABLE
                diagnosis.reasons.append('CLI version check failed: ' + Redactor()(text[:200] or 'no output'))
                diagnosis.details['block_code'] = 'CLI_NOT_RUNNABLE'
                return diagnosis
            diagnosis.details['cli_version'] = Redactor()(text.splitlines()[-1])[:120]
            self.check_features(exe, env, diagnosis)
            if diagnosis.status == AVAILABLE:
                self.check_auth(exe, env, auth, diagnosis)
        except Exception as exc:  # 진단 실패가 다른 provider의 진단을 막지 않도록 UNAVAILABLE로 환원한다.
            diagnosis.status = UNAVAILABLE
            diagnosis.reasons.append(f'Diagnosis error: {type(exc).__name__}: {Redactor()(str(exc))[:200]}')
            diagnosis.details['block_code'] = 'DIAGNOSIS_ERROR'
        return diagnosis

    def run(self, brief: dict, entry: dict, output: Path, seed: int | None) -> ProviderRun:
        assert_not_nested()
        backend = self._backend(entry)
        auth = self._auth(entry)
        record: dict[str, Any] = {'provider_id': entry.get('id', self.engine), 'engine': self.engine, 'status': 'NOT_STARTED',
            'auth': {'mode': auth['mode'], 'secrets_recorded': False},
            'reproducibility': {'seed': 'UNSUPPORTED', 'seed_requested': seed, 'seed_applied': False, 'exact_reproduction': 'UNSUPPORTED'},
            'retry': {'attempts': 0, 'policy': 'NONE', 'fallback': 'NONE'}}
        try:
            return self._run(brief, entry, backend, auth, output, record)
        except ProviderError as exc:
            record.update({'status': exc.status, 'error_code': exc.code, 'error': Redactor()(str(exc))[:500]})
            exc.record = {**exc.record, **record}
            raise

    def _run(self, brief: dict, entry: dict, backend: dict, auth: dict, output: Path, record: dict) -> ProviderRun:
        from ..manifests import write
        from ..prompts import compile_prompt
        diagnosis = self.diagnose(entry)
        record['diagnosis'] = diagnosis.as_dict()
        diagnosis.raise_if_not_available()
        exe = diagnosis.details['executable']
        compiled = compile_prompt(brief, entry, self.config.root)
        write(Path(output) / 'compiled_prompt.json', compiled)
        reference = Path(brief['source']['paths'][0]) if brief['source']['type'] == 'REFERENCE_IMAGE' else None
        tool = backend.get('edit_tool', 'image_edit') if reference else backend.get('tool', 'image_gen')
        if reference and not backend.get('edit_tool'):
            raise ProviderFailed('REFERENCE_UNSUPPORTED', f'{self.engine} has no registered edit tool for reference images')
        spec_text = compiled['positive']
        job = JobDir(self.engine, self.settings.get('job_root'))
        redact = Redactor(self._secret_values(auth))
        try:
            reference_name = None
            if reference is not None:
                if not reference.is_file():
                    raise ProviderFailed('REFERENCE_MISSING', 'Reference image does not exist')
                reference_name = 'reference' + reference.suffix.lower()
                shutil.copy2(reference, job.inputs / reference_name)
                record['reference'] = {'sha256': sha256_file(reference), 'copied_as': 'inputs/' + reference_name}
            prompt_text = self.wrap_prompt(spec_text, tool, compiled.get('aspect_ratio'), job.inputs / reference_name if reference_name else None)
            argv, stdin_text, extra = self.build_argv(exe, job, backend, tool, job.inputs / reference_name if reference_name else None)
            env, names = self._env(auth, job)
            log_dir = Path(output) / self.engine
            log_dir.mkdir(parents=True, exist_ok=True)
            (log_dir / 'prompt.txt').write_text(prompt_text, encoding='utf-8')
            record.update({'tool': tool, 'model': {'configured': backend.get('model'), 'reported': None, 'note': 'CLI default model when not configured'},
                'cli_version': diagnosis.details.get('cli_version'), 'prompt_sha256': sha256_text(prompt_text),
                'prompt_file': str(log_dir / 'prompt.txt'), 'negative_prompt_mode': compiled.get('negative_mode'),
                'command': {'argv': [redact(a.replace(str(job.root), '<job_dir>')) for a in argv], 'prompt_via': extra.get('prompt_via', 'stdin'),
                    'cwd': '<isolated temp job dir>', 'env_passed': names, 'sandbox': extra.get('sandbox')},
                'status': 'RUNNING', 'started': now_iso()})
            if stdin_text is None and extra.get('prompt_via') == 'file':
                (job.work / extra['prompt_file']).write_text(prompt_text, encoding='utf-8')
            elif stdin_text is None:
                stdin_text = prompt_text
            roots = self.snapshot_roots(env)
            state = {'roots': roots, 'before': snapshot_images([*roots, job.work])}
            record['retry']['attempts'] = 1
            timeout = float(backend.get('timeout_seconds', 600))
            try:
                result = run_cli(argv, cwd=job.work, env=env, timeout=timeout, stdin_text=stdin_text)
            except OSError as exc:
                raise ProviderFailed('CLI_NOT_RUNNABLE', f'Cannot start {self.engine} CLI: {exc}')
            parsed = self.parse_events(result)
            record.update({'finished': result.finished, 'duration_seconds': result.duration_seconds, 'exit_code': result.returncode,
                'request': {'request_id': parsed['request_id'], 'session_id': parsed['session_id']},
                'usage': parsed['usage'], 'usage_support': 'REPORTED' if parsed['usage'] else 'NOT_REPORTED'})
            if parsed['reported_model']:
                record['model']['reported'] = str(parsed['reported_model'])
            record['logs'] = self._write_logs(log_dir, result, redact)
            last_message = self.last_message(result, job)
            (log_dir / 'last_message.txt').write_text(redact(last_message), encoding='utf-8')
            record['logs']['last_message'] = str(log_dir / 'last_message.txt')
            if result.timed_out:
                record['orphan_outputs'] = [str(p) for p in self._safe_harvest(result, parsed, job, env, state)]
                raise ProviderFailed('TIMEOUT', f'{self.engine} timed out after {timeout:g}s; no automatic retry to avoid duplicate paid requests')
            combined = result.stdout + '\n' + result.stderr
            if result.returncode != 0:
                if AUTH_FAILURE.search(combined):
                    raise ProviderBlocked('AUTH_NOT_CONFIGURED', f'{self.engine} reported an authentication problem')
                raise ProviderFailed('CLI_EXIT_NONZERO', f'{self.engine} exited with code {result.returncode}')
            candidates = self.harvest(result, parsed, job, env, state)
            if not candidates:
                message = last_message + '\n' + result.stderr
                if REFUSAL.search(message):
                    raise ProviderFailed('REFUSED', f'{self.engine} declined to generate the image')
                raise ProviderFailed('OUTPUT_MISSING', f'{self.engine} finished without producing an image file')
            if len(candidates) > int(backend.get('max_outputs', 1)):
                record['orphan_outputs'] = [str(p) for p in candidates]
                raise ProviderFailed('OUTPUT_AMBIGUOUS', f'{len(candidates)} image files appeared; refusing to guess which belongs to this request')
            rows = preserve_outputs(candidates, log_dir / 'raw', state.get('correlated_roots', []))
            record['outputs'] = rows
            record['status'] = 'COMPLETED'
            return ProviderRun([Path(r['path']) for r in rows], record)
        finally:
            job.cleanup()

    def _secret_values(self, auth: dict) -> list[str]:
        import os
        names = list(self.settings.get('pass_env', [])) + (list(auth.get('env', [])) if auth['mode'] == 'env_api_key' else [])
        return [os.environ[n] for n in names if n in os.environ]

    def _write_logs(self, log_dir: Path, result: CliResult, redact: Redactor) -> dict[str, str]:
        (log_dir / 'stdout.log').write_text(redact(result.stdout), encoding='utf-8')
        (log_dir / 'stderr.log').write_text(redact(result.stderr), encoding='utf-8')
        return {'stdout': str(log_dir / 'stdout.log'), 'stderr': str(log_dir / 'stderr.log'), 'redacted': True}

    def _safe_harvest(self, result, parsed, job, env, state) -> list[Path]:
        try:
            return self.harvest(result, parsed, job, env, state)
        except Exception:
            return []
