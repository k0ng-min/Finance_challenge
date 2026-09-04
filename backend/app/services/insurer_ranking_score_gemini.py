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
  · 보험사별 비교 가능한 약관 근거 축의 단계(1~5)와 근거 문장 — UNKNOWN 축은 제외
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
from collections import OrderedDict

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import config
from app.models.kb import Insurer, InsurerComparisonMetric
from app.services.insurer_tiers import TIER_LABELS, plan_name_for_tier


def _get_client():
    """google.genai는 쓰는 자리에서 불러온다.

    이 패키지는 import만으로 1.4초가 걸리는데(로컬 기준, 무료 인스턴스는 더 오래),
    앱 기동에는 필요 없고 실제 Gemini 호출이 있을 때만 필요하다. 최상단에 두면 무료
    인스턴스가 잠에서 깰 때마다 첫 방문자가 그 시간을 그대로 기다린다.
    doc_verify_gemini·incident_classify_gemini도 같은 이유로 같은 모양을 쓴다.
    """
    from google import genai

    return genai.Client(api_key=config.GEMINI_API_KEY)

logger = logging.getLogger(__name__)

# 방금 계산에 쓰인 보험사별 원점수. score_ranking이 정렬된 순위를 돌려주는 것과 별개로,
# 가중치 점수 모델과 섞으려면 점수 자체가 필요하다(순위만으로는 얼마나 앞서는지를 못 쓴다).
_last_scores: dict[str, dict] = {}


def last_scores() -> dict[str, dict]:
    """직전 score_ranking 호출이 받은 보험사별 점수·이유. 실패했으면 빈 dict."""
    return dict(_last_scores)

# 같은 입력에는 모델을 다시 부르지 않는다. 등급 버튼(실속/표준/고급)은 사용자가 화면에서
# 여러 번 왔다갔다 누르는 자리라, 누를 때마다 수 초씩 기다리면 등급 선택기 자체가 못 쓸
# 물건이 된다. 실패는 담지 않는다 — 일시적 장애를 캐시하면 그 뒤로 영영 규칙 기반
# 순위만 나온다.
_CACHE_LIMIT = 64
_cache: "OrderedDict[str, list[dict]]" = OrderedDict()


def clear_cache() -> None:
    """캐시를 비운다. 약관 KB나 보장금액을 다시 적재했을 때, 그리고 테스트에서 쓴다."""
    _cache.clear()
    _last_scores.clear()


def _cache_key(
    *, tier_code: str, plan_tier: int, trip_context: dict | None, ranking: list[dict]
) -> str:
    """모델에게 실제로 넘어가는 입력만 키에 담는다.

    보험사 코드와 근거 축 단계가 같으면 프롬프트도 같다 — 표시용 문구(이름·태그)가
    달라졌다고 다시 물을 이유는 없다."""
    payload = {
        "tier_code": tier_code,
        "plan_tier": plan_tier,
        "trip": trip_context or {},
        "ranking": [
            {
                "code": item["insurer_code"],
                "dims": [
                    (d.get("code"), d.get("level"), d.get("comparison_state"), d.get("available"))
                    for d in item["dimensions"]
                ],
            }
            for item in ranking
        ],
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)


class _ScoreItem(BaseModel):
    insurer_code: str
    score: float
    reasons: list[str]


class _ScoreSchema(BaseModel):
    items: list[_ScoreItem]


