"""사고 내용에 맞춰 추가 확인 질문을 그때그때 만들어 내는 Gemini 호출.

왜 필요했나
-----------
예전에는 질문이 전부 question_bank에 미리 적혀 있었다(seed_questions.py). 사고를
L1(상해/질병/휴대품/…)으로 분류한 뒤 그 L1에 태그된 문항을 impact_weight 순으로
꺼내 물었다. 문제는 두 방향으로 났다.

  · 이미 답이 적혀 있는 걸 또 물었다 — "발목이 부러져서 입원했습니다"라고 써도
    "병원에 입원하셨나요, 통원 치료만 받으셨나요?"가 그대로 나왔다.
  · 이 사고에서만 중요한 건 아무도 묻지 않았다 — "휴대폰을 분실했다"에서 정작
    갈리는 건 잠금장치가 있었는지·경찰 신고를 했는지인데, 뱅크에 없으면 못 묻는다.

무엇을 주고 무엇을 받나
-----------------------
사고 자유서술과 지금까지 확보된 값, 그리고 **담보 판단에 실제로 쓰이는 필드 목록**을
넘긴다. 모델은 질문 2~4개를 만들되, 그중 담보 판단에 쓰이는 필드에 해당하는 질문은
반드시 그 필드 이름(target_field)을 그대로 붙여야 한다 — 그래야 답변이
claim_review.py가 보는 자리로 들어간다. 그 목록에 없는 질문은 `ai_`로 시작하는 새
필드 이름을 붙이게 하고, 답변은 incident.modifiers에 쌓인다.

실패하면
--------
None을 돌려준다. 호출부(claim_review.pending_questions)는 그러면 기존 공용 뱅크
질문을 그대로 쓴다 — 사고 접수 흐름이 Gemini 가용성에 묶이지 않는다.
"""
from __future__ import annotations

import json
import logging
import re

from pydantic import BaseModel
from sqlalchemy.orm import Session
from google import genai
from google.genai import types

from app import config
from app.models.kb import IncidentType
from app.models.question import QuestionBank
from app.models.user import Incident

logger = logging.getLogger(__name__)

# 한 번에 물어볼 질문 수의 상한. 사고 접수는 한 화면에 한 문항씩 넘기는 흐름이라,
# 너무 많으면 결과를 보기까지의 길이 길어져 중간에 이탈한다.
MAX_GENERATED_QUESTIONS = 4

# 담보 판단(claim_review.py)이 실제로 읽는 필드 — 이 이름을 그대로 붙여야 답변이
# incident 컬럼/merged 경로로 흘러 들어간다. 설명은 프롬프트에 그대로 나간다.
KNOWN_TARGET_FIELDS: dict[str, str] = {
    "diagnosis": "진단명 또는 증상(상해)",
    "hospitalized": "입원 여부(예/아니오)",
    "surgery": "수술 여부(예/아니오)",
    "local_treatment": "현지에서 치료받았는지 여부(예/아니오)",
    "returned_home": "이미 귀국했는지 여부(예/아니오)",
    "medical_cost": "지출한 의료비 금액",
    "item_damage_type": "휴대품 손해가 도난인지 파손인지 분실인지",
}

