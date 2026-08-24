"""현지 대응 팩 — 해외 현지에 서 있는 사람에게 필요한 것만 한 번에 모은다.

이 서비스가 없던 자리에 있던 공백: 생애주기가 "여행 전 → 사고 접수 → 청구 준비 →
부지급 후"로 이어지는데, 정작 청구 결과가 결정되는 **현지에서의 몇 시간**이 비어 있었다.
해외에서 부지급이 나는 흔한 이유는 담보가 없어서가 아니라, 약관이 요구하는 형식
(예: "국외의 의료관련법에서 정한 의료기관에서 발급한 것")을 모른 채 영수증만 받아오기
때문이다. 귀국하면 그 서류는 영영 못 받는다.

판단에 쓰는 데이터는 전부 이미 있던 것이다 — RequiredDocStd.acquire_location('현지only'
14종 중 9종), CoverageDocMap, DocRequirement(근거 조항이 물려 있음). 새 판정 로직을
만들지 않는다.

**응답은 한 번에 전부 내려보낸다.** 오프라인 캐시에 담기는 단위가 요청 하나여야
비행기모드에서 화면이 온전히 뜬다. 서류 14종·요건 7건 규모라 8개 L1을 다 담아도 작다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.models.kb import (
    Clause, Coverage, CoverageDocMap, ClauseIncidentMap, DocRequirement, IncidentType,
    Insurer, OnsitePhraseI18n, PolicyVersion, Product, RequiredDocStd,
)
from app.models.user import Evidence, Incident, Trip, UserPolicy
from app.services.clause_quote import quote_clause
from app.services.onsite_i18n import resolve_language, translate

LOCAL_ONLY = "현지only"


@dataclass
class OnsiteRequirement:
    """약관이 요구하는 형식 하나. 근거 조항 인용은 언제나 한국어 원문이다."""
    label_ko: str
    label_local: str | None
    clause_id: int | None
    clause_article_no: str | None
    clause_quote: str | None
    insurer_name: str | None


@dataclass
class OnsiteDoc:
    required_doc_std_id: int
    doc_code: str
    doc_name_ko: str
    doc_name_local: str | None
    acquire_location: str | None
    note: str | None
    status: str | None                       # 연결된 사고가 있을 때만
    requirements: list[OnsiteRequirement] = field(default_factory=list)

    @property
    def local_only(self) -> bool:
        return self.acquire_location == LOCAL_ONLY


@dataclass
class OnsitePack:
    country: str | None
    lang_code: str
    lang_name_ko: str
    intro_ko: str
    intro_local: str | None
    trip_id: int | None
    start_date: date | None
    end_date: date | None
    insurer_names: list[str]
    incident_types: list[dict]
    docs_by_type: dict[int, list[OnsiteDoc]]
    progress_total: int | None
    progress_secured: int | None
    generated_at: datetime


def _policy_version_ids(db: Session, user_policy: UserPolicy | None) -> list[int] | None:
    """대상 보험사 범위. None이면 전 보험사를 뜻한다.

    등록한 보험이 있으면 그 보험사 하나로 좁힌다 — 실제로 가입한 약관의 요건만 보여주는
    쪽이 정확하다. 없으면 전 보험사 합집합을 보여주되, 요건마다 어느 보험사 조항인지 밝힌다
    (근거의 출처를 뭉뚱그리지 않는다).
    """
    if user_policy and user_policy.policy_version_id:
        return [user_policy.policy_version_id]
    return None


def _l1_types(db: Session) -> list[IncidentType]:
    return (
        db.query(IncidentType)
        .filter(IncidentType.parent_id.is_(None), IncidentType.is_active.is_(True))
        .order_by(IncidentType.type_id)
        .all()
    )


def _type_ids_for_l1(db: Session, l1: IncidentType) -> list[int]:
    children = db.query(IncidentType.type_id).filter(IncidentType.parent_id == l1.type_id).all()
    return [l1.type_id] + [c[0] for c in children]


def _coverage_ids_for_types(
    db: Session, type_ids: list[int], policy_version_ids: list[int] | None,
) -> list[int]:
    query = (
        db.query(Coverage.coverage_id)
        .join(Clause, Clause.coverage_id == Coverage.coverage_id)
        .join(ClauseIncidentMap, ClauseIncidentMap.clause_id == Clause.clause_id)
        .filter(ClauseIncidentMap.type_id.in_(type_ids))
    )
    if policy_version_ids is not None:
        query = query.filter(Coverage.policy_version_id.in_(policy_version_ids))
    return [row[0] for row in query.distinct().all()]


def _requirements_by_doc(
    db: Session, policy_version_ids: list[int] | None,
) -> dict[int, list[tuple[DocRequirement, Clause, str | None]]]:
    """서류별 약관 요건 + 그 요건의 근거 조항·보험사.

    요건 전체가 7건 규모라 한 번에 다 읽어도 된다.
    """
    query = (
        db.query(DocRequirement, Clause, Insurer.name)
        .join(Clause, Clause.clause_id == DocRequirement.clause_id)
        .join(Coverage, Coverage.coverage_id == Clause.coverage_id)
        .join(PolicyVersion, PolicyVersion.policy_version_id == Coverage.policy_version_id)
        .join(Product, Product.product_id == PolicyVersion.product_id)
        .join(Insurer, Insurer.insurer_id == Product.insurer_id)
    )
    if policy_version_ids is not None:
        query = query.filter(Coverage.policy_version_id.in_(policy_version_ids))

    result: dict[int, list[tuple[DocRequirement, Clause, str | None]]] = {}
    for req, clause, insurer_name in query.all():
        result.setdefault(req.required_doc_std_id, []).append((req, clause, insurer_name))
    return result


def _linked_incident(db: Session, trip: Trip | None) -> Incident | None:
    if trip is None:
        return None
    return (
        db.query(Incident)
        .filter(Incident.trip_id == trip.trip_id)
        .order_by(Incident.incident_id.desc())
        .first()
    )


def build_onsite_pack(
    db: Session,
    *,
    country: str | None,
    trip: Trip | None = None,
) -> OnsitePack:
    """현지 대응 팩을 조립한다. 저장하지 않고 조회할 때마다 계산한다 —
    약관 DB가 갱신되면 결과도 자동으로 따라온다(coverage_overlap과 같은 이유)."""
    destination = (trip.destination if trip and trip.destination else country) or None
    lang, lang_name = resolve_language(db, destination)

    user_policy = db.get(UserPolicy, trip.user_policy_id) if trip and trip.user_policy_id else None
    pv_ids = _policy_version_ids(db, user_policy)

    insurer_names: list[str] = []
    if pv_ids is not None:
        rows = (
            db.query(Insurer.name)
            .join(Product, Product.insurer_id == Insurer.insurer_id)
            .join(PolicyVersion, PolicyVersion.product_id == Product.product_id)
            .filter(PolicyVersion.policy_version_id.in_(pv_ids))
            .distinct().all()
        )
        insurer_names = [r[0] for r in rows]
    else:
        insurer_names = [r[0] for r in db.query(Insurer.name).order_by(Insurer.code).all()]

    incident = _linked_incident(db, trip)
    evidence_by_doc: dict[int, Evidence] = {}
    if incident is not None:
        evidence_by_doc = {
            e.required_doc_std_id: e
            for e in db.query(Evidence).filter(Evidence.incident_id == incident.incident_id).all()
            if e.required_doc_std_id is not None
        }

    reqs_by_doc = _requirements_by_doc(db, pv_ids)
    docs_cache: dict[int, RequiredDocStd] = {
        d.required_doc_std_id: d for d in db.query(RequiredDocStd).all()
    }

    l1_types = _l1_types(db)
    docs_by_type: dict[int, list[OnsiteDoc]] = {}
    for l1 in l1_types:
        type_ids = _type_ids_for_l1(db, l1)
        coverage_ids = _coverage_ids_for_types(db, type_ids, pv_ids)
        if not coverage_ids:
            docs_by_type[l1.type_id] = []
            continue
        doc_ids: dict[int, bool] = {}
        for dm in db.query(CoverageDocMap).filter(CoverageDocMap.coverage_id.in_(coverage_ids)).all():
            # 한 서류가 여러 담보에 걸리면 필수 여부는 하나라도 필수면 필수로 본다.
            doc_ids[dm.required_doc_std_id] = doc_ids.get(dm.required_doc_std_id, False) or bool(dm.is_mandatory)

        items: list[OnsiteDoc] = []
        for doc_id in doc_ids:
            doc = docs_cache.get(doc_id)
            if doc is None:
                continue
            ev = evidence_by_doc.get(doc_id)
            items.append(OnsiteDoc(
                required_doc_std_id=doc.required_doc_std_id,
                doc_code=doc.doc_code,
                doc_name_ko=doc.doc_name,
                doc_name_local=None,     # 아래에서 한꺼번에 채운다
                acquire_location=doc.acquire_location,
                note=doc.note,
                status=(ev.status if ev else "미확인") if incident is not None else None,
                requirements=[
                    OnsiteRequirement(
                        label_ko=req.label,
                        label_local=None,
                        clause_id=clause.clause_id,
                        clause_article_no=clause.article_no,
                        clause_quote=quote_clause(clause, req.anchor_phrase),
                        insurer_name=insurer_name,
                    )
                    for req, clause, insurer_name in reqs_by_doc.get(doc_id, [])
                ],
            ))
        # 귀국하면 못 받는 것부터 위로. 그 안에서는 서류 표준코드가 시드된 순서를 따른다 —
        # 청구서·진료비 영수증처럼 흔한 것이 앞, 사망진단서처럼 드문 것이 뒤로 간다.
        items.sort(key=lambda d: (not d.local_only, d.required_doc_std_id))
        docs_by_type[l1.type_id] = items

    _fill_local_text(db, lang, lang_name, docs_by_type)

    intro_ko, intro_local = _intro(db, lang, lang_name)
    total, secured = _progress(db, incident, docs_by_type)

    return OnsitePack(
        country=destination,
        lang_code=lang,
        lang_name_ko=lang_name,
        intro_ko=intro_ko,
        intro_local=intro_local,
        trip_id=trip.trip_id if trip else None,
        start_date=trip.start_date if trip else None,
        end_date=trip.end_date if trip else None,
        insurer_names=insurer_names,
        incident_types=[
            {"type_id": t.type_id, "l1_code": t.l1_code, "name": t.name} for t in l1_types
        ],
        docs_by_type=docs_by_type,
        progress_total=total,
        progress_secured=secured,
        generated_at=datetime.now(),
    )


def _fill_local_text(
    db: Session, lang: str, lang_name: str, docs_by_type: dict[int, list[OnsiteDoc]],
) -> None:
    """서류명·요건 문구의 현지어를 한꺼번에 채운다. 번역을 못 구한 항목은 None으로 남고,
    화면은 그 자리에 한국어만 보여준다 — 번역된 척하지 않는다."""
    wanted: dict[tuple[str, int], str] = {}
    for items in docs_by_type.values():
        for doc in items:
            wanted[(OnsitePhraseI18n.KIND_DOC_NAME, doc.required_doc_std_id)] = doc.doc_name_ko

    # 요건은 DocRequirement.requirement_id 단위로 캐시된다(시드가 그렇게 넣는다).
    # 같은 label을 쓰는 요건이 여러 건이라(현재 7건 중 6건이 같은 label) 아래에서
    # label 기준으로 한 번만 골라 쓴다.
    req_ids: dict[tuple[str, int], str] = {}
    label_to_ids: dict[str, list[int]] = {}
    for req_row in db.query(DocRequirement).all():
        label_to_ids.setdefault(req_row.label, []).append(req_row.requirement_id)
        req_ids[(OnsitePhraseI18n.KIND_REQUIREMENT, req_row.requirement_id)] = req_row.label

    items_to_translate = [(k[0], k[1], v) for k, v in {**wanted, **req_ids}.items()]
    if not items_to_translate:
        return
    translated = translate(db, lang, lang_name, items_to_translate)

    # label -> 현지어 (같은 label을 쓰는 요건 중 하나라도 번역이 있으면 그걸 쓴다)
    label_local: dict[str, str] = {}
    for label, ids in label_to_ids.items():
        for rid in ids:
            text = translated.get((OnsitePhraseI18n.KIND_REQUIREMENT, rid))
            if text:
                label_local[label] = text
                break

    for items in docs_by_type.values():
        for doc in items:
            doc.doc_name_local = translated.get(
                (OnsitePhraseI18n.KIND_DOC_NAME, doc.required_doc_std_id)
            )
            for req in doc.requirements:
                req.label_local = label_local.get(req.label_ko)


def _intro(db: Session, lang: str, lang_name: str) -> tuple[str, str | None]:
    from app.seed_onsite_phrases import INTRO_KO

    translated = translate(db, lang, lang_name, [(OnsitePhraseI18n.KIND_INTRO, 0, INTRO_KO)])
    return INTRO_KO, translated.get((OnsitePhraseI18n.KIND_INTRO, 0))


def _progress(
    db: Session, incident: Incident | None, docs_by_type: dict[int, list[OnsiteDoc]],
) -> tuple[int | None, int | None]:
    """연결된 사고가 있을 때만 진행률을 낸다. 사고가 없으면 0/N으로 지어내지 않고 None.

    세는 대상은 그 사고 유형의 **현지only** 서류다 — 이 화면이 막으려는 실패가
    "귀국해서야 못 받는 걸 알게 되는 것"이기 때문이다.
    """
    if incident is None or incident.type_id is None:
        return None, None

    # 사고는 L2까지 확정돼 있을 수 있는데 docs_by_type의 키는 L1이다. 부모를 타고 올라간다.
    incident_type = db.get(IncidentType, incident.type_id)
    if incident_type is None:
        return None, None
    l1_id = incident_type.parent_id or incident_type.type_id

    local_only = [d for d in docs_by_type.get(l1_id, []) if d.local_only]
    if not local_only:
        return None, None
    secured = sum(1 for d in local_only if d.status == "보유")
    return len(local_only), secured
