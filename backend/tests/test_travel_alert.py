"""여행경보를 약관 면책 조항에 잇는 규칙.

지키려는 경계: 경보 단계 자체는 보상 여부의 근거가 아니다. 외교부 자료와 보험 약관은
출처가 다르므로, 경보가 높다고 "보상되지 않는다"고 단정하지 않고 "이 보험사 약관에
전쟁·내란 면책 조항이 있다"는 사실을 원문과 함께 알리는 데까지만 쓴다.
"""
import datetime as dt

import pytest

from app.models.kb import (
    Clause, ClauseIncidentMap, Coverage, CoverageStd, IncidentType,
    Insurer, PolicyVersion, Product, TravelAlert,
)
from app.services.travel_alert import build_alert_findings, find_alert

WAR_CLAUSE = (
    "회사는 다음의 사유로 생긴 손해는 보상하여 드리지 않습니다. "
    "전쟁, 외국의 무력행사, 혁명, 내란, 사변, 폭동으로 생긴 손해"
)


@pytest.fixture
def kb(db_session):
    db = db_session

    war = IncidentType(l1_code="SPC", l2_code="SPC_WAR_TERROR", name="전쟁·테러(면책)")
    db.add(war)
    db.flush()

    std = CoverageStd(std_code="DEATH_INJURY", std_name="상해사망·후유장해")
    db.add(std)
    db.flush()

    for code, name in [("A", "가나화재"), ("B", "다라해상")]:
        insurer = Insurer(name=name, code=code)
        db.add(insurer)
        db.flush()
        product = Product(insurer_id=insurer.insurer_id, name=f"{name} 여행보험")
        db.add(product)
        db.flush()
        version = PolicyVersion(product_id=product.product_id, version_label="테스트판")
        db.add(version)
        db.flush()
        cov = Coverage(policy_version_id=version.policy_version_id,
                       coverage_std_id=std.coverage_std_id, raw_name="상해사망 보통약관")
        db.add(cov)
        db.flush()
        clause = Clause(policy_version_id=version.policy_version_id, coverage_id=cov.coverage_id,
                        clause_type="면책", article_no="제5조", text=WAR_CLAUSE, default_color="빨강")
        db.add(clause)
        db.flush()
        db.add(ClauseIncidentMap(clause_id=clause.clause_id, type_id=war.type_id,
                                 relevance="면책", mapped_by="human", confidence=1.0))

    db.add_all([
        TravelAlert(country_name="시리아", level=4, region_type="전 지역",
                    issued_on="2026-01-15", source="외교부", source_url="https://www.0404.go.kr/",
                    collected_at=dt.date(2026, 8, 9)),
        TravelAlert(country_name="이집트", level=3, region_type="일부 지역",
                    collected_at=dt.date(2026, 8, 9)),
        TravelAlert(country_name="필리핀", level=2, collected_at=dt.date(2026, 8, 9)),
        TravelAlert(country_name="일본", level=1, collected_at=dt.date(2026, 8, 9)),
    ])
    db.commit()
    return db


def test_경보가_높으면_보험사별_면책조항을_근거로_알린다(kb):
    findings = build_alert_findings(kb, "시리아")

    assert len(findings) == 2, "약관을 가진 보험사마다 한 건씩 나와야 합니다"
    for f in findings:
        assert f["finding_type"] == "제한조건"
        assert f["evidence"], "면책 안내에는 근거 조항이 반드시 있어야 합니다"
        clause, _color = f["evidence"][0]
        assert "전쟁" in clause.text


def test_경보_단계를_보상_판정으로_말하지_않는다(kb):
    """외교부 자료를 근거로 보상 여부를 단정하면 출처가 다른 두 자료를 섞는 것이 된다."""
    findings = build_alert_findings(kb, "시리아")

    for f in findings:
        text = f["description"]
        assert "보상되지 않습니다" not in text
        assert "지급되지 않습니다" not in text
        # 약관에 그런 조항이 '있다'는 사실과, 직접 확인하라는 안내까지만 한다.
        assert "확인" in text


def test_출국권고도_면책조항을_보여준다(kb):
    assert build_alert_findings(kb, "이집트")


@pytest.mark.parametrize("country", ["필리핀", "일본"])
def test_낮은_단계에서는_제한조건을_만들지_않는다(kb, country):
    """여행유의·자제는 대부분의 나라에 붙어 있어, 그때마다 면책을 꺼내면 경고가 무의미해진다."""
    assert build_alert_findings(kb, country) == []


def test_자료에_없는_나라는_추측하지_않는다(kb):
    assert find_alert(kb, "안도라") is None
    assert build_alert_findings(kb, "안도라") == []


def test_경보_자료가_아예_없어도_동작한다(db_session):
    """스냅샷을 아직 채우지 않은 상태(인증키 없음). 기능만 비활성이고 앱은 정상이어야 한다."""
    assert find_alert(db_session, "시리아") is None
    assert build_alert_findings(db_session, "시리아") == []


def test_목적지가_비어도_터지지_않는다(kb):
    assert find_alert(kb, None) is None
    assert build_alert_findings(kb, "") == []
