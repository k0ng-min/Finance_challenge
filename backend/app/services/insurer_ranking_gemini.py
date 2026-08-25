"""
보험사 상대 순위 "설명" 전용 Gemini 호출(현재 랭킹 경로에서는 사용하지 않음).

중요: 이 파일은 순위를 절대 정하지 않는다. insurer_ranking.py가 근거로 이미
확정한 상대 순위를 그대로 받아서, 그 근거(신호)와 실제 약관 원문을 Gemini에게 주고
"왜 이 순위인지"를 사람이 읽기 좋은 문장으로 다듬어달라고만 요청한다.

검증: Gemini 응답에 이번 비교 대상 보험사 코드가 정확히 한 번씩만 있는지 확인하고, 하나라도
어긋나면 응답 전체를 버리고 None을 반환한다 — 이 경우 호출부는 규칙 기반 reasons를
그대로 쓴다(자연어만 덜 매끄러울 뿐 근거 자체는 항상 실제 신호에서 나온다).
"""
from __future__ import annotations

import logging

from pydantic import BaseModel
from sqlalchemy.orm import Session
from google import genai
from google.genai import types

from app import config
from app.models.kb import Insurer, Product, PolicyVersion, Coverage, Clause, CoverageStd

logger = logging.getLogger(__name__)

_RELEVANT_STD_CODES = ["DEATH_INJURY", "OVS_INJ_MED", "RESCUE"]
_RELEVANT_CLAUSE_TYPES = ["보장정의", "면책", "조건"]


def _collect_clause_texts(db: Session) -> dict[str, dict]:
    """보험사코드 -> {name, clauses: [조항 원문 목록]}"""
    insurers = db.query(Insurer).order_by(Insurer.code).all()
    out: dict[str, dict] = {}
    for insurer in insurers:
        rows = (
            db.query(Clause, CoverageStd)
            .join(Coverage, Clause.coverage_id == Coverage.coverage_id)
            .join(CoverageStd, Coverage.coverage_std_id == CoverageStd.coverage_std_id)
            .join(PolicyVersion, Coverage.policy_version_id == PolicyVersion.policy_version_id)
            .join(Product, PolicyVersion.product_id == Product.product_id)
            .filter(Product.insurer_id == insurer.insurer_id)
            .filter(CoverageStd.std_code.in_(_RELEVANT_STD_CODES))
            .filter(Clause.clause_type.in_(_RELEVANT_CLAUSE_TYPES))
            .all()
        )
        clauses = [f"[{std.std_name} · {c.clause_type} · {c.article_no}] {c.text}" for c, std in rows]
        out[insurer.code] = {"name": insurer.name, "clauses": clauses}
    return out


class _ExplainItem(BaseModel):
    insurer_code: str
    reasons: list[str]


class _ExplainSchema(BaseModel):
    items: list[_ExplainItem]


_EXPLAIN_PROMPT = """당신은 여행자보험 {insurer_count}개 보험사를 실제 약관 원문 근거로 비교 설명하는 분석가입니다.

아래는 "{tier_label}"({tier_description}) 기준으로 이미 코드로 확정된 상대 순위와 그 근거 신호입니다.
당신의 역할은 **순위를 바꾸는 것이 아니라**, 각 보험사별로 주어진 신호와 실제 약관
원문을 근거로 왜 이 순위가 나왔는지 자연스러운 문장 2~3개로 다시 써주는 것입니다.
{trip_context}

절대 규칙:
1. 상대 순위는 이미 정해져 있습니다. 절대 다른 순서를 암시하지 마세요.
2. 아래 제공된 신호와 실제 약관 원문 안에서만 근거를 찾으세요. 원문에 없는 내용을 추측하거나
   지어내지 마세요.
3. {insurer_count}개 보험사를 반드시 모두 포함하세요. 하나도 빠뜨리면 안 됩니다.
4. insurer_code는 아래 대괄호 안에 주어진 코드를 정확히 그대로 사용하세요.

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
        parts.append(f"보장 우선순위: {', '.join(trip_context['coverage_priority'])}")
    if not parts:
        return ""
    return "\n여행 정보:\n" + "\n".join(f"- {p}" for p in parts)


def explain_ranking(
    db: Session,
    tier_code: str,
    tier_label: str,
    tier_description: str,
    trip_context: dict | None,
    ranking: list[dict],
) -> list[dict] | None:
    """ranking(이미 확정된 상대 순위)을 그대로 두고 reasons만 자연어로 다듬는다.
    실패/검증탈락 시 None을 반환해 호출부가 규칙 기반 reasons를 그대로 쓰게 한다."""
    if not config.GEMINI_ENABLED:
        return None

    data = _collect_clause_texts(db)
    valid_codes = {r["insurer_code"] for r in ranking}
    if len(valid_codes) < 2:
        return None

    signal_blocks = "\n\n".join(
        f"[{r['insurer_code']}] {r['insurer_name']} ({r['rank']}위, {r['comparison_basis']})\n"
        f"신호: {' / '.join(r['reasons'])}\n"
        f"실제 약관 원문:\n" + "\n".join(data.get(r["insurer_code"], {}).get("clauses", []))
        for r in ranking
    )

    prompt = _EXPLAIN_PROMPT.format(
        # 보험사 수는 고정이 아니다 — 그 등급 상품이 없는 보험사는 이미 빠진 채로 들어온다
        # (예: 고급 등급에서는 2등급만 파는 신한EZ손보가 빠져 하나 줄어든다).
        insurer_count=len(ranking),
        tier_label=tier_label,
        tier_description=tier_description,
        trip_context=_trip_context_text(trip_context),
        insurer_blocks=signal_blocks,
    )

    try:
        client = genai.Client(api_key=config.GEMINI_API_KEY)
        response = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=_ExplainSchema,
                temperature=0.2,
            ),
        )
        parsed: _ExplainSchema = response.parsed
        if parsed is None:
            import json
            parsed = _ExplainSchema.model_validate(json.loads(response.text))

        by_code = {item.insurer_code: item.reasons for item in parsed.items}
        if set(by_code.keys()) != valid_codes:
            logger.warning("Gemini 순위 설명 검증 실패(코드 불일치), 규칙 기반 reasons 유지")
            return None

        out = []
        for r in ranking:
            reasons = by_code.get(r["insurer_code"])
            out.append({**r, "reasons": reasons if reasons else r["reasons"]})
        return out
    except Exception:
        logger.exception("Gemini 순위 설명 생성 실패, 규칙 기반 reasons 유지")
        return None