_PROMPT = """당신은 여행자보험 {insurer_count}개 보험사를 실제 자료만 근거로 비교해 순위를 매기는 분석가입니다.

사용자가 고른 비교 기준: **{tier_label}** — {tier_description}
사용자가 고른 가입 등급: **{plan_tier_label}**
{trip_context}

아래에는 보험사마다 세 종류의 자료가 있습니다.
1. 비교 가능한 약관 근거 축의 상대 단계(1~5, 높을수록 사용자에게 유리)입니다.
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
5. UNKNOWN/NOT_APPLICABLE인 약관 축은 아래 목록에서 제외했습니다. 빠진 축을 0점이나
   좋은 점수로 추정하지 말고, 보험사 간 비교 근거로 사용하지 마세요.

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


def _tier_diff_lines(by_tier: dict[int, dict[str, str]]) -> list[str]:
    """같은 항목을 실속 → 표준 → 고급 순으로 나란히 놓되, 세 값이 모두 같은 항목은 뺀다.

    선택한 등급의 금액만 넘기면 모델은 그게 다른 등급과 뭐가 다른지 알 도리가 없다.
    등급을 올려도 그대로인 보험사와 크게 뛰는 보험사를 가르는 건 이 표뿐이다. 값이
    똑같은 줄까지 넣으면 정작 갈리는 항목이 그 안에 묻힌다."""
    labels: list[str] = []
    for tier in (0, 1, 2):
        for label in by_tier.get(tier, {}):
            if label not in labels:
                labels.append(label)

    lines = []
    for label in labels:
        values = [by_tier.get(tier, {}).get(label, "-") for tier in (0, 1, 2)]
        if len(set(values)) == 1:
            continue
        lines.append(
            f"{label}: {TIER_LABELS[0]} {values[0]} → {TIER_LABELS[1]} {values[1]}"
            f" → {TIER_LABELS[2]} {values[2]}"
        )
    return lines


def _as_label_map(lines: list[str]) -> dict[str, str]:
    """"[카테고리] 항목: 값" 한 줄을 {"[카테고리] 항목": "값"}으로 나눈다."""
    out: dict[str, str] = {}
    for line in lines:
        label, sep, value = line.rpartition(": ")
        if sep:
            out[label] = value
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

    by_tier = {tier: _coverage_amounts_by_code(db, tier) for tier in (0, 1, 2)}
    amounts = by_tier[plan_tier]
    # 그 등급의 보장금액을 한 곳도 못 구했으면 등급을 반영할 수 없다 — 굳이 모델을
    # 부르지 않고 규칙 기반 순위를 그대로 쓴다(같은 결과를 비싸게 만들 이유가 없다).
    if not any(amounts.get(code) for code in valid_codes):
        return None

    cache_key = _cache_key(
        tier_code=tier_code, plan_tier=plan_tier, trip_context=trip_context, ranking=ranking
    )
    cached = _cache.get(cache_key)
    if cached is not None:
        _cache.move_to_end(cache_key)
        return [dict(row) for row in cached]

    blocks = []
    for item in ranking:
        code = item["insurer_code"]
        available_dimensions = [
            dimension
            for dimension in item["dimensions"]
            if dimension.get("available", (dimension.get("level") or 0) > 0)
            and dimension.get("comparison_state", "AVAILABLE") == "AVAILABLE"
        ]
        dims = "\n".join(
            f"  - {d['label']}: 5단계 중 {d['level']}단계 ({d['status']}) — {d['summary']}"
            for d in available_dimensions
        ) or "  - (비교 가능한 약관 근거 축 없음)"
        coverage = "\n".join(f"  - {line}" for line in amounts.get(code, [])) or "  - (이 등급의 보장금액 자료 없음)"
        diff = _tier_diff_lines(
            {tier: _as_label_map(by_tier[tier].get(code, [])) for tier in (0, 1, 2)}
        )
        diff_text = "\n".join(f"  - {line}" for line in diff) or "  - (등급을 올려도 달라지는 항목이 없음)"
        blocks.append(
            f"[{code}] {item['insurer_name']}\n"
            f"약관 근거 축:\n{dims}\n"
            f"{TIER_LABELS[plan_tier]} 등급 보장금액:\n{coverage}\n"
            f"등급에 따라 달라지는 항목:\n{diff_text}"
        )

    prompt = _PROMPT.format(
        # 그 등급 상품이 없는 보험사는 이미 빠진 채로 들어오므로 개수를 고정하지 않는다.
        insurer_count=len(blocks),
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
                response_schema=_ScoreSchema,
                # 같은 입력에는 늘 같은 순서가 나와야 한다. 등급을 왜왰다갔다 하는 사이
                # 순서가 흔들리면 사용자는 그걸 버그로 읽는다.
                temperature=0,
            ),
        )
        parsed: _ScoreSchema | None = response.parsed
        if parsed is None:
            parsed = _ScoreSchema.model_validate(json.loads(response.text))

        by_code = {item.insurer_code: item for item in parsed.items}
        if set(by_code.keys()) != valid_codes:
            logger.warning("Gemini 순위 점수 검증 실패(보험사 코드 불일치) — 규칙 기반 순위 유지")
            return None
        _last_scores.clear()
        _last_scores.update({
            code: {"score": item.score, "reasons": list(item.reasons or [])}
            for code, item in by_code.items()
        })

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
        _cache[cache_key] = [dict(row) for row in out]
        _cache.move_to_end(cache_key)
        while len(_cache) > _CACHE_LIMIT:
            _cache.popitem(last=False)
        return out
    except Exception:
        logger.exception("Gemini 순위 점수 생성 실패 — 규칙 기반 순위 유지")
        return None
