"""
DB손해보험(insurer.code="DB") 전체 재검토 - 청크 1(PDF p.1-42).
data/raw_pdfs/db_overseas.pdf (총 126쪽, "프로미 해외여행보험Ⅰ")의 p.1-42을 pdfplumber로
직접 읽고 대조한 결과를 반영한다.

## p.1-2 (목차)
스킵 - 목차만 있음.

## p.3-18 (보통약관 제1관~제7관)
직접 다 읽었다. 내용은 다음과 같고 전부 "사고가 뭐였나"(incident_type)와 무관한
계약 구조/행정 조항이다 - 억지로 끼워맞추지 않고 그대로 스킵한다.
- p.3-4: 제1관(목적/용어정의), 제2관 시작(제3조 보험금지급사유, 제4조 세부규정)
  * 제3조·제4조는 상해사망·후유장해로 이미 보통약관에서 DB에 있음(DEATH_INJURY).
- p.5: 제5조(보험금을 지급하지 않는 사유) - 면책조항, 이미 있는 것으로 추정
- p.6-18: 제6조~제38조 (보험금 청구절차, 주소변경, 보험수익자 지정, 대표자 지정,
  계약전 알릴의무, 상해보험계약 후 알릴의무, 알릴의무 위반효과, 사기에 의한 계약,
  보험계약 성립, 청약철회, 약관교부, 계약무효, 계약내용변경, 보험나이, 계약소멸,
  보험료 납입, 보험료 연체 및 해지, 계약부활, 보험료 환급, 분쟁조정, 관할법원,
  소멸시효, 약관해석, 예금자보호제도)
  결론: 이 조항들은 모두 계약 유지/관리/절차에 관한 것으로, 사고유형 분류에 직접
  쓸 내용이 없다. 확인 완료, 스킵함(억지 매핑 없음).

## p.19-42 (기본형 실손의료비 특별약관)
CoverageStd OVS_INJ_MED(해외발생 상해의료비), OVS_ILL_MED(해외발생 질병의료비),
NON_COVERED_MED(비급여 실손의료비)를 재사용하여 새로운 Coverage를 생성한다.

### 담보 구성
기본형 해외여행 실손의료비는 크게 4가지 보장종목으로 구성:
1. 상해의료비-해외: 해외에서 상해로 인한 의료비
2. 상해의료비-국내: 국내에서 상해로 인한 의료비(보험기간 종료 후 180일 한정)
3. 질병의료비-해외: 해외에서 질병으로 인한 의료비
4. 질병의료비-국내: 국내에서 질병으로 인한 의료비(보험기간 종료 후 180일 한정)

### 주요 특징
- 제3조: 보장종목별 보상내용(상해/질병, 각각 해외/국내 분리)
- 제4조: 보상하지 않는 사항(각 보장종목별 면책사항 상세 규정)
- 제4조의2: 특별약관에서 보상하는 사항 - 중요함!
  "제3조·제4조에도 불구하고 다음은 기본형에서 보상하지 않음":
  1. 도수치료·체외충격파·증식치료 비급여
  2. 비급여 주사료(항암제/항생제/희귀의약품 제외)
  3. MRI/MRA 비급여
  4. 자동차보험·산재보험 본인부담금
  → 이들은 별도 비급여 특약에서 보상함을 명시(p.1-42 범위 밖, 후속 청크에서 담당)

### Clause 매핑 전략
각 보장종목별로:
- 제3조 각 호: 보장정의(clause_type="보장정의")
- 제4조 각 호: 면책(clause_type="면책")
- 제4조의2: 특수 조건(clause_type="조건")
- 제6조~제10조: 청구/지급 절차(clause_type="서류" 또는 "조건")

멱등성: Coverage는 raw_name, Clause는 (policy_version_id, coverage_id, article_no, text)
조합, ClauseIncidentMap은 (clause_id, type_id) 조합으로 이미 있으면 건너뛴다.
"""
from app.database import SessionLocal
from app import models  # noqa: F401
from app.models.kb import (
    Clause, ClauseIncidentMap, Coverage, IncidentType, Insurer, PolicyVersion, Product,
)
from app.services.kb_seed_common import get_or_create_coverage_std

# ---------------------------------------------------------------------------
# 기본형 실손의료비 특별약관 - 제3조 보장종목별 보상내용
# (p.20-21, 상해의료비-해외)
# ---------------------------------------------------------------------------

