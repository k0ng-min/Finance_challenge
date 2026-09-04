"""이미 정해진 보험사 순위를 사람 말로 옮기는 Gemini 호출.

왜 설명 전용인가
----------------
예전에는 이 모듈이 보험사마다 0~100 점수를 매기고, 그 점수가 결정적 점수와 8:2로
섞여 최종 순위를 바꿨다. 금융상품 추천에서 그건 감당하기 어려운 성질을 만든다.

  · 같은 자료·같은 입력인데도 모델이 바뀌면 순위가 바뀐다.
  · "왜 이 보험사가 1위인가"를 끝까지 수식으로 되짚을 수 없다 — 마지막 20%가 모델
    안에 있다.
  · 점수를 감사(audit)할 수 없다.

그래서 순위와 총점은 ranking_score.score_insurers()의 결정적 계산만으로 끝낸다.
이 모듈은 그 결과를 **입력으로 받아** 이유 문장만 만든다. 순서를 바꿀 수단 자체가
없다 — 점수를 돌려주지 않고, 호출부도 reasons 말고는 아무것도 쓰지 않는다.

지어내지 못하게 하는 방법
-------------------------
모델에게 넘기는 것은 전부 DB나 결정적 계산에서 나온 값이다.
  · 확정된 순위와 총점
  · 축별 점수·비중·기여도와 그 축이 스스로 적어 둔 근거 문장(AxisScore.detail)
  · 그 등급의 실제 보장금액표(InsurerComparisonMetric)
받는 것은 보험사별 이유 문장뿐이다. 요청한 보험사 코드가 정확히 한 번씩 오지 않거나
문장이 비면 전체를 버리고 None을 돌려준다 — 그러면 호출부가 축 근거로 만든 결정적
설명을 그대로 쓴다.
"""
from __future__ import annotations

import json
import logging
from collections import OrderedDict

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import config
from app.models.kb import Insurer, InsurerComparisonMetric
from app.services.insurer_tiers import TIER_LABELS, plan_name_for_tier

logger = logging.getLogger(__name__)


def _get_client():
    """google.genai는 쓰는 자리에서 불러온다.

    이 패키지는 import만으로 1.4초가 걸리는데(로컬 기준, 무료 인스턴스는 더 오래),
    앱 기동에는 필요 없고 실제 Gemini 호출이 있을 때만 필요하다.
    """
    from google import genai

    return genai.Client(api_key=config.GEMINI_API_KEY)


# 같은 입력에는 모델을 다시 부르지 않는다. 등급 버튼(실속/표준/고급)은 사용자가 화면에서
# 여러 번 왔다갔다 누르는 자리라, 누를 때마다 수 초씩 기다리면 등급 선택기 자체가 못 쓸
# 물건이 된다. 실패는 담지 않는다 — 일시적 장애를 캐시하면 그 뒤로 영영 설명이 안 붙는다.
_CACHE_LIMIT = 64
_cache: "OrderedDict[str, dict[str, list[str]]]" = OrderedDict()


def clear_cache() -> None:
    """캐시를 비운다. 약관 KB나 보장금액을 다시 적재했을 때, 그리고 테스트에서 쓴다."""
    _cache.clear()


def _cache_key(*, tier_code: str, plan_tier: int, trip_context: dict | None,
               ranked: list[dict]) -> str:
    """모델에게 실제로 넘어가는 것만 키에 담는다.

    순위·총점·축 기여도가 같으면 프롬프트도 같다 — 표시용 문구(태그 등)가 달라졌다고
    다시 물을 이유는 없다."""
    payload = {
        "tier_code": tier_code,
        "plan_tier": plan_tier,
        "trip": trip_context or {},
        "ranked": [
            {
                "code": item["insurer_code"],
                "rank": item.get("rank"),
                "total": item.get("total_score"),
                "axes": [
                    (a.get("code"), round(float(a.get("contribution") or 0.0), 3), a.get("available"))
                    for a in item.get("axes") or []
                ],
            }
            for item in ranked
        ],
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)


class _ExplanationItem(BaseModel):
    insurer_code: str
    reasons: list[str]


class _ExplanationSchema(BaseModel):
    items: list[_ExplanationItem]


