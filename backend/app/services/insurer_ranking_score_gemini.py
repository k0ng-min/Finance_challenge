"""등급(실속/표준/고급)까지 반영해 보험사 순위를 실제로 매기는 Gemini 호출.

왜 필요했나
-----------
insurer_ranking.py는 약관 근거 네 축(coverage_fit / condition_clarity /
claim_simplicity / restrictions)만 보고 순위를 정한다. 이 축들은 "그 보험사의 약관이
어떻게 쓰여 있는가"에서 나오는 값이라 등급을 바꿔도 변하지 않는다 — 그래서 화면에서
실속·표준·고급을 아무리 바꿔도 순위가 늘 똑같이 나왔다. 하지만 실제로 등급 사이에서
갈리는 건 **보장금액**이다(실속에서는 해외의료비 2,000만원인 곳이 고급에서는
1억원이 되기도 한다). 그 차이가 순위에 반영되지 않으면 등급 선택기가 가격 표시만
바꾸는 장식이 된다.

무엇을 주고 무엇을 받나
-----------------------
Gemini에게는 지어낼 여지를 주지 않는다. 넘기는 것은 전부 DB에 실제로 있는 값이다.
  · 사용자가 고른 비교 기준(tier)과 그 기준의 정의
  · 여행 맥락(목적지·기간·위험도·활동·걱정되는 사고유형)
  · 보험사별 약관 근거 네 축의 단계(1~5)와 그 근거 문장 — insurer_ranking.py가 계산한 값
  · **그 등급의 실제 보장금액 표**(InsurerComparisonMetric의 해당 plan_name 행)
받는 것은 보험사별 점수(0~100)와 이유 2~3문장뿐이다. 순서는 우리가 점수로 정렬해서
만든다 — 모델이 "1위"라고 써 준 걸 그대로 믿지 않는다.

검증
----
응답에 요청한 보험사 코드가 정확히 한 번씩만 있어야 하고, 점수가 전부 숫자여야 한다.
하나라도 어긋나면 전체를 버리고 None을 돌려준다 — 그러면 호출부가 기존 규칙 기반
순위를 그대로 쓴다(기능이 죽지 않고, 근거 없는 순위도 나오지 않는다).
"""
from __future__ import annotations

import json
import logging

from pydantic import BaseModel
from sqlalchemy.orm import Session
from google import genai
from google.genai import types

from app import config
from app.models.kb import Insurer, InsurerComparisonMetric
from app.services.insurer_tiers import TIER_LABELS, plan_name_for_tier

logger = logging.getLogger(__name__)


class _ScoreItem(BaseModel):
    insurer_code: str
    score: float
    reasons: list[str]


class _ScoreSchema(BaseModel):
    items: list[_ScoreItem]


