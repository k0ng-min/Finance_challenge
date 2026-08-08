"""서류별 '약관에 실제로 적힌 요건'을 시드한다.

    python -m app.seed_doc_requirements

왜 데이터로 두는가: 화면에서 이 요건을 "약관이 요구하는 것"이라고 조항 원문과 함께 인용한다.
코드에 문자열로 박아두면 약관을 다시 시드했을 때 원문과 어긋나도 아무도 모른다. 그래서
seed_overlap_rules와 같은 방식을 쓴다 — 행마다 근거 조항을 조회해 붙이고, anchor_phrase가
그 조항 원문의 부분 문자열이 아니면 예외를 던지고 롤백한다.

지금 넣는 요건은 두 가지뿐이다. 6개사 약관 제7조를 읽어 실제로 적혀 있는 것만 골랐다.

  - 사고증명서(진료비계산서·세부내역서·입원치료확인서·처방전·장해진단서·사망진단서)
    → "의료기관에서 발급한 것이어야" (제7조 ②항)
      해외 서류를 정면으로 다루는 조항이라, 외국 병원 서류를 볼 때 바로 쓸 수 있다.
  - 신분증 → "사진이 붙은 정부기관발행" (제7조 ①항 3호)

금액·진료일자·환자명 같은 항목은 약관 어디에도 없다. 그건 근거가 없으므로 여기 넣지 않고
services/doc_verify_gemini.py의 PRACTICAL_CHECKS에 따로 두며, 화면에서도 칸을 나눠
"약관 근거는 아니에요"라고 밝힌다.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.models.kb import Clause, DocRequirement, RequiredDocStd

Base.metadata.create_all(bind=engine)

# (요건코드, 화면 표시 라벨, 조항에서 찾을 문구, 이 요건이 붙는 서류 코드들)
REQUIREMENTS: list[tuple[str, str, str, tuple[str, ...]]] = [
    (
        "ISSUER_MEDICAL",
        "의료기관이 발급한 서류",
        "의료기관에서 발급한 것이어야",
        (
            "MEDICAL_EXPENSE_CERT",
            "MEDICAL_DETAIL_CERT",
            "TREATMENT_CERT",
            "PRESCRIPTION",
            "DISABILITY_CERT",
            "DEATH_CERT",
        ),
    ),
    (
        "PHOTO_GOV_ID",
        "사진이 붙은 정부기관 발행 신분증",
        "사진이 붙은 정부기관발행 신분증",
        ("ID_CARD",),
    ),
]


def _find_clause(db: Session, phrase: str) -> Clause | None:
    """문구를 실제로 담고 있는 조항을 찾는다. 여러 보험사에 같은 문구가 있으면 가장 앞의
    하나를 근거로 쓴다 — 어느 보험사 약관에도 같은 취지로 적혀 있다는 뜻이라 대표로 충분하다."""
    return (
        db.query(Clause)
        .filter(Clause.clause_type == "서류", Clause.text.contains(phrase))
        .order_by(Clause.clause_id)
        .first()
    )


def seed(db: Session) -> int:
    db.query(DocRequirement).delete()
    inserted = 0

    for code, label, phrase, doc_codes in REQUIREMENTS:
        clause = _find_clause(db, phrase)
        if clause is None:
            raise RuntimeError(
                f"[{code}] 근거 조항을 찾지 못했습니다: '{phrase}'. "
                "약관 시드가 끝난 뒤에 이 스크립트를 실행하세요."
            )
        # 조회로 찾았으니 당연히 들어 있지만, 조회 조건이 바뀌어도 이 불변식이 깨지지 않도록
        # 저장 직전에 한 번 더 대조한다(ClauseTerm.raw_text와 같은 규칙).
        if phrase not in clause.text:
            raise RuntimeError(f"[{code}] anchor_phrase가 조항 원문에 없습니다: '{phrase}'")

        for doc_code in doc_codes:
            doc = db.query(RequiredDocStd).filter_by(doc_code=doc_code).first()
            if doc is None:
                raise RuntimeError(f"[{code}] 표준서류를 찾지 못했습니다: {doc_code}")
            db.add(DocRequirement(
                required_doc_std_id=doc.required_doc_std_id,
                code=code,
                label=label,
                anchor_phrase=phrase,
                clause_id=clause.clause_id,
            ))
            inserted += 1

    return inserted


def main() -> None:
    db = SessionLocal()
    try:
        count = seed(db)
        db.commit()
        print(f"doc_requirement {count}건 시드 완료")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
