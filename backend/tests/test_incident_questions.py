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
from app.routers import incidents as incidents_router
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


def _shared_question(db, text="입원하셨나요?", field="hospitalized", applies_to_l1=None, weight=0.5,
                     applies_to_l2=None):
    row = QuestionBank(
        context_type="사고후", question_text=text, target_field=field,
        impact_weight=weight, applies_to_l1=applies_to_l1, applies_to_l2=applies_to_l2,
        incident_id=None,
    )
    db.add(row)
    db.flush()
    return row


def _generated_question(db, incident_id, text="경찰 신고서를 받으셨나요?", field="ai_police_report",
                        stage="L1", answer_type="yesno"):
    row = QuestionBank(
        context_type="사고후", question_text=text, target_field=field,
        impact_weight=0.9, applies_to_l1=None, incident_id=incident_id,
        stage=stage, answer_type=answer_type,
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
    def generate(db, *, incident, stage, l1_code, merged, modifiers=None, answers=None, create=True):
        incident_id = incident.incident_id
        existing = (
            db.query(QuestionBank)
            .filter(QuestionBank.incident_id == incident_id, QuestionBank.stage == stage)
            .all()
        )
        if existing:
            return existing
        if not create:
            return None
        rows = [
            QuestionBank(
                context_type="사고후", question_text=text, target_field=f"ai_q{i}",
                impact_weight=0.9 - i * 0.1, applies_to_l1=None, incident_id=incident_id,
                stage=stage, answer_type="yesno",
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


def test_담보판단에_꼭_필요한_질문은_생성질문이_빼먹어도_함께_묻는다(db_session):
    """item_damage_type은 claim_review가 휴대품 L2(도난/파손/분실)를 가르는 유일한
    결정적 입력이다(_item_damage_type_id). 분실은 휴대품손해 특약에서 아예 빠지는
    보험사가 있어, 이걸 모르면 "청구 가능"과 "면책"이 갈리는 자리가 통째로 흐려진다.

    생성 질문은 그 사고에서만 중요한 걸 묻느라 이걸 빠뜨릴 수 있다. 모델의 판단에
    맡길 수 없는 자리라, 아직 답이 없으면 공용 뱅크에서 이 질문만은 같이 꺼낸다."""
    _shared_question(
        db_session, text="도난·파손·분실 중 어느 쪽인가요?", field="item_damage_type",
        applies_to_l1="PROP",
    )
    _shared_question(db_session, text="공통 질문", field="ai_common", applies_to_l1=None)
    incident = _incident(db_session, free_text="파리에서 휴대폰을 잃어버렸어요")
    _generated_question(db_session, incident.incident_id)

    questions = claim_review.pending_questions(
        db_session, "PROP", {}, incident=incident, generate=False,
    )

    # 공용 뱅크가 통째로 되살아나면 안 된다 — ai_common은 나오지 않아야 한다.
    assert [q.target_field for q in questions] == ["ai_police_report", "item_damage_type"]


def test_생성질문이_이미_그_필드를_물으면_공용_질문을_겹쳐_넣지_않는다(db_session):
    _shared_question(
        db_session, text="도난·파손·분실 중 어느 쪽인가요?", field="item_damage_type",
        applies_to_l1="PROP",
    )
    incident = _incident(db_session, free_text="파리에서 휴대폰을 도난당했어요")
    _generated_question(
        db_session, incident.incident_id, text="소매치기였나요?", field="item_damage_type",
    )

    questions = claim_review.pending_questions(
        db_session, "PROP", {}, incident=incident, generate=False,
    )

    assert [q.question_text for q in questions] == ["소매치기였나요?"]


def test_이미_답이_있으면_필수_질문도_다시_묻지_않는다(db_session):
    _shared_question(
        db_session, text="도난·파손·분실 중 어느 쪽인가요?", field="item_damage_type",
        applies_to_l1="PROP",
    )
    incident = _incident(db_session, free_text="파리에서 휴대폰을 도난당했어요")
    _generated_question(db_session, incident.incident_id)

    merged = {"item_damage_type": ExtractedField(value="도난", confidence=0.9)}
    questions = claim_review.pending_questions(
        db_session, "PROP", merged, incident=incident, generate=False,
    )

    assert [q.target_field for q in questions] == ["ai_police_report"]


def test_다른_대분류에서는_휴대품_질문을_끌어오지_않는다(db_session):
    _shared_question(
        db_session, text="도난·파손·분실 중 어느 쪽인가요?", field="item_damage_type",
        applies_to_l1="PROP",
    )
    incident = _incident(db_session)
    _generated_question(db_session, incident.incident_id)

    questions = claim_review.pending_questions(
        db_session, "INJ", {}, incident=incident, generate=False,
    )

    assert [q.target_field for q in questions] == ["ai_police_report"]


def test_시드는_사고별_생성질문을_공용_질문으로_착각하지_않는다(db_session, monkeypatch):
    """seed_questions는 target_field로 기존 행을 찾는다. 그런데 생성 질문도 같은 테이블에
    같은 target_field(diagnosis 등 — 프롬프트가 그 이름을 그대로 쓰라고 시킨다)로 들어온다.

    그걸 공용 행으로 오인하면 두 가지가 한꺼번에 깨진다. 공용 질문이 영영 안 만들어져
    Gemini가 없는 환경에서는 질문을 하나도 못 받고, 사고별 행에 공용 태그(applies_to_l1)가
    덧칠돼 그 사고 밖으로 새어 나갈 문이 열린다."""
    from app import seed_questions

    incident = _incident(db_session)
    _generated_question(db_session, incident.incident_id, text="진단명이 뭔가요?", field="diagnosis")
    db_session.commit()
    monkeypatch.setattr(seed_questions, "SessionLocal", lambda: db_session)

    seed_questions.run()

    shared = db_session.query(QuestionBank).filter(
        QuestionBank.target_field == "diagnosis",
        QuestionBank.incident_id.is_(None),
    ).all()
    assert len(shared) == 1

    generated = db_session.query(QuestionBank).filter(
        QuestionBank.incident_id.isnot(None)
    ).one()
    assert generated.applies_to_l1 is None


def test_세부유형이_정해지면_그_유형_전용_질문까지_묻는다(db_session):
    """대분류 질문만 있으면 "휴대품 사고"에 늘 같은 질문이 나온다. 도난이면 경찰
    신고서를, 분실이면 잃어버린 상황을 물어야 청구에 실제로 쓸 답이 모인다."""
    _shared_question(db_session, text="도난·파손·분실 중 어느 쪽인가요?", field="item_damage_type",
                     applies_to_l1="PROP", weight=0.9)
    _shared_question(db_session, text="도난 신고서를 받으셨나요?", field="prop_police_report",
                     applies_to_l1="PROP", applies_to_l2="PROP_THEFT", weight=0.8)
    _shared_question(db_session, text="어디서 잃어버리셨나요?", field="prop_loss_place",
                     applies_to_l1="PROP", applies_to_l2="PROP_LOSS", weight=0.8)

    questions = claim_review.pending_questions(db_session, "PROP", {}, l2_code="PROP_THEFT")

    assert [q.target_field for q in questions] == ["item_damage_type", "prop_police_report"]


def test_세부유형이_아직_없으면_전용_질문은_묻지_않는다(db_session):
    """어느 세부유형인지 모르는 채로 전용 질문을 다 꺼내면, 도난·파손·분실 질문이
    한꺼번에 쏟아진다."""
    _shared_question(db_session, text="도난·파손·분실 중 어느 쪽인가요?", field="item_damage_type",
                     applies_to_l1="PROP", weight=0.9)
    _shared_question(db_session, text="도난 신고서를 받으셨나요?", field="prop_police_report",
                     applies_to_l1="PROP", applies_to_l2="PROP_THEFT", weight=0.8)

    questions = claim_review.pending_questions(db_session, "PROP", {})

    assert [q.target_field for q in questions] == ["item_damage_type"]


def test_한_페이지_답변을_한_번에_저장하고_분석은_한_번만_돈다(client, db_session, monkeypatch):
    """질문이 한 화면에 다 뜨는 흐름이라, 답도 한 번에 들어온다. 답마다 따로 저장하면
    같은 사고 분석이 답변 수만큼 돌아 응답이 그만큼 느려지고 결과도 중간 상태가 섞인다."""
    _shared_question(db_session)
    db_session.commit()
    monkeypatch.setattr(
        claim_review.incident_questions_gemini, "generate_questions",
        _fake_generator(["경찰 신고서를 받으셨나요?", "가방은 잠겨 있었나요?"]),
    )
    body = client.post("/users", json={"nickname": "배치게스트"}).json()
    user_id, auth = body["user_id"], {"Authorization": f"Bearer {body['token']}"}
    analysis = client.post("/incidents", json={
        "user_id": user_id, "free_text": "휴대폰을 소매치기당했어요",
    }, headers=auth).json()
    incident_id = analysis["incident_id"]
    questions = analysis["pending_questions"]
    assert len(questions) == 2

    runs = []
    original = incidents_router._run_analysis
    monkeypatch.setattr(
        incidents_router, "_run_analysis",
        lambda db, incident, merged: runs.append(1) or original(db, incident, merged),
    )

    res = client.post(f"/incidents/{incident_id}/answers/batch", json={
        "answers": [
            {"question_id": questions[0]["question_id"], "answer_text": "예"},
            {"question_id": questions[1]["question_id"], "answer_text": "아니오"},
        ],
        "extra_note": "지하철에서 당했어요",
    }, headers=auth)

    assert res.status_code == 200, res.text
    assert len(runs) == 1, "답변 수만큼 분석이 돌면 안 된다"

    logs = client.get(f"/incidents/{incident_id}", headers=auth)
    assert logs.status_code == 200


def test_기타_자유입력은_사고에_남아_재분류에_쓰인다(client, db_session, monkeypatch):
    """예/아니오로 다 담기지 않는 이야기를 받는 칸이다. 받아만 두고 버리면 물어본
    의미가 없다 — 사고 수식자로 남겨 재분류·조항 판단에 들어가야 한다."""
    from app.models.user import Incident

    _shared_question(db_session)
    db_session.commit()
    monkeypatch.setattr(
        claim_review.incident_questions_gemini, "generate_questions",
        _fake_generator(["경찰 신고서를 받으셨나요?"]),
    )
    body = client.post("/users", json={"nickname": "기타게스트"}).json()
    user_id, auth = body["user_id"], {"Authorization": f"Bearer {body['token']}"}
    analysis = client.post("/incidents", json={
        "user_id": user_id, "free_text": "휴대폰을 소매치기당했어요",
    }, headers=auth).json()
    incident_id = analysis["incident_id"]

    client.post(f"/incidents/{incident_id}/answers/batch", json={
        "answers": [],
        "extra_note": "지하철 4호선에서 당했습니다",
    }, headers=auth)

    incident = db_session.get(Incident, incident_id)
    db_session.refresh(incident)
    assert "지하철 4호선" in (incident.modifiers or "")


def test_질문에는_예아니오인지_입력칸인지가_같이_내려온다(client, db_session, monkeypatch):
    """한 페이지에 버튼과 입력칸을 섞어 그리려면 화면이 그걸 알아야 한다."""
    _shared_question(db_session)
    db_session.commit()
    monkeypatch.setattr(
        claim_review.incident_questions_gemini, "generate_questions",
        _fake_generator(["경찰 신고서를 받으셨나요?"]),
    )
    body = client.post("/users", json={"nickname": "형태게스트"}).json()
    user_id, auth = body["user_id"], {"Authorization": f"Bearer {body['token']}"}
    analysis = client.post("/incidents", json={
        "user_id": user_id, "free_text": "휴대폰을 소매치기당했어요",
    }, headers=auth).json()

    question = analysis["pending_questions"][0]
    assert question["answer_type"] == "yesno"
    assert question["stage"] == "L1"