_PROMPT = """당신은 여행자보험 6개 보험사를 실제 자료만 근거로 비교해 순위를 매기는 분석가입니다.

사용자가 고른 비교 기준: **{tier_label}** — {tier_description}
사용자가 고른 가입 등급: **{plan_tier_label}**
{trip_context}

아래에는 보험사마다 세 종류의 자료가 있습니다.
1. 약관 근거 네 축의 상대 단계(1~5, 높을수록 사용자에게 유리) — 실제 약관 조항을 집계한 값입니다.
2. **{plan_tier_label} 등급의 실제 보장금액** — 각 보험사 다이렉트 사이트에서 조회한 값입니다.
3. **등급에 따라 달라지는 항목** — 같은 항목을 실속 → 표준 → 고급 순으로 나열한 값입니다.
   이 사용자가 고른 등급은 **{plan_tier_label}**이므로, 그 자리의 값이 이번 판단의 기준입니다.

당신이 할 일:
- 보험사마다 0~100 사이의 점수를 매기세요. 점수가 높을수록 이 사용자에게 더 나은 선택입니다.
- **{tier_label}** 기준이 무엇을 중시하는지에 맞춰 가중치를 두세요.
- 3번 자료를 보면 어떤 보험사는 등급을 올려도 금액이 그대로이고, 어떤 보험사는 크게 뜁니다.
  {plan_tier_label} 등급에서 실제로 얼마를 받는지로 판단하세요.
- 그 결과 **등급이 달라도 순위가 같아도 됩니다.** 등급 사이에 실질적인 차이가 없으면 같은 순서를
  그대로 두세요 — 차이를 만들어내려고 없는 근거를 끌어오지 마세요.
- 각 보험사마다 왜 그 점수인지 자연스러운 문장 2~3개로 쓰세요. 금액이 근거라면 그 금액을
  문장 안에 그대로 적으세요.

절대 규칙:
1. 아래 제공된 값 안에서만 판단하세요. 없는 담보나 금액을 추측하거나 지어내지 마세요.
2. 보험료(가격)는 자료에 없습니다. 가격을 근거로 들지 마세요.
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


def score_ranking(
    db: Session,
    *,
    tier_code: str,
    tier_label: str,
    tier_description: str,
    plan_tier: int,
    trip_context: dict | None,
    ranking: list[dict],
) -> list[dict] | None:
    """규칙 기반 ranking(근거 축이 이미 계산된 상태)을 받아, 등급별 보장금액까지 넣고
    Gemini에게 점수를 매기게 한 뒤 그 점수로 다시 정렬한 ranking을 돌려준다.

    실패하거나 검증에 걸리면 None — 호출부는 규칙 기반 순위를 그대로 쓴다."""
    if not config.GEMINI_ENABLED:
        return None
    if plan_tier not in (0, 1, 2):
        return None
    valid_codes = {item["insurer_code"] for item in ranking}
    if len(valid_codes) < 2:
        return None

    amounts = _coverage_amounts_by_code(db, plan_tier)
    # 그 등급의 보장금액을 한 곳도 못 구했으면 등급을 반영할 수 없다 — 굳이 모델을
    # 부르지 않고 규칙 기반 순위를 그대로 쓴다(같은 결과를 비싸게 만들 이유가 없다).
    if not any(amounts.get(code) for code in valid_codes):
        return None

    blocks = []
    for item in ranking:
        code = item["insurer_code"]
        dims = "\n".join(
            f"  - {d['label']}: 5단계 중 {d['level']}단계 ({d['status']}) — {d['summary']}"
            for d in item["dimensions"]
        )
        coverage = "\n".join(f"  - {line}" for line in amounts.get(code, [])) or "  - (이 등급의 보장금액 자료 없음)"
        blocks.append(
            f"[{code}] {item['insurer_name']}\n"
            f"약관 근거 축:\n{dims}\n"
            f"{TIER_LABELS[plan_tier]} 등급 보장금액:\n{coverage}"
        )

    prompt = _PROMPT.format(
        tier_label=tier_label,
        tier_description=tier_description,
        plan_tier_label=TIER_LABELS[plan_tier],
        trip_context=_trip_context_text(trip_context),
        insurer_blocks="\n\n".join(blocks),
    )

    try:
        client = genai.Client(api_key=config.GEMINI_API_KEY)
        response = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=_ScoreSchema,
                temperature=0.2,
            ),
        )
        parsed: _ScoreSchema | None = response.parsed
        if parsed is None:
            parsed = _ScoreSchema.model_validate(json.loads(response.text))

        by_code = {item.insurer_code: item for item in parsed.items}
        if set(by_code.keys()) != valid_codes:
            logger.warning("Gemini 순위 점수 검증 실패(보험사 코드 불일치) — 규칙 기반 순위 유지")
            return None

        # 점수 내림차순, 동점이면 보험사 코드순 — 같은 입력이면 항상 같은 순서가 나온다.
        ordered = sorted(ranking, key=lambda r: (-by_code[r["insurer_code"]].score, r["insurer_code"]))
        out = []
        for index, item in enumerate(ordered, start=1):
            scored = by_code[item["insurer_code"]]
            out.append({
                **item,
                "rank": index,
                "reasons": scored.reasons or item["reasons"],
                "comparison_basis": f"{tier_code} 기준 · {TIER_LABELS[plan_tier]} 등급 보장금액 반영",
            })
        return out
    except Exception:
        logger.exception("Gemini 순위 점수 생성 실패 — 규칙 기반 순위 유지")
        return None
