"""사고 접수 → 추가질문 → 재분류 상태 전이의 API 회귀 테스트."""
import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models.analysis import AnalysisRun
from app.models.kb import IncidentType
from app.models.question import QuestionBank, UserQuestionLog
from app.models.user import AppUser, Incident
from app.services import incident_classify_gemini as classifier
from app.routers import incidents


def _seed_taxonomy(db):
    for l1_code, name, children in (
        ("INJ", "상해", (("INJ_OVERSEAS_TREATMENT", "해외상해치료"),)),
        ("PROP", "휴대품·재물", (
            ("PROP_THEFT", "도난"), ("PROP_DAMAGE", "파손"), ("PROP_LOSS", "분실"),
        )),
        ("SPC", "특수·기타", (("SPC_WAR_TERROR", "전쟁·테러"),)),
    ):
        root = IncidentType(l1_code=l1_code, l2_code=l1_code, name=name, is_active=True)
        db.add(root)
        db.flush()
        for l2_code, l2_name in children:
            db.add(IncidentType(
                l1_code=l1_code, l2_code=l2_code, name=l2_name,
                parent_id=root.type_id, is_active=True,
            ))

    questions = (
        ("무슨 일이 있었는지 구체적으로 알려주세요.", "incident_type_detail", 1.0, "UNRESOLVED"),
        ("다쳤거나 치료받았나요?", "diagnosis", 0.9, "INJ"),
        ("도난·파손·분실 중 무엇인가요?", "item_damage_type", 0.9, "PROP"),
        ("전쟁이나 테러와 관련됐나요?", "spc_war_terror", 0.9, "SPC"),
    )
    for text, field, weight, applies_to_l1 in questions:
        db.add(QuestionBank(
            context_type="사고후", question_text=text, target_field=field,
            impact_weight=weight, applies_to_l1=applies_to_l1,
        ))
    db.commit()


