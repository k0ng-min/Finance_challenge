"""
약관 조항 원문을 여러 색상 구간으로 나눠 표시하기 위한 Gemini 기반 분석.

핵심 안전장치: Gemini는 "발췌(extractive)"만 하도록 강제한다 — 조각을 새로 쓰거나
요약하지 못하게 하고, 결과로 받은 각 조각이 원문에 실제로 등장하는 부분 문자열인지
코드에서 직접 검증한다. 한 조각이라도 원문에서 못 찾으면 전체 결과를 버리고
None을 반환해서, 호출부가 기존처럼 조항 전체를 단색으로 표시하도록 안전하게 폴백한다.
→ "근거 없는 결과 금지" 원칙을 프롬프트뿐 아니라 코드 레벨에서도 강제.

분석 결과는 Clause.highlight_spans에 JSON으로 캐시해서, 같은 조항을 다시 볼 때
Gemini를 또 호출하지 않는다(비용·속도).
"""
from __future__ import annotations

import json
import logging

from pydantic import BaseModel
from sqlalchemy.orm import Session
from google import genai
from google.genai import types

from app import config
from app.models.kb import Clause

logger = logging.getLogger(__name__)

_VALID_COLORS = {"파랑", "초록", "노랑", "빨강", "회색"}

_SPAN_PROMPT = """다음은 여행자보험 약관의 한 조항 원문입니다. 이 원문을 아래 5가지 색상 범주로
나눠서 하이라이트하려고 합니다.

색상 범주:
- 파랑: 무엇을·어떤 조건에서 보장하는지 정의하는 핵심 문장(보장 정의) — 숫자·기한이 아닌 "정의" 부분
- 초록: 이미 충족된 것으로 보이는 조건, 일반적인 지급 사유 설명
- 노랑: 기간·일수(예: "14일 이상", "180일까지"), 금액·한도(예: "US$1,000 한도", "가입금액 한도"),
  상해정도·장해율(예: "장해지급률", "전액") 등 "구체적인 숫자나 기한이 담긴" 문구만. 이 범주는
  아껴서 쓰세요 — 단순히 조건이 있다고 다 노랑으로 칠하지 말고, 실제 숫자·기간·정도가 명시된
  부분에만 사용하세요.
- 빨강: 보장하지 않는 경우, 제한, 예외, 면책 사유
- 회색: 위 4개에 해당하지 않는 부수적 문구(제목, 접속어, 목차 표시, 숫자 없는 일반 조건 등)

절대 규칙 (반드시 지키세요):
1. 원문의 글자를 하나도 바꾸거나 요약하지 마세요. 반드시 원문에 있는 문자열을 "그대로" 잘라서 사용하세요.
2. 원문을 처음부터 끝까지 순서대로, 빠짐없이 조각으로 나누세요.
3. 문장 또는 의미 단위로 나누되 조각당 최소 4자 이상으로 하세요. 너무 잘게 쪼개지 마세요.
4. 노랑은 숫자·기간·정도가 실제로 포함된 문구에만 쓰세요. 숫자가 없는 조건부 문구는 노랑이 아니라
   회색이나 파랑으로 분류하세요.

조항 원문:
\"\"\"{clause_text}\"\"\"
"""


class _Span(BaseModel):
    text: str
    color: str


class _SpanResult(BaseModel):
    spans: list[_Span]


def _locate_spans(clause_text: str, spans: list[_Span]) -> list[dict] | None:
    """Gemini가 반환한 조각들이 실제로 원문의 부분 문자열인지 순서대로 검증하며 위치를 찾는다.
    하나라도 못 찾으면 전체를 무효 처리(None)한다. 놓친 구간은 회색으로 채워 원문 손실을 막는다."""
    cursor = 0
    result: list[dict] = []
    for span in spans:
        text = span.text.strip()
        if not text:
            continue
        color = span.color if span.color in _VALID_COLORS else "회색"
        idx = clause_text.find(text, cursor)
        if idx == -1:
            return None  # 원문에 없는 조각 → 근거 없음, 전체 무효
        if idx > cursor:
            result.append({"text": clause_text[cursor:idx], "color": "회색"})
        result.append({"text": text, "color": color})
        cursor = idx + len(text)
    if cursor < len(clause_text):
        result.append({"text": clause_text[cursor:], "color": "회색"})
    return result or None


