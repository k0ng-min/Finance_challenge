"""
2026년 재구축 KB의 조항(clause) ↔ 사고유형(incident_type) 매핑 시드.

담보표준코드(coverage_std)와 clause_type 조합만으로 매핑한다 — 같은 담보 종류면
보험사가 달라도 같은 사고유형에 걸린다는 것이 이 프로젝트의 전제다(CoverageStd 자체가
그 전제 위에서 재사용되도록 설계돼 있다). 조항 원문 문구별 세부 증거 매핑(예: "시신"이라는
단어가 있어야만 유해송환에 건다)은 이번 재구축 1차분에서는 생략했다 — 담보표준코드 수준의
매핑만으로 우선 시뮬레이션·청구검토 기능이 동작하게 하고, 문구 단위 세분화는 다음 단계로
미룬다(정직하게 남김).

administrative 담보(DISABILITY_CONVERSION/TRAVEL_COMPANION/DELEGATION_CLAIM)는 계약
행정 특약이라 사고유형과 무관하므로 매핑하지 않는다. clause_type='서류'도 매핑하지
않는다(CoverageDocMap 경로로 이미 소비됨).

L1 8개(INJ/ILL/PROP/LIA/TRV/CHG/EMG/SPC) 어디에도 뚜렷이 맞지 않는 담보
(BONE_FRACTURE/AIRCRAFT_INJURY/INJ_HOSPITAL_ALLOWANCE류/CLIMATE_ILLNESS류)는 가장
가까운 기존 L2에 relevance='조건부'로 근사 매핑했다 — 전용 L2가 없다고 조용히
빠뜨리면 "근거는 있는데 누락"이 되므로, 근사가 부정확할 수 있음을 이 주석에 정직하게
남기고 needs_review 대상으로 표시하지 않는 대신(기존 L2를 씀) 이 파일에 근사임을
기록한다.
"""
from app.database import Base, SessionLocal, engine
from app import models  # noqa: F401
from app.models.kb import Clause, ClauseIncidentMap, Coverage, CoverageStd, IncidentType

Base.metadata.create_all(bind=engine)

MAPPED_BY = "human"

