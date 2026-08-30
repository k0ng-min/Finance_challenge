"""
2026년 재구축 KB의 담보(coverage) ↔ 청구서류(required_doc_std) 매핑 시드.

CoverageStd 단위로 "이 종류의 담보를 청구하려면 보통 어떤 서류가 필요한가"를
매핑한다 — clause_incident_map과 같은 이유로 std_code 기준 재사용 규칙을 쓴다.
DocRequirement(서류별 세부 요건, 조항 원문 anchor_phrase 필요)는 이번 재구축
1차분에서는 만들지 않는다 — 조항 원문을 다시 읽고 요건 문구를 앵커링하는 별도
작업이 필요해서 정직하게 다음 단계로 미룬다.

administrative 담보(DISABILITY_CONVERSION/TRAVEL_COMPANION/DELEGATION_CLAIM)는
보험금 청구 자체가 없는 계약 절차 특약이라 서류 매핑 대상이 아니다.
"""
from app.database import Base, SessionLocal, engine
from app import models  # noqa: F401
from app.models.kb import Coverage, CoverageDocMap, CoverageStd, RequiredDocStd
from app.services.kb_seed_common import ADMIN_STD_CODES

Base.metadata.create_all(bind=engine)

# std_code -> [(doc_code, is_mandatory)]
DOC_RULES: dict[str, list[tuple[str, bool]]] = {
    "DEATH_INJURY": [("CLAIM_FORM", True), ("DEATH_CERT", False), ("DISABILITY_CERT", False), ("ID_CARD", True)],
    "ILL_DEATH": [("CLAIM_FORM", True), ("DEATH_CERT", False), ("DISABILITY_CERT", False), ("ID_CARD", True)],
    "INJ_DISABILITY_50PLUS": [("CLAIM_FORM", True), ("DISABILITY_CERT", True), ("ID_CARD", True)],
    "INJ_DISABILITY_80PLUS": [("CLAIM_FORM", True), ("DISABILITY_CERT", True), ("ID_CARD", True)],
    "INJ_DISABILITY_100": [("CLAIM_FORM", True), ("DISABILITY_CERT", True), ("ID_CARD", True)],

    "OVS_INJ_MED": [("CLAIM_FORM", True), ("MEDICAL_EXPENSE_CERT", True), ("MEDICAL_DETAIL_CERT", True),
                    ("TREATMENT_CERT", True), ("PRESCRIPTION", False), ("ID_CARD", True)],
    "OVS_ILL_MED": [("CLAIM_FORM", True), ("MEDICAL_EXPENSE_CERT", True), ("MEDICAL_DETAIL_CERT", True),
                    ("TREATMENT_CERT", True), ("PRESCRIPTION", False), ("ID_CARD", True)],
    "NON_COVERED_MED": [("CLAIM_FORM", True), ("MEDICAL_EXPENSE_CERT", True), ("MEDICAL_DETAIL_CERT", True), ("ID_CARD", True)],
    "NON_COVERED_MED_INJ": [("CLAIM_FORM", True), ("MEDICAL_EXPENSE_CERT", True), ("MEDICAL_DETAIL_CERT", True), ("ID_CARD", True)],
    "NON_COVERED_MED_MRI": [("CLAIM_FORM", True), ("MEDICAL_EXPENSE_CERT", True), ("MEDICAL_DETAIL_CERT", True), ("ID_CARD", True)],
    "OVS_MED_BASIC": [("CLAIM_FORM", True), ("MEDICAL_EXPENSE_CERT", True), ("MEDICAL_DETAIL_CERT", True),
                      ("TREATMENT_CERT", True), ("PRESCRIPTION", False), ("ID_CARD", True)],
    "DOM_MED_SEVERE_NONCOV": [("CLAIM_FORM", True), ("MEDICAL_EXPENSE_CERT", True), ("MEDICAL_DETAIL_CERT", True), ("ID_CARD", True)],
    "DOM_MED_NONSEVERE_NONCOV": [("CLAIM_FORM", True), ("MEDICAL_EXPENSE_CERT", True), ("MEDICAL_DETAIL_CERT", True), ("ID_CARD", True)],
    "DOM_MED_NONINSURED": [("CLAIM_FORM", True), ("MEDICAL_EXPENSE_CERT", True), ("MEDICAL_DETAIL_CERT", True), ("ID_CARD", True)],
    "INJ_HOSPITAL_ALLOWANCE": [("CLAIM_FORM", True), ("TREATMENT_CERT", True), ("ID_CARD", True)],
    "INJURY_HOSPITAL_DAILY": [("CLAIM_FORM", True), ("TREATMENT_CERT", True), ("ID_CARD", True)],
    "ILL_HOSPITAL_ALLOWANCE": [("CLAIM_FORM", True), ("TREATMENT_CERT", True), ("ID_CARD", True)],
    "BONE_FRACTURE": [("CLAIM_FORM", True), ("MEDICAL_DETAIL_CERT", True), ("ID_CARD", True)],
    "AIRCRAFT_INJURY": [("CLAIM_FORM", True), ("MEDICAL_EXPENSE_CERT", False), ("ID_CARD", True)],
    "CLIMATE_ILLNESS_HOT": [("CLAIM_FORM", True), ("MEDICAL_DETAIL_CERT", True), ("ID_CARD", True)],
    "CLIMATE_ILLNESS_COLD": [("CLAIM_FORM", True), ("MEDICAL_DETAIL_CERT", True), ("ID_CARD", True)],
    "FOOD_POISONING": [("CLAIM_FORM", True), ("MEDICAL_EXPENSE_CERT", False), ("TREATMENT_CERT", True), ("ID_CARD", True)],
    "FOOD_POISONING_HOSPITAL_DAILY": [("CLAIM_FORM", True), ("TREATMENT_CERT", True), ("ID_CARD", True)],
    "INFECTIOUS_DISEASE": [("CLAIM_FORM", True), ("MEDICAL_DETAIL_CERT", True), ("TREATMENT_CERT", True), ("ID_CARD", True)],

    "RESCUE": [("CLAIM_FORM", True), ("MEDICAL_EXPENSE_CERT", False), ("DEATH_CERT", False), ("ID_CARD", True)],
    "GOOD_SAMARITAN": [("CLAIM_FORM", True), ("MEDICAL_EXPENSE_CERT", False), ("ID_CARD", True)],
    "WAR_RISK": [("CLAIM_FORM", True), ("DEATH_CERT", False), ("MEDICAL_EXPENSE_CERT", False), ("ID_CARD", True)],
    "HIJACK": [("CLAIM_FORM", True), ("ID_CARD", True)],
    "SPORTS_INJ_EXCLUSION": [],
    "SPORTS_MED_EXCLUSION": [],
    "INJ_SPECIAL_SPORTS": [("CLAIM_FORM", True), ("MEDICAL_EXPENSE_CERT", True), ("ID_CARD", True)],
    "INJ_SPECIAL_DRIVING": [("CLAIM_FORM", True), ("MEDICAL_EXPENSE_CERT", True), ("ID_CARD", True)],

    "LIABILITY": [("CLAIM_FORM", True), ("LIABILITY_EVIDENCE", True), ("POLICE_REPORT", False), ("ID_CARD", True)],

    "PERSONAL_EFFECTS": [("CLAIM_FORM", True), ("THEFT_LOSS_STATEMENT", True), ("POLICE_REPORT", True), ("ID_CARD", True)],
    # 골프용품손해도 화재·도난·파손이라 휴대품과 같은 서류를 낸다.
    "GOLF_EQUIPMENT": [("CLAIM_FORM", True), ("THEFT_LOSS_STATEMENT", True), ("POLICE_REPORT", True), ("ID_CARD", True)],
    "HOME_THEFT": [("CLAIM_FORM", True), ("THEFT_LOSS_STATEMENT", True), ("POLICE_REPORT", True), ("ID_CARD", True)],
    "PASSPORT_LOSS": [("CLAIM_FORM", True), ("PASSPORT_REISSUE_RECEIPT", True), ("POLICE_REPORT", False), ("ID_CARD", True)],

    "FLIGHT_DELAY": [("CLAIM_FORM", True), ("FLIGHT_DELAY_CERT", True), ("ID_CARD", True)],
    "DEPARTURE_DELAY": [("CLAIM_FORM", True), ("FLIGHT_DELAY_CERT", True), ("ID_CARD", True)],
    "INDEX_FLIGHT_DELAY": [("CLAIM_FORM", True), ("FLIGHT_DELAY_CERT", True), ("ID_CARD", True)],
    "TRV_BAGGAGE_DELAY": [("CLAIM_FORM", True), ("BAGGAGE_IRREGULARITY", True), ("ID_CARD", True)],

    "TRIP_INTERRUPTION": [("CLAIM_FORM", True), ("MEDICAL_EXPENSE_CERT", False), ("ID_CARD", True)],
    "PET_CARE": [("CLAIM_FORM", True), ("ID_CARD", True)],
}



