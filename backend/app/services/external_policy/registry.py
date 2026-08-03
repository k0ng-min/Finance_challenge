"""활성 Provider 관리.

프론트는 list_available_providers() 결과로 버튼을 그린다 — 그래서 CODEF가 꺼져 있으면
버튼 자체가 안 보이고, 환경변수만 켜면 나타난다. 프론트 코드를 고칠 필요가 없다.
"""
from __future__ import annotations

from app import config
from app.services.external_policy.base import ExternalPolicyProvider
from app.services.external_policy.codef import CodefProvider
from app.services.external_policy.manual import ManualProvider
from app.services.external_policy.mock import MockProvider

_ALL: dict[str, ExternalPolicyProvider] = {
    p.name: p for p in (ManualProvider(), MockProvider(), CodefProvider())
}


def get_provider(name: str) -> ExternalPolicyProvider:
    provider = _ALL.get(name)
    if provider is None:
        raise ValueError(f"지원하지 않는 수집 방식: {name}")
    return provider


def list_available_providers() -> list[ExternalPolicyProvider]:
    """설정으로 켜 둔 것만 돌려준다. 순서는 설정에 적은 순서를 따른다."""
    return [_ALL[n] for n in config.EXTERNAL_POLICY_PROVIDERS if n in _ALL]
