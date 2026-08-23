"""
사고유형(incident_type) L1/L2 분류 + 수식자(modifiers) 추출.

claim_review.py의 담보 판단이 예전엔 키워드 휴리스틱(item_related/has_injury_signal)이었지만,
이제 incident_type 사전을 기준으로 판단하므로 "이 사고가 어떤 유형인지"를 먼저 확정해야 한다.
그 확정을 이 모듈이 담당한다.

절대 규칙(다른 nlu_gemini.py 프롬프트들과 동일한 원칙):
1. L1은 8개 중에서만 고른다(근거 부족하면 SPC 루트에서 추가 질문한다).
2. L2는 해당 L1의 기존 후보 목록 중에서 고르되, 원문에 그 표현이 그대로 없어도 상식적으로
   충분히 그 범주라고 추론되면 골라도 된다("추상적으로 들어갈 수 있는 범위"). 하지만 근거가
   거의 없는데 억지로 끼워맞추면 안 되고, 그럴 땐 new_type_name으로 새 유형을 제안하게 한다
   (SPC_OTHER catch-all 원칙을 8개 L1 전체로 일반화한 것 — incident_type.needs_review=True로
   저장돼 사람이 나중에 검수한다).
3. Gemini가 비활성화되거나 호출에 실패하거나 신뢰 임계값에 못 미치면 L2를 추측하지 않는다.
   L1 루트에 보류(abstain)해 후속 질문으로 정보를 보강한다.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import config
from app.models.kb import IncidentType

logger = logging.getLogger(__name__)

# confidence는 정확도 확률이 아니라 자동 분류/추가 질문을 가르는 라우팅 신호다.
# incident-eval-v2 calibration 80건의 2차원 grid search로 선택하고 held-out 80건으로 검증했다.
DEFAULT_L1_AUTO_THRESHOLD = 0.40
DEFAULT_L2_AUTO_THRESHOLD = 0.80

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
    abstained: bool = False


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
3. 아직 정보가 부족해서 후보들 사이 구분이 안 되면 l2_code를 null로 두세요. 억지로 하나를
   고르지 마세요. new_type_name은 기존 후보 어디에도 속하지 않을 때만 사용합니다.
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


# --- Gemini 없이 대분류만이라도 잡는 키워드 폴백 -------------------------------
#
# 예전에는 키가 없거나 호출이 실패하면 무조건 SPC(특수·기타)로 보류했다. 그런데 조항
# 매핑은 대분류마다 따로 달려 있어서, SPC로 보류되면 "다리를 다쳤어요"에도 관련 약관이
# 한 건도 안 걸린다 — 사용자에게는 "약관이 없다"로 보이지만 KB에는 상해 약관이 그대로
# 있다. 그래서 대분류만이라도 사고 내용에서 직접 잡는다.
#
# 이건 분류를 지어내는 게 아니라 "어느 서랍을 열지"를 정하는 일이다. 실제로 보여주는
# 내용은 그 뒤에도 여전히 약관 원문 근거가 있는 것만이다. 근거가 약한 추정이므로 확신은
# 자동 임계값 아래로 둬서, 세부유형은 반드시 사용자에게 물어 확인하게 한다.
_FALLBACK_CONFIDENCE = 0.35

# 먼저 걸리는 것이 이긴다 — 위쪽일수록 다른 대분류와 헷갈릴 여지가 적은 단서다.
_FALLBACK_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("TRV", ("결항", "지연", "수하물", "위탁수하물", "항공편", "비행기", "납치", "환승")),
    ("CHG", ("여행취소", "여행 취소", "일정취소", "일정 취소", "조기귀국", "조기 귀국",
             "중단", "취소했", "여행을 접")),
    ("EMG", ("조난", "수색", "구조", "이송", "송환", "유해", "실종")),
    # "깨졌"(내 물건이 깨짐)과 "깨뜨렸"(내가 남의 것을 깨뜨림)은 걸리는 약관이 통째로
    # 다르다 — 앞은 휴대품손해, 뒤는 배상책임이다. 타동사 형태를 여기서 먼저 잡는다.
    ("LIA", ("배상", "물어주", "변상", "다치게", "손해를 입혔", "파손시",
             "깨뜨", "깨트", "깨먹", "부숴", "부쉈", "망가뜨", "망가트")),
    ("PROP", ("도난", "소매치기", "분실", "잃어버", "훔쳐", "파손", "깨졌", "여권")),
    ("ILL", ("질병", "병원", "감염", "격리", "발열", "복통", "배탈", "설사", "식중독", "코로나", "몸살", "아파", "아팠")),
    ("INJ", ("다쳤", "다침", "부상", "골절", "부러", "삐", "염좌", "화상", "찢어", "베였", "타박", "넘어져", "부딪")),
)


def _score_keywords(text: str, keywords: tuple[str, ...]) -> tuple[int, str | None]:
    """본문에 걸린 단서 개수와, 그중 첫 단서를 돌려준다."""
    hit = None
    count = 0
    for word in keywords:
        if word in text:
            count += 1
            if hit is None:
                hit = word
    return count, hit


def _fallback_l1(text: str) -> tuple[str, float, str] | None:
    """사고 내용에서 대분류 단서를 찾는다. 못 찾으면 None(=SPC 보류).

    먼저 걸린 하나가 이기게 두면 스쳐 지나가는 단어 하나에 대분류가 끌려간다 —
    "무릎이 깨졌고 발목도 삐었어요"가 '깨졌'(휴대품 파손) 때문에 휴대품 사고가 됐다.
    단서 개수를 세서 더 많이 걸린 쪽을 고르고, 같으면 목록 위쪽(=다른 대분류와 헷갈릴
    여지가 적은 단서)을 쓴다."""
    lowered = text.lower()
    best: tuple[int, int, str, str] | None = None  # (개수, -순번, 코드, 단서)
    for order, (code, keywords) in enumerate(_FALLBACK_KEYWORDS):
        count, hit = _score_keywords(lowered, keywords)
        if count == 0:
            continue
        candidate = (count, -order, code, hit or "")
        if best is None or candidate > best:
            best = candidate
    if best is None:
        return None
    _count, _order, code, hit = best
    return code, _FALLBACK_CONFIDENCE, f"사고 내용의 '{hit}'로 대분류만 추정(세부유형은 확인 필요)"


# 대분류 안에서 세부유형까지 좁히는 단서. 대분류만 잡으면 그 대분류의 조항이 전부
# 딸려온다 — 도난인지 분실인지에 따라 보상 여부가 갈리는데도 둘 다 보여주게 된다.
# 단서가 뚜렷할 때만 좁히고, 없으면 좁히지 않는다(근거 없이 찍지 않는다).
_FALLBACK_L2_KEYWORDS: dict[str, tuple[tuple[str, tuple[str, ...]], ...]] = {
    "PROP": (
        ("PROP_PASSPORT_LOSS", ("여권",)),
        ("PROP_CASH_SECURITIES", ("현금", "지폐", "수표", "유가증권")),
        ("PROP_THEFT", ("도난", "소매치기", "훔쳐", "강취", "털렸", "빼앗")),
        ("PROP_DAMAGE", ("파손", "깨졌", "깨뜨", "부서", "망가")),
        ("PROP_LOSS", ("분실", "잃어버", "두고 내렸", "놓고 왔")),
    ),
    "TRV": (
        ("TRV_HIJACK", ("납치", "하이재킹")),
        ("TRV_BAGGAGE_LOSS", ("수하물 분실", "수하물을 잃", "짐을 잃", "수하물 못 찾")),
        ("TRV_BAGGAGE_DELAY", ("수하물", "짐이 안", "위탁수하물", "캐리어가 안")),
        ("TRV_FLIGHT_DELAY", ("지연", "결항", "연착", "취소된 항공")),
    ),
    "INJ": (
        ("INJ_DEATH_DISABILITY", ("사망", "후유장해", "장해")),
        ("INJ_DOMESTIC_TREATMENT", ("귀국 후", "귀국후", "한국에서 치료", "국내에서 치료")),
        ("INJ_OVERSEAS_TREATMENT", ("현지", "해외에서", "병원", "치료", "입원", "수술")),
    ),
    "ILL": (
        ("ILL_DEATH_DISABILITY", ("사망", "고도후유장해")),
        ("ILL_INFECTIOUS", ("감염병", "격리", "코로나", "확진", "전염")),
        ("ILL_DOMESTIC_TREATMENT", ("귀국 후", "귀국후", "국내에서 치료")),
        ("ILL_OVERSEAS_TREATMENT", ("현지", "해외에서", "병원", "치료", "입원")),
    ),
    "LIA": (
        ("LIA_LODGING", ("호텔", "숙소", "객실", "에어비앤비", "임차")),
        ("LIA_PERSONAL", ("다치게", "부상을 입혔", "사람을")),
        ("LIA_PROPERTY", ("물건", "파손시켰", "깨뜨", "변상", "물어주")),
    ),
    "CHG": (
        ("CHG_INTERRUPTION", ("중단", "조기귀국", "조기 귀국", "돌아왔")),
        ("CHG_CANCELLATION", ("취소",)),
    ),
    "EMG": (
        ("EMG_REPATRIATION", ("유해", "시신", "송환")),
        ("EMG_RESCUE", ("조난", "수색", "구조", "실종")),
        ("EMG_MEDICAL_TRANSPORT", ("이송", "후송", "에어앰뷸런스")),
        ("EMG_FAMILY_VISIT", ("가족 방문", "가족이 와", "보호자 항공")),
    ),
    "SPC": (
        ("SPC_WAR_TERROR", ("전쟁", "테러", "폭동", "내전")),
        ("SPC_NATURAL_DISASTER", ("지진", "홍수", "태풍", "화산", "천재지변", "쓰나미")),
        ("SPC_PET_CARE", ("반려동물", "강아지", "고양이", "펫")),
    ),
}


def _fallback_l2(l1_code: str, text: str) -> tuple[str, str] | None:
    """(l2_code, 걸린 단서). 단서가 없으면 None."""
    table = _FALLBACK_L2_KEYWORDS.get(l1_code)
    if not table:
        return None
    lowered = text.lower()
    best: tuple[int, int, str, str] | None = None
    for order, (code, keywords) in enumerate(table):
        count, hit = _score_keywords(lowered, keywords)
        if count == 0:
            continue
        candidate = (count, -order, code, hit or "")
        if best is None or candidate > best:
            best = candidate
    if best is None:
        return None
    return best[2], best[3]


def classify_l1(free_text: str, *, raise_on_error: bool = False) -> tuple[str, float, str]:
    """자유서술 → (l1_code, confidence, reason).

    운영에서는 API 실패를 안전하게 abstain한다. 정량평가는 실패 응답이 예측으로 섞이면 안 되므로
    ``raise_on_error=True``로 원래 예외를 받아 재시도하거나 평가를 중단할 수 있다.
    """
    text = (free_text or "").strip()
    if not text:
        return "SPC", 0.0, "분류 근거 없음(자유서술 없음)"
    if not config.GEMINI_ENABLED:
        return _fallback_l1(text) or ("SPC", 0.0, "분류 근거 없음(Gemini 미설정, 짚을 단서도 없음)")

    l1_list = "\n".join(f"- {code}: {desc}" for code, desc in L1_DESCRIPTIONS.items())
    try:
        client = _get_client()
        result = _generate_json(
            client, _L1_PROMPT.format(l1_list=l1_list, free_text=text), _L1ClassifySchema
        )
    except Exception:
        if raise_on_error:
            raise
        logger.exception("classify_l1 실패 — 사고 내용의 단서로 대분류만 추정")
        return _fallback_l1(text) or ("SPC", 0.0, "분류 실패(API 오류, 짚을 단서도 없음)")

    if result.l1_code not in L1_DESCRIPTIONS:
        return "SPC", 0.0, f"모델이 알 수 없는 코드 반환({result.l1_code}) — 안전하게 SPC 처리"
    return result.l1_code, round(result.confidence, 2), result.reason


def _l2_from_keywords(candidates, l1_code: str, free_text: str, root):
    """Gemini를 못 쓸 때, 사고 내용의 단서로 세부유형까지 좁힌다. 단서가 없으면 None.

    대분류만 잡아두면 그 대분류의 조항이 전부 딸려온다 — 도난인지 분실인지에 따라
    보상 여부가 갈리는데도 둘 다 보여주게 된다. 단서가 뚜렷할 때만 좁히고, 확신은
    자동 임계값 아래로 둬서 사용자 답변으로 다시 확인하게 한다."""
    picked = _fallback_l2(l1_code, (free_text or "").strip())
    if picked is None:
        return None
    code, hit = picked
    match = next((c for c in candidates if c.l2_code == code), None)
    if match is None:
        return None
    return L2ClassifyResult(
        type_id=match.type_id, l2_code=match.l2_code, confidence=_FALLBACK_CONFIDENCE,
        reason=f"사고 내용의 '{hit}'로 세부유형을 좁힘(확인 필요)", abstained=False,
    )


def classify_l2(
    db: Session, l1_code: str, free_text: str, answers: dict[str, str] | None = None,
    *, auto_threshold: float = DEFAULT_L2_AUTO_THRESHOLD, raise_on_error: bool = False,
) -> L2ClassifyResult:
    """L1이 정해진 뒤 L2를 분류한다.

    confidence는 보정된 확률이 아니라 라우팅 신호다. 임계값 미만, 비활성화, API 오류,
    불완전 응답은 모두 L1 루트에 abstain한다. 이 함수는 근거 없는 L2를 반환하지 않는다.
    """
    root = db.query(IncidentType).filter_by(l1_code=l1_code, parent_id=None).first()
    candidates = (
        db.query(IncidentType)
        .filter(IncidentType.parent_id == root.type_id, IncidentType.is_active.is_(True))
        .all()
        if root else []
    )
    if not candidates:
        return L2ClassifyResult(
            type_id=root.type_id if root else None, l2_code=None, confidence=0.0,
            reason="L2 후보 없음(L1 루트에서 추가 정보 확인)", abstained=True,
        )

    if not config.GEMINI_ENABLED or not (free_text or "").strip():
        narrowed = _l2_from_keywords(candidates, l1_code, free_text, root)
        if narrowed is not None:
            return narrowed
        return L2ClassifyResult(
            type_id=root.type_id if root else None, l2_code=None, confidence=0.0,
            reason="근거 부족(자유서술 없음 또는 Gemini 미설정) — 추가 정보 필요",
            abstained=True,
        )

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
        if raise_on_error:
            raise
        logger.exception("classify_l2 실패 — 사고 내용의 단서로 세부유형만 추정")
        narrowed = _l2_from_keywords(candidates, l1_code, free_text, root)
        if narrowed is not None:
            return narrowed
        return L2ClassifyResult(
            type_id=root.type_id if root else None, l2_code=None, confidence=0.0,
            reason="분류 실패(API 오류) — L1 루트에서 추가 정보 필요", abstained=True,
        )

    valid_codes = {c.l2_code: c for c in candidates}
    if result.l2_code and result.l2_code in valid_codes:
        chosen = valid_codes[result.l2_code]
        confidence = round(max(0.0, min(1.0, result.confidence)), 2)
        if confidence < auto_threshold:
            return L2ClassifyResult(
                type_id=root.type_id if root else None, l2_code=None, confidence=confidence,
                reason=f"신뢰 신호 {confidence:.2f}가 자동 분류 임계값 {auto_threshold:.2f} 미만 — 추가 정보 필요",
                abstained=True,
            )
        return L2ClassifyResult(
            type_id=chosen.type_id, l2_code=chosen.l2_code, confidence=confidence,
            reason=result.reason, abstained=False,
        )

    if result.new_type_name:
        return L2ClassifyResult(
            type_id=root.type_id if root else None, l2_code=None,
            confidence=round(max(0.0, min(1.0, result.confidence)), 2), reason=result.reason,
            new_type_suggested={"name": result.new_type_name, "reason": result.new_type_reason or ""},
            abstained=True,
        )

    return L2ClassifyResult(
        type_id=root.type_id if root else None, l2_code=None, confidence=0.0,
        reason="모델 응답 불충분 — L1 루트에서 추가 정보 필요", abstained=True,
    )


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
    """관리자 검수·오프라인 시드 작업에서만 reviewable L2 행을 만든다.

    런타임 사고 분류에서는 자동 호출하지 말아야 한다. 모델 제안은 L1 루트에 abstain한 뒤
    별도 관리자 검수 절차를 거쳐야 하며, 현재 incidents router는 이 함수를 호출하지 않는다.

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
