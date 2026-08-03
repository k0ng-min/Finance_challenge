import pytest

from app.services.external_policy.manual import ManualProvider


def test_게스트도_쓸_수_있다():
    """수동입력은 외부 인증이 필요 없으므로 로그인 없이 허용한다."""
    assert ManualProvider().requires_login is False


def test_실손은_가입시기로_세대를_채운다():
    result = ManualProvider().fetch(user=None, credentials={
        "items": [{"kind": "MEDICAL_INDEMNITY", "insurer_name_raw": "삼성화재", "enrolled_ym": "2019-05"}]
    })
    assert len(result) == 1
    assert result[0].kind == "MEDICAL_INDEMNITY"
    assert result[0].indemnity_gen == 3
    assert result[0].source == "manual"


def test_가입시기를_모르면_세대를_비워둔다():
    result = ManualProvider().fetch(user=None, credentials={
        "items": [{"kind": "MEDICAL_INDEMNITY", "enrolled_ym": None}]
    })
    assert result[0].indemnity_gen is None
    assert result[0].coverages == []


def test_실손_외_종류는_금액을_모르는_상태로_담는다():
    """상해·일상생활배상책임·운전자보험은 표준약관이 없어 회사·상품마다 담보가 다르다.
    종류만 저장하고 금액은 unknown으로 둔다 — 중복 판정 자체는 종류만으로 가능하다."""
    result = ManualProvider().fetch(user=None, credentials={
        "items": [{"kind": "DAILY_LIABILITY", "insurer_name_raw": "현대해상"}]
    })
    assert result[0].indemnity_gen is None
    assert result[0].coverages == []


def test_알수없는_종류는_거부한다():
    with pytest.raises(ValueError, match="알 수 없는 보험 종류"):
        ManualProvider().fetch(user=None, credentials={"items": [{"kind": "NOT_A_KIND"}]})
