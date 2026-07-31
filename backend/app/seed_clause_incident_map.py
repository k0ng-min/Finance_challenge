"""
이미 DB에 시드된 조항(clause) ↔ 사고유형(incident_type) 매핑 시드.

범위: PDF 재추출은 하지 않는다. seed_samsung/hyundai/meritz/kb/db/kakaopay +
seed_personal_effects가 이미 넣어둔 실물 조항(DEATH_INJURY / OVS_INJ_MED / RESCUE /
PERSONAL_EFFECTS, 6개 보험사)만 대상으로 한다.

매핑 원칙 — 담보코드만 보고 찍지 않는다:
아래 EVIDENCE_* 로 시작하는 추가 매핑은 전부 "조항 원문에 그 문구가 문자 그대로
들어있는지"를 확인한 뒤에만 넣는다(clause_spans_gemini._locate_spans와 같은 원칙).
문구가 없으면 그 매핑은 조용히 건너뛰고, 마지막에 건너뛴 내역을 출력한다.
그래서 예를 들어 메리츠 구조송환 조항(축약 발췌본)은 '유해/시신 이송' 문구가 없으므로
EMG_REPATRIATION에 매핑되지 않는다 — 다른 5개사와 달라 보이지만 이게 실제 저장된 원문이다.

실제 원문을 읽고 확인한 사실:
- RESCUE 보장정의 6건 모두 지급사유가 (1)항공기·선박 행방불명/조난, (2)산악등반 조난,
  (3)긴급수색구조 필요, (4)**상해**를 직접원인으로 한 사망·N일 이상 입원,
  (5)**질병**을 직접원인으로 한 사망·N일 이상 입원 — 즉 상해/질병 양쪽에서 촉발된다.
  그래서 EMG_RESCUE(직접) 외에 INJ_DEATH_DISABILITY / ILL_DEATH_DISABILITY에
  '조건부'로도 건다. 일수는 회사별로 다르다(KB·DB 14일 고정, 삼성·카카오페이 14/7/4일
  선택, 현대·메리츠 증권 기재 일수) — 매핑 자체는 같지만 실제 원문을 읽었다는 확인.
- RESCUE 비용의 범위에 '이송비용(사망 시 시신/유해 송환, 치료 계속중 피보험자 이송)'과
  '구원자 2명분 교통비·숙박비'가 명시되어 있다. 이 담보가 유해송환·의료이송·가족방문
  비용까지 실제로 커버하므로, 해당 문구가 확인된 조항에 한해 EMG_REPATRIATION /
  EMG_MEDICAL_TRANSPORT / EMG_FAMILY_VISIT에도 매핑한다. 매핑하지 않으면 "유해송환을
  보장하는 조항이 하나도 없다"는 잘못된 결론(근거가 있는데 누락)이 나온다.
- PERSONAL_EFFECTS 면책 조항 6건 모두 '전쟁·천재지변·방사능' 면책과 '보험의 목적의
  방치 또는 분실' 면책을 함께 담고 있다. 그래서 PROP_LOSS(면책) 외에
  SPC_WAR_TERROR / SPC_NATURAL_DISASTER(면책)에도 건다.

매핑하지 않는 것:
- clause_type='서류'(제7조 보험금의 청구 등) — 사고유형과 무관한 공통 청구 절차이고,
  이미 CoverageDocMap.clause_id로 연결되어 다른 경로로 소비된다.
"""
from app.database import Base, SessionLocal, engine
from app import models  # noqa: F401  (모델 등록)
from app.models.kb import (
    Clause, ClauseIncidentMap, Coverage, CoverageStd, IncidentType,
)

Base.metadata.create_all(bind=engine)

MAPPED_BY = "human"  # 이 스크립트의 매핑은 전부 사람이 원문을 읽고 손으로 정한 것

# (std_code, clause_type) -> [(l2_code, relevance, confidence)]
# 원문 확인 없이 담보코드만으로 확정할 수 있는 기본 매핑.
BASE_RULES: dict[tuple[str, str], list[tuple[str, str, float]]] = {
    ("DEATH_INJURY", "보장정의"): [("INJ_DEATH_DISABILITY", "직접", 1.0)],
    ("DEATH_INJURY", "면책"): [("INJ_DEATH_DISABILITY", "면책", 1.0)],
    ("OVS_INJ_MED", "보장정의"): [("INJ_OVERSEAS_TREATMENT", "직접", 1.0)],
    ("OVS_INJ_MED", "면책"): [("INJ_OVERSEAS_TREATMENT", "면책", 1.0)],
    ("RESCUE", "보장정의"): [
        ("EMG_RESCUE", "직접", 1.0),
        # 상해/질병으로 인한 사망·장기입원이 지급사유이므로 조건부로 연결(원문 확인 완료)
        ("INJ_DEATH_DISABILITY", "조건부", 0.9),
        ("ILL_DEATH_DISABILITY", "조건부", 0.9),
    ],
    ("RESCUE", "면책"): [("EMG_RESCUE", "면책", 1.0)],
    # 자기부담금·보상한도액 조항 — 지급 여부가 아니라 지급 '조건'을 정한다
    ("RESCUE", "조건"): [("EMG_RESCUE", "조건부", 1.0)],
    ("PERSONAL_EFFECTS", "보장정의"): [
        # 이 특약은 '분실'을 빼고 도난·파손만 보상한다(특약명 자체가 "(분실제외)")
        ("PROP_THEFT", "직접", 1.0),
        ("PROP_DAMAGE", "직접", 1.0),
    ],
    # "보험의 목적의 방치 또는 분실"을 명시적으로 빼는 조항 — 분실 사고의 근거 조항
    ("PERSONAL_EFFECTS", "면책"): [("PROP_LOSS", "면책", 1.0)],
}

