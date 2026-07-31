"""
사고유형(incident_type) L1/L2 분류 + 수식자(modifiers) 추출.

claim_review.py의 담보 판단이 예전엔 키워드 휴리스틱(item_related/has_injury_signal)이었지만,
이제 incident_type 사전을 기준으로 판단하므로 "이 사고가 어떤 유형인지"를 먼저 확정해야 한다.
그 확정을 이 모듈이 담당한다.

절대 규칙(다른 nlu_gemini.py 프롬프트들과 동일한 원칙):
1. L1은 8개 중에서만 고른다(근거 부족하면 SPC로 보낸다 — 조용히 버리지 않는다).
2. L2는 해당 L1의 기존 후보 목록 중에서 고르되, 원문에 그 표현이 그대로 없어도 상식적으로
   충분히 그 범주라고 추론되면 골라도 된다("추상적으로 들어갈 수 있는 범위"). 하지만 근거가
   거의 없는데 억지로 끼워맞추면 안 되고, 그럴 땐 new_type_name으로 새 유형을 제안하게 한다
   (SPC_OTHER catch-all 원칙을 8개 L1 전체로 일반화한 것 — incident_type.needs_review=True로
   저장돼 사람이 나중에 검수한다).
3. Gemini가 비활성화(GEMINI_ENABLED=False)이거나 호출 실패면 예외를 삼키지 않고 상위에서
   처리하도록 값을 보수적으로 반환한다(L1은 SPC/confidence 0 — 질문에 전부 의존).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import config
from app.models.kb import IncidentType

logger = logging.getLogger(__name__)

L1_DESCRIPTIONS: dict[str, str] = {
    "INJ": "상해 — 사고로 인한 신체 부상(골절·열상·화상·사망·후유장해 등). 급격하고 우연한 외부 사고가 원인.",
    "ILL": "질병 — 감염병을 포함해 몸 안에서 비롯된 병으로 인한 사망·후유장해·치료. 외부 사고가 아님.",
    "PROP": "휴대품·재물 — 여행 중 소지품(휴대폰·카메라·캐리어·현금·여권 등)의 도난·파손·분실.",
    "LIA": "배상책임 — 여행 중 본인 과실로 남(사람·물건·숙소)에게 피해를 입힌 경우.",
    "TRV": "운송 — 항공·교통편의 지연·결항·수하물 지연/분실·항공기 납치.",
    "CHG": "여행변경 — 여행 자체의 취소, 또는 여행 중 중단·조기귀국.",
    "EMG": "긴급지원 — 수색구조, 의료이송, 사망 시 유해송환, 가족 방문 비용 등 긴급 지원 서비스.",
    "SPC": "특수·기타 — 전쟁·테러, 천재지변, 반려동물 돌봄, 또는 위 7개 어디에도 명확히 안 맞는 경우.",
}


class _L1ClassifySchema(BaseModel):
    l1_code: str
    confidence: float = 0.0
    reason: str = ""


class _L2ClassifySchema(BaseModel):
    l2_code: str | None = None
    confidence: float = 0.0
    reason: str = ""
    new_type_name: str | None = None
    new_type_reason: str | None = None


class _ModifiersSchema(BaseModel):
    activity: str | None = None   # 활동: 스키·수상레저·등산·렌터카운전 등
    location: str | None = None   # 장소: 해외/국내/이동중/숙박시설/공공장소
    timing: str | None = None     # 시점: 보험기간내외/여행기간내외 관련 특이사항
    status: str | None = None     # 상태: 음주/무면허/고의/기왕증
    target: str | None = None     # 대상: 본인/동반자/제3자/타인재물


@dataclass
class L2ClassifyResult:
    type_id: int | None
    l2_code: str | None
    confidence: float
    reason: str
    new_type_suggested: dict | None = None  # {"name": str, "reason": str} — l2_code가 None일 때만


_L1_PROMPT = """당신은 여행자보험 사고 접수를 돕는 사고유형 분류기입니다.
아래 "사고 설명"을 읽고, 아래 8개 대분류(L1) 중 가장 적합한 하나를 고르세요.

