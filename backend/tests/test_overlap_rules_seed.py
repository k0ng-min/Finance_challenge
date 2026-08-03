from app.models.external import OverlapRule
from app.seed_overlap_rules import RULE_SPECS


def test_UNKNOWN이_아닌_규칙은_모두_근거조항_조회조건을_갖는다():
    """근거 없는 판정을 구조적으로 막는다 — 이 테스트가 그 계약을 강제한다."""
    for spec in RULE_SPECS:
        if spec["relation"] != "UNKNOWN":
            assert spec.get("clause_lookup"), f"근거 없는 규칙: {spec}"


def test_같은_담보_구간_조합이_중복되지_않는다():
    seen = set()
    for spec in RULE_SPECS:
        key = (spec["external_kind"], spec["coverage_std_code"], spec["scope"])
        assert key not in seen, f"중복된 규칙 키: {key}"
        seen.add(key)


def test_relation은_정의된_값만_쓴다():
    allowed = {"NO_OVERLAP", "DUPLICATE_PRORATA", "DUPLICATE_FIXED", "PARTIAL", "UNKNOWN"}
    for spec in RULE_SPECS:
        assert spec["relation"] in allowed


def test_실손과_해외의료비는_겹치지_않는다고_판정한다():
    """기존 실손은 국내 의료기관만 보상한다 — '실손 있으니 해외의료비를 빼라'는 조언은 틀렸다."""
    specs = [
        s for s in RULE_SPECS
        if s["external_kind"] == "MEDICAL_INDEMNITY"
        and s["coverage_std_code"] == "OVS_INJ_MED"
    ]
    assert len(specs) == 1
    assert specs[0]["relation"] == "NO_OVERLAP"


def test_질병의료비는_구간에_따라_판정이_갈린다():
    specs = {
        s["scope"]: s["relation"] for s in RULE_SPECS
        if s["external_kind"] == "MEDICAL_INDEMNITY"
        and s["coverage_std_code"] == "OVS_ILL_MED"
    }
    assert specs["해외 의료기관"] == "NO_OVERLAP"
    assert specs["국내 의료기관"] == "PARTIAL"


def test_시드는_빈_DB에서도_돌고_결과를_남긴다(db_session):
    """근거 조항이 없는 테스트 DB에서는 아무 행도 넣지 않되 예외도 내지 않는다
    (운영 DB 시드는 별도로 조항 존재를 검증한다)."""
    from app.seed_overlap_rules import seed_overlap_rules
    inserted = seed_overlap_rules(db_session, strict=False)
    assert inserted == 0
    assert db_session.query(OverlapRule).count() == 0
