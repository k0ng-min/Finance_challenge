"""대표 사용자 여정 두 개를 처음부터 끝까지 관통해 검증한다.

기능별 단위 테스트는 함수 하나씩만 본다. 그런데 이 서비스는 여행 생성 → 추천 → 보험사
비교 → 보험 등록 → 사고 접수 → 분류 → 담보 검토 → 서류 → 근거 조항이 줄줄이 이어지는
구조라, 단위 테스트가 전부 통과해도 이음매에서 깨질 수 있다. 실제로 이 저장소에서
백엔드가 필드명을 premium_total → published_premium으로 바꿨는데 프론트가 옛 이름을
계속 읽어 화면만 깨진 일이 있었다.

그래서 여기서는 "각 단계가 200을 주는가"가 아니라 다음 두 가지를 본다.

  1. 서비스 전체를 관통하는 불변식 — 단정적인 결과에는 반드시 근거 조항이 붙어 있고,
     근거가 없으면 '확인불가'로 내려간다.
  2. 이미 폐기한 구조가 되살아나지 않는가 — premium_total(여행일수 환산 보험료),
     score(절대 적합도 점수)처럼 팀이 의도적으로 없앤 필드.

Gemini는 부르지 않는다. 사고유형 분류는 고정값으로 갈아끼워, 검증 대상을 AI가 아니라
분류 이후의 파이프라인으로 못박는다(외부 API에 매달리면 테스트가 비결정적이 된다).
"""
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models.kb import IncidentType
from app.models.user import AppUser
from app.services import incident_classify_gemini as incident_classify
from app.services.incident_classify_gemini import L2ClassifyResult

# 근거가 없다고 정직하게 밝힌 결과. 이 상태만 근거 조항 없이 존재할 수 있다.
UNKNOWN_STATUSES = {"확인불가"}


@pytest.fixture
def client(kb_session):
    app.dependency_overrides[get_db] = lambda: kb_session
    yield TestClient(app)
    app.dependency_overrides.clear()


def assert_findings_are_grounded(findings, where: str):
    """단정적인 결과에는 근거 조항이 반드시 붙어 있어야 한다.

    이 프로젝트의 절대 원칙을 시스템 전체 수준에서 강제하는 검증이다. 어느 모듈이든
    근거 없이 단정하기 시작하면 여기서 걸린다.
    """
    for f in findings:
        if f["status"] in UNKNOWN_STATUSES:
            continue
        assert f["clauses"], (
            f"[{where}] '{f['status']}'로 단정했는데 근거 조항이 없습니다: "
            f"{f['finding_type']} / {f['target_ref']}"
        )
        for clause in f["clauses"]:
            assert clause["text"].strip(), f"[{where}] 근거 조항의 원문이 비어 있습니다"


def create_user(client, nickname="e2e"):
    """게스트 계정을 만들고 (user_id, 인증 헤더)를 돌려준다.

    게스트도 토큰으로 본인을 증명해야 자기 데이터를 꺼낼 수 있다(익명 접근은 막혀 있다).
    """
    res = client.post("/users", json={"nickname": nickname})
    assert res.status_code == 200, res.text
    body = res.json()
    return body["user_id"], {"Authorization": f"Bearer {body['token']}"}


