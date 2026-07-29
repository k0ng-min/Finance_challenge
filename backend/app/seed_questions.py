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
]


def run():
    db = SessionLocal()
    try:
        if db.query(QuestionBank).count() > 0:
            print("이미 시드됨 (question_bank). 스킵합니다.")
            return
        for context_type, text, target_field, weight in QUESTIONS:
            db.add(QuestionBank(
                context_type=context_type, question_text=text,
                target_field=target_field, impact_weight=weight,
            ))
        db.commit()
        print(f"question_bank 시드 완료: {len(QUESTIONS)}건")
    finally:
        db.close()


if __name__ == "__main__":
    run()