_PROMPT = """당신은 여행자보험 청구를 돕는 상담원입니다. 아래 사고 내용을 읽고, 보험금 청구
가능 여부를 판단하는 데 **아직 부족한 정보**만 골라 추가 질문을 만드세요.

사고 내용(사용자가 직접 쓴 글):
\"\"\"{free_text}\"\"\"

분류된 사고 대분류: {l1_code}

이 대분류 안에서 아직 어느 세부유형인지 정해지지 않았습니다. 후보는 이렇습니다.
{l2_candidates}
세부유형이 갈리면 적용되는 약관 조항이 통째로 달라집니다. **후보를 실제로 갈라낼 수
있는 질문**을 우선으로 만드세요 — 답을 듣고도 후보가 그대로 남는 질문은 만들지 마세요.

이미 확보된 정보(다시 묻지 마세요):
{known}

질문을 만들 때 지켜야 할 것:
1. 최대 {max_questions}개까지만 만드세요. 꼭 필요한 것이 적으면 적게 만들어도 됩니다.
   사고 내용만으로 충분히 판단할 수 있으면 빈 목록을 주세요.
2. **사고 내용에 이미 적혀 있는 것은 절대 다시 묻지 마세요.**
3. 이 사고에서 실제로 보상 여부가 갈리는 지점을 물으세요(예: 휴대품이라면 도난인지
   분실인지, 잠금·감시 상태였는지, 경찰 신고서를 받았는지 / 항공지연이라면 몇 시간
   지연됐는지, 확인서를 받았는지).
4. 질문은 한국어 한 문장, 존댓말, 사용자가 바로 답할 수 있게 구체적으로.
5. target_field는 아래 목록에 해당하는 질문이면 **그 이름을 그대로** 쓰세요:
{field_list}
   목록에 없는 질문이면 `ai_`로 시작하는 짧은 영문 snake_case 이름을 새로 지으세요
   (예: ai_police_report, ai_lock_state).
6. impact_weight는 0.0~1.0 사이로, 보상 판단에 미치는 영향이 클수록 높게 주세요.
7. 답을 지어내지 마세요. 당신은 질문만 만듭니다.
"""


class _QuestionItem(BaseModel):
    question_text: str
    target_field: str
    impact_weight: float


class _QuestionSchema(BaseModel):
    items: list[_QuestionItem]


def _known_summary(merged: dict, modifiers: dict | None) -> str:
    lines = []
    for name, field in (merged or {}).items():
        value = getattr(field, "value", None)
        if value is None or value == "":
            continue
        lines.append(f"- {name}: {value}")
    for name, value in (modifiers or {}).items():
        if value:
            lines.append(f"- {name}: {value}")
    return "\n".join(lines) if lines else "- (아직 없음)"


def _l2_candidates_text(db: Session, l1_code: str | None) -> str:
    """이 대분류 아래의 세부유형 후보를 프롬프트에 넣을 줄로 만든다.

    질문의 목적은 "무엇이 궁금한가"가 아니라 "약관을 어디까지 추려낼 수 있는가"다.
    조항 매핑은 세부유형 단위로 달려 있어서, 세부유형이 갈리면 걸리는 조항이 통째로
    바뀜다. 후보를 안 알려주면 모델은 사고 내용만 보고 조항을 하나도 못 가르는 질문을
    만든다(예: "언제 그랬나요")."""
    if not l1_code:
        return "   · (대분류가 정해지지 않아 후보를 알 수 없음)"
    root = db.query(IncidentType).filter_by(l1_code=l1_code, parent_id=None).first()
    if root is None:
        return "   · (후보 없음)"
    children = (
        db.query(IncidentType)
        .filter(IncidentType.parent_id == root.type_id, IncidentType.is_active.is_(True))
        .order_by(IncidentType.type_id)
        .all()
    )
    if not children:
        return "   · (후보 없음)"
    return "\n".join(f"   · {c.name}" for c in children)


def _normalize_field(raw: str, used: set[str]) -> str | None:
    """모델이 준 target_field를 실제로 쓸 수 있는 이름으로 정리한다.

    알려진 필드면 그대로 두고, 아니면 `ai_` 접두사 + snake_case로 강제한다. 답변 저장
    경로(routers/incidents.answer_question)가 필드 이름으로 분기하므로, 여기서 이상한
    이름이 새어 나가면 답변이 엉뚱한 컬럼에 들어간다."""
    name = (raw or "").strip()
    if name in KNOWN_TARGET_FIELDS:
        return None if name in used else name
    slug = re.sub(r"[^a-z0-9_]", "", name.lower().replace("-", "_").replace(" ", "_"))
    if not slug:
        return None
    if not slug.startswith("ai_"):
        slug = f"ai_{slug}"
    slug = slug[:48]
    return None if slug in used else slug


