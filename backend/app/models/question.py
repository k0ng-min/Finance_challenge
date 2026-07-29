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

    logs = relationship("UserQuestionLog", back_populates="question")


class UserQuestionLog(Base):
    __tablename__ = "user_question_log"

    qlog_id = Column(Integer, primary_key=True)
    analysis_run_id = Column(Integer, ForeignKey("analysis_run.analysis_run_id"), nullable=False)
    question_id = Column(Integer, ForeignKey("question_bank.question_id"), nullable=False)
    answer_text = Column(Text)
    asked_at = Column(DateTime)

    question = relationship("QuestionBank", back_populates="logs")
