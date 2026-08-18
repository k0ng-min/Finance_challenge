"""
삼성화재(insurer.code="SAMSUNG") 2026년판 약관 청크 C.
backend/data/processed/samsung_overseas_2026_full_text.txt 페이지 77-181.

## 담당 범위

### 페이지 77-115 (기본형 해외여행 실손의료비 특별약관 - 상해의료비)
CoverageStd OVS_INJ_MED. 핵심 조항만:
- 제1조: 보장종목 (정의)
- 제3조: 보상내용 (보장정의) - 상해의료비
- 제4조: 보상하지 않는 사항 (면책)
- 제5조: 보험가입금액 한도 (제한)

### 페이지 116-150 (기본형 해외여행 실손의료비 특별약관 - 질병의료비)
CoverageStd OVS_ILL_MED. 핵심 조항만:
- 제3조: 보상내용 (보장정의) - 질병의료비
- 제4조: 보상하지 않는 사항 (면책)
- 제5조: 보험가입금액 한도 (제한)

### 페이지 144-148 (해외여행 비급여 실손의료비 특별약관1)
CoverageStd NON_COVERED_MED_INJ. 핵심 조항만:
- 제3조: 보상내용 (보장정의) - 상해비급여 (산정특례 제외 비급여 의료비)
- 제4조: 보상하지 않는 사항 (면책)

### 페이지 149-170 (해외여행 비급여 실손의료비 특별약관2 - 비중증 비급여)
CoverageStd NON_COVERED_MED_MRI. 핵심 조항만:
- 제1조: 보장종목 (정의) - 3개 보장종목 (상해비급여 국내, 질병비급여 국내, 자기공명영상진단)
- 제3조: 보상내용 (보장정의) - 자기공명영상진단 비급여
- 제4조: 보상하지 않는 사항 (면책)
"""

from app.database import SessionLocal
from app import models  # noqa: F401
from app.models.kb import Clause, Coverage, PolicyVersion, Product
from app.services.kb_seed_common import get_or_create_coverage_std

PRODUCT_CODE = "SAMSUNG-OVERSEAS-2026"
VERSION_LABEL = "2026수집본"


