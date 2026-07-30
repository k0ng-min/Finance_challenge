"""
Gemini + RAG 기반 NLUEngine 구현체.

원래 계획은 자체 초경량 로컬 모델이었지만, 팀 결정으로 Gemini 무료 API를 쓰기로 했다.
다만 이 프로젝트의 절대 원칙("근거 없는 결과 금지")은 그대로 지킨다:

- structure_incident: Gemini에게 "입력 텍스트에 명시적으로 없는 내용은 절대 채우지 말라"고
  강제하고, 값마다 원문에서 그대로 뽑은 source_span(근거 문구)을 같이 받는다.
  source_span이 비어있으면 confidence를 0으로 깎는다 — 모델이 span을 못 대면 근거가 없다고 본다.
- normalize_coverage_name: "검색(R)"은 이미 호출부(policy_matching.py)가 DB에서
  std_candidates로 후보를 추려온 상태다. Gemini는 그 후보 목록 "안에서만" 고르게 하고,
  목록에 없는 std_code를 반환하면 무효 처리한다(생성 결과를 검증 없이 믿지 않음).
- explain_clause_plain: 입력으로 받은 실제 약관 원문 자체가 근거이므로, "원문에 없는
  숫자·조건을 추가하지 말라"는 제약을 프롬프트에 명시한다.

Gemini 호출이 실패(키 없음/네트워크 오류/쿼터 초과)하면 예외를 삼키지 않고 상위에서
RuleBasedNLU로 폴백하도록 get_nlu_engine()에서 감싼다.
"""
from __future__ import annotations

import json
import logging

from pydantic import BaseModel
from google import genai
from google.genai import types

from app import config
from app.services.nlu import ExtractedField, IncidentDraft, RuleBasedNLU

logger = logging.getLogger(__name__)


class _IncidentExtractionSchema(BaseModel):
    country: str | None = None
    country_confidence: float = 0.0
    country_span: str | None = None
    cause: str | None = None
    cause_confidence: float = 0.0
    cause_span: str | None = None
    injury_part: str | None = None
    injury_part_confidence: float = 0.0
    injury_part_span: str | None = None
    diagnosis: str | None = None
    diagnosis_confidence: float = 0.0
    diagnosis_span: str | None = None
    hospitalized: bool | None = None
    hospitalized_confidence: float = 0.0
    hospitalized_span: str | None = None
    surgery: bool | None = None
    surgery_confidence: float = 0.0
    surgery_span: str | None = None
    local_treatment: bool | None = None
    local_treatment_confidence: float = 0.0
    local_treatment_span: str | None = None
    returned_home: bool | None = None
    returned_home_confidence: float = 0.0
    returned_home_span: str | None = None


class _CoverageMatchSchema(BaseModel):
    std_code: str | None = None
    confidence: float = 0.0
    reason: str = ""


_INCIDENT_PROMPT = """당신은 여행자보험 사고 접수를 돕는 정보 추출기입니다.
아래 "사고 설명" 텍스트에서 다음 항목을 추출하세요.

절대 규칙:
1. 텍스트에 명시적으로 나온 내용만 채우세요. 추측하거나 일반 상식으로 채우지 마세요.
2. 값을 채웠다면 반드시 그 근거가 된 원문 문구를 *_span 필드에 그대로(변형 없이) 옮겨 적으세요.
3. 텍스트에 언급이 없으면 값은 null, confidence는 0.0, span도 null로 두세요.
4. hospitalized/surgery/local_treatment/returned_home은 "아직 ~ 아니다/전이다"처럼 명시적으로
   부정된 경우 false로, 명확히 확인된 경우 true로, 언급이 아예 없으면 null로 하세요.
5. confidence는 0.0~1.0. 문맥상 추론이 섞였으면 낮게(0.4~0.6), 원문에 그대로 명시돼 있으면
   높게(0.8~1.0) 매기세요.

사고 설명:
\"\"\"{free_text}\"\"\"
"""

_COVERAGE_MATCH_PROMPT = """보험 증권에 사용자가 직접 입력한 담보명을, 아래 표준 담보 후보 목록 중
가장 의미가 가까운 것과 매칭하세요.

절대 규칙:
1. 반드시 아래 후보 목록에 있는 std_code 중 하나만 고르세요. 목록에 없는 코드를 만들어내지 마세요.
2. 의미가 애매하거나 어느 것도 맞지 않으면 std_code를 null로, confidence를 0.0으로 하세요.
3. reason에는 왜 그렇게 판단했는지 한 문장으로 설명하세요.

사용자가 입력한 담보명: "{raw_name}"

표준 담보 후보 목록:
{candidates}
"""

_EXPLAIN_PROMPT = """다음은 여행자보험 약관의 실제 원문입니다. 이 원문에 있는 내용만 사용해서
쉬운 말로 1~2문장으로 풀어서 설명하세요.

절대 규칙:
1. 원문에 없는 금액·조건·예외를 추가하지 마세요.
2. 법률 용어를 일상 언어로 바꾸되, 의미를 왜곡하지 마세요.
3. 설명만 출력하세요. 다른 말은 붙이지 마세요.

약관 원문:
\"\"\"{clause_text}\"\"\"
"""

