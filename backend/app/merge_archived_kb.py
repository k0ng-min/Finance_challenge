"""이전 판 약관에서 **빈칸만** 메워 현재 KB를 보완한다.

왜 필요했나
-----------
2026-08-18에 약관 원본을 새 PDF로 갈아끼우며 KB를 전면 재구축했다(89beae8). 전체로는
사고유형 매핑이 352 → 527건으로 늘었지만, 보험사별로 보면 통째로 비어버린 자리가 생겼다.

    보험사        휴대품(PROP)   긴급지원(EMG)
    현대해상          5 → 0          6 → 0
    카카오페이         3 → 0          6 → 0

새 PDF에 그 특약이 실리지 않은 탓이다. 그래서 현대해상으로 "휴대폰을 분실했어요"를
접수하면 관련 약관이 **하나도** 나오지 않는다 — 이 서비스에서 가장 흔한 사고 하나가
통째로 답을 못 받는 상태였다.

무엇을 하나
-----------
(보험사, 사고유형) 짝을 하나씩 보고, **현재 판에 조항이 하나도 없을 때만** 이전 판의
그 자리 조항을 원문 그대로 들여온다. 지어낸 문장은 없고, 이전 판 약관에 실제로 적혀
있던 문장만 옮긴다. 들여온 조항에는 어느 판에서 왔는지 표시(clause.source_edition)를
남긴다.

지키는 규칙
-----------
1. **현재 판이 항상 우선.** 현재 판에 조항이 하나라도 있는 자리에는 절대 넣지 않는다.
   그래서 이미 잘 채워진 보험사(삼성·메리츠·DB·KB)의 결과는 한 글자도 바뀌지 않는다.
2. **보험사별로 독립.** 조항은 그 보험사의 policy_version에 속한다 — 현대해상 빈칸을
   삼성 조항으로 메우는 일은 없다.
3. **원문 그대로.** 조항 본문·조 번호·쪽수를 그대로 옮긴다. 수치 조건(ClauseTerm)은
   raw_text가 조항 원문의 부분 문자열일 때만 함께 옮긴다(raw_text_is_grounded).
4. **중복 금지.** 같은 보험사에 같은 문장이 이미 있으면 조항을 또 만들지 않고 매핑만
   붙인다 — 안 그러면 약관 형광펜에 같은 조항이 나란히 두 번 뜬다.

쓰는 법
-------
이전 판 DB는 저장소 이력에 있다(약관 재구축 직전 커밋). 파일로 꺼낸 뒤 넘긴다::

    cd backend
    git show 89beae8^:backend/data/app.db > /tmp/kb_prev.db
    python -m app.merge_archived_kb /tmp/kb_prev.db            # 무엇이 들어올지만 확인
    python -m app.merge_archived_kb /tmp/kb_prev.db --confirm  # 실제 반영
"""
from __future__ import annotations

import argparse
import sys
from typing import NamedTuple

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import SessionLocal
from app.models.kb import (
    Clause, ClauseIncidentMap, ClauseTerm, Coverage, CoverageStd, IncidentType, Insurer,
    PolicyVersion, Product,
)
from app.services.kb_seed_common import raw_text_is_grounded

DEFAULT_EDITION_LABEL = "2025년 판"


class ArchivedClause(NamedTuple):
    """이전 판 조항에서 옮길 값만 담는다.

    이전 판 DB는 그때의 스키마로 굳어 있어서 Clause 모델을 그대로 조회하면 그 뒤에 늘어난
    컬럼(source_edition 등)이 없어 깨진다. 옮길 값만 이름으로 집어 오면 스키마가 더
    벌어져도 이 파일이 계속 돌아간다."""
    clause_id: int
    coverage_id: int | None
    clause_type: str | None
    article_no: str | None
    text: str
    page_ref: str | None
    default_color: str | None


def _insurer_index(db: Session) -> dict[str, int]:
    """보험사 이름 → insurer_id. 두 DB 사이의 id는 다를 수 있어 이름으로 잇는다."""
    return {i.name: i.insurer_id for i in db.query(Insurer).all()}


def _primary_policy_version(db: Session, insurer_id: int) -> PolicyVersion | None:
    return (
        db.query(PolicyVersion)
        .join(Product, Product.product_id == PolicyVersion.product_id)
        .filter(Product.insurer_id == insurer_id)
        .order_by(PolicyVersion.policy_version_id)
        .first()
    )


