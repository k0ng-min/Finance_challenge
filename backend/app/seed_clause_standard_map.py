"""보험사 조항 ↔ 표준약관(해외여행 실손의료보험) 조항 대응 판정 시드.

overlap_rule과 같은 원칙: 판정을 코드가 아니라 행 데이터로 두고, 앵커 문구가 원문에
없으면(양쪽 다) 예외를 던지고 롤백한다. clause_id를 상수로 박지 않고 (보험사명, 조항
제목 조각, 표준담보, 조항종류)로 조회한다 — 약관을 재시드해도 어긋나지 않도록.

MVP 범위(제3·4조)만 다룬다. 6개사 전부 제3조(해외 상해의료비)는 grounding이 가능했지만,
제4조(전쟁·내란 면책)는 실손의료비 특약 자체에 이 문구를 반복해 담은 3개사(DB·현대·삼성)
에서만 근거 조항을 찾았다 — 카카오페이·KB·메리츠는 이 특약에서 전쟁 면책을 별도로
반복하지 않거나(상해사망 보통약관에서만 규정) 근거를 못 찾아 행을 만들지 않았다.
'대응 조항 없음'이라고 단정하지 않고 조용히 빠뜨린다 — 근거 없이 MISSING_IN_INSURER로
단정하면 그것 역시 근거 없는 판정이기 때문이다. 매핑 커버리지는
docs/compliance/source_register.md에 기록한다.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.models.kb import Clause, ClauseStandardMap, Coverage, CoverageStd, Insurer, PolicyVersion, Product, StandardClause
from app.services.kb_seed_common import raw_text_is_grounded

Base.metadata.create_all(bind=engine)

STANDARD_NAME = "해외여행 실손의료보험"

RULE_SPECS = [
    # --- 제3조(보장종목별 보상내용) — 해외 상해의료비. 6개사 전부 표준 문구를 사실상
    # 그대로 옮겨 썼다(치료받는 국가 법정 병원·의사 자격, 보험가입금액 한도 등은 표준
    # 제5조가 별도 규정하는 내용과 부합하므로 범위를 넓히거나 좁히지 않는다).
    {
        "insurer_frag": "삼성", "article_no": "제3조", "clause_lookup": "해외의료비",
        "coverage_std_code": "OVS_INJ_MED", "clause_type": "보장정의", "relation": "SAME",
        "anchor_insurer": "보험가입금액을 한도로 피보험자가 실제 부담한 의료비 전액을 보상합니다",
        "note": "해외 상해의료비 보상 취지가 표준약관 제3조와 실질적으로 동일. "
                "치료받는 국가 법정 병원·의사 요건 등은 절차적 부연일 뿐 보장 범위를 넓히거나 좁히지 않음.",
    },
    {
        "insurer_frag": "현대", "article_no": "제3조", "clause_lookup": "해외의료비",
        "coverage_std_code": "OVS_INJ_MED", "clause_type": "보장정의", "relation": "SAME",
        "anchor_insurer": "보험가입금액을 한도로 피보험자가 실제 부담한 의료비 전액을 보상합니다",
        "note": "해외 상해의료비 보상 취지가 표준약관 제3조와 실질적으로 동일.",
    },
    {
        "insurer_frag": "카카오페이", "article_no": "제3조", "clause_lookup": "해외의료비",
        "coverage_std_code": "OVS_INJ_MED", "clause_type": "보장정의", "relation": "SAME",
        "anchor_insurer": "보험가입금액을 한도로 피보험자가 실제 부담한 의료비 전액을 보상합니다",
        "note": "해외 상해의료비 보상 취지가 표준약관 제3조와 실질적으로 동일.",
    },
    {
        "insurer_frag": "KB", "article_no": "제3조", "clause_lookup": "해외의료비",
        "coverage_std_code": "OVS_INJ_MED", "clause_type": "보장정의", "relation": "SAME",
        "anchor_insurer": "보험가입금액을 한도로 피보험자가 실제 부담한 의료비 전액을 보상합니다",
        "note": "해외 상해의료비 보상 취지가 표준약관 제3조와 실질적으로 동일.",
    },
    {
        "insurer_frag": "메리츠", "article_no": "제3조", "clause_lookup": "상해의료비 해외",
        "coverage_std_code": "OVS_INJ_MED", "clause_type": "보장정의", "relation": "SAME",
        "anchor_insurer": "보험가입금액을 한도로 피보험자가 실제 부담한 의료비 전액을 보상합니다",
        "note": "해외 상해의료비 보상 취지가 표준약관 제3조와 실질적으로 동일.",
    },
    {
        "insurer_frag": "DB", "article_no": "제3조", "clause_lookup": "해외의료비",
        "coverage_std_code": "OVS_INJ_MED", "clause_type": "보장정의", "relation": "SAME",
        "anchor_insurer": "보험가입금액을 한도로 피보험자가 실제 부담한 의료비 전액을 보상합니다",
        "note": "해외 상해의료비 보상 취지가 표준약관 제3조와 실질적으로 동일.",
    },
    # --- 제4조(보상하지 않는 사항) — 전쟁·내란 면책. 실손의료비 특약 자체에 이 문구를
    # 반복해 담은 보험사만(근거 조항을 직접 찾은 경우만) 매핑한다.
    {
        "insurer_frag": "삼성", "article_no": "제4조", "clause_lookup": "해외의료비",
        "coverage_std_code": "OVS_INJ_MED", "clause_type": "면책", "relation": "SAME",
        "anchor_insurer": "전쟁, 외국의 무력행사, 혁명, 내란, 사변, 폭동으로 인한 경우",
        "note": "전쟁·내란 면책 문구가 표준약관 제4조 ①5호와 자구까지 동일.",
    },
    {
        "insurer_frag": "현대", "article_no": "제4조", "clause_lookup": "전쟁",
        "coverage_std_code": "OVS_INJ_MED", "clause_type": "면책", "relation": "SAME",
        "anchor_insurer": "전쟁, 외국의 무력행사, 혁명, 내란, 사변, 폭동으로 인한 경우",
        "note": "전쟁·내란 면책 문구가 표준약관 제4조 ①5호와 자구까지 동일.",
    },
    {
        "insurer_frag": "DB", "article_no": "제4조", "clause_lookup": "전쟁",
        "coverage_std_code": "OVS_INJ_MED", "clause_type": "면책", "relation": "SAME",
        "anchor_insurer": "전쟁, 외국의 무력행사, 혁명, 내란, 사변, 폭동으로 인한 경우",
        "note": "전쟁·내란 면책 문구가 표준약관 제4조 ①5호와 자구까지 동일.",
    },
]

ARTICLE_ANCHOR = {
    "제3조": "해외의료기관주1)에서 의료비가 발생한 경우에 보상",
    "제4조": "전쟁, 외국의 무력행사, 혁명, 내란, 사변, 폭동으로 인한 경우",
}


def _find_clause(db: Session, insurer_frag: str, clause_lookup_frag: str, coverage_std_code: str, clause_type: str) -> Clause | None:
    return (
        db.query(Clause)
        .join(PolicyVersion, PolicyVersion.policy_version_id == Clause.policy_version_id)
        .join(Product, Product.product_id == PolicyVersion.product_id)
        .join(Insurer, Insurer.insurer_id == Product.insurer_id)
        .join(Coverage, Coverage.coverage_id == Clause.coverage_id)
        .join(CoverageStd, CoverageStd.coverage_std_id == Coverage.coverage_std_id)
        .filter(Insurer.name.like(f"%{insurer_frag}%"))
        .filter(Clause.article_no.like(f"%{clause_lookup_frag}%"))
        .filter(CoverageStd.std_code == coverage_std_code)
        .filter(Clause.clause_type == clause_type)
        .order_by(Clause.clause_id)
        .first()
    )


def seed_clause_standard_map(db: Session, *, strict: bool = True) -> int:
    """다시 심는다(멱등) — 기존 행은 지우고 새로 넣는다."""
    db.query(ClauseStandardMap).delete()

    standard_clauses = {
        s.article_no: s
        for s in db.query(StandardClause).filter(StandardClause.standard_name == STANDARD_NAME).all()
    }
    if not standard_clauses:
        raise RuntimeError("standard_clause가 비어 있습니다. seed_standard_clauses를 먼저 실행하세요.")

    inserted = 0
    missing: list[str] = []
    for spec in RULE_SPECS:
        standard = standard_clauses.get(spec["article_no"])
        if standard is None:
            missing.append(f"표준조문 없음: {spec['article_no']}")
            continue

        clause = _find_clause(
            db, spec["insurer_frag"], spec["clause_lookup"], spec["coverage_std_code"], spec["clause_type"]
        )
        if clause is None:
            missing.append(f"근거 조항 없음: {spec['insurer_frag']} / {spec['article_no']} / {spec['clause_lookup']}")
            continue

        insurer = (
            db.query(Insurer).join(Product).join(PolicyVersion)
            .filter(PolicyVersion.policy_version_id == clause.policy_version_id).first()
        )

        anchor_standard = ARTICLE_ANCHOR[spec["article_no"]]
        anchor_insurer = spec["anchor_insurer"]

        if not raw_text_is_grounded(standard.text, anchor_standard):
            missing.append(f"표준 조문 앵커 근거 없음: {spec['article_no']} / {anchor_standard!r}")
            continue
        if not raw_text_is_grounded(clause.text, anchor_insurer):
            missing.append(f"보험사 조항 앵커 근거 없음: {insurer.code if insurer else '?'} / {clause.clause_id} / {anchor_insurer!r}")
            continue

        db.add(ClauseStandardMap(
            standard_clause_id=standard.standard_clause_id,
            insurer_id=insurer.insurer_id,
            clause_id=clause.clause_id,
            relation=spec["relation"],
            anchor_phrase_standard=anchor_standard,
            anchor_phrase_insurer=anchor_insurer,
            note=spec["note"],
        ))
        inserted += 1

    if missing and strict:
        db.rollback()
        raise RuntimeError("clause_standard_map 시드 실패:\n" + "\n".join(missing))

    db.commit()
    if missing:
        print("건너뜀(근거 없음, strict=False):\n" + "\n".join(missing))
    return inserted


def run():
    db = SessionLocal()
    try:
        n = seed_clause_standard_map(db, strict=True)
        print(f"clause_standard_map {n}건 시드 완료.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