def login(db, user_id: int, token: str = "e2e-token") -> dict:
    """이 사용자를 로그인 상태로 만들고 인증 헤더를 돌려준다.

    보험 등록은 로그인 계정만 할 수 있다(게스트는 401). OAuth를 태울 수는 없으므로
    세션 토큰을 직접 심는다 — 검증 대상은 로그인 절차가 아니라 그 다음 파이프라인이다.
    """
    user = db.get(AppUser, user_id)
    user.auth_provider = "kakao"
    user.session_token = token
    user.session_expires_at = datetime.utcnow() + timedelta(days=1)
    db.commit()
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------- Golden Path A
def test_가입_전_여정이_근거와_함께_끝까지_이어진다(client):
    """여행 생성 → 가입 전 추천 → 보험사 비교까지, 각 단계 결과가 다음 단계로 이어지는지."""
    user_id, auth = create_user(client, "가입전")

    trip = client.post("/trips", json={
        "user_id": user_id, "destination": "일본",
        "start_date": "2026-09-01", "end_date": "2026-09-05",
        "purpose": "관광", "activities": ["관광"],
        "companion_type": "혼자", "rental_car": False,
        "coverage_priority": ["PROP"],
    }, headers=auth)
    assert trip.status_code == 200, trip.text
    body = trip.json()

    # 고른 사고유형이 실제로 결과에 반영돼야 한다(빈 추천은 이어붙일 게 없다는 뜻).
    assert body["findings"], "PROP을 골랐는데 추천 결과가 하나도 없습니다"
    assert_findings_are_grounded(body["findings"], "가입 전 추천")

    # 여행에서 고른 조건이 보험사 비교로 그대로 넘어간다.
    ranking = client.get("/insurers/ranking", params={
        "tier": "균형형", "coverage_priority": "PROP",
        "destination": "일본", "trip_days": 5, "age": 30, "sex": "M",
    })
    assert ranking.status_code == 200, ranking.text
    rows = ranking.json()["ranking"]
    assert len(rows) >= 2, "비교할 보험사가 둘 이상은 나와야 합니다"

    for item in rows:
        assert item["dimensions"], "평가축이 비어 있습니다"
        for dim in item["dimensions"]:
            assert 0 <= dim["level"] <= 5
            # 근거가 없으면 0단계여야 한다 — 근거 부족을 유리하게 치지 않는다.
            if dim["level"] == 0:
                assert dim["status"] == "근거 부족"

        if item["published_premium"] is not None:
            assert item["premium_period_days"] == 1, "공시 기준 기간이 1일이 아닙니다"
        else:
            # 값이 없으면 왜 없는지 밝혀야 한다(조용히 빼지 않는다).
            assert item["premium_note"], "보험료가 없는데 사유가 비어 있습니다"


def test_근거_검증_자체가_동작한다():
    """위 여정들은 현재 근거 없는 단정을 만들지 않아서, 불변식 검사가 무증상으로 통과한다.
    그러면 이 검사가 살아 있는지 알 수 없으므로 여기서 직접 걸어본다 — 검사가 고장 나면
    나머지 E2E가 통과해도 아무것도 지켜주지 못한다."""
    ungrounded = [{
        "status": "청구검토후보", "finding_type": "추천담보",
        "target_ref": "가짜 담보", "clauses": [],
    }]
    with pytest.raises(AssertionError, match="단정했는데"):
        assert_findings_are_grounded(ungrounded, "자기검증")

    # 근거가 없어도 '확인불가'라고 밝힌 결과는 통과해야 한다(이게 정상 경로다).
    assert_findings_are_grounded(
        [{"status": "확인불가", "finding_type": "보장공백", "target_ref": "x", "clauses": []}],
        "자기검증",
    )


def test_폐기한_응답_필드가_스키마에_되살아나지_않는다():
    """구 필드가 되살아나는 것을 응답 본문으로는 못 잡는다 — Pydantic이 스키마에 없는 키를
    조용히 버려서, 라우터가 무엇을 담든 JSON에는 나타나지 않기 때문이다. 그래서 응답이 아니라
    스키마(=프론트와의 계약)를 직접 본다.

    premium_total: 공시값에 여행일수를 곱해 "내 견적"처럼 보이던 값. 실제로 이 저장소에서
      published_premium으로 바뀐 뒤 프론트가 옛 이름을 계속 읽어 화면이 깨진 적이 있다.
    score: 절대 적합도 점수. 상대 단계 비교로 대체됐다.
    """
    from app.schemas import InsurerRankOut

    fields = set(InsurerRankOut.model_fields)
    assert "premium_total" not in fields, "폐기한 premium_total이 스키마에 되살아났습니다"
    assert "score" not in fields, "폐기한 절대 점수(score)가 스키마에 되살아났습니다"
    # 대체 필드는 반드시 있어야 한다 — 없으면 화면이 보험료를 아예 못 그린다.
    assert {"published_premium", "premium_period_days", "dimensions"} <= fields


