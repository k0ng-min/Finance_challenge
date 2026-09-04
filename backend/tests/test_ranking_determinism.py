"""보험사 추천의 최종 순위가 100% 결정적인지를 못 박는다.

예전에는 결정적 점수(ranking_score)와 Gemini가 매긴 0~100 점수를 8:2로 섞어 최종
총점을 만들고, 그 총점으로 다시 정렬했다. 그래서 같은 자료·같은 입력인데도

  · 모델이 바뀌면 순위가 바뀔 수 있었고,
  · AI를 켜고 끄는 것만으로 1위가 달라질 수 있었고,
  · "왜 이 보험사가 1위인가"의 마지막 20%를 수식으로 되짚을 수 없었다.

이제 순위와 총점은 score_insurers()의 계산만으로 끝난다. Gemini는 확정된 순위를
받아 이유 문장만 만든다. 여기서 지키는 것:

  A. AI를 끈 결과와 켠 결과의 rank·total_score가 완전히 같다.
  B. 모델 응답이 깨져도 rank·total_score가 같다.
  C. 동점은 보험사 코드순이라는 기존 규칙을 그대로 지킨다(무작위 아님).
  D. 같은 입력을 여러 번 불러도 늘 같은 결과.
"""
import json

import pytest
from fastapi.testclient import TestClient

from app import config
from app.database import get_db
from app.main import app
from app.models.kb import Insurer, InsurerComparisonMetric, InsurerPremium
from app.services import insurer_ranking_explain_gemini as explainer
from app.services import ranking_score

TIER = "균형형"
QUERY = f"/insurers/ranking?tier={TIER}&plan_tier=1&age=30&sex=M&trip_days=7"


@pytest.fixture
def client(kb_session):
    """실제 약관 KB 사본으로 돈다 — 순위는 KB가 있어야 의미가 있다."""
    app.dependency_overrides[get_db] = lambda: kb_session
    explainer.clear_cache()
    yield TestClient(app)
    app.dependency_overrides.clear()
    explainer.clear_cache()


def _ranks(payload: dict) -> list[tuple[int, str, float]]:
    return [(r["rank"], r["insurer_code"], r["total_score"]) for r in payload["ranking"]]


# --- 가짜 Gemini ------------------------------------------------------------

class _FakeResponse:
    def __init__(self, payload):
        self.parsed = None
        self.text = json.dumps(payload)


class _FakeClient:
    def __init__(self, payload, recorder):
        outer = self

        class _Models:
            def generate_content(self, *, model, contents, config):
                recorder.append(contents)
                return _FakeResponse(outer._payload)

        self._payload = payload
        self.models = _Models()


def _install_gemini(monkeypatch, payload, recorder):
    monkeypatch.setattr(config, "GEMINI_ENABLED", True)
    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(explainer, "_get_client", lambda: _FakeClient(payload, recorder))
    explainer.clear_cache()


