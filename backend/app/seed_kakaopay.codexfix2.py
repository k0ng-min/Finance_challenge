"""
카카오페이손해보험 해외여행보험 실물 약관 KB 시드 스크립트.

원문 출처: data/raw_pdfs/kakaopay_overseas_20241101.pdf
(docs/compliance/source_register.md 참조)

수집 경로: 공식 사이트(kakaopayinscorp.co.kr/disclosure/goods)는 SPA(JS 동적 렌더링)라
정적 크롤링이 안 되어, 해당 페이지가 내부적으로 호출하는 공식 API
(papi.kakaoinsure.com/notilus/v1/notices, categoryId=15 '판매중 상품')를 사용해
실제 게시된 파일 목록(제목·시행일·PDF 경로)을 조회한 뒤, 그 중 '해외여행보험' 최신
INSURANCE_POLICY(보험약관) 항목(2024-11-01 시행)을 다운로드했다. 최종 파일은 정식
서비스가 사용자에게 실제로 내려주는 것과 동일한 원본 PDF이므로 다른 5개사와 신뢰도 차이 없음.

ne.md 최초 버전은 "카카오페이는 약관 원문 미공개로 제외"라고 명시했으나, 실제로는
공시실에 공개되어 있음을 확인했으므로 6번째 보험사로 편입한다.
"""
import datetime as dt

from app.database import Base, SessionLocal, engine
from app import models
from app.models.kb import Coverage, Clause, CoverageDocMap
from app.services.kb_seed_common import seed_common_coverage_std, seed_common_doc_std, seed_insurer_core

Base.metadata.create_all(bind=engine)


