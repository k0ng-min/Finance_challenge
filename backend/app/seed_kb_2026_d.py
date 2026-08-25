"""
KB해외여행보험 2026년판 청크 D (p.170-286)

원문 출처: backend/data/processed/kb_overseas_26-15505-1_full_text.txt (페이지 170-286)

## 포함된 특약 및 조항
- p.170+: 기본형 해외여행 실손의료비(급여) 특별약관
  * 제3조(보장종목별 보상내용) — 4개 조항 (상해/질병, 해외/국내)
  * 제4조(보상하지 않는 사항) — 면책 조항
  * 제5조(보험가입금액 한도 등) — 지급한도 및 자기부담금

- 중증/비중증 비급여 실손의료비 추가특별약관 (건너뜸 — 청구절차 세부)
- 국민건강보험 미가입자 추가특별약관 (건너뜸 — 청구절차 세부)
- 장애인전용보험전환 특별약관 (건너뜸 — 계약행정)

## 추출 전략 (다른 보험사와 동일 수준)
다른 5개 보험사(삼성/현대/메리츠/DB/카카오) 모두 실손의료비 특약을 상세히 추출했으므로,
KB도 동일하게:
1. 상해의료비(해외) — 보장정의
2. 질병의료비(해외) — 보장정의
3. 면책사유 — 고의·임신·정신질환·전쟁 등
4. 지급한도·자기부담금·본인부담금 상한제 — 핵심 금액

를 추출합니다.

## 건너뜀 — 청구 절차 세부 (범위 밖)
다음은 "확인함 무관" (담보 자체 제외)이 아니라, "건너뜸" (담보는 있지만 청구절차는 범위 밖):
- 비급여 의료비 추가특약의 세부 기준 (비급여 기준표 인용)
- 국민건강보험 미가입자 청구 절차
- 건강보험심사평가원 진료비확인요청제도
- 보험금 심사·가지급·이자 관련 세부 절차
- 중증도 분류 및 심사위원회 운영

CoverageStd 재사용:
- OVS_INJ_MED (해외발생 상해의료비)
- OVS_ILL_MED (해외발생 질병의료비)

멱등성: Coverage/Clause는 조회 후 중복 검사 (이미 있으면 건너뜀).
"""
from app.database import SessionLocal
from app import models  # noqa: F401
from app.models.kb import Clause, Coverage, Product, PolicyVersion
from app.services.kb_seed_common import get_or_create_coverage_std

PRODUCT_CODE = "KB-OVERSEAS-2026"
VERSION_LABEL = "일반26-15505-1"


