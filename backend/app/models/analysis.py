"""영역 D: 분석 · 형광펜 · 평가 (new.md 참조)"""
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class AnalysisRun(Base):
    __tablename__ = "analysis_run"

    analysis_run_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("app_user.user_id"), nullable=False)
    run_type = Column(String)  # 가입전추천/사고후검토/누락검증
    trip_id = Column(Integer, ForeignKey("trip.trip_id"), nullable=True)
    incident_id = Column(Integer, ForeignKey("incident.incident_id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    result_summary = Column(Text)  # JSON

    findings = relationship("AnalysisFinding", back_populates="analysis_run")
    validation_results = relationship("ValidationResult", back_populates="analysis_run")
    question_logs = relationship("UserQuestionLog")


class AnalysisFinding(Base):
    __tablename__ = "analysis_finding"

    finding_id = Column(Integer, primary_key=True)
    analysis_run_id = Column(Integer, ForeignKey("analysis_run.analysis_run_id"), nullable=False)
    finding_type = Column(String)  # 추천담보/보장공백/필요서류/누락/모순/제한조건
    status = Column(String)  # 청구검토후보/추가정보필요/서류확보필요/계약확인필요/관련성낮음/확인불가
    target_ref = Column(String)
    description = Column(Text)  # 확정적 지급표현 금지
    confidence = Column(String)
    coverage_amount = Column(String, nullable=True)  # 약관상 보장한도 원문(또는 사용자 입력)
    # 등록할 때 고른 등급 기준의 실제 가입금액. 위 coverage_amount와 성격이 다르다 —
    # 약관은 대부분 금액을 "보험증권 기재 금액"이라고만 쓰고 증권으로 미루는데, 그 실제
    # 숫자는 보험사 공시 등급별 가입금액표에 있다(services/coverage_amounts.py).
    plan_amount = Column(String, nullable=True)

    analysis_run = relationship("AnalysisRun", back_populates="findings")
    evidence_links = relationship("FindingEvidenceLink", back_populates="finding")


class FindingEvidenceLink(Base):
    __tablename__ = "finding_evidence_link"

    link_id = Column(Integer, primary_key=True)
    finding_id = Column(Integer, ForeignKey("analysis_finding.finding_id"), nullable=False)
    clause_id = Column(Integer, ForeignKey("clause.clause_id"), nullable=False)
    highlight_color = Column(String)  # 파랑/초록/노랑/빨강/회색

    finding = relationship("AnalysisFinding", back_populates="evidence_links")
    clause = relationship("Clause")


class ValidationRule(Base):
    __tablename__ = "validation_rule"

    rule_id = Column(Integer, primary_key=True)
    rule_code = Column(String, unique=True, nullable=False)
    rule_name = Column(String, nullable=False)
    severity = Column(String)  # 오류/경고/확인
    description = Column(Text)

    results = relationship("ValidationResult", back_populates="rule")


class ValidationResult(Base):
    __tablename__ = "validation_result"

    vresult_id = Column(Integer, primary_key=True)
    analysis_run_id = Column(Integer, ForeignKey("analysis_run.analysis_run_id"), nullable=False)
    rule_id = Column(Integer, ForeignKey("validation_rule.rule_id"), nullable=False)
    passed = Column(Boolean)
    detail = Column(Text)

    analysis_run = relationship("AnalysisRun", back_populates="validation_results")
    rule = relationship("ValidationRule", back_populates="results")


class EvalLog(Base):
    __tablename__ = "eval_log"

    eval_id = Column(Integer, primary_key=True)
    analysis_run_id = Column(Integer, ForeignKey("analysis_run.analysis_run_id"), nullable=True)
    baseline_type = Column(String)  # 규칙/일반LLM/단순RAG/필터+RAG/통합
    metric_name = Column(String)
    metric_value = Column(Float)
    dataset_tag = Column(String)
    recorded_at = Column(DateTime, server_default=func.now())