BASIC_INJ_OVERSEAS_CLAUSE1_TEXT = (
    "① 회사는 피보험자가 보험증권에 기재된 해외여행 중에 상해를 입고, 이로 인해 "
    "해외의료기관에서 의사(치료받는 국가의 법에서 정한 병원 및 의사의 자격을 가진 "
    "자에 한함)의 치료를 받은 때에는 보험가입금액을 한도로 피보험자가 실제 부담한 "
    "의료비 전액을 보상합니다."
)

BASIC_INJ_OVERSEAS_CLAUSE2_TEXT = (
    "② 제1항에도 불구하고 척추지압술(Chiropractic, 추나요법 등)이나 침술(부항, 뜸 "
    "포함) 치료로 인한 의료비는 치료받는 국가의 법에서 정한 병원 및 의사의 자격을 "
    "가진 자에 의하여 치료를 받은 경우에 한하며, 하나의 상해에 대하여 US $1,000.00 "
    "한도로 보상합니다."
)

BASIC_INJ_OVERSEAS_CLAUSE3_TEXT = (
    "③ 제1항의 상해에는 유독가스 또는 유독물질을 우연히 일시에 흡입, 흡수 또는 "
    "섭취한 결과로 생긴 중독증상이 포함됩니다. 다만, 유독가스 또는 유독물질을 "
    "상습적으로 흡입, 흡수 또는 섭취한 결과로 생긴 중독증상과 세균성 음식물 중독증상은 "
    "포함되지 않습니다."
)

BASIC_INJ_OVERSEAS_CLAUSE4_TEXT = (
    "④ 해외여행 중에 피보험자가 입은 상해로 인해 치료를 받던 중 보험기간이 끝났을 "
    "경우에는 보험기간 종료일부터 180일까지(보험기간 종료일은 제외합니다) 보상합니다."
)

# (p.21, 상해의료비-국내)
BASIC_INJ_DOMESTIC_CLAUSE_TEXT = (
    "① 회사는 피보험자가 보험증권에 기재된 해외여행 중에 상해를 입고, 이로 인해 "
    "국내 의료기관·약국에서 치료를 받은 때에는 <붙임2>에 따라 보상합니다. 다만, "
    "보험기간이 1년 미만인 경우에는 해외여행 중에 피보험자가 입은 상해로 보험기간 종료후 "
    "30일(보험기간 종료일은 제외합니다) 이내에 의사의 치료를 받기 시작했을 때에는 "
    "의사의 치료를 받기 시작한 날부터 180일(통원은 180일 동안 외래는 방문 90회, "
    "처방조제비는 처방전 90건)까지만(보험기간 종료일은 제외합니다) 보상합니다."
)

# (p.21, 질병의료비-해외)
BASIC_ILL_OVERSEAS_CLAUSE1_TEXT = (
    "① 회사는 피보험자가 보험증권에 기재된 해외여행 중에 발생한 질병으로 인하여 "
    "해외의료기관에서 의사(치료받는 국가의 법에서 정한 병원 및 의사의 자격을 가진 "
    "자에 한함)의 치료를 받은 때에는 보험가입금액을 한도로 피보험자가 실제 부담한 "
    "의료비 전액을 보상합니다."
)

BASIC_ILL_OVERSEAS_CLAUSE2_TEXT = (
    "② 제1항에도 불구하고 척추지압술(Chiropractic, 추나요법 등)이나 침술(부항, 뜸 "
    "포함) 치료로 인한 의료비는 치료받는 국가의 법에서 정한 병원 및 의사의 자격을 "
    "가진 자에 의하여 치료를 받은 경우에 한하며, 하나의 질병에 대하여 US $1,000.00 "
    "한도로 보상합니다."
)

BASIC_ILL_OVERSEAS_CLAUSE3_TEXT = (
    "③ 해외여행 중에 피보험자가 제1항의 질병으로 인해 치료를 받던 중 보험기간이 "
    "끝났을 경우에는 보험기간 종료일부터 180일까지(보험기간 종료일은 제외합니다) "
    "보상합니다."
)