def run():
    """담보별 필요서류를 채운다. 이미 있는 담보는 건드리지 않고 없는 담보만 채운다.

    예전에는 "coverage_doc_map에 행이 하나라도 있으면 통째로 건너뛴다"였다. 그러면 이 시드가
    한 번 돈 뒤에 추가된 담보는 영영 서류가 안 붙는다 — 실제로 현대해상 특별약관 8건
    (구조송환·휴대품·식중독·전염병·항공기납치·여권분실·여행중단·자택도난)과 삼성화재
    반려동물 돌봄 1건이 그렇게 빈 채로 남아 있었고, 청구 안내에서 서류가 나오지 않았다.
    seed_premiums_actual·seed_questions가 같은 이유로 이미 "없는 것만 추가"로 바뀌어 있어서
    여기도 같은 방식으로 맞춘다.

    규칙에 없는 표준담보와 ADMIN_STD_CODES(지정대리청구·장애인전용전환 같은 제도성 특약)는
    그대로 넘어간다. 청구서류라는 개념 자체가 없는 특약이라, 없는 서류를 붙이지 않는다.
    """
    db = SessionLocal()
    try:
        docs = {d.doc_code: d for d in db.query(RequiredDocStd).all()}
        already = {r[0] for r in db.query(CoverageDocMap.coverage_id).distinct()}
        rows = [
            (coverage, std_code)
            for coverage, std_code in (
                db.query(Coverage, CoverageStd.std_code)
                .outerjoin(CoverageStd, CoverageStd.coverage_std_id == Coverage.coverage_std_id)
                .all()
            )
            if coverage.coverage_id not in already
        ]
        if not rows:
            print("coverage_doc_map: 모든 담보에 이미 서류가 붙어 있습니다.")
            return

        created = 0
        no_docs: list[tuple[int, str]] = []
        for coverage, std_code in rows:
            if std_code in ADMIN_STD_CODES:
                continue
            targets = DOC_RULES.get(std_code)
            if targets is None:
                no_docs.append((coverage.coverage_id, std_code or "-"))
                continue
            for doc_code, is_mandatory in targets:
                doc = docs.get(doc_code)
                if doc is None:
                    continue
                db.add(CoverageDocMap(
                    coverage_id=coverage.coverage_id,
                    required_doc_std_id=doc.required_doc_std_id,
                    is_mandatory=is_mandatory,
                ))
                created += 1

        db.commit()
        print(f"coverage_doc_map 시드 완료: {created}건 생성 (담보 {len(rows)}건 검토)")
        print(f"  매핑 규칙 없음 {len(no_docs)}건: {no_docs[:20]}")
    finally:
        db.close()


if __name__ == "__main__":
    run()
