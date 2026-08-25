"""여행경보를 약관 면책 조항에 잇는 규칙.

지키려는 경계가 둘이다.

1. 경보 단계 자체는 보상 여부의 근거가 아니다. 외교부 자료와 보험 약관은 출처가 다르므로,
   경보가 높다고 "보상되지 않는다"고 단정하지 않고 "이 보험사 약관에 전쟁·내란 면책 조항이
   있다"는 사실을 원문과 함께 알리는 데까지만 쓴다.
2. 경보 범위를 넓혀 말하지 않는다. 외교부 경보는 지역 단위라, 일부 지역 경보를 국가 전체
   경보처럼 표시하면 도쿄 여행자에게 출국권고가 뜬다.

region_type·note는 실제 외교부 응답의 표기('전체'/'일부')를 그대로 쓴다.
"""
import datetime as dt

import pytest

from app.models.kb import (
    Clause, ClauseIncidentMap, Coverage, CoverageStd, IncidentType,
    Insurer, PolicyVersion, Product, TravelAlert,
)
from app.services.travel_alert import (
    BASIS_LOCAL, BASIS_REMAINDER, BASIS_WHOLE, build_alert_findings, country_alert,
)

WAR_CLAUSE = (
    "회사는 다음의 사유로 생긴 손해는 보상하여 드리지 않습니다. "
    "전쟁, 외국의 무력행사, 혁명, 내란, 사변, 폭동으로 생긴 손해"
)


def _alert(country, level, region_type="일부", note=None):
    return TravelAlert(country_name=country, level=level, region_type=region_type, note=note,
                       source="외교부", source_url="https://www.0404.go.kr/",
                       collected_at=dt.date(2026, 8, 11))


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
        # 우크라이나형 — '전체' 행 하나. 나라 전체가 4단계.
        _alert("우크라이나", 4, region_type="전체", note="전 지역"),
        # 시리아형 — 전체 행은 없지만 "…를 제외한 전 지역"이 있어 사실상 전국.
        # 3단계 행의 괄호 속 '제외'는 특정 지역을 좁히는 단서지 나머지 전역이 아니다.
        _alert("시리아", 4, note="3단계를 제외한 전 지역"),
        _alert("시리아", 3, note="골란고원 일부(레바논 접경 및 UNDOF 분리선 4km 이내 지역 제외)"),
        # 필리핀형 — 나머지 전역 문구가 2단계에 붙어 있다.
        _alert("필리핀", 4, note="민다나오의 잠보앙가, 술루 군도"),
        _alert("필리핀", 3, note="팔라완섬 이남, 민다나오섬 일부(2단계 및 4단계 지역 제외)"),
        _alert("필리핀", 2, note="1, 3, 4단계 지역을 제외한 지역"),
        # 러시아형 — 두 행 다 특정 지역이다. 모스크바에는 경보가 없으므로 기본단계도 없다.
        _alert("러시아", 4, note="우크라이나 접경지역(쿠르스크주 전체 및 국경 30km 구간)"),
        _alert("러시아", 3, note="북카프카즈 지역(체첸/다게스탄) 및 우크라이나 접경지역(4단계 제외 로스토프)"),
        # 니제르형 — '제외한'이 아니라 '제외 전 지역'으로 온다.
        _alert("니제르", 4, note="수도 니아메 제외 전 지역"),
        # 일본형 — 국지적 경보 하나뿐. 그 나라 일반 지역의 단계라 할 것이 없다.
        _alert("일본", 3, note="후쿠시마 원전 반경 30km 이내 및 일본 정부 지정 피난지시구역"),
        # 베트남형 — 전체 1단계.
        _alert("베트남", 1, region_type="전체", note="전 지역"),
    ])
    db.commit()
    return db


# ── baseline 판정 ────────────────────────────────────────────────────────────

def test_전체_행이_있으면_그게_기본단계다(kb):
    alert = country_alert(kb, "우크라이나")
    assert alert.baseline.level == 4
    assert alert.baseline_basis == BASIS_WHOLE
    assert alert.regions == []


def test_제외한_지역_행이_나머지_전역의_기본단계다(kb):
    alert = country_alert(kb, "시리아")
    assert alert.baseline.level == 4
    assert alert.baseline_basis == BASIS_REMAINDER
    assert [r.level for r in alert.regions] == [3]


def test_괄호_속_제외는_나머지_전역이_아니다(kb):
    """"골란고원 일부(…지역 제외)"는 특정 지역을 좁히는 단서다. 이걸 나머지 전역으로
    읽으면 시리아 기본단계가 4가 아니라 3이 된다."""
    alert = country_alert(kb, "시리아")
    괄호행 = next(r for r in alert.regions if r.level == 3)
    assert "제외" in 괄호행.note
    assert alert.baseline.level == 4, "괄호 속 '제외'에 끌려가면 안 됩니다"


