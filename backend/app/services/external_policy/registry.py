"""활성 Provider 관리.

프론트와 API는 list_available_providers() 결과만 보고 수집 방식을 그린다. 여기 없는 방식은
화면에도, /providers 응답에도 나오지 않는다.

목록에 오르는 조건은 두 가지다.
  1) config.EXTERNAL_POLICY_PROVIDERS(환경변수)에 이름이 들어 있을 것.
  2) 구현체가 실제로 동작할 것(implemented=True).

2)가 필요한 이유: CodefProvider처럼 fetch()가 비어 있는 자리표시자를 환경변수만으로 켤 수
있으면, 화면에는 연동 버튼이 멀쩡히 뜨는데 누르면 503이 난다. "환경변수만 켜면 된다"가
성립하려면 구현이 먼저 있어야 한다. 그래서 미구현 방식은 목록에서 빼고, 설정에 적혀 있으면
validate_configured_providers()가 기동 시점에 오류로 막는다 — 조용히 무시하면 운영자는
켠 줄 알고 넘어간다.
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


def validate_configured_providers(names: list[str] | None = None) -> None:
    """설정에 적힌 수집 방식이 실제로 쓸 수 있는 것인지 기동 시점에 확인한다.

    오타로 적은 이름이나 아직 구현되지 않은 방식은 조용히 넘어가지 않고 여기서 막는다.
    """
    for name in (config.EXTERNAL_POLICY_PROVIDERS if names is None else names):
        provider = _ALL.get(name)
        if provider is None:
            raise ValueError(
                f"EXTERNAL_POLICY_PROVIDERS에 알 수 없는 수집 방식이 있습니다: {name} "
                f"(쓸 수 있는 값: {', '.join(sorted(_ALL))})"
            )
        if not provider.implemented:
            raise ValueError(
                f"'{name}' 연동은 아직 구현되지 않아 켤 수 없습니다. "
                f"{provider.notice or ''} 구현을 마치고 implemented=True로 바꾼 뒤에 "
                "EXTERNAL_POLICY_PROVIDERS에 넣으세요."
            )


def list_available_providers() -> list[ExternalPolicyProvider]:
    """설정으로 켜 두었고 실제로 동작하는 것만 돌려준다. 순서는 설정에 적은 순서를 따른다."""
    return [
        _ALL[n] for n in config.EXTERNAL_POLICY_PROVIDERS
        if n in _ALL and _ALL[n].implemented
    ]


# 기동할 때(=이 모듈이 처음 import될 때) 한 번 검증한다. 잘못된 설정으로 서비스가 뜨는 것보다
# 뜨지 않는 편이 낫다 — 뜨고 나면 어느 방식이 왜 안 보이는지 아무도 모른다.
validate_configured_providers()
