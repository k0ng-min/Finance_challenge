"""여행 기록·사고 접수 이력 삭제 시, 거기 딸린 분석 결과(추천/발견/검증/서류)까지
함께 정리한다. FK 순서상 자식 레코드부터 지워야 한다."""
from sqlalchemy.orm import Session

from app.models.analysis import AnalysisFinding, AnalysisRun, FindingEvidenceLink, ValidationResult
from app.models.question import UserQuestionLog
from app.models.user import AppUser, Evidence, Incident, Trip, UserPolicy, UserCoverage


def delete_analysis_run(db: Session, run: AnalysisRun):
    finding_ids = [
        f.finding_id for f in
        db.query(AnalysisFinding).filter(AnalysisFinding.analysis_run_id == run.analysis_run_id).all()
    ]
    if finding_ids:
        db.query(FindingEvidenceLink).filter(FindingEvidenceLink.finding_id.in_(finding_ids)) \
            .delete(synchronize_session=False)
        db.query(AnalysisFinding).filter(AnalysisFinding.analysis_run_id == run.analysis_run_id) \
            .delete(synchronize_session=False)
    db.query(ValidationResult).filter(ValidationResult.analysis_run_id == run.analysis_run_id) \
        .delete(synchronize_session=False)
    db.query(UserQuestionLog).filter(UserQuestionLog.analysis_run_id == run.analysis_run_id) \
        .delete(synchronize_session=False)
    db.delete(run)


def delete_trip_cascade(db: Session, trip: Trip):
    runs = db.query(AnalysisRun).filter(AnalysisRun.trip_id == trip.trip_id).all()
    for run in runs:
        delete_analysis_run(db, run)
    # 이 여행을 참조하던 사고 기록은 그대로 두되, 끊어진 참조만 비운다.
    db.query(Incident).filter(Incident.trip_id == trip.trip_id).update({"trip_id": None})
    db.delete(trip)


def delete_incident_cascade(db: Session, incident: Incident):
    runs = db.query(AnalysisRun).filter(AnalysisRun.incident_id == incident.incident_id).all()
    for run in runs:
        delete_analysis_run(db, run)
    db.query(Evidence).filter(Evidence.incident_id == incident.incident_id).delete(synchronize_session=False)
    db.delete(incident)


def delete_user_cascade(db: Session, user: AppUser):
    """회원 탈퇴 — 이 계정이 만든 사고·여행·보험 기록을 전부 지우고 계정 자체도 지운다.
    되돌릴 수 없으므로 라우터에서 반드시 확인(ConfirmDialog) 후에만 호출해야 한다."""
    for incident in db.query(Incident).filter(Incident.user_id == user.user_id).all():
        delete_incident_cascade(db, incident)
    for trip in db.query(Trip).filter(Trip.user_id == user.user_id).all():
        delete_trip_cascade(db, trip)
    policy_ids = [p.user_policy_id for p in db.query(UserPolicy).filter(UserPolicy.user_id == user.user_id).all()]
    if policy_ids:
        db.query(UserCoverage).filter(UserCoverage.user_policy_id.in_(policy_ids)).delete(synchronize_session=False)
        db.query(UserPolicy).filter(UserPolicy.user_policy_id.in_(policy_ids)).delete(synchronize_session=False)
    db.delete(user)