_RELEVANCE_PROMPT = """다음은 여행자보험 약관 조항 원문과, 사용자가 실제로 겪은 사고 상황입니다.
이 조항 안에서, 이 사고가 "보장되는지 여부·조건"을 판단하는 데 실질적으로 쓰이는 부분만
원문 그대로 정확히 잘라서 표시하세요.

사고 상황: {situation}

무엇을 관련 있다고 볼지 판단 기준:
- 이 사고 유형(상해/질병 여부, 다친 부위, 증상)이 이 조항의 보장 정의·지급 사유·면책 사유·
  지급 조건(기간·한도 등)에 해당하는지 여부를 결정하는 문구 → 관련 있음
- 모든 사고에 공통으로 적용되는 일반적인 서류 제출 안내, 청구 절차, 통지 의무 같은 절차적
  문구는 이 특정 사고의 내용과 실질적으로 관련된 게 아니므로, 그 사고에서만 특별히 의미가
  달라지는 부분이 아니라면 관련 있다고 표시하지 마세요.
- 단순히 "상해", "치료" 같은 일반 단어가 겹친다고 관련 있다고 보지 마세요. 이 사고의 구체적인
  내용(부위·원인·정도)이 이 조항의 적용 여부를 실제로 좌우하는지를 기준으로 판단하세요.

절대 규칙:
1. 원문의 글자를 하나도 바꾸거나 요약하지 마세요. 반드시 원문에 있는 문자열을 "그대로" 잘라서 사용하세요.
2. 관련된 부분이 여러 곳에 흩어져 있으면 각각 별도 조각으로 반환하세요.
3. 이 조항이 이 사고 상황의 보장 여부 판단에 실질적으로 쓰이지 않으면 spans를 빈 목록으로 반환하세요.

약관 조항 원문:
\"\"\"{clause_text}\"\"\"
"""


class _RelevantSpan(BaseModel):
    text: str


class _RelevanceResult(BaseModel):
    spans: list[_RelevantSpan]


def _locate_relevant(clause_text: str, spans: list[_RelevantSpan]) -> list[str] | None:
    """각 조각이 원문의 실제 부분 문자열인지 확인한다(순서·커버리지 무관).
    하나라도 원문에 없으면 전체 무효 처리해서 근거 없는 하이라이트를 막는다."""
    found = []
    for span in spans:
        text = span.text.strip()
        if not text or len(text) < 3:
            continue
        if text not in clause_text:
            return None
        found.append(text)
    return found


def _build_relevance_segments(clause_text: str, relevant_texts: list[str]) -> tuple[list[dict], int]:
    """clause_text 전체를 관련/비관련 구간으로 순서대로 나눠서, 프론트가 이어 붙여 렌더링할 수 있게 한다."""
    positions = []
    for t in relevant_texts:
        idx = clause_text.find(t)
        if idx != -1:
            positions.append((idx, idx + len(t)))
    positions.sort()

    merged: list[tuple[int, int]] = []
    for start, end in positions:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))

    segments: list[dict] = []
    cursor = 0
    relevant_chars = 0
    for start, end in merged:
        if start > cursor:
            segments.append({"text": clause_text[cursor:start], "highlighted": False})
        segments.append({"text": clause_text[start:end], "highlighted": True})
        relevant_chars += end - start
        cursor = end
    if cursor < len(clause_text):
        segments.append({"text": clause_text[cursor:], "highlighted": False})
    return segments, relevant_chars


def get_incident_relevance(clause_text: str, incident_context: dict) -> tuple[list[dict], int] | None:
    """이 조항에서 주어진 사고 상황과 직접 관련된 부분만 노란색으로 표시할 구간을 계산한다.
    실패/무관련 시 (전체를 비강조 구간 1개로) 또는 None(호출부가 폴백)을 반환한다."""
    if not config.GEMINI_ENABLED or not clause_text or not clause_text.strip():
        return None
    situation = ", ".join(f"{k}: {v}" for k, v in incident_context.items() if v)
    if not situation:
        return None
    try:
        client = genai.Client(api_key=config.GEMINI_API_KEY)
        response = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=_RELEVANCE_PROMPT.format(situation=situation, clause_text=clause_text),
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=_RelevanceResult,
                temperature=0.1,
            ),
        )
        parsed: _RelevanceResult = response.parsed or _RelevanceResult.model_validate(json.loads(response.text))
        found = _locate_relevant(clause_text, parsed.spans)
        if found is None:
            logger.warning("조항 관련도 분석 검증 실패, 비강조 폴백")
            return [{"text": clause_text, "highlighted": False}], 0
        return _build_relevance_segments(clause_text, found)
    except Exception:
        logger.exception("조항 관련도 분석 실패")
        return None


def get_highlight_spans(db: Session, clause: Clause) -> list[dict] | None:
    """캐시된 결과가 있으면 그대로 반환. 없고 Gemini가 켜져 있으면 새로 분석해서 캐시 후 반환.
    실패하거나 Gemini가 꺼져 있으면 None(호출부가 단색 표시로 폴백)."""
    if clause.highlight_spans:
        try:
            return json.loads(clause.highlight_spans)
        except (json.JSONDecodeError, TypeError):
            pass  # 캐시가 깨졌으면 다시 분석

    if not config.GEMINI_ENABLED or not clause.text or not clause.text.strip():
        return None

    try:
        client = genai.Client(api_key=config.GEMINI_API_KEY)
        response = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=_SPAN_PROMPT.format(clause_text=clause.text),
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=_SpanResult,
                temperature=0.1,
            ),
        )
        parsed: _SpanResult = response.parsed or _SpanResult.model_validate(json.loads(response.text))
        spans = _locate_spans(clause.text, parsed.spans)
        if spans is None:
            logger.warning("clause %s: Gemini 하이라이트 검증 실패, 단색 폴백", clause.clause_id)
            return None

        clause.highlight_spans = json.dumps(spans, ensure_ascii=False)
        db.commit()
        return spans
    except Exception:
        logger.exception("clause %s: Gemini 하이라이트 분석 실패, 단색 폴백", clause.clause_id)
        return None
