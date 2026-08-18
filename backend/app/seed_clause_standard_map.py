"""보험사 조항 ↔ 표준약관(해외여행 실손의료보험) 조항 대응 판정 시드.

2026-08-18 약관 재구축 후 재작성. overlap_rule과 같은 원칙: 판정을 코드가 아니라 행
데이터로 두고, 앵커 문구가 원문에 없으면(양쪽 다) 예외를 던지고 롤백한다. clause_id를
직접 박아 쓰는 이유는 seed_overlap_rules.py와 같다 — 각 앵커 문구가 실제로 어느
조항에 있는지 전수 검색으로 이미 확인했다.

MVP 범위(제3·4조)만 다룬다. 새 원문 전수 검색 결과:
- 제3조(해외 상해의료비, "보험가입금액을 한도로 피보험자가 실제 부담한 의료비 전액을
  보상합니다"): 6개사 전부 확인(2026-08-19 현대의 "기본형 해외여행 급여 실손의료비보장"을
  OVS_INJ_MED/OVS_ILL_MED로 분리한 뒤 현대도 이 문구가 있음을 확인했다 — 분리 전에는
  OVS_MED_BASIC 하나로 묶여 있어 근거가 없었다).
- 제4조(전쟁·내란 면책, "전쟁, 외국의 무력행사, 혁명, 내란, 사변, 폭동으로 인한 경우"):
  삼성·현대·메리츠·KB·DB 5개사에서 확인(현대는 OVS_MED_BASIC 분리 후 확인). 카카오페이는
  실손의료비 특약 자체에 이 문구를 반복하지 않아(상해사망 보통약관에서만 규정하거나
  다른 표현을 씀) 근거 조항을 못 찾았다 — 단정하지 않는다.

매핑 커버리지는 docs/compliance/source_register.md에 기록한다.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.models.kb import Clause, ClauseStandardMap, Insurer, PolicyVersion, Product, StandardClause
from app.services.kb_seed_common import raw_text_is_grounded

Base.metadata.create_all(bind=engine)

STANDARD_NAME = "해외여행 실손의료보험"

ARTICLE_ANCHOR = {
    "제3조": "해외의료기관",
    "제4조": "전쟁, 외국의 무력행사, 혁명, 내란, 사변, 폭동으로 인한 경우",
}

# (article_no, clause_id, relation, anchor_insurer, note)
RULE_SPECS: list[dict] = [
    {
        "article_no": "제3조", "clause_id": 29, "relation": "SAME",
        "anchor_insurer": "보험가입금액을 한도로 피보험자가 실제 부담한 의료비 전액을 보상합니다",
        "note": "해외 상해의료비 보상 취지가 표준약관 제3조와 실질적으로 동일.",
    },
    {
        "article_no": "제3조", "clause_id": 884, "relation": "SAME",
        "anchor_insurer": "보험가입금액을 한도로 피보험자가 실제 부담한 의료비 전액을 보상합니다",
        "note": "해외 상해의료비 보상 취지가 표준약관 제3조와 실질적으로 동일.",
    },
    {
        "article_no": "제3조", "clause_id": 464, "relation": "SAME",
        "anchor_insurer": "보험가입금액을 한도로 피보험자가 실제 부담한 의료비 전액을 보상합니다",
        "note": "해외 상해의료비 보상 취지가 표준약관 제3조와 실질적으로 동일.",
    },
    {
        "article_no": "제3조", "clause_id": 647, "relation": "SAME",
        "anchor_insurer": "보험가입금액을 한도로 피보험자가 실제 부담한 의료비 전액을 보상합니다",
        "note": "해외 상해의료비 보상 취지가 표준약관 제3조와 실질적으로 동일.",
    },
    {
        "article_no": "제3조", "clause_id": 752, "relation": "SAME",
        "anchor_insurer": "보험가입금액을 한도로 피보험자가 실제 부담한 의료비 전액을 보상합니다",
        "note": "해외 상해의료비 보상 취지가 표준약관 제3조와 실질적으로 동일.",
    },
    {
        "article_no": "제3조", "clause_id": 52, "relation": "SAME",
        "anchor_insurer": "보험가입금액을 한도로 피보험자가 실제 부담한 의료비 전액을 보상합니다",
        "note": "해외 상해의료비 보상 취지가 표준약관 제3조와 실질적으로 동일(2026-08-19 "
                "OVS_MED_BASIC 분리 후 확인).",
    },
    {
        "article_no": "제4조", "clause_id": 30, "relation": "SAME",
        "anchor_insurer": "전쟁, 외국의 무력행사, 혁명, 내란, 사변, 폭동으로 인한 경우",
        "note": "전쟁·내란 면책 문구가 표준약관 제4조 ①5호와 자구까지 동일.",
    },
    {
        "article_no": "제4조", "clause_id": 54, "relation": "SAME",
        "anchor_insurer": "전쟁, 외국의 무력행사, 혁명, 내란, 사변, 폭동으로 인한 경우",
        "note": "전쟁·내란 면책 문구가 표준약관 제4조 ①5호와 자구까지 동일(2026-08-19 "
                "OVS_MED_BASIC 분리 후 확인).",
    },
    {
        "article_no": "제4조", "clause_id": 886, "relation": "SAME",
        "anchor_insurer": "전쟁, 외국의 무력행사, 혁명, 내란, 사변, 폭동으로 인한 경우",
        "note": "전쟁·내란 면책 문구가 표준약관 제4조 ①5호와 자구까지 동일.",
    },
    {
        "article_no": "제4조", "clause_id": 466, "relation": "SAME",
        "anchor_insurer": "전쟁, 외국의 무력행사, 혁명, 내란, 사변, 폭동으로 인한 경우",
        "note": "전쟁·내란 면책 문구가 표준약관 제4조 ①5호와 자구까지 동일.",
    },
    {
        "article_no": "제4조", "clause_id": 650, "relation": "SAME",
        "anchor_insurer": "전쟁, 외국의 무력행사, 혁명, 내란, 사변, 폭동으로 인한 경우",
        "note": "전쟁·내란 면책 문구가 표준약관 제4조 ①5호와 자구까지 동일.",
    },
]


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

        clause = db.query(Clause).filter_by(clause_id=spec["clause_id"]).first()
        if clause is None:
            missing.append(f"근거 조항 없음: {spec['article_no']} / clause_id={spec['clause_id']}")
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
            missing.append(
                f"보험사 조항 앵커 근거 없음: {insurer.code if insurer else '?'} / "
                f"{clause.clause_id} / {anchor_insurer!r}"
            )
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
