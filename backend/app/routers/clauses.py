from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app import config
from app.database import get_db
from app.limiter import limiter
from app.models.kb import Clause
from app.models.user import Incident
from app.schemas import HighlightSpanOut, ClauseOut
from app.services.clause_spans_gemini import get_highlight_spans, get_incident_relevance
from app.services.nlu import get_nlu_engine

router = APIRouter(prefix="/clauses", tags=["clauses"])


@router.get("/{clause_id}", response_model=ClauseOut)
def get_clause(clause_id: int, db: Session = Depends(get_db)):
    """사고 맥락 없이 조항 원문 자체만 필요할 때(예: 가입 전 추천 화면에서 근거 조항을 약관
    형광펜으로 열어보는 경우) 쓴다."""
    clause = db.get(Clause, clause_id)
    if not clause:
        raise HTTPException(status_code=404, detail="조항을 찾을 수 없습니다.")
    return ClauseOut(
        clause_id=clause.clause_id, article_no=clause.article_no, text=clause.text,
        page_ref=clause.page_ref, default_color=clause.default_color, highlight_color=clause.default_color,
    )


@router.get("/{clause_id}/spans", response_model=list[HighlightSpanOut] | None)
@limiter.limit("40/minute")
def get_clause_spans(request: Request, clause_id: int, db: Session = Depends(get_db)):
    """조항 하나의 인라인 색상 구간을 지금 보고 있는 조항에 대해서만 그때그때 분석한다.
    (findings/trip 생성 시 한꺼번에 다 분석하면 느려서, 사용자가 실제로 펼쳐본 조항만 처리)"""
    clause = db.get(Clause, clause_id)
    if not clause:
        raise HTTPException(status_code=404, detail="조항을 찾을 수 없습니다.")
    return get_highlight_spans(db, clause)


_CONTEXT_LABELS = {
    "country": "사고 발생 국가",
    "cause": "사고 원인",
    "injury_part": "다친 부위",
    "diagnosis": "진단명·증상",
}


def _incident_context(incident: Incident) -> dict:
    return {
        _CONTEXT_LABELS[f]: getattr(incident, f)
        for f in ("country", "cause", "injury_part", "diagnosis")
        if getattr(incident, f)
    }


@router.get("/{clause_id}/relevance")
@limiter.limit("40/minute")
def get_clause_relevance(request: Request, clause_id: int, incident_id: int, db: Session = Depends(get_db)):
    """이 조항에서 그 사고 상황과 직접 관련된 부분만 노란색으로 표시하기 위한 구간을 계산한다.
    다양한 색상 구분 없이, "이 사고와 관련 있는지"만 노랑 하나로 표시한다."""
    clause = db.get(Clause, clause_id)
    if not clause:
        raise HTTPException(status_code=404, detail="조항을 찾을 수 없습니다.")
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="사고 정보를 찾을 수 없습니다.")

    result = get_incident_relevance(clause.text, _incident_context(incident))
    if result is None:
        return {"segments": [{"text": clause.text, "highlighted": False}], "relevant_chars": 0, "supported": False}
    segments, relevant_chars = result
    return {"segments": segments, "relevant_chars": relevant_chars, "supported": True}


@router.get("/{clause_id}/plain")
@limiter.limit("40/minute")
def get_clause_plain_text(request: Request, clause_id: int, incident_id: int | None = None, db: Session = Depends(get_db)):
    """약관 원문을 쉬운 말로 풀어 설명한다(원문을 대체하지 않고 병기용).
    incident_id가 있으면 그 사고 상황에 맞춰 그때그때 설명하고(캐시하지 않음),
    없으면 일반 설명을 DB에 캐시해 재사용한다."""
    clause = db.get(Clause, clause_id)
    if not clause:
        raise HTTPException(status_code=404, detail="조항을 찾을 수 없습니다.")

    if incident_id is not None:
        if not config.GEMINI_ENABLED:
            return {"plain_text": None, "supported": False}
        incident = db.get(Incident, incident_id)
        if not incident:
            raise HTTPException(status_code=404, detail="사고 정보를 찾을 수 없습니다.")
        context = _incident_context(incident)
        explained = get_nlu_engine().explain_clause_plain(clause.text, context or None)
        if explained and explained.strip() and explained.strip() != clause.text.strip():
            return {"plain_text": explained.strip(), "supported": True}
        return {"plain_text": None, "supported": False}

    if clause.plain_text:
        return {"plain_text": clause.plain_text, "supported": True}
    if not config.GEMINI_ENABLED:
        return {"plain_text": None, "supported": False}

    explained = get_nlu_engine().explain_clause_plain(clause.text)
    if explained and explained.strip() and explained.strip() != clause.text.strip():
        clause.plain_text = explained.strip()
        db.commit()
        return {"plain_text": clause.plain_text, "supported": True}
    return {"plain_text": None, "supported": False}
