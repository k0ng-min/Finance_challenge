"""가입 전 추천 엔진이 사고 후와 같은 판단축(IncidentType ↔ Clause)을 쓰는지 검증한다.

핵심 원칙(사고 후 claim_review.py와 동일):
  - 담보는 ClauseIncidentMap에 실제로 매핑된 것만 후보로 올린다.
  - 활동(modifier) 기반 면책 경고는 그 보험사 조항 원문에 활동명이 실제로 있을 때만 낸다.
  - 근거가 없으면 추천도 단정적 경고도 하지 않고 '확인불가'로만 남긴다.
"""
import datetime as dt

import pytest

from app.models.kb import (
    Clause, ClauseIncidentMap, Coverage, CoverageStd, IncidentType,
    Insurer, PolicyVersion, Product,
)
from app.services.rules import build_risk_profile, generate_pre_trip_findings

# 실제 약관 문구를 본뜬 테스트용 원문. '스쿠버다이빙'이 문자 그대로 들어있는 쪽과 없는 쪽을 나눈다.
WAIVER_TEXT_WITH_SCUBA = (
    "회사는 아래의 사유로 생긴 손해는 보상하여 드리지 않습니다. "
    "피보험자가 직업, 직무 또는 동호회 활동목적으로 스쿠버다이빙, 스카이다이빙을 하는 동안 생긴 손해"
)
WAIVER_TEXT_WITHOUT_SCUBA = (
    "회사는 아래의 사유로 생긴 손해는 보상하여 드리지 않습니다. "
    "피보험자의 고의로 생긴 손해"
)


def _make_insurer(db, code, name):
    insurer = Insurer(name=name, code=code)
    db.add(insurer)
    db.flush()
    product = Product(insurer_id=insurer.insurer_id, name=f"{name} 해외여행보험")
    db.add(product)
    db.flush()
    version = PolicyVersion(
        product_id=product.product_id, version_label="테스트판",
        effective_date=dt.date(2026, 1, 1),
    )
    db.add(version)
    db.flush()
    return insurer, version


def _make_incident_type(db, l1_code, l2_code, name, parent=None):
    row = IncidentType(
        l1_code=l1_code, l2_code=l2_code, name=name,
        parent_id=parent.type_id if parent else None,
    )
    db.add(row)
    db.flush()
    return row


def _make_coverage(db, version, std, raw_name, limit_amount="1억원"):
    cov = Coverage(
        policy_version_id=version.policy_version_id,
        coverage_std_id=std.coverage_std_id,
        raw_name=raw_name,
        limit_amount=limit_amount,
    )
    db.add(cov)
    db.flush()
    return cov


def _make_clause(db, version, cov, clause_type, text, color, article_no="제5조"):
    clause = Clause(
        policy_version_id=version.policy_version_id,
        coverage_id=cov.coverage_id,
        clause_type=clause_type,
        article_no=article_no,
        text=text,
        default_color=color,
    )
    db.add(clause)
    db.flush()
    return clause


def _map(db, clause, itype, relevance):
    db.add(ClauseIncidentMap(
        clause_id=clause.clause_id, type_id=itype.type_id,
        relevance=relevance, mapped_by="human", confidence=1.0,
    ))
    db.flush()


