"""사고별 맞춤 질문 생성(incident_questions_gemini)이 호출부와 주고받는 계약을 고정한다.

이 모듈의 반환값 하나에 흐름이 통째로 갈린다. 호출부(claim_review.pending_questions)는
`None`을 "생성이 안 됐으니 공용 질문 뱅크를 써라"로 읽는다. 그래서 **모델이 일부러 질문을
안 만든 경우**와 **호출 자체가 실패한 경우**를 같은 값으로 뭉뚱그리면, 프롬프트가
"사고 내용만으로 충분하면 빈 목록을 주세요"라고 시킨 결과가 정반대로 뒤집힌다 —
질문을 아예 안 하는 대신 공용 뱅크 전부를 물어보게 된다.

Gemini 키 없이도 돌아가야 하므로 응답만 가짜로 끼운다. 검증 대상은 응답을 받은 뒤의
분기이지 네트워크가 아니다.
"""
import json

import pytest

from app import config
from app.models.user import AppUser, Incident
from app.models.question import QuestionBank
from app.services import incident_questions_gemini as qgen


class _FakeResponse:
    def __init__(self, payload):
        self.parsed = None
        self.text = json.dumps(payload)


class _FakeModels:
    def __init__(self, payload):
        self._payload = payload

    def generate_content(self, *, model, contents, config):
        return _FakeResponse(self._payload)


class _FakeClient:
    def __init__(self, payload):
        self.models = _FakeModels(payload)


def _install(monkeypatch, payload=None, error=None):
    monkeypatch.setattr(config, "GEMINI_ENABLED", True)
    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-key")

    def _client(api_key=None):
        if error is not None:
            raise error
        return _FakeClient(payload)

    monkeypatch.setattr(qgen, "_get_client", _client)


def _incident(db):
    user = AppUser(nickname="테스터")
    db.add(user)
    db.flush()
    incident = Incident(user_id=user.user_id, free_text="파리에서 휴대폰을 도난당했어요")
    db.add(incident)
    db.flush()
    return incident


def _generate(db, incident, stage=qgen.STAGE_L1, answers=None):
    return qgen.generate_questions(
        db, incident=incident, stage=stage, l1_code="PROP", merged={}, answers=answers,
    )


def test_모델이_질문_없음이라고_하면_빈_목록을_돌려준다(db_session, monkeypatch):
    """빈 목록은 실패가 아니라 '더 물을 게 없다'는 판정이다. None으로 뭉개면 호출부가
    공용 뱅크 전체를 꺼내와서, 안 물어도 될 걸 도로 다 묻게 된다."""
    incident = _incident(db_session)
    _install(monkeypatch, payload={"items": []})

    assert _generate(db_session, incident) == []


def test_호출이_실패하면_None으로_공용_뱅크_폴백을_연다(db_session, monkeypatch):
    incident = _incident(db_session)
    _install(monkeypatch, error=RuntimeError("401 ACCESS_TOKEN_TYPE_UNSUPPORTED"))

    assert _generate(db_session, incident) is None


def test_받은_질문이_전부_쓸_수_없으면_None으로_폴백한다(db_session, monkeypatch):
    """모델은 질문을 만들려 했는데 하나도 쓸 수 없는 형태였다 — 이건 '충분해서 안 물었다'가
    아니라 생성 실패다. 이때는 공용 뱅크로 되돌아가는 쪽이 맞다."""
    incident = _incident(db_session)
    _install(monkeypatch, payload={"items": [
        {"question_text": "   ", "target_field": "ai_x", "impact_weight": 0.5},
        {"question_text": "무언가요?", "target_field": "!!!", "impact_weight": 0.5},
    ]})

    assert _generate(db_session, incident) is None


def test_만들어진_질문은_그_사고에만_묶여_저장된다(db_session, monkeypatch):
    incident = _incident(db_session)
    _install(monkeypatch, payload={"items": [
        {"question_text": "경찰에 도난 신고를 하셨나요?", "target_field": "police report", "impact_weight": 0.9},
        {"question_text": "도난·파손·분실 중 어느 쪽인가요?", "target_field": "item_damage_type", "impact_weight": 0.8},
    ]})

    rows = _generate(db_session, incident)

    assert [r.target_field for r in rows] == ["ai_police_report", "item_damage_type"]
    assert {r.incident_id for r in rows} == {incident.incident_id}


def _boom(api_key=None):
    raise AssertionError("재방문 경로에서 Gemini를 부르면 안 된다")


def test_질문_없음으로_끝난_사고는_다시_열어도_빈_목록이다(db_session, monkeypatch):
    """Gemini가 "더 물을 게 없다"고 판정해 결과 화면까지 간 사고를, 나중에 ?resultOf=로
    다시 열면 조회 전용 경로(create=False)를 탄다. 그때 "저장된 질문이 없다"를 "생성을
    안 했다"로 읽으면 공용 뱅크가 통째로 되살아나 — 이미 끝난 사고가 질문 화면으로
    되돌아간다. 생성을 했는지 여부는 사고에 남겨야 구분된다."""
    incident = _incident(db_session)
    _install(monkeypatch, payload={"items": []})
    assert _generate(db_session, incident) == []

    monkeypatch.setattr(qgen, "_get_client", _boom)
    again = qgen.generate_questions(
        db_session, incident=incident, stage=qgen.STAGE_L1, l1_code="PROP",
        merged={}, create=False,
    )

    assert again == []


