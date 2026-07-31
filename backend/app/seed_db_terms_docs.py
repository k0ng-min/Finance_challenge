"""
DB손해보험 ClauseTerm(금액·한도 수치) + CoverageDocMap(필요서류) 채우기

이 스크립트는 다음을 수행한다:
1. DB손해보험의 모든 Clause(66개)를 훑으면서 ClauseTerm 추출 — 지급한도, 자기부담금,
   지연기준시간, 보상일수한도, 면책일수, 1일당지급액 등의 숫자 조건
2. DB손해보험의 모든 Coverage(21개)에 CoverageDocMap 연결 — 최소 CLAIM_FORM + ID_CARD는 필수

새로 생성되는 RequiredDocStd:
- POLICE_REPORT: 현지 경찰 신고확인서(도난·분실·배상책임 사고)
- LIABILITY_EVIDENCE: 배상책임 관련 서류(합의서·손해배상 청구서·상대방 피해 확인서류)

산출: ClauseTerm XX개 생성, CoverageDocMap 21개 추가
"""
import re
from app.database import SessionLocal
from app.models.kb import (
    Insurer, Product, PolicyVersion, Clause, Coverage, ClauseTerm,
    RequiredDocStd, CoverageDocMap
)
from app.services.kb_seed_common import raw_text_is_grounded, get_or_create_doc_std


def extract_clause_terms(clause: Clause, db) -> list[ClauseTerm]:
    """Clause.text에서 ClauseTerm 후보를 추출한다.

    raw_text_is_grounded(clause.text, raw_text)로 검증한 후에만 반환한다.
    """
    terms = []
    text = clause.text
    if not text:
        return terms

    # 패턴 모음: (정규식, term_type, unit, basis 또는 None)
    # 이 패턴들은 PLAYBOOK의 term_type 고정 어휘를 따른다.
    patterns = [
        # 지급한도: "USD $1,000", "1,000달러", "1,000원", "100만원", "5천만원" 등
        (r'(?:US)?\$[\d,]+(?:\.\d+)?', '지급한도', 'USD', None),
        (r'[\d,]+(?:\.\d+)?\s*(?:달러|원|일|시간|%)', '지급한도', None, None),

        # 면책일수: "2일 이상", "3일 이상" — 입원 최소 조건
        (r'(\d+)\s*일\s*이상\s*(?:입원|통원|입원·통원)', '면책일수', '일', None),

        # 보상일수한도: "180일까지", "90일 한도", "20일 이내"
        (r'(\d+)\s*일\s*(?:까지|한도|이내)', '보상일수한도', '일', None),

        # 지연기준시간: "4시간 이상", "12시간 이상" (항공기/수하물 지연)
        (r'(\d+)\s*시간\s*이상', '지연기준시간', '시간', None),

        # 1일당지급액: "1일당 70,000원", "일당 10달러"
        (r'(?:1)?일당\s*[\d,]+(?:\.\d+)?\s*(?:원|달러|%)?', '1일당지급액', None, None),
    ]

    for pattern, term_type, unit, basis in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            raw_text = match.group(0)

            # grounding 검증
            if not raw_text_is_grounded(text, raw_text):
                continue

            # value_num 추출 시도
            num_match = re.search(r'[\d,]+(?:\.\d+)?', raw_text)
            value_num = None
            if num_match:
                try:
                    value_num = float(num_match.group(0).replace(',', ''))
                except ValueError:
                    pass

            # unit 재확인
            actual_unit = unit
            if not actual_unit:
                if '원' in raw_text:
                    actual_unit = '원'
                elif '달러' in raw_text or '$' in raw_text:
                    actual_unit = 'USD'
                elif '%' in raw_text:
                    actual_unit = '%'
                elif '일' in raw_text:
                    actual_unit = '일'
                elif '시간' in raw_text:
                    actual_unit = '시간'

            term = ClauseTerm(
                clause_id=clause.clause_id,
                term_type=term_type,
                value_num=value_num,
                unit=actual_unit,
                basis=basis,
                condition_text=None,  # 짧은 문맥이 필요하면 수동으로 채워진다
                raw_text=raw_text,
                confidence=0.7,  # 자동 추출이므로 낮은 신뢰도
            )
            terms.append(term)

    return terms


