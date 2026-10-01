"""NONPIXEL 이미지 생성 provider의 공통 계약.

모든 provider(comfyui, codex_cli, grok_cli)는 같은 진단·실행 인터페이스를 따른다.
- 진단은 과금 요청 없이 수행하며, 실제 생성 가능 여부는 E2E 검증으로만 확정한다.
- 실행 실패 시 다른 provider로 암묵적으로 넘어가지 않고 오류 코드와 함께 중단한다.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# 진단 상태: AVAILABLE=즉시 시도 가능, BLOCKED=사용자 조치(로그인 등)가 필요,
# UNAVAILABLE=설치되지 않았거나 기능이 없어 사용할 수 없음.
AVAILABLE = 'AVAILABLE'
BLOCKED = 'BLOCKED'
UNAVAILABLE = 'UNAVAILABLE'
DIAGNOSIS_STATUSES = (AVAILABLE, BLOCKED, UNAVAILABLE)


class ProviderError(Exception):
    """provider 실패. code는 진단과 manifest에 기록하는 안정적인 식별자다."""

    status = 'FAILED'

    def __init__(self, code: str, message: str, *, record: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.record = record or {}


class ProviderUnavailable(ProviderError):
    status = UNAVAILABLE


class ProviderBlocked(ProviderError):
    status = BLOCKED


class ProviderFailed(ProviderError):
    status = 'FAILED'


@dataclass
class Diagnosis:
    provider_id: str
    engine: str
    status: str
    reasons: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)
    checked_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, Any]:
        return {'provider_id': self.provider_id, 'engine': self.engine, 'status': self.status,
                'reasons': list(self.reasons), 'details': dict(self.details), 'checked_at': self.checked_at}

    def raise_if_not_available(self, code_hint: str | None = None) -> None:
        """AVAILABLE이 아니면 과금 요청 전에 해당 상태의 오류로 중단한다."""
        if self.status == AVAILABLE:
            return
        code = code_hint or self.details.get('block_code') or ('PROVIDER_' + self.status)
        error = ProviderBlocked if self.status == BLOCKED else ProviderUnavailable
        raise error(code, '; '.join(self.reasons) or f'{self.provider_id} is {self.status}', record={'diagnosis': self.as_dict()})


@dataclass
class ProviderRun:
    """provider 실행 결과. outputs는 원본 보존용 복사본이며 record는 manifest에 그대로 기록한다."""
    outputs: list[Path]
    record: dict[str, Any]


class ImageProvider(abc.ABC):
    """이미지 생성 provider의 공통 인터페이스."""

    provider_id: str
    engine: str

    @abc.abstractmethod
    def diagnose(self) -> Diagnosis:
        """과금 요청 없이 설치·인증·기능 상태를 확인한다."""

    @abc.abstractmethod
    def run(self, brief: dict, entry: dict, output: Path, seed: int | None) -> ProviderRun:
        """브리프로 후보 이미지를 생성한다. 실패는 ProviderError로 알린다."""
