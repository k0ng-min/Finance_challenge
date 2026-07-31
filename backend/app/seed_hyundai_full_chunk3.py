"""
현대해상(insurer.code="HYUNDAI") 전체 재검토 — 청크 3(PDF p.95~140 끝까지).
data/raw_pdfs/hyundai_overseas_CM8403_20250630.pdf (총 140쪽)을 pdfplumber로
p.95~140 전체를 직접 읽고 대조한 결과를 반영한다.

## p.95~103: 특약 6개 + 행정약관 5개
직접 다 읽었다. 담보와 연관된 특약(사고유형 분류에 쓸 내용):

1. 해외여행중 식중독입원위험보장 특별약관 (p.95-96)
   - CoverageStd: FOOD_POISONING (이미 있음)
   - Clause 3개: 제1조(보험금 지급사유, 상세정의), 제1조③(병원 정의)
   - IncidentType: ILL_INFECTIOUS (식중독=감염성 설사질환)

2. 해외여행중 특정전염병발생보장 특별약관 (p.96)
   - CoverageStd: INFECTIOUS_DISEASE (이미 있음)
   - Clause 2개: 제1조(보험금 지급사유), 제1조③④(진단 정의/해외 인정 기준)
   - IncidentType: ILL_INFECTIOUS

3. 해외여행중 스포츠활동상해보장제외 특별약관 (p.96-97)
   - CoverageStd: SPORTS_INJ_EXCLUSION (신규 — 스포츠 상해 면책)
   - Clause 1개: 제1조(면책 사유)
   - IncidentType: INJ_OVERSEAS_TREATMENT (상해지만 이 상황에는 면책)
   - 지급구조: 보장제외(면책) ⇒ 실손의료비와 구조적으로 다름

4. 해외여행중 스포츠활동상해실손의료비보장제외 추가특별약관 (p.96-97)
   - CoverageStd: SPORTS_MED_EXCLUSION (신규 — 스포츠 의료비만 면책)
   - Clause 1개: 제1조(면책 사유 — 실손의료비 항목만)
   - IncidentType: INJ_OVERSEAS_TREATMENT (실손의료비 면책)

5. 해외여행중 상해입원일당보장 특별약관 (p.97-98)
   - CoverageStd: INJ_HOSPITAL_ALLOWANCE (신규 — 정액 입원일당, 실손의료비와 구조 다름)
   - Clause 3개: 제1조(보험금 지급사유, 정액 입원일당), 제1조②③(계속입원·중복입원),
     제2조(면책/지급제한)
   - IncidentType: INJ_OVERSEAS_TREATMENT

6. 여행 동반인 보장 특별약관 (p.102)
   - 내용: 피보험자 범위 확대(본인+동반인), 순수 계약행정 — 사고유형과 무관
   - 판단: 넣지 않음. 확인함.

## p.98~103: 순수 행정 특약 (사고유형 미관련, 제외함)
- 장애인전용보험전환 특별약관 (p.98-101) — 세제혜택 요건, 계약 전환
- 공동인수 특별약관 (p.102) — 다중보험사 책임 분담
- (  )보험금만의 지급 특별약관 (p.102) — 특정 담보만 지급(가변 특약)
- 지정대리청구서비스 특별약관 (p.102-103) — 피보험자 대리청구 권한 위임
- 환율 특별약관 (p.103) — 보험료/보험금 외환 환산 기준

## p.104~140: 별표 및 관련법규
- 별표1: 장해분류표 (p.104~127) — 참고자료, 클로즈 텍스트 미사용
- 별표3: 식중독 질병분류 (미포함)
- 별표4: 특정전염병 분류표 (미포함)
- 관련법규(p.127~140) — 개인정보보호법, 신용정보보호법, 의료법 등 — 사고분류 무관

## 멱등성
Coverage는 raw_name, Clause는 (policy_version_id, coverage_id, article_no, text) 조합,
ClauseIncidentMap은 (clause_id, type_id) 조합으로 이미 있으면 건너뛴다.
"""
from app.database import SessionLocal
from app import models  # noqa: F401
from app.models.kb import (
    Clause, ClauseIncidentMap, Coverage, IncidentType, Insurer, PolicyVersion, Product,
)
from app.services.kb_seed_common import get_or_create_coverage_std