def test_생성을_한_적_없는_사고는_None으로_공용_뱅크를_연다(db_session, monkeypatch):
    """Gemini 키가 없는 환경에서는 생성이 아예 일어나지 않는다. 그때는 공용 뱅크가
    유일한 질문 출처이므로 폴백이 반드시 열려야 한다."""
    incident = _incident(db_session)
    monkeypatch.setattr(qgen, "_get_client", _boom)

    result = qgen.generate_questions(
        db_session, incident=incident, stage=qgen.STAGE_L1, l1_code="PROP",
        merged={}, create=False,
    )

    assert result is None


def test_프롬프트에_이_대분류의_세부유형_후보가_들어간다(db_session, monkeypatch):
    """질문의 목적은 "무엇이 궁금한지"가 아니라 "약관을 어디까지 추려낼 수 있는지"다.
    같은 휴대품 사고라도 도난이냐 분실이냐에 따라 걸리는 조항이 통째로 달라지므로,
    모델이 그 갈림길을 알아야 그걸 가르는 질문을 만든다. 후보를 안 주면 모델은
    사고 내용만 보고 "언제 그랬나요" 같은, 조항을 하나도 못 가르는 질문을 만든다."""
    from app.models.kb import IncidentType

    root = IncidentType(l1_code="INJ", l2_code="INJ", name="상해", parent_id=None, is_active=True)
    db_session.add(root)
    db_session.flush()
    for code, name in [("INJ_OVS", "해외상해치료"), ("INJ_DOM", "귀국후 국내치료")]:
        db_session.add(IncidentType(
            l1_code="INJ", l2_code=code, name=name, parent_id=root.type_id, is_active=True,
        ))
    db_session.flush()

    incident = _incident(db_session)
    captured = {}

    class _Recording(_FakeModels):
        def generate_content(self, *, model, contents, config):
            captured["prompt"] = contents
            return _FakeResponse({"items": [
                {"question_text": "경찰 신고서를 받으셨나요?", "target_field": "ai_police_report",
                 "impact_weight": 0.9},
            ]})

    monkeypatch.setattr(config, "GEMINI_ENABLED", True)
    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(
        qgen, "_get_client",
        lambda api_key=None: type("C", (), {"models": _Recording(None)})(),
    )

    qgen.generate_questions(db_session, incident=incident, stage=qgen.STAGE_L1, l1_code="INJ", merged={})

    assert "해외상해치료" in captured["prompt"], "세부유형 후보가 프롬프트에 없다"
    assert "귀국후 국내치료" in captured["prompt"]


def test_1단계_질문에는_단계와_답변_형태가_붙는다(db_session, monkeypatch):
    """한 페이지에 예/아니오 버튼과 입력칸을 섞어 그리려면, 질문마다 어느 쪽인지가
    있어야 한다. 진단명·지연 시간처럼 약관의 금액·시간 조건과 직결되는 값은 예/아니오로
    받을 수 없다."""
    incident = _incident(db_session)
    _install(monkeypatch, payload={"items": [
        {"question_text": "경찰에 신고하셨나요?", "target_field": "ai_police_report",
         "impact_weight": 0.9, "answer_type": "yesno"},
        {"question_text": "도난당한 물건의 구입가가 얼마인가요?", "target_field": "ai_item_price",
         "impact_weight": 0.7, "answer_type": "text"},
    ]})

    rows = _generate(db_session, incident)

    assert [r.stage for r in rows] == [qgen.STAGE_L1, qgen.STAGE_L1]
    assert [r.answer_type for r in rows] == ["yesno", "text"]
    assert incident.question_stage == 1


def test_2단계_프롬프트에_1단계_답이_들어간다(db_session, monkeypatch):
    """2단계 질문의 존재 이유가 이것이다 — 1단계 답을 읽고 세부유형을 가르는 질문을
    새로 만든다. 답을 안 넘기면 1단계와 똑같은 걸 또 묻는다."""
    incident = _incident(db_session)
    captured = {}

    class _Recording(_FakeModels):
        def generate_content(self, *, model, contents, config):
            captured["prompt"] = contents
            return _FakeResponse({"items": [
                {"question_text": "잠금장치가 있었나요?", "target_field": "ai_lock",
                 "impact_weight": 0.8, "answer_type": "yesno"},
            ]})

    monkeypatch.setattr(config, "GEMINI_ENABLED", True)
    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(
        qgen, "_get_client",
        lambda api_key=None: type("C", (), {"models": _Recording(None)})(),
    )

    rows = _generate(db_session, incident, stage=qgen.STAGE_L2,
                     answers={"경찰에 신고하셨나요?": "아니오"})

    assert "경찰에 신고하셨나요?" in captured["prompt"]
    assert "아니오" in captured["prompt"]
    assert [r.stage for r in rows] == [qgen.STAGE_L2]
    assert incident.question_stage == 2


def test_단계마다_저장된_질문만_돌려준다(db_session, monkeypatch):
    """1단계 질문이 2단계 화면에 다시 나오면 사용자는 같은 걸 두 번 답하게 된다."""
    incident = _incident(db_session)
    _install(monkeypatch, payload={"items": [
        {"question_text": "경찰에 신고하셨나요?", "target_field": "ai_police_report",
         "impact_weight": 0.9, "answer_type": "yesno"},
    ]})
    _generate(db_session, incident)

    _install(monkeypatch, payload={"items": [
        {"question_text": "잠금장치가 있었나요?", "target_field": "ai_lock",
         "impact_weight": 0.8, "answer_type": "yesno"},
    ]})
    _generate(db_session, incident, stage=qgen.STAGE_L2)

    l1 = qgen.saved_questions(db_session, incident.incident_id, qgen.STAGE_L1)
    l2 = qgen.saved_questions(db_session, incident.incident_id, qgen.STAGE_L2)

    assert [r.target_field for r in l1] == ["ai_police_report"]
    assert [r.target_field for r in l2] == ["ai_lock"]
