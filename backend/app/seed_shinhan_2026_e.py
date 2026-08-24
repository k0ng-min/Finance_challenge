"""
신한EZ손해보험(insurer.code="SHINHAN") - 청크 e: 매핑 (조항↔사고유형, 담보↔청구서류)

## 왜 따로 있나
6개사 분량은 `app.seed_clause_incident_map`과 `app.seed_coverage_doc_map`이 한 번에
만들었다. 그 두 스크립트는 첫머리에서 "이미 시드됨이면 스킵"으로 막혀 있어서(전체를
다시 만들면 기존 매핑의 map_id가 바뀐다), 나중에 들어온 보험사는 같은 규칙을 그대로
빌려 쓰되 **자기 보험사분만** 채우는 스크립트가 필요하다. 이 파일이 그 역할이다.

규칙 자체는 새로 쓰지 않고 원본 모듈에서 그대로 import한다 — 규칙이 두 벌이 되면
"같은 담보면 보험사가 달라도 같은 사고유형에 걸린다"는 이 프로젝트의 전제가 조용히
깨진다. 신한 때문에 새로 필요해진 규칙(GOLF_EQUIPMENT)은 이 파일이 아니라 원본
모듈의 규칙표에 넣었다.

## 원본 규칙으로 안 되는 부분 (EXTRA_RULES)
규칙은 (담보표준코드, clause_type) 조합으로 매핑한다. 그런데 신한 약관에는 조문 하나가
담보 둘을 한꺼번에 담은 자리가 두 군데 있다. 담보표준코드는 하나뿐이라 규칙만으로는
나머지 절반이 빠진다. 그 자리를 여기서 조항 단위로 보충한다.

1. [기본형 해외여행 실손의료비 특별약관] 제1·3·4·5조
   보장종목이 상해의료비형과 질병의료비형 둘인데, 제3조(보장종목별 보상내용)와
   제4조(보상하지 않는 사항)가 두 종목을 한 조문에 표로 담고 있다(청크 c 참고 - 표
   레이아웃 때문에 조문을 종목별로 쪼개면 원문 대조가 깨져서 통째로 넣었다).
   조항은 OVS_INJ_MED 담보에 붙어 있어 규칙은 INJ_OVERSEAS_TREATMENT만 걸어 준다.
   -> 질병 쪽(ILL_OVERSEAS_TREATMENT, ILL_DOMESTIC_TREATMENT)과 국내 급여 상해
      (INJ_DOMESTIC_TREATMENT)를 여기서 더한다. 이걸 빼면 "해외에서 병이 났다"로
      들어온 사고에서 실손 조항이 하나도 안 잡힌다.

2. [항공기 및 수하물 지연비용 특별약관] 제1~5조
   제1조가 "항공기 지연/결항"과 "위탁수하물 지연/손실"을 한 표에 담고 있다. 담보는
   TRV_BAGGAGE_DELAY 하나로 두었으므로(청크 b 참고) 규칙은 수하물 쪽만 걸어 준다.
   -> 항공지연·결항(TRV_FLIGHT_DELAY)과 수하물분실(TRV_BAGGAGE_LOSS)을 여기서 더한다.
      원문 제1조에 "항공편이 4시간 이상 출발이 지연, 취소"와 "수화물이 손실되거나 ...
      영구적으로 손실된 것으로 간주됩니다"가 지급사유로 직접 적혀 있다.

## 만드는 행
- clause_incident_map: 신한 조항 중 clause_type='서류'가 아니고 계약행정 담보가 아닌 것
- coverage_doc_map: 신한 담보 중 계약행정 담보가 아닌 것

## 안 만드는 것
- clause_term(수치조건): 6개사도 재구축 1차분에서 만들지 않은 보험사가 있다(DB/HYUNDAI는
  일부만). 조항 원문에서 금액·일수·시간을 뽑아 raw_text로 앵커링하는 별도 작업이라
  여기서는 정직하게 미룬다. ClauseTerm.raw_text는 반드시 clause.text의 부분 문자열이어야
  하므로 짐작으로 채우면 안 된다.

Run from ``backend``::

    python -m app.seed_shinhan_2026_e
"""
from app.database import SessionLocal
from app import models  # noqa: F401
from app.models.kb import (
    Clause, ClauseIncidentMap, Coverage, CoverageDocMap, CoverageStd,
    IncidentType, Insurer, PolicyVersion, Product, RequiredDocStd,
)
from app.seed_clause_incident_map import (
    ADMIN_STD_CODES, BASE_RULES, EVIDENCE_RULES, MAPPED_BY, SKIP_CLAUSE_TYPES,
)
from app.seed_coverage_doc_map import ADMIN_STD_CODES as DOC_ADMIN_STD_CODES, DOC_RULES

