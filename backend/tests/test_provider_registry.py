"""기존보험 수집 방식(Provider) 노출 규칙.

배포본에 실제로 켜져 있는 것만 목록에 오르는지, 그리고 구현이 없는 방식이 환경변수만으로
켜지지 않는지를 지킨다 — 목록에 오르는 순간 화면에는 쓸 수 있는 기능처럼 보인다.
"""
import importlib

import pytest

from app import config
from app.services.external_policy.base import ExternalPolicyDTO
from app.services.external_policy.registry import (
    get_provider, list_available_providers, validate_configured_providers,
)


def test_이름으로_구현체를_고른다():
    assert get_provider("manual").name == "manual"
    assert get_provider("mock").name == "mock"


def test_등록되지_않은_이름은_거부한다():
    with pytest.raises(ValueError, match="지원하지 않는 수집 방식"):
        get_provider("없는provider")


def test_설정에_알수없는_이름이_있으면_기동을_막는다():
    """오타를 조용히 무시하면 운영자는 켰다고 믿고 넘어간다."""
    with pytest.raises(ValueError, match="알 수 없는 수집 방식"):
        validate_configured_providers(["manual", "없는provider"])


def test_배포_기본값은_직접입력_하나뿐이다(monkeypatch):
    """운영(Render)에는 EXTERNAL_POLICY_PROVIDERS를 두지 않는다 — 그때 켜지는 값이 기본값이다.

    시연용 mock이 기본값에 있으면 배포본에서 만들어 둔 예시가 실제 조회처럼 보인다.
    """
    monkeypatch.delenv("EXTERNAL_POLICY_PROVIDERS", raising=False)
    try:
        importlib.reload(config)
        assert config.EXTERNAL_POLICY_PROVIDERS == ["manual"]
    finally:
        monkeypatch.undo()
        importlib.reload(config)


def test_기본_사용가능_목록은_manual뿐이고_mock과_codef는_없다(monkeypatch):
    monkeypatch.setattr(config, "EXTERNAL_POLICY_PROVIDERS", ["manual"])
    names = [p.name for p in list_available_providers()]
    assert names == ["manual"]


def test_mock은_환경변수로_켰을_때만_목록에_나온다(monkeypatch):
    """시연·테스트 환경은 EXTERNAL_POLICY_PROVIDERS="manual,mock"으로 켠다."""
    monkeypatch.setattr(config, "EXTERNAL_POLICY_PROVIDERS", ["manual"])
    assert "mock" not in [p.name for p in list_available_providers()]

    monkeypatch.setattr(config, "EXTERNAL_POLICY_PROVIDERS", ["manual", "mock"])
    assert "mock" in [p.name for p in list_available_providers()]


def test_mock은_시연용임을_스스로_밝힌다():
    """켜졌을 때 화면이 실제 조회처럼 그릴 수 없도록, 안내 문구를 구현체가 들고 있어야 한다."""
    mock = get_provider("mock")
    assert mock.is_demo is True
    assert mock.notice and "실제" in mock.notice
    assert get_provider("manual").is_demo is False


def test_미구현_codef는_환경변수로_켜도_목록에_나오지_않는다(monkeypatch):
    """구현이 없는데 목록에 오르면 버튼은 보이고 누르면 실패하는 함정이 된다."""
    monkeypatch.setattr(config, "EXTERNAL_POLICY_PROVIDERS", ["manual", "codef"])
    assert [p.name for p in list_available_providers()] == ["manual"]


def test_미구현_codef를_설정에_넣으면_기동을_막는다():
    """목록에서 빼는 것만으로는 부족하다 — 켠 줄 알고 넘어가지 않게 기동 때 알린다."""
    with pytest.raises(ValueError, match="구현되지 않아"):
        validate_configured_providers(["manual", "codef"])


def test_codef는_아직_호출할_수_없다():
    with pytest.raises(NotImplementedError, match="CODEF 연동"):
        get_provider("codef").fetch(user=None, credentials={})


def test_mock은_CODEF_형태의_샘플을_돌려준다():
    result = get_provider("mock").fetch(user=None, credentials={})
    assert len(result) >= 2
    assert all(isinstance(p, ExternalPolicyDTO) for p in result)
    assert all(p.source == "mock" for p in result)
    # 실연동 전환 시 스키마가 그대로 쓰이도록 원본 payload를 함께 담는다
    assert all(p.raw_payload is not None for p in result)


def test_세_구현체가_모두_같은_DTO_형태를_돌려준다():
    """수집 방식이 달라도 저장·진단·화면이 구분하지 않게 하려면 반환 형태가 같아야 한다."""
    manual = get_provider("manual").fetch(
        user=None, credentials={"items": [{"kind": "ACCIDENT"}]}
    )
    mock = get_provider("mock").fetch(user=None, credentials={})
    for dto in manual + mock:
        assert isinstance(dto, ExternalPolicyDTO)
        assert isinstance(dto.coverages, list)
        assert dto.kind