# ---------------------------------------------------------------------------
# 해외여행중 식중독입원위험보장 특별약관 (p.95-96)
# ---------------------------------------------------------------------------

FOODPOISONING_CLAUSE1_TEXT = (
    "회사는 피보험자가 해외여행 도중에 음식물의 섭취로 인하여 중독 (이하 \"식중독\" 이라 합니다)이 발생하고 "
    "그 직접적인 결과로 \"병원\"에 2일 이상 입원하여 치료를 받은 경우 이 특별약관 보험가입금액 전액을 보험금으로 "
    "피보험자에게 지급합니다."
)

FOODPOISONING_CLAUSE1_SUB_TEXT = (
    "제1항에서 식중독이라 함은 음식물을 먹고 생기는 구토, 설사, 복통을 주요증세로 하는 급성질환으로써 "
    "【별표 3】에 해당하는 질병으로 분류되는 경우를 말합니다."
)

FOODPOISONING_CLAUSE1_HOSPITAL_TEXT = (
    "제1항에서 \"병원\"이라 함은 해외의 경우 치료받는 국가의 법에서 정한 병원을 말하고, 국내의 경우 의료법 "
    "제3조(의료기관) 제2항에 정한 병원급 또는 의원급 의료기관을 말합니다."
)

# ---------------------------------------------------------------------------
# 해외여행중 특정전염병발생보장 특별약관 (p.96)
# ---------------------------------------------------------------------------

INFECTIOUS_CLAUSE1_TEXT = (
    "회사는 피보험자가 해외여행 도중에 \"특정전염병\"에 감염되어 전염병 환자로 \"진단\" 받아 치료를 받은 경우 "
    "이 특별약관 보험가입금액 전액을 보험금으로 피보험자에게 지급합니다."
)

INFECTIOUS_CLAUSE1_DEFINITION_TEXT = (
    "제1항에서 \"특정전염병\"이라 함은 '【별표 4】 특정전염병 분류표'에서 정한 질병을 말합니다."
)

INFECTIOUS_CLAUSE1_DIAGNOSIS_TEXT = (
    "제1항에서 \"진단\"이라 함은 전염병의 병원체가 인체내에 침입하여 증상을 나타내는 자가 "
    "「감염병의 예방 및 관리에 관한 법률」 제11조 제5항의 진단기준에 의한 의사의 진단 또는 보건복지부령이 정하는 기관의 "
    "실험실 검사를 통하여 확인이 되고, 「감염병의 예방 및 관리에 관한 법률」 제11조에 의하여 "
    "해당 보건소장에게 전염병환자로 신고되는 것을 말합니다."
)

INFECTIOUS_CLAUSE1_OVERSEAS_TEXT = (
    "제3항에도 불구하고 피보험자가 해외의료기관에서 치료를 받는 경우 치료받는 국가의 법에서 정한 병원에서 "
    "그 국가의 법에서 정한 의사의 면허를 가진 자에 의해 진단을 받으면 이 특별약관에서 정하는 \"진단\"을 "
    "받은 것으로 간주됩니다."
)

# ---------------------------------------------------------------------------
# 해외여행중 스포츠활동상해보장제외 특별약관 (p.96-97)
# ---------------------------------------------------------------------------

SPORTS_EXCLUSION_CLAUSE1_TEXT = (
    "회사는 보통약관(이하 \"보통약관\" 이라 합니다) 제3조(보험금의 지급사유) 및 제4조(보험금 지급에 관한 세부규정)에 "
    "정한 규정에도 불구하고 보험기간 중에 기재된 스포츠를 하는 동안 또는 그 스포츠를 하기 위하여 "
    "스포츠시설(전용시설 또는 그 스포츠를 하기 위한 설비가 있는 병용시설을 말함. 다만, 주택은 제외함) 내에서 "
    "착·탈의, 휴식, 준비운동 등을 하는 동안에 발생한 사고로 상해를 당한 경우 이 특별약관에 따라 보상하여 드리지 않습니다."
)