_PROMPT = """당신은 이미 계산이 끝난 여행자보험 비교 결과를 사용자에게 말로 풀어 주는 사람입니다.

**순위는 이미 정해져 있습니다. 당신은 순위를 바꾸지 않습니다.**
점수를 다시 매기지 마세요. 순서를 바꾸자고 제안하지 마세요. 아래에 적힌 순위와 점수가
최종입니다. 당신이 할 일은 그 숫자가 왜 그렇게 나왔는지를 사람이 읽을 문장으로 옮기는 것뿐입니다.

사용자가 고른 비교 기준: **{tier_label}** — {tier_description}
사용자가 고른 가입 등급: **{plan_tier_label}**
{trip_context}

총점은 축별 기여도의 합입니다(기여도 = 그 축의 점수 x 비중 x 100). 아래 블록에 보험사마다
확정된 순위·총점과, 각 축이 총점에 얼마를 보탰는지, 그리고 그 축이 무엇을 근거로 그 점수를
냈는지가 적혀 있습니다. "자료 없음"으로 표시된 축은 총점 계산에서 아예 빠졌습니다 — 그 축이
나쁘다는 뜻이 아니라 판단할 자료가 없다는 뜻이니, 나쁘게 쓰지 마세요.

각 보험사마다 이유 문장을 2~3개 쓰세요.
- 기여도가 큰 축부터 말하세요. 그게 그 보험사가 그 자리에 있는 실제 이유입니다.
- 금액이나 보험료가 근거라면 아래 적힌 숫자를 그대로 문장에 넣으세요.
- 존댓말로, 한 문장은 한 가지만 말하세요.

절대 규칙:
1. 아래 제공된 값 안에서만 쓰세요. 없는 담보·금액·보험료·약관 내용을 추측하거나 지어내지 마세요.
2. 점수나 순위를 새로 매기지 마세요. 아래 숫자를 그대로 쓰세요.
3. 아래 나열된 보험사를 하나도 빠짐없이, 각각 정확히 한 번씩 포함하세요.
4. insurer_code는 대괄호 안에 주어진 코드를 그대로 사용하세요.

{insurer_blocks}
"""


def _trip_context_text(trip_context: dict | None) -> str:
    if not trip_context:
        return ""
    parts = []
    if trip_context.get("destination"):
        parts.append(f"목적지: {trip_context['destination']}")
    if trip_context.get("trip_days"):
        parts.append(f"여행 기간: {trip_context['trip_days']}일")
    if trip_context.get("risk_level"):
        parts.append(f"위험도: {trip_context['risk_level']}")
    if trip_context.get("activities"):
        parts.append(f"주요 활동: {', '.join(trip_context['activities'])}")
    if trip_context.get("coverage_priority"):
        parts.append(f"걱정되는 사고유형: {', '.join(trip_context['coverage_priority'])}")
    if not parts:
        return ""
    return "\n여행 정보:\n" + "\n".join(f"- {p}" for p in parts)


def _coverage_amounts_by_code(db: Session, plan_tier: int) -> dict[str, list[str]]:
    """보험사코드 -> ["[카테고리] 항목: 값", ...] (그 등급의 실제 보장금액표)."""
    insurers = {i.insurer_id: i for i in db.query(Insurer).all()}
    wanted = {
        insurer_id: plan_name_for_tier(insurer.code, plan_tier)
        for insurer_id, insurer in insurers.items()
    }
    rows = (
        db.query(InsurerComparisonMetric)
        .order_by(
            InsurerComparisonMetric.category_order.asc(),
            InsurerComparisonMetric.sort_order.asc(),
        )
        .all()
    )
    out: dict[str, list[str]] = {insurer.code: [] for insurer in insurers.values()}
    for row in rows:
        if row.plan_name != wanted.get(row.insurer_id):
            continue
        code = insurers[row.insurer_id].code
        value = row.value_text
        if value in (None, "", "-"):
            continue
        unit = row.unit or ""
        display = f"{int(value):,}{unit}" if value.isdigit() else value
        out[code].append(f"[{row.category}] {row.metric_label}: {display}")
    return out


