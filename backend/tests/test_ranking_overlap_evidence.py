"""랭킹의 겹침 축이 중복 진단 엔진과 같은 근거만 쓰는지 고정한다.

예전에는 랭킹이 기존보험 종류를 사고유형(L1)에 직접 이어 붙였다 — MEDICAL_INDEMNITY면
INJ·ILL 전체를, DRIVER면 LIA 전체를 "이미 덮고 있다"고 보고 무게를 낮췄다. 그런데 같은
저장소의 근거 기반 엔진(coverage_overlap.diagnose)은 바로 그 조합들을 UNKNOWN, 즉
"약관 근거를 확보하지 못했다"로 판정하고 있었다. 한 서비스가 같은 사실을 두 화면에서
다르게 말한 것이고, 그건 "근거 없는 결과를 내지 않는다"는 원칙과 정면으로 어긋난다.

여기서 지키는 것:
  A. UNKNOWN뿐이면 감점하지 않는다(축을 아예 내린다).
  B. DUPLICATE_FIXED만 있으면 감점하지 않는다 — 정액 담보는 계약마다 각각 지급된다.
  C. DUPLICATE_PRORATA는 근거와 함께 있을 때만 반영된다.
  D. 랭킹의 설명이 coverage_overlap API의 판정과 어긋나지 않는다.
  E. 기존보험을 등록하지 않았으면 예전 그대로 중립이다.
"""
import pytest

from app.models.external import ExternalPolicy, OverlapRule
from app.models.kb import (
    Clause, Coverage, CoverageStd, Insurer, PolicyVersion, Product,
)
from app.services import ranking_score
from app.services.coverage_overlap import diagnose

CLAUSE_TEXT = "회사는 보험금을 지급할 다른 계약이 있으면 그 비율에 따라 나누어 지급합니다."


@pytest.fixture
def kb(db_session):
    """담보 세 종을 파는 보험사 하나. 규칙은 각 시험에서 필요한 것만 따로 심는다."""
    insurer = Insurer(code="TESTINS", name="테스트화재")
    db_session.add(insurer)
    db_session.flush()
    product = Product(insurer_id=insurer.insurer_id, name="해외여행보험")
    db_session.add(product)
    db_session.flush()
    version = PolicyVersion(product_id=product.product_id, version_label="2026.01")
    db_session.add(version)
    db_session.flush()

    stds = {}
    for std_id, code, name in [
        (2, "OVS_INJ_MED", "해외발생 상해의료비"),
        (6, "LIABILITY", "배상책임"),
        (9, "DEATH_INJURY", "상해사망·후유장해"),
    ]:
        std = CoverageStd(coverage_std_id=std_id, std_code=code, std_name=name,
                          category="기타", is_base=0)
        db_session.add(std)
        stds[code] = std_id
        db_session.add(Coverage(
            policy_version_id=version.policy_version_id, coverage_std_id=std_id,
            raw_name=name, limit_amount="3000",
        ))

    db_session.add(Clause(
        clause_id=901, policy_version_id=version.policy_version_id, article_no="제10조",
        clause_type="다른보험과의관계", text=CLAUSE_TEXT,
    ))
    db_session.commit()
    return stds


def _external(db, kind):
    policy = ExternalPolicy(user_id=1, source="manual", kind=kind)
    db.add(policy)
    db.commit()
    return policy


def _rule(db, kind, std_id, relation, clause_id=901, scope="전체"):
    db.add(OverlapRule(
        external_kind=kind, coverage_std_id=std_id, scope=scope, relation=relation,
        clause_id=clause_id if relation != "UNKNOWN" else None,
        anchor_phrase="비율에 따라" if relation != "UNKNOWN" else None,
        note="시험용 규칙",
    ))
    db.commit()


# --- Case A: UNKNOWN은 감점하지 않는다 -------------------------------------

def test_A_근거가_없으면_겹침_축을_감점하지_않고_내린다(db_session, kb):
    """DRIVER 보험은 어떤 규칙에도 걸리지 않는다 — 예전 휴리스틱은 이걸로 LIA 전체를
    기보장 처리했다. 이제는 판정 자체를 하지 않아야 한다."""
    policy = _external(db_session, "DRIVER")

    axis = ranking_score.overlap_score(db_session, "TESTINS", [policy])

    assert axis.available is False, "근거가 없는데 점수를 만들었습니다"
    assert axis.score == 0.0
    assert "근거" in axis.detail
    # 축이 available=False면 renormalize가 비중을 빼고 나머지로 100%를 다시 맞춘다 —
    # 즉 감점이 아니라 "이 축은 안 씀"이 된다.
    applied = ranking_score.renormalize(ranking_score._default_axis_weights(), {"overlap"})
    assert "overlap" not in applied
    assert abs(sum(applied.values()) - 1.0) < 1e-9


def test_A2_명시적_UNKNOWN_규칙도_감점하지_않는다(db_session, kb):
    """규칙 행이 있어도 relation이 UNKNOWN이면 마찬가지다."""
    _rule(db_session, "DAILY_LIABILITY", kb["LIABILITY"], "UNKNOWN")
    policy = _external(db_session, "DAILY_LIABILITY")

    axis = ranking_score.overlap_score(db_session, "TESTINS", [policy])
    assert axis.available is False