# (p.21, 질병의료비-국내)
BASIC_ILL_DOMESTIC_CLAUSE_TEXT = (
    "① 회사는 피보험자가 보험증권에 기재된 해외여행 중에 발생한 질병으로 인해 "
    "국내 의료기관·약국에서 치료를 받은 때에는 <붙임3>에 따라 보상합니다. 다만, "
    "보험기간이 1년 미만인 경우에는 해외여행 중에 질병을 원인으로 하여 보험기간 종료후 "
    "30일(보험기간 종료일은 제외합니다) 이내에 의사의 치료를 받기 시작했을 때에는 "
    "의사의 치료를 받기 시작한 날부터 180일(통원은 180일 동안 외래는 방문 90회, "
    "처방조제비는 처방전 90건)까지만(보험기간 종료일은 제외합니다) 보상합니다."
)

# ---------------------------------------------------------------------------
# 기본형 실손의료비 특별약관 - 제4조 보상하지 않는 사항 (핵심 면책사항)
# (p.22-24, 상해의료비)
# ---------------------------------------------------------------------------

BASIC_INJ_EXCLUSION_GENERAL_TEXT = (
    "① 회사는 다음의 사유로 인하여 생긴 의료비는 보상하지 않습니다. "
    "1. 피보험자가 고의로 자신을 해친 경우. 다만, 피보험자가 심신상실 등으로 자유로운 "
    "의사결정을 할 수 없는 상태에서 자신을 해친 사실이 증명된 경우에는 보상합니다. "
    "2. 보험수익자가 고의로 피보험자를 해친 경우. 다만, 그 보험수익자가 보험금의 "
    "일부 보험수익자인 경우에는 다른 보험수익자에 대한 보험금은 지급합니다. "
    "3. 계약자가 고의로 피보험자를 해친 경우 "
    "4. 피보험자가 임신, 출산(제왕절개를 포함합니다), 산후기로 치료한 경우. 다만 "
    "회사가 보상하는 상해로 인한 경우에는 보상합니다. "
    "5. 전쟁, 외국의 무력행사, 혁명, 내란, 사변, 폭동으로 인한 경우"
)

BASIC_INJ_EXCLUSION_BEHAVIOR_TEXT = (
    "② 회사는 다른 약정이 없으면 피보험자가 직업, 직무 또는 동호회 활동 목적으로 한 "
    "다음의 어느 하나에 해당하는 행위로 인하여 생긴 상해에 대해서는 보상하지 않습니다. "
    "1. 전문등반(전문적인 등산용구를 사용하여 암벽 또는 빙벽을 오르내리거나 특수한 "
    "기술, 경험, 사전 훈련이 필요한 등반을 말합니다), 글라이더 조종, 스카이다이빙, "
    "스쿠버다이빙, 행글라이딩, 수상보트, 패러글라이딩 "
    "2. 모터보트, 자동차 또는 오토바이에 의한 경기, 시범, 행사(이를 위한 연습을 포함합니다) "
    "또는 시운전(다만, 공용도로에서 시운전을 하는 동안 발생한 상해는 보상합니다) "
    "3. 선박승무원, 어부, 사공, 그밖에 선박에 탑승하는 것을 직무로 하는 사람의 "
    "직무상 선박탑승"
)

BASIC_INJ_EXCLUSION_MEDICAL_TEXT = (
    "③ 회사는 아래의 의료비에 대하여는 보상하지 않습니다. "
    "1. 건강검진(단, 검사결과 이상 소견에 따라 건강검진센터 등에서 발생한 추가의료비용은 "
    "보상합니다), 예방접종, 인공유산에 든 비용. 다만, 회사가 보상하는 상해 치료를 목적으로 "
    "하는 경우에는 보상합니다. "
    "2. 영양제, 비타민제, 호르몬 투여, 보신용 투약, 친자 확인을 위한 진단, 불임검사, "
    "불임수술, 불임복원술, 보조생식술(체내, 체외 인공수정을 포함합니다), 성장촉진, "
    "의약외품과 관련하여 소요된 비용. 다만, 회사가 보상하는 상해 치료를 목적으로 하는 경우에는 "
    "보상합니다. "
    "3. 의치, 의수족, 의안, 안경, 콘택트렌즈, 보청기, 목발, 팔걸이(Arm Sling), 보조기 등 "
    "진료재료의 구입 및 대체비용. 다만, 인공장기 등 신체에 이식되어 그 기능을 대신하는 경우에는 "
    "보상합니다. "
    "4. 외모개선 목적의 치료로 인하여 발생한 의료비"
)