def _mapped_pairs(db: Session) -> set[tuple[int, int]]:
    """(insurer_id, type_id) 중 조항 매핑이 하나라도 있는 짝."""
    rows = (
        db.query(Product.insurer_id, ClauseIncidentMap.type_id)
        .join(Clause, Clause.clause_id == ClauseIncidentMap.clause_id)
        .join(PolicyVersion, PolicyVersion.policy_version_id == Clause.policy_version_id)
        .join(Product, Product.product_id == PolicyVersion.product_id)
        .distinct().all()
    )
    return {(a, b) for a, b in rows}


def _resolve_target_coverage(
    db: Session, archived: Session, *, old_clause: Clause, policy_version_id: int, counters: dict,
) -> int | None:
    """들여올 조항을 붙일 현재 판 담보를 정한다.

    같은 표준담보코드(coverage_std)를 쓰는 담보가 현재 판에 있으면 그것에 붙인다. 없으면
    (새 PDF에 그 특약이 아예 안 실린 경우) 이전 판 담보를 현재 판 아래에 새로 만든다.
    조항에 담보가 없으면(보통약관 공통 조항) None 그대로 둔다."""
    if old_clause.coverage_id is None:
        return None
    old_cov = archived.get(Coverage, old_clause.coverage_id)
    if old_cov is None:
        return None

    old_std = archived.get(CoverageStd, old_cov.coverage_std_id) if old_cov.coverage_std_id else None
    if old_std is not None:
        std = db.query(CoverageStd).filter_by(std_code=old_std.std_code).first()
        if std is None:
            std = CoverageStd(std_code=old_std.std_code, std_name=old_std.std_name,
                              category=old_std.category, is_base=old_std.is_base)
            db.add(std)
            db.flush()
        existing = (
            db.query(Coverage)
            .filter(Coverage.policy_version_id == policy_version_id,
                    Coverage.coverage_std_id == std.coverage_std_id)
            .first()
        )
        if existing is not None:
            return existing.coverage_id
        std_id = std.coverage_std_id
    else:
        # 표준담보에 묶이지 않은 담보 — 이름이 같은 것이 있으면 그것을 쓴다.
        existing = (
            db.query(Coverage)
            .filter(Coverage.policy_version_id == policy_version_id,
                    Coverage.raw_name == old_cov.raw_name)
            .first()
        )
        if existing is not None:
            return existing.coverage_id
        std_id = None

    cov = Coverage(
        policy_version_id=policy_version_id, coverage_std_id=std_id, raw_name=old_cov.raw_name,
        definition=old_cov.definition, limit_amount=old_cov.limit_amount,
        deductible=old_cov.deductible, waiting_condition=old_cov.waiting_condition,
    )
    db.add(cov)
    db.flush()
    counters["coverages"] += 1
    return cov.coverage_id


def _copy_terms(db: Session, archived: Session, *, old_clause_id: int, new_clause: Clause, counters: dict):
    """조항의 수치 조건을 함께 옮긴다.

    raw_text는 반드시 조항 원문의 부분 문자열이어야 한다는 규칙(raw_text_is_grounded)은
    옮길 때도 그대로 지킨다 — 원문에 없는 조각이 근거로 붙으면 안 된다."""
    for old_term in archived.query(ClauseTerm).filter(ClauseTerm.clause_id == old_clause_id).all():
        if old_term.raw_text and not raw_text_is_grounded(new_clause.text, old_term.raw_text):
            continue
        db.add(ClauseTerm(
            clause_id=new_clause.clause_id, term_type=old_term.term_type, value_num=old_term.value_num,
            unit=old_term.unit, basis=old_term.basis, condition_text=old_term.condition_text,
            raw_text=old_term.raw_text,
        ))
        counters["terms"] += 1