# --- Case B: 정액 중복은 감점하지 않는다 -----------------------------------

def test_B_정액_중복만_있으면_감점하지_않는다(db_session, kb):
    """정액 담보는 여러 계약에서 각각 지급된다. 겹친다는 이유만으로 깎으면 사실과
    반대되는 감점이 된다."""
    _rule(db_session, "ACCIDENT", kb["DEATH_INJURY"], "DUPLICATE_FIXED")
    policy = _external(db_session, "ACCIDENT")

    axis = ranking_score.overlap_score(db_session, "TESTINS", [policy])

    assert axis.available is False, "정액 중복만으로 점수를 만들었습니다"
    assert "정액" in axis.detail
    assert axis.score == 0.0  # available=False라 총점에 들어가지 않는다


def test_B2_정액_중복은_다른_판정의_점수를_끌어내리지_않는다(db_session, kb):
    """근거 있는 보완(NO_OVERLAP)과 정액 중복이 함께 있으면, 정액 쪽은 분모에서 빠져
    보완효용을 희석하지 않아야 한다."""
    _rule(db_session, "ACCIDENT", kb["DEATH_INJURY"], "DUPLICATE_FIXED")
    _rule(db_session, "ACCIDENT", kb["OVS_INJ_MED"], "NO_OVERLAP")
    policy = _external(db_session, "ACCIDENT")

    axis = ranking_score.overlap_score(db_session, "TESTINS", [policy])

    assert axis.available is True
    assert axis.score == 1.0, "정액 중복이 보완효용을 깎아내렸습니다"


# --- Case C: 비례분담 중복은 근거가 있을 때만 반영된다 ----------------------

def test_C_비례분담_중복은_근거와_함께_있을_때만_반영된다(db_session, kb):
    _rule(db_session, "MEDICAL_INDEMNITY", kb["OVS_INJ_MED"], "DUPLICATE_PRORATA")
    policy = _external(db_session, "MEDICAL_INDEMNITY")

    axis = ranking_score.overlap_score(db_session, "TESTINS", [policy])

    assert axis.available is True
    assert axis.score == 0.0, "근거 있는 비례분담 중복이 반영되지 않았습니다"
    assert "비례분담" in axis.detail


def test_C2_부분_중복은_절반만_반영된다(db_session, kb):
    _rule(db_session, "MEDICAL_INDEMNITY", kb["OVS_INJ_MED"], "PARTIAL")
    policy = _external(db_session, "MEDICAL_INDEMNITY")

    axis = ranking_score.overlap_score(db_session, "TESTINS", [policy])
    assert axis.score == 0.5
    assert "일부 겹침" in axis.detail


# --- Case D: 두 화면의 판정이 어긋나지 않는다 -------------------------------

def test_D_랭킹_설명과_중복진단_API_판정이_어긋나지_않는다(db_session, kb):
    """같은 기존보험·같은 담보에 대해, 진단 엔진이 '중복 없음'이라 한 것을 랭킹이
    '겹친다'고 말하거나 그 반대가 되어서는 안 된다."""
    _rule(db_session, "MEDICAL_INDEMNITY", kb["OVS_INJ_MED"], "NO_OVERLAP")
    _rule(db_session, "MEDICAL_INDEMNITY", kb["LIABILITY"], "DUPLICATE_PRORATA")
    policy = _external(db_session, "MEDICAL_INDEMNITY")

    target_ids = sorted(kb.values())
    report = diagnose(db_session, external_policies=[policy], target_coverage_std_ids=target_ids)
    axis = ranking_score.overlap_score(db_session, "TESTINS", [policy])

    prorata = [f for f in report.duplicates if f.relation == "DUPLICATE_PRORATA"]
    no_overlap = report.gaps
    assert len(prorata) == 1 and len(no_overlap) == 1

    # 진단이 반반이면 랭킹 점수도 정확히 그 반반이어야 한다.
    assert axis.score == 0.5
    assert f"안 겹침 {len(no_overlap)}건" in axis.detail
    assert f"비례분담 중복 {len(prorata)}건" in axis.detail
    # 진단이 확인불가로 남긴 담보 수도 설명에 그대로 드러난다.
    assert f"근거 없는 {len(report.unknown)}건" in axis.detail


# --- Case E: 기존보험 미등록 시 기존 동작 유지 ------------------------------

def test_E_기존보험을_등록하지_않았으면_예전대로_중립이다(db_session, kb):
    axis = ranking_score.overlap_score(db_session, "TESTINS", [])
    assert axis.available is True
    assert axis.score == 0.5
    assert "기존보험이 없어" in axis.detail

    axis_none = ranking_score.overlap_score(db_session, "TESTINS", None)
    assert axis_none.score == 0.5


def test_E2_기존보험은_사고유형_무게를_더는_흔들지_않는다():
    """예전에는 실손이 있으면 INJ·ILL 무게를 통째로 낮췄다. 그 가정을 없앴으므로
    incident_weights는 기존보험을 아예 모른다."""
    import inspect
    params = inspect.signature(ranking_score.incident_weights).parameters
    assert "external_kinds" not in params, "L1 기보장 가정이 아직 남아 있습니다"
    assert not hasattr(ranking_score, "EXTERNAL_KIND_TO_INCIDENT")
