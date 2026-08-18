"""
2026년 재구축 KB의 조항(clause) → 정량 조건(ClauseTerm) 추출.

term_type 고정 어휘(과거 시드와 동일하게 유지): 지급한도/자기부담금/면책일수/
보상일수한도/지연기준시간/1일당지급액.

정규식으로 조항 원문에서 숫자·기한·금액 패턴을 찾고, 찾은 발췌(raw_text)가 실제로
그 조항 원문의 부분 문자열인지 raw_text_is_grounded()로 검증한 뒤에만 행을 만든다
(그렇지 않은 조각은 조용히 버린다 — 근거 없는 결과 금지 원칙).

정규식은 재현율(있는 걸 다 찾기)보다 정밀도(찾은 건 확실히 맞기)를 우선한다. 놓치는
숫자 조건이 있을 수 있으나, 잘못된 term_type으로 잘못 분류하는 것보다 낫다.
"""
import re

from app.database import SessionLocal
from app import models  # noqa: F401
from app.models.kb import Clause, ClauseTerm
from app.services.kb_seed_common import raw_text_is_grounded

# (정규식, term_type, unit, basis)
# unit/basis가 None이면 매치 내용에서 판단한다.
PATTERNS: list[tuple[str, str, str | None, str | None]] = [
    # 지급한도 — 금액 + "한도"/"이내"/"까지" 근처
    (r"US\s*\$\s*[\d,]+(?:\.\d+)?\s*(?:까지|한도|이내)?", "지급한도", "USD", None),
    (r"[\d,]+\s*만\s*원\s*(?:이내|한도|까지)", "지급한도", "원", None),
    (r"[\d,]+\s*천\s*만\s*원\s*(?:이내|한도|까지)", "지급한도", "원", None),
    (r"[\d,]+\s*억\s*원\s*(?:이내|한도|까지)", "지급한도", "원", None),
    (r"보험가입금액을?\s*한도로", "지급한도", None, None),
    (r"보험가입금액\s*전액", "지급한도", None, None),

    # 자기부담금 — "자기부담금"/"공제"라는 단어와 금액이 함께 나오는 경우
    (r"자기부담금\s*[\d,]*\s*(?:만\s*원|원|USD|US\s*\$\s*[\d,]+)?", "자기부담금", None, None),
    (r"[\d,]+\s*(?:만\s*원|원|US\s*\$\s*[\d,]+(?:\.\d+)?)\s*(?:을|를)?\s*공제", "자기부담금", None, None),
    (r"1회당\s*[\d,]+\s*(?:만\s*원|원)\s*(?:을|를)?\s*(?:공제|자기부담)", "자기부담금", "원", None),

    # 면책일수 — "N일 이상 입원/통원"해야 지급되는 최소 조건
    (r"\d+\s*일\s*이상\s*(?:계속\s*)?(?:입원|통원)", "면책일수", "일", None),
    (r"\d+\s*일\s*이상\s*(?:의\s*)?(?:장해|후유장해)", "면책일수", "일", None),

    # 보상일수한도 — 최대 며칠까지 보상하는지
    (r"\d+\s*일\s*(?:까지|한도|이내에)(?!\s*입원)", "보상일수한도", "일", None),
    (r"\d+\s*일분?을?\s*한도로", "보상일수한도", "일", None),
    (r"연간\s*\d+\s*일", "보상일수한도", "일", None),
    (r"\d+\s*박\s*\d+\s*일", "보상일수한도", "일", None),

    # 지연기준시간 — 항공기/수하물 지연 인정 최소 시간
    (r"\d+\s*시간\s*이상\s*(?:지연|결항)", "지연기준시간", "시간", None),
    (r"\d+\s*시간\s*이상(?!\s*(?:지연|결항))", "지연기준시간", "시간", None),

    # 1일당지급액 — 입원일당 등 정액 담보의 일 단위 지급액
    (r"1일\s*당\s*[\d,]+\s*(?:만\s*원|원|US\s*\$\s*[\d,]+(?:\.\d+)?)", "1일당지급액", None, None),
    (r"입원\s*1일당\s*[\d,]+", "1일당지급액", None, None),
]

_NUM_RE = re.compile(r"[\d][\d,]*(?:\.\d+)?")


def _extract_value(raw: str) -> float | None:
    m = _NUM_RE.search(raw)
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except ValueError:
        return None


def _guess_unit(raw: str, given: str | None) -> str | None:
    if given:
        return given
    if "US$" in raw or "US $" in raw.replace(" ", "") or "USD" in raw:
        return "USD"
    if "억" in raw:
        return "원"
    if "만" in raw and "원" in raw:
        return "원"
    if "원" in raw:
        return "원"
    if "일" in raw:
        return "일"
    if "시간" in raw:
        return "시간"
    if "%" in raw:
        return "%"
    return None


def extract_terms(clause_text: str) -> list[dict]:
    seen_spans: set[tuple[int, int]] = set()
    results: list[dict] = []
    for pattern, term_type, unit, basis in PATTERNS:
        for match in re.finditer(pattern, clause_text):
            span = (match.start(), match.end())
            if span in seen_spans:
                continue
            raw = match.group(0).strip()
            if len(raw) < 2:
                continue
            if not raw_text_is_grounded(clause_text, raw):
                continue
            seen_spans.add(span)
            results.append({
                "term_type": term_type,
                "value_num": _extract_value(raw),
                "unit": _guess_unit(raw, unit),
                "basis": basis,
                "raw_text": raw,
            })
    return results


def run() -> None:
    db = SessionLocal()
    try:
        if db.query(ClauseTerm).count() > 0:
            print("이미 시드됨 (clause_term). 스킵합니다.")
            return

        clauses = db.query(Clause).filter(Clause.text.isnot(None)).all()
        created = 0
        by_type: dict[str, int] = {}
        for clause in clauses:
            for term in extract_terms(clause.text):
                db.add(ClauseTerm(
                    clause_id=clause.clause_id,
                    term_type=term["term_type"],
                    value_num=term["value_num"],
                    unit=term["unit"],
                    basis=term["basis"],
                    condition_text=None,
                    raw_text=term["raw_text"],
                    confidence=None,
                ))
                created += 1
                by_type[term["term_type"]] = by_type.get(term["term_type"], 0) + 1
        db.commit()
        print(f"clause_term 시드 완료: {created}건 생성 (조항 {len(clauses)}건 검토)")
        print(f"  term_type 분포: {by_type}")
    finally:
        db.close()


if __name__ == "__main__":
    run()
