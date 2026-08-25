"""능동 질문 엔진 시드 (ne.md 7.4 / new.md question_bank).

Phase 2부터는 질문이 incident_type L1(사고 대분류)별로 태그된다(applies_to_l1) — 사고가
어느 L1로 분류됐는지에 따라 그 L1의 L2(작은 틀) 판별에 필요한 질문만 골라서 묻는다
(app.services.claim_review.pending_questions). applies_to_l1=None인 질문은 L1과 무관하게
항상 후보에 들어가는 완전 공통 질문이다. 여러 L1에만(전체는 아니게) 걸리는 질문은 콤마로
나열한다(예: "INJ,ILL" — 의료비는 상해·질병에서만 의미가 있고 휴대품·운송 등에는 해당 없음).

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
    # L1 자체가 보류된 경우에는 임시 SPC/INJ 전용 질문을 노출하지 않는다. 이 중립
    # 질문의 답까지 재분류 문맥에 넣은 뒤 실제 L1 질문 또는 분석 결과로 진행한다.
    ("사고후", "사고 유형을 더 확인하기 위해 무슨 일이 있었는지 구체적으로 알려주세요. (예: 다침, 질병, 휴대품 도난·분실·파손, 항공편·수하물 문제)", "incident_type_detail", 1.0, "UNRESOLVED"),
    ("사고후", "정확한 진단명 또는 증상을 알려주시겠어요? (예: 발목 골절, 열상 등)", "diagnosis", 0.9, "INJ"),
    ("사고후", "병원에 입원하셨나요, 아니면 통원 치료만 받으셨나요?", "hospitalized", 0.85, "INJ"),
    ("사고후", "수술을 받으셨나요?", "surgery", 0.7, "INJ"),
    ("사고후", "현지 병원에서 치료를 받으셨나요, 아니면 귀국 후 국내에서 치료받으셨나요?", "local_treatment", 0.6, "INJ"),
    # 의료비 질문은 상해/질병(INJ·ILL)에서만 의미가 있다 — 휴대품 도난·항공지연 같은 사고에는
    # "의료비"가 애초에 해당하지 않으므로 공통(None) 질문으로 두지 않고 두 L1에만 한정한다.
    # applies_to_l1은 콤마로 여러 L1을 나열할 수 있다(pending_questions 참고).
    ("사고후", "지금까지 지출하신 의료비가 대략 얼마인가요?", "medical_cost", 0.55, "INJ,ILL"),
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


# --- 세부유형(L2)이 정해졌을 때만 묻는 질문 ---------------------------------
#
# 대분류 질문만 있으면 "휴대품 사고"에는 늘 같은 문항이 나온다. 정작 청구에 필요한 건
# 도난이면 경찰 신고서, 분실이면 잃어버린 상황, 파손이면 수리 견적처럼 세부유형마다
# 다른 것들이다. 세부유형이 확정되기 전에는 이 질문들이 나오지 않는다(그 전에 다 꺼내면
# 도난·파손·분실 질문이 한꺼번에 쏟아진다).
L2_QUESTIONS = [
    # --- 휴대품(PROP) ---
    ("사고후", "도난 신고서(경찰 확인서)를 받아두셨나요?", "prop_police_report", 0.85, "PROP", "PROP_THEFT"),
    ("사고후", "도난당한 물건과 구입가를 알려주시겠어요?", "prop_theft_item", 0.7, "PROP", "PROP_THEFT"),
    ("사고후", "파손된 물건의 수리 견적서나 수리비 영수증이 있나요?", "prop_damage_estimate", 0.85, "PROP", "PROP_DAMAGE"),
    ("사고후", "어디서 어떻게 잃어버리셨는지 알려주시겠어요?", "prop_loss_place", 0.8, "PROP", "PROP_LOSS"),
    ("사고후", "여권 재발급에 실제로 든 비용이 얼마인가요?", "prop_passport_cost", 0.85, "PROP", "PROP_PASSPORT_LOSS"),
    ("사고후", "분실한 것이 현금인가요, 여행자수표·유가증권인가요?", "prop_cash_kind", 0.8, "PROP", "PROP_CASH_SECURITIES"),

    # --- 운송(TRV) ---
    ("사고후", "항공사에서 지연·결항 확인서를 받으셨나요?", "trv_delay_certificate", 0.85, "TRV", "TRV_FLIGHT_DELAY"),
    ("사고후", "지연 때문에 실제로 쓰신 비용(숙박·식사 등)이 있나요?", "trv_delay_expense", 0.7, "TRV", "TRV_FLIGHT_DELAY"),
    ("사고후", "수하물이 몇 시간 만에 도착했나요?", "trv_baggage_delay_hours", 0.85, "TRV", "TRV_BAGGAGE_DELAY"),
    ("사고후", "항공사에서 수하물 사고 접수증(PIR)을 받으셨나요?", "trv_baggage_pir", 0.85, "TRV", "TRV_BAGGAGE_DELAY,TRV_BAGGAGE_LOSS"),

    # --- 상해(INJ) ---
    ("사고후", "현지 병원 진단서와 진료비 영수증을 받아두셨나요?", "inj_overseas_docs", 0.8, "INJ", "INJ_OVERSEAS_TREATMENT"),
    ("사고후", "귀국 후 국내에서 치료를 시작한 날짜가 언제인가요?", "inj_domestic_start", 0.75, "INJ", "INJ_DOMESTIC_TREATMENT"),
    ("사고후", "후유장해 진단을 받으셨다면 장해 정도(%)가 어떻게 되나요?", "inj_disability_rate", 0.8, "INJ", "INJ_DEATH_DISABILITY"),

    # --- 질병(ILL) ---
    ("사고후", "격리 통지서나 확진 증명서를 받으셨나요?", "ill_quarantine_doc", 0.85, "ILL", "ILL_INFECTIOUS"),
    ("사고후", "격리 기간이 며칠이었나요?", "ill_quarantine_days", 0.75, "ILL", "ILL_INFECTIOUS"),
    ("사고후", "현지 병원 진단서와 진료비 영수증을 받아두셨나요?", "ill_overseas_docs", 0.8, "ILL", "ILL_OVERSEAS_TREATMENT"),

    # --- 배상책임(LIA) ---
    ("사고후", "숙소에서 청구서나 수리 견적서를 받으셨나요?", "lia_lodging_bill", 0.85, "LIA", "LIA_LODGING"),
    ("사고후", "피해자와 합의하셨나요? 합의서가 있으면 함께 준비해주세요.", "lia_settlement", 0.8, "LIA", "LIA_PERSONAL,LIA_PROPERTY"),

    # --- 여행변경(CHG) ---
    ("사고후", "실제로 청구된 취소 수수료가 얼마인가요?", "chg_cancel_fee", 0.85, "CHG", "CHG_CANCELLATION"),
    ("사고후", "조기 귀국하며 추가로 든 항공료가 얼마인가요?", "chg_return_cost", 0.85, "CHG", "CHG_INTERRUPTION"),

    # --- 긴급지원(EMG) ---
    ("사고후", "수색·구조 비용 청구서를 받으셨나요?", "emg_rescue_bill", 0.85, "EMG", "EMG_RESCUE"),
    ("사고후", "이송에 든 비용과 이송 수단(에어앰뷸런스 등)을 알려주시겠어요?", "emg_transport_cost", 0.85, "EMG", "EMG_MEDICAL_TRANSPORT"),
]


def run():
    db = SessionLocal()
    try:
        # incident_id가 달린 행은 사고 한 건을 위해 그때그때 만들어진 질문이다
        # (incident_questions_gemini). 프롬프트가 담보 필드 이름(diagnosis 등)을 그대로
        # 쓰라고 시키므로 여기 target_field가 겹친다 — 공용 행으로 오인하면 공용 질문이
        # 영영 안 만들어지고, 사고별 행에 공용 태그가 덧칠돼 다른 사고로 새어 나간다.
        existing_by_field = {
            q.target_field: q
            for q in db.query(QuestionBank).filter(QuestionBank.incident_id.is_(None)).all()
        }
        added = updated = 0
        specs = [(c, t, f, w, l1, None) for c, t, f, w, l1 in QUESTIONS] + L2_QUESTIONS
        for context_type, text, target_field, weight, applies_to_l1, applies_to_l2 in specs:
            row = existing_by_field.get(target_field)
            if row is None:
                db.add(QuestionBank(
                    context_type=context_type, question_text=text, target_field=target_field,
                    impact_weight=weight, applies_to_l1=applies_to_l1, applies_to_l2=applies_to_l2,
                ))
                added += 1
            elif row.applies_to_l1 != applies_to_l1 or row.applies_to_l2 != applies_to_l2:
                row.applies_to_l1 = applies_to_l1
                row.applies_to_l2 = applies_to_l2
                updated += 1
        db.commit()
        print(f"question_bank 시드 완료: {added}건 추가, {updated}건 applies_to_l1 갱신 (기존 {len(existing_by_field)}건)")
    finally:
        db.close()


if __name__ == "__main__":
    run()
