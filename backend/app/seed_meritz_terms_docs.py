"""
메리츠화재 ClauseTerm(금액·한도 수치) + CoverageDocMap(필요서류) 채우기

이 스크립트는 다음을 수행한다:
1. 메리츠화재의 모든 Clause(52개)를 훑으면서 ClauseTerm 추출 — 지급한도, 자기부담금,
   지연기준시간, 보상일수한도, 면책일수, 1일당지급액 등의 숫자 조건
2. 메리츠화재의 모든 Coverage(26개)에 CoverageDocMap 연결 — 최소 CLAIM_FORM + ID_CARD는 필수

산출: ClauseTerm XX개 생성, CoverageDocMap XX개 추가
"""
import re
from datetime import datetime
from app.database import SessionLocal
from app.models.kb import (
    Insurer, Product, PolicyVersion, Clause, Coverage, ClauseTerm,
    RequiredDocStd, CoverageDocMap
)
from app.services.kb_seed_common import raw_text_is_grounded, get_or_create_doc_std


def extract_clause_terms(clause: Clause, db) -> list[ClauseTerm]:
    """Clause.text에서 ClauseTerm을 추출한다.

    PLAYBOOK 규칙:
    - term_type은 고정 어휘: 지급한도, 자기부담금, 지연기준시간, 보상일수한도, 면책일수, 1일당지급액
    - raw_text는 clause.text의 부분 문자열이어야 함 (raw_text_is_grounded 검증 필수)
    - value_num이 없는 경우(예: "10만원 공제 후 10%") raw_text만 저장
    """
    terms = []
    text = clause.text
    if not text:
        return terms

    # 구체적인 숫자 패턴들 (메리츠 Clause에서 실제로 나타나는 형태)
    candidates = []

    # 1) 지급한도: "US $1,000.00", "1,000원", "180일", "14박" 등
    # US $1,000.00 형식
    for m in re.finditer(r'US\s*\$[\d,]+(?:\.\d+)?', text):
        raw = m.group(0)
        if raw_text_is_grounded(text, raw):
            num_match = re.search(r'[\d,]+(?:\.\d+)?', raw)
            value = float(num_match.group(0).replace(',', '')) if num_match else None
            candidates.append(ClauseTerm(
                clause_id=clause.clause_id, term_type='지급한도', value_num=value,
                unit='USD', basis=None, condition_text=None, raw_text=raw, confidence=0.8
            ))

    # 2) 보상일수한도: "180일", "30일", "20일" 등 ("...일 한도", "...일까지", "...일 이내" 형식)
    for m in re.finditer(r'(\d+)\s*일\s*(?:한도|까지|이내)', text):
        raw = m.group(0)
        if raw_text_is_grounded(text, raw):
            num_str = m.group(1)
            try:
                value = float(num_str)
                candidates.append(ClauseTerm(
                    clause_id=clause.clause_id, term_type='보상일수한도', value_num=value,
                    unit='일', basis=None, condition_text=None, raw_text=raw, confidence=0.85
                ))
            except ValueError:
                pass

    # 3) 면책일수: "4일 이상" (입원 최소 조건)
    for m in re.finditer(r'(\d+)\s*일\s*이상\s*(?:입원|통원)', text):
        raw = m.group(0)
        if raw_text_is_grounded(text, raw):
            num_str = m.group(1)
            try:
                value = float(num_str)
                candidates.append(ClauseTerm(
                    clause_id=clause.clause_id, term_type='면책일수', value_num=value,
                    unit='일', basis=None, condition_text=None, raw_text=raw, confidence=0.8
                ))
            except ValueError:
                pass

    # 4) 지연기준시간: "4시간 이상", "12시간이 경과"
    for m in re.finditer(r'(\d+)\s*시간\s*(?:이상|이 경과)', text):
        raw = m.group(0)
        if raw_text_is_grounded(text, raw):
            num_str = m.group(1)
            try:
                value = float(num_str)
                candidates.append(ClauseTerm(
                    clause_id=clause.clause_id, term_type='지연기준시간', value_num=value,
                    unit='시간', basis=None, condition_text=None, raw_text=raw, confidence=0.8
                ))
            except ValueError:
                pass

    # 5) 1일당지급액: "1일당 70,000원", "1일에 대하여 [금액]"
    for m in re.finditer(r'(?:매일\s*|1일당\s*|1일에\s*대하여\s*)([\d,]+)\s*원', text):
        raw = m.group(0)
        if raw_text_is_grounded(text, raw):
            num_str = m.group(1)
            try:
                value = float(num_str.replace(',', ''))
                candidates.append(ClauseTerm(
                    clause_id=clause.clause_id, term_type='1일당지급액', value_num=value,
                    unit='원', basis='정액', condition_text=None, raw_text=raw, confidence=0.85
                ))
            except ValueError:
                pass

    # 6) 자기부담금: "1사고당 10만원"
    for m in re.finditer(r'(\d+)\s*(?:사고당|회당)\s*([\d,]+)\s*원', text):
        raw = m.group(0)
        if raw_text_is_grounded(text, raw):
            try:
                value = float(m.group(2).replace(',', ''))
                candidates.append(ClauseTerm(
                    clause_id=clause.clause_id, term_type='자기부담금', value_num=value,
                    unit='원', basis=None, condition_text=None, raw_text=raw, confidence=0.8
                ))
            except ValueError:
                pass

    # 중복 제거 (같은 raw_text로 여러 번 추가되는 것 방지)
    seen = set()
    unique_terms = []
    for term in candidates:
        key = (term.clause_id, term.raw_text)
        if key not in seen:
            seen.add(key)
            unique_terms.append(term)

    return unique_terms


