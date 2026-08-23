"""영역 C: 능동 질문 엔진 (new.md 참조)"""
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class QuestionBank(Base):
    __tablename__ = "question_bank"

    question_id = Column(Integer, primary_key=True)
    context_type = Column(String)  # 가입전/사고후/누락검증
    question_text = Column(Text, nullable=False)
    target_field = Column(String)
    impact_weight = Column(Float, default=0.0)
    # 이 질문이 어느 사고유형 L1(예: "INJ")의 L2 판별에 쓰이는지. None이면 L1 공통(예: 의료비).
    applies_to_l1 = Column(String, nullable=True)
    # 그 대분류 안의 특정 세부유형(L2)에서만 묻는 질문. 예: 휴대품 사고라도 "도난"일
    # 때만 경찰 신고서를 묻는다. None이면 그 대분류 전체에 해당한다. 세부유형이 아직
    # 안 정해졌으면 이 질문들은 꺼내지 않는다 — 도난·파손·분실 질문이 한꺼번에 쏟아진다.
    applies_to_l2 = Column(String, nullable=True)
    # "L1" | "L2" — 사고 접수는 질문을 두 번 한다. 1단계는 대분류에서 확인할 것,
    # 2단계는 1단계 답까지 읽고 세부유형을 가르는 것. None이면 단계 구분 없는 옛 행이다.
    stage = Column(String, nullable=True)
    # "yesno" | "text" — 예/아니오 버튼으로 받을지, 한 줄 입력칸으로 받을지.
    # 진단명·지연 시간·의료비처럼 약관의 금액·시간 조건과 직결되는 값은 text로 받는다.
    answer_type = Column(String, nullable=False, default="text")
    # 이 질문이 특정 사고 한 건을 위해 그 자리에서 만들어진 것이면 그 사고 id.
    # None이면 미리 심어둔 공용 질문(seed_questions.py)이다.
    #
    # 예전에는 질문이 전부 공용 뱅크에 미리 적혀 있어서, 무슨 사고를 적든 "입원하셨나요,
    # 통원 치료만 받으셨나요?" 같은 정해진 문항이 순서대로 나왔다. 사고 내용에 이미
    # 답이 적혀 있어도 다시 물었고, 반대로 그 사고에서만 중요한 것(예: 분실 장소에
    # 잠금장치가 있었는지)은 아무도 묻지 않았다. 이제는 사고 내용을 보고 필요한 질문을
    # 그때그때 만들어(app.services.incident_questions_gemini) 이 컬럼에 사고 id를 달아
    # 저장한다 — 공용 뱅크를 오염시키지 않으면서 답변 저장 경로(UserQuestionLog)는
    # 기존 것을 그대로 쓴다.
    incident_id = Column(Integer, nullable=True, index=True)

    logs = relationship("UserQuestionLog", back_populates="question")


class UserQuestionLog(Base):
    __tablename__ = "user_question_log"

    qlog_id = Column(Integer, primary_key=True)
    analysis_run_id = Column(Integer, ForeignKey("analysis_run.analysis_run_id"), nullable=False)
    question_id = Column(Integer, ForeignKey("question_bank.question_id"), nullable=False)
    answer_text = Column(Text)
    asked_at = Column(DateTime)

    question = relationship("QuestionBank", back_populates="logs")