@pytest.fixture
def kb(db_session):
    """보험사 2곳 × (INJ 상해 / PROP 휴대품) 담보를 심는다.

    A사: 상해 담보에 '스쿠버다이빙' 면책 원문이 실제로 있음
    B사: 같은 상해 담보가 있지만 면책 원문에 '스쿠버다이빙'이 없음
    LIA(배상책임) L1은 만들되 조항 매핑을 하나도 하지 않는다(=근거 없는 유형).
    """
    db = db_session

    inj = _make_incident_type(db, "INJ", "INJ", "상해")
    inj_death = _make_incident_type(db, "INJ", "INJ_DEATH", "상해사망·후유장해", parent=inj)
    prop = _make_incident_type(db, "PROP", "PROP", "휴대품·재물")
    prop_theft = _make_incident_type(db, "PROP", "PROP_THEFT", "도난", parent=prop)
    _make_incident_type(db, "LIA", "LIA", "배상책임")  # 매핑 없음

    std_death = CoverageStd(std_code="DEATH_INJURY", std_name="상해사망·후유장해", is_base=True)
    std_prop = CoverageStd(std_code="PERSONAL_EFFECTS", std_name="휴대품손해")
    db.add_all([std_death, std_prop])
    db.flush()

    insurer_a, version_a = _make_insurer(db, "A", "가나화재")
    insurer_b, version_b = _make_insurer(db, "B", "다라해상")

    # A사 상해 담보: 보장정의(직접) + 면책(스쿠버다이빙 원문 있음)
    cov_a = _make_coverage(db, version_a, std_death, "상해사망후유장해 보통약관")
    clause_a_def = _make_clause(db, version_a, cov_a, "보장정의", "여행 중 상해로 사망한 경우 보험가입금액을 지급합니다.", "파랑", "제3조")
    clause_a_waiver = _make_clause(db, version_a, cov_a, "면책", WAIVER_TEXT_WITH_SCUBA, "빨강")
    _map(db, clause_a_def, inj_death, "직접")
    _map(db, clause_a_waiver, inj_death, "면책")

    # B사 상해 담보: 보장정의(직접) + 면책(스쿠버다이빙 원문 없음)
    cov_b = _make_coverage(db, version_b, std_death, "상해사망 특별약관")
    clause_b_def = _make_clause(db, version_b, cov_b, "보장정의", "여행 중 급격한 외래의 사고로 사망 시 보험금을 지급합니다.", "파랑", "제3조")
    clause_b_waiver = _make_clause(db, version_b, cov_b, "면책", WAIVER_TEXT_WITHOUT_SCUBA, "빨강")
    _map(db, clause_b_def, inj_death, "직접")
    _map(db, clause_b_waiver, inj_death, "면책")

    # A사 휴대품 담보: 도난 직접 보장
    cov_a_prop = _make_coverage(db, version_a, std_prop, "휴대품손해 특별약관", limit_amount="20만원")
    clause_a_prop = _make_clause(db, version_a, cov_a_prop, "보장정의", "여행 중 휴대품이 도난당한 경우 손해액을 보상합니다.", "파랑", "제2조")
    _map(db, clause_a_prop, prop_theft, "직접")

    # C사: 보험사 코드가 가장 뒤라 조회 순서상 마지막에 오지만 면책 근거는 갖고 있다.
    # (정렬을 하지 않으면 이 경고가 다른 보험사 추천 뒤로 밀린다 — 정렬 테스트의 판별 케이스)
    insurer_c, version_c = _make_insurer(db, "C", "마바보험")
    cov_c = _make_coverage(db, version_c, std_death, "상해사망 보통약관")
    clause_c_waiver = _make_clause(db, version_c, cov_c, "면책", WAIVER_TEXT_WITH_SCUBA, "빨강")
    _map(db, clause_c_waiver, inj_death, "면책")

    db.commit()
    return {
        "db": db,
        "insurer_a": insurer_a, "insurer_b": insurer_b, "insurer_c": insurer_c,
        "cov_a": cov_a, "cov_b": cov_b, "cov_a_prop": cov_a_prop, "cov_c": cov_c,
    }


def _profile(activities, coverage_priority):
    profile = build_risk_profile(
        destination="일본",
        start_date=dt.date(2026, 9, 1),
        end_date=dt.date(2026, 9, 5),
        purpose="관광",
        activities=activities,
        companion_type="혼자",
        rental_car=False,
    )
    profile["coverage_priority"] = coverage_priority
    return profile


def _waiver_findings(findings, insurer_code=None):
    rows = [f for f in findings if f["finding_type"] == "제한조건"]
    if insurer_code is not None:
        rows = [f for f in rows if f["insurer_code"] == insurer_code]
    return rows


# ---------------------------------------------------------------- T1
def test_일반_관광은_위험행위_경고를_내지_않는다(kb):
    findings = generate_pre_trip_findings(kb["db"], _profile(["관광"], ["INJ"]))

    assert _waiver_findings(findings) == []


