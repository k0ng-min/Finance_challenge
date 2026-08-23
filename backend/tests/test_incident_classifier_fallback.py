import pytest

from app import config
from app.models.kb import IncidentType
from app.models.question import QuestionBank
from app.routers.incidents import _classify_incident
from app.services.claim_review import pending_questions, resolve_type_ids
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


def _break_api(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_ENABLED", True)
    monkeypatch.setattr(classifier, "_get_client", lambda: object())
    monkeypatch.setattr(
        classifier, "_generate_json",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )


def test_api가_죽어도_단서가_있으면_세부유형까지_좁힌다(db_session, monkeypatch):
    """예전에는 API 오류면 무조건 L1 루트로 보류했다. 그러면 그 대분류의 조항이 전부
    딸려와서, 수하물 지연 사고에 항공기납치 조항까지 같이 뜬다. 사고 내용에 단서가
    뚜렷하면 세부유형까지 좁힌다 — 대신 확신은 낮게 둬서 답변으로 다시 확인한다."""
    _seed_taxonomy(db_session)
    _break_api(monkeypatch)

    result = classifier.classify_l2(db_session, "TRV", "수하물이 아직 도착하지 않았어요")

    assert result.l2_code == "TRV_BAGGAGE_DELAY"
    assert result.confidence < classifier.DEFAULT_L2_AUTO_THRESHOLD


def test_api가_죽고_단서도_없으면_L1_루트로_보류한다(db_session, monkeypatch):
    _seed_taxonomy(db_session)
    _break_api(monkeypatch)

    result = classifier.classify_l2(db_session, "TRV", "여행 중에 좀 곤란한 일이 있었어요")
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

    def _classify_l2(_db, l1_code, _free_text, answers):
        assert l1_code == "PROP"
        assert answers["item_damage_type"] == "도난"
        return classifier.L2ClassifyResult(
            type_id=theft.type_id, l2_code=theft.l2_code,
            confidence=0.93, reason="도난 확인", abstained=False,
        )

    monkeypatch.setattr(classifier, "classify_l2", _classify_l2)
    merged = {"item_damage_type": ExtractedField("도난", 0.99, "소매치기")}
    final_type_id, final_confidence, _ = _classify_incident(
        db_session, "여행 중 문제가 생겼어요", merged,
        existing_type_id=initial_type_id, existing_confidence=initial_confidence,
    )

    assert "item_damage_type: 도난" in l1_inputs[1]
    assert final_type_id == theft.type_id
    assert final_confidence == 0.93


def test_new_type_suggestion_is_not_auto_created_or_marked_confident(db_session, monkeypatch):
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
    assert confidence == 0.0


def test_L1_루트로_보류된_사고도_그_대분류의_조항을_찾는다(db_session):
    """조항 매핑(clause_incident_map)은 전부 L2에 달려 있다. L2 분류가 확신이 없어 L1
    루트에 보류되면 루트 type_id로는 매핑이 하나도 안 걸려서 "관련 약관을 찾지 못했다"가
    나온다 — KB에 그 대분류 약관이 그대로 있는데도.

    예: "다리를 다쳤어요"가 상해(INJ)까지만 잡히고 세부유형이 안 정해진 경우."""
    _seed_taxonomy(db_session)
    root = db_session.query(IncidentType).filter_by(l1_code="INJ", parent_id=None).one()
    children = db_session.query(IncidentType).filter_by(parent_id=root.type_id).all()

    ids = resolve_type_ids(db_session, root.type_id, {})

    assert ids[0] == root.type_id
    assert {c.type_id for c in children} <= set(ids), "L1 루트만으로는 세부유형 조항을 못 찾는다"


def test_세부유형까지_정해졌으면_형제유형까지_끌어오지_않는다(db_session):
    """확신 있게 L2가 정해졌는데 같은 대분류의 다른 세부유형 조항까지 붙이면, 이번 사고와
    상관없는 담보가 "청구검토 후보"로 섞인다."""
    _seed_taxonomy(db_session)
    child = db_session.query(IncidentType).filter_by(l2_code="INJ_OVERSEAS_TREATMENT").one()

    assert resolve_type_ids(db_session, child.type_id, {}) == [child.type_id]


def test_Gemini가_없어도_사고_내용으로_대분류를_잡는다(monkeypatch):
    """예전에는 키가 없거나 호출이 실패하면 전부 SPC(특수·기타)로 보류했다. SPC에는
    상해 약관이 없으니 "다리를 다쳤어요"에도 관련 약관이 한 건도 안 걸렸다. 대분류만이라도
    사고 내용에서 직접 잡아 두면 그 대분류의 실제 약관 조항을 근거로 보여줄 수 있다."""
    monkeypatch.setattr(config, "GEMINI_ENABLED", False)

    assert classifier.classify_l1("다리를 다쳤어요")[0] == "INJ"
    assert classifier.classify_l1("파리에서 휴대폰을 도난당했어요")[0] == "PROP"
    assert classifier.classify_l1("항공편이 6시간 지연됐어요")[0] == "TRV"
    assert classifier.classify_l1("배탈이 나서 병원에 갔어요")[0] == "ILL"


def test_짚을_단서가_없으면_여전히_SPC로_보류한다(monkeypatch):
    """근거 없이 아무 대분류나 찍지 않는다 — 못 잡았으면 못 잡았다고 둔다."""
    monkeypatch.setattr(config, "GEMINI_ENABLED", False)

    assert classifier.classify_l1("그냥 좀 곤란한 일이 있었어요")[0] == "SPC"


def test_키워드로_잡은_대분류는_확신을_낮게_둔다(monkeypatch):
    """키워드 일치는 근거가 약하다. 확신을 높게 주면 세부유형 분류까지 자동으로 밀고
    들어가고 사용자에게 확인 질문도 안 묻게 된다 — 대분류만 잡고 나머지는 물어야 한다."""
    monkeypatch.setattr(config, "GEMINI_ENABLED", False)

    _code, confidence, _reason = classifier.classify_l1("다리를 다쳤어요")

    assert 0 < confidence < classifier.DEFAULT_L1_AUTO_THRESHOLD


def test_대분류는_먼저_걸린_단어가_아니라_더_많이_걸린_쪽으로_잡는다(monkeypatch):
    """예전에는 목록 순서대로 먼저 걸린 하나가 그대로 이겼다. "무릎이 깨졌고 발목도
    삐었어요"는 '깨졌'(휴대품 파손) 하나 때문에 휴대품 사고가 됐다 — 상해 단서가 둘
    있는데도. 단서 개수를 세서 더 많이 걸린 쪽을 고른다."""
    monkeypatch.setattr(config, "GEMINI_ENABLED", False)

    assert classifier.classify_l1("넘어져서 무릎이 깨졌고 발목도 삐었어요")[0] == "INJ"


def test_Gemini가_없어도_세부유형까지_좁힌다(db_session, monkeypatch):
    """대분류만 잡으면 그 대분류의 조항이 전부 딸려온다 — 도난인지 분실인지에 따라
    보상 여부가 갈리는데도 둘 다 보여준다. 단서가 뚜렷하면 세부유형까지 좁힌다."""
    _seed_taxonomy(db_session)
    monkeypatch.setattr(config, "GEMINI_ENABLED", False)

    theft = classifier.classify_l2(db_session, "PROP", "파리에서 소매치기를 당했어요")
    loss = classifier.classify_l2(db_session, "PROP", "그냥 어디서 잃어버렸어요")

    assert theft.l2_code == "PROP_THEFT"
    assert loss.l2_code == "PROP_LOSS"


def test_세부유형_단서가_없으면_좁히지_않는다(db_session, monkeypatch):
    """근거 없이 세부유형을 찍으면 엉뚱한 조항만 보여주고 맞는 조항은 감춘다."""
    _seed_taxonomy(db_session)
    monkeypatch.setattr(config, "GEMINI_ENABLED", False)

    result = classifier.classify_l2(db_session, "PROP", "여행 중에 좀 곤란한 일이 있었어요")

    assert result.l2_code is None and result.abstained


def test_남의_물건을_망가뜨린_건_휴대품이_아니라_배상책임이다(monkeypatch):
    """"깨졌"(내 물건이 깨짐)와 "깨뜨렸"(내가 남의 것을 깨뜨림)은 걸리는 약관이 통째로
    다르다. 앞은 휴대품손해, 뒤는 배상책임이다."""
    monkeypatch.setattr(config, "GEMINI_ENABLED", False)

    assert classifier.classify_l1("호텔 객실 유리를 깨뜨렸어요")[0] == "LIA"
    assert classifier.classify_l1("가방에 넣어둔 카메라가 깨졌어요")[0] == "PROP"


def test_띄어쓴_조기_귀국도_여행변경으로_잡는다(monkeypatch):
    """단서를 한 가지 표기로만 적어두면 띄어쓰기 하나에 대분류가 통째로 어긋난다."""
    monkeypatch.setattr(config, "GEMINI_ENABLED", False)

    assert classifier.classify_l1("여행 중 조기 귀국했어요")[0] == "CHG"
    assert classifier.classify_l1("일정을 중단하고 돌아왔어요")[0] == "CHG"