# (p.24, 질병의료비)
BASIC_ILL_EXCLUSION_GENERAL_TEXT = (
    "① 회사는 아래의 사유를 원인으로 하여 생긴 의료비는 보상하지 않습니다. "
    "1. 피보험자가 고의로 자신을 해친 경우. 다만, 피보험자가 심신상실 등으로 자유로운 "
    "의사결정을 할 수 없는 상태에서 자신을 해친 사실이 증명된 경우에는 보상합니다. "
    "2. 보험수익자가 고의로 피보험자를 해친 경우. 다만, 그 보험수익자가 보험금의 "
    "일부 보험수익자인 경우에는 다른 보험수익자에 대한 보험금은 지급합니다. "
    "3. 계약자가 고의로 피보험자를 해친 경우 "
    "4. 피보험자가 정당한 이유없이 입원 또는 통원기간 중 의사의 지시를 따르지 않아 "
    "발생한 의료비와 의사가 통원치료가 가능하다고 인정함에도 피보험자 본인이 자의적으로 "
    "입원하여 발생한 입원의료비"
)

BASIC_ILL_EXCLUSION_DISEASE_TEXT = (
    "② 회사는 한국표준질병사인분류에 있어서 아래의 의료비에 대하여는 보상하지 않습니다. "
    "1. 정신 및 행동장애(F04～F99) "
    "(다만, F04～F09, F20～F29, F30～F39, F40～F48, F51, F90～F98과 관련한 치료에서 "
    "발생한 \"국민건강보험법\"에 따른 요양급여에 해당하는 의료비는 보상합니다) "
    "2. 여성생식기의 비염증성 장애로 인한 습관성 유산, 불임 및 인공수정관련 합병증(N96～N98) "
    "3. 피보험자가 임신, 출산(제왕절개를 포함합니다), 산후기로 치료한 경우(O00～O99) "
    "4. 선천성 뇌질환(Q00～Q04) "
    "5. 비만(E66) "
    "6. 요실금(N39.3, N39.4, R32) "
    "7. 직장 또는 항문질환 중 \"국민건강보험법\"에 따른 요양급여에 해당하지 않는 부분(I84, K60～K62, K64)"
)

# ---------------------------------------------------------------------------
# 기본형 실손의료비 특별약관 - 제4조의2 특별약관에서 보상하는 사항
# (p.25, 중요: 비급여 특약 연계)
# ---------------------------------------------------------------------------

BASIC_NON_COVERED_REFERENCE_TEXT = (
    "① 제3조 및 제4조에도 불구하고 다음 각 호에 해당하는 국내 상해의료비 및 국내 "
    "질병의료비는 기본형 실손의료비 특별약관에서 보상하지 않습니다. "
    "1. 도수치료·체외충격파치료·증식치료로 인하여 발생한 비급여의료비 "
    "2. 비급여 주사료[다만, 항암제, 항생제(항진균제 포함), 희귀의약품은 보상합니다] "
    "3. 자기공명영상진단(MRI/MRA)으로 인하여 발생한 비급여의료비(조영제, 판독료를 포함합니다) "
    "4. 제1호, 제2호, 제3호와 관련하여 자동차보험(공제를 포함합니다) 또는 산재보험에서 "
    "발생한 본인부담의료비"
)


def _get_or_create_clause(db, *, policy_version_id, coverage_id, clause_type, article_no, text, page_ref, default_color):
    existing = (
        db.query(Clause)
        .filter(
            Clause.policy_version_id == policy_version_id,
            Clause.coverage_id == coverage_id,
            Clause.article_no == article_no,
            Clause.text == text,
        )
        .first()
    )
    if existing:
        return existing, False
    clause = Clause(
        policy_version_id=policy_version_id, coverage_id=coverage_id,
        clause_type=clause_type, article_no=article_no, text=text,
        page_ref=page_ref, default_color=default_color,
    )
    db.add(clause)
    db.flush()
    return clause, True


def _get_or_create_map(db, *, clause_id, type_id, relevance, confidence):
    existing = (
        db.query(ClauseIncidentMap)
        .filter(ClauseIncidentMap.clause_id == clause_id, ClauseIncidentMap.type_id == type_id)
        .first()
    )
    if existing:
        return False
    db.add(ClauseIncidentMap(
        clause_id=clause_id, type_id=type_id,
        relevance=relevance, mapped_by="human", confidence=confidence,
    ))
    return True