대분류 목록:
{l1_list}

절대 규칙:
1. 반드시 위 8개 코드 중 하나만 고르세요. 새 코드를 만들지 마세요.
2. 여러 대분류에 걸칠 수 있는 사고면(예: 다쳤는데 물건도 잃어버림) 사고 설명에서 가장
   핵심적인(먼저 언급되거나 더 심각한) 쪽을 고르세요. 나머지는 이후 단계에서 추가로 다뤄집니다.
3. 원문만으로 판단이 거의 안 서면 "SPC"를 고르고 confidence를 낮게(0.2 이하) 주세요.
   대충 추측해서 엉뚱한 대분류를 고르는 것보다 낫습니다.
4. confidence는 0.0~1.0. reason은 한 문장.

사고 설명:
\"\"\"{free_text}\"\"\"
"""

_L2_PROMPT = """당신은 여행자보험 사고 접수를 돕는 사고유형 세부분류기입니다.
이미 대분류는 "{l1_name}"({l1_code})로 확정됐습니다. 아래 세부분류(L2) 후보 중
가장 적합한 하나를 고르세요.

세부분류 후보:
{l2_list}

사고 설명:
\"\"\"{free_text}\"\"\"

지금까지 확인된 추가 정보:
{answers_text}

절대 규칙:
1. 후보 목록에 있는 l2_code 중 하나를 고르는 게 원칙입니다. 원문에 후보명과 똑같은 단어가
   없어도, 상식적으로 그 후보에 충분히 속한다고 추론되면 골라도 됩니다(예: "산에서 굴러
   다쳤다"는 별도 등산 후보가 없어도 일반 상해 후보에 속함).
2. 다만 근거가 거의 없는데 억지로 후보 하나에 끼워맞추지 마세요. 8개 후보 어디에도 안
   맞는다고 판단되면 l2_code는 null로 두고, new_type_name(간단한 한글 유형명)과
   new_type_reason(왜 기존 후보로 안 되는지)을 채우세요. 이 경우가 아니면 new_type_name은
   비워두세요.
3. 아직 정보가 부족해서(예: 추가 정보가 비어 있음) 후보들 사이 구분이 안 되면, 그래도 가장
   그럴듯한 후보를 confidence를 낮게(0.4 이하) 줘서 고르세요. null보다는 낮은 확신의 선택이
   낫습니다 — 위쪽 라우터가 confidence로 추가 질문 여부를 판단합니다.
4. confidence는 0.0~1.0. reason은 한 문장.

사고 설명과 후보 목록:
"""

_DOC_EXPLAIN_PROMPT = """다음은 여행자보험 사고 상황과, 청구 시 필요하다고 이미 정해진 서류
목록입니다. 이 서류들이 왜 필요한지 이 사고 상황에 맞춰 1~2문장으로 쉽게 설명하세요.

절대 규칙:
1. 목록에 없는 서류를 새로 추가하거나 추천하지 마세요 — 이미 정해진 목록을 사용자가
   이해하기 쉽게 설명하는 것만이 목적입니다.
2. 서류 발급 방법·절차를 지어내지 마세요.
3. 설명 문장만 출력하세요. 다른 말은 붙이지 마세요.

사고 상황: {situation}
필요 서류 목록: {docs}
"""

_MODIFIERS_PROMPT = """다음 여행자보험 사고 설명에서, 아래 5개 축에 해당하는 정보가 명시적으로
있으면만 채우세요. 없으면 null로 두세요(추측 금지).

- activity: 사고 당시 활동(예: 스키, 스쿠버다이빙, 등산, 렌터카 운전, 오토바이 등 — 특별히
  위험하거나 특약 면책과 관련될 수 있는 활동만. 그냥 "관광 중"이면 null로 두세요.)
- location: 장소 특징(해외/국내/이동 중/숙박시설/공공장소 중 원문에서 명확한 것만)
- timing: 여행기간·보험기간과 관련된 특이사항(예: "여행 마지막 날", "귀국 비행기 안에서")
- status: 음주/무면허/고의/기왕증 등 면책판단에 영향줄 수 있는 상태(명시된 경우만)
- target: 피해 대상(본인/동반자/제3자/타인재물 — 명확한 경우만)

사고 설명:
\"\"\"{free_text}\"\"\"
"""


def _get_client():
    from google import genai
    return genai.Client(api_key=config.GEMINI_API_KEY)


def _generate_json(client, prompt: str, schema: type[BaseModel]) -> BaseModel:
    import json as _json
    from google.genai import types

    response = client.models.generate_content(
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
    return schema.model_validate(_json.loads(response.text))


def classify_l1(free_text: str) -> tuple[str, float, str]:
    """자유서술 → (l1_code, confidence, reason). 실패/미설정 시 ("SPC", 0.0, ...)."""
    text = (free_text or "").strip()
    if not text or not config.GEMINI_ENABLED:
        return "SPC", 0.0, "분류 근거 없음(자유서술 없음 또는 Gemini 미설정)"

    l1_list = "\n".join(f"- {code}: {desc}" for code, desc in L1_DESCRIPTIONS.items())
    try:
        client = _get_client()
        result = _generate_json(
            client, _L1_PROMPT.format(l1_list=l1_list, free_text=text), _L1ClassifySchema
        )
    except Exception:
        logger.exception("classify_l1 실패, SPC로 폴백")
        return "SPC", 0.0, "분류 실패(API 오류)"

    if result.l1_code not in L1_DESCRIPTIONS:
        return "SPC", 0.0, f"모델이 알 수 없는 코드 반환({result.l1_code}) — 안전하게 SPC 처리"
    return result.l1_code, round(result.confidence, 2), result.reason


def classify_l2(
    db: Session, l1_code: str, free_text: str, answers: dict[str, str] | None = None,
) -> L2ClassifyResult:
    """L1이 확정된 뒤, 그 L1의 L2 후보 중 하나를 고르거나 새 유형을 제안한다."""
    root = db.query(IncidentType).filter_by(l1_code=l1_code, parent_id=None).first()
    candidates = (
        db.query(IncidentType)
        .filter(IncidentType.parent_id == root.type_id, IncidentType.is_active.is_(True))
        .all()
        if root else []
    )
    if not candidates:
        return L2ClassifyResult(type_id=root.type_id if root else None, l2_code=l1_code, confidence=0.0, reason="L2 후보 없음(L1 루트로 처리)")

    if not config.GEMINI_ENABLED or not (free_text or "").strip():
        # 근거가 없으면 첫 후보를 낮은 확신으로 잠정 선택 — 라우터가 질문으로 보완한다.
        first = candidates[0]
        return L2ClassifyResult(type_id=first.type_id, l2_code=first.l2_code, confidence=0.0, reason="근거 부족(자유서술 없음 또는 Gemini 미설정)")

    l2_list = "\n".join(f"- {c.l2_code}: {c.name}" for c in candidates)
    answers_text = "\n".join(f"- {k}: {v}" for k, v in (answers or {}).items() if v) or "(아직 없음)"

    try:
        client = _get_client()
        prompt = _L2_PROMPT.format(
            l1_name=L1_DESCRIPTIONS.get(l1_code, l1_code), l1_code=l1_code,
            l2_list=l2_list, free_text=free_text, answers_text=answers_text,
        )
        result = _generate_json(client, prompt, _L2ClassifySchema)
    except Exception:
        logger.exception("classify_l2 실패, L1 루트로 폴백")
        first = candidates[0]
        return L2ClassifyResult(type_id=first.type_id, l2_code=first.l2_code, confidence=0.0, reason="분류 실패(API 오류)")

    valid_codes = {c.l2_code: c for c in candidates}
    if result.l2_code and result.l2_code in valid_codes:
        chosen = valid_codes[result.l2_code]
        return L2ClassifyResult(type_id=chosen.type_id, l2_code=chosen.l2_code, confidence=round(result.confidence, 2), reason=result.reason)

    if result.new_type_name:
        return L2ClassifyResult(
            type_id=None, l2_code=None, confidence=round(result.confidence, 2), reason=result.reason,
            new_type_suggested={"name": result.new_type_name, "reason": result.new_type_reason or ""},
        )

    # 모델이 후보도 못 고르고 새 유형 제안도 안 했으면(스키마 위반 등) 첫 후보로 안전하게 폴백.
    first = candidates[0]
    return L2ClassifyResult(type_id=first.type_id, l2_code=first.l2_code, confidence=0.0, reason="모델 응답 불충분 — 잠정 폴백")


def extract_modifiers(free_text: str) -> dict:
    """실패해도 전체 흐름이 죽지 않도록 예외를 삼키고 빈 dict를 반환한다."""
    text = (free_text or "").strip()
    if not text or not config.GEMINI_ENABLED:
        return {}
    try:
        client = _get_client()
        result = _generate_json(client, _MODIFIERS_PROMPT.format(free_text=text), _ModifiersSchema)
    except Exception:
        logger.exception("extract_modifiers 실패, 빈 값으로 처리")
        return {}
    return {k: v for k, v in result.model_dump().items() if v}


def explain_docs_for_incident(doc_names: list[str], incident_context: dict) -> str | None:
    """필요서류 목록을 이 사고 상황에 맞춰 한 문장으로 풀어 설명한다. 목록 자체는 이미
    CoverageDocMap(결정론적)로 정해진 것이고, 여기선 "왜 필요한지"만 사고 내용과 엮어
    설명한다 — 새 서류를 추천하지 않는다. 실패해도 findings 생성 흐름이 죽지 않도록
    예외를 삼키고 None을 반환한다(호출부는 그러면 기본 설명만 쓴다)."""
    if not config.GEMINI_ENABLED or not doc_names:
        return None
    situation = ", ".join(f"{k}: {v}" for k, v in incident_context.items() if v)
    if not situation:
        return None
    try:
        from google.genai import types

        client = _get_client()
        response = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=_DOC_EXPLAIN_PROMPT.format(situation=situation, docs=", ".join(doc_names)),
            config=types.GenerateContentConfig(temperature=0.2),
        )
        text = (response.text or "").strip()
        return text or None
    except Exception:
        logger.exception("explain_docs_for_incident 실패, 기본 설명으로 대체")
        return None


def create_reviewable_type(db: Session, l1_code: str, name: str) -> IncidentType:
    """classify_l2가 new_type_suggested를 반환했을 때 실제로 L2 행을 만든다.

    l2_code는 사람이 검수하며 다시 이름 붙일 것을 전제로 임시 생성한다(l1_code + 일련번호).
    같은 이름이 이미 있으면(이전에 같은 사고유형이 여러 번 발견됐으면) 재사용한다.
    """
    existing = db.query(IncidentType).filter_by(l1_code=l1_code, name=name).first()
    if existing:
        return existing

    root = db.query(IncidentType).filter_by(l1_code=l1_code, parent_id=None).first()
    n = db.query(IncidentType).filter(IncidentType.l1_code == l1_code, IncidentType.needs_review.is_(True)).count() + 1
    new_type = IncidentType(
        l1_code=l1_code, l2_code=f"{l1_code}_NEW_{n}", name=name,
        parent_id=root.type_id if root else None, is_active=True, needs_review=True,
    )
    db.add(new_type)
    db.flush()
    return new_type
