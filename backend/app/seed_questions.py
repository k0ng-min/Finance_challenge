"""능동 질문 엔진 시드 (ne.md 7.4 / new.md question_bank). 사고 후 컨텍스트 MVP 6문항."""
from app.database import Base, SessionLocal, engine
from app import models
from app.models.question import QuestionBank

Base.metadata.create_all(bind=engine)

QUESTIONS = [
    ("사고후", "정확한 진단명 또는 증상을 알려주시겠어요? (예: 발목 골절, 열상 등)", "diagnosis", 0.9),
    ("사고후", "병원에 입원하셨나요, 아니면 통원 치료만 받으셨나요?", "hospitalized", 0.85),
    ("사고후", "수술을 받으셨나요?", "surgery", 0.7),
    ("사고후", "현지 병원에서 치료를 받으셨나요, 아니면 귀국 후 국내에서 치료받으셨나요?", "local_treatment", 0.6),
    ("사고후", "지금까지 지출하신 의료비가 대략 얼마인가요?", "medical_cost", 0.55),
    ("사고후", "이미 귀국하셨나요, 아직 현지에 계신가요?", "returned_home", 0.5),
    # 휴대품손해(분실제외) 특약은 "도난"·"파손"만 보상하고 "분실"(본인 부주의로 잃어버림)은
    # 보상하지 않는다 — 실제 6개 보험사 약관에 공통으로 명시된 구분이라, 이 셋 중 어느
    # 쪽인지 반드시 확인해야 정확한 담보 판단이 가능하다(claim_review.py의 item_damage_type).
    ("사고후", "휴대품 손해는 도난·강취를 당하신 건가요, 파손된 건가요, 아니면 본인 부주의로 잃어버리신 건가요?", "item_damage_type", 0.65),
]


def run():
    db = SessionLocal()
    try:
        existing_fields = {q.target_field for q in db.query(QuestionBank).all()}
        added = 0
        for context_type, text, target_field, weight in QUESTIONS:
            if target_field in existing_fields:
                continue
            db.add(QuestionBank(
                context_type=context_type, question_text=text,
                target_field=target_field, impact_weight=weight,
            ))
            added += 1
        db.commit()
        print(f"question_bank 시드 완료: {added}건 추가(기존 {len(existing_fields)}건은 스킵)")
    finally:
        db.close()


if __name__ == "__main__":
    run()