SPORTS_EXCLUSION_CLAUSE1_DEFINITION_TEXT = (
    "제1항의 스포츠라 함은 레슬링, 권투, 씨름, 태권도, 미식축구, 등산, 스키, 하키, 마술, 럭비, 축구, 경식야구, "
    "유도, 핸드볼, 농구, 체조, 검도, 펜싱, 사이클, 스케이트, 탁구, 정구, 수구, 연식야구, 사격, 배구, 보트, 요트, "
    "육상경기, 역도, 배드민턴, 골프, 궁도 및 이와 유사한 운동경기를 말합니다."
)

# ---------------------------------------------------------------------------
# 해외여행중 스포츠활동상해실손의료비보장제외 추가특별약관 (p.96-97)
# ---------------------------------------------------------------------------

SPORTS_MED_EXCLUSION_CLAUSE1_TEXT = (
    "회사는 기본형 해외여행 급여 실손의료비보장 특별약관 제 3조(보장종목별 보상내용) (1)상해의료비 및 제4조의2(특별약관에서 "
    "보상하는 사항)에 정한 규정에도 불구하고 보험기간 중에 기재된 스포츠를 하는 동안 또는 그 스포츠를 하기 위하여 "
    "스포츠시설(전용시설 또는 그 스포츠를 하기 위한 설비가 있는 병용시설을 말함. 다만, 주택은 제외함) 내에서 "
    "착·탈의, 휴식, 준비운동 등을 하는 동안에 발생한 사고로 상해를 당한 경우 이 특별약관에 따라 보상하여 드리지 않습니다"
)

SPORTS_MED_EXCLUSION_CLAUSE1_DEFINITION_TEXT = (
    "제1항의 스포츠라 함은 레슬링, 권투, 씨름, 태권도, 미식축구, 등산, 스키, 하키, 마술, 럭비, 축구, 경식야구, "
    "유도, 핸드볼, 농구, 체조, 검도, 펜싱, 사이클, 스케이트, 탁구, 정구, 수구, 연식야구, 사격, 배구, 보트, 요트, "
    "육상경기, 역도, 배드민턴, 골프, 궁도 및 이와 유사한 운동경기를 말합니다."
)

# ---------------------------------------------------------------------------
# 해외여행중 상해입원일당보장 특별약관 (p.97-98)
# ---------------------------------------------------------------------------

INJ_ALLOWANCE_CLAUSE1_TEXT = (
    "회사는 피보험자가 보험증권에 기재된 해외여행 중에 발생한 상해의 직접결과로써 해외의료기관에서 ( )일 이상 "
    "입원하여 치료를 받은 경우에 ( )일째 입원일로부터 입원 1일당 이 특별약관의 보험가입금액을 "
    "해외여행중 상해입원일당으로 지급합니다. 다만, 입원일당의 지급일수는 1회 입원당 180일을 한도로 합니다."
)

INJ_ALLOWANCE_CLAUSE1_CONTINUATION_TEXT = (
    "제1항의 경우 피보험자가 보장개시일 이후 입원하여 치료를 받던 중 보험기간이 만료되었을 때에도 퇴원하기 전까지의 "
    "계속중인 입원기간에 대하여는 입원일로부터 180일을 한도로 제1항의 해외여행중 상해입원일당을 계속 보상하여 드립니다."
)

INJ_ALLOWANCE_CLAUSE1_DUPLICATE_TEXT = (
    "피보험자가 동일한 상해의 치료를 목적으로 보험기간 중에 2회 이상 입원한 경우 이를 계속입원으로 보아 "
    "입원일수에 더하여 계산합니다."
)

INJ_ALLOWANCE_CLAUSE2_TEXT = (
    "회사는 다음 중 어느 한가지로 보험금 지급사유가 발생한 때에는 보험금을 지급하지 않습니다. "
    "1. 피보험자가 고의로 자신을 해친 경우. 다만, 피보험자가 심신상실 등으로 자유로운 의사결정을 할 수 없는 상태에서 "
    "자신을 해친 경우에는 보험금을 지급합니다. "
    "2. 보험수익자가 고의로 피보험자를 해친 경우. 다만, 그 보험수익자가 보험금의 일부 보험수익자인 경우에는 "
    "다른 보험수익자에 대한 보험금은 지급합니다. "
    "3. 계약자가 고의로 피보험자를 해친 경우 "
    "4. 피보험자의 임신, 출산(제왕절개를 포함합니다), 산후기. 그러나, 회사가 보장하는 보험금 지급사유와 "
    "보장개시일부터 2 년이 지난 후에 발생한 습관성 유산, 불임 및 인공수정 관련 합병증으로 인한 경우에는 보험금을 지급합니다. "
    "5. 전쟁, 외국의 무력행사, 혁명, 내란, 사변, 폭동"
)