@pytest.fixture
def client(db_session, monkeypatch):
    _seed_taxonomy(db_session)
    db_session.add(AppUser(user_id=1, nickname="테스트", auth_provider="guest"))
    db_session.commit()

    # 질문 상태 전이만 검증한다. 담보/검증 결과는 다른 테스트의 책임이다.
    monkeypatch.setattr(incidents, "generate_claim_findings", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(incidents, "run_core_validation", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(incidents, "check_docs_not_secured", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(classifier, "extract_modifiers", lambda _text: {})

    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as test_client:
        yield test_client, db_session
    app.dependency_overrides.clear()


def _abstain_l2(db, l1_code, *_args, **_kwargs):
    root = db.query(IncidentType).filter_by(l2_code=l1_code, parent_id=None).one()
    return classifier.L2ClassifyResult(
        type_id=root.type_id, l2_code=None, confidence=0.0,
        reason="추가 정보 필요", abstained=True,
    )


def test_answered_question_is_not_returned_again(client, monkeypatch):
    test_client, _db = client
    monkeypatch.setattr(classifier, "classify_l1", lambda _text: ("PROP", 0.9, "휴대품"))
    monkeypatch.setattr(classifier, "classify_l2", _abstain_l2)

    created = test_client.post("/incidents", json={"user_id": 1, "free_text": "휴대품에 문제가 생겼어요"})
    assert created.status_code == 200
    first = created.json()["pending_questions"][0]
    assert first["target_field"] == "item_damage_type"
    assert "전쟁" not in first["question_text"]

    answered = test_client.post(
        f"/incidents/{created.json()['incident_id']}/answers",
        json={"question_id": first["question_id"], "answer_text": "정확히 모르겠어요"},
    )
    assert answered.status_code == 200
    returned_ids = {q["question_id"] for q in answered.json()["pending_questions"]}
    assert first["question_id"] not in returned_ids

    refreshed = test_client.get(f"/incidents/{created.json()['incident_id']}")
    assert refreshed.status_code == 200
    assert first["question_id"] not in {
        q["question_id"] for q in refreshed.json()["pending_questions"]
    }


def test_low_confidence_l1_can_change_after_followup_api(client, monkeypatch):
    test_client, db = client
    predictions = iter((("INJ", 0.30, "불명확"), ("PROP", 0.95, "도난 명확")))
    monkeypatch.setattr(classifier, "classify_l1", lambda _text: next(predictions))
    monkeypatch.setattr(classifier, "classify_l2", _abstain_l2)

    created = test_client.post("/incidents", json={"user_id": 1, "free_text": "여행 중 문제가 생겼어요"})
    assert created.status_code == 200
    pending = created.json()["pending_questions"]
    assert [q["target_field"] for q in pending] == ["incident_type_detail"]
    assert all("전쟁" not in q["question_text"] for q in pending)

    answered = test_client.post(
        f"/incidents/{created.json()['incident_id']}/answers",
        json={"question_id": pending[0]["question_id"], "answer_text": "휴대폰을 소매치기당했어요"},
    )
    assert answered.status_code == 200
    assert answered.json()["pending_questions"] == []
    incident = db.get(Incident, created.json()["incident_id"])
    assert incident.incident_type.l2_code == "PROP_THEFT"
    assert incident.item_damage_type == "도난"


@pytest.mark.parametrize(
    ("text", "expected_l2"),
    (
        ("여행 중 휴대폰을 변기에 빠뜨려 고장났어요.", "PROP_DAMAGE"),
        ("여행 중 휴대폰을 어디선가 잃어버렸어요.", "PROP_LOSS"),
    ),
)
def test_clear_phone_incident_finishes_without_unrelated_question(
    client, monkeypatch, text, expected_l2,
):
    test_client, db = client
    monkeypatch.setattr(classifier, "classify_l1", lambda _text: ("PROP", 0.95, "휴대품"))
    monkeypatch.setattr(classifier, "classify_l2", _abstain_l2)

    response = test_client.post("/incidents", json={"user_id": 1, "free_text": text})
    assert response.status_code == 200
    assert response.json()["pending_questions"] == []
    incident = db.get(Incident, response.json()["incident_id"])
    assert incident.incident_type.l2_code == expected_l2
    assert incident.item_damage_type == {"PROP_DAMAGE": "파손", "PROP_LOSS": "분실"}[expected_l2]


def test_modifier_target_question_is_resolved_after_answer(client, monkeypatch):
    test_client, db = client
    monkeypatch.setattr(classifier, "classify_l1", lambda _text: ("SPC", 0.9, "특수"))
    monkeypatch.setattr(classifier, "classify_l2", _abstain_l2)

    created = test_client.post("/incidents", json={"user_id": 1, "free_text": "특수한 문제가 생겼어요"})
    question = created.json()["pending_questions"][0]
    answered = test_client.post(
        f"/incidents/{created.json()['incident_id']}/answers",
        json={"question_id": question["question_id"], "answer_text": "아니요"},
    )
    assert answered.status_code == 200
    assert answered.json()["pending_questions"] == []
    assert db.query(UserQuestionLog).count() == 1


def test_pending_questions_eventually_terminates(db_session):
    _seed_taxonomy(db_session)
    user = AppUser(user_id=7, nickname="종료 테스트", auth_provider="guest")
    root = db_session.query(IncidentType).filter_by(l2_code="INJ").one()
    incident = Incident(user_id=7, free_text="모호함", type_id=root.type_id, classify_confidence=0.9)
    db_session.add_all([user, incident])
    db_session.flush()

    # 실제 질문 수가 더 많더라도 다섯 라운드 뒤에는 보수적 분석 단계로 종료한다.
    questions = []
    for index in range(6):
        q = QuestionBank(
            context_type="사고후", question_text=f"상해 질문 {index}",
            target_field=f"inj_extra_{index}", impact_weight=0.8 - index / 100,
            applies_to_l1="INJ",
        )
        db_session.add(q)
        questions.append(q)
    run = AnalysisRun(user_id=7, run_type="사고후검토", incident_id=incident.incident_id)
    db_session.add(run)
    db_session.flush()
    for q in questions[:5]:
        db_session.add(UserQuestionLog(
            analysis_run_id=run.analysis_run_id, question_id=q.question_id, answer_text="확인함",
        ))
    db_session.commit()

    assert incidents._pending_questions_for_incident(db_session, incident, {}) == []
