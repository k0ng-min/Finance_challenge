import pytest

from app.services.external_policy.base import ExternalPolicyDTO
from app.services.external_policy.registry import get_provider, list_available_providers


def test_이름으로_구현체를_고른다():
    assert get_provider("manual").name == "manual"
    assert get_provider("mock").name == "mock"


def test_등록되지_않은_이름은_거부한다():
    with pytest.raises(ValueError, match="지원하지 않는 수집 방식"):
        get_provider("없는provider")


def test_기본_사용가능_목록에_codef는_없다():
    """CODEF는 주민등록번호 처리 요건을 갖추기 전까지 꺼둔다."""
    names = [p.name for p in list_available_providers()]
    assert "manual" in names
    assert "mock" in names
    assert "codef" not in names


def test_mock은_CODEF_형태의_샘플을_돌려준다():
    result = get_provider("mock").fetch(user=None, credentials={})
    assert len(result) >= 2
    assert all(isinstance(p, ExternalPolicyDTO) for p in result)
    assert all(p.source == "mock" for p in result)
    # 실연동 전환 시 스키마가 그대로 쓰이도록 원본 payload를 함께 담는다
    assert all(p.raw_payload is not None for p in result)


def test_codef는_아직_호출할_수_없다():
    with pytest.raises(NotImplementedError, match="CODEF 연동"):
        get_provider("codef").fetch(user=None, credentials={})


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
