"""사고별 맞춤 질문(incident_questions_gemini)이 공용 질문 뱅크와 섞이지 않는지 확인한다.

질문에는 두 종류가 있다.
  · 공용 뱅크(seed_questions.py) — incident_id=None. 모든 사고에서 후보가 된다.
  · 사고별 생성 질문 — incident_id=그 사고. 그 사고 한 건에서만 후보가 돼야 한다.

둘을 한 테이블(question_bank)에 담으므로, 사고별 질문이 다른 사고로 새어 나가지
않는 것이 이 기능의 유일한 위험 지점이다.
"""
import pytest

from app.models.user import AppUser, Incident
from app.models.question import QuestionBank
from app.services import claim_review
from app.services.nlu import ExtractedField


def _incident(db, free_text="발목이 부러져서 병원에 갔어요"):
    user = AppUser(nickname="테스터")
    db.add(user)
    db.flush()
    incident = Incident(user_id=user.user_id, free_text=free_text)
    db.add(incident)
    db.flush()
    return incident


def _shared_question(db, text="입원하셨나요?", field="hospitalized"):
    row = QuestionBank(
        context_type="사고후", question_text=text, target_field=field,
        impact_weight=0.5, applies_to_l1=None, incident_id=None,
    )
    db.add(row)
    db.flush()
    return row


def _generated_question(db, incident_id, text="경찰 신고서를 받으셨나요?", field="ai_police_report"):
    row = QuestionBank(
        context_type="사고후", question_text=text, target_field=field,
        impact_weight=0.9, applies_to_l1=None, incident_id=incident_id,
    )
    db.add(row)
    db.flush()
    return row


def test_다른_사고의_생성질문은_후보에_섞이지_않는다(db_session):
    _shared_question(db_session)
    other = _incident(db_session)
    _generated_question(db_session, other.incident_id)
    mine = _incident(db_session)

    questions = claim_review.pending_questions(db_session, "INJ", {}, incident=mine, generate=False)

    assert [q.target_field for q in questions] == ["hospitalized"]


def test_incident을_안_넘기면_공용_질문만_나온다(db_session):
    _shared_question(db_session)
    other = _incident(db_session)
    _generated_question(db_session, other.incident_id)

    questions = claim_review.pending_questions(db_session, "INJ", {})

    assert [q.target_field for q in questions] == ["hospitalized"]


def test_생성질문이_있으면_공용_질문_대신_그것을_쓴다(db_session):
    _shared_question(db_session)
    incident = _incident(db_session)
    _generated_question(db_session, incident.incident_id)

    questions = claim_review.pending_questions(db_session, "INJ", {}, incident=incident, generate=False)

    assert [q.target_field for q in questions] == ["ai_police_report"]


def test_이미_답한_생성질문은_다시_묻지_않는다(db_session):
    incident = _incident(db_session)
    _generated_question(db_session, incident.incident_id)
    _generated_question(db_session, incident.incident_id, text="잠금장치가 있었나요?", field="ai_lock_state")

    questions = claim_review.pending_questions(
        db_session, "PROP", {}, modifiers={"ai_police_report": "네 받았어요"},
        incident=incident, generate=False,
    )

    assert [q.target_field for q in questions] == ["ai_lock_state"]


def test_생성질문이_담보필드를_쓰면_merged로도_걸러진다(db_session):
    incident = _incident(db_session)
    _generated_question(db_session, incident.incident_id, text="입원하셨나요?", field="hospitalized")
    _generated_question(db_session, incident.incident_id, text="수술하셨나요?", field="surgery")

    merged = {"hospitalized": ExtractedField(value=True, confidence=0.9)}
    questions = claim_review.pending_questions(
        db_session, "INJ", merged, incident=incident, generate=False,
    )

    assert [q.target_field for q in questions] == ["surgery"]


def test_생성에_실패하면_공용_질문으로_되돌아간다(db_session, monkeypatch):
    _shared_question(db_session)
    incident = _incident(db_session)
    monkeypatch.setattr(
        claim_review.incident_questions_gemini, "generate_questions",
        lambda *a, **kw: None,
    )

    questions = claim_review.pending_questions(db_session, "INJ", {}, incident=incident, generate=True)

    assert [q.target_field for q in questions] == ["hospitalized"]


def test_generate가_False면_Gemini를_부르지_않는다(db_session, monkeypatch):
    incident = _incident(db_session)
    called = []
    monkeypatch.setattr(
        claim_review.incident_questions_gemini, "generate_questions",
        lambda *a, **kw: called.append(kw) or None,
    )

    claim_review.pending_questions(db_session, "INJ", {}, incident=incident, generate=False)

    assert called and called[0]["create"] is False