def merge_archived(db: Session, archived_db_path: str, *, edition_label: str = DEFAULT_EDITION_LABEL) -> dict:
    """이전 판 DB에서 현재 판의 빈칸만 메운다. 넣은 행 수를 돌려준다(커밋은 호출부가 한다)."""
    counters = {"clauses": 0, "maps": 0, "coverages": 0, "terms": 0}

    engine = create_engine(f"sqlite:///{archived_db_path}")
    archived = sessionmaker(bind=engine)()
    try:
        current_insurers = _insurer_index(db)
        archived_insurers = _insurer_index(archived)
        filled = _mapped_pairs(db)
        # 같은 실행 안에서 방금 채운 자리를 다시 채우지 않도록 함께 본다.
        valid_type_ids = {t.type_id for t in db.query(IncidentType).all()}

        old_rows = (
            archived.query(
                ClauseIncidentMap.type_id, ClauseIncidentMap.relevance, ClauseIncidentMap.confidence,
                Clause.clause_id, Clause.coverage_id, Clause.clause_type, Clause.article_no,
                Clause.text, Clause.page_ref, Clause.default_color, Product.insurer_id,
            )
            .join(Clause, Clause.clause_id == ClauseIncidentMap.clause_id)
            .join(PolicyVersion, PolicyVersion.policy_version_id == Clause.policy_version_id)
            .join(Product, Product.product_id == PolicyVersion.product_id)
            .order_by(ClauseIncidentMap.map_id).all()
        )
        old_maps = [
            (r.type_id, r.relevance, r.confidence,
             ArchivedClause(r.clause_id, r.coverage_id, r.clause_type, r.article_no,
                            r.text, r.page_ref, r.default_color),
             r.insurer_id)
            for r in old_rows
        ]

        # 이전 판 조항 하나가 여러 사고유형에 매핑돼 있을 수 있다 — 그때 조항은 한 번만 만든다.
        imported_clause_ids: dict[int, int] = {}

        for map_type_id, map_relevance, map_confidence, old_clause, old_insurer_id in old_maps:
            name = next((n for n, i in archived_insurers.items() if i == old_insurer_id), None)
            insurer_id = current_insurers.get(name) if name else None
            if insurer_id is None or map_type_id not in valid_type_ids:
                continue
            if (insurer_id, map_type_id) in filled:
                continue  # 현재 판에 이미 근거가 있다 — 건드리지 않는다.

            pv = _primary_policy_version(db, insurer_id)
            if pv is None:
                continue

            new_clause_id = imported_clause_ids.get(old_clause.clause_id)
            if new_clause_id is None:
                # 같은 보험사에 같은 문장이 이미 있으면 그것을 쓴다(중복 조항 방지).
                twin = (
                    db.query(Clause)
                    .filter(Clause.policy_version_id == pv.policy_version_id, Clause.text == old_clause.text)
                    .first()
                )
                if twin is not None:
                    new_clause_id = twin.clause_id
                else:
                    coverage_id = _resolve_target_coverage(
                        db, archived, old_clause=old_clause,
                        policy_version_id=pv.policy_version_id, counters=counters,
                    )
                    new_clause = Clause(
                        policy_version_id=pv.policy_version_id, coverage_id=coverage_id,
                        clause_type=old_clause.clause_type, article_no=old_clause.article_no,
                        text=old_clause.text, page_ref=old_clause.page_ref,
                        default_color=old_clause.default_color, source_edition=edition_label,
                    )
                    db.add(new_clause)
                    db.flush()
                    counters["clauses"] += 1
                    _copy_terms(db, archived, old_clause_id=old_clause.clause_id,
                                new_clause=new_clause, counters=counters)
                    new_clause_id = new_clause.clause_id
                imported_clause_ids[old_clause.clause_id] = new_clause_id

            already = (
                db.query(ClauseIncidentMap)
                .filter(ClauseIncidentMap.clause_id == new_clause_id,
                        ClauseIncidentMap.type_id == map_type_id)
                .first()
            )
            if already is not None:
                continue
            db.add(ClauseIncidentMap(
                clause_id=new_clause_id, type_id=map_type_id, relevance=map_relevance,
                mapped_by=f"archived:{edition_label}", confidence=map_confidence,
            ))
            db.flush()
            counters["maps"] += 1

        return counters
    finally:
        archived.close()
        engine.dispose()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archived_db", help="이전 판 약관이 담긴 SQLite 파일 경로")
    parser.add_argument("--edition-label", default=DEFAULT_EDITION_LABEL)
    parser.add_argument("--confirm", action="store_true", help="실제로 반영한다(없으면 미리보기)")
    args = parser.parse_args(argv)

    # 스키마 마이그레이션(clause.source_edition 추가 등)은 app.main을 불러올 때 실행된다.
    # 이 도구는 서버를 거치지 않고 DB를 직접 고치므로, 여기서 한 번 통과시켜 둔다.
    import app.main  # noqa: F401

    db = SessionLocal()
    try:
        counters = merge_archived(db, args.archived_db, edition_label=args.edition_label)
        print(f"조항 {counters['clauses']}건, 매핑 {counters['maps']}건, "
              f"담보 {counters['coverages']}건, 수치조건 {counters['terms']}건을 이전 판에서 들여온다.")
        if args.confirm:
            db.commit()
            print("반영 완료.")
        else:
            db.rollback()
            print("--confirm 없이 실행했으므로 되돌렸다.")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
