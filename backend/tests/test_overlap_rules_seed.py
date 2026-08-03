import os

import pytest

from app.models.external import OverlapRule
from app.seed_overlap_rules import RULE_SPECS

# db_session fixture(인메모리, 빈 DB)로는 근거 조항 원문을 대조할 수 없다 — 실제 약관 텍스트가
# 운영 DB(backend/data/app.db)에만 있기 때문이다. 그래서 이 파일이 있는 위치를 기준으로 상대
# 경로를 잡는다(테스트가 어느 디렉터리에서 실행되든 항상 backend/data/app.db를 가리키도록).
_APP_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "app.db")

# (external_kind, coverage_std_code, scope) -> 근거 조항 원문에 반드시 있어야 하는 핵심 문구.
# "clause_id가 채워졌다"는 조회가 성공했다는 뜻일 뿐, 그 조항이 note의 주장을 실제로
# 뒷받침한다는 보장은 아니다(실제로 PASSPORT_LOSS 규칙이 한 번 이렇게 어긋난 적이 있다 —
# 조회는 성공했지만 엉뚱한/불충분한 조항이 걸렸었다). 이 표가 그 간극을 구조적으로 막는다.
_KEY_PHRASES = {
    ("MEDICAL_INDEMNITY", "OVS_INJ_MED", "해외 의료기관"): "해외의료기관",
    ("MEDICAL_INDEMNITY", "OVS_ILL_MED", "해외 의료기관"): "해외의료기관",
    ("MEDICAL_INDEMNITY", "OVS_ILL_MED", "국내 의료기관"): "실제 본인이 부담한 의료비",
    ("DAILY_LIABILITY", "LIABILITY", "전체"): "초과액만을 보상합니다",
    ("ACCIDENT", "DEATH_INJURY", "전체"): "약정한 보험금을 지급합니다",
    ("OTHER", "PASSPORT_LOSS", "전체"): "비율에 따라",
    ("OTHER", "HIJACK", "전체"): "하나의 계약에서만 보상",
}


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


def test_시드된_규칙의_근거조항_원문에_note의_핵심주장이_실제로_있다():
    """clause_id가 붙어 있다고 근거가 맞는 것은 아니다 — 그 조항 원문을 직접 읽어 note의
    핵심 주장이 실제로 쓰여 있는지 확인한다. 운영 DB가 없는 환경(CI 등)에서는 건너뛴다."""
    if not os.path.exists(_APP_DB_PATH):
        pytest.skip("운영 DB(backend/data/app.db)가 없어 근거 원문 대조를 건너뜁니다")

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.models.external import OverlapRule as _OverlapRule
    from app.models.kb import Clause, CoverageStd

    engine = create_engine(f"sqlite:///{_APP_DB_PATH}")
    db = sessionmaker(bind=engine)()
    try:
        rules = (
            db.query(_OverlapRule, CoverageStd.std_code)
            .join(CoverageStd, CoverageStd.coverage_std_id == _OverlapRule.coverage_std_id)
            .all()
        )
        if not rules:
            pytest.skip("운영 DB에 overlap_rule이 아직 시드되지 않았습니다")

        checked = 0
        for rule, std_code in rules:
            key = (rule.external_kind, std_code, rule.scope)
            phrase = _KEY_PHRASES.get(key)
            if phrase is None:
                continue  # 이 표에 없는 규칙(추가된 신규 규칙)은 검증 대상이 아니다

            assert rule.clause_id is not None, f"근거 조항 없음: {key}"
            clause = db.query(Clause).filter(Clause.clause_id == rule.clause_id).first()
            assert clause is not None, f"clause_id={rule.clause_id}가 가리키는 조항이 없음: {key}"
            assert phrase in clause.text, (
                f"{key} 규칙의 근거 조항(clause_id={rule.clause_id})에 핵심 문구 "
                f"'{phrase}'가 없습니다 — 조회는 됐지만 근거가 note를 뒷받침하지 못합니다.\n"
                f"조항 원문: {clause.text[:200]}"
            )
            checked += 1

        assert checked == len(_KEY_PHRASES), (
            f"_KEY_PHRASES에 정의된 규칙 중 일부를 대조하지 못했습니다 "
            f"({checked}/{len(_KEY_PHRASES)}) — RULE_SPECS나 _KEY_PHRASES 표를 갱신했는지 확인하세요."
        )
    finally:
        db.close()