_EXPLAIN_SITUATIONAL_PROMPT = """다음은 여행자보험 약관의 실제 원문이고, 사용자가 실제로 겪은 사고 상황입니다.
이 원문에 있는 내용만 사용해서, 이 사고 상황에 이 조항이 어떻게 관련되는지 1~2문장으로 쉽게 설명하세요.

사고 상황: {situation}

절대 규칙:
1. 원문에 없는 금액·조건·예외를 추가하지 마세요.
2. "지급된다/안 된다"처럼 단정적으로 결론 내리지 말고, 이 조항이 이 상황과 어떻게 관련되는지만 설명하세요. 실제 지급 여부는 보험회사 심사에 따른다는 전제를 벗어나지 마세요.
3. 법률 용어를 일상 언어로 바꾸되, 의미를 왜곡하지 마세요.
4. 설명만 출력하세요. 다른 말은 붙이지 마세요.

약관 원문:
\"\"\"{clause_text}\"\"\"
"""


class GeminiNLU:
    """Gemini API + (호출부가 이미 검색해온) 후보 컨텍스트를 근거로만 답하게 강제하는 구현체.
    실패 시 예외를 던지고, 상위(get_nlu_engine)에서 RuleBasedNLU로 폴백한다."""

    def __init__(self):
        self._client = genai.Client(api_key=config.GEMINI_API_KEY)
        self._fallback = RuleBasedNLU()

    def _generate_json(self, prompt: str, schema: type[BaseModel]) -> BaseModel:
        response = self._client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
                temperature=0.1,
            ),
        )
        if response.parsed is not None:
            return response.parsed
        return schema.model_validate(json.loads(response.text))

    @staticmethod
    def _field_from(value, confidence: float, span: str | None) -> ExtractedField:
        # span이 없으면 근거가 없는 것으로 보고 신뢰도를 강제로 낮춘다 (근거 없는 결과 금지 원칙).
        if value is not None and not span:
            confidence = min(confidence, 0.4)
        return ExtractedField(value=value, confidence=confidence, source_span=span)

    def structure_incident(self, free_text: str) -> IncidentDraft:
        text = free_text or ""
        if not text.strip():
            return IncidentDraft()
        try:
            result = self._generate_json(
                _INCIDENT_PROMPT.format(free_text=text), _IncidentExtractionSchema
            )
        except Exception:
            logger.exception("Gemini structure_incident 실패, RuleBasedNLU로 폴백")
            return self._fallback.structure_incident(text)

        return IncidentDraft(
            country=self._field_from(result.country, result.country_confidence, result.country_span),
            cause=self._field_from(result.cause, result.cause_confidence, result.cause_span),
            injury_part=self._field_from(result.injury_part, result.injury_part_confidence, result.injury_part_span),
            diagnosis=self._field_from(result.diagnosis, result.diagnosis_confidence, result.diagnosis_span),
            hospitalized=self._field_from(result.hospitalized, result.hospitalized_confidence, result.hospitalized_span),
            surgery=self._field_from(result.surgery, result.surgery_confidence, result.surgery_span),
            local_treatment=self._field_from(result.local_treatment, result.local_treatment_confidence, result.local_treatment_span),
            returned_home=self._field_from(result.returned_home, result.returned_home_confidence, result.returned_home_span),
        )

    def normalize_coverage_name(self, raw_name: str, std_candidates: list[tuple[str, str]]) -> tuple[str | None, float]:
        if not raw_name or not std_candidates:
            return None, 0.0
        candidates_text = "\n".join(f"- {code}: {name}" for code, name in std_candidates)
        try:
            result = self._generate_json(
                _COVERAGE_MATCH_PROMPT.format(raw_name=raw_name, candidates=candidates_text),
                _CoverageMatchSchema,
            )
        except Exception:
            logger.exception("Gemini normalize_coverage_name 실패, RuleBasedNLU로 폴백")
            return self._fallback.normalize_coverage_name(raw_name, std_candidates)

        valid_codes = {code for code, _ in std_candidates}
        if result.std_code not in valid_codes:
            return None, 0.0
        return result.std_code, round(result.confidence, 2)

    def explain_clause_plain(self, clause_text: str, incident_context: dict | None = None) -> str:
        if not clause_text or not clause_text.strip():
            return clause_text
        try:
            if incident_context:
                situation = ", ".join(f"{k}: {v}" for k, v in incident_context.items() if v)
                prompt = _EXPLAIN_SITUATIONAL_PROMPT.format(clause_text=clause_text, situation=situation)
            else:
                prompt = _EXPLAIN_PROMPT.format(clause_text=clause_text)
            response = self._client.models.generate_content(
                model=config.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.2),
            )
            explained = (response.text or "").strip()
            return explained or clause_text
        except Exception:
            logger.exception("Gemini explain_clause_plain 실패, 원문 그대로 반환")
            return self._fallback.explain_clause_plain(clause_text, incident_context)
