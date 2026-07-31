"""능동 질문 엔진 시드 (ne.md 7.4 / new.md question_bank).

Phase 2부터는 질문이 incident_type L1(사고 대분류)별로 태그된다(applies_to_l1) — 사고가
어느 L1로 분류됐는지에 따라 그 L1의 L2(작은 틀) 판별에 필요한 질문만 골라서 묻는다
(app.services.claim_review.pending_questions). applies_to_l1=None인 질문은 L1과 무관하게
항상 후보에 들어가는 공통 질문(예: 의료비)이다.

기존 7문항(상해/휴대품 MVP)은 그대로 두고 L1 태그만 붙였다. 나머지 6개 L1(ILL/LIA/TRV/
CHG/EMG/SPC)에는 아직 조항 데이터가 얕지만(clause_incident_map 매핑이 상해 위주), 사고
접수 흐름 자체는 8개 L1 전부에서 동작해야 하므로 골격 질문만 먼저 채워둔다 — 사용자가 준
슬롯 예시(항공지연시간/수하물, 취소사유/시점, 수색구조/의료이송 여부 등)를 그대로 썼다.
"""
from app.database import Base, SessionLocal, engine
from app import models
from app.models.question import QuestionBank

Base.metadata.create_all(bind=engine)

# (context_type, question_text, target_field, impact_weight, applies_to_l1)
QUESTIONS = [
    ("사고후", "정확한 진단명 또는 증상을 알려주시겠어요? (예: 발목 골절, 열상 등)", "diagnosis", 0.9, "INJ"),
    ("사고후", "병원에 입원하셨나요, 아니면 통원 치료만 받으셨나요?", "hospitalized", 0.85, "INJ"),
    ("사고후", "수술을 받으셨나요?", "surgery", 0.7, "INJ"),
    ("사고후", "현지 병원에서 치료를 받으셨나요, 아니면 귀국 후 국내에서 치료받으셨나요?", "local_treatment", 0.6, "INJ"),
    ("사고후", "지금까지 지출하신 의료비가 대략 얼마인가요?", "medical_cost", 0.55, None),
    ("사고후", "이미 귀국하셨나요, 아직 현지에 계신가요?", "returned_home", 0.5, "INJ"),
    # 휴대품손해(분실제외) 특약은 "도난"·"파손"만 보상하고 "분실"(본인 부주의로 잃어버림)은
    # 보상하지 않는다 — 실제 6개 보험사 약관에 공통으로 명시된 구분이라, 이 셋 중 어느
    # 쪽인지 반드시 확인해야 정확한 담보 판단이 가능하다(claim_review.py의 item_damage_type).
    ("사고후", "휴대품 손해는 도난·강취를 당하신 건가요, 파손된 건가요, 아니면 본인 부주의로 잃어버리신 건가요?", "item_damage_type", 0.65, "PROP"),

    # --- 질병(ILL) ---
    ("사고후", "정확한 병명 또는 증상을 알려주시겠어요?", "ill_diagnosis", 0.9, "ILL"),
    ("사고후", "입원하셨나요, 통원 치료만 받으셨나요?", "ill_hospitalized", 0.8, "ILL"),
    ("사고후", "여행 전부터 있던 지병인가요, 여행 중 새로 생긴 증상인가요?", "ill_preexisting", 0.7, "ILL"),

    # --- 배상책임(LIA) ---
    ("사고후", "상대방(사람)이 다치셨나요, 물건이 파손됐나요, 아니면 숙소(호텔 객실 등) 시설이 파손됐나요?", "lia_damage_target", 0.9, "LIA"),
    ("사고후", "피해를 입힌 상황을 조금 더 설명해주시겠어요? (고의가 아닌 실수였는지 등)", "lia_cause_detail", 0.6, "LIA"),

    # --- 운송(TRV) ---
    ("사고후", "항공편이 몇 시간 이상 지연되거나 결항됐나요?", "flight_delay_hours", 0.9, "TRV"),
    ("사고후", "수하물이 늦게 도착했나요, 아예 분실됐나요?", "baggage_issue_type", 0.8, "TRV"),

    # --- 여행변경(CHG) ---
    ("사고후", "여행을 아예 취소하신 건가요, 여행 중 일정을 중단하고 조기 귀국하신 건가요?", "trip_change_type", 0.9, "CHG"),
    ("사고후", "취소·중단 사유가 무엇인가요? (본인 질병, 가족 사망 등)", "trip_change_reason", 0.8, "CHG"),
    ("사고후", "여행 출발 전이었나요, 이미 출발한 뒤였나요?", "trip_change_timing", 0.6, "CHG"),

    # --- 긴급지원(EMG) ---
    ("사고후", "산악·바다 등에서 조난돼 수색구조가 필요한 상황인가요?", "emg_rescue_needed", 0.9, "EMG"),
    ("사고후", "환자를 다른 병원으로, 또는 귀국을 위해 이송해야 하는 상황인가요?", "emg_transport_needed", 0.8, "EMG"),
    ("사고후", "돌아가신 경우라면, 유해(시신) 송환이 필요한 상황인가요?", "emg_repatriation_needed", 0.85, "EMG"),

    # --- 특수·기타(SPC) ---
    ("사고후", "전쟁이나 테러와 관련된 상황인가요?", "spc_war_terror", 0.8, "SPC"),
    ("사고후", "지진, 홍수 같은 천재지변과 관련된 상황인가요?", "spc_natural_disaster", 0.8, "SPC"),
    ("사고후", "반려동물과 관련된 상황인가요?", "spc_pet_care", 0.5, "SPC"),
]


def run():
    db = SessionLocal()
    try:
        existing_by_field = {q.target_field: q for q in db.query(QuestionBank).all()}
        added = updated = 0
        for context_type, text, target_field, weight, applies_to_l1 in QUESTIONS:
            row = existing_by_field.get(target_field)
            if row is None:
                db.add(QuestionBank(
                    context_type=context_type, question_text=text, target_field=target_field,
                    impact_weight=weight, applies_to_l1=applies_to_l1,
                ))
                added += 1
            elif row.applies_to_l1 != applies_to_l1:
                row.applies_to_l1 = applies_to_l1
                updated += 1
        db.commit()
        print(f"question_bank 시드 완료: {added}건 추가, {updated}건 applies_to_l1 갱신 (기존 {len(existing_by_field)}건)")
    finally:
        db.close()


if __name__ == "__main__":
    run()
