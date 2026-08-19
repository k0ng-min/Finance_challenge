"""여행 기록·사고 접수 이력 삭제 시, 거기 딸린 분석 결과(추천/발견/검증/서류)까지
함께 정리한다. FK 순서상 자식 레코드부터 지워야 한다."""
from sqlalchemy.orm import Session

from app.models.analysis import AnalysisFinding, AnalysisRun, FindingEvidenceLink, ValidationResult
from app.models.external import ExternalCoverage, ExternalPolicy
from app.models.question import QuestionBank, UserQuestionLog
from app.models.user import (
    AppUser, Evidence, Incident, Trip, UserPolicy, UserCoverage, UserPremiumWatchlist,
)


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
    # 이 사고 하나를 위해 만들어진 추가 질문(incident_questions_gemini)도 같이 지운다.
    # 공용 질문 뱅크(incident_id=NULL)는 건드리지 않는다 — 그건 모든 사고가 함께 쓴다.
    # 답변 로그(UserQuestionLog)는 위에서 분석 실행과 함께 이미 지워져 참조가 남지 않는다.
    db.query(QuestionBank).filter(QuestionBank.incident_id == incident.incident_id)         .delete(synchronize_session=False)
    db.delete(incident)


def wipe_user_data(db: Session, user_id: int):
    """계정은 남기고 그 계정이 만든 사고·여행·보험 기록만 전부 지운다.

    두 군데서 쓴다.
    1) 게스트가 로그인·회원가입할 때 — 로그인 전에 체험 삼아 만든 기록이 정식 계정 이력에
       섞이면 안 된다.
    2) 비로그인 사용자가 새 여행/사고를 다시 등록할 때 — 게스트는 "여행 1개 + 거기 이어지는
       사고 1개"만 들고 갈 수 있어서, 새로 시작하면 앞의 기록을 정리한다.
    """
    for incident in db.query(Incident).filter(Incident.user_id == user_id).all():
        delete_incident_cascade(db, incident)
    for trip in db.query(Trip).filter(Trip.user_id == user_id).all():
        delete_trip_cascade(db, trip)
    policy_ids = [p.user_policy_id for p in db.query(UserPolicy).filter(UserPolicy.user_id == user_id).all()]
    if policy_ids:
        db.query(UserCoverage).filter(UserCoverage.user_policy_id.in_(policy_ids)).delete(synchronize_session=False)
        db.query(UserPolicy).filter(UserPolicy.user_policy_id.in_(policy_ids)).delete(synchronize_session=False)
    # 기존보험(이번 여행자보험이 아니라 사용자가 밖에서 이미 든 보험)도 같이 지운다.
    # user_id는 AUTOINCREMENT가 아니라 탈퇴 후 rowid가 재사용될 수 있어, 여기서 안 지우면
    # 다음에 그 user_id를 받는 신규 사용자가 탈퇴자의 기존보험 정보를 그대로 물려받는다.
    ext_ids = [
        p.external_policy_id
        for p in db.query(ExternalPolicy).filter(ExternalPolicy.user_id == user_id).all()
    ]
    if ext_ids:
        db.query(ExternalCoverage).filter(
            ExternalCoverage.external_policy_id.in_(ext_ids)
        ).delete(synchronize_session=False)
        db.query(ExternalPolicy).filter(
            ExternalPolicy.external_policy_id.in_(ext_ids)
        ).delete(synchronize_session=False)
    # 보험료 비교함(찜한 보험사 목록)도 같은 이유(rowid 재사용)로 같이 지운다.
    db.query(UserPremiumWatchlist).filter(UserPremiumWatchlist.user_id == user_id) \
        .delete(synchronize_session=False)


def delete_user_cascade(db: Session, user: AppUser):
    """회원 탈퇴 — 이 계정이 만든 사고·여행·보험 기록을 전부 지우고 계정 자체도 지운다.
    되돌릴 수 없으므로 라우터에서 반드시 확인(ConfirmDialog) 후에만 호출해야 한다."""
    wipe_user_data(db, user.user_id)
    db.delete(user)