def run():
    db = SessionLocal()
    try:
        insurer, product, pv = seed_insurer_core(
            db,
            name="카카오페이손해보험", code="KAKAOPAY", official_url="https://kakaopayinscorp.co.kr",
            product_name="해외여행보험", product_code="KAKAOPAY-OVERSEAS", channel="다이렉트(카카오톡/카카오페이)",
            sale_start=dt.date(2024, 11, 1), collected_at=dt.date(2026, 7, 29),
            version_label="20241101", effective_date=dt.date(2024, 11, 1),
            source_url="https://static.kakaoinsure.com/notilus/files/20241101_해외여행보험 약관.pdf",
            file_hash="d9e33fa75a75ec284cb35f4880ae6735693fcf0081bb601867ddc21001742cfb",
        )
        if insurer is None:
            print("이미 시드됨 (KAKAOPAY). 스킵합니다.")
            return

        std = seed_common_coverage_std(db)
        std_death_injury, std_ovs_inj_med, std_rescue = std["DEATH_INJURY"], std["OVS_INJ_MED"], std["RESCUE"]

        cov_death_injury = Coverage(
            policy_version_id=pv.policy_version_id, coverage_std_id=std_death_injury.coverage_std_id,
            raw_name="상해사망·후유장해 (보통약관)",
            definition=(
                "회사는 피보험자가 보험증권에 기재된 여행을 목적으로 주거지를 출발하여 여행을 마치고 "
                "주거지에 도착할 때까지의 여행도중에 다음 중 어느 하나의 사유가 발생한 경우에는 보험수익자에게 "
                "약정한 보험금을 지급합니다. 1. 보험기간 중에 상해의 직접결과로써 사망한 경우(질병으로 인한 "
                "사망은 제외합니다): 사망보험금 2. 보험기간 중 상해로 장해분류표([별표1]참조)에서 정한 각 "
                "장해지급률에 해당하는 장해상태가 되었을 때: 후유장해보험금"
            ),
            limit_amount="가입금액 한도 (증권 기재 보험가입금액)",
            deductible=None,
            waiting_condition="장해지급률 미확정 시 상해 발생일부터 180일 시점 진단 기준",
        )
        cov_ovs_inj_med = Coverage(
            policy_version_id=pv.policy_version_id, coverage_std_id=std_ovs_inj_med.coverage_std_id,
            raw_name="해외여행 실손의료비 특별약관 - (1)상해 해외의료비",
            definition=(
                "회사는 피보험자가 보험증권에 기재된 해외여행 중에 상해를 입고, 이로 인해 해외의료기관에서 "
                "의사(치료받는 국가의 법에서 정한 병원 및 의사의 자격을 가진 자에 한함)의 치료를 받은 때에는 "
                "보험가입금액을 한도로 피보험자가 실제 부담한 의료비 전액을 보상합니다."
            ),
            limit_amount="보험가입금액 한도, 실제 부담 의료비 전액 (척추지압술·침술은 건당 US$1,000 한도). "
                         "2025년 보도자료 기준 의료비 최대 1억원까지 보장 확대(플랜별 상이, 원문 별도 확인 필요)",
            deductible="가입 플랜별 상이",
            waiting_condition="보험기간 종료 후에도 종료일부터 180일까지 계속 치료 시 보상",
        )
        cov_rescue = Coverage(
            policy_version_id=pv.policy_version_id, coverage_std_id=std_rescue.coverage_std_id,
            raw_name="해외여행중 중대사고 구조/송환비용 특별약관",
            definition=(
                "회사는 해외여행 중 피보험자가 탑승한 항공기·선박의 행방불명·조난, 산악등반 중 조난, "
                "긴급수색구조가 필요한 사고(경찰 등 공공기관 확인), 상해의 직접결과로 사망 또는 회사가 정한 "
                "일수(14일/7일/4일 중 선택) 이상 계속 입원, 질병을 직접원인으로 한 사망·약정 일수 이상 입원 시 "
                "수색구조비용·구원자 교통비·숙박비·이송비용·제잡비를 보상합니다."
            ),
            limit_amount="보험가입금액 한도 (구원자 교통비 2명분, 숙박비 1인당 14박분 한도, 제잡비 10만원 한도)",
            deductible="청약 시 선택(자기부담률 없음/10%/20%, 10만원 공제 후 적용)",
            waiting_condition="입원의 경우 계약자가 청약 시 선택한 일수(14일/7일/4일) 이상 계속 입원 필요",
        )
        db.add_all([cov_death_injury, cov_ovs_inj_med, cov_rescue])
        db.flush()

        clauses = [
            Clause(
                policy_version_id=pv.policy_version_id, coverage_id=cov_death_injury.coverage_id,
                clause_type="보장정의", article_no="제3조(보험금의 지급사유)",
                text=(
                    "회사는 피보험자가 보험증권에 기재된 여행을 목적으로 주거지를 출발하여 여행을 마치고 "
                    "주거지에 도착할 때까지의 여행도중에 다음 중 어느 하나의 사유가 발생한 경우에는 보험수익자에게 "
                    "약정한 보험금을 지급합니다. 1. 보험기간 중에 상해의 직접결과로써 사망한 경우(질병으로 인한 "
                    "사망은 제외합니다): 사망보험금 2. 보험기간 중 상해로 장해분류표([별표1]참조)에서 정한 각 "
                    "장해지급률에 해당하는 장해상태가 되었을 때: 후유장해보험금"
                ),
                page_ref="p.16-17", embedding_id=None, default_color="파랑",
            ),
            Clause(
                policy_version_id=pv.policy_version_id, coverage_id=cov_death_injury.coverage_id,
                clause_type="면책", article_no="제5조(보험금을 지급하지 않는 사유)",
                text=(
                    "① 회사는 다음 중 어느 한가지로 보험금 지급사유가 발생한 때에는 보험금을 지급하지 않습니다. "
                    "1. 피보험자가 고의로 자신을 해친 경우(심신상실 등 예외 있음) 2. 보험수익자가 고의로 피보험자를 "
                    "해친 경우 3. 계약자가 고의로 피보험자를 해친 경우 4. 피보험자의 임신, 출산(제왕절개 포함), "
                    "산후기 5. 전쟁, 외국의 무력행사, 혁명, 내란, 사변, 폭동 ② 전문등반, 글라이더 조종, 스카이다이빙, "
                    "스쿠버다이빙, 행글라이딩, 수상보트, 패러글라이딩 등 직업·직무·동호회 활동 목적의 위험 행위로 "
                    "인한 상해는 다른 약정이 없으면 보장하지 않습니다."
                ),
                page_ref="p.18-19", embedding_id=None, default_color="빨강",
            ),
            Clause(
                policy_version_id=pv.policy_version_id, coverage_id=None,
                clause_type="서류", article_no="제7조(보험금의 청구)",
                text=(
                    "① 보험수익자는 다음의 서류를 제출하고 보험금을 청구하여야 합니다. 1. 보험금 청구서(회사 양식) "
                    "2. 사고증명서(진료비계산서, 사망진단서, 장해진단서, 입원치료확인서, 의사처방전(처방조제비)등) "
                    "3. 신분증(주민등록증이나 운전면허증 등 사진이 붙은 정부기관발행 신분증, 본인이 아닌 경우에는 "
                    "본인의 인감증명서 또는 본인서명사실확인서 포함) 4. 기타 보험수익자가 보험금의 수령에 필요하여 "
                    "제출하는 서류 ② 사고증명서는 의료법 제3조(의료기관)에서 규정한 국내의 병원이나 의원 또는 "
                    "국외의 의료관련법에서 정한 의료기관에서 발급한 것이어야 합니다."
                ),
                page_ref="p.19", embedding_id=None, default_color="노랑",
            ),
            Clause(
                policy_version_id=pv.policy_version_id, coverage_id=cov_ovs_inj_med.coverage_id,
                clause_type="보장정의", article_no="제3조(보장종목별 보상내용) (1)상해-해외의료비",
                text=(
                    "① 회사는 피보험자가 보험증권에 기재된 해외여행 중에 상해를 입고, 이로 인해 해외의료기관에서 "
                    "의사(치료받는 국가의 법에서 정한 병원 및 의사의 자격을 가진 자에 한함)의 치료를 받은 때에는 "
                    "보험가입금액을 한도로 피보험자가 실제 부담한 의료비 전액을 보상합니다. ② 척추지압술이나 "
                    "침술 치료로 인한 의료비는 하나의 상해에 대하여 US $1,000.00 한도로 보상합니다. ③ 유독가스 "
                    "또는 유독물질을 우연히 일시에 흡입·흡수·섭취한 결과로 생긴 중독증상이 포함됩니다. ④ 보험기간 "
                    "종료일부터 180일까지(종료일 제외) 계속 치료 시 보상합니다."
                ),
                page_ref="p.41-42", embedding_id=None, default_color="파랑",
            ),
            Clause(
                policy_version_id=pv.policy_version_id, coverage_id=cov_rescue.coverage_id,
                clause_type="보장정의", article_no="제1조(보험금의 지급사유)~제2조(중대사고 구조송환비용의 범위)",
                text=(
                    "① 회사는 해외여행 중에 피보험자가 탑승한 항공기 또는 선박이 행방불명 또는 조난된 경우, "
                    "산악등반 중 조난된 경우, 급격하고도 우연한 외래의 사고로 긴급수색구조 등이 필요한 상태로 된 것이 "
                    "경찰 등 공공기관에 의해 확인된 경우, 보통약관 제3조의 상해의 직접결과로써 사망하거나 회사가 "
                    "정한 일수(14일/7일/4일 중 계약자 선택) 이상 계속 입원한 경우, 질병을 직접원인으로 해외여행 중 "
                    "사망 또는 약정 일수 이상 입원한 경우에 비용을 보상합니다. 비용의 범위: 1.수색구조비용 "
                    "2.항공운임 등 교통비(구원자 2명분 한도) 3.숙박비(구원자 2명분, 1인당 14박분 한도) 4.이송비용 "
                    "5.제잡비(10만원 한도)"
                ),
                page_ref="p.127-128", embedding_id=None, default_color="파랑",
            ),
            Clause(
                policy_version_id=pv.policy_version_id, coverage_id=cov_rescue.coverage_id,
                clause_type="면책", article_no="제3조(보험금을 지급하지 않는 사유)",
                text=(
                    "회사는 보통약관 제5조(보험금을 지급하지 않는 사유) 제1항 제1호 내지 제3호, 제5호에 의하여 "
                    "보험금 지급사유가 발생한 때에는 보험금을 지급하지 않습니다. (제5호=전쟁·무력행사·혁명·내란·"
                    "사변·폭동까지 명시 — 삼성화재는 제1~3호만 배제하여 카카오페이보다 면책범위가 좁음)"
                ),
                page_ref="p.128", embedding_id=None, default_color="빨강",
            ),
            Clause(
                policy_version_id=pv.policy_version_id, coverage_id=cov_rescue.coverage_id,
                clause_type="조건", article_no="제6조(자기부담금 및 보상한도액)",
                text=(
                    "① 회사는 1사고당 또는 1질병당 계약자가 청약할 때 선택한 자기부담률(자기부담률 없음 / "
                    "10만원 공제 후 10% / 10만원 공제 후 20%)을 적용하여 자기부담금을 계산합니다. "
                    "② 회사가 지급할 보험금은 보험기간을 통하여 이 특별약관의 보험가입금액을 한도로 합니다."
                ),
                page_ref="p.129", embedding_id=None, default_color="노랑",
            ),
        ]
        db.add_all(clauses)
        db.flush()
        clause_by_article = {c.article_no: c for c in clauses}
        common_doc_clause = clause_by_article["제7조(보험금의 청구)"]

        docs_map = seed_common_doc_std(db)

        doc_maps = [
            CoverageDocMap(coverage_id=cov_death_injury.coverage_id, required_doc_std_id=docs_map["CLAIM_FORM"].required_doc_std_id, is_mandatory=True, clause_id=common_doc_clause.clause_id),
            CoverageDocMap(coverage_id=cov_death_injury.coverage_id, required_doc_std_id=docs_map["DEATH_CERT"].required_doc_std_id, is_mandatory=True, clause_id=common_doc_clause.clause_id),
            CoverageDocMap(coverage_id=cov_death_injury.coverage_id, required_doc_std_id=docs_map["DISABILITY_CERT"].required_doc_std_id, is_mandatory=False, clause_id=common_doc_clause.clause_id),
            CoverageDocMap(coverage_id=cov_death_injury.coverage_id, required_doc_std_id=docs_map["ID_CARD"].required_doc_std_id, is_mandatory=True, clause_id=common_doc_clause.clause_id),

            CoverageDocMap(coverage_id=cov_ovs_inj_med.coverage_id, required_doc_std_id=docs_map["CLAIM_FORM"].required_doc_std_id, is_mandatory=True, clause_id=common_doc_clause.clause_id),
            CoverageDocMap(coverage_id=cov_ovs_inj_med.coverage_id, required_doc_std_id=docs_map["MEDICAL_EXPENSE_CERT"].required_doc_std_id, is_mandatory=True, clause_id=common_doc_clause.clause_id),
            CoverageDocMap(coverage_id=cov_ovs_inj_med.coverage_id, required_doc_std_id=docs_map["TREATMENT_CERT"].required_doc_std_id, is_mandatory=False, clause_id=common_doc_clause.clause_id),
            CoverageDocMap(coverage_id=cov_ovs_inj_med.coverage_id, required_doc_std_id=docs_map["PRESCRIPTION"].required_doc_std_id, is_mandatory=False, clause_id=common_doc_clause.clause_id),
            CoverageDocMap(coverage_id=cov_ovs_inj_med.coverage_id, required_doc_std_id=docs_map["ID_CARD"].required_doc_std_id, is_mandatory=True, clause_id=common_doc_clause.clause_id),

            CoverageDocMap(coverage_id=cov_rescue.coverage_id, required_doc_std_id=docs_map["CLAIM_FORM"].required_doc_std_id, is_mandatory=False, clause_id=common_doc_clause.clause_id),
            CoverageDocMap(coverage_id=cov_rescue.coverage_id, required_doc_std_id=docs_map["ID_CARD"].required_doc_std_id, is_mandatory=False, clause_id=common_doc_clause.clause_id),
        ]
        db.add_all(doc_maps)

        db.commit()
        print(f"카카오페이손해보험 KB 시드 완료: coverage=3, clause={len(clauses)}, coverage_doc_map={len(doc_maps)}")
    finally:
        db.close()


if __name__ == "__main__":
    run()