# (std_code, clause_type) -> [(l2_code, relevance)]
BASE_RULES: dict[tuple[str, str], list[tuple[str, str]]] = {
    ("DEATH_INJURY", "보장정의"): [("INJ_DEATH_DISABILITY", "직접")],
    ("DEATH_INJURY", "면책"): [("INJ_DEATH_DISABILITY", "면책")],
    ("DEATH_INJURY", "제한"): [("INJ_DEATH_DISABILITY", "조건부")],
    ("DEATH_INJURY", "조건"): [("INJ_DEATH_DISABILITY", "조건부")],

    ("OVS_INJ_MED", "보장정의"): [("INJ_OVERSEAS_TREATMENT", "직접")],
    ("OVS_INJ_MED", "면책"): [("INJ_OVERSEAS_TREATMENT", "면책")],
    ("OVS_INJ_MED", "제한"): [("INJ_OVERSEAS_TREATMENT", "조건부")],
    ("OVS_INJ_MED", "조건"): [("INJ_OVERSEAS_TREATMENT", "조건부")],

    ("RESCUE", "보장정의"): [
        ("EMG_RESCUE", "직접"),
        ("INJ_DEATH_DISABILITY", "조건부"),
        ("ILL_DEATH_DISABILITY", "조건부"),
        ("EMG_REPATRIATION", "조건부"),
        ("EMG_MEDICAL_TRANSPORT", "조건부"),
        ("EMG_FAMILY_VISIT", "조건부"),
    ],
    ("RESCUE", "면책"): [("EMG_RESCUE", "면책")],
    ("RESCUE", "제한"): [("EMG_RESCUE", "조건부")],
    ("RESCUE", "조건"): [("EMG_RESCUE", "조건부")],

    ("PERSONAL_EFFECTS", "보장정의"): [("PROP_THEFT", "직접"), ("PROP_DAMAGE", "직접")],
    ("PERSONAL_EFFECTS", "면책"): [("PROP_LOSS", "면책"), ("PROP_THEFT", "면책"), ("PROP_DAMAGE", "면책")],
    ("PERSONAL_EFFECTS", "제한"): [("PROP_THEFT", "조건부"), ("PROP_DAMAGE", "조건부")],

    # 골프용품손해(신한 2026판에서 처음 들어온 담보). 보험의 목적이 골프채·골프가방 등으로
    # 휴대품과 따로 정의돼 있지만, 사고의 성격은 같다 — 화재·도난과 파손이다.
    ("GOLF_EQUIPMENT", "보장정의"): [("PROP_THEFT", "직접"), ("PROP_DAMAGE", "직접")],
    ("GOLF_EQUIPMENT", "면책"): [("PROP_THEFT", "면책"), ("PROP_DAMAGE", "면책")],
    ("GOLF_EQUIPMENT", "제한"): [("PROP_THEFT", "조건부"), ("PROP_DAMAGE", "조건부")],
    ("GOLF_EQUIPMENT", "조건"): [("PROP_THEFT", "조건부"), ("PROP_DAMAGE", "조건부")],

    ("ILL_DEATH", "보장정의"): [("ILL_DEATH_DISABILITY", "직접")],
    ("ILL_DEATH", "면책"): [("ILL_DEATH_DISABILITY", "면책")],
    ("ILL_DEATH", "제한"): [("ILL_DEATH_DISABILITY", "조건부")],
    ("ILL_DEATH", "조건"): [("ILL_DEATH_DISABILITY", "조건부")],

    ("LIABILITY", "보장정의"): [("LIA_PERSONAL", "직접"), ("LIA_PROPERTY", "직접")],
    ("LIABILITY", "면책"): [("LIA_PERSONAL", "면책"), ("LIA_PROPERTY", "면책")],
    ("LIABILITY", "제한"): [("LIA_PERSONAL", "조건부"), ("LIA_PROPERTY", "조건부")],
    ("LIABILITY", "조건"): [("LIA_PERSONAL", "조건부"), ("LIA_PROPERTY", "조건부")],

    ("HIJACK", "보장정의"): [("TRV_HIJACK", "직접")],
    ("HIJACK", "면책"): [("TRV_HIJACK", "면책")],

    ("OVS_ILL_MED", "보장정의"): [("ILL_OVERSEAS_TREATMENT", "직접")],
    ("OVS_ILL_MED", "면책"): [("ILL_OVERSEAS_TREATMENT", "면책")],
    ("OVS_ILL_MED", "제한"): [("ILL_OVERSEAS_TREATMENT", "조건부")],
    ("OVS_ILL_MED", "조건"): [("ILL_OVERSEAS_TREATMENT", "조건부")],

    ("FLIGHT_DELAY", "보장정의"): [("TRV_FLIGHT_DELAY", "직접")],
    ("FLIGHT_DELAY", "면책"): [("TRV_FLIGHT_DELAY", "면책")],
    ("FLIGHT_DELAY", "제한"): [("TRV_FLIGHT_DELAY", "조건부")],
    ("FLIGHT_DELAY", "조건"): [("TRV_FLIGHT_DELAY", "조건부")],

    ("PET_CARE", "보장정의"): [("SPC_PET_CARE", "직접")],
    ("PET_CARE", "면책"): [("SPC_PET_CARE", "면책")],

    ("FOOD_POISONING", "보장정의"): [("ILL_NEW_1", "직접")],
    ("FOOD_POISONING", "면책"): [("ILL_NEW_1", "면책")],
    ("FOOD_POISONING", "제한"): [("ILL_NEW_1", "조건부")],

    ("INFECTIOUS_DISEASE", "보장정의"): [("ILL_INFECTIOUS", "직접")],
    ("INFECTIOUS_DISEASE", "면책"): [("ILL_INFECTIOUS", "면책")],

    ("TRIP_INTERRUPTION", "보장정의"): [("CHG_INTERRUPTION", "직접")],
    ("TRIP_INTERRUPTION", "면책"): [("CHG_INTERRUPTION", "면책")],
    ("TRIP_INTERRUPTION", "제한"): [("CHG_INTERRUPTION", "조건부")],

    ("PASSPORT_LOSS", "보장정의"): [("PROP_PASSPORT_LOSS", "직접")],
    ("PASSPORT_LOSS", "면책"): [("PROP_PASSPORT_LOSS", "면책")],
    ("PASSPORT_LOSS", "제한"): [("PROP_PASSPORT_LOSS", "조건부")],

    ("HOME_THEFT", "보장정의"): [("PROP_NEW_1", "직접")],
    ("HOME_THEFT", "면책"): [("PROP_NEW_1", "면책")],
    ("HOME_THEFT", "제한"): [("PROP_NEW_1", "조건부")],

    # 근사 매핑(전용 L2 없음): 의사상자 상해위험 — 상해사망·후유장해에 조건부로 연결
    ("GOOD_SAMARITAN", "보장정의"): [("INJ_DEATH_DISABILITY", "조건부")],

    ("WAR_RISK", "보장정의"): [("SPC_WAR_TERROR", "직접")],
    ("WAR_RISK", "면책"): [("SPC_WAR_TERROR", "면책")],

    # 근사 매핑: 비급여 실손의료비류는 국내치료 조건부로 연결
    ("NON_COVERED_MED", "보장정의"): [("INJ_DOMESTIC_TREATMENT", "조건부"), ("ILL_DOMESTIC_TREATMENT", "조건부")],
    ("NON_COVERED_MED", "면책"): [("INJ_DOMESTIC_TREATMENT", "면책"), ("ILL_DOMESTIC_TREATMENT", "면책")],
    ("NON_COVERED_MED_INJ", "보장정의"): [("INJ_DOMESTIC_TREATMENT", "조건부")],
    ("NON_COVERED_MED_INJ", "면책"): [("INJ_DOMESTIC_TREATMENT", "면책")],
    ("NON_COVERED_MED_MRI", "보장정의"): [("INJ_DOMESTIC_TREATMENT", "조건부"), ("ILL_DOMESTIC_TREATMENT", "조건부")],
    ("NON_COVERED_MED_MRI", "면책"): [("INJ_DOMESTIC_TREATMENT", "면책"), ("ILL_DOMESTIC_TREATMENT", "면책")],

    ("SPORTS_INJ_EXCLUSION", "면책"): [("INJ_DEATH_DISABILITY", "면책")],
    ("SPORTS_INJ_EXCLUSION", "보장정의"): [("INJ_DEATH_DISABILITY", "면책")],
    ("SPORTS_MED_EXCLUSION", "면책"): [("INJ_OVERSEAS_TREATMENT", "면책")],
    ("SPORTS_MED_EXCLUSION", "보장정의"): [("INJ_OVERSEAS_TREATMENT", "면책")],

    # 근사 매핑: 입원일당류(정액) — 해외/국내치료 조건부
    ("INJ_HOSPITAL_ALLOWANCE", "보장정의"): [("INJ_OVERSEAS_TREATMENT", "조건부")],
    ("INJ_HOSPITAL_ALLOWANCE", "면책"): [("INJ_OVERSEAS_TREATMENT", "면책")],
    ("INJURY_HOSPITAL_DAILY", "보장정의"): [("INJ_OVERSEAS_TREATMENT", "조건부")],
    ("INJURY_HOSPITAL_DAILY", "면책"): [("INJ_OVERSEAS_TREATMENT", "면책")],
    ("ILL_HOSPITAL_ALLOWANCE", "보장정의"): [("ILL_OVERSEAS_TREATMENT", "조건부")],
    ("ILL_HOSPITAL_ALLOWANCE", "면책"): [("ILL_OVERSEAS_TREATMENT", "면책")],

    # 위험스포츠/특수운전 확장 — 기본 상해담보의 면책 예외를 되돌리는 특약이라 조건부로 연결
    ("INJ_SPECIAL_SPORTS", "보장정의"): [("INJ_DEATH_DISABILITY", "조건부"), ("INJ_OVERSEAS_TREATMENT", "조건부")],
    ("INJ_SPECIAL_DRIVING", "보장정의"): [("INJ_DEATH_DISABILITY", "조건부"), ("INJ_OVERSEAS_TREATMENT", "조건부")],

    ("TRV_BAGGAGE_DELAY", "보장정의"): [("TRV_BAGGAGE_DELAY", "직접")],
    ("TRV_BAGGAGE_DELAY", "면책"): [("TRV_BAGGAGE_DELAY", "면책")],

    ("INJ_DISABILITY_50PLUS", "보장정의"): [("INJ_DEATH_DISABILITY", "직접")],
    ("INJ_DISABILITY_80PLUS", "보장정의"): [("INJ_DEATH_DISABILITY", "직접")],
    ("INJ_DISABILITY_100", "보장정의"): [("INJ_DEATH_DISABILITY", "직접")],

    ("OVS_MED_BASIC", "보장정의"): [("INJ_OVERSEAS_TREATMENT", "직접"), ("ILL_OVERSEAS_TREATMENT", "직접")],
    ("OVS_MED_BASIC", "면책"): [("INJ_OVERSEAS_TREATMENT", "면책"), ("ILL_OVERSEAS_TREATMENT", "면책")],
    ("OVS_MED_BASIC", "제한"): [("INJ_OVERSEAS_TREATMENT", "조건부"), ("ILL_OVERSEAS_TREATMENT", "조건부")],

    ("DOM_MED_SEVERE_NONCOV", "보장정의"): [("INJ_DOMESTIC_TREATMENT", "조건부"), ("ILL_DOMESTIC_TREATMENT", "조건부")],
    ("DOM_MED_NONSEVERE_NONCOV", "보장정의"): [("INJ_DOMESTIC_TREATMENT", "조건부"), ("ILL_DOMESTIC_TREATMENT", "조건부")],
    ("DOM_MED_NONINSURED", "보장정의"): [("INJ_DOMESTIC_TREATMENT", "조건부"), ("ILL_DOMESTIC_TREATMENT", "조건부")],
    ("DOM_MED_SEVERE_NONCOV", "조건"): [("INJ_DOMESTIC_TREATMENT", "조건부"), ("ILL_DOMESTIC_TREATMENT", "조건부")],
    ("DOM_MED_NONSEVERE_NONCOV", "조건"): [("INJ_DOMESTIC_TREATMENT", "조건부"), ("ILL_DOMESTIC_TREATMENT", "조건부")],
    ("DOM_MED_NONINSURED", "조건"): [("INJ_DOMESTIC_TREATMENT", "조건부"), ("ILL_DOMESTIC_TREATMENT", "조건부")],

    # 근사 매핑: 골절진단비 — 정액 상해급부, 전용 L2 없어 상해사망후유장해에 조건부
    ("BONE_FRACTURE", "보장정의"): [("INJ_DEATH_DISABILITY", "조건부")],

    # 근사 매핑: 항공기탑승중 상해위험 — 전쟁위험과 유사한 특수 확장담보
    ("AIRCRAFT_INJURY", "보장정의"): [("INJ_DEATH_DISABILITY", "조건부")],
    ("AIRCRAFT_INJURY", "면책"): [("INJ_DEATH_DISABILITY", "면책")],

    ("FOOD_POISONING_HOSPITAL_DAILY", "보장정의"): [("ILL_NEW_1", "조건부")],

    # 근사 매핑: 기후성질환(온열/한랭) 진단비 — 전용 L2 없어 해외질병치료에 조건부
    ("CLIMATE_ILLNESS_HOT", "보장정의"): [("ILL_OVERSEAS_TREATMENT", "조건부")],
    ("CLIMATE_ILLNESS_COLD", "보장정의"): [("ILL_OVERSEAS_TREATMENT", "조건부")],

    ("DEPARTURE_DELAY", "보장정의"): [("TRV_FLIGHT_DELAY", "직접")],
    ("DEPARTURE_DELAY", "면책"): [("TRV_FLIGHT_DELAY", "면책")],
    ("INDEX_FLIGHT_DELAY", "보장정의"): [("TRV_FLIGHT_DELAY", "직접")],
    ("INDEX_FLIGHT_DELAY", "면책"): [("TRV_FLIGHT_DELAY", "면책")],
}

