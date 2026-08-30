"""등급(실속/표준/고급)까지 반영해 순위를 매기는 Gemini 호출의 계약을 고정한다.

원래 불만은 "실속·표준·고급을 아무리 바꿔도 순위가 늘 똑같다"였다. 규칙 기반 순위가
약관 근거 네 축만 보기 때문인데, 그 축은 등급을 바꿔도 변하지 않는다. 그래서 그 등급의
실제 보장금액을 함께 넘겨 모델이 점수를 매기게 한다.

여기서 지키는 것은 네 가지다.
  1. 모델에게 **등급에 따라 무엇이 달라지는지**를 실제 숫자로 알려준다. 선택한 등급의
     금액만 주면 모델은 그게 다른 등급과 뭐가 다른지 알 도리가 없다.
  2. 순위가 등급별로 **같을 수도 있다**. 억지로 다르게 만들라고 시키지 않는다 — 그러면
     근거 없는 차이를 지어낸다.
  3. 같은 입력에는 늘 같은 순서. 등급을 왔다갔다 하는 사이 순서가 흔들리면 사용자는
     그걸 버그로 읽는다.
  4. 같은 입력을 다시 물어보지 않는다. 등급 버튼은 사용자가 여러 번 누르는 자리다.
"""
import json

import pytest

from app import config
from app.services import insurer_ranking_score_gemini as scorer


class _FakeResponse:
    def __init__(self, payload):
        self.parsed = None
        self.text = json.dumps(payload)


class _FakeModels:
    def __init__(self, recorder, payload):
        self._recorder = recorder
        self._payload = payload

    def generate_content(self, *, model, contents, config):
        self._recorder.append({"model": model, "prompt": contents, "config": config})
        return _FakeResponse(self._payload)


class _FakeClient:
    def __init__(self, recorder, payload):
        self.models = _FakeModels(recorder, payload)


def _install_fake(monkeypatch, recorder, scores):
    payload = {"items": [{"insurer_code": c, "score": s, "reasons": [f"{c} 이유"]}
                         for c, s in scores.items()]}
    monkeypatch.setattr(config, "GEMINI_ENABLED", True)
    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(scorer, "_get_client", lambda api_key=None: _FakeClient(recorder, payload))
    scorer.clear_cache()


def _ranking(codes):
    return [
        {
            "rank": i + 1, "insurer_code": c, "insurer_name": f"{c}보험", "official_url": None,
            "tags": [], "reasons": [f"규칙 기반 {c}"], "comparison_basis": "안정형 기준 상대 비교",
            "dimensions": [
                {"code": "coverage_fit", "label": "보장 적합도", "level": 3, "status": "보통",
                 "summary": "요약", "evidence": [], "evidence_count": 0},
            ],
        }
        for i, c in enumerate(codes)
    ]


@pytest.fixture
def amounts(monkeypatch):
    """보장금액 조회를 고정값으로 바꾼다 — 이 테스트가 보는 건 KB 내용이 아니라 프롬프트다."""
    table = {
        0: {"AAA": ["[사망] 상해사망: 10,000만원"], "BBB": ["[사망] 상해사망: 5,000만원"]},
        1: {"AAA": ["[사망] 상해사망: 20,000만원"], "BBB": ["[사망] 상해사망: 30,000만원"]},
        2: {"AAA": ["[사망] 상해사망: 20,000만원"], "BBB": ["[사망] 상해사망: 50,000만원"]},
    }
    monkeypatch.setattr(scorer, "_coverage_amounts_by_code", lambda db, tier: table[tier])
    return table


def _call(db=None, *, plan_tier=1, ranking=None, trip_context=None):
    return scorer.score_ranking(
        db, tier_code="안정형", tier_label="안정형", tier_description="빠짐없는 보장",
        plan_tier=plan_tier, trip_context=trip_context, ranking=ranking or _ranking(["AAA", "BBB"]),
    )


def test_점수가_높은_보험사가_1위로_다시_정렬된다(monkeypatch, amounts):
    calls = []
    _install_fake(monkeypatch, calls, {"AAA": 40.0, "BBB": 90.0})

    out = _call()

    assert [r["insurer_code"] for r in out] == ["BBB", "AAA"]
    assert [r["rank"] for r in out] == [1, 2]
    assert out[0]["reasons"] == ["BBB 이유"]


