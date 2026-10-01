"""외부 생성 CLI를 격리된 job directory에서 실행하는 공통 러너.

- 프로젝트 문서·소스 경로·환경변수·시크릿을 자식 프로세스에 넘기지 않는다.
- 프롬프트는 argv가 아니라 stdin/파일로 전달한다(길이 제한·셸 인용 문제 방지).
- 자식이 다시 assetpipe를 호출하는 재귀 실행은 환경변수 가드로 차단한다.
- 로그에는 비밀로 보이는 값을 마스킹한 사본만 저장한다.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

from .base import ProviderBlocked

# 자식 CLI 안에서 assetpipe 계열 도구가 다시 시작되는 것을 막는 표식.
DEPTH_ENV = 'ASSETPIPE_PROVIDER_DEPTH'

# 자식 프로세스에 전달하는 환경변수 허용목록. 인증 저장소 위치(HOME 등)와 실행에 필요한 최소 항목만 둔다.
# 프록시·API 키처럼 시크릿이 될 수 있는 값은 registry/설정에서 이름을 명시한 경우에만 전달한다.
SAFE_ENV_NAMES = (
    'PATH', 'PATHEXT', 'HOME', 'USERPROFILE', 'HOMEDRIVE', 'HOMEPATH', 'APPDATA', 'LOCALAPPDATA',
    'SYSTEMROOT', 'SYSTEMDRIVE', 'COMSPEC', 'WINDIR', 'TEMP', 'TMP', 'TMPDIR', 'LANG', 'LC_ALL',
    'XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_CACHE_HOME', 'XDG_STATE_HOME',
)
ENV_NAME = re.compile(r'^[A-Za-z_][A-Za-z0-9_]{0,63}$')
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp'}
MAX_IMAGE_BYTES = 64 * 1024 * 1024
MAX_LOG_CHARS = 1_000_000

_SECRET_PATTERNS = [
    re.compile(r'\bsk-[A-Za-z0-9_\-]{8,}'),
    re.compile(r'\bxai-[A-Za-z0-9_\-]{8,}'),
    re.compile(r'\beyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{4,}'),
    re.compile(r'(?i)\bBearer\s+[A-Za-z0-9._~+/\-]{8,}=*'),
    re.compile(r'(?i)(["\']?(?:api[_-]?key|access[_-]?token|refresh[_-]?token|token|secret|password|authorization)["\']?\s*[:=]\s*["\']?)[^\s"\',}]{4,}'),
    re.compile(r'(?i)(https?://[^/\s:@]+:)[^@\s/]+(@)'),
]


def assert_not_nested() -> None:
    """생성 CLI 내부에서 다시 assetpipe 생성이 시작되면 즉시 거부한다."""
    if os.environ.get(DEPTH_ENV):
        raise ProviderBlocked('RECURSION_BLOCKED', 'Nested assetpipe execution inside a provider CLI job is blocked')


class Redactor:
    """로그·기록에 남기기 전에 비밀로 보이는 값을 가린다."""

    def __init__(self, secret_values: Iterable[str] = ()):
        self.values = sorted({v for v in secret_values if isinstance(v, str) and len(v) >= 6}, key=len, reverse=True)

    def __call__(self, text: str) -> str:
        for value in self.values:
            text = text.replace(value, '[REDACTED]')
        for pattern in _SECRET_PATTERNS:
            if pattern.groups:
                text = pattern.sub(lambda m: m.group(1) + '[REDACTED]' + (m.group(2) if m.lastindex and m.lastindex >= 2 else ''), text)
            else:
                text = pattern.sub('[REDACTED]', text)
        return text


def build_env(pass_env: Iterable[str] = (), extra: dict[str, str] | None = None) -> tuple[dict[str, str], list[str]]:
    """허용목록 기반 환경을 만든다. 반환값의 두 번째 항목은 전달한 변수 이름(값 제외)이다."""
    env: dict[str, str] = {}
    for name in SAFE_ENV_NAMES:
        if name in os.environ:
            env[name] = os.environ[name]
    explicit = []
    for name in pass_env:
        if not isinstance(name, str) or not ENV_NAME.fullmatch(name):
            raise ValueError(f'Invalid environment variable name: {name!r}')
        if name in os.environ:
            env[name] = os.environ[name]
            explicit.append(name)
    for name in ('CODEX_HOME', 'GROK_HOME'):
        # 인증 저장소 위치일 뿐 비밀이 아니므로, 사용자가 지정했다면 그대로 따른다.
        if name in os.environ:
            env[name] = os.environ[name]
    env.update(extra or {})
    env[DEPTH_ENV] = '1'
    env['NO_COLOR'] = '1'
    return env, sorted(set(explicit) | {DEPTH_ENV})


def resolve_executable(configured: str | None, default_name: str) -> str | None:
    """설정된 경로를 우선하고, 없으면 PATH에서 찾는다. 찾지 못하면 None."""
    if configured:
        path = Path(configured).expanduser()
        return str(path) if path.is_file() else None
    return shutil.which(default_name)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class CliResult:
    argv: list[str]
    returncode: int | None
    timed_out: bool
    stdout: str
    stderr: str
    started: str
    finished: str
    duration_seconds: float


def _kill_tree(process: subprocess.Popen) -> None:
    try:
        if os.name == 'nt':
            subprocess.run(['taskkill', '/F', '/T', '/PID', str(process.pid)], capture_output=True, timeout=15)
        else:
            os.killpg(process.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError, subprocess.SubprocessError):
        process.kill()


def run_cli(argv: list[str], *, cwd: Path, env: dict[str, str], timeout: float, stdin_text: str | None = None) -> CliResult:
    """셸 없이 한 번만 실행한다. 타임아웃 시 프로세스 트리를 종료하며 재시도하지 않는다."""
    started, clock = now_iso(), time.monotonic()
    kwargs: dict[str, Any] = {'cwd': str(cwd), 'env': env, 'stdin': subprocess.PIPE if stdin_text is not None else subprocess.DEVNULL,
        'stdout': subprocess.PIPE, 'stderr': subprocess.PIPE, 'shell': False}
    if os.name == 'nt':
        kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP | getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    else:
        kwargs['start_new_session'] = True
    process = subprocess.Popen(argv, **kwargs)
    timed_out = False
    try:
        out, err = process.communicate(input=stdin_text.encode('utf-8') if stdin_text is not None else None, timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        _kill_tree(process)
        try:
            out, err = process.communicate(timeout=15)
        except subprocess.TimeoutExpired:
            out, err = b'', b''
    return CliResult(argv=list(argv), returncode=None if timed_out else process.returncode, timed_out=timed_out,
        stdout=out.decode('utf-8', 'replace')[-MAX_LOG_CHARS:], stderr=err.decode('utf-8', 'replace')[-MAX_LOG_CHARS:],
        started=started, finished=now_iso(), duration_seconds=round(time.monotonic() - clock, 3))


def probe(argv: list[str], *, env: dict[str, str], timeout: float, cwd: Path | None = None) -> CliResult:
    """진단용 짧은 명령 실행. 실행 실패(파일 없음 등)는 returncode=None 결과로 돌려준다."""
    try:
        return run_cli(argv, cwd=cwd or Path(tempfile.gettempdir()), env=env, timeout=timeout)
    except OSError as exc:
        now = now_iso()
        return CliResult(argv, None, False, '', str(exc), now, now, 0.0)


class JobDir:
    """프로젝트 트리 밖에 만드는 일회용 작업 폴더. 모델이 보는 파일은 이 안에 복사한 것뿐이다."""

    def __init__(self, provider_id: str, base: str | Path | None = None):
        if base:
            Path(base).mkdir(parents=True, exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix=f'assetpipe_{provider_id}_', dir=str(base) if base else None)).resolve()
        self.work = self.root / 'work'
        self.inputs = self.work / 'inputs'
        self.inputs.mkdir(parents=True)

    def cleanup(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)


def iter_json_values(text: str) -> Iterator[Any]:
    """JSONL 또는 단일 JSON 출력에서 파싱 가능한 값을 모두 꺼낸다. 파싱 불가한 줄은 건너뛴다."""
    text = text.strip()
    if not text:
        return
    try:
        yield json.loads(text)
        return
    except ValueError:
        pass
    for line in text.splitlines():
        line = line.strip()
        if line.startswith(('{', '[')):
            try:
                yield json.loads(line)
            except ValueError:
                continue


def walk(value: Any) -> Iterator[tuple[str | None, Any]]:
    """중첩 JSON을 (키, 값) 쌍으로 훑는다."""
    if isinstance(value, dict):
        for key, item in value.items():
            yield key, item
            yield from walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk(item)


def find_first(values: Iterable[Any], names: Iterable[str], kinds: tuple[type, ...] = (str,)) -> Any:
    wanted = set(names)
    for value in values:
        for key, item in walk(value):
            if key in wanted and isinstance(item, kinds) and item not in ('', None):
                return item
    return None


_PATH_IN_TEXT = re.compile(r'(?:[A-Za-z]:[\\/]|/)[^\s"\'<>|*?\x00]+?\.(?:png|jpe?g|webp)\b', re.IGNORECASE)


def image_paths_in(values: Iterable[Any], raw_text: str = '') -> list[Path]:
    """출력(JSON 문자열 값과 원문)에서 이미지 파일 절대경로 후보를 모은다."""
    found: dict[str, None] = {}
    for value in values:
        for _key, item in walk(value):
            if isinstance(item, str):
                for match in _PATH_IN_TEXT.findall(item):
                    found[match] = None
    for match in _PATH_IN_TEXT.findall(raw_text):
        found[match] = None
    return [Path(p) for p in found]


def is_within(path: Path, roots: Iterable[Path]) -> bool:
    try:
        resolved = path.resolve()
    except OSError:
        return False
    return any(resolved.is_relative_to(Path(root).resolve()) for root in roots)


def usable_image(path: Path) -> bool:
    try:
        return path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS and 0 < path.stat().st_size <= MAX_IMAGE_BYTES
    except OSError:
        return False


def snapshot_images(roots: Iterable[Path]) -> dict[str, int]:
    """실행 전 이미지 파일 상태(경로 → 수정 시각)를 기록한다. 이후 새로 생기거나 바뀐 파일만 이번 요청의 결과로 본다."""
    state: dict[str, int] = {}
    for root in roots:
        if Path(root).is_dir():
            for path in Path(root).rglob('*'):
                if path.suffix.lower() in IMAGE_EXTENSIONS:
                    try:
                        state[str(path)] = path.stat().st_mtime_ns
                    except OSError:
                        continue
    return state


def is_new(path: Path, before: dict[str, int]) -> bool:
    try:
        return before.get(str(path)) != path.stat().st_mtime_ns
    except OSError:
        return False


def new_images(roots: Iterable[Path], before: dict[str, int]) -> list[Path]:
    """roots 아래에서 실행 전 스냅샷에 없었거나 내용이 갱신된 이미지를 오래된 순으로 돌려준다."""
    rows = []
    for root in roots:
        if Path(root).is_dir():
            for path in Path(root).rglob('*'):
                if path.suffix.lower() in IMAGE_EXTENSIONS and usable_image(path) and is_new(path, before):
                    rows.append((path.stat().st_mtime_ns, path))
    return [path for _m, path in sorted(rows)]


def preserve_outputs(sources: list[Path], destination: Path) -> list[dict[str, Any]]:
    """원본 이미지를 이름·내용 그대로 복사해 보존하고 해시를 계산한다. 원본 위치는 건드리지 않는다."""
    destination.mkdir(parents=True, exist_ok=True)
    rows = []
    for index, source in enumerate(sources, 1):
        target = destination / f'{index:02d}_{source.name}'
        shutil.copy2(source, target)
        rows.append({'path': str(target), 'sha256': sha256_file(target), 'bytes': target.stat().st_size, 'source_path': str(source)})
    return rows
