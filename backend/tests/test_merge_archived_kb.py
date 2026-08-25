"""이전 판 약관에서 빈칸만 메우는 병합(merge_archived_kb)의 규칙을 고정한다.

2026-08-18 약관 전면 재구축은 전체로는 매핑을 352→527건으로 늘렸지만, 현대해상과
카카오페이는 휴대품·긴급지원처럼 통째로 비어버린 사고유형이 생겼다. 그 자리에서
"휴대폰을 분실했다"를 접수하면 관련 약관이 하나도 나오지 않는다.

이 병합이 지켜야 할 것은 딱 두 가지다.
  1. 현재 판에 조항이 하나라도 있는 자리는 절대 건드리지 않는다(현재 판 우선).
  2. 채워 넣는 것은 이전 판 약관의 실제 원문 그대로다 — 지어낸 문장이 아니다.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.merge_archived_kb import merge_archived
from app.models.kb import (
    Clause, ClauseIncidentMap, Coverage, CoverageStd, IncidentType, Insurer, PolicyVersion, Product,
)


def _build(session, *, clause_text, type_id, insurer_name, std_code, with_map=True):
    """보험사 하나 + 담보 하나 + 조항 하나 + (선택) 사고유형 매핑을 만든다."""
    insurer = session.query(Insurer).filter_by(name=insurer_name).first()
    if not insurer:
        insurer = Insurer(name=insurer_name, code=insurer_name[:3])
        session.add(insurer)
        session.flush()
        product = Product(insurer_id=insurer.insurer_id, name="해외여행보험")
        session.add(product)
        session.flush()
        pv = PolicyVersion(product_id=product.product_id, version_label="테스트판")
        session.add(pv)
        session.flush()
    else:
        pv = (
            session.query(PolicyVersion)
            .join(Product, Product.product_id == PolicyVersion.product_id)
            .filter(Product.insurer_id == insurer.insurer_id).first()
        )

    std = session.query(CoverageStd).filter_by(std_code=std_code).first()
    if not std:
        std = CoverageStd(std_code=std_code, std_name=std_code, category="특약", is_base=False)
        session.add(std)
        session.flush()
    cov = (
        session.query(Coverage)
        .filter(Coverage.policy_version_id == pv.policy_version_id,
                Coverage.coverage_std_id == std.coverage_std_id).first()
    )
    if not cov:
        cov = Coverage(policy_version_id=pv.policy_version_id, coverage_std_id=std.coverage_std_id,
                       raw_name=f"{std_code} 특별약관")
        session.add(cov)
        session.flush()
    clause = Clause(policy_version_id=pv.policy_version_id, coverage_id=cov.coverage_id,
                    clause_type="보장정의", article_no="제1조", text=clause_text)
    session.add(clause)
    session.flush()
    if with_map:
        session.add(ClauseIncidentMap(clause_id=clause.clause_id, type_id=type_id,
                                      relevance="직접", mapped_by="test", confidence=1.0))
    session.flush()
    return insurer, cov, clause


def _seed_types(session):
    for tid, l1, l2, name in [(13, "PROP", "PROP_LOSS", "분실"), (11, "PROP", "PROP_THEFT", "도난")]:
        session.add(IncidentType(type_id=tid, l1_code=l1, l2_code=l2, name=name, is_active=True))
    session.flush()


@pytest.fixture
def archived_db(tmp_path):
    """이전 판 역할을 하는 별도 SQLite 파일을 만들어 (세션, 경로)를 준다."""
    path = tmp_path / "archived.db"
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    _seed_types(session)
    session.commit()
    yield session, str(path)
    session.close()
    engine.dispose()


def _mapped_texts(session, type_id):
    return sorted(
        c.text for c in session.query(Clause)
        .join(ClauseIncidentMap, ClauseIncidentMap.clause_id == Clause.clause_id)
        .filter(ClauseIncidentMap.type_id == type_id).all()
    )


def test_현재_판이_비어_있는_자리만_이전_판_원문으로_채운다(db_session, archived_db):
    archived, path = archived_db
    _seed_types(db_session)
    # 현재 판: 휴대품 담보는 있지만 '분실'에 매핑된 조항이 없다.
    _build(db_session, clause_text="현재 판 도난 조항", type_id=11,
           insurer_name="현대해상", std_code="PERSONAL_EFFECTS")
    db_session.commit()
    _build(archived, clause_text="이전 판 분실 조항 원문", type_id=13,
           insurer_name="현대해상", std_code="PERSONAL_EFFECTS")
    archived.commit()

    result = merge_archived(db_session, path, edition_label="2025판")
    db_session.commit()

    assert _mapped_texts(db_session, 13) == ["이전 판 분실 조항 원문"]
    imported = db_session.query(Clause).filter(Clause.text == "이전 판 분실 조항 원문").one()
    assert imported.source_edition == "2025판"
    assert result["clauses"] == 1 and result["maps"] == 1


def test_현재_판에_이미_있는_자리는_건드리지_않는다(db_session, archived_db):
    archived, path = archived_db
    _seed_types(db_session)
    _build(db_session, clause_text="현재 판 분실 조항", type_id=13,
           insurer_name="현대해상", std_code="PERSONAL_EFFECTS")
    db_session.commit()
    _build(archived, clause_text="이전 판 분실 조항", type_id=13,
           insurer_name="현대해상", std_code="PERSONAL_EFFECTS")
    archived.commit()

    result = merge_archived(db_session, path, edition_label="2025판")
    db_session.commit()

    assert _mapped_texts(db_session, 13) == ["현재 판 분실 조항"]
    assert result["clauses"] == 0 and result["maps"] == 0


def test_다른_보험사의_조항을_끌어오지_않는다(db_session, archived_db):
    """보험사별로 독립이어야 한다 — 삼성에 있다고 현대해상 결과에 삼성 조항이 붙으면 안 된다."""
    archived, path = archived_db
    _seed_types(db_session)
    _build(db_session, clause_text="현재 판 삼성 분실 조항", type_id=13,
           insurer_name="삼성화재", std_code="PERSONAL_EFFECTS")
    _build(db_session, clause_text="현재 판 현대 도난 조항", type_id=11,
           insurer_name="현대해상", std_code="PERSONAL_EFFECTS")
    db_session.commit()
    _build(archived, clause_text="이전 판 현대 분실 조항", type_id=13,
           insurer_name="현대해상", std_code="PERSONAL_EFFECTS")
    archived.commit()

    merge_archived(db_session, path, edition_label="2025판")
    db_session.commit()

    rows = (
        db_session.query(Clause.text, Insurer.name)
        .join(ClauseIncidentMap, ClauseIncidentMap.clause_id == Clause.clause_id)
        .join(PolicyVersion, PolicyVersion.policy_version_id == Clause.policy_version_id)
        .join(Product, Product.product_id == PolicyVersion.product_id)
        .join(Insurer, Insurer.insurer_id == Product.insurer_id)
        .filter(ClauseIncidentMap.type_id == 13).all()
    )
    assert sorted((name, text) for text, name in rows) == [
        ("삼성화재", "현재 판 삼성 분실 조항"),
        ("현대해상", "이전 판 현대 분실 조항"),
    ]


def test_담보_자체가_없으면_담보도_같이_들여온다(db_session, archived_db):
    """현대해상은 새 PDF에 휴대품 특약이 아예 없어서 담보 행조차 없다."""
    archived, path = archived_db
    _seed_types(db_session)
    _build(db_session, clause_text="현재 판 상해 조항", type_id=11,
           insurer_name="현대해상", std_code="OVERSEAS_MED")
    db_session.commit()
    _build(archived, clause_text="이전 판 휴대품 분실 조항", type_id=13,
           insurer_name="현대해상", std_code="PERSONAL_EFFECTS")
    archived.commit()

    result = merge_archived(db_session, path, edition_label="2025판")
    db_session.commit()

    cov = (
        db_session.query(Coverage)
        .join(CoverageStd, CoverageStd.coverage_std_id == Coverage.coverage_std_id)
        .filter(CoverageStd.std_code == "PERSONAL_EFFECTS").one()
    )
    clause = db_session.query(Clause).filter(Clause.text == "이전 판 휴대품 분실 조항").one()
    assert clause.coverage_id == cov.coverage_id, "들여온 조항이 새로 만든 담보에 붙어야 한다"
    assert result["coverages"] == 1


def test_이미_같은_원문이_있으면_조항을_또_만들지_않는다(db_session, archived_db):
    """같은 문장이 두 번 들어가면 약관 형광펜에 같은 조항이 나란히 두 번 뜬다."""
    archived, path = archived_db
    _seed_types(db_session)
    _build(db_session, clause_text="똑같은 조항 원문", type_id=11,
           insurer_name="현대해상", std_code="PERSONAL_EFFECTS")
    db_session.commit()
    _build(archived, clause_text="똑같은 조항 원문", type_id=13,
           insurer_name="현대해상", std_code="PERSONAL_EFFECTS")
    archived.commit()

    merge_archived(db_session, path, edition_label="2025판")
    db_session.commit()

    assert db_session.query(Clause).filter(Clause.text == "똑같은 조항 원문").count() == 1
    assert db_session.query(ClauseIncidentMap).filter(ClauseIncidentMap.type_id == 13).count() == 1


def test_이전_판에_없는_보험사는_아무_일도_일어나지_않는다(db_session, archived_db):
    archived, path = archived_db
    _seed_types(db_session)
    _build(db_session, clause_text="현재 판 조항", type_id=11,
           insurer_name="카카오페이", std_code="PERSONAL_EFFECTS")
    db_session.commit()

    result = merge_archived(db_session, path, edition_label="2025판")

    assert result == {"clauses": 0, "maps": 0, "coverages": 0, "terms": 0}