def test_사고를_지우면_그_사고의_생성질문도_같이_지워진다(db_session):
    """생성 질문은 그 사고 한 건에만 쓰인다 — 사고가 사라지면 아무도 못 쓰는 행으로 남는다."""
    from app.services.deletion import delete_incident_cascade

    shared = _shared_question(db_session)
    incident = _incident(db_session)
    _generated_question(db_session, incident.incident_id)
    other = _incident(db_session)
    other_row = _generated_question(db_session, other.incident_id)
    db_session.commit()

    delete_incident_cascade(db_session, incident)
    db_session.commit()

    left = db_session.query(QuestionBank).order_by(QuestionBank.question_id).all()
    assert [q.question_id for q in left] == [shared.question_id, other_row.question_id]


# ── 라우터까지 이어지는 경로 ────────────────────────────────────────────────
# 생성 자체는 Gemini에 달려 있어 테스트에서 부르지 않는다. 여기서 확인하는 건
# "만들어진 질문이 API 응답까지 나오는가"와 "조회만 하는 경로에서는 새로 만들지
# 않는가" 두 가지 — 즉 라우터가 붙인 generate 플래그가 실제로 지켜지는지다.

@pytest.fixture
def client(db_session):
    from fastapi.testclient import TestClient
    from app.database import get_db
    from app.main import app

    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


def _fake_generator(texts):
    """Gemini 대신 정해진 질문을 만들어 저장하는 스텁."""
    def generate(db, *, incident_id, free_text, l1_code, merged, modifiers=None, create=True):
        existing = db.query(QuestionBank).filter(QuestionBank.incident_id == incident_id).all()
        if existing:
            return existing
        if not create:
            return None
        rows = [
            QuestionBank(
                context_type="사고후", question_text=text, target_field=f"ai_q{i}",
                impact_weight=0.9 - i * 0.1, applies_to_l1=None, incident_id=incident_id,
            ) for i, text in enumerate(texts)
        ]
        for row in rows:
            db.add(row)
        db.flush()
        return rows
    return generate


def test_접수_응답에_사고별_질문이_나오고_조회해도_그대로다(client, db_session, monkeypatch):
    _shared_question(db_session)
    db_session.commit()
    monkeypatch.setattr(
        claim_review.incident_questions_gemini, "generate_questions",
        _fake_generator(["경찰 신고서를 받으셨나요?", "가방은 잠겨 있었나요?"]),
    )
    res = client.post("/users", json={"nickname": "질문게스트"})
    body = res.json()
    user_id, auth = body["user_id"], {"Authorization": f"Bearer {body['token']}"}

    created = client.post("/incidents", json={
        "user_id": user_id, "free_text": "휴대폰을 소매치기당했어요",
    }, headers=auth)
    assert created.status_code == 200, created.text
    analysis = created.json()
    assert [q["question_text"] for q in analysis["pending_questions"]] == [
        "경찰 신고서를 받으셨나요?", "가방은 잠겨 있었나요?",
    ]

    # 다시 조회해도 같은 질문이어야 한다 — 조회 때마다 새로 만들면 답한 질문이 되살아난다.
    fetched = client.get(f"/incidents/{analysis['incident_id']}", headers=auth).json()
    assert [q["question_id"] for q in fetched["pending_questions"]] \
        == [q["question_id"] for q in analysis["pending_questions"]]


def test_조회만_하는_경로는_질문을_새로_만들지_않는다(client, db_session, monkeypatch):
    """생성은 접수·답변처럼 커밋이 뒤따르는 경로에서만 일어나야 한다."""
    _shared_question(db_session)
    db_session.commit()
    res = client.post("/users", json={"nickname": "조회게스트"})
    body = res.json()
    user_id, auth = body["user_id"], {"Authorization": f"Bearer {body['token']}"}
    created = client.post("/incidents", json={
        "user_id": user_id, "free_text": "휴대폰을 소매치기당했어요",
    }, headers=auth)
    incident_id = created.json()["incident_id"]

    calls = []
    def spy(db, **kw):
        calls.append(kw)
        return None
    monkeypatch.setattr(claim_review.incident_questions_gemini, "generate_questions", spy)

    client.get(f"/incidents/{incident_id}", headers=auth)

    assert calls and all(kw["create"] is False for kw in calls)