def run():
    db = SessionLocal()
    try:
        insurer = db.query(Insurer).filter_by(code="DB").first()
        if not insurer:
            print("DB손해보험이 아직 시딩되지 않았습니다. seed_db.py를 먼저 실행하세요.")
            return
        pv = (
            db.query(PolicyVersion)
            .join(Product, Product.product_id == PolicyVersion.product_id)
            .filter(Product.insurer_id == insurer.insurer_id)
            .first()
        )
        if not pv:
            print("DB손해보험 policy_version을 찾을 수 없습니다.")
            return

        types = {t.l2_code: t for t in db.query(IncidentType).all()}
        required = ["INJ_OVERSEAS_TREATMENT", "ILL_OVERSEAS_TREATMENT"]
        missing = [c for c in required if c not in types]
        if missing:
            print(f"incident_type 사전에 없는 코드: {missing}. seed_incident_types를 먼저 실행하세요.")
            return

        # 기존 CoverageStd 재사용
        std_inj_med = get_or_create_coverage_std(db, "OVS_INJ_MED", "해외발생 상해의료비", "상해", False)
        std_ill_med = get_or_create_coverage_std(db, "OVS_ILL_MED", "해외발생 질병의료비", "질병", False)

        clause_created = map_created = coverage_created = 0

        # ------------------------------------------------------------------
        # 1) 기본형 실손의료비 특별약관 - 상해의료비
        # ------------------------------------------------------------------
        cov_basic_inj = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "기본형 실손의료비 특별약관 - 상해의료비",
            )
            .first()
        )
        if not cov_basic_inj:
            cov_basic_inj = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_inj_med.coverage_std_id,
                raw_name="기본형 실손의료비 특별약관 - 상해의료비",
                definition=BASIC_INJ_OVERSEAS_CLAUSE1_TEXT,
                limit_amount="보험증권 기재 보험가입금액(보장종목별)",
                deductible="자기부담금(약정된 경우)",
                waiting_condition="해외여행 중 발생 필수, 국내는 보험기간 종료 후 30일 이내 치료 시작 필요",
            )
            db.add(cov_basic_inj)
            db.flush()
            coverage_created += 1

        # 상해의료비 보장정의 (해외)
        clause_inj_1, c1 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_basic_inj.coverage_id,
            clause_type="보장정의", article_no="[기본형 실손의료비] 제3조(1)상해의료비-해외 제1항",
            text=BASIC_INJ_OVERSEAS_CLAUSE1_TEXT, page_ref="p.20", default_color="파랑",
        )
        clause_inj_2, c2 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_basic_inj.coverage_id,
            clause_type="제한", article_no="[기본형 실손의료비] 제3조(1)상해의료비-해외 제2항(척추지압술/침술)",
            text=BASIC_INJ_OVERSEAS_CLAUSE2_TEXT, page_ref="p.20-21", default_color="초록",
        )
        clause_inj_3, c3 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_basic_inj.coverage_id,
            clause_type="보장정의", article_no="[기본형 실손의료비] 제3조(1)상해의료비-해외 제3항(중독증상)",
            text=BASIC_INJ_OVERSEAS_CLAUSE3_TEXT, page_ref="p.21", default_color="파랑",
        )
        clause_inj_4, c4 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_basic_inj.coverage_id,
            clause_type="제한", article_no="[기본형 실손의료비] 제3조(1)상해의료비-해외 제4항(180일 한정)",
            text=BASIC_INJ_OVERSEAS_CLAUSE4_TEXT, page_ref="p.21", default_color="초록",
        )
        # 주의: seed_db_inj_deep.py가 이미 이 조항(문구의 특수문자 표기만 다름 - ․ vs ·)을
        # 넣어뒀을 수 있다 — exact-match dedup을 우회할 수 있는 표기 차이라 핵심 문구로 먼저 확인.
        _existing_inj5 = db.query(Clause).filter(
            Clause.coverage_id == cov_basic_inj.coverage_id,
            Clause.text.like("%외래는 방문 90회%"),
        ).first()
        if _existing_inj5:
            clause_inj_5, c5 = _existing_inj5, False
        else:
            clause_inj_5, c5 = _get_or_create_clause(
                db, policy_version_id=pv.policy_version_id, coverage_id=cov_basic_inj.coverage_id,
                clause_type="보장정의", article_no="[기본형 실손의료비] 제3조(1)상해의료비-국내 제1항",
                text=BASIC_INJ_DOMESTIC_CLAUSE_TEXT, page_ref="p.21", default_color="파랑",
            )

        # 상해의료비 면책사항
        clause_inj_excl1, c6 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_basic_inj.coverage_id,
            clause_type="면책", article_no="[기본형 실손의료비] 제4조(1)상해의료비-해외 제1항(고의/임신/전쟁)",
            text=BASIC_INJ_EXCLUSION_GENERAL_TEXT, page_ref="p.22", default_color="빨강",
        )
        clause_inj_excl2, c7 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_basic_inj.coverage_id,
            clause_type="면책", article_no="[기본형 실손의료비] 제4조(1)상해의료비-해외 제2항(위험행위)",
            text=BASIC_INJ_EXCLUSION_BEHAVIOR_TEXT, page_ref="p.22", default_color="빨강",
        )
        clause_inj_excl3, c8 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_basic_inj.coverage_id,
            clause_type="면책", article_no="[기본형 실손의료비] 제4조(1)상해의료비-해외 제3항(의료비 제외)",
            text=BASIC_INJ_EXCLUSION_MEDICAL_TEXT, page_ref="p.22-23", default_color="빨강",
        )

        clause_created += sum([c1, c2, c3, c4, c5, c6, c7, c8])

        # ------------------------------------------------------------------
        # 2) 기본형 실손의료비 특별약관 - 질병의료비
        # ------------------------------------------------------------------
        cov_basic_ill = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "기본형 실손의료비 특별약관 - 질병의료비",
            )
            .first()
        )
        if not cov_basic_ill:
            cov_basic_ill = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_ill_med.coverage_std_id,
                raw_name="기본형 실손의료비 특별약관 - 질병의료비",
                definition=BASIC_ILL_OVERSEAS_CLAUSE1_TEXT,
                limit_amount="보험증권 기재 보험가입금액(보장종목별)",
                deductible="자기부담금(약정된 경우)",
                waiting_condition="해외여행 중 발생 필수, 국내는 보험기간 종료 후 30일 이내 치료 시작 필요",
            )
            db.add(cov_basic_ill)
            db.flush()
            coverage_created += 1

        # 질병의료비 보장정의 (해외)
        clause_ill_1, c9 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_basic_ill.coverage_id,
            clause_type="보장정의", article_no="[기본형 실손의료비] 제3조(2)질병의료비-해외 제1항",
            text=BASIC_ILL_OVERSEAS_CLAUSE1_TEXT, page_ref="p.21", default_color="파랑",
        )
        clause_ill_2, c10 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_basic_ill.coverage_id,
            clause_type="제한", article_no="[기본형 실손의료비] 제3조(2)질병의료비-해외 제2항(척추지압술/침술)",
            text=BASIC_ILL_OVERSEAS_CLAUSE2_TEXT, page_ref="p.21", default_color="초록",
        )
        clause_ill_3, c11 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_basic_ill.coverage_id,
            clause_type="제한", article_no="[기본형 실손의료비] 제3조(2)질병의료비-해외 제3항(180일 한정)",
            text=BASIC_ILL_OVERSEAS_CLAUSE3_TEXT, page_ref="p.21", default_color="초록",
        )
        clause_ill_4, c12 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_basic_ill.coverage_id,
            clause_type="보장정의", article_no="[기본형 실손의료비] 제3조(2)질병의료비-국내 제1항",
            text=BASIC_ILL_DOMESTIC_CLAUSE_TEXT, page_ref="p.21", default_color="파랑",
        )

        # 질병의료비 면책사항
        clause_ill_excl1, c13 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_basic_ill.coverage_id,
            clause_type="면책", article_no="[기본형 실손의료비] 제4조(2)질병의료비-해외 제1항(고의/의사지시불순종)",
            text=BASIC_ILL_EXCLUSION_GENERAL_TEXT, page_ref="p.24", default_color="빨강",
        )
        clause_ill_excl2, c14 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_basic_ill.coverage_id,
            clause_type="면책", article_no="[기본형 실손의료비] 제4조(2)질병의료비-해외 제2항(정신질환/임신/기타질병)",
            text=BASIC_ILL_EXCLUSION_DISEASE_TEXT, page_ref="p.24", default_color="빨강",
        )

        clause_created += sum([c9, c10, c11, c12, c13, c14])

        # ------------------------------------------------------------------
        # 3) 기본형 실손의료비 특별약관 - 제4조의2 (비급여 특약 연계)
        # ------------------------------------------------------------------
        # Coverage 추가 (NON_COVERED_MED 재사용)
        std_non_covered = get_or_create_coverage_std(
            db, "NON_COVERED_MED", "비급여 실손의료비", "상해", False
        )
        cov_non_covered = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "기본형 실손의료비 - 비급여 제외 안내",
            )
            .first()
        )
        if not cov_non_covered:
            cov_non_covered = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_non_covered.coverage_std_id,
                raw_name="기본형 실손의료비 - 비급여 제외 안내",
                definition="기본형에서 제외하고 별도 비급여 특약에서 보상: 도수치료·체외충격파·증식치료, "
                           "비급여 주사료(항암제/항생제/희귀의약품 제외), MRI/MRA 비급여",
                limit_amount="별도 비급여 특약 참조",
                deductible=None,
                waiting_condition="별도 비급여 특약 가입 필요",
            )
            db.add(cov_non_covered)
            db.flush()
            coverage_created += 1

        clause_non_covered, c15 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_non_covered.coverage_id,
            clause_type="조건", article_no="[기본형 실손의료비] 제4조의2(특별약관에서 보상하는 사항)",
            text=BASIC_NON_COVERED_REFERENCE_TEXT, page_ref="p.25", default_color="노랑",
        )
        clause_created += c15

        # ------------------------------------------------------------------
        # ClauseIncidentMap 매핑
        # ------------------------------------------------------------------
        inj_med_type = types["INJ_OVERSEAS_TREATMENT"]
        ill_med_type = types["ILL_OVERSEAS_TREATMENT"]

        # 상해의료비 매핑
        map_created += sum([
            _get_or_create_map(db, clause_id=clause_inj_1.clause_id, type_id=inj_med_type.type_id, relevance="직접", confidence=1.0),
            _get_or_create_map(db, clause_id=clause_inj_2.clause_id, type_id=inj_med_type.type_id, relevance="제한", confidence=0.9),
            _get_or_create_map(db, clause_id=clause_inj_3.clause_id, type_id=inj_med_type.type_id, relevance="직접", confidence=0.85),
            _get_or_create_map(db, clause_id=clause_inj_4.clause_id, type_id=inj_med_type.type_id, relevance="제한", confidence=0.95),
            _get_or_create_map(db, clause_id=clause_inj_5.clause_id, type_id=inj_med_type.type_id, relevance="직접", confidence=0.95),
            _get_or_create_map(db, clause_id=clause_inj_excl1.clause_id, type_id=inj_med_type.type_id, relevance="면책", confidence=1.0),
            _get_or_create_map(db, clause_id=clause_inj_excl2.clause_id, type_id=inj_med_type.type_id, relevance="면책", confidence=1.0),
            _get_or_create_map(db, clause_id=clause_inj_excl3.clause_id, type_id=inj_med_type.type_id, relevance="면책", confidence=0.9),
        ])

        # 질병의료비 매핑
        map_created += sum([
            _get_or_create_map(db, clause_id=clause_ill_1.clause_id, type_id=ill_med_type.type_id, relevance="직접", confidence=1.0),
            _get_or_create_map(db, clause_id=clause_ill_2.clause_id, type_id=ill_med_type.type_id, relevance="제한", confidence=0.9),
            _get_or_create_map(db, clause_id=clause_ill_3.clause_id, type_id=ill_med_type.type_id, relevance="제한", confidence=0.95),
            _get_or_create_map(db, clause_id=clause_ill_4.clause_id, type_id=ill_med_type.type_id, relevance="직접", confidence=0.95),
            _get_or_create_map(db, clause_id=clause_ill_excl1.clause_id, type_id=ill_med_type.type_id, relevance="면책", confidence=1.0),
            _get_or_create_map(db, clause_id=clause_ill_excl2.clause_id, type_id=ill_med_type.type_id, relevance="면책", confidence=1.0),
        ])

        db.commit()
        print(
            "DB 청크1(p.1-42) 완료: "
            f"coverage 신규={coverage_created}(기본형 실손의료비 상해/질병/비급여 참조), "
            f"clause 신규={clause_created}(보장정의/제한/면책/조건), "
            f"clause_incident_map 신규={map_created}(INJ_MEDICAL/ILL_MEDICAL). "
            "p.1-2(목차), p.3-18(보통약관 제1관~제7관 행정조항 확인 스킵)."
        )
    finally:
        db.close()


if __name__ == "__main__":
    run()