def generate_questions(
    db: Session,
    *,
    incident: Incident,
    l1_code: str | None,
    merged: dict,
    modifiers: dict | None = None,
    create: bool = True,
) -> list[QuestionBank] | None:
    """이 사고 한 건을 위한 추가 질문을 만들어 question_bank에 저장하고 돌려준다.

    같은 사고에 대해 이미 만들어 둔 질문이 있으면 새로 만들지 않고 그것을 그대로 준다 —
    답변할 때마다 분석이 다시 돌기 때문에(_run_analysis), 매번 새로 만들면 질문이
    끝없이 불어나고 답한 질문이 다른 문장으로 되살아난다.

    create=False면 이미 저장된 것만 읽고 Gemini를 부르지 않는다. 조회 전용 경로(분석
    결과 다시 보기)는 세션을 커밋하지 않아서, 거기서 질문을 새로 만들면 저장되지도
    않은 채 요청마다 API만 다시 쓴다.

    반환값 세 가지를 호출부가 서로 다르게 읽는다.
      · 리스트(비어 있지 않음) — 이 질문들을 쓴다.
      · 빈 리스트 — 이 사고는 더 물을 게 없다고 판정됐다. 공용 뱅크를 열지 않는다.
      · None — 생성이 안 됐거나 실패했다. 공용 뱅크로 되돌아간다."""
    incident_id = incident.incident_id
    free_text = incident.free_text
    existing = (
        db.query(QuestionBank)
        .filter(QuestionBank.incident_id == incident_id)
        .order_by(QuestionBank.impact_weight.desc())
        .all()
    )
    if existing:
        return existing

    if incident.questions_generated:
        # 생성은 이미 끝났는데 저장된 질문이 0건이다 = "더 물을 게 없다"는 판정이었다.
        # 이걸 None으로 돌려주면 재방문 때마다 공용 뱅크가 되살아나, 결과 화면까지 갔던
        # 사고가 질문 화면으로 되돌아간다.
        return []

    if not create or not config.GEMINI_ENABLED or not (free_text or "").strip():
        return None

    field_list = "\n".join(f"   · {name} — {desc}" for name, desc in KNOWN_TARGET_FIELDS.items())
    prompt = _PROMPT.format(
        free_text=free_text.strip(),
        l1_code=l1_code or "(분류 안 됨)",
        l2_candidates=_l2_candidates_text(db, l1_code),
        known=_known_summary(merged, modifiers),
        max_questions=MAX_GENERATED_QUESTIONS,
        field_list=field_list,
    )

    try:
        client = genai.Client(api_key=config.GEMINI_API_KEY)
        response = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=_QuestionSchema,
                temperature=0.3,
            ),
        )
        parsed: _QuestionSchema | None = response.parsed
        if parsed is None:
            parsed = _QuestionSchema.model_validate(json.loads(response.text))
    except Exception:
        logger.exception("Gemini 추가 질문 생성 실패 — 공용 질문 뱅크로 되돌림")
        return None

    if not parsed.items:
        # 모델이 "사고 내용만으로 충분하다"고 판단한 경우다. 실패가 아니므로 빈 목록을
        # 준다 — None으로 뭉개면 호출부가 공용 뱅크를 다시 열어서, 프롬프트가 시킨 것과
        # 정반대로 안 물어도 될 질문을 전부 도로 묻게 된다.
        incident.questions_generated = True
        return []

    used: set[str] = set()
    rows: list[QuestionBank] = []
    for item in parsed.items[:MAX_GENERATED_QUESTIONS]:
        text = (item.question_text or "").strip()
        if not text:
            continue
        field = _normalize_field(item.target_field, used)
        if field is None:
            continue
        used.add(field)
        weight = min(max(item.impact_weight, 0.0), 1.0)
        row = QuestionBank(
            context_type="사고후",
            question_text=text,
            target_field=field,
            impact_weight=weight,
            applies_to_l1=None,
            incident_id=incident_id,
        )
        db.add(row)
        rows.append(row)

    if not rows:
        # 만들려고는 했는데 하나도 쓸 수 없는 형태였다 — 이건 생성 실패다(위의 빈 목록과
        # 다르다). 공용 뱅크로 되돌아가는 쪽이 맞다.
        return None
    incident.questions_generated = True
    db.flush()
    rows.sort(key=lambda r: -(r.impact_weight or 0.0))
    return rows
