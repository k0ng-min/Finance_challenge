"""기존보험 × 여행자보험 담보의 중복 판정 규칙을 시드한다.

판정을 코드에 숨기지 않고 데이터로 두는 이유: 행마다 근거 조항을 물려야 근거 없는 판정이
구조적으로 불가능해진다. relation이 UNKNOWN이 아닌 규칙은 반드시 실제 clause를 찾아 붙이고,
못 찾으면(strict=True) 예외를 던진다 — 조용히 빠뜨리면 근거 없이 단정하는 결과가 나간다.

clause_id를 상수로 박지 않는 이유: 약관을 재시드하면 id가 어긋난다. 보험사명과 조항 제목
조각으로 조회한다.

    python -m app.seed_overlap_rules
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.models.external import OverlapRule
from app.models.kb import Clause, Coverage, CoverageStd, Insurer, PolicyVersion, Product

# 다른 seed_*.py와 동일한 관례: 이 스크립트를 처음 돌리는 환경(테이블이 아직 없는 운영 DB 등)에서도
# 재현 가능하도록 모듈 로드 시 누락된 테이블을 만든다. 이미 있는 테이블은 건드리지 않는다.
Base.metadata.create_all(bind=engine)


def _add_missing_columns(table: str, additions: dict[str, str]) -> None:
    """SQLAlchemy는 기존 테이블에 새 컬럼을 자동 추가하지 않는다. app/main.py의 앱 기동
    마이그레이션과 같은 방식을 이 스크립트에도 둔다 — `python -m app.seed_overlap_rules`를
    서버 기동 없이 단독으로 돌리는 경우가 있어서, main.py의 마이그레이션에만 기대면
    이 스크립트가 구 스키마의 app.db에서 실패한다."""
    with engine.connect() as conn:
        existing = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}
        for col, ddl in additions.items():
            if col not in existing:
                conn.execute(text(ddl))
        conn.commit()


_add_missing_columns("overlap_rule", {
    "anchor_phrase": "ALTER TABLE overlap_rule ADD COLUMN anchor_phrase VARCHAR",
})

#: 각 규칙의 근거 조항은 (보험사명 조각, 조항 제목 조각)으로 찾는다.
#: anchor_phrase: note가 근거로 삼는 조항 원문 속 핵심 문구. clause.text가 길어 인용문이
#: 잘려야 할 때 이 문구를 포함하는 창을 잘라내는 데 쓴다(coverage_overlap._quote 참고).
#: relation이 UNKNOWN이 아니면 반드시 있어야 하고, seed_overlap_rules()가 실제 clause.text의
#: 부분 문자열인지 검증한다(strict=True에서 못 찾으면 예외).
RULE_SPECS: list[dict] = [
    {
        "external_kind": "MEDICAL_INDEMNITY",
        "coverage_std_code": "OVS_INJ_MED",
        "scope": "해외 의료기관",
        "relation": "UNKNOWN",
        # 이전에는 clause_id=4(삼성화재 여행자보험 제3조)를 근거로 "기존 실손은 국내
        # 의료기관 진료만 보상한다"고 단정했다. 하지만 clause 4는 *이 여행자보험 상품*이
        # 해외의료기관 치료비를 보상한다는 조항일 뿐, 사용자가 기존에 든 실손의료보험의
        # 보장 범위를 말하지 않는다. 실손 표준약관은 이 DB에 없어 그 주장을 뒷받침할
        # 근거가 없다 — 근거 없이 단정하지 않고 확인불가로 내린다.
        "note": "기존 실손의료보험의 보장 범위를 확인할 약관 근거를 확보하지 못했습니다. "
                "실손 표준약관 확보 후 판정 예정입니다.",
    },
    {
        "external_kind": "MEDICAL_INDEMNITY",
        "coverage_std_code": "OVS_ILL_MED",
        "scope": "해외 의료기관",
        "relation": "UNKNOWN",
        # 위와 같은 이유(근거 clause 75도 이 여행자보험 상품 자체의 보장 조항일 뿐 기존
        # 실손의 보장 범위를 말하지 않는다).
        "note": "기존 실손의료보험의 보장 범위를 확인할 약관 근거를 확보하지 못했습니다. "
                "실손 표준약관 확보 후 판정 예정입니다.",
    },
    {
        "external_kind": "MEDICAL_INDEMNITY",
        "coverage_std_code": "OVS_ILL_MED",
        "scope": "국내 의료기관",
        "relation": "PARTIAL",
        "clause_lookup": ("삼성화재", "국내 의료기관 의료비"),
        "anchor_phrase": "실제 본인이 부담한 의료비",
        "note": "귀국 후 국내에서 이어 받는 치료는 기존 실손과 겹친다. 실제 부담한 금액을 넘겨 "
                "이중으로 받지는 못한다.",
    },
    {
        "external_kind": "DAILY_LIABILITY",
        "coverage_std_code": "LIABILITY",
        "scope": "전체",
        "relation": "UNKNOWN",
        # 이전에는 clause_id=67(삼성화재 "의무보험과의 관계")을 근거로 "일상생활배상책임
        # 특약과 겹친다"고 단정했다. 하지만 clause 67 ②항은 "의무보험"을 "법률에 의하여
        # 의무적으로 가입하여야 하는 보험"으로 직접 정의한다 — 일상생활배상책임은 의무보험이
        # 아니므로 이 조항은 그 관계를 다루지 않는다. 근거가 없어 확인불가로 내린다.
        "note": "일상생활배상책임 특약과의 관계를 확인할 약관 근거를 확보하지 못했습니다. "
                "찾은 조항(의무보험과의 관계)은 일상생활배상책임에 적용되지 않습니다.",
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
        "anchor_phrase": "약정한 보험금을 지급합니다",
        "note": "정액 지급 담보라 기존 상해보험과 겹쳐도 각각 다 받는다. 실손형과 달리 "
                "중복가입이 손해가 아니다.",
    },
    {
        # 여권분실은 기존보험 종류와 무관하게 "다른 계약과의 비례분담" 조항이 적용된다 —
        # 실손이든 상해든 일상배상책임이든 상관없이 매칭돼야 한다. 예전에는 external_kind를
        # "OTHER"로 넣어서 사용자가 칩에서 "그 외"를 명시적으로 골라야만 매칭됐다(설계 §4는
        # 이 규칙을 (any)로 정의한다). 'ANY'는 diagnose()가 사용자가 고른 종류와 무관하게
        # 항상 매칭하도록 넓혀 조회하는 센티널이다(coverage_overlap.diagnose 참고).
        "external_kind": "ANY",
        "coverage_std_code": "PASSPORT_LOSS",
        "scope": "전체",
        "relation": "DUPLICATE_PRORATA",
        # 삼성화재 여권분실 특약의 조항(clause_id=98)은 이 규칙의 note와 글자 그대로 일치하는
        # 비례분담 문구("다른 계약이... 비율에 따라 보험금을 지급합니다")를 담고 있다. 다만
        # article_no가 "제1조(보상하는 손해)"뿐이라 삼성화재의 다른 8개 특약(항공기납치 등,
        # clause_id 72부터 시작)과 글자 그대로 동일하다 — article_no만 보면 clause_id
        # 오름차순 조회가 더 앞선(무관한) 특약을 집어올 수 있다. 그래서 _find_clause에
        # coverage_std_id 필터를 추가해 PASSPORT_LOSS 담보에 실제로 연결된 조항(98)만
        # 골라내도록 했다(아래 _find_clause 참조).
        "clause_lookup": ("삼성화재", "보상하는 손해"),
        "anchor_phrase": "비율에 따라",
        "note": "보험금을 지급할 다른 계약이 있으면 비율에 따라 나눠 지급한다.",
    },
    {
        # HIJACK도 PASSPORT_LOSS와 같은 이유로 (any) — 기존보험 종류와 무관하게 적용된다.
        "external_kind": "ANY",
        "coverage_std_code": "HIJACK",
        "scope": "전체",
        "relation": "DUPLICATE_PRORATA",
        "clause_lookup": ("현대해상", "다른 보험과의 관계"),
        "anchor_phrase": "하나의 계약에서만 보상",
        "note": "유사한 다수 계약이 있으면 그중 하나에서만 보상하고, 나머지 계약의 보험료는 "
                "돌려받는다.",
    },
]


def _find_clause(
    db: Session, insurer_frag: str, article_frag: str, coverage_std_id: int
) -> Clause | None:
    """보험사명·조항 제목 조각 + 표준담보로 근거 조항을 찾는다.

    article_no만으로는 서로 다른 특약이 똑같은 제목("제1조(보상하는 손해)")을 재사용하는
    경우가 있다(예: 삼성화재의 여권분실·항공기납치 특약). coverage_std_id로 좁혀야 이럴 때
    엉뚱한 담보의 조항이 clause_id 순서상 먼저 걸려 잘못 붙는 것을 막을 수 있다.
    면책 조항(clause_type="면책")은 보장 내용 자체를 설명하지 않으므로 후보에서 제외한다
    — 같은 article_frag가 "보장정의"와 "면책" 조항 한 쌍에 동시에 걸리는 경우가 있어,
    이 필터가 없으면 어느 쪽이 먼저 걸릴지 clause_id 우연에 좌우된다.
    """
    return (
        db.query(Clause)
        .join(PolicyVersion, PolicyVersion.policy_version_id == Clause.policy_version_id)
        .join(Product, Product.product_id == PolicyVersion.product_id)
        .join(Insurer, Insurer.insurer_id == Product.insurer_id)
        .join(Coverage, Coverage.coverage_id == Clause.coverage_id)
        .filter(Insurer.name.like(f"%{insurer_frag}%"))
        .filter(Clause.article_no.like(f"%{article_frag}%"))
        .filter(Coverage.coverage_std_id == coverage_std_id)
        .filter(Clause.clause_type != "면책")
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
        anchor_phrase = None
        if spec["relation"] != "UNKNOWN":
            clause = _find_clause(db, *spec["clause_lookup"], coverage_std_id=std.coverage_std_id)
            if clause is None:
                missing.append(
                    f"근거 조항 없음: {spec['coverage_std_code']} / {spec['clause_lookup']}"
                )
                continue

            anchor_phrase = spec.get("anchor_phrase")
            if not anchor_phrase:
                missing.append(
                    f"anchor_phrase 없음: {spec['coverage_std_code']} — note의 핵심 주장을 "
                    "가리키는 문구가 없으면 인용문이 근거를 뒷받침하는지 검증할 수 없다."
                )
                continue
            if anchor_phrase not in clause.text:
                missing.append(
                    f"anchor_phrase가 조항 원문에 없음: {spec['coverage_std_code']} / "
                    f"'{anchor_phrase}' not in clause_id={clause.clause_id}"
                )
                continue

        db.add(OverlapRule(
            external_kind=spec["external_kind"],
            coverage_std_id=std.coverage_std_id,
            scope=spec["scope"],
            relation=spec["relation"],
            clause_id=clause.clause_id if clause else None,
            anchor_phrase=anchor_phrase,
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
