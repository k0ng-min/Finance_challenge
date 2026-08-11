from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app import config
from app.database import get_db
from app.limiter import limiter
from app.models.kb import Clause, ClauseIncidentMap, Insurer, PolicyVersion, Product
from app.models.user import Incident
from app.schemas import ClauseIncidentLinkOut, ClauseSearchResultOut, HighlightSpanOut, ClauseOut, ClauseTermOut
from app.services.clause_spans_gemini import get_highlight_spans, get_incident_relevance
from app.services.incident_context import build_incident_context
from app.services.nlu import get_nlu_engine

router = APIRouter(prefix="/clauses", tags=["clauses"])


@router.get("/search", response_model=list[ClauseSearchResultOut])
@limiter.limit("30/minute")
def search_clauses(request: Request, insurer_code: str, keyword: str, db: Session = Depends(get_db)):
    """부지급(면책) 통지서에 보험사가 적어 둔 조항 번호나 문구로 그 보험사 약관에서
    조항을 찾는다. 조항 원문과, 어떤 사고유형에 직접/조건부/면책 중 무엇으로 매핑돼
    있는지까지만 보여준다 — 법률 자문이 아니며 실제 이번 사고에 적용되는지는 상황마다
    다르므로 화면에서 "확실하지 않으면 보험사에 직접 묻거나 금융감독원 분쟁조정을
    신청하라"고 안내한다(프론트엔드 문구로 고정)."""
    keyword = keyword.strip()
    if len(keyword) < 2:
        raise HTTPException(status_code=400, detail="검색어를 2자 이상 입력하세요.")

    insurer = db.query(Insurer).filter(Insurer.code == insurer_code.upper()).first()
    if not insurer:
        raise HTTPException(status_code=404, detail="보험사를 찾을 수 없습니다.")

    product = db.query(Product).filter(Product.insurer_id == insurer.insurer_id).first()
    if not product:
        return []
    policy_version = (
        db.query(PolicyVersion)
        .filter(PolicyVersion.product_id == product.product_id)
        .order_by(PolicyVersion.effective_date.desc().nullslast())
        .first()
    )
    if not policy_version:
        return []

    clauses = (
        db.query(Clause)
        .filter(
            Clause.policy_version_id == policy_version.policy_version_id,
            or_(Clause.article_no.like(f"%{keyword}%"), Clause.text.like(f"%{keyword}%")),
        )
        .order_by(Clause.clause_id)
        .limit(20)
        .all()
    )

    results: list[ClauseSearchResultOut] = []
    for c in clauses:
        maps = db.query(ClauseIncidentMap).filter(ClauseIncidentMap.clause_id == c.clause_id).all()
        links = [
            ClauseIncidentLinkOut(type_name=m.incident_type.name, relevance=m.relevance)
            for m in maps
        ]
        results.append(ClauseSearchResultOut(
            clause=ClauseOut(
                clause_id=c.clause_id, article_no=c.article_no, text=c.text,
                page_ref=c.page_ref, default_color=c.default_color, highlight_color=c.default_color,
                terms=[ClauseTermOut.model_validate(t) for t in c.terms],
            ),
            incident_links=links,
        ))
    return results


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
        terms=[ClauseTermOut.model_validate(t) for t in clause.terms],
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

    result = get_incident_relevance(clause.text, build_incident_context(db, incident))
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
        context = build_incident_context(db, incident)
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
