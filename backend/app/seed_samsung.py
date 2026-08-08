"""
삼성화재 해외여행보험(50002_0, 2024-04-01) 실물 약관 KB 시드 스크립트.

원문 출처: data/raw_pdfs/samsung_overseas_50002_0_20240401.pdf
(docs/compliance/source_register.md 참조)

MVP 범위(ne.md 9.2)에 맞춰 다음 3개 표준담보만 우선 적재한다.
- DEATH_INJURY : 상해사망·후유장해 (보통약관)
- OVS_INJ_MED  : 해외발생 상해의료비 (기본형 해외여행 실손의료비 특별약관 내 상해-해외의료비)
- RESCUE       : 중대사고 구조송환비용 (여행중 중대사고 구조송환비용 특별약관)

조항 텍스트는 PDF에서 추출한 원문을 그대로 인용한다(요약/재작성 금지 — 형광펜 근거 무결성).
"""
import datetime as dt

from app.database import Base, SessionLocal, engine
from app import models
from app.models.kb import Insurer, Product, PolicyVersion, Coverage, Clause, CoverageDocMap
from app.services.kb_seed_common import seed_common_coverage_std, seed_common_doc_std

Base.metadata.create_all(bind=engine)


def run():
    db = SessionLocal()
    try:
        if db.query(Insurer).filter_by(code="SAMSUNG").first():
            print("이미 시드됨 (SAMSUNG). 스킵합니다.")
            return

        insurer = Insurer(
            name="삼성화재해상보험",
            code="SAMSUNG",
            is_underwriter=True,
            official_url="https://www.samsungfire.com",
        )
        db.add(insurer)
        db.flush()

        product = Product(
            insurer_id=insurer.insurer_id,
            name="해외여행보험(다이렉트)",
            product_code="50002",
            channel="다이렉트",
            sale_start=dt.date(2024, 4, 1),
            sale_end=None,
            collected_at=dt.date(2026, 7, 28),
            review_status="raw",
        )
        db.add(product)
        db.flush()

        pv = PolicyVersion(
            product_id=product.product_id,
            version_label="50002_0",
            effective_date=dt.date(2024, 4, 1),
            approval_no=None,
            source_url="https://www.samsungfire.com/publication/pdf/50002_0_20240401_file1.pdf",
            file_hash="0ca4c127c566bc3a61d41ddb459d7134e8d5b931b06a99bceff6b48f92db7bb0",
        )
        db.add(pv)
        db.flush()

        # --- 표준 담보 사전 (MVP 3종. 보험사 공통이므로 get_or_create로 공유) ---
        std = seed_common_coverage_std(db)
        std_death_injury, std_ovs_inj_med, std_rescue = std["DEATH_INJURY"], std["OVS_INJ_MED"], std["RESCUE"]

        # --- 담보(coverage) ---
        cov_death_injury = Coverage(
            policy_version_id=pv.policy_version_id,
            coverage_std_id=std_death_injury.coverage_std_id,
            raw_name="상해사망·후유장해 (보통약관)",
            definition=(
                "회사는 피보험자에게 해외여행 도중에 다음 중 어느 하나의 사유가 발생한 경우에는 "
                "보험수익자에게 약정한 보험금을 지급합니다. "
                "1. 보험기간 중에 상해의 직접결과로써 사망한 경우(질병으로 인한 사망은 제외합니다): 사망보험금 "
                "2. 보험기간 중 상해로 장해분류표(<별표 1> 참조)에서 정한 각 장해지급률에 해당하는 "
                "장해상태가 되었을 때: 후유장해보험금"
            ),
            limit_amount="가입금액 한도 (증권 기재 보험가입금액)",
            deductible=None,
            waiting_condition="장해지급률 미확정 시 상해 발생일부터 180일 시점 진단 기준",
        )
        cov_ovs_inj_med = Coverage(
            policy_version_id=pv.policy_version_id,
            coverage_std_id=std_ovs_inj_med.coverage_std_id,
            raw_name="기본형 해외여행 실손의료비 특별약관 - (1)상해 해외의료비",
            definition=(
                "회사는 피보험자가 보험증권에 기재된 해외여행 중에 상해를 입고, 이로 인해 해외의료기관에서 "
                "의사(치료받는 국가의 법에서 정한 병원 및 의사의 자격을 가진 자에 한함)의 치료를 받은 때에는 "
                "보험가입금액을 한도로 피보험자가 실제 부담한 의료비 전액을 보상합니다."
            ),
            limit_amount="보험가입금액 한도, 실제 부담 의료비 전액 (척추지압술·침술은 건당 US$1,000 한도)",
            deductible="가입 시 선택한 자기부담금(자기부담금설정 추가특별약관 가입 시)",
            waiting_condition="보험기간 종료 후에도 종료일부터 180일까지 계속 치료 시 보상",
        )
        cov_rescue = Coverage(
            policy_version_id=pv.policy_version_id,
            coverage_std_id=std_rescue.coverage_std_id,
            raw_name="여행중 중대사고 구조송환비용 특별약관",
            definition=(
                "회사는 해외여행 도중 피보험자가 탑승한 항공기·선박의 행방불명·조난, 산악등반 중 조난, "
                "긴급수색구조가 필요한 사고(경찰 등 공공기관 확인), 사망 또는 회사가 정한 일수(14일/7일/4일 중 "
                "선택) 이상 계속 입원한 경우에 수색구조비용·구원자 교통비·숙박비·이송비용·제잡비를 보상합니다."
            ),
            limit_amount="보험가입금액 한도 (구원자 교통비 2명분, 숙박비 1인당 14박 한도, 제잡비 10만원 한도)",
            deductible="청약 시 선택(자기부담률 없음/10%/20%, 10만원 공제 후 적용)",
            waiting_condition="입원의 경우 계약자가 청약 시 선택한 일수(14일/7일/4일) 이상 계속 입원 필요",
        )
        db.add_all([cov_death_injury, cov_ovs_inj_med, cov_rescue])
        db.flush()

        # --- 조항(clause) : 원문 인용, 형광펜 근거 ---
        clauses = [
            # DEATH_INJURY
            Clause(
                policy_version_id=pv.policy_version_id, coverage_id=cov_death_injury.coverage_id,
                clause_type="보장정의", article_no="제3조(보험금의 지급사유)",
                text=(
                    "회사는 피보험자에게 해외여행 도중에 다음 중 어느 하나의 사유가 발생한 경우에는 "
                    "보험수익자에게 약정한 보험금을 지급합니다. "
                    "1. 보험기간 중에 상해의 직접결과로써 사망한 경우(질병으로 인한 사망은 제외합니다): 사망보험금 "
                    "2. 보험기간 중 상해로 장해분류표(<별표 1> 참조)에서 정한 각 장해지급률에 해당하는 "
                    "장해상태가 되었을 때: 후유장해보험금"
                ),
                page_ref="p.10-11", embedding_id=None, default_color="파랑",
            ),
            Clause(
                policy_version_id=pv.policy_version_id, coverage_id=cov_death_injury.coverage_id,
                clause_type="면책", article_no="제5조(보험금을 지급하지 않는 사유)",
                text=(
                    "① 회사는 다음 중 어느 한가지로 보험금 지급사유가 발생한 때에는 보험금을 지급하지 않습니다. "
                    "1. 피보험자가 고의로 자신을 해친 경우(심신상실 등 예외 있음) "
                    "2. 보험수익자가 고의로 피보험자를 해친 경우 "
                    "3. 계약자가 고의로 피보험자를 해친 경우 "
                    "4. 피보험자의 임신, 출산(제왕절개 포함), 산후기 "
                    "5. 전쟁, 외국의 무력행사, 혁명, 내란, 사변, 폭동 "
                    "② 전문등반, 글라이더 조종, 스카이다이빙, 스쿠버다이빙, 행글라이딩, 수상보트, "
                    "패러글라이딩 등 직업·직무·동호회 활동 목적의 위험 행위로 인한 상해는 다른 약정이 없으면 보장하지 않습니다."
                ),
                page_ref="p.13", embedding_id=None, default_color="빨강",
            ),
            # 공통 서류 조항 (coverage_id=null)
            Clause(
                policy_version_id=pv.policy_version_id, coverage_id=None,
                clause_type="서류", article_no="제7조(보험금의 청구)",
                text=(
                    "① 보험수익자는 다음의 서류를 제출하고 보험금을 청구하여야 합니다. "
                    "1. 청구서(회사 양식) "
                    "2. 사고증명서(진료비계산서, 사망진단서, 장해진단서, 입원치료확인서, 의사처방전(처방조제비) 등) "
                    "3. 신분증(주민등록증이나 운전면허증 등 사진이 붙은 정부기관발행 신분증) "
                    "4. 기타 보험수익자가 보험금의 수령에 필요하여 제출하는 서류 "
                    "② 사고증명서는 국내 의료기관 또는 국외의 의료관련법에서 정한 의료기관에서 발급한 것이어야 합니다."
                ),
                page_ref="p.14", embedding_id=None, default_color="노랑",
            ),
            # OVS_INJ_MED
            Clause(
                policy_version_id=pv.policy_version_id, coverage_id=cov_ovs_inj_med.coverage_id,
                clause_type="보장정의", article_no="제3조(보장종목별 보상내용) (1)상해-해외의료비",
                text=(
                    "① 회사는 피보험자가 보험증권에 기재된 해외여행 중에 상해를 입고, 이로 인해 해외의료기관에서 "
                    "의사(치료받는 국가의 법에서 정한 병원 및 의사의 자격을 가진 자에 한함)의 치료를 받은 때에는 "
                    "보험가입금액을 한도로 피보험자가 실제 부담한 의료비 전액을 보상합니다. "
                    "② 척추지압술이나 침술 치료로 인한 의료비는 하나의 상해에 대하여 US $1,000.00 한도로 보상합니다. "
                    "③ 유독가스 또는 유독물질을 우연히 일시에 흡입·흡수·섭취한 결과로 생긴 중독증상이 포함됩니다. "
                    "④ 보험기간 종료일부터 180일까지(종료일 제외) 계속 치료 시 보상합니다."
                ),
                page_ref="p.56", embedding_id=None, default_color="파랑",
            ),
            Clause(
                policy_version_id=pv.policy_version_id, coverage_id=cov_ovs_inj_med.coverage_id,
                clause_type="면책", article_no="제4조(보상하지 않는 사항) (1)상해-해외의료비",
                text=(
                    "회사는 다음의 사유로 인하여 생긴 의료비는 보상하지 않습니다. "
                    "1. 피보험자가 고의로 자신을 해친 경우(심신상실 등 예외 있음) "
                    "2. 보험수익자가 고의로 피보험자를 해친 경우 "
                    "3. 계약자가 고의로 피보험자를 해친 경우 "
                    "4. 피보험자가 임신, 출산(제왕절개 포함), 산후기로 치료한 경우(상해로 인한 경우 제외) "
                    "5. 전쟁, 외국의 무력행사, 혁명, 내란, 사변, 폭동으로 인한 경우 "
                    "6. 피보험자가 정당한 이유 없이 입원기간 중 의사의 지시를 따르지 않은 경우 등"
                ),
                page_ref="p.58", embedding_id=None, default_color="빨강",
            ),
            Clause(
                policy_version_id=pv.policy_version_id, coverage_id=cov_ovs_inj_med.coverage_id,
                clause_type="서류", article_no="제7조(보험금의 청구) [실손의료비 특약]",
                text=(
                    "① 보험수익자는 다음의 서류를 제출하고 보험금을 청구하여야 합니다. "
                    "1. 청구서(회사 양식) "
                    "2. 사고증명서(진료비계산서, 진료비세부내역서, 장해진단서, 입원치료확인서, 의사처방전(처방조제비) 등) "
                    "3. 신분증 "
                    "4. 기타 보험수익자가 보험금의 수령에 필요하여 제출하는 서류 "
                    "② 사고증명서는 국내 의료기관 또는 국외 의료관련법에서 정한 의료기관에서 발급한 것이어야 합니다."
                ),
                page_ref="p.66-67", embedding_id=None, default_color="노랑",
            ),
            # RESCUE
            Clause(
                policy_version_id=pv.policy_version_id, coverage_id=cov_rescue.coverage_id,
                clause_type="보장정의", article_no="제1조(보상하는 손해)~제2조(비용의 범위)",
                text=(
                    "① 회사는 해외여행 도중에 피보험자가 탑승한 항공기 또는 선박이 행방불명 또는 조난된 경우, "
                    "산악등반 중 조난된 경우, 급격하고도 우연한 외래의 사고로 긴급수색구조 등이 필요한 상태로 된 것이 "
                    "경찰 등 공공기관에 의해 확인된 경우, 사망하거나 회사가 정한 일수(14일/7일/4일 중 선택) 이상 "
                    "계속 입원한 경우에 비용을 보상합니다. "
                    "비용의 범위: 1.수색구조비용 2.항공운임 등 교통비(구원자 2명분 한도) "
                    "3.숙박비(구원자 2명분, 1인당 14박 한도) 4.이송비용 5.제잡비(10만원 한도)"
                ),
                page_ref="p.51-52", embedding_id=None, default_color="파랑",
            ),
            Clause(
                policy_version_id=pv.policy_version_id, coverage_id=cov_rescue.coverage_id,
                clause_type="면책", article_no="제3조(보상하지 않는 손해)",
                text=(
                    "회사는 보통약관 제5조(보험금을 지급하지 않는 사유)에도 불구하고, 동조 제1항 제1호 내지 제3호"
                    "(피보험자·보험수익자·계약자의 고의)의 사유로 인하여 생긴 손해에 한하여 보상하지 않습니다."
                ),
                page_ref="p.52", embedding_id=None, default_color="빨강",
            ),
            Clause(
                policy_version_id=pv.policy_version_id, coverage_id=cov_rescue.coverage_id,
                clause_type="조건", article_no="제6조(자기부담금 및 보상한도액)",
                text=(
                    "① 회사는 1사고당 또는 1질병당 계약자가 청약할 때 선택한 자기부담률(자기부담률 없음 / "
                    "10만원 공제 후 10% / 10만원 공제 후 20%)을 적용하여 자기부담금을 계산합니다. "
                    "② 회사가 지급할 보험금은 보험기간을 통하여 이 특별약관의 보험가입금액을 한도로 합니다."
                ),
                page_ref="p.53", embedding_id=None, default_color="노랑",
            ),
        ]
        db.add_all(clauses)
        db.flush()
        clause_by_article = {c.article_no: c for c in clauses}

        # --- 표준 청구서류 (보험사 공통이므로 get_or_create로 공유) ---
        docs_map = seed_common_doc_std(db)
        doc_claim_form = docs_map["CLAIM_FORM"]
        doc_medical_cost = docs_map["MEDICAL_EXPENSE_CERT"]
        doc_medical_detail = docs_map["MEDICAL_DETAIL_CERT"]
        doc_treatment_cert = docs_map["TREATMENT_CERT"]
        doc_prescription = docs_map["PRESCRIPTION"]
        doc_disability_cert = docs_map["DISABILITY_CERT"]
        doc_death_cert = docs_map["DEATH_CERT"]
        doc_id_card = docs_map["ID_CARD"]
        docs = list(docs_map.values())

        # --- 담보 x 서류 매핑 ---
        doc_maps = [
            CoverageDocMap(coverage_id=cov_death_injury.coverage_id, required_doc_std_id=doc_claim_form.required_doc_std_id, is_mandatory=True, clause_id=clause_by_article["제7조(보험금의 청구)"].clause_id),
            CoverageDocMap(coverage_id=cov_death_injury.coverage_id, required_doc_std_id=doc_death_cert.required_doc_std_id, is_mandatory=True, clause_id=clause_by_article["제7조(보험금의 청구)"].clause_id),
            CoverageDocMap(coverage_id=cov_death_injury.coverage_id, required_doc_std_id=doc_disability_cert.required_doc_std_id, is_mandatory=False, clause_id=clause_by_article["제7조(보험금의 청구)"].clause_id),
            CoverageDocMap(coverage_id=cov_death_injury.coverage_id, required_doc_std_id=doc_id_card.required_doc_std_id, is_mandatory=True, clause_id=clause_by_article["제7조(보험금의 청구)"].clause_id),

            CoverageDocMap(coverage_id=cov_ovs_inj_med.coverage_id, required_doc_std_id=doc_claim_form.required_doc_std_id, is_mandatory=True, clause_id=clause_by_article["제7조(보험금의 청구) [실손의료비 특약]"].clause_id),
            CoverageDocMap(coverage_id=cov_ovs_inj_med.coverage_id, required_doc_std_id=doc_medical_cost.required_doc_std_id, is_mandatory=True, clause_id=clause_by_article["제7조(보험금의 청구) [실손의료비 특약]"].clause_id),
            CoverageDocMap(coverage_id=cov_ovs_inj_med.coverage_id, required_doc_std_id=doc_medical_detail.required_doc_std_id, is_mandatory=True, clause_id=clause_by_article["제7조(보험금의 청구) [실손의료비 특약]"].clause_id),
            CoverageDocMap(coverage_id=cov_ovs_inj_med.coverage_id, required_doc_std_id=doc_treatment_cert.required_doc_std_id, is_mandatory=False, clause_id=clause_by_article["제7조(보험금의 청구) [실손의료비 특약]"].clause_id),
            CoverageDocMap(coverage_id=cov_ovs_inj_med.coverage_id, required_doc_std_id=doc_prescription.required_doc_std_id, is_mandatory=False, clause_id=clause_by_article["제7조(보험금의 청구) [실손의료비 특약]"].clause_id),
            CoverageDocMap(coverage_id=cov_ovs_inj_med.coverage_id, required_doc_std_id=doc_id_card.required_doc_std_id, is_mandatory=True, clause_id=clause_by_article["제7조(보험금의 청구) [실손의료비 특약]"].clause_id),

            # 구조송환비용 특약 원문 자체에는 서류 목록이 없음(제4조는 "정당하다고 인정된 부분만 보상"이라고만 규정).
            # 보통약관 공통 제7조를 근거로 추론 매핑한 것이므로 is_mandatory=False로 표시하고,
            # 실제 서비스 화면에서는 "이 특약에 명시된 서류 목록 아님, 보험사 확인 필요"로 안내해야 한다.
            CoverageDocMap(coverage_id=cov_rescue.coverage_id, required_doc_std_id=doc_claim_form.required_doc_std_id, is_mandatory=False, clause_id=clause_by_article["제7조(보험금의 청구)"].clause_id),
            CoverageDocMap(coverage_id=cov_rescue.coverage_id, required_doc_std_id=doc_id_card.required_doc_std_id, is_mandatory=False, clause_id=clause_by_article["제7조(보험금의 청구)"].clause_id),
        ]
        db.add_all(doc_maps)

        db.commit()
        print("삼성화재 KB 시드 완료: insurer=1, product=1, policy_version=1, coverage_std=3, "
              f"coverage=3, clause={len(clauses)}, required_doc_std={len(docs)}, coverage_doc_map={len(doc_maps)}")
    finally:
        db.close()


if __name__ == "__main__":
    run()