def map_coverage_to_docs(coverage: Coverage, db) -> list[CoverageDocMap]:
    """Coverage의 성격을 바탕으로 필요한 RequiredDocStd를 매핑한다.

    PLAYBOOK 규칙:
    - 모든 담보에 최소 CLAIM_FORM + ID_CARD는 필수 (공통 서류)
    - 담보 성격에 따라 추가 서류 매핑
    - 이미 있는 담보는 건너뛰고, 새로운 담보에만 추가
    """
    maps = []
    raw_name = coverage.raw_name.lower() if coverage.raw_name else ""

    # 공통 필수 서류: CLAIM_FORM, ID_CARD
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

    # 의료비 관련 (상해의료비, 의료비, 진료, 치료, 입원일당, 식중독)
    if any(x in raw_name for x in ['의료', '의학', '진료', '치료', '입원', '식중독', '감염병', '특정전염병']):
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

    # 사망 관련
    if any(x in raw_name for x in ['사망', '사망보험금']):
        death_doc = db.query(RequiredDocStd).filter_by(doc_code='DEATH_CERT').first()
        if death_doc:
            maps.append(CoverageDocMap(
                coverage_id=coverage.coverage_id,
                required_doc_std_id=death_doc.required_doc_std_id,
                is_mandatory=True,
                clause_id=None,
            ))

    # 후유장해 관련 (장해, 후유장해)
    if any(x in raw_name for x in ['장해', '후유', '고도장해']):
        disability_doc = db.query(RequiredDocStd).filter_by(doc_code='DISABILITY_CERT').first()
        if disability_doc:
            maps.append(CoverageDocMap(
                coverage_id=coverage.coverage_id,
                required_doc_std_id=disability_doc.required_doc_std_id,
                is_mandatory=True,
                clause_id=None,
            ))

    # 도난/분실/배상책임/자택도난 관련 — 다른 5개사와 동일하게 POLICE_REPORT 재사용
    # (다른 보험사 스크립트가 이미 만들어뒀을 수 있으므로 get_or_create로 통일한다)
    if any(x in raw_name for x in ['도난', '분실', '휴대품', '도둑', '배상책임', '배상', '손해배상']):
        police_doc = get_or_create_doc_std(
            db, 'POLICE_REPORT', '현지 경찰 신고확인서', '현지only',
            '도난·분실·배상책임 사고 시 현지 경찰서에서 발급'
        )
        maps.append(CoverageDocMap(
            coverage_id=coverage.coverage_id,
            required_doc_std_id=police_doc.required_doc_std_id,
            is_mandatory=True,
            clause_id=None,
        ))

    # 배상책임 관련 — LIABILITY_EVIDENCE
    if any(x in raw_name for x in ['배상책임', '배상', '손해배상']):
        liability_doc = get_or_create_doc_std(
            db, 'LIABILITY_EVIDENCE', '배상책임 관련 서류', '귀국가능',
            '합의서·손해배상 청구서·상대방 피해 확인서류'
        )
        maps.append(CoverageDocMap(
            coverage_id=coverage.coverage_id,
            required_doc_std_id=liability_doc.required_doc_std_id,
            is_mandatory=True,
            clause_id=None,
        ))

    # 여권분실 관련 — PASSPORT_REISSUE_RECEIPT
    if any(x in raw_name for x in ['여권', '여행증명서']):
        passport_doc = get_or_create_doc_std(
            db, 'PASSPORT_REISSUE_RECEIPT', '여권(여행증명서) 재발급 영수증·확인서', '귀국가능',
            '여권 분실 후 재발급 시 발급받는 영수증 또는 확인서'
        )
        maps.append(CoverageDocMap(
            coverage_id=coverage.coverage_id,
            required_doc_std_id=passport_doc.required_doc_std_id,
            is_mandatory=True,
            clause_id=None,
        ))

    # 항공기 지연·결항 관련 — FLIGHT_DELAY_CERT
    if any(x in raw_name for x in ['항공기', '항공', '지연']) and '납치' not in raw_name:
        flight_doc = get_or_create_doc_std(
            db, 'FLIGHT_DELAY_CERT', '항공기 지연·결항 확인서', '귀국가능',
            '항공사가 발급하는 지연·결항 확인서'
        )
        maps.append(CoverageDocMap(
            coverage_id=coverage.coverage_id,
            required_doc_std_id=flight_doc.required_doc_std_id,
            is_mandatory=True,
            clause_id=None,
        ))

    # 수하물 지연·분실 관련 — BAGGAGE_IRREGULARITY
    if '수하물' in raw_name:
        baggage_doc = get_or_create_doc_std(
            db, 'BAGGAGE_IRREGULARITY', '수하물 지연·분실 확인서(PIR)', '현지only',
            '항공사가 발급하는 수하물 이상 신고서(Property Irregularity Report)'
        )
        maps.append(CoverageDocMap(
            coverage_id=coverage.coverage_id,
            required_doc_std_id=baggage_doc.required_doc_std_id,
            is_mandatory=True,
            clause_id=None,
        ))

    return maps


