import os

import pytest

from app.seed_clause_standard_map import ARTICLE_ANCHOR, RULE_SPECS

_APP_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "app.db")


def test_모든_규칙은_보험사_조항_앵커문구를_갖는다():
    """근거 없는 대조 판정을 구조적으로 막는다 — overlap_rule과 같은 계약."""
    for spec in RULE_SPECS:
        assert spec.get("anchor_insurer"), f"anchor_insurer 없는 규칙: {spec}"


def test_모든_규칙의_표준조문은_ARTICLE_ANCHOR에_앵커문구가_정의돼있다():
    for spec in RULE_SPECS:
        assert spec["article_no"] in ARTICLE_ANCHOR, f"앵커 미정의 조문: {spec['article_no']}"


def test_relation은_정의된_값만_쓴다():
    allowed = {"SAME", "BROADER", "NARROWER", "MISSING_IN_INSURER"}
    for spec in RULE_SPECS:
        assert spec["relation"] in allowed


def test_같은_보험사_같은_조문_규칙이_중복되지_않는다():
    seen = set()
    for spec in RULE_SPECS:
        key = (spec["insurer_frag"], spec["article_no"])
        assert key not in seen, f"중복된 규칙 키: {key}"
        seen.add(key)


def test_MISSING_IN_INSURER_규칙은_clause_lookup이_없다():
    """대응 조항이 없다는 판정은 근거 조항을 조회하지 않는다 — clause_id가 실수로도
    채워지지 않게 하는 구조적 장치(현재 RULE_SPECS에는 아직 이런 행이 없지만, 앞으로
    추가될 때도 이 계약이 지켜져야 한다)."""
    for spec in RULE_SPECS:
        if spec["relation"] == "MISSING_IN_INSURER":
            assert "clause_lookup" not in spec, f"MISSING_IN_INSURER인데 clause_lookup이 있는 규칙: {spec}"


def test_시드는_빈_DB에서도_돌고_예외를_던진다(db_session):
    """근거 조항이 없는 테스트 DB에서는 표준조문 자체가 비어 있으므로 예외를 던진다
    (운영 DB 시드는 별도로 조항 존재를 검증한다)."""
    from app.seed_clause_standard_map import seed_clause_standard_map

    with pytest.raises(RuntimeError):
        seed_clause_standard_map(db_session, strict=True)


def test_시드된_규칙의_양쪽_원문에_앵커문구가_실제로_있다():
    """clause_id가 붙어 있다고 근거가 맞는 것은 아니다 — 표준약관 원문과 보험사 조항
    원문 양쪽에서 앵커 문구가 실제로 부분 문자열인지 직접 확인한다.
    운영 DB가 없는 환경(CI 등)에서는 건너뛴다."""
    if not os.path.exists(_APP_DB_PATH):
        pytest.skip("운영 DB(backend/data/app.db)가 없어 근거 원문 대조를 건너뜁니다")

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.models.kb import Clause, ClauseStandardMap, StandardClause

    engine = create_engine(f"sqlite:///{_APP_DB_PATH}")
    db = sessionmaker(bind=engine)()
    try:
        rows = db.query(ClauseStandardMap).all()
        if not rows:
            pytest.skip("운영 DB에 clause_standard_map이 아직 시드되지 않았습니다")

        for row in rows:
            standard = db.query(StandardClause).filter(
                StandardClause.standard_clause_id == row.standard_clause_id
            ).first()
            assert standard is not None
            assert row.anchor_phrase_standard in standard.text, (
                f"map_id={row.map_id}: anchor_phrase_standard가 표준조문 원문의 부분 문자열이 아닙니다"
            )

            if row.relation == "MISSING_IN_INSURER":
                assert row.clause_id is None
                assert row.anchor_phrase_insurer is None
            else:
                assert row.clause_id is not None
                clause = db.query(Clause).filter(Clause.clause_id == row.clause_id).first()
                assert clause is not None
                assert row.anchor_phrase_insurer, f"map_id={row.map_id}: anchor_phrase_insurer가 비어있습니다"
                assert row.anchor_phrase_insurer in clause.text, (
                    f"map_id={row.map_id}: anchor_phrase_insurer가 보험사 조항 원문의 부분 문자열이 아닙니다"
                )
    finally:
        db.close()


def test_표준조문_원문이_HWP_표를_재구성한_부분은_원문_단어를_바꾸지_않았다():
    """제3·4조는 원문이 표(Row/Cell)라 선형 텍스트가 아니다. 표를 이어붙이며 구분자
    (' | ', ' / ')를 추가했을 뿐 원문 단어 자체는 바꾸지 않았는지 핵심 문구로 확인한다.
    운영 DB가 없는 환경(CI 등)에서는 건너뛴다."""
    if not os.path.exists(_APP_DB_PATH):
        pytest.skip("운영 DB(backend/data/app.db)가 없어 근거 원문 대조를 건너뜁니다")

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.models.kb import StandardClause

    engine = create_engine(f"sqlite:///{_APP_DB_PATH}")
    db = sessionmaker(bind=engine)()
    try:
        article3 = db.query(StandardClause).filter(
            StandardClause.standard_name == "해외여행 실손의료보험",
            StandardClause.article_no == "제3조",
        ).first()
        if article3 is None:
            pytest.skip("운영 DB에 standard_clause가 아직 시드되지 않았습니다")

        assert "해외의료기관주1)에서 의료비가 발생한 경우에 보상" in article3.text
        assert "급여주2) 치료를 받거나 급여 처방조제를 받은 경우에 보상" in article3.text

        article4 = db.query(StandardClause).filter(
            StandardClause.standard_name == "해외여행 실손의료보험",
            StandardClause.article_no == "제4조",
        ).first()
        assert article4 is not None
        assert "전쟁, 외국의 무력행사, 혁명, 내란, 사변, 폭동으로 인한 경우" in article4.text
        assert "간병비 <신설 2026.5.6.>" in article4.text
    finally:
        db.close()
