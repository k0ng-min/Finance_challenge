import pytest

from app.models.external import ExternalPolicy, OverlapRule
from app.models.kb import Clause, CoverageStd
from app.services.coverage_overlap import diagnose, _QUOTE_LIMIT


@pytest.fixture
def seeded(db_session):
    db_session.add(CoverageStd(
        coverage_std_id=2, std_code="OVS_INJ_MED", std_name="해외발생 상해의료비",
        category="의료", is_base=0,
    ))
    db_session.add(CoverageStd(
        coverage_std_id=6, std_code="LIABILITY", std_name="배상책임",
        category="배상책임", is_base=0,
    ))
    db_session.add(Clause(
        clause_id=901, policy_version_id=1, article_no="제3조",
        clause_type="보장정의",
        text="회사는 보험가입금액을 한도로 피보험자가 실제 부담한 의료비 전액을 보상합니다.",
    ))
    db_session.add(OverlapRule(
        external_kind="MEDICAL_INDEMNITY", coverage_std_id=2, scope="해외 의료기관",
        relation="NO_OVERLAP", clause_id=901, note="해외 진료는 기존 실손으로 보상되지 않는다",
    ))
    db_session.add(OverlapRule(
        external_kind="DAILY_LIABILITY", coverage_std_id=6, scope="전체",
        relation="DUPLICATE_PRORATA", clause_id=901, note="초과액만 보상한다",
    ))
    db_session.commit()
    return db_session


def test_기존보험이_없으면_모두_확인대상에서_빠진다(seeded):
    report = diagnose(seeded, external_policies=[], target_coverage_std_ids=[2, 6])
    assert report.duplicates == []
    assert report.gaps == []
    assert report.fixed_ok == []


def test_실손이_있으면_해외의료비는_공백으로_잡힌다(seeded):
    policy = ExternalPolicy(user_id=1, source="manual", kind="MEDICAL_INDEMNITY")
    seeded.add(policy)
    seeded.commit()

    report = diagnose(seeded, external_policies=[policy], target_coverage_std_ids=[2])
    assert len(report.gaps) == 1
    finding = report.gaps[0]
    assert finding.coverage_std_code == "OVS_INJ_MED"
    assert finding.relation == "NO_OVERLAP"
    assert finding.clause_id == 901


def test_일상배상책임이_있으면_배상책임은_중복으로_잡힌다(seeded):
    policy = ExternalPolicy(user_id=1, source="manual", kind="DAILY_LIABILITY")
    seeded.add(policy)
    seeded.commit()

    report = diagnose(seeded, external_policies=[policy], target_coverage_std_ids=[6])
    assert len(report.duplicates) == 1
    assert report.duplicates[0].relation == "DUPLICATE_PRORATA"


def test_규칙이_없는_조합은_확인불가로_남는다(seeded):
    """근거가 없으면 단정하지 않는다."""
    policy = ExternalPolicy(user_id=1, source="manual", kind="DRIVER")
    seeded.add(policy)
    seeded.commit()

    report = diagnose(seeded, external_policies=[policy], target_coverage_std_ids=[2, 6])
    assert len(report.unknown) == 2
    assert all(f.relation == "UNKNOWN" for f in report.unknown)
    assert all(f.clause_id is None for f in report.unknown)


def test_인용문은_조항_원문의_부분_문자열이다(seeded):
    policy = ExternalPolicy(user_id=1, source="manual", kind="MEDICAL_INDEMNITY")
    seeded.add(policy)
    seeded.commit()

    report = diagnose(seeded, external_policies=[policy], target_coverage_std_ids=[2])
    clause = seeded.query(Clause).filter(Clause.clause_id == 901).one()
    quote = report.gaps[0].clause_quote
    assert quote
    assert quote in clause.text


def test_길이를_초과하는_조항은_정확히_자른다(seeded):
    """
    _QUOTE_LIMIT를 넘는 조항 텍스트는 정확히 자르고, 말줄임표를 붙이지 않는다.
    이 테스트는 `text[:_QUOTE_LIMIT] + "..."` 같은 회귀를 감지한다.
    """
    long_text = (
        "보험사는 피보험자가 여행 중 질병, 상해, 사고로 인하여 의료기관에서 치료받은 모든 의료비를 "
        "보험가입금액을 한도로 실제 청구액 범위 내에서 보상합니다. 다만 진단비, 입원비, 수술비, "
        "약제비 등 각 항목별로 정한 한도액이 있으며, 자기부담금을 공제합니다. 해외에서 발생한 질병 및 상해는 "
        "특별 약관의 보장 범위와 조건을 따르며, 보험사가 지정한 네트워크 병원을 이용할 경우 할인이 적용됩니다."
    )
    # 길이 확인: _QUOTE_LIMIT(200)보다 길어야 함
    assert len(long_text) > _QUOTE_LIMIT

    # 긴 텍스트를 포함하는 Clause 추가
    seeded.add(Clause(
        clause_id=902, policy_version_id=1, article_no="제5조",
        clause_type="보장정의",
        text=long_text,
    ))
    # 새 OverlapRule 추가 (clause_id=902를 가리킴)
    seeded.add(OverlapRule(
        external_kind="MEDICAL_INDEMNITY", coverage_std_id=2, scope="해외 의료비",
        relation="NO_OVERLAP", clause_id=902, note="상세 보장 범위",
    ))
    seeded.commit()

    # 진단 실행
    policy = ExternalPolicy(user_id=1, source="manual", kind="MEDICAL_INDEMNITY")
    seeded.add(policy)
    seeded.commit()

    report = diagnose(seeded, external_policies=[policy], target_coverage_std_ids=[2])
    # 이제 gaps에 2개의 항목이 있어야 함 (기존 clause_id=901 + 새로운 clause_id=902)
    gaps_by_id = {f.clause_id: f for f in report.gaps}
    assert 902 in gaps_by_id
    finding = gaps_by_id[902]

    quote = finding.clause_quote
    assert quote is not None

    # 검증 1: 인용문이 원문의 부분 문자열이다
    assert quote in long_text, f"인용문이 원문의 부분 문자열이 아닙니다: {quote!r}"

    # 검증 2: 말줄임표로 끝나지 않는다 (회귀 방지)
    assert not quote.endswith("..."), f"인용문이 '...'로 끝나면 안 됩니다: {quote!r}"
    assert not quote.endswith("…"), f"인용문이 '…'로 끝나면 안 됩니다: {quote!r}"

    # 검증 3: 길이가 제한 이하다
    assert len(quote) <= _QUOTE_LIMIT, (
        f"인용문 길이({len(quote)})가 _QUOTE_LIMIT({_QUOTE_LIMIT})을 초과합니다: {quote!r}"
    )
