"""생성 provider 모음. 엔진 이름으로 인스턴스를 만들고 진단은 provider별로 독립 수행한다."""
from concurrent.futures import ThreadPoolExecutor

from .base import (AVAILABLE, BLOCKED, UNAVAILABLE, Diagnosis, ImageProvider, ProviderBlocked, ProviderError,
                   ProviderFailed, ProviderRun, ProviderUnavailable)

ENGINES = ('comfyui', 'codex_cli', 'grok_cli')
CLI_ENGINES = ('codex_cli', 'grok_cli')


def create_provider(engine, config):
    if engine == 'comfyui':
        from .comfyui import ComfyUIProvider
        return ComfyUIProvider(config)
    if engine == 'codex_cli':
        from .codex_cli import CodexCliProvider
        return CodexCliProvider(config)
    if engine == 'grok_cli':
        from .grok_cli import GrokCliProvider
        return GrokCliProvider(config)
    raise ValueError(f'Unknown provider engine: {engine}')


def diagnose_providers(config, engines=ENGINES):
    """엔진별 진단을 서로 독립적으로(병렬로) 수행한다. 한 엔진의 실패가 다른 엔진 결과에 영향을 주지 않는다."""
    def one(engine):
        try:
            return create_provider(engine, config).diagnose().as_dict()
        except Exception as exc:
            return Diagnosis(engine, engine, UNAVAILABLE, [f'Diagnosis error: {type(exc).__name__}: {exc}'], {'block_code': 'DIAGNOSIS_ERROR'}).as_dict()
    with ThreadPoolExecutor(max_workers=len(engines)) as pool:
        return dict(zip(engines, pool.map(one, engines)))