def _axis_lines(axes: list[dict]) -> list[str]:
    """축별 기여도를 큰 순서로. 총점을 만든 것이 무엇인지가 한눈에 보여야 한다."""
    lines = []
    for axis in sorted(axes, key=lambda a: -(float(a.get("contribution") or 0.0))):
        label = axis.get("label") or axis.get("code")
        detail = axis.get("detail") or ""
        if not axis.get("available", True):
            lines.append(f"{label}: 자료 없음(총점 계산에서 제외) — {detail}")
            continue
        score = float(axis.get("score") or 0.0)
        weight = float(axis.get("weight") or 0.0)
        contribution = float(axis.get("contribution") or 0.0)
        lines.append(
            f"{label}: 점수 {score:.2f} x 비중 {weight * 100:.0f}% = +{contribution:.1f}점 — {detail}"
        )
    return lines


def explain_ranking(
    db: Session,
    *,
    tier_code: str,
    tier_label: str,
    tier_description: str,
    plan_tier: int,
    trip_context: dict | None,
    ranked: list[dict],
) -> dict[str, list[str]] | None:
    """확정된 순위를 받아 보험사별 이유 문장만 만들어 돌려준다.

    돌려주는 것은 {보험사코드: [문장, ...]}뿐이다. 점수도 순서도 돌려주지 않는다 —
    이 함수가 순위를 흔들 수단 자체를 두지 않기 위해서다.

    실패하거나 검증에 걸리면 None. 호출부는 축 근거로 만든 결정적 설명을 그대로 쓴다.
    """
    if not config.GEMINI_ENABLED:
        return None
    if plan_tier not in (0, 1, 2):
        return None
    valid_codes = {item["insurer_code"] for item in ranked}
    if not valid_codes:
        return None

    cache_key = _cache_key(
        tier_code=tier_code, plan_tier=plan_tier, trip_context=trip_context, ranked=ranked
    )
    cached = _cache.get(cache_key)
    if cached is not None:
        _cache.move_to_end(cache_key)
        return {code: list(reasons) for code, reasons in cached.items()}

    amounts = _coverage_amounts_by_code(db, plan_tier)

    blocks = []
    for item in ranked:
        code = item["insurer_code"]
        axis_text = "\n".join(f"  - {line}" for line in _axis_lines(item.get("axes") or []))
        coverage = "\n".join(f"  - {line}" for line in amounts.get(code, []))
        blocks.append(
            f"[{code}] {item.get('insurer_name') or code}"
            f" — 확정 {item.get('rank')}위 · 총점 {item.get('total_score')}점\n"
            f"축별 기여(총점을 만든 것):\n{axis_text or '  - (축 자료 없음)'}\n"
            f"{TIER_LABELS[plan_tier]} 등급 보장금액:\n"
            f"{coverage or '  - (이 등급의 보장금액 자료 없음)'}"
        )

    prompt = _PROMPT.format(
        tier_label=tier_label,
        tier_description=tier_description,
        plan_tier_label=TIER_LABELS[plan_tier],
        trip_context=_trip_context_text(trip_context),
        insurer_blocks="\n\n".join(blocks),
    )

    try:
        from google.genai import types

        client = _get_client()
        response = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=_ExplanationSchema,
                # 같은 입력에 같은 설명이 나오게 한다. 순위는 이미 결정적이지만, 등급을
                # 왔다갔다 하는 사이 설명 문장만 매번 바뀌면 그것도 버그로 읽힌다.
                temperature=0,
            ),
        )
        parsed: _ExplanationSchema | None = response.parsed
        if parsed is None:
            parsed = _ExplanationSchema.model_validate(json.loads(response.text))

        by_code = {item.insurer_code: item for item in parsed.items}
        if set(by_code.keys()) != valid_codes:
            logger.warning("Gemini 순위 설명 검증 실패(보험사 코드 불일치) — 결정적 설명 유지")
            return None

        out: dict[str, list[str]] = {}
        for code, item in by_code.items():
            reasons = [r.strip() for r in (item.reasons or []) if isinstance(r, str) and r.strip()]
            if not reasons:
                logger.warning("Gemini 순위 설명이 비어 있음(%s) — 결정적 설명 유지", code)
                return None
            out[code] = reasons

        _cache[cache_key] = {code: list(reasons) for code, reasons in out.items()}
        _cache.move_to_end(cache_key)
        while len(_cache) > _CACHE_LIMIT:
            _cache.popitem(last=False)
        return out
    except Exception:
        logger.exception("Gemini 순위 설명 생성 실패 — 결정적 설명 유지")
        return None