# 계약행정 담보 — 사고유형과 무관하므로 의도적으로 매핑하지 않는다.
ADMIN_STD_CODES = {"DISABILITY_CONVERSION", "TRAVEL_COMPANION", "DELEGATION_CLAIM"}

SKIP_CLAUSE_TYPES = {"서류"}

# 담보표준코드만으로는 못 잡는 L2(SPC_NATURAL_DISASTER/PROP_CASH_SECURITIES/LIA_LODGING)를
# 문구 증거로 보충한다. 원문에 이 문구가 실제로 있는 조항에만 건다(EVIDENCE_RULES 원칙,
# seed_overlap_rules.py와 동일) — 없으면 조용히 건너뛴다.
# (evidence_phrase, l2_code, relevance)
EVIDENCE_RULES: list[tuple[str, str, str]] = [
    # 천재지변으로 인한 여행중단은 TRIP_INTERRUPTION 보장정의 안에 "지진, 분화, 해일
    # 또는 이와 비슷한 천재지변"이 지급사유로 직접 열거돼 있다.
    ("천재지변", "SPC_NATURAL_DISASTER", "직접"),
    # 배상책임 면책 조항에 "통화, 유가증권..." 등을 보험목적에서 제외한다는 문구가 있으면
    # 현금·유가증권 손해는 이 담보로 보상받지 못한다는 직접 증거다.
    ("유가증권", "PROP_CASH_SECURITIES", "면책"),
    # 배상책임 면책 조항이 재물손해 배상책임을 일반적으로 면책하면서 "호텔의 객실이나
    # 객실내의 동산에 끼치는 손해"만 예외로 되살리는 경우 — 임차물·호텔객실 배상책임이
    # 조건부로 살아 있다는 증거다.
    ("호텔의 객실", "LIA_LODGING", "조건부"),
    # 6개사 전부 "항공기 및 수하물 지연비용" 특별약관 하나로 항공지연·수하물지연을 함께
    # 다룬다(별도 CoverageStd로 안 나뉜다) — "피보험자의 수하물이 …도착시각으로부터 N시간
    # 이후에 도착"이라는 지급사유 문구가 있으면 수하물 지연도 같은 담보로 보상된다는
    # 직접 증거다.
    ("수하물이 항공편의 예정된 도착", "TRV_BAGGAGE_DELAY", "직접"),
]


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
        unmapped: list[tuple[int, str, str]] = []

        made: set[tuple[int, int, str]] = set()  # (clause_id, type_id, relevance) 중복 방지

        def _add(clause_id: int, l2_code: str, relevance: str) -> bool:
            itype = types.get(l2_code)
            if itype is None:
                return False
            key = (clause_id, itype.type_id, relevance)
            if key in made:
                return False
            made.add(key)
            db.add(ClauseIncidentMap(
                clause_id=clause_id, type_id=itype.type_id,
                relevance=relevance, mapped_by=MAPPED_BY, confidence=None,
            ))
            return True

        for clause, std_code in rows:
            if clause.clause_type in SKIP_CLAUSE_TYPES:
                continue

            base_hit = False
            if std_code not in ADMIN_STD_CODES:
                targets = BASE_RULES.get((std_code, clause.clause_type), [])
                for l2_code, relevance in targets:
                    if _add(clause.clause_id, l2_code, relevance):
                        base_hit = True
                        created += 1
                        by_relevance[relevance] = by_relevance.get(relevance, 0) + 1
                    else:
                        unmapped.append((clause.clause_id, std_code, f"incident_type 사전에 {l2_code} 없음"))

            # 담보표준코드 규칙과 별개로, 원문에 증거 문구가 있으면 추가로 매핑한다
            # (같은 조항이 BASE_RULES로 이미 매핑됐어도 중복 없이 더 붙는다).
            for phrase, l2_code, relevance in EVIDENCE_RULES:
                if phrase in (clause.text or "") and _add(clause.clause_id, l2_code, relevance):
                    base_hit = True
                    created += 1
                    by_relevance[relevance] = by_relevance.get(relevance, 0) + 1

            if not base_hit and std_code not in ADMIN_STD_CODES:
                reason = "담보에 연결되지 않은 조항(coverage_id NULL)" if std_code is None else \
                    f"매핑 규칙 없음 (std={std_code}, type={clause.clause_type})"
                unmapped.append((clause.clause_id, std_code or "-", reason))

        db.commit()
        print(f"clause_incident_map 시드 완료: {created}건 생성 (조항 {len(rows)}건 검토)")
        print(f"  relevance 분포: {by_relevance}")
        print(f"  매핑 없음 {len(unmapped)}건")
        for cid, std, reason in unmapped[:30]:
            print(f"    - clause_id={cid} std={std}: {reason}")
    finally:
        db.close()


if __name__ == "__main__":
    run()