# 원문에 아래 문구 중 하나가 **문자 그대로** 있어야만 넣는 추가 매핑.
# (std_code, clause_type) -> [(l2_code, relevance, confidence, [증거문구...])]
EVIDENCE_RULES: dict[tuple[str, str], list[tuple[str, str, float, list[str]]]] = {
    ("RESCUE", "보장정의"): [
        ("EMG_REPATRIATION", "직접", 0.9, ["시신", "유해"]),
        ("EMG_MEDICAL_TRANSPORT", "조건부", 0.85, ["치료를 계속"]),
        ("EMG_FAMILY_VISIT", "조건부", 0.85, ["구원자"]),
    ],
    ("DEATH_INJURY", "면책"): [
        ("SPC_WAR_TERROR", "면책", 0.9, ["전쟁"]),
    ],
    ("OVS_INJ_MED", "면책"): [
        ("SPC_WAR_TERROR", "면책", 0.9, ["전쟁"]),
    ],
    ("RESCUE", "면책"): [
        # 대부분의 구조송환 면책 조항은 보통약관 제5조를 '번호로만' 인용해서 전쟁이라는
        # 단어가 원문에 없다 → 문구가 없으면 매핑하지 않는다(간접 인용은 근거로 안 본다).
        ("SPC_WAR_TERROR", "면책", 0.9, ["전쟁"]),
        ("SPC_NATURAL_DISASTER", "면책", 0.9, ["천재지변", "지진"]),
    ],
    ("PERSONAL_EFFECTS", "면책"): [
        ("SPC_WAR_TERROR", "면책", 0.9, ["전쟁"]),
        ("SPC_NATURAL_DISASTER", "면책", 0.9, ["천재지변"]),
    ],
}

SKIP_CLAUSE_TYPES = {"서류"}


def run():
    db = SessionLocal()
    try:
        types = {t.l2_code: t for t in db.query(IncidentType).all()}
        if not types:
            print("incident_type이 비어 있습니다. 먼저 `python -m app.seed_incident_types`를 실행하세요.")
            return

        if db.query(ClauseIncidentMap).count() > 0:
            print("이미 시드됨 (clause_incident_map). 스킵합니다.")
            return

        rows = (
            db.query(Clause, CoverageStd.std_code)
            .outerjoin(Coverage, Coverage.coverage_id == Clause.coverage_id)
            .outerjoin(CoverageStd, CoverageStd.coverage_std_id == Coverage.coverage_std_id)
            .order_by(Clause.clause_id)
            .all()
        )

        created = 0
        by_relevance: dict[str, int] = {}
        unmapped: list[tuple[int, str, str]] = []   # (clause_id, std_code, 사유)
        evidence_skipped: list[tuple[int, str, str]] = []  # (clause_id, l2_code, 사유)

        for clause, std_code in rows:
            key = (std_code, clause.clause_type)
            targets: list[tuple[str, str, float]] = list(BASE_RULES.get(key, []))

            for l2_code, relevance, conf, evidences in EVIDENCE_RULES.get(key, []):
                hit = next((e for e in evidences if e in (clause.text or "")), None)
                if hit is None:
                    evidence_skipped.append(
                        (clause.clause_id, l2_code, f"원문에 {'/'.join(evidences)} 문구 없음")
                    )
                    continue
                targets.append((l2_code, relevance, conf))

            if not targets:
                if clause.clause_type in SKIP_CLAUSE_TYPES:
                    reason = "청구서류 조항 — 사고유형 무관(CoverageDocMap으로 연결됨)"
                elif std_code is None:
                    reason = "담보에 연결되지 않은 조항(coverage_id NULL)"
                else:
                    reason = f"매핑 규칙 없음 (std={std_code}, type={clause.clause_type})"
                unmapped.append((clause.clause_id, std_code or "-", reason))
                continue

            for l2_code, relevance, conf in targets:
                itype = types.get(l2_code)
                if itype is None:
                    evidence_skipped.append((clause.clause_id, l2_code, "incident_type 사전에 없음"))
                    continue
                db.add(ClauseIncidentMap(
                    clause_id=clause.clause_id, type_id=itype.type_id,
                    relevance=relevance, mapped_by=MAPPED_BY, confidence=conf,
                ))
                created += 1
                by_relevance[relevance] = by_relevance.get(relevance, 0) + 1

        db.commit()

        lines = [
            f"clause_incident_map 시드 완료: {created}건 생성 (조항 {len(rows)}건 검토)",
            f"  relevance 분포: {by_relevance}",
            f"  매핑 없음 {len(unmapped)}건:",
        ]
        for cid, std, reason in unmapped:
            lines.append(f"    - clause_id={cid} std={std}: {reason}")
        lines.append(f"  증거문구 미확인으로 건너뛴 추가매핑 {len(evidence_skipped)}건:")
        for cid, l2, reason in evidence_skipped:
            lines.append(f"    - clause_id={cid} -> {l2}: {reason}")
        print("\n".join(lines))
    finally:
        db.close()


if __name__ == "__main__":
    run()
