"""기존보험 × 여행자보험 담보의 중복 판정 규칙을 시드한다.

2026-08-18 약관 재구축 후 재작성. 판정을 코드에 숨기지 않고 데이터로 두는 이유:
행마다 근거 조항을 물려야 근거 없는 판정이 구조적으로 불가능해진다. relation이
UNKNOWN이 아닌 규칙은 반드시 실제 clause를 찾아 붙이고, anchor_phrase가 그 조항
원문의 부분 문자열이 아니면 예외를 던지고 롤백한다.

clause_id를 상수로 박아 쓰는 이유: 새 원문에서 각 앵커 문구가 정확히 어느 조항에
있는지 이미 전수 검색으로 확인했다(보험사명이 아니라 조항 내용 자체로 확인했으므로
구판본처럼 "보험사명+조항 제목 조각" 조회가 다른 특약을 잘못 집어올 위험이 없다).
약관을 다시 재구축하면 이 스크립트도 다시 손봐야 한다 — 그건 다른 시드들도 마찬가지다.

    python -m app.seed_overlap_rules
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.models.external import OverlapRule
from app.models.kb import Clause, CoverageStd

Base.metadata.create_all(bind=engine)

# (external_kind, coverage_std_code, scope, relation, clause_id 또는 None, anchor_phrase 또는 None, note)
RULE_SPECS: list[dict] = [
    {
        "external_kind": "MEDICAL_INDEMNITY",
        "coverage_std_code": "OVS_INJ_MED",
        "scope": "해외 의료기관",
        "relation": "UNKNOWN",
        "note": "기존 실손의료보험의 보장 범위를 확인할 약관 근거를 확보하지 못했습니다. "
                "실손 표준약관 확보 후 판정 예정입니다.",
    },
    {
        "external_kind": "MEDICAL_INDEMNITY",
        "coverage_std_code": "OVS_ILL_MED",
        "scope": "해외 의료기관",
        "relation": "UNKNOWN",
        "note": "기존 실손의료보험의 보장 범위를 확인할 약관 근거를 확보하지 못했습니다. "
                "실손 표준약관 확보 후 판정 예정입니다.",
    },
    {
        # 메리츠 <붙임3>(국내 의료기관 의료비 중 보상하는 질병의료비) — 귀국 후 국내
        # 치료도 실제 부담액 기준으로 보상한다는 조항. 기존 실손과 이중으로 받지 못한다.
        "external_kind": "MEDICAL_INDEMNITY",
        "coverage_std_code": "OVS_ILL_MED",
        "scope": "국내 의료기관",
        "relation": "PARTIAL",
        "clause_id": 898,
        "anchor_phrase": "실제 본인이 부담한 의료비",
        "note": "귀국 후 국내에서 이어 받는 치료는 기존 실손과 겹친다. 실제 부담한 금액을 넘겨 "
                "이중으로 받지는 못한다.",
    },
    {
        "external_kind": "DAILY_LIABILITY",
        "coverage_std_code": "LIABILITY",
        "scope": "전체",
        "relation": "UNKNOWN",
        "note": "일상생활배상책임 특약과의 관계를 확인할 약관 근거를 확보하지 못했습니다.",
    },
    {
        # 현대해상 보통약관 제3조(보험금의 지급사유) — 상해사망·후유장해 정액 지급 조항.
        "external_kind": "ACCIDENT",
        "coverage_std_code": "DEATH_INJURY",
        "scope": "전체",
        "relation": "DUPLICATE_FIXED",
        "clause_id": 49,
        "anchor_phrase": "약정한 보험금을 지급합니다",
        "note": "정액 지급 담보라 기존 상해보험과 겹쳐도 각각 다 받는다. 실손형과 달리 "
                "중복가입이 손해가 아니다.",
    },
    {
        # 메리츠 여권분실후 재발급비용 특별약관 제1조③ — 다른 계약과의 비례분담 조항.
        # 기존보험 종류와 무관하게 적용되므로 external_kind='ANY'(diagnose()가 사용자가
        # 고른 종류와 무관하게 항상 매칭하도록 넓혀 조회하는 센티널).
        "external_kind": "ANY",
        "coverage_std_code": "PASSPORT_LOSS",
        "scope": "전체",
        "relation": "DUPLICATE_PRORATA",
        "clause_id": 844,
        "anchor_phrase": "비율에 따라",
        "note": "보험금을 지급할 다른 계약이 있으면 비율에 따라 나눠 지급한다.",
    },
    {
        # 메리츠 항공기납치 특별약관 제3조(다른보험과의 관계).
        "external_kind": "ANY",
        "coverage_std_code": "HIJACK",
        "scope": "전체",
        "relation": "DUPLICATE_PRORATA",
        "clause_id": 837,
        "anchor_phrase": "하나의 계약에서만 보상",
        "note": "유사한 다수 계약이 있으면 그중 하나에서만 보상하고, 나머지 계약의 보험료는 "
                "돌려받는다.",
    },
]


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
            clause = db.query(Clause).filter_by(clause_id=spec["clause_id"]).first()
            if clause is None:
                missing.append(f"근거 조항 없음: {spec['coverage_std_code']} / clause_id={spec['clause_id']}")
                continue

            anchor_phrase = spec.get("anchor_phrase")
            if not anchor_phrase or anchor_phrase not in clause.text:
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
