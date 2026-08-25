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
#
# MEDICAL_INDEMNITY×OVS_INJ_MED(해외 의료기관)와 MEDICAL_INDEMNITY×OVS_ILL_MED(해외 의료기관),
# DAILY_LIABILITY×LIABILITY(전체) 세 조합은 이 표에 없다 — 근거 조항이 note의 주장을 실제로
# 뒷받침하지 못한다고 판명돼 UNKNOWN(확인불가)으로 내려졌다(RULE_SPECS 주석 참고).
_KEY_PHRASES = {
    ("MEDICAL_INDEMNITY", "OVS_ILL_MED", "국내 의료기관"): "실제 본인이 부담한 의료비",
    ("ACCIDENT", "DEATH_INJURY", "전체"): "약정한 보험금을 지급합니다",
    ("ANY", "PASSPORT_LOSS", "전체"): "비율에 따라",
    ("ANY", "HIJACK", "전체"): "하나의 계약에서만 보상",
}


def test_UNKNOWN이_아닌_규칙은_모두_근거조항_조회조건을_갖는다():
    """근거 없는 판정을 구조적으로 막는다 — 이 테스트가 그 계약을 강제한다.

    2026-08-18 재구축 이후로는 "보험사명+조항 제목 조각" 퍼지 조회(clause_lookup) 대신
    앵커 문구를 원문 전수 검색으로 먼저 확인한 뒤 그 clause_id를 직접 박아 쓴다 —
    구판본에서 fuzzy 조회가 엉뚱한 특약을 집어온 적이 있어(PASSPORT_LOSS 사례,
    seed_overlap_rules.py 주석 참고) 더 안전한 방식으로 바꿨다."""
    for spec in RULE_SPECS:
        if spec["relation"] != "UNKNOWN":
            assert spec.get("clause_id") is not None, f"근거 없는 규칙: {spec}"


def test_UNKNOWN이_아닌_규칙은_anchor_phrase도_갖는다():
    """clause_id가 있다고 인용문이 근거를 담는 건 아니다 — note의 핵심 주장을 가리키는
    anchor_phrase가 있어야 quote_clause()가 그 문구를 잘라내지 않고 담을 수 있다."""
    for spec in RULE_SPECS:
        if spec["relation"] != "UNKNOWN":
            assert spec.get("anchor_phrase"), f"anchor_phrase 없는 규칙: {spec}"


def test_UNKNOWN_규칙은_clause_id가_없다():
    """근거를 못 찾은 규칙은 clause_id 자체를 두지 않는다 — 실수로도 채워지지 않게 하는
    구조적 장치다(seed_overlap_rules()가 relation==UNKNOWN이면 clause_id를 아예 쓰지
    않는다)."""
    for spec in RULE_SPECS:
        if spec["relation"] == "UNKNOWN":
            assert "clause_id" not in spec, f"UNKNOWN인데 clause_id가 있는 규칙: {spec}"


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


def test_실손과_해외의료비는_근거가_없어_확인불가로_판정한다():
    """예전에는 이 조합을 '기존 실손은 국내 의료기관만 보상하니 여전히 필요하다'(NO_OVERLAP)로
    단정했다. 하지만 근거로 삼은 조항은 여행자보험 상품 자체의 보장 조항이지 기존 실손의
    보장 범위를 말하지 않는다 — 실손 표준약관이 이 DB에 없어 그 주장을 뒷받침할 근거가 없다.
    근거 없이 단정하지 않고 확인불가로 내리는 쪽이 이 프로젝트의 원칙과 맞다."""
    specs = [
        s for s in RULE_SPECS
        if s["external_kind"] == "MEDICAL_INDEMNITY"
        and s["coverage_std_code"] == "OVS_INJ_MED"
    ]
    assert len(specs) == 1
    assert specs[0]["relation"] == "UNKNOWN"


def test_질병의료비는_구간에_따라_판정이_갈린다():
    specs = {
        s["scope"]: s["relation"] for s in RULE_SPECS
        if s["external_kind"] == "MEDICAL_INDEMNITY"
        and s["coverage_std_code"] == "OVS_ILL_MED"
    }
    # 해외 의료기관 구간도 예전엔 NO_OVERLAP으로 단정했지만, 근거 조항이 기존 실손의 보장
    # 범위를 말하지 않아 확인불가로 내렸다(위 test_실손과_해외의료비는... 참고).
    assert specs["해외 의료기관"] == "UNKNOWN"
    assert specs["국내 의료기관"] == "PARTIAL"