def test_두_행_다_특정_지역이면_기본단계가_없다(kb):
    """러시아 경보는 우크라이나 접경과 북카프카즈다. 모스크바에는 경보가 없다.
    '제외'라는 글자만 보고 판단하면 모스크바 여행자에게 자동으로 면책 조항이 붙는다."""
    alert = country_alert(kb, "러시아")
    assert alert.baseline is None
    assert alert.baseline_basis == BASIS_LOCAL
    assert build_alert_findings(kb, "러시아") == []


def test_제외_전_지역_표기도_나머지_전역으로_읽는다(kb):
    """'제외한'이 아니라 '제외 전 지역'으로 오는 나라가 있다(니제르)."""
    alert = country_alert(kb, "니제르")
    assert alert.baseline.level == 4
    assert alert.baseline_basis == BASIS_REMAINDER
    assert len(build_alert_findings(kb, "니제르")) == 2


def test_나머지행이_여러_단계면_최저를_기본단계로_쓴다(kb):
    """필리핀의 나머지 전역은 2단계다. 최고인 4단계를 쓰면 세부 여행자에게 여행금지가 뜬다."""
    alert = country_alert(kb, "필리핀")
    assert alert.baseline.level == 2
    assert alert.baseline_basis == BASIS_REMAINDER
    assert sorted(r.level for r in alert.regions) == [3, 4]


def test_국지적_경보만_있으면_기본단계가_없다(kb):
    alert = country_alert(kb, "일본")
    assert alert.baseline is None
    assert alert.baseline_basis == BASIS_LOCAL
    assert [r.level for r in alert.regions] == [3]


# ── 면책 조항 연결 ───────────────────────────────────────────────────────────

def test_기본단계가_높으면_보험사별_면책조항을_근거로_알린다(kb):
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


def test_일부_지역_경보는_체크하지_않으면_면책을_꺼내지_않는다(kb):
    """일본의 3단계는 후쿠시마 원전 30km다. 도쿄 여행자에게 출국권고를 띄우면
    사용자는 경보를 무시하게 되고, 정말 위험한 시리아에서도 똑같이 무시한다."""
    assert build_alert_findings(kb, "일본") == []
    assert build_alert_findings(kb, "필리핀") == []


def test_그_지역에_간다고_체크하면_면책조항을_보여준다(kb):
    region = country_alert(kb, "일본").regions[0]

    findings = build_alert_findings(kb, "일본", [region.alert_id])

    assert len(findings) == 2
    for f in findings:
        assert f["evidence"]
        # 어느 지역 때문에 붙은 안내인지 문장에 드러나야 한다.
        assert "후쿠시마" in f["description"]
        assert "여행 경로에 포함" in f["description"]


def test_다른_나라의_지역id는_인정하지_않는다(kb):
    """남의 나라 alert_id를 넣어 면책 카드를 억지로 띄우는 것을 막는다."""
    시리아_지역 = country_alert(kb, "시리아").regions[0]

    assert build_alert_findings(kb, "일본", [시리아_지역.alert_id]) == []


def test_낮은_단계_지역은_체크해도_면책을_꺼내지_않는다(kb):
    """필리핀의 2단계 baseline 행을 지목해도 3단계 미만이라 대상이 아니다."""
    alert = country_alert(kb, "필리핀")
    낮은_단계_id = [r.alert_id for r in alert.regions if r.level < 3]

    assert build_alert_findings(kb, "필리핀", 낮은_단계_id) == []


def test_전체가_낮은_단계면_아무것도_만들지_않는다(kb):
    assert build_alert_findings(kb, "베트남") == []


# ── 없는 자료 ────────────────────────────────────────────────────────────────

def test_자료에_없는_나라는_추측하지_않는다(kb):
    assert country_alert(kb, "안도라") is None
    assert build_alert_findings(kb, "안도라") == []


def test_경보_자료가_아예_없어도_동작한다(db_session):
    """스냅샷을 아직 채우지 않은 상태(인증키 없음). 기능만 비활성이고 앱은 정상이어야 한다."""
    assert country_alert(db_session, "시리아") is None
    assert build_alert_findings(db_session, "시리아") == []


def test_목적지가_비어도_터지지_않는다(kb):
    assert country_alert(kb, None) is None
    assert country_alert(kb, "   ") is None
    assert build_alert_findings(kb, "") == []