# ---------------------------------------------------------------- Golden Path B
@pytest.fixture
def fixed_classifier(monkeypatch, kb_session):
    """사고유형 분류를 PROP/PROP_THEFT로 고정한다.

    CI에서 Gemini를 부르지 않기 위함이자, 이 테스트의 검증 대상을 분류 정확도가 아니라
    '분류가 끝난 뒤의 파이프라인'으로 좁히기 위함이다.
    """
    theft = kb_session.query(IncidentType).filter_by(l2_code="PROP_THEFT").first()
    if theft is None:
        pytest.skip("PROP_THEFT 사고유형이 KB에 없습니다")

    monkeypatch.setattr(incident_classify, "classify_l1", lambda text: ("PROP", 1.0, "테스트 고정"))
    monkeypatch.setattr(incident_classify, "extract_modifiers", lambda text: {})
    monkeypatch.setattr(
        incident_classify, "classify_l2",
        lambda db, l1_code, free_text, answers=None: L2ClassifyResult(
            type_id=theft.type_id, l2_code="PROP_THEFT", confidence=1.0, reason="테스트 고정",
        ),
    )
    # 상황별 설명도 외부 호출이라 끈다(없어도 흐름은 그대로 이어진다).
    monkeypatch.setattr(incident_classify, "explain_docs_for_incident", lambda docs, ctx: None)
    return theft


def test_사고_후_여정이_담보와_서류까지_이어진다(client, kb_session, fixed_classifier):
    """보험 등록 → 사고 접수 → 담보 검토 → 필요서류 → 근거 조항."""
    user_id, auth = create_user(client, "사고후")

    trip = client.post("/trips", json={
        "user_id": user_id, "destination": "일본",
        "start_date": "2026-09-01", "end_date": "2026-09-05",
        "purpose": "관광", "activities": ["관광"],
        "companion_type": "혼자", "rental_car": False,
        "coverage_priority": ["PROP"],
    }, headers=auth).json()

    policy = client.post(f"/users/{user_id}/policies", headers=auth, json={
        "trip_id": trip["trip_id"],
        "insurer_name_raw": "삼성화재",
        "product_name_raw": None,
        "period_start": "2026-09-01",
        "period_end": "2026-09-05",
    })
    assert policy.status_code == 200, policy.text
    policy_id = policy.json()["user_policy_id"]

    incident = client.post("/incidents", json={
        "user_id": user_id,
        "trip_id": trip["trip_id"],
        "user_policy_id": policy_id,
        "insurer_code": None,
        "free_text": "일본 여행 중 숙소에서 휴대폰을 도난당했어요",
        "occurred_at": None,
    }, headers=auth)
    assert incident.status_code == 200, incident.text
    analysis = incident.json()

    # 고정한 분류가 실제로 반영됐는지 — 여기가 어긋나면 아래 검증이 의미를 잃는다.
    assert analysis["findings"], "사고 검토 결과가 비어 있습니다"
    assert_findings_are_grounded(analysis["findings"], "사고 후 검토")

    # 서류 체크리스트까지 이어지고, 각 항목이 표준서류에 연결돼 있어야 한다.
    checklist = client.get(f"/incidents/{analysis['incident_id']}/checklist", headers=auth)
    assert checklist.status_code == 200, checklist.text
    items = checklist.json()["items"]
    assert items, "필요서류가 하나도 나오지 않았습니다"
    for it in items:
        assert it["doc_name"].strip()
        assert it["acquire_location"] in {"현지only", "귀국가능", "공통"}


def test_근거_없는_단정은_확인불가로만_나온다(client, kb_session, fixed_classifier):
    """등록한 보험이 없으면 담보를 찾을 수 없다. 그때 '청구검토후보'라고 우기지 않고
    확인불가로 내려가는지 — 근거 없는 결과 금지 원칙의 반대 방향 검증이다."""
    user_id, auth = create_user(client, "근거없음")

    incident = client.post("/incidents", json={
        "user_id": user_id,
        "trip_id": None,
        "user_policy_id": None,
        "insurer_code": None,
        "free_text": "여행 중 가방을 도난당했어요",
        "occurred_at": None,
        "country": "일본",
        "new_trip_destination": "일본",
        "new_trip_start_date": "2026-09-01",
        "new_trip_end_date": "2026-09-05",
    }, headers=auth)
    assert incident.status_code == 200, incident.text
    findings = incident.json()["findings"]

    assert_findings_are_grounded(findings, "보험 미등록 사고")
    # 근거를 못 찾았으면 반드시 확인불가가 하나는 있어야 한다(조용히 빈 결과로 끝내지 않는다).
    assert any(f["status"] in UNKNOWN_STATUSES for f in findings), (
        "담보를 못 찾았는데 확인불가 안내가 없습니다"
    )
