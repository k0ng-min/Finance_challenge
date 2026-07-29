"""규칙 엔진 정의 시드 (ne.md 11.2 / new.md validation_rule)."""
from app.database import Base, SessionLocal, engine
from app import models
from app.models.analysis import ValidationRule

Base.metadata.create_all(bind=engine)

RULES = [
    ("PERIOD_MISMATCH", "보험기간-사고일 불일치", "오류",
     "등록된 보험계약의 보험기간에 사고일이 포함되는지 확인합니다."),
    ("INFO_MISSING", "사고정보 누락", "경고",
     "청구 검토에 필요한 핵심 사고정보(진단명, 입원/수술 여부 등)가 아직 확인되지 않았는지 점검합니다."),
    ("CONTRADICTION_SURGERY_HOSP", "입력 모순(수술·입원 여부)", "경고",
     "수술을 받았다고 했으나 입원 여부가 '아니오'로 응답된 경우처럼 사고 설명 간 모순을 점검합니다."),
    ("DOC_NOT_SECURED", "필수서류 미확보", "확인",
     "청구 검토 대상 담보의 필수서류 중 아직 확보되지 않았거나 발급이 불가능하다고 표시된 서류가 있는지 확인합니다."),
]


def run():
    db = SessionLocal()
    try:
        if db.query(ValidationRule).count() > 0:
            print("이미 시드됨 (validation_rule). 스킵합니다.")
            return
        for code, name, severity, desc in RULES:
            db.add(ValidationRule(rule_code=code, rule_name=name, severity=severity, description=desc))
        db.commit()
        print(f"validation_rule 시드 완료: {len(RULES)}건")
    finally:
        db.close()


if __name__ == "__main__":
    run()