INSURER_CODE = "SHINHAN"

#: (Coverage.raw_name, clause_type) -> [(l2_code, relevance)]
#: 조문 하나가 담보 둘을 담고 있어 규칙만으로는 절반이 빠지는 자리를 보충한다.
EXTRA_RULES: dict[tuple[str, str], list[tuple[str, str]]] = {
    ("기본형 해외여행 실손의료비 특별약관 - 상해의료비", "보장정의"): [
        ("ILL_OVERSEAS_TREATMENT", "직접"),
        ("ILL_DOMESTIC_TREATMENT", "직접"),
        ("INJ_DOMESTIC_TREATMENT", "직접"),
    ],
    ("기본형 해외여행 실손의료비 특별약관 - 상해의료비", "면책"): [
        ("ILL_OVERSEAS_TREATMENT", "면책"),
        ("ILL_DOMESTIC_TREATMENT", "면책"),
        ("INJ_DOMESTIC_TREATMENT", "면책"),
    ],
    ("기본형 해외여행 실손의료비 특별약관 - 상해의료비", "제한"): [
        ("ILL_OVERSEAS_TREATMENT", "조건부"),
        ("ILL_DOMESTIC_TREATMENT", "조건부"),
        ("INJ_DOMESTIC_TREATMENT", "조건부"),
    ],
    ("기본형 해외여행 실손의료비 특별약관 - 상해의료비", "조건"): [
        ("ILL_OVERSEAS_TREATMENT", "조건부"),
        ("ILL_DOMESTIC_TREATMENT", "조건부"),
        ("INJ_DOMESTIC_TREATMENT", "조건부"),
    ],
    ("항공기 및 수하물 지연비용 특별약관", "보장정의"): [
        ("TRV_FLIGHT_DELAY", "직접"),
        ("TRV_BAGGAGE_LOSS", "직접"),
    ],
    ("항공기 및 수하물 지연비용 특별약관", "면책"): [
        ("TRV_FLIGHT_DELAY", "면책"),
        ("TRV_BAGGAGE_LOSS", "면책"),
    ],
    ("항공기 및 수하물 지연비용 특별약관", "제한"): [
        ("TRV_FLIGHT_DELAY", "조건부"),
        ("TRV_BAGGAGE_LOSS", "조건부"),
    ],
    ("항공기 및 수하물 지연비용 특별약관", "조건"): [
        ("TRV_FLIGHT_DELAY", "조건부"),
        ("TRV_BAGGAGE_LOSS", "조건부"),
    ],
}


def _policy_version(db) -> PolicyVersion:
    pv = (
        db.query(PolicyVersion)
        .join(Product, Product.product_id == PolicyVersion.product_id)
        .join(Insurer, Insurer.insurer_id == Product.insurer_id)
        .filter(Insurer.code == INSURER_CODE)
        .first()
    )
    if pv is None:
        raise SystemExit("신한 약관버전이 없습니다. app.seed_shinhan_2026_a부터 실행하세요.")
    return pv