def run():
    """시드 함수. 멱등성: policy_version_id + text 조합이 있으면 스킵."""
    db = SessionLocal()
    try:
        # 기존 Product/PolicyVersion 조회
        product = db.query(Product).filter_by(product_code=PRODUCT_CODE).first()
        if not product:
            print("ERROR: Product not found. Run seed_samsung_2026_a.py first.")
            return

        policy_version = db.query(PolicyVersion).filter_by(
            product_id=product.product_id,
            version_label=VERSION_LABEL
        ).first()
        if not policy_version:
            print("ERROR: PolicyVersion not found. Run seed_samsung_2026_a.py first.")
            return

        # 이 청크가 이미 시드됐으면(Coverage 생성이 idempotent하지 않으므로) 통째로 건너뛴다.
        if db.query(Coverage).filter_by(
            policy_version_id=policy_version.policy_version_id,
            raw_name="기본형 해외여행 실손의료비 특별약관 - 상해의료비"
        ).first():
            print("삼성화재 2026년판 청크 C: 이미 시드됨, 건너뜀.")
            return

        # 1. 해외발생 상해의료비 (p.77-115)
        ovs_inj_med_std = get_or_create_coverage_std(
            db, "OVS_INJ_MED", "해외발생 상해의료비", "의료", False
        )

        coverage_ovs_inj = Coverage(
            policy_version_id=policy_version.policy_version_id,
            coverage_std_id=ovs_inj_med_std.coverage_std_id,
            raw_name="기본형 해외여행 실손의료비 특별약관 - 상해의료비",
            definition="해외여행 중 상해로 인한 의료비 실비 보상 (해외/국내 선택)",
            limit_amount=None,
            deductible=None,
            waiting_condition=None
        )
        db.add(coverage_ovs_inj)
        db.flush()

        # Clause: 제1조 (보장종목)
        clause_c1_text = (
            "회사는 기본형 해외여행 실손의료비 특별약관을 상해의료비형, 질병의료비형 등 "
            "2가지 이내의 보장종목으로 구성하며, 계약자는 이들 2개 보장종목 중 한 가지 이상을 "
            "선택하여 가입할 수 있습니다. 또한, 세부구성항목의 해외 및 국내(급여)의료비도 선택하여 "
            "가입할 수 있습니다. "
            "보장 세부 구성: "
            "상해의료비 해외: 피보험자가 해외여행 중에 입은 상해로 인하여 해외의료기관에서 의료비가 "
            "발생한 경우에 보상 "
            "상해의료비 국내(급여): 피보험자가 해외여행 중에 입은 상해로 인하여 의료기관에 입원 또는 "
            "통원하여 급여치료를 받거나 급여 처방조제를 받은 경우에 보상"
        )
        if not db.query(Clause).filter_by(
            policy_version_id=policy_version.policy_version_id,
            text=clause_c1_text
        ).first():
            db.add(Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=coverage_ovs_inj.coverage_id,
                clause_type="보장정의",
                article_no="[기본형 해외여행 실손의료비 특별약관] 제1조(보장종목)",
                text=clause_c1_text,
                page_ref="p.77",
                default_color="파랑"
            ))

        # Clause: 제3조 - 상해의료비 보상내용
        clause_c3_inj_text = (
            "① 회사는 피보험자가 보험증권에 기재된 해외여행 중에 상해를 입고, 이로 인해 해외의료기관에서 "
            "의사(치료받는 국가의 법에서 정한 병원 및 의사의 자격을 가진 자에 한함)의 치료를 받은 때에는 "
            "보험가입금액을 한도로 피보험자가 실제 부담한 의료비 전액을 보상합니다. "
            "② 제1항에도 불구하고 척추지압술(Chiropractic, 추나요법 등)이나 침술(부항, 뜸 포함) 치료로 인한 "
            "의료비는 치료받는 국가의 법에서 정한 병원 및 의사의 면허를 가진 자에 의하여 치료를 받은 경우에 "
            "한하며, 하나의 상해에 대하여 US $1,000.00 한도로 보상합니다. "
            "③ 제1항의 상해에는 유독가스 또는 유독물질을 우연히 일시에 흡입, 흡수 또는 섭취한 결과로 생긴 "
            "중독증상이 포함됩니다. 다만, 유독가스 또는 유독물질을 상습적으로 흡입, 흡수 또는 섭취한 결과로 "
            "생긴 중독증상과 세균성 음식물 중독증상은 포함되지 않습니다. "
            "④ 해외여행 중에 피보험자가 입은 상해로 인해 치료를 받던 중 보험기간이 끝났을 경우에는 "
            "보험기간 종료일부터 180일까지(보험기간 종료일은 제외합니다) 보상합니다."
        )
        if not db.query(Clause).filter_by(
            policy_version_id=policy_version.policy_version_id,
            text=clause_c3_inj_text
        ).first():
            db.add(Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=coverage_ovs_inj.coverage_id,
                clause_type="보장정의",
                article_no="[기본형 해외여행 실손의료비 특별약관] 제3조(보장종목별 보상내용) - 상해의료비",
                text=clause_c3_inj_text,
                page_ref="p.77-78",
                default_color="파랑"
            ))

        # Clause: 제4조 - 상해의료비 면책
        clause_c4_inj_text = (
            "회사는 다음의 사유로 인하여 생긴 의료비는 보상하지 않습니다. "
            "① 1. 피보험자가 고의로 자신을 해친 경우. 다만, 피보험자가 심신상실 등으로 자유로운 의사결정을 "
            "할 수 없는 상태에서 자신을 해친 사실이 증명된 경우에는 보상합니다. "
            "2. 보험수익자가 고의로 피보험자를 해친 경우. 다만, 그 보험수익자가 보험금의 일부 보험수익자인 "
            "경우에는 다른 보험수익자에 대한 보험금은 지급합니다. "
            "3. 계약자가 고의로 피보험자를 해친 경우 "
            "4. 피보험자가 임신, 출산(제왕절개를 포함합니다), 산후기로 치료한 경우. 다만 회사가 보상하는 상해로 "
            "인한 경우에는 보상합니다. "
            "5. 전쟁, 외국의 무력행사, 혁명, 내란, 사변, 폭동으로 인한 경우 "
            "6. 피보험자가 정당한 이유 없이 입원기간 중 의사의 지시를 따르지 않거나 의사가 통원치료가 가능하다고 "
            "인정함에도 피보험자 본인이 자의적으로 입원하여 발생한 입원의료비 "
            "7. 피보험자가 정당한 이유 없이 통원기간 중 의사의 지시를 따르지 않아 발생한 통원의료비"
        )
        if not db.query(Clause).filter_by(
            policy_version_id=policy_version.policy_version_id,
            text=clause_c4_inj_text
        ).first():
            db.add(Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=coverage_ovs_inj.coverage_id,
                clause_type="면책",
                article_no="[기본형 해외여행 실손의료비 특별약관] 제4조(보상하지 않는 사항) - 상해",
                text=clause_c4_inj_text,
                page_ref="p.79-80",
                default_color="빨강"
            ))

        # Clause: 제5조 - 보험가입금액 한도
        clause_c5_text = (
            "① 이 계약의 보험가입금액은 (1)상해의료비 해외, (2)질병의료비 해외의 경우 각각에 대하여 계약시 "
            "계약자가 선택한 금액, (1)상해의료비 국내(급여), (2)질병의료비 국내(급여)의 경우 연간 (1)상해의료비 "
            "국내(급여)에 대하여 입원과 통원의 보상금액을 합산하여 5천만원 이내에서, (2)질병의료비 국내(급여)에 "
            "대하여 입원과 통원의 보상금액을 합산하여 5천만원 이내에서 회사가 정한 금액 중 계약자가 선택한 금액을 "
            "말하며, 제3조(보장종목별 보상내용)에 의한 의료비를 이 금액 한도 내에서 보상합니다."
        )
        if not db.query(Clause).filter_by(
            policy_version_id=policy_version.policy_version_id,
            text=clause_c5_text
        ).first():
            db.add(Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=coverage_ovs_inj.coverage_id,
                clause_type="제한",
                article_no="[기본형 해외여행 실손의료비 특별약관] 제5조(보험가입금액 한도 등)",
                text=clause_c5_text,
                page_ref="p.84",
                default_color="초록"
            ))

        # 2. 해외발생 질병의료비 (p.116-150)
        ovs_ill_med_std = get_or_create_coverage_std(
            db, "OVS_ILL_MED", "해외발생 질병의료비", "의료", False
        )

        coverage_ovs_ill = Coverage(
            policy_version_id=policy_version.policy_version_id,
            coverage_std_id=ovs_ill_med_std.coverage_std_id,
            raw_name="기본형 해외여행 실손의료비 특별약관 - 질병의료비",
            definition="해외여행 중 질병으로 인한 의료비 실비 보상 (해외/국내 선택)",
            limit_amount=None,
            deductible=None,
            waiting_condition=None
        )
        db.add(coverage_ovs_ill)
        db.flush()

        # Clause: 제3조 - 질병의료비 보상내용
        clause_c3_ill_text = (
            "① 회사는 피보험자가 보험증권에 기재된 해외여행 중에 질병으로 인하여 해외의료기관에서 "
            "의사(치료받는 국가의 법에서 정한 병원 및 의사의 자격을 가진 자에 한함)의 치료를 받은 때에는 "
            "보험가입금액을 한도로 피보험자가 실제 부담한 의료비 전액을 보상합니다. "
            "② 제1항에도 불구하고 척추지압술(Chiropractic, 추나요법 등)이나 침술(부항, 뜸 포함) 치료로 인한 "
            "의료비는 치료받는 국가의 법에서 정한 병원 및 의사의 면허를 가진 자에 의하여 치료를 받은 경우에 "
            "한하며, 하나의 질병에 대하여 US $1,000.00 한도로 보상합니다. "
            "③ 해외여행 중에 피보험자가 제1항의 질병으로 인해 치료를 받던 중 보험기간이 끝났을 경우에는 "
            "보험기간 종료일부터 180일까지(보험기간 종료일은 제외합니다) 보상합니다."
        )
        if not db.query(Clause).filter_by(
            policy_version_id=policy_version.policy_version_id,
            text=clause_c3_ill_text
        ).first():
            db.add(Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=coverage_ovs_ill.coverage_id,
                clause_type="보장정의",
                article_no="[기본형 해외여행 실손의료비 특별약관] 제3조(보장종목별 보상내용) - 질병의료비",
                text=clause_c3_ill_text,
                page_ref="p.79-80",
                default_color="파랑"
            ))

        # Clause: 제4조 - 질병의료비 면책
        clause_c4_ill_text = (
            "① 회사는 아래의 사유를 원인으로 하여 생긴 의료비는 보상하지 않습니다. "
            "1. 피보험자가 고의로 자신을 해친 경우. 다만, 피보험자가 심신상실 등으로 자유로운 의사결정을 "
            "할 수 없는 상태에서 자신을 해친 사실이 증명된 경우에는 보상합니다. "
            "2. 보험수익자가 고의로 피보험자를 해친 경우. 다만, 그 보험수익자가 보험금의 일부 보험수익자인 "
            "경우에는 다른 보험수익자에 대한 보험금은 지급합니다. "
            "3. 계약자가 고의로 피보험자를 해친 경우 "
            "4. 피보험자가 정당한 이유 없이 입원기간 중 의사의 지시를 따르지 않거나 의사가 통원치료가 가능하다고 "
            "인정함에도 피보험자 본인이 자의적으로 입원하여 발생한 입원의료비 "
            "5. 피보험자가 정당한 이유 없이 통원기간 중 의사의 지시를 따르지 않아 발생한 통원의료비 "
            "② 회사는 한국표준질병사인분류에 있어서 아래의 의료비에 대하여는 보상하지 않습니다. "
            "1. 정신 및 행동장애(F04-F99) (다만, F04-F09, F20-F29, F30-F39, F40-F48, F51, F90-F98과 관련한 "
            "치료에서 발생한 요양급여에 해당하는 의료비는 보상) "
            "2. 여성생식기의 비염증성 장애로 인한 습관성 유산, 불임 및 인공수정관련 합병증(N96-N98) "
            "3. 피보험자의 임신, 출산(제왕절개를 포함합니다), 산후기(O00-O99)로 발생한 의료비"
        )
        if not db.query(Clause).filter_by(
            policy_version_id=policy_version.policy_version_id,
            text=clause_c4_ill_text
        ).first():
            db.add(Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=coverage_ovs_ill.coverage_id,
                clause_type="면책",
                article_no="[기본형 해외여행 실손의료비 특별약관] 제4조(보상하지 않는 사항) - 질병",
                text=clause_c4_ill_text,
                page_ref="p.79-82",
                default_color="빨강"
            ))

        # 3. 비급여 실손의료비 특별약관1 (p.144-148)
        noncov_inj_std = get_or_create_coverage_std(
            db, "NON_COVERED_MED_INJ", "비급여 상해의료비", "의료", False
        )

        coverage_nonc_inj = Coverage(
            policy_version_id=policy_version.policy_version_id,
            coverage_std_id=noncov_inj_std.coverage_std_id,
            raw_name="해외여행 비급여 실손의료비 특별약관1 - 상해비급여",
            definition="해외여행 중 상해로 인한 비급여 의료비 보상 (산정특례 대상질환 제외)",
            limit_amount=None,
            deductible=None,
            waiting_condition=None
        )
        db.add(coverage_nonc_inj)
        db.flush()

        # Clause: 특약1 제3조 상해비급여 보상
        clause_special1_inj_text = (
            "① 회사는 피보험자가 상해로 인하여 의료기관에 입원 또는 통원(외래 및 처방조제)하여 "
            "산정특례 대상 질환 외 치료를 받은 경우에는 비급여의료비(3대비급여는 제외)를 "
            "제5조(보험가입금액 한도 등)에서 정한 연간 보험가입금액의 한도 내에서 다음과 같이 보상합니다. "
            "입원(입원실료, 입원제비용, 입원수술비): 비급여 의료비의 50% (종합병원 제외 의료기관은 1회당 300만원 한도) "
            "상급병실료 차액: 비급여 병실료의 50% (1일 평균 10만원 한도) "
            "통원(외래제비용, 외래수술비, 처방조제비): 통원항목별 공제금액을 뺀 금액 (연간 100회 한도)"
        )
        if not db.query(Clause).filter_by(
            policy_version_id=policy_version.policy_version_id,
            text=clause_special1_inj_text
        ).first():
            db.add(Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=coverage_nonc_inj.coverage_id,
                clause_type="보장정의",
                article_no="[해외여행 비급여 실손의료비 특별약관1] 제3조(보장종목별 보상내용) - 상해비급여",
                text=clause_special1_inj_text,
                page_ref="p.153-154",
                default_color="파랑"
            ))

        # Clause: 특약1 제4조 상해비급여 면책
        clause_special1_inj_exempt_text = (
            "① 회사는 다음의 사유로 인하여 생긴 비급여 의료비는 보상하지 않습니다. "
            "1. 피보험자가 고의로 자신을 해친 경우 (다만 심신상실 등 증명 시 보상) "
            "2. 보험수익자가 고의로 피보험자를 해친 경우 (다만 일부 보험수익자는 다른 수익자 보상) "
            "3. 계약자가 고의로 피보험자를 해친 경우 "
            "4. 피보험자가 임신, 출산, 산후기로 입원 또는 통원한 경우 (다만 보상 상해로 인한 경우는 보상) "
            "5. 전쟁, 외국의 무력행사, 혁명, 내란, 사변, 폭동으로 인한 경우 "
            "6. 피보험자가 정당한 이유 없이 입원 또는 통원 기간 중 의사의 지시를 따르지 않은 경우 "
            "② 회사는 다른 약정이 없으면 피보험자가 직업·직무·동호회 활동 목적으로 전문등반, 글라이더, "
            "스카이다이빙, 스쿠버다이빙, 행글라이딩, 수상보트, 패러글라이딩, 모터보트, 자동차, 오토바이 경기·시범·행사 등으로 "
            "인한 상해에 대해 보상하지 않습니다. "
            "③ 회사는 다음의 비급여 의료비에 대해 보상하지 않습니다: 치과치료, 한방치료, 영양제, 비타민제, "
            "호르몬 투여, 의치·의수족, 진료와 무관한 비용, 자동차보험·산재보험 보상 의료비, 외국 의료기관 의료비 등"
        )
        if not db.query(Clause).filter_by(
            policy_version_id=policy_version.policy_version_id,
            text=clause_special1_inj_exempt_text
        ).first():
            db.add(Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=coverage_nonc_inj.coverage_id,
                clause_type="면책",
                article_no="[해외여행 비급여 실손의료비 특별약관1] 제4조(보상하지 않는 사항) - 상해비급여",
                text=clause_special1_inj_exempt_text,
                page_ref="p.160-161",
                default_color="빨강"
            ))

        # 4. 비급여 실손의료비 특별약관2 (p.149-170) - 자기공명영상진단
        nonc_mri_std = get_or_create_coverage_std(
            db, "NON_COVERED_MED_MRI", "자기공명영상진단 비급여", "의료", False
        )

        coverage_nonc_mri = Coverage(
            policy_version_id=policy_version.policy_version_id,
            coverage_std_id=nonc_mri_std.coverage_std_id,
            raw_name="해외여행 비급여 실손의료비 특별약관2 - 자기공명영상진단",
            definition="해외여행 중 상해·질병으로 인한 자기공명영상진단(MRI) 비급여 비용 보상",
            limit_amount=None,
            deductible=None,
            waiting_condition=None
        )
        db.add(coverage_nonc_mri)
        db.flush()

        # Clause: 특약2 제1조 보장종목
        clause_special2_title_text = (
            "회사가 판매하는 해외여행 비급여 실손의료비 특별약관2(이하 '특별약관2')는 상해 비급여형(국내), "
            "질병 비급여형(국내), 비급여 자기공명영상진단형(국내)의 3개 보장종목으로 구성되어 있습니다. "
            "[보장종목별 보상 내용] "
            "상해비급여(국내): 해외여행 중 상해로 인하여 의료기관에 입원 또는 통원하여 산정특례 대상 질환이 아닌 질환으로 인한 "
            "비급여 치료 또는 비급여 처방조제를 받은 경우에 보상(비급여 자기공명영상진단 제외) "
            "질병비급여(국내): 해외여행 중 질병으로 인하여 의료기관에 입원 또는 통원하여 산정특례 대상 질환이 아닌 질환으로 인한 "
            "비급여 치료 또는 비급여 처방조제를 받은 경우에 보상(비급여 자기공명영상진단 제외) "
            "비급여 자기공명영상진단(국내): 해외여행 중 입은 상해 또는 질병의 치료목적으로 의료기관에 입원 또는 통원하여 "
            "산정특례 대상 질환이 아닌 질환으로 인한 비급여 자기공명영상진단을 받은 경우에 보상"
        )
        if not db.query(Clause).filter_by(
            policy_version_id=policy_version.policy_version_id,
            text=clause_special2_title_text
        ).first():
            db.add(Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=coverage_nonc_mri.coverage_id,
                clause_type="보장정의",
                article_no="[해외여행 비급여 실손의료비 특별약관2] 제1조(보장종목)",
                text=clause_special2_title_text,
                page_ref="p.149-150",
                default_color="파랑"
            ))

        # Clause: 특약2 제3조③ 자기공명영상진단 보상
        clause_special2_mri_text = (
            "③ 회사는 피보험자가 이 특별약관2의 보험기간 중 산정특례 대상 질환 외 상해 또는 질병의 치료목적으로 "
            "의료기관에 입원 또는 통원하여 아래의 비급여 의료행위로 치료를 받은 경우에는 본인이 실제로 부담한 "
            "비급여의료비(행위료, 약제비, 치료재료대, 조영제, 판독료 포함)에서 공제금액을 뺀 금액을 아래의 보장한도 "
            "범위 내에서 각각 보상합니다. "
            "[자기공명영상진단] 공제금액: 1회당 5만원과 본인 비급여의료비의 50% 중 큰 금액. "
            "보장한도: 계약일 또는 매년 계약해당일부터 1년 단위로 각 상해·질병 치료행위를 합산하여 200만원"
        )
        if not db.query(Clause).filter_by(
            policy_version_id=policy_version.policy_version_id,
            text=clause_special2_mri_text
        ).first():
            db.add(Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=coverage_nonc_mri.coverage_id,
                clause_type="보장정의",
                article_no="[해외여행 비급여 실손의료비 특별약관2] 제3조(보장종목별 보상내용) - 자기공명영상진단",
                text=clause_special2_mri_text,
                page_ref="p.157-158",
                default_color="파랑"
            ))

        # Clause: 특약2 제4조③ 자기공명영상진단 면책
        clause_special2_mri_exempt_text = (
            "③ 회사는 한국표준질병사인분류에 따른 다음의 비급여 의료비에 대해서는 보상하지 않습니다. "
            "1. 정신 및 행동장애(F04∼F99) "
            "2. 여성생식기의 비염증성 장애로 인한 습관성 유산, 불임 및 인공수정관련 합병증(N96∼N98) "
            "3. 피보험자가 임신, 출산(제왕절개를 포함합니다), 산후기로 입원 또는 통원한 경우(O00∼O99). "
            "다만 회사가 보상하는 상해로 인하여 입원 또는 통원한 경우에는 보상합니다. "
            "4. 선천성 뇌질환(Q00∼Q04) "
            "5. 비만(E66) "
            "6. 요실금(N39.3, N39.4, R32) "
            "7. 직장 또는 항문 질환 중 국민건강보험법에 따른 요양급여에 해당하지 않는 부분(K60∼K62, K64)"
        )
        if not db.query(Clause).filter_by(
            policy_version_id=policy_version.policy_version_id,
            text=clause_special2_mri_exempt_text
        ).first():
            db.add(Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=coverage_nonc_mri.coverage_id,
                clause_type="면책",
                article_no="[해외여행 비급여 실손의료비 특별약관2] 제4조(보상하지 않는 사항) - 자기공명영상진단",
                text=clause_special2_mri_exempt_text,
                page_ref="p.165",
                default_color="빨강"
            ))

        db.commit()
        print("삼성화재 2026년판 청크 C 완료 (4개 담보, 14개 조항): OVS_INJ_MED, OVS_ILL_MED, NON_COVERED_MED_INJ, NON_COVERED_MED_MRI")

    finally:
        db.close()


if __name__ == "__main__":
    run()