def run():
    """메리츠화재 ClauseTerm + CoverageDocMap 시드.

    Idempotent: 이미 생성된 항목은 건너뛴다.
    """
    db = SessionLocal()
    try:
        # 메리츠화재 확인
        insurer = db.query(Insurer).filter_by(code='MERITZ').first()
        if not insurer:
            print("메리츠화재가 아직 시딩되지 않았습니다.")
            return

        # PolicyVersion 조회
        pv = (db.query(PolicyVersion)
              .join(Product, Product.product_id == PolicyVersion.product_id)
              .filter(Product.insurer_id == insurer.insurer_id)
              .first())
        if not pv:
            print("메리츠화재 PolicyVersion을 찾을 수 없습니다.")
            return

        print(f"메리츠화재(MERITZ) 시딩 시작")
        print(f"  PolicyVersion ID: {pv.policy_version_id}")

        # 1) ClauseTerm 추출 및 저장
        print("\n1) ClauseTerm 추출...")
        clauses = (db.query(Clause)
                   .filter(Clause.policy_version_id == pv.policy_version_id)
                   .order_by(Clause.clause_id)
                   .all())

        inserted_terms = 0
        term_type_dist = {}
        skipped_clauses = []

        for clause in clauses:
            # 이미 있는 ClauseTerm은 건너뛴다 (idempotent)
            existing = db.query(ClauseTerm).filter_by(clause_id=clause.clause_id).count()
            if existing > 0:
                continue

            new_terms = extract_clause_terms(clause, db)
            if new_terms:
                for term in new_terms:
                    db.add(term)
                    inserted_terms += 1
                    term_type_dist[term.term_type] = term_type_dist.get(term.term_type, 0) + 1
            elif clause.text:
                # 숫자가 없는 조항들은 기록만 하고 건너뜀
                pass

        if inserted_terms > 0:
            db.commit()
            print(f"  ClauseTerm 추가: {inserted_terms}개")
            for tt in sorted(term_type_dist.keys()):
                print(f"    - {tt}: {term_type_dist[tt]}개")
        else:
            print(f"  ClauseTerm 추가: 0개 (숫자 조건 없음 또는 기존 데이터)")

        # 2) CoverageDocMap 채우기
        print("\n2) CoverageDocMap 채우기...")
        coverages = (db.query(Coverage)
                     .filter(Coverage.policy_version_id == pv.policy_version_id)
                     .order_by(Coverage.coverage_id)
                     .all())

        inserted_maps = 0
        coverage_with_docs = 0
        coverage_already_has = []

        for coverage in coverages:
            # 이미 있는 CoverageDocMap 개수 확인
            existing_count = db.query(CoverageDocMap).filter_by(coverage_id=coverage.coverage_id).count()

            # PLAYBOOK: 새 담보는 전부 추가, 기존 담보는 건너뛴다 (idempotent)
            if existing_count > 0:
                coverage_already_has.append(coverage.coverage_id)
                continue

            new_maps = map_coverage_to_docs(coverage, db)
            for map_obj in new_maps:
                db.add(map_obj)
                inserted_maps += 1

            if new_maps:
                coverage_with_docs += 1

        if inserted_maps > 0:
            db.commit()
            print(f"  CoverageDocMap 추가: {inserted_maps}개 ({coverage_with_docs}개 담보)")
        else:
            print(f"  CoverageDocMap 추가: 0개")

        if coverage_already_has:
            print(f"  기존 CoverageDocMap 보유 담보: {len(coverage_already_has)}개 (건너뜀)")

        # 최종 요약
        print(f"\n=== 메리츠화재(MERITZ) 시딩 완료 ===")
        print(f"ClauseTerm: {inserted_terms}개 추가")
        if term_type_dist:
            for tt in sorted(term_type_dist.keys()):
                print(f"  - {tt}: {term_type_dist[tt]}개")
        print(f"CoverageDocMap: {inserted_maps}개 추가 ({coverage_with_docs}개 담보)")
        print(f"전체 Coverage: {len(coverages)}개 (기존 {len(coverage_already_has)}개)")

    except Exception as e:
        db.rollback()
        print(f"오류: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
