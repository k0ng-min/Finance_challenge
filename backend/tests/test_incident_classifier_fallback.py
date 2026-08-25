import pytest

from app import config
from app.models.kb import IncidentType
from app.models.question import QuestionBank
from app.routers.incidents import _classify_incident
from app.services.claim_review import pending_questions
from app.services import incident_classify_gemini as classifier
from app.services.nlu import ExtractedField

TAXONOMY = [
    ("INJ", "상해", [
        ("INJ_DEATH_DISABILITY", "상해사망·후유장해"),
        ("INJ_OVERSEAS_TREATMENT", "해외상해치료"),
        ("INJ_DOMESTIC_TREATMENT", "귀국후 국내치료"),
    ]),
    ("ILL", "질병", [
        ("ILL_DEATH_DISABILITY", "질병사망·고도후유장해"),
        ("ILL_OVERSEAS_TREATMENT", "해외질병치료"),
    ]),
    ("PROP", "휴대품·재물", [
        ("PROP_THEFT", "도난"),
        ("PROP_DAMAGE", "파손"),
        ("PROP_LOSS", "분실"),
    ]),
    ("TRV", "운송", [
        ("TRV_FLIGHT_DELAY", "항공지연·결항"),
        ("TRV_BAGGAGE_DELAY", "수하물지연"),
    ]),
]


def _seed_taxonomy(db):
    for l1_code, l1_name, children in TAXONOMY:
        root = IncidentType(
            l1_code=l1_code, l2_code=l1_code, name=l1_name,
            parent_id=None, is_active=True,
        )
        db.add(root)
        db.flush()
        for l2_code, name in children:
            db.add(IncidentType(
                l1_code=l1_code, l2_code=l2_code, name=name,
                parent_id=root.type_id, is_active=True,
            ))
    db.commit()


def test_gemini_disabled_does_not_force_first_l2(db_session, monkeypatch):
    _seed_taxonomy(db_session)
    monkeypatch.setattr(config, "GEMINI_ENABLED", False)

    result = classifier.classify_l2(db_session, "PROP", "휴대품에 문제가 생겼어요")
    root = db_session.query(IncidentType).filter_by(l2_code="PROP").one()

    assert result.abstained is True
    assert result.type_id == root.type_id
    assert result.l2_code is None
    assert result.confidence == 0.0


def test_api_error_abstains_to_l1_root(db_session, monkeypatch):
    _seed_taxonomy(db_session)
    monkeypatch.setattr(config, "GEMINI_ENABLED", True)
    monkeypatch.setattr(classifier, "_get_client", lambda: object())
    monkeypatch.setattr(classifier, "_generate_json", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("boom")))

    result = classifier.classify_l2(db_session, "TRV", "수하물이 아직 도착하지 않았어요")
    root = db_session.query(IncidentType).filter_by(l2_code="TRV").one()

    assert result.abstained is True
    assert result.type_id == root.type_id
    assert result.l2_code is None


def test_evaluation_mode_propagates_api_error(db_session, monkeypatch):
    _seed_taxonomy(db_session)
    monkeypatch.setattr(config, "GEMINI_ENABLED", True)
    monkeypatch.setattr(classifier, "_get_client", lambda: object())
    monkeypatch.setattr(
        classifier, "_generate_json",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("quota")),
    )

    with pytest.raises(RuntimeError, match="quota"):
        classifier.classify_l2(
            db_session, "TRV", "수하물이 오지 않았어요", raise_on_error=True,
        )


def test_low_confidence_l2_abstains(db_session, monkeypatch):
    _seed_taxonomy(db_session)
    monkeypatch.setattr(config, "GEMINI_ENABLED", True)
    monkeypatch.setattr(classifier, "_get_client", lambda: object())
    monkeypatch.setattr(
        classifier, "_generate_json",
        lambda *_args, **_kwargs: classifier._L2ClassifySchema(
            l2_code="PROP_THEFT", confidence=0.49, reason="도난인지 분실인지 불명확"
        ),
    )

    result = classifier.classify_l2(db_session, "PROP", "휴대폰이 없어졌어요", auto_threshold=0.70)

    assert result.abstained is True
    assert result.l2_code is None
    assert result.type_id == db_session.query(IncidentType).filter_by(l2_code="PROP").one().type_id


def test_high_confidence_l2_is_accepted(db_session, monkeypatch):
    _seed_taxonomy(db_session)
    monkeypatch.setattr(config, "GEMINI_ENABLED", True)
    monkeypatch.setattr(classifier, "_get_client", lambda: object())
    monkeypatch.setattr(
        classifier, "_generate_json",
        lambda *_args, **_kwargs: classifier._L2ClassifySchema(
            l2_code="PROP_THEFT", confidence=0.91, reason="소매치기를 명시함"
        ),
    )

    result = classifier.classify_l2(db_session, "PROP", "소매치기가 휴대폰을 훔쳐갔어요")

    assert result.abstained is False
    assert result.l2_code == "PROP_THEFT"
    assert result.type_id == db_session.query(IncidentType).filter_by(l2_code="PROP_THEFT").one().type_id