def run():
    db = SessionLocal()
    try:
        # Product/PolicyVersion 조회 (a.py에서 이미 생성됨)
        product = db.query(Product).filter(
            Product.product_code == PRODUCT_CODE
        ).first()
        if not product:
            print(f"Product {PRODUCT_CODE} not found. Run seed_kb_2026_a.py first.")
            return

        pv = db.query(PolicyVersion).filter(
            PolicyVersion.product_id == product.product_id,
            PolicyVersion.version_label == VERSION_LABEL
        ).first()
        if not pv:
            print(f"PolicyVersion {VERSION_LABEL} not found.")
            return

        # ===== 기본형 해외여행 실손의료비(급여) 특별약관 =====
        # CoverageStd 재사용
        ovs_inj_med = get_or_create_coverage_std(
            db, "OVS_INJ_MED", "해외발생 상해의료비", "의료비", True
        )
        ovs_ill_med = get_or_create_coverage_std(
            db, "OVS_ILL_MED", "해외발생 질병의료비", "의료비", True
        )

        # Coverage: 해외발생 상해의료비
        cov_ovs_inj = db.query(Coverage).filter(
            Coverage.policy_version_id == pv.policy_version_id,
            Coverage.raw_name == "해외발생 상해의료비"
        ).first()
        if not cov_ovs_inj:
            cov_ovs_inj = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=ovs_inj_med.coverage_std_id,
                raw_name="해외발생 상해의료비",
            )
            db.add(cov_ovs_inj)
            db.flush()

        # Clause: 제3조(1) 해외 상해의료비 지급사유
        clause_text = (
            "회사는 피보험자가 보험증권에 기재된 해외여행 중에 상해를 입고, "
            "이로 인해 해외의료기관에서 의사(치료받는 국가의 법에서 정한 병원 및 의사의 자격을 가진 자)의 치료를 받은 때에는 "
            "보험가입금액을 한도로 피보험자가 실제 부담한 의료비 전액을 보상합니다. "
            "다만, 척추지압술(Chiroparactic, 추나요법 등)이나 침술(부항, 뜸 포함) 치료로 인한 의료비는 "
            "치료받는 국가의 법에서 정한 병원 및 의사의 자격을 가진자에 의하여 치료를 받은 경우에 한하며, "
            "하나의 상해에 대하여 US $1,000.00 한도로 보상합니다."
        )
        existing = db.query(Clause).filter(
            Clause.policy_version_id == pv.policy_version_id,
            Clause.coverage_id == cov_ovs_inj.coverage_id,
            Clause.article_no == "제3조(보장종목별 보상내용) ①",
            Clause.text == clause_text
        ).first()
        if not existing:
            db.add(Clause(
                policy_version_id=pv.policy_version_id,
                coverage_id=cov_ovs_inj.coverage_id,
                clause_type="보장정의",
                article_no="제3조(보장종목별 보상내용) ①",
                text=clause_text,
                page_ref="p.170",
                default_color="파랑",
            ))

        # Coverage: 해외발생 질병의료비
        cov_ovs_ill = db.query(Coverage).filter(
            Coverage.policy_version_id == pv.policy_version_id,
            Coverage.raw_name == "해외발생 질병의료비"
        ).first()
        if not cov_ovs_ill:
            cov_ovs_ill = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=ovs_ill_med.coverage_std_id,
                raw_name="해외발생 질병의료비",
            )
            db.add(cov_ovs_ill)
            db.flush()

        # Clause: 제3조(2) 해외 질병의료비 지급사유
        clause_text = (
            "회사는 피보험자가 보험증권에 기재된 해외여행 중에 질병으로 인하여 "
            "해외의료기관에서 의사(치료받는 국가의 법에서 정한 병원 및 의사의 자격을 가진 자)의 치료를 받은 때에는 "
            "보험가입금액을 한도로 피보험자가 실제 부담한 의료비 전액을 보상합니다. "
            "다만, 척추지압술(Chiroparactic, 추나요법 등)이나 침술(부항, 뜸 포함) 치료로 인한 의료비는 "
            "치료받는 국가의 법에서 정한 병원 및 의사의 자격을 가진자에 의하여 치료를 받은 경우에 한하며, "
            "하나의 질병에 대하여 US $1,000.00 한도로 보상합니다."
        )
        existing = db.query(Clause).filter(
            Clause.policy_version_id == pv.policy_version_id,
            Clause.coverage_id == cov_ovs_ill.coverage_id,
            Clause.article_no == "제3조(보장종목별 보상내용) ②",
            Clause.text == clause_text
        ).first()
        if not existing:
            db.add(Clause(
                policy_version_id=pv.policy_version_id,
                coverage_id=cov_ovs_ill.coverage_id,
                clause_type="보장정의",
                article_no="제3조(보장종목별 보상내용) ②",
                text=clause_text,
                page_ref="p.171",
                default_color="파랑",
            ))

        # Clause: 제4조 상해의료비 면책사유
        clause_text = (
            "회사는 다음의 사유로 인하여 생긴 의료비는 보상하지 않습니다.\n"
            "1. 피보험자가 고의로 자신을 해친 경우. 다만, 피보험자가 심신상실 등으로 자유로운 의사결정을 할 수 없는 상태에서 자신을 해친 사실이 증명된 경우에는 보상합니다.\n"
            "2. 보험수익자가 고의로 피보험자를 해친 경우. 다만, 그 보험수익자가 보험금의 일부 보험수익자인 경우에는 다른 보험수익자에 대한 보험금은 지급합니다.\n"
            "3. 계약자가 고의로 피보험자를 해친 경우\n"
            "4. 피보험자가 임신, 출산(제왕절개를 포함합니다), 산후기로 치료한 경우. 다만 회사가 보상하는 상해로 인한 경우에는 보상합니다.\n"
            "5. 전쟁, 외국의 무력행사, 혁명, 내란, 사변, 폭동으로 인한 경우\n"
            "6. 피보험자가 정당한 이유 없이 입원기간 중 의사의 지시를 따르지 않거나 의사가 통원치료가 가능하다고 인정함에도 피보험자 본인이 자의적으로 입원하여 발생한 입원의료비\n"
            "7. 피보험자가 정당한 이유 없이 통원기간 중 의사의 지시를 따르지 않아 발생한 통원의료비"
        )
        existing = db.query(Clause).filter(
            Clause.policy_version_id == pv.policy_version_id,
            Clause.coverage_id == cov_ovs_inj.coverage_id,
            Clause.article_no == "제4조(보상하지 않는 사항) 상해",
            Clause.text == clause_text
        ).first()
        if not existing:
            db.add(Clause(
                policy_version_id=pv.policy_version_id,
                coverage_id=cov_ovs_inj.coverage_id,
                clause_type="면책",
                article_no="제4조(보상하지 않는 사항) 상해",
                text=clause_text,
                page_ref="p.173",
                default_color="빨강",
            ))

        # Clause: 제4조 질병의료비 면책사유
        clause_text = (
            "회사는 아래의 사유를 원인으로 하여 생긴 의료비는 보상하지 않습니다.\n"
            "1. 피보험자가 고의로 자신을 해친 경우. 다만, 피보험자가 심신상실 등으로 자유로운 의사결정을 할 수 없는 상태에서 자신을 해친 사실이 증명된 경우에는 보상합니다.\n"
            "2. 보험수익자가 고의로 피보험자를 해친 경우. 다만, 그 보험수익자가 보험금의 일부 보험수익자인 경우에는 다른 보험수익자에 대한 보험금은 지급합니다.\n"
            "3. 계약자가 고의로 피보험자를 해친 경우\n"
            "4. 피보험자가 정당한 이유 없이 입원기간 중 의사의 지시를 따르지 않거나 의사가 통원치료가 가능하다고 인정함에도 피보험자 본인이 자의적으로 입원하여 발생한 입원의료비\n"
            "5. 피보험자가 정당한 이유 없이 통원기간 중 의사의 지시를 따르지 않아 발생한 통원의료비\n"
            "또한, 회사는 한국표준질병사인분류에 있어서 정신 및 행동장애(F04~F99)와 "
            "여성생식기의 비염증성 장애로 인한 습관성 유산, 불임 및 인공수정관련 합병증(N96~N98), "
            "피보험자의 임신, 출산, 산후기(O00~O99)로 발생한 의료비는 보상하지 않습니다."
        )
        existing = db.query(Clause).filter(
            Clause.policy_version_id == pv.policy_version_id,
            Clause.coverage_id == cov_ovs_ill.coverage_id,
            Clause.article_no == "제4조(보상하지 않는 사항) 질병",
            Clause.text == clause_text
        ).first()
        if not existing:
            db.add(Clause(
                policy_version_id=pv.policy_version_id,
                coverage_id=cov_ovs_ill.coverage_id,
                clause_type="면책",
                article_no="제4조(보상하지 않는 사항) 질병",
                text=clause_text,
                page_ref="p.175-176",
                default_color="빨강",
            ))

        # Clause: 제5조 보험가입금액 한도 및 자기부담금
        clause_text = (
            "이 계약의 보험가입금액은 "
            "(1)상해의료비 해외, (2)질병의료비 해외의 경우 각각에 대하여 계약시 계약자가 선택한 금액, "
            "(1)상해의료비 국내(급여), (2)질병의료비 국내(급여)의 경우 연간 "
            "(1)상해의료비 국내(급여)에 대하여 입원과 통원의 보상금액을 합산하여 5천만원 이내에서, "
            "(2)질병의료비 국내(급여)에 대하여 입원과 통원의 보상금액을 합산하여 5천만원 이내에서 회사가 정한 금액 중 계약자가 선택한 금액을 말합니다. "
            "통원의 경우 1회당 20만원 이내에서 회사가 정한 금액 중 계약자가 선택한 금액의 한도 내에서 보상하며, "
            "입원의 경우 본인부담금 20%에 해당하는 금액이 연간 200만원을 초과하는 경우 그 초과금액은 보험가입금액 한도 내에서 보상합니다."
        )
        existing = db.query(Clause).filter(
            Clause.policy_version_id == pv.policy_version_id,
            Clause.coverage_id == cov_ovs_inj.coverage_id,
            Clause.article_no == "제5조(보험가입금액 한도 등)",
            Clause.text == clause_text
        ).first()
        if not existing:
            db.add(Clause(
                policy_version_id=pv.policy_version_id,
                coverage_id=cov_ovs_inj.coverage_id,
                clause_type="조건",
                article_no="제5조(보험가입금액 한도 등)",
                text=clause_text,
                page_ref="p.179-180",
                default_color="회색",
            ))

        db.commit()
        print("Seed completed for KB 2026 chunk D (p.170-286)")
        print(f"Extracted coverages: OVS_INJ_MED, OVS_ILL_MED")
        print(f"Extracted clauses: 4개 (보장정의 2, 면책 2)")
        print(f"Note: 비급여 추가특약, 미가입자 추가약관, 청구절차 세부는 건너뜸 — 범위 밖")

    finally:
        db.close()


if __name__ == "__main__":
    run()
