import pytest

from app.models.external import ExternalPolicy, OverlapRule
from app.models.kb import Clause, CoverageStd
from app.services.coverage_overlap import diagnose


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