def _map_incidents(db, pv: PolicyVersion) -> tuple[int, list[str]]:
    types = {t.l2_code: t for t in db.query(IncidentType).all()}
    rows = (
        db.query(Clause, CoverageStd.std_code, Coverage.raw_name)
        .outerjoin(Coverage, Coverage.coverage_id == Clause.coverage_id)
        .outerjoin(CoverageStd, CoverageStd.coverage_std_id == Coverage.coverage_std_id)
        .filter(Clause.policy_version_id == pv.policy_version_id)
        .order_by(Clause.clause_id)
        .all()
    )
    existing = {
        (m.clause_id, m.type_id, m.relevance)
        for m in db.query(ClauseIncidentMap)
        .join(Clause, Clause.clause_id == ClauseIncidentMap.clause_id)
        .filter(Clause.policy_version_id == pv.policy_version_id)
        .all()
    }

    created = 0
    unmapped: list[str] = []

    def add(clause_id: int, l2_code: str, relevance: str) -> bool:
        itype = types.get(l2_code)
        if itype is None:
            return False
        key = (clause_id, itype.type_id, relevance)
        if key in existing:
            return False
        existing.add(key)
        db.add(ClauseIncidentMap(
            clause_id=clause_id, type_id=itype.type_id,
            relevance=relevance, mapped_by=MAPPED_BY, confidence=None,
        ))
        return True

    for clause, std_code, raw_name in rows:
        if clause.clause_type in SKIP_CLAUSE_TYPES:
            continue
        hit = False
        if std_code not in ADMIN_STD_CODES:
            for l2_code, relevance in BASE_RULES.get((std_code, clause.clause_type), []):
                if add(clause.clause_id, l2_code, relevance):
                    created += 1
                hit = True
            for l2_code, relevance in EXTRA_RULES.get((raw_name, clause.clause_type), []):
                if add(clause.clause_id, l2_code, relevance):
                    created += 1
                hit = True
        for phrase, l2_code, relevance in EVIDENCE_RULES:
            if phrase in (clause.text or "") and add(clause.clause_id, l2_code, relevance):
                created += 1
                hit = True
        if not hit and std_code not in ADMIN_STD_CODES:
            reason = "담보에 연결되지 않은 조항" if std_code is None else \
                f"매핑 규칙 없음 (std={std_code}, type={clause.clause_type})"
            unmapped.append(f"clause_id={clause.clause_id} {clause.article_no}: {reason}")
    return created, unmapped


def _map_docs(db, pv: PolicyVersion) -> tuple[int, list[str]]:
    docs = {d.doc_code: d for d in db.query(RequiredDocStd).all()}
    rows = (
        db.query(Coverage, CoverageStd.std_code)
        .outerjoin(CoverageStd, CoverageStd.coverage_std_id == Coverage.coverage_std_id)
        .filter(Coverage.policy_version_id == pv.policy_version_id)
        .all()
    )
    existing = {
        (m.coverage_id, m.required_doc_std_id)
        for m in db.query(CoverageDocMap)
        .join(Coverage, Coverage.coverage_id == CoverageDocMap.coverage_id)
        .filter(Coverage.policy_version_id == pv.policy_version_id)
        .all()
    }
    created = 0
    no_docs: list[str] = []
    for coverage, std_code in rows:
        if std_code in DOC_ADMIN_STD_CODES:
            continue
        targets = DOC_RULES.get(std_code)
        if targets is None:
            no_docs.append(f"{coverage.raw_name} (std={std_code})")
            continue
        for doc_code, is_mandatory in targets:
            doc = docs.get(doc_code)
            if doc is None:
                continue
            key = (coverage.coverage_id, doc.required_doc_std_id)
            if key in existing:
                continue
            existing.add(key)
            db.add(CoverageDocMap(
                coverage_id=coverage.coverage_id,
                required_doc_std_id=doc.required_doc_std_id,
                is_mandatory=is_mandatory,
            ))
            created += 1
    return created, no_docs


def run():
    db = SessionLocal()
    try:
        pv = _policy_version(db)

        made, unmapped = _map_incidents(db, pv)
        docs_made, no_docs = _map_docs(db, pv)
        db.commit()

        print(f"clause_incident_map: {made}건 생성")
        if unmapped:
            print(f"  매핑 없음 {len(unmapped)}건")
            for line in unmapped[:20]:
                print(f"    - {line}")
        print(f"coverage_doc_map: {docs_made}건 생성")
        if no_docs:
            print(f"  서류 규칙 없음 {len(no_docs)}건: {no_docs}")
    finally:
        db.close()


if __name__ == "__main__":
    run()