def test_incomplete_model_response_abstains(db_session, monkeypatch):
    _seed_taxonomy(db_session)
    monkeypatch.setattr(config, "GEMINI_ENABLED", True)
    monkeypatch.setattr(classifier, "_get_client", lambda: object())
    monkeypatch.setattr(
        classifier, "_generate_json",
        lambda *_args, **_kwargs: classifier._L2ClassifySchema(confidence=0.8, reason="판단 불가"),
    )

    result = classifier.classify_l2(db_session, "ILL", "몸이 안 좋아요")

    assert result.abstained is True
    assert result.l2_code is None


def test_low_l1_confidence_skips_l2_and_keeps_root(db_session, monkeypatch):
    _seed_taxonomy(db_session)
    monkeypatch.setattr(classifier, "classify_l1", lambda _text: ("INJ", 0.31, "부상 여부 불명확"))
    monkeypatch.setattr(classifier, "extract_modifiers", lambda _text: {})
    called = {"l2": False}

    def _unexpected_l2(*_args, **_kwargs):
        called["l2"] = True
        raise AssertionError("낮은 L1 신뢰도에서는 L2를 호출하면 안 됩니다")

    monkeypatch.setattr(classifier, "classify_l2", _unexpected_l2)
    type_id, confidence, _ = _classify_incident(db_session, "여행 중 문제가 있었어요", {})

    assert called["l2"] is False
    assert type_id == db_session.query(IncidentType).filter_by(l2_code="INJ").one().type_id
    assert confidence == 0.31

    db_session.add(QuestionBank(
        context_type="사고후", question_text="어디에서 치료받았나요?",
        target_field="treatment_location", impact_weight=0.9, applies_to_l1="INJ",
    ))
    db_session.commit()
    questions = pending_questions(db_session, "INJ", {}, {})
    assert [q.question_text for q in questions] == ["어디에서 치료받았나요?"]


def test_low_confidence_l1_can_change_after_followup(db_session, monkeypatch):
    _seed_taxonomy(db_session)
    l1_inputs = []
    l1_predictions = iter([
        ("INJ", 0.30, "최초 설명만으로 불명확"),
        ("PROP", 0.95, "후속 답변에 휴대품 도난이 명확"),
    ])

    def _classify_l1(text):
        l1_inputs.append(text)
        return next(l1_predictions)

    monkeypatch.setattr(classifier, "classify_l1", _classify_l1)
    monkeypatch.setattr(classifier, "extract_modifiers", lambda _text: {})

    initial_type_id, initial_confidence, _ = _classify_incident(
        db_session, "여행 중 문제가 생겼어요", {},
    )
    assert initial_type_id == db_session.query(IncidentType).filter_by(l2_code="INJ").one().type_id
    assert initial_confidence == 0.30

    theft = db_session.query(IncidentType).filter_by(l2_code="PROP_THEFT").one()

    merged = {"item_damage_type": ExtractedField("도난", 0.99, "소매치기")}
    final_type_id, final_confidence, _ = _classify_incident(
        db_session, "여행 중 문제가 생겼어요", merged,
        existing_type_id=initial_type_id, existing_confidence=initial_confidence,
    )

    assert "item_damage_type: 도난" in l1_inputs[1]
    assert final_type_id == theft.type_id
    # 명시 답변과 taxonomy가 1:1이므로 외부 모델 없이 확정한다.
    assert final_confidence == 1.0


def test_new_type_suggestion_is_not_auto_created_and_keeps_l1_confidence(db_session, monkeypatch):
    _seed_taxonomy(db_session)
    monkeypatch.setattr(classifier, "classify_l1", lambda _text: ("PROP", 0.91, "재물 피해"))
    monkeypatch.setattr(classifier, "extract_modifiers", lambda _text: {})
    monkeypatch.setattr(
        classifier, "classify_l2",
        lambda *_args, **_kwargs: classifier.L2ClassifyResult(
            type_id=db_session.query(IncidentType).filter_by(l2_code="PROP").one().type_id,
            l2_code=None, confidence=0.95, reason="새 유형 후보",
            new_type_suggested={"name": "검수 전 유형", "reason": "기존 후보 외"}, abstained=True,
        ),
    )

    before = db_session.query(IncidentType).count()
    type_id, confidence, _ = _classify_incident(db_session, "특수한 재물 피해", {})

    assert db_session.query(IncidentType).count() == before
    assert type_id == db_session.query(IncidentType).filter_by(l2_code="PROP").one().type_id
    assert confidence == 0.91
