"""사고 상황을 Gemini 프롬프트용 dict로 만드는 공통 헬퍼.

조항 형광펜/쉬운말 설명(routers/clauses.py)과 findings 설명(claim_review.py)이 둘 다
"이 사고 상황에 맞춰 설명"이 필요해서 컨텍스트 조립 로직이 겹친다 — 여기 하나로 모은다.
"""
import json

from sqlalchemy.orm import Session

from app.models.kb import IncidentType
from app.models.user import Incident

_FIELD_LABELS = {
    "country": "사고 발생 국가",
    "cause": "사고 원인",
    "injury_part": "다친 부위",
    "diagnosis": "진단명·증상",
}

# incident.modifiers(JSON) 축 이름 → 사람이 읽을 라벨. incident_classify_gemini._ModifiersSchema와 짝을 맞춘다.
_MODIFIER_LABELS = {
    "activity": "사고 당시 활동",
    "location": "장소",
    "timing": "시점",
    "status": "상태",
    "target": "피해 대상",
}


def build_incident_context(db: Session, incident: Incident) -> dict:
    """조항 형광펜·쉬운말 설명, findings 설명에 넘기는 사고 맥락. 분류된 사고유형(L1/L2)과
    수식자(modifiers)를 포함시켜, "이 조항/서류가 이 사고와 어떻게 관련되는지"를 Gemini가
    더 정확히 짚게 한다."""
    context = {
        _FIELD_LABELS[f]: getattr(incident, f)
        for f in ("country", "cause", "injury_part", "diagnosis")
        if getattr(incident, f)
    }
    if incident.type_id:
        type_row = db.get(IncidentType, incident.type_id)
        if type_row:
            context["분류된 사고유형"] = type_row.name
    if incident.modifiers:
        try:
            modifiers = json.loads(incident.modifiers)
        except (TypeError, ValueError):
            modifiers = {}
        for key, value in modifiers.items():
            if value:
                context[_MODIFIER_LABELS.get(key, key)] = value
    return context
