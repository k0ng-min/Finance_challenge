"""기존보험 × 여행자보험 담보의 중복 판정 규칙을 시드한다.

판정을 코드에 숨기지 않고 데이터로 두는 이유: 행마다 근거 조항을 물려야 근거 없는 판정이
구조적으로 불가능해진다. relation이 UNKNOWN이 아닌 규칙은 반드시 실제 clause를 찾아 붙이고,
못 찾으면(strict=True) 예외를 던진다 — 조용히 빠뜨리면 근거 없이 단정하는 결과가 나간다.

clause_id를 상수로 박지 않는 이유: 약관을 재시드하면 id가 어긋난다. 보험사명과 조항 제목
조각으로 조회한다.

    python -m app.seed_overlap_rules
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.external import OverlapRule
from app.models.kb import Clause, Coverage, CoverageStd, Insurer, PolicyVersion, Product

#: 각 규칙의 근거 조항은 (보험사명 조각, 조항 제목 조각)으로 찾는다.
RULE_SPECS: list[dict] = [
    {
        "external_kind": "MEDICAL_INDEMNITY",
        "coverage_std_code": "OVS_INJ_MED",
        "scope": "해외 의료기관",
        "relation": "NO_OVERLAP",
        "clause_lookup": ("삼성화재", "(1)상해-해외의료비"),
        "note": "기존 실손의료보험은 국내 의료기관 진료만 보상한다. 해외 현지에서 쓴 상해 치료비는 "
                "여행자보험에서만 나오므로 이 담보는 여전히 필요하다.",
    },
    {
        "external_kind": "MEDICAL_INDEMNITY",
        "coverage_std_code": "OVS_ILL_MED",
        "scope": "해외 의료기관",
        "relation": "NO_OVERLAP",
        "clause_lookup": ("삼성화재", "(2)질병의료비-해외"),
        "note": "해외 현지 질병 치료비도 기존 실손으로는 보상받지 못한다.",
    },
    {
        "external_kind": "MEDICAL_INDEMNITY",
        "coverage_std_code": "OVS_ILL_MED",
        "scope": "국내 의료기관",
        "relation": "PARTIAL",
        "clause_lookup": ("삼성화재", "국내 의료기관 의료비"),
        "note": "귀국 후 국내에서 이어 받는 치료는 기존 실손과 겹친다. 실제 부담한 금액을 넘겨 "
                "이중으로 받지는 못한다.",
    },
    {
        "external_kind": "DAILY_LIABILITY",
        "coverage_std_code": "LIABILITY",
        "scope": "전체",
        "relation": "DUPLICATE_PRORATA",
        "clause_lookup": ("삼성화재", "의무보험과의 관계"),
        "note": "기존 일상생활배상책임 특약과 겹친다. 초과액만 보상하므로 두 개를 들어도 "
                "받는 총액이 늘지 않는다.",
    },
    {
        "external_kind": "ACCIDENT",
        "coverage_std_code": "DEATH_INJURY",
        "scope": "전체",
        "relation": "DUPLICATE_FIXED",
        # 실제 article_no는 "상해사망"을 포함하지 않는다(예: "상해 사망위험 보상제외 특별약관
        # 제1조" — 사이에 공백이 있고 게다가 보상"제외" 특약이라 이 규칙 취지와 반대).
        # 상해사망·후유장해 보통약관의 지급사유 조항(clause_id=1, coverage_std_id=1)이
        # 실제 정액 지급 근거이므로 이 조각으로 조회한다.
        "clause_lookup": ("삼성화재", "보험금의 지급사유"),
        "note": "정액 지급 담보라 기존 상해보험과 겹쳐도 각각 다 받는다. 실손형과 달리 "
                "중복가입이 손해가 아니다.",
    },
    {
        "external_kind": "OTHER",
        "coverage_std_code": "PASSPORT_LOSS",
        "scope": "전체",
        "relation": "DUPLICATE_PRORATA",
        # 삼성화재 여권분실 특약의 조항(clause_id=98)은 실제로 이 규칙과 정확히 일치하는
        # 비례분담 문구("다른 계약이... 비율에 따라 보험금을 지급합니다")를 담고 있지만,
        # 그 article_no가 "제1조(보상하는 손해)"뿐이라 삼성화재의 다른 8개 특약(항공기납치 등,
        # clause_id 72부터 시작)과 글자 그대로 동일하다 — article_no만으로는 clause_id
        # 오름차순 조회가 항상 더 앞선(무관한) 특약을 집어와 근거를 잘못 붙이게 된다.
        # 현대해상은 여권분실 특약 article_no에 "[여권분실]" 접두어를 붙여 놓아 고유하게
        # 조회되므로(clause_id=253) 이쪽으로 바꾼다.
        "clause_lookup": ("현대해상", "여권분실"),
        "note": "보험금을 지급할 다른 계약이 있으면 비율에 따라 나눠 지급한다.",
    },
    {
        "external_kind": "OTHER",
        "coverage_std_code": "HIJACK",
        "scope": "전체",
        "relation": "DUPLICATE_PRORATA",
        "clause_lookup": ("현대해상", "다른 보험과의 관계"),
        "note": "유사한 다수 계약이 있으면 그중 하나에서만 보상하고, 나머지 계약의 보험료는 "
                "돌려받는다.",
    },
]


def _find_clause(db: Session, insurer_frag: str, article_frag: str) -> Clause | None:
    """보험사명·조항 제목 조각으로 근거 조항을 찾는다. 여러 개면 가장 앞선 것을 쓴다."""
    return (
        db.query(Clause)
        .join(PolicyVersion, PolicyVersion.policy_version_id == Clause.policy_version_id)
        .join(Product, Product.product_id == PolicyVersion.product_id)
        .join(Insurer, Insurer.insurer_id == Product.insurer_id)
        .filter(Insurer.name.like(f"%{insurer_frag}%"))
        .filter(Clause.article_no.like(f"%{article_frag}%"))
        .order_by(Clause.clause_id)
        .first()
    )


def seed_overlap_rules(db: Session, *, strict: bool = True) -> int:
    """규칙을 다시 심는다. 기존 행은 지우고 새로 넣는다(멱등).

    strict=True면 근거 조항을 못 찾은 규칙에서 예외를 던진다. 운영 시드는 반드시 strict로
    돌린다 — 근거를 못 찾았는데 넘어가면 판정만 남고 근거가 사라진다.
    """
    db.query(OverlapRule).delete()

    inserted = 0
    missing: list[str] = []
    for spec in RULE_SPECS:
        std = (
            db.query(CoverageStd)
            .filter(CoverageStd.std_code == spec["coverage_std_code"])
            .first()
        )
        if std is None:
            missing.append(f"표준담보 없음: {spec['coverage_std_code']}")
            continue

        clause = None
        if spec["relation"] != "UNKNOWN":
            clause = _find_clause(db, *spec["clause_lookup"])
            if clause is None:
                missing.append(
                    f"근거 조항 없음: {spec['coverage_std_code']} / {spec['clause_lookup']}"
                )
                continue

        db.add(OverlapRule(
            external_kind=spec["external_kind"],
            coverage_std_id=std.coverage_std_id,
            scope=spec["scope"],
            relation=spec["relation"],
            clause_id=clause.clause_id if clause else None,
            note=spec["note"],
        ))
        inserted += 1

    if missing and strict:
        db.rollback()
        raise RuntimeError("근거를 찾지 못한 규칙이 있습니다:\n  " + "\n  ".join(missing))

    db.commit()
    return inserted


def main() -> None:
    db = SessionLocal()
    try:
        count = seed_overlap_rules(db)
        print(f"중복 판정 규칙 {count}건 시드 완료")
    finally:
        db.close()


if __name__ == "__main__":
    main()