# ---------------------------------------------------------------- T2
def test_면책_원문에_활동명이_있으면_근거와_함께_경고한다(kb):
    findings = generate_pre_trip_findings(kb["db"], _profile(["스쿠버다이빙"], ["INJ"]))

    warnings = _waiver_findings(findings, insurer_code="A")
    assert len(warnings) == 1
    warning = warnings[0]
    assert "스쿠버다이빙" in warning["description"]
    # 근거 조항이 반드시 붙고, 그 원문에 활동명이 문자 그대로 들어 있어야 한다.
    assert warning["evidence"], "면책 경고에는 근거 조항이 반드시 있어야 한다"
    assert any("스쿠버다이빙" in clause.text for clause, _color in warning["evidence"])


def test_고르지_않은_사고유형의_면책은_경고하지_않는다(kb):
    """활동이 위험해도, 사용자가 고르지 않은 사고유형(INJ)의 면책 조항까지 끌고 오면 안 된다.

    예전 엔진은 담보코드(DEATH_INJURY/OVS_INJ_MED)를 하드코딩해서 활동만 걸리면 무조건
    상해 면책을 붙였다. 판단축이 IncidentType으로 바뀌면 선택한 유형 안에서만 걸려야 한다."""
    findings = generate_pre_trip_findings(kb["db"], _profile(["스쿠버다이빙"], ["PROP"]))

    assert _waiver_findings(findings) == []


# ---------------------------------------------------------------- T3
def test_다른_보험사_약관에_근거가_없으면_단정적_면책경고를_하지_않는다(kb):
    findings = generate_pre_trip_findings(kb["db"], _profile(["스쿠버다이빙"], ["INJ"]))

    assert _waiver_findings(findings, insurer_code="B") == []


# ---------------------------------------------------------------- T4
def test_선택한_사고유형이_추천_담보에_반영된다(kb):
    findings = generate_pre_trip_findings(kb["db"], _profile(["관광"], ["PROP"]))

    recommended = [f for f in findings if f["finding_type"] == "추천담보"]
    assert recommended, "PROP을 골랐으면 휴대품 담보가 나와야 한다"
    assert all(f["insurer_code"] == "A" for f in recommended)
    assert any("휴대품" in f["target_ref"] for f in recommended)
    # INJ 담보는 고르지 않았으므로 나오면 안 된다.
    assert not any("상해" in f["target_ref"] for f in recommended)


# ---------------------------------------------------------------- T5
def test_매핑_근거가_없는_사고유형은_추천하지_않고_확인불가로_남긴다(kb):
    findings = generate_pre_trip_findings(kb["db"], _profile(["관광"], ["LIA"]))

    assert [f for f in findings if f["finding_type"] == "추천담보"] == []
    gaps = [f for f in findings if f["finding_type"] == "보장공백"]
    assert gaps, "근거가 없으면 조용히 빠뜨리지 않고 확인불가로 남겨야 한다"
    assert all(f["status"] == "확인불가" for f in gaps)
    assert all(f["evidence"] == [] for f in gaps)


def test_경고가_먼저_확인불가가_마지막으로_정렬된다(kb):
    """사고유형을 여러 개 고르면 결과가 수십 건이 될 수 있다. 근거 있는 결과를 버리지는
    않되, 먼저 봐야 하는 것(면책 경고)이 위로 오고 판단 근거가 없는 항목이 맨 뒤로 가야 한다."""
    findings = generate_pre_trip_findings(
        kb["db"], _profile(["스쿠버다이빙"], ["INJ", "PROP", "LIA"])
    )
    order = [f["finding_type"] for f in findings]

    assert "제한조건" in order and "추천담보" in order and "보장공백" in order
    # 보험사가 여러 곳이면 경고도 여러 건이다. 그 '전부'가 추천보다 앞에 와야 한다
    # (일부만 앞에 오면 뒤쪽 보험사 경고를 놓친다).
    rank = {"제한조건": 0, "추천담보": 1, "보장공백": 2}
    ranks = [rank[t] for t in order]
    assert ranks == sorted(ranks), f"경고→추천→확인불가 순으로 묶여야 한다: {order}"