def _disable_gemini(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_ENABLED", False)
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    explainer.clear_cache()


# --- Case A: AI on/off로 순위가 달라지지 않는다 -----------------------------

def test_A_AI를_끄든_켜든_순위와_총점이_같다(client, monkeypatch):
    _disable_gemini(monkeypatch)
    off = client.get(QUERY)
    assert off.status_code == 200, off.text
    off_ranks = _ranks(off.json())
    assert off_ranks, "순위가 비어 있어 비교할 수 없습니다"

    # 켠 쪽은 순서를 뒤집으려 드는 응답을 준다 — 그래도 순위가 흔들리면 안 된다.
    codes = [code for _, code, _ in off_ranks]
    payload = {"items": [
        {"insurer_code": code, "reasons": [f"{code} 설명 문장"]} for code in codes
    ]}
    calls = []
    _install_gemini(monkeypatch, payload, calls)
    on = client.get(QUERY)
    assert on.status_code == 200, on.text

    assert _ranks(on.json()) == off_ranks, "AI를 켜자 순위나 총점이 달라졌습니다"
    assert calls, "설명 생성을 위해 모델이 불렸어야 합니다"
    # 역할은 문장뿐 — 설명은 실제로 바뀌어야 한다.
    assert on.json()["ranking"][0]["reasons"] == [f"{codes[0]} 설명 문장"]


def test_A2_모델은_점수를_돌려줄_수_없다(client, monkeypatch):
    """설명 스키마에 점수 필드 자체가 없다. 모델이 점수를 써 보내도 들어올 곳이 없다."""
    fields = explainer._ExplanationItem.model_fields
    assert set(fields) == {"insurer_code", "reasons"}, f"설명 스키마에 점수가 생겼습니다: {set(fields)}"


# --- Case B: 응답이 깨져도 순위는 그대로 ------------------------------------

@pytest.mark.parametrize("broken", [
    {"items": [{"insurer_code": "없는보험사", "reasons": ["엉뚱"]}]},   # 코드 불일치
    {"items": []},                                                      # 빈 응답
    {"쓰레기": True},                                                    # 스키마 위반
])
def test_B_모델_응답이_깨져도_순위와_총점이_같다(client, monkeypatch, broken):
    _disable_gemini(monkeypatch)
    baseline = _ranks(client.get(QUERY).json())

    calls = []
    _install_gemini(monkeypatch, broken, calls)
    res = client.get(QUERY)

    assert res.status_code == 200, res.text
    assert _ranks(res.json()) == baseline, "모델 응답이 깨졌는데 순위가 달라졌습니다"
    # 설명은 결정적 문장으로 남는다 — 비어 있으면 안 된다.
    assert all(r["reasons"] for r in res.json()["ranking"])


def test_B2_모델_호출이_터져도_순위와_총점이_같다(client, monkeypatch):
    _disable_gemini(monkeypatch)
    baseline = _ranks(client.get(QUERY).json())

    monkeypatch.setattr(config, "GEMINI_ENABLED", True)
    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-key")

    def boom():
        raise RuntimeError("네트워크 끊김")

    monkeypatch.setattr(explainer, "_get_client", boom)
    explainer.clear_cache()

    res = client.get(QUERY)
    assert _ranks(res.json()) == baseline


# --- Case C: 동점 처리는 기존 규칙 그대로 -----------------------------------

def test_C_동점이면_보험사_코드순이고_무작위가_아니다(db_session):
    """축 자료가 완전히 같은 두 보험사는 총점이 같다. 그때 순서를 무작위로 흔들면
    같은 입력에 다른 화면이 나온다 — 코드순으로 고정한다."""
    for code in ("ZZZ", "AAA", "MMM"):
        insurer = Insurer(code=code, name=f"{code}보험")
        db_session.add(insurer)
        db_session.flush()
        db_session.add(InsurerComparisonMetric(
            insurer_id=insurer.insurer_id, plan_name="표준형", category="의료비",
            metric_label="해외 상해의료비", value_text="3000", unit="만원",
            category_order=1, sort_order=0,
        ))
        db_session.add(InsurerPremium(
            insurer_id=insurer.insurer_id, plan_name="표준형", sex="M", age=30,
            premium=10000, period_days=1,
        ))
    db_session.commit()

    ranking = [
        {"insurer_code": code, "insurer_name": f"{code}보험", "dimensions": []}
        for code in ("ZZZ", "AAA", "MMM")
    ]
    scored = ranking_score.score_insurers(
        db_session, tier_code=TIER, plan_tier=1, trip_context={}, ranking=ranking,
        age=30, sex="M",
    )

    totals = {s.insurer_code: s.total for s in scored}
    assert len(set(round(t, 9) for t in totals.values())) == 1, "동점 상황을 만들지 못했습니다"
    assert [s.insurer_code for s in scored] == ["AAA", "MMM", "ZZZ"]


# --- Case D: 같은 입력 = 같은 결과 ------------------------------------------

def test_D_같은_입력을_여러_번_불러도_결과가_같다(client, monkeypatch):
    _disable_gemini(monkeypatch)
    results = [_ranks(client.get(QUERY).json()) for _ in range(3)]
    assert results[0] == results[1] == results[2]
    assert results[0], "순위가 비어 있어 비교할 수 없습니다"


# --- 설명가능성: 총점이 축 기여도의 합으로 되짚어진다 -----------------------

def test_응답의_총점은_축_기여도의_합으로_되짚어진다(client, monkeypatch):
    """"왜 이 순서인가"가 응답 안에서 끝까지 설명돼야 한다. 축을 그대로 내려보내는 것이
    그 약속의 실체다 — 화면이 없어도 API만으로 감사할 수 있다."""
    _disable_gemini(monkeypatch)
    for row in client.get(QUERY).json()["ranking"]:
        axes = row["axes"]
        assert axes, "축 정보가 응답에 없습니다"
        합 = sum(a["contribution"] for a in axes if a["available"])
        assert abs(row["total_score"] - round(합, 2)) < 0.01, (
            f"{row['insurer_code']}: 총점 {row['total_score']}이 축 기여도 합 {합}과 다릅니다"
        )
        for a in axes:
            assert abs(a["contribution"] - a["score"] * a["weight"] * 100) < 1e-6