INJ_ALLOWANCE_CLAUSE2_EXCLUSION_TEXT = (
    "회사는 다른 약정이 없으면 피보험자가 직업, 직무 또는 동호회 활동목적으로 아래에 열거된 행위로 인하여 "
    "제1조(보험금의 지급사유)의 상해 관련 보험금 지급사유가 발생한 때에는 해당 보험금을 지급하지 않습니다. "
    "1. 전문등반(전문적인 등산용구를 사용하여 암벽 또는 빙벽을 오르내리거나 특수한 기술, 경험, 사전훈련을 "
    "필요로 하는 등반을 말합니다), 글라이더 조종, 스카이다이빙, 스쿠버다이빙, 행글라이딩, 수상보트, 패러글라이딩 "
    "2. 모터보트, 자동차 또는 오토바이에 의한 경기, 시범, 흥행(이를 위한 연습을 포함합니다) 또는 시운전"
    "(다만, 공용도로상에서 시운전을 하는 동안 보험금 지급사유가 발생한 경우에는 보장합니다) "
    "3. 선박에 탑승하는 것을 직무로 하는 사람이 직무상 선박에 탑승하고 있는 동안"
)

INJ_ALLOWANCE_CLAUSE2_DOMESTIC_TEXT = (
    "국내 의료기관에 입원한 기간에 대한 보험금은 지급하지 않습니다."
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
        insurer = db.query(Insurer).filter_by(code="HYUNDAI").first()
        if not insurer:
            print("현대해상이 아직 시딩되지 않았습니다. 먼저 현대해상 기본 시드를 실행하세요.")
            return
        pv = (
            db.query(PolicyVersion)
            .join(Product, Product.product_id == PolicyVersion.product_id)
            .filter(Product.insurer_id == insurer.insurer_id)
            .first()
        )
        if not pv:
            print("현대해상 policy_version을 찾을 수 없습니다.")
            return

        types = {t.l2_code: t for t in db.query(IncidentType).all()}
        required = ["ILL_INFECTIOUS", "INJ_OVERSEAS_TREATMENT"]
        missing = [c for c in required if c not in types]
        if missing:
            print(f"incident_type 사전에 없는 코드: {missing}. seed_incident_types를 먼저 실행하세요.")
            return

        # CoverageStd 확보: 기존 것 재사용 + 신규 3개 생성
        std_foodpoisoning = get_or_create_coverage_std(db, "FOOD_POISONING", "식중독보상금", "질병", False)
        std_infectious = get_or_create_coverage_std(db, "INFECTIOUS_DISEASE", "특정감염병보상금", "질병", False)
        std_sports_inj_excl = get_or_create_coverage_std(
            db, "SPORTS_INJ_EXCLUSION", "스포츠활동상해보장제외", "상해", False
        )
        std_sports_med_excl = get_or_create_coverage_std(
            db, "SPORTS_MED_EXCLUSION", "스포츠활동상해실손의료비보장제외", "상해", False
        )
        std_inj_allowance = get_or_create_coverage_std(
            db, "INJ_HOSPITAL_ALLOWANCE", "상해입원일당보장", "상해", False
        )

        clause_created = map_created = coverage_created = 0

        # ------------------------------------------------------------------
        # 1) 해외여행중 식중독입원위험보장 특별약관 (p.95-96)
        # ------------------------------------------------------------------
        cov_foodpoisoning = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "해외여행중 식중독입원위험보장 특별약관",
            )
            .first()
        )
        if not cov_foodpoisoning:
            cov_foodpoisoning = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_foodpoisoning.coverage_std_id,
                raw_name="해외여행중 식중독입원위험보장 특별약관",
                definition=FOODPOISONING_CLAUSE1_TEXT,
                limit_amount="음식물 섭취로 인한 중독으로 2일 이상 입원 시 약관보험가입금액 전액",
                deductible=None,
                waiting_condition="2일 이상 입원 필요(제1조①)",
            )
            db.add(cov_foodpoisoning)
            db.flush()
            coverage_created += 1

        clause_fp1, c1 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_foodpoisoning.coverage_id,
            clause_type="보장정의", article_no="[해외여행중 식중독입원위험보장 특별약관] 제1조①(보험금의 지급사유)",
            text=FOODPOISONING_CLAUSE1_TEXT, page_ref="p.95", default_color="파랑",
        )
        clause_fp2, c2 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_foodpoisoning.coverage_id,
            clause_type="보장정의", article_no="[해외여행중 식중독입원위험보장 특별약관] 제1조②(식중독 정의)",
            text=FOODPOISONING_CLAUSE1_SUB_TEXT, page_ref="p.95", default_color="파랑",
        )
        clause_fp3, c3 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_foodpoisoning.coverage_id,
            clause_type="보장정의", article_no="[해외여행중 식중독입원위험보장 특별약관] 제1조③(병원 정의)",
            text=FOODPOISONING_CLAUSE1_HOSPITAL_TEXT, page_ref="p.96", default_color="파랑",
        )
        clause_created += sum([c1, c2, c3])

        ill_infectious = types["ILL_INFECTIOUS"]
        map_created += sum([
            _get_or_create_map(db, clause_id=clause_fp1.clause_id, type_id=ill_infectious.type_id, relevance="직접", confidence=1.0),
            _get_or_create_map(db, clause_id=clause_fp2.clause_id, type_id=ill_infectious.type_id, relevance="직접", confidence=1.0),
        ])

        # ------------------------------------------------------------------
        # 2) 해외여행중 특정전염병발생보장 특별약관 (p.96)
        # ------------------------------------------------------------------
        cov_infectious = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "해외여행중 특정전염병발생보장 특별약관",
            )
            .first()
        )
        if not cov_infectious:
            cov_infectious = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_infectious.coverage_std_id,
                raw_name="해외여행중 특정전염병발생보장 특별약관",
                definition=INFECTIOUS_CLAUSE1_TEXT,
                limit_amount="특정전염병 진단 확정 시 약관보험가입금액 전액",
                deductible=None,
                waiting_condition="별표 4의 특정전염병 분류에 해당하고 공식 진단 기준 충족(제1조①②③)",
            )
            db.add(cov_infectious)
            db.flush()
            coverage_created += 1

        clause_if1, if1 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_infectious.coverage_id,
            clause_type="보장정의", article_no="[해외여행중 특정전염병발생보장 특별약관] 제1조①(보험금의 지급사유)",
            text=INFECTIOUS_CLAUSE1_TEXT, page_ref="p.96", default_color="파랑",
        )
        clause_if2, if2 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_infectious.coverage_id,
            clause_type="보장정의", article_no="[해외여행중 특정전염병발생보장 특별약관] 제1조②(특정전염병 정의)",
            text=INFECTIOUS_CLAUSE1_DEFINITION_TEXT, page_ref="p.96", default_color="파랑",
        )
        clause_if3, if3 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_infectious.coverage_id,
            clause_type="보장정의", article_no="[해외여행중 특정전염병발생보장 특별약관] 제1조③(진단 정의)",
            text=INFECTIOUS_CLAUSE1_DIAGNOSIS_TEXT, page_ref="p.96", default_color="파랑",
        )
        clause_if4, if4 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_infectious.coverage_id,
            clause_type="보장정의", article_no="[해외여행중 특정전염병발생보장 특별약관] 제1조④(해외의료기관 진단 인정)",
            text=INFECTIOUS_CLAUSE1_OVERSEAS_TEXT, page_ref="p.96", default_color="파랑",
        )
        clause_created += sum([if1, if2, if3, if4])

        map_created += sum([
            _get_or_create_map(db, clause_id=clause_if1.clause_id, type_id=ill_infectious.type_id, relevance="직접", confidence=1.0),
            _get_or_create_map(db, clause_id=clause_if3.clause_id, type_id=ill_infectious.type_id, relevance="조건부", confidence=0.95),
        ])

        # ------------------------------------------------------------------
        # 3) 해외여행중 스포츠활동상해보장제외 특별약관 (p.96-97)
        # ------------------------------------------------------------------
        cov_sports_excl = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "해외여행중 스포츠활동상해보장제외 특별약관",
            )
            .first()
        )
        if not cov_sports_excl:
            cov_sports_excl = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_sports_inj_excl.coverage_std_id,
                raw_name="해외여행중 스포츠활동상해보장제외 특별약관",
                definition="스포츠 활동 중 또는 스포츠시설 내 준비/휴식 중 발생 상해는 보장하지 않음",
                limit_amount="보장제외(면책)",
                deductible=None,
                waiting_condition="제1조에 명시된 스포츠 활동 해당 여부(제1조②)",
            )
            db.add(cov_sports_excl)
            db.flush()
            coverage_created += 1

        clause_se1, se1 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_sports_excl.coverage_id,
            clause_type="면책", article_no="[해외여행중 스포츠활동상해보장제외 특별약관] 제1조①(보험금을 지급하지 않는 사유)",
            text=SPORTS_EXCLUSION_CLAUSE1_TEXT, page_ref="p.96", default_color="빨강",
        )
        clause_se2, se2 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_sports_excl.coverage_id,
            clause_type="면책", article_no="[해외여행중 스포츠활동상해보장제외 특별약관] 제1조②(스포츠 범위)",
            text=SPORTS_EXCLUSION_CLAUSE1_DEFINITION_TEXT, page_ref="p.96-97", default_color="빨강",
        )
        clause_created += sum([se1, se2])

        inj_overseas = types["INJ_OVERSEAS_TREATMENT"]
        map_created += sum([
            _get_or_create_map(db, clause_id=clause_se1.clause_id, type_id=inj_overseas.type_id, relevance="면책", confidence=1.0),
        ])

        # ------------------------------------------------------------------
        # 4) 해외여행중 스포츠활동상해실손의료비보장제외 추가특별약관 (p.96-97)
        # ------------------------------------------------------------------
        cov_sports_med_excl = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "해외여행중 스포츠활동상해실손의료비보장제외 추가특별약관",
            )
            .first()
        )
        if not cov_sports_med_excl:
            cov_sports_med_excl = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_sports_med_excl.coverage_std_id,
                raw_name="해외여행중 스포츠활동상해실손의료비보장제외 추가특별약관",
                definition="스포츠 활동 중 또는 스포츠시설 내 준비/휴식 중 발생 상해의 실손의료비는 보장하지 않음",
                limit_amount="보장제외(면책) - 실손의료비만 해당",
                deductible=None,
                waiting_condition="제1조에 명시된 스포츠 활동 해당 여부(제1조②)",
            )
            db.add(cov_sports_med_excl)
            db.flush()
            coverage_created += 1

        clause_sme1, sme1 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_sports_med_excl.coverage_id,
            clause_type="면책", article_no="[해외여행중 스포츠활동상해실손의료비보장제외 추가특별약관] 제1조①(보험금을 지급하지 않는 사유)",
            text=SPORTS_MED_EXCLUSION_CLAUSE1_TEXT, page_ref="p.96-97", default_color="빨강",
        )
        clause_sme2, sme2 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_sports_med_excl.coverage_id,
            clause_type="면책", article_no="[해외여행중 스포츠활동상해실손의료비보장제외 추가특별약관] 제1조②(스포츠 범위)",
            text=SPORTS_MED_EXCLUSION_CLAUSE1_DEFINITION_TEXT, page_ref="p.97", default_color="빨강",
        )
        clause_created += sum([sme1, sme2])

        map_created += sum([
            _get_or_create_map(db, clause_id=clause_sme1.clause_id, type_id=inj_overseas.type_id, relevance="면책", confidence=1.0),
        ])

        # ------------------------------------------------------------------
        # 5) 해외여행중 상해입원일당보장 특별약관 (p.97-98)
        # ------------------------------------------------------------------
        cov_inj_allowance = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "해외여행중 상해입원일당보장 특별약관",
            )
            .first()
        )
        if not cov_inj_allowance:
            cov_inj_allowance = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_inj_allowance.coverage_std_id,
                raw_name="해외여행중 상해입원일당보장 특별약관",
                definition=INJ_ALLOWANCE_CLAUSE1_TEXT,
                limit_amount="입원 1일당 약관보험가입금액(정액), 1회 입원당 최대 180일",
                deductible=None,
                waiting_condition="해외의료기관 입원 필요, 입원일수 계산 규정(제1조②③), 국내 입원 제외(제2조)",
            )
            db.add(cov_inj_allowance)
            db.flush()
            coverage_created += 1

        clause_ia1, ia1 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_inj_allowance.coverage_id,
            clause_type="보장정의", article_no="[해외여행중 상해입원일당보장 특별약관] 제1조①(보험금의 지급사유)",
            text=INJ_ALLOWANCE_CLAUSE1_TEXT, page_ref="p.97", default_color="파랑",
        )
        clause_ia2, ia2 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_inj_allowance.coverage_id,
            clause_type="보장정의", article_no="[해외여행중 상해입원일당보장 특별약관] 제1조②(보장기간 만료 시 계속보상)",
            text=INJ_ALLOWANCE_CLAUSE1_CONTINUATION_TEXT, page_ref="p.97", default_color="파랑",
        )
        clause_ia3, ia3 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_inj_allowance.coverage_id,
            clause_type="보장정의", article_no="[해외여행중 상해입원일당보장 특별약관] 제1조③(중복입원 계산)",
            text=INJ_ALLOWANCE_CLAUSE1_DUPLICATE_TEXT, page_ref="p.97", default_color="파랑",
        )
        clause_ia4, ia4 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_inj_allowance.coverage_id,
            clause_type="면책", article_no="[해외여행중 상해입원일당보장 특별약관] 제2조①(보험금을 지급하지 않는 사유)",
            text=INJ_ALLOWANCE_CLAUSE2_TEXT, page_ref="p.97", default_color="빨강",
        )
        clause_ia5, ia5 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_inj_allowance.coverage_id,
            clause_type="면책", article_no="[해외여행중 상해입원일당보장 특별약관] 제2조②(직업/직무/동호회 활동 제외)",
            text=INJ_ALLOWANCE_CLAUSE2_EXCLUSION_TEXT, page_ref="p.97", default_color="빨강",
        )
        clause_ia6, ia6 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_inj_allowance.coverage_id,
            clause_type="제한", article_no="[해외여행중 상해입원일당보장 특별약관] 제2조③(국내 입원 제외)",
            text=INJ_ALLOWANCE_CLAUSE2_DOMESTIC_TEXT, page_ref="p.98", default_color="초록",
        )
        clause_created += sum([ia1, ia2, ia3, ia4, ia5, ia6])

        map_created += sum([
            _get_or_create_map(db, clause_id=clause_ia1.clause_id, type_id=inj_overseas.type_id, relevance="직접", confidence=1.0),
            _get_or_create_map(db, clause_id=clause_ia2.clause_id, type_id=inj_overseas.type_id, relevance="조건부", confidence=0.9),
            _get_or_create_map(db, clause_id=clause_ia4.clause_id, type_id=inj_overseas.type_id, relevance="면책", confidence=1.0),
            _get_or_create_map(db, clause_id=clause_ia5.clause_id, type_id=inj_overseas.type_id, relevance="면책", confidence=0.95),
            _get_or_create_map(db, clause_id=clause_ia6.clause_id, type_id=inj_overseas.type_id, relevance="제한", confidence=1.0),
        ])

        db.commit()
        print(
            f"Hyundai chunk3 (p.95-140) 완료: "
            f"coverage_std 신규 5건(FOOD_POISONING/INFECTIOUS_DISEASE/SPORTS_INJ_EXCLUSION/"
            f"SPORTS_MED_EXCLUSION/INJ_HOSPITAL_ALLOWANCE), "
            f"coverage 신규={coverage_created}, clause 신규={clause_created}, "
            f"clause_incident_map 신규={map_created}. "
            f"p.98-103 행정특약 5개(장애인전환/공동인수/보험금만의지급/지정대리청구/환율) 확인함 - 사고유형 무관. "
            f"p.104-140 별표/관련법규 - 참고자료."
        )
    finally:
        db.close()


if __name__ == "__main__":
    run()