def test_프롬프트에_등급별로_달라지는_금액이_들어간다(monkeypatch, amounts):
    """선택한 등급의 금액만 주면 모델은 그게 다른 등급과 뭐가 다른지 알 수 없다."""
    calls = []
    _install_fake(monkeypatch, calls, {"AAA": 60.0, "BBB": 50.0})

    _call(plan_tier=1)

    prompt = calls[0]["prompt"]
    # 실속 → 표준 → 고급 세 값이 한 줄에 나란히 보여야 등급 차이를 판단할 수 있다.
    assert "10,000만원" in prompt and "20,000만원" in prompt, "다른 등급 금액이 프롬프트에 없다"
    assert "5,000만원" in prompt and "30,000만원" in prompt and "50,000만원" in prompt


def test_순위가_같아도_된다고_알려준다(monkeypatch, amounts):
    """억지로 다르게 만들라고 시키면 모델이 근거 없는 차이를 지어낸다."""
    calls = []
    _install_fake(monkeypatch, calls, {"AAA": 60.0, "BBB": 50.0})

    _call()

    prompt = calls[0]["prompt"]
    assert "같아도 됩니다" in prompt or "같을 수 있습니다" in prompt
    assert "늘 같은 순서를 내면 안 됩니다" not in prompt, "차이를 강요하는 문구가 남아 있다"


def test_같은_입력이면_모델을_다시_부르지_않는다(monkeypatch, amounts):
    """등급 버튼은 사용자가 여러 번 누르는 자리다 — 누를 때마다 수 초씩 기다리면 못 쓴다."""
    calls = []
    _install_fake(monkeypatch, calls, {"AAA": 60.0, "BBB": 50.0})

    first = _call()
    second = _call()

    assert len(calls) == 1, "같은 입력인데 모델을 두 번 불렀다"
    assert [r["insurer_code"] for r in first] == [r["insurer_code"] for r in second]


def test_등급이_다르면_따로_묻는다(monkeypatch, amounts):
    calls = []
    _install_fake(monkeypatch, calls, {"AAA": 60.0, "BBB": 50.0})

    _call(plan_tier=0)
    _call(plan_tier=2)

    assert len(calls) == 2


def test_여행_정보가_다르면_따로_묻는다(monkeypatch, amounts):
    """순위는 여행 준비에서 고른 내용까지 반영한 결과다 — 여행이 달라지면 답도 달라야 한다."""
    calls = []
    _install_fake(monkeypatch, calls, {"AAA": 60.0, "BBB": 50.0})

    _call(trip_context={"destination": "일본", "activities": ["스키"]})
    _call(trip_context={"destination": "베트남", "activities": ["스쿠버다이빙"]})

    assert len(calls) == 2


def test_같은_입력에_늘_같은_순서가_나오게_온도를_0으로_둔다(monkeypatch, amounts):
    calls = []
    _install_fake(monkeypatch, calls, {"AAA": 60.0, "BBB": 50.0})

    _call()

    assert calls[0]["config"].temperature == 0


def test_보험사가_빠지면_통째로_버린다(monkeypatch, amounts):
    """일부만 점수가 오면 나머지는 순위를 매길 근거가 없다 — 규칙 기반 순위로 되돌린다."""
    calls = []
    _install_fake(monkeypatch, calls, {"AAA": 60.0})

    assert _call() is None


def test_모델이_실패하면_규칙_기반_순위를_그대로_쓴다(monkeypatch, amounts):
    monkeypatch.setattr(config, "GEMINI_ENABLED", True)
    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-key")

    def boom(api_key=None):
        raise RuntimeError("네트워크 끊김")

    monkeypatch.setattr(scorer, "_get_client", boom)
    scorer.clear_cache()

    assert _call() is None


def test_실패는_캐시하지_않는다(monkeypatch, amounts):
    """일시적 장애를 캐시하면 그 뒤로 영영 규칙 기반 순위만 나온다."""
    calls = []
    monkeypatch.setattr(config, "GEMINI_ENABLED", True)
    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-key")
    scorer.clear_cache()

    state = {"fail": True}

    def client(api_key=None):
        if state["fail"]:
            raise RuntimeError("일시적 장애")
        return _FakeClient(calls, {"items": [
            {"insurer_code": "AAA", "score": 10.0, "reasons": ["a"]},
            {"insurer_code": "BBB", "score": 90.0, "reasons": ["b"]},
        ]})

    monkeypatch.setattr(scorer, "_get_client", client)

    assert _call() is None
    state["fail"] = False
    out = _call()
    assert out is not None and [r["insurer_code"] for r in out] == ["BBB", "AAA"]