def map_coverage_to_docs(coverage: Coverage, db) -> list[CoverageDocMap]:
    """Coverage의 성격을 바탕으로 필요한 RequiredDocStd를 매핑한다.

    PLAYBOOK의 완전성 원칙: 모든 담보에 최소 CLAIM_FORM + ID_CARD 필수.
    """
    maps = []
    raw_name = coverage.raw_name.lower()

    # 공통 필수 서류
    claim_form = db.query(RequiredDocStd).filter_by(doc_code='CLAIM_FORM').first()
    id_card = db.query(RequiredDocStd).filter_by(doc_code='ID_CARD').first()

    if claim_form:
        maps.append(CoverageDocMap(
            coverage_id=coverage.coverage_id,
            required_doc_std_id=claim_form.required_doc_std_id,
            is_mandatory=True,
            clause_id=None,
        ))

    if id_card:
        maps.append(CoverageDocMap(
            coverage_id=coverage.coverage_id,
            required_doc_std_id=id_card.required_doc_std_id,
            is_mandatory=True,
            clause_id=None,
        ))

    # 담보 성격별 추가 서류
    # 의료비 관련 (상해의료비, 질병의료비, 의료비 등)
    if any(x in raw_name for x in ['의료', '의학', '진료', '치료', '질병']):
        medical_docs = ['MEDICAL_EXPENSE_CERT', 'MEDICAL_DETAIL_CERT', 'TREATMENT_CERT']
        for doc_code in medical_docs:
            doc = db.query(RequiredDocStd).filter_by(doc_code=doc_code).first()
            if doc:
                maps.append(CoverageDocMap(
                    coverage_id=coverage.coverage_id,
                    required_doc_std_id=doc.required_doc_std_id,
                    is_mandatory=True,
                    clause_id=None,
                ))

    # 사망 관련 (질병사망 포함)
    if any(x in raw_name for x in ['사망', '사망보험금']):
        death_doc = db.query(RequiredDocStd).filter_by(doc_code='DEATH_CERT').first()
        if death_doc:
            maps.append(CoverageDocMap(
                coverage_id=coverage.coverage_id,
                required_doc_std_id=death_doc.required_doc_std_id,
                is_mandatory=True,
                clause_id=None,
            ))

    # 후유장해 관련
    if any(x in raw_name for x in ['장해', '후유', '장해진단']):
        disability_doc = db.query(RequiredDocStd).filter_by(doc_code='DISABILITY_CERT').first()
        if disability_doc:
            maps.append(CoverageDocMap(
                coverage_id=coverage.coverage_id,
                required_doc_std_id=disability_doc.required_doc_std_id,
                is_mandatory=True,
                clause_id=None,
            ))

    # 도난/분실/휴대품손해 관련 — 경찰신고 필요
    if any(x in raw_name for x in ['도난', '분실', '도둑', '휴대품']):
        police_doc = db.query(RequiredDocStd).filter_by(doc_code='POLICE_REPORT').first()
        if police_doc:
            maps.append(CoverageDocMap(
                coverage_id=coverage.coverage_id,
                required_doc_std_id=police_doc.required_doc_std_id,
                is_mandatory=True,
                clause_id=None,
            ))

    # 배상책임 관련 — 배상책임 증거 서류 필요
    if any(x in raw_name for x in ['배상책임', '배상']):
        liability_doc = db.query(RequiredDocStd).filter_by(doc_code='LIABILITY_EVIDENCE').first()
        if liability_doc:
            maps.append(CoverageDocMap(
                coverage_id=coverage.coverage_id,
                required_doc_std_id=liability_doc.required_doc_std_id,
                is_mandatory=True,
                clause_id=None,
            ))

    return maps


def run():
    """DB손해보험 ClauseTerm + CoverageDocMap 시드.

    Idempotent: 이미 생성된 항목은 건너뛴다.
    """
    db = SessionLocal()
    try:
        # DB손해보험 확인
        insurer = db.query(Insurer).filter_by(code='DB').first()
        if not insurer:
            print("DB손해보험이 아직 시딩되지 않았습니다.")
            return

        # PolicyVersion 조회
        pv = (db.query(PolicyVersion)
              .join(Product, Product.product_id == PolicyVersion.product_id)
              .filter(Product.insurer_id == insurer.insurer_id)
              .first())
        if not pv:
            print("DB손해보험 PolicyVersion을 찾을 수 없습니다.")
            return

        print(f"DB손해보험 시딩 시작 (PolicyVersion {pv.policy_version_id})")

        # 새로운 RequiredDocStd 코드 생성 (필요한 경우만)
        police_report = get_or_create_doc_std(
            db, 'POLICE_REPORT', '현지 경찰 신고확인서(도난·분실·배상책임 사고)',
            '현지only', '도난·분실·배상책임 사고 시 현지 경찰에서 발급'
        )
        liability_evidence = get_or_create_doc_std(
            db, 'LIABILITY_EVIDENCE', '배상책임 관련 서류(합의서·손해배상 청구서·상대방 피해 확인서류)',
            '귀국가능', '배상책임 보험금 청구 시 필요'
        )

        # 1) ClauseTerm 추출
        clauses = (db.query(Clause)
                   .filter(Clause.policy_version_id == pv.policy_version_id)
                   .order_by(Clause.clause_id)
                   .all())

        inserted_terms = 0
        term_type_dist = {}

        for clause in clauses:
            # 이미 있는 ClauseTerm은 건너뛴다
            existing = db.query(ClauseTerm).filter_by(clause_id=clause.clause_id).count()
            if existing > 0:
                continue

            new_terms = extract_clause_terms(clause, db)
            for term in new_terms:
                db.add(term)
                inserted_terms += 1
                term_type_dist[term.term_type] = term_type_dist.get(term.term_type, 0) + 1

        if inserted_terms > 0:
            db.commit()
            print(f"  ClauseTerm 추가: {inserted_terms}개")
            for tt, count in sorted(term_type_dist.items()):
                print(f"    {tt}: {count}개")
        else:
            print("  ClauseTerm 추가: 0개 (기존 데이터 유지)")

        # 2) CoverageDocMap 채우기
        coverages = (db.query(Coverage)
                     .filter(Coverage.policy_version_id == pv.policy_version_id)
                     .order_by(Coverage.coverage_id)
                     .all())

        inserted_maps = 0
        coverage_count = 0

        for coverage in coverages:
            # 이미 있는 CoverageDocMap 개수 확인
            existing = db.query(CoverageDocMap).filter_by(coverage_id=coverage.coverage_id).count()

            # PLAYBOOK: 새 담보는 전부 추가, 기존 담보는 건너뛴다
            if existing > 0:
                continue

            new_maps = map_coverage_to_docs(coverage, db)
            for map_obj in new_maps:
                db.add(map_obj)
                inserted_maps += 1

            if new_maps:
                coverage_count += 1

        if inserted_maps > 0:
            db.commit()
            print(f"  CoverageDocMap 추가: {inserted_maps}개 ({coverage_count}개 담보)")
        else:
            print("  CoverageDocMap 추가: 0개 (기존 데이터 유지)")

        print(f"\nDB손해보험 시딩 완료")

    except Exception as e:
        db.rollback()
        print(f"오류: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
