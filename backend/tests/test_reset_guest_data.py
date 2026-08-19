"""배포 전 사용자 데이터 정리(reset_guest_data)가 약관 KB 쪽을 지우지 않는지 확인한다.

question_bank 한 테이블에 공용 질문 뱅크(seed_questions.py로 심는 것)와 사고 한 건을
위해 만들어진 질문이 함께 들어 있다. 여기서 통째로 DELETE 하면 커밋되는 app.db에서
공용 질문이 통째로 사라져, 클론한 사람은 사고 접수를 해도 아무 질문도 못 받게 된다.
"""
from app import reset_guest_data
from app.models.question import QuestionBank
from app.models.user import AppUser, Incident


def test_공용_질문은_남고_사고별_질문만_지워진다(db_session, monkeypatch, capsys):
    user = AppUser(nickname="게스트")
    db_session.add(user)
    db_session.flush()
    incident = Incident(user_id=user.user_id, free_text="사고")
    db_session.add(incident)
    db_session.flush()

    shared = QuestionBank(
        context_type="사고후", question_text="입원하셨나요?", target_field="hospitalized",
        impact_weight=0.5, incident_id=None,
    )
    generated = QuestionBank(
        context_type="사고후", question_text="경찰 신고서를 받으셨나요?", target_field="ai_police_report",
        impact_weight=0.9, incident_id=incident.incident_id,
    )
    db_session.add_all([shared, generated])
    db_session.commit()

    monkeypatch.setattr(db_session, "close", lambda: None)
    monkeypatch.setattr(reset_guest_data, "SessionLocal", lambda: db_session)

    reset_guest_data.run(confirm=True)

    left = db_session.query(QuestionBank).all()
    assert [q.target_field for q in left] == ["hospitalized"]
    assert db_session.query(AppUser).count() == 0
    assert db_session.query(Incident).count() == 0