def test_일상배상책임은_근거가_없어_확인불가로_판정한다():
    """예전엔 '의무보험과의 관계' 조항을 근거로 일상생활배상책임과 겹친다고 단정했다. 하지만
    그 조항 ②항은 의무보험을 '법률에 의하여 의무적으로 가입하여야 하는 보험'으로 직접
    정의하고, 일상생활배상책임은 의무보험이 아니다 — 근거가 안 맞아 확인불가로 내린다."""
    specs = [
        s for s in RULE_SPECS
        if s["external_kind"] == "DAILY_LIABILITY"
        and s["coverage_std_code"] == "LIABILITY"
    ]
    assert len(specs) == 1
    assert specs[0]["relation"] == "UNKNOWN"


def test_여권분실_항공기납치는_기존보험_종류와_무관하게_매칭되는_ANY다():
    """설계 §4는 이 두 규칙의 기존보험 종류를 (any)로 정의한다 — 실손이든 상해든 일상배상
    책임이든 상관없이 '다른 계약과의 비례분담' 조항이 적용된다. external_kind를 특정 종류
    (예: OTHER)로 좁히면 사용자가 그 종류를 명시적으로 골라야만 매칭돼 근거가 있는데도
    확인불가로 잘못 표시된다."""
    for code in ("PASSPORT_LOSS", "HIJACK"):
        specs = [s for s in RULE_SPECS if s["coverage_std_code"] == code]
        assert len(specs) == 1
        assert specs[0]["external_kind"] == "ANY", f"{code}는 external_kind가 ANY여야 한다"


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
                continue  # 이 표에 없는 규칙(UNKNOWN이거나 추가된 신규 규칙)은 검증 대상이 아니다

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


def test_시드된_규칙의_clause_quote에_note의_핵심주장이_실제로_있다():
    """clause.text 전체에 핵심 문구가 있어도, 화면에 실제로 보여주는 clausequote_clause(인용문)가
    그 문구를 잘라버리면 사용자는 근거 없는 주장을 보게 된다 — 이전 리뷰 두 번이 이 간극을
    놓쳤다(PASSPORT_LOSS·OVS_ILL_MED 국내 규칙에서 실제로 발생). clause.text가 아니라
    quote_clause()가 만드는 clause_quote 자체를 검증해야 이 결함을 잡는다.
    운영 DB가 없는 환경(CI 등)에서는 건너뛴다."""
    if not os.path.exists(_APP_DB_PATH):
        pytest.skip("운영 DB(backend/data/app.db)가 없어 근거 원문 대조를 건너뜁니다")

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.models.external import OverlapRule as _OverlapRule
    from app.models.kb import Clause, CoverageStd
    from app.services.clause_quote import quote_clause

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
                continue

            clause = db.query(Clause).filter(Clause.clause_id == rule.clause_id).first()
            assert clause is not None, f"clause_id={rule.clause_id}가 가리키는 조항이 없음: {key}"

            quote = quote_clause(clause, rule.anchor_phrase)
            assert quote is not None, f"{key} 규칙의 clause_quote가 비어있습니다"
            assert quote in clause.text, f"{key} 규칙의 clause_quote가 원문의 부분 문자열이 아닙니다"
            assert phrase in quote, (
                f"{key} 규칙의 clause_quote에 핵심 문구 '{phrase}'가 없습니다 — 화면에 보여주는 "
                f"인용문이 note의 주장을 뒷받침하지 못합니다.\n인용문: {quote!r}"
            )
            checked += 1

        assert checked == len(_KEY_PHRASES), (
            f"_KEY_PHRASES에 정의된 규칙 중 일부를 대조하지 못했습니다 "
            f"({checked}/{len(_KEY_PHRASES)}) — RULE_SPECS나 _KEY_PHRASES 표를 갱신했는지 확인하세요."
        )
    finally:
        db.close()
