"""
메리츠화재(insurer.code="MERITZ") 해외여행보험 청크2 — p.75-147

data/raw_pdfs/meritz_overseas_udirect.pdf를 pdfplumber로 p.75-147 전체를
직접 읽고 분석한 결과를 반영한다.

## 이 범위에서 추출한 특약들:

p.75-78: 해외여행 실손의료보험 특별약관(비급여 의료비 제외규정)
        — 사고유형 분류 대상 아님(순수 비급여의료비 제외 조항, 보장근거 아님). 확인 완료, 스킵.

p.79-84: 운동 및 기타위험 확장보상(전문등반 등) 추가특별약관(I, II)
        — 상해비급여/3대비급여 추가로, 다른 청크에서 처리될 가능성 있음.

p.85-95: 상해 사망·후유장해 특별약관, 부보장 추가, 전쟁위험, 운동위험 확장보상
        — 다른 청크(p.1-74, 상해사망 계열)에서 처리됨. 이 범위에서는 스킵.

p.96-107: 해외여행중 상해고도후유장해 특별약관(50%/80%/100%)
         — 상해 후유장해 관련. 다른 청크 처리 가능성 높음.

### 이 청크에서 실제 처리할 특약:

p.108-112: 질병사망 및 질병 80%이상 후유장해 특별약관
          CoverageStd ILL_DEATH로 매핑. 제1조(지급사유), 제2조(지급세부규정) 포함.

p.113-120: 배상책임 특별약관
          CoverageStd LIABILITY로 매핑. 제1조(손해범위), 제2조(보상범위),
          제3조(면책), 제4조(의무보험 관계), 제5조(지급한도) 등.

p.121-124: 휴대품손해(분실제외) 특별약관
          CoverageStd PERSONAL_EFFECTS로 매핑. 제1조(지급사유), 제2조(보상내용),
          제3조(보상하지않는손해), 제4조(지급보험금 계산).

p.125: 휴대품손해(분실제외) 휴대폰한도 감액 추가특별약관
       PERSONAL_EFFECTS의 추가 제한 조항. 제1조(지급보험금의 계산-감액).

p.126-128: 여행중 중대사고 구조송환비용 특별약관
          CoverageStd RESCUE로 매핑. 제1조(지급사유), 제2조(비용범위),
          제3조(보상하지않는사유), 제4조(보험금 지급), 제6조(보상한도액).

p.129-130: 항공기납치 특별약관
          CoverageStd HIJACK으로 매핑. 제1조(지급사유), 제2조(보장범위),
          제3조(다른보험 관계).

p.131-132: 해외여행중 여권분실후 재발급비용 특별약관
          CoverageStd PASSPORT_LOSS로 매핑. 제1조(보상하는손해), 제2조(보상하지않는손해).

p.133-135: 해외여행중 항공기 및 수하물 지연비용 특별약관
          CoverageStd FLIGHT_DELAY로 매핑. 제1조(지급사유), 제2조(보상내용),
          제3조(보상하지않는손해).

p.136-137: 해외여행중 중단사고발생 추가비용 특별약관
          CoverageStd TRIP_INTERRUPTION으로 매핑. 제1조(지급사유), 제2조(보상내용).

p.138-139: 해외여행중 식중독입원일당(4일 이상 120일 한도) 특별약관
          CoverageStd FOOD_POISONING으로 매핑. 제1조(지급사유).

p.140-141: 해외여행중 특정전염병치료비 특별약관
          CoverageStd INFECTIOUS_DISEASE로 매핑. 제1조(지급사유).

p.141-142: 해외여행 상해입원일당(1일 이상 180일 한도) 특별약관
          CoverageStd INJ_HOSPITAL_ALLOWANCE(새 코드) 매핑. 제1조(지급사유).

p.143-144: 해외여행 상해입원일당(4일 이상 30일 한도) 특별약관
          CoverageStd INJ_HOSPITAL_ALLOWANCE로 매핑.

p.145-146: 해외여행 질병입원일당(1일 이상 180일 한도) 특별약관
          CoverageStd ILL_HOSPITAL_ALLOWANCE(새 코드) 매핑. 제1조(지급사유).

p.147: 해외여행 질병입원일당(4일 이상 30일 한도) 특별약관
       CoverageStd ILL_HOSPITAL_ALLOWANCE로 매핑.

멱등성: Coverage는 raw_name, Clause는 (coverage_id, article_no, text) 조합,
        ClauseIncidentMap은 (clause_id, type_id) 조합으로 이미 있으면 건너뛴다.
"""
from app.database import SessionLocal
from app import models  # noqa: F401
from app.models.kb import (
    Clause, ClauseIncidentMap, Coverage, CoverageStd, IncidentType, Insurer, PolicyVersion, Product,
)
from app.services.kb_seed_common import get_or_create_coverage_std


# =========================================================================
# 각 특약별 주요 조항 텍스트 (PDF p.108-147에서 직접 추출)
# =========================================================================

# --- p.108-112: 질병사망 및 질병 80%이상 후유장해 특별약관 ---
ILL_DEATH_CLAUSE1_TEXT = (
    "회사는 피보험자가 보험기간 중에 다음 각 호의 사유가 발생한 때에는 보험수익자에게 약정한 "
    "보험금을 지급합니다. "
    "1. 질병으로 인하여 사망한 경우: 질병사망보험금 "
    "2. 진단확정된 질병으로 장해분류표에서 정한 장해지급률이 80% 이상에 해당하는 "
    "장해상태가 되었을 때: 고도후유장해보험금"
)

ILL_DEATH_CLAUSE2_TEXT = (
    "질병의 직접원인으로 사고일부터 1년 이내에 사망하거나 또는 80% 이상 후유장해가 남았을 경우에도 "
    "동일하게 보상하여 드립니다."
)

# --- p.113-120: 배상책임 특별약관 ---
LIABILITY_CLAUSE1_TEXT = (
    "회사는 피보험자가 여행도중에 생긴 보험사고로 인하여 피해자에게 법률상의 배상책임을 부담함으로써 "
    "입은 손해를 이 특별약관에 따라 보상하여 드립니다."
)

LIABILITY_CLAUSE2_TEXT = (
    "회사가 보상하는 손해의 범위는 아래와 같습니다. "
    "1. 피보험자가 피해자에게 지급할 책임을 지는 법률상의 손해배상금 "
    "2. 계약자 또는 피보험자가 지출한 아래의 비용 - 피보험자가 손해의 방지 또는 경감을 위하여 "
    "지출한 필요 또는 유익하였던 비용, 소송비용, 변호사비용, 중재, 화해 또는 조정에 관한 비용"
)

LIABILITY_CLAUSE3_TEXT = (
    "회사는 아래의 사유로 손해배상책임을 부담하게 됨으로써 입은 손해는 보상하여 드리지 않습니다. "
    "1. 피보험자의 직접적인 직무수행으로 인한 배상책임 "
    "2. 피보험자와 세대를 같이하는 친족에 대한 배상책임 "
    "3. 피보험자가 소유, 사용 또는 관리하는 재물의 파손에 대한 배상책임(호텔의 객실이나 객실내 동산 제외)"
)

# --- p.121-124: 휴대품손해(분실제외) 특별약관 ---
PERSONAL_EFFECTS_CLAUSE1_TEXT = (
    "회사는 피보험자가 여행 도중에 휴대하며 소유, 사용, 관리하는 짐(휴대품)의 손해에 대하여 "
    "이 특별약관에 따라 보상해 드립니다."
)

PERSONAL_EFFECTS_CLAUSE2_TEXT = (
    "회사가 보상하는 손해는 다음과 같습니다. "
    "1. 화재, 폭발, 도난, 강도 등 외래의 사고로 인한 손해 "
    "2. 파손, 손상, 오손 등 물리적 손해"
)

# --- p.125: 휴대품손해 휴대폰한도 감액 추가특별약관 ---
PERSONAL_EFFECTS_PHONE_CLAUSE1_TEXT = (
    "휴대품손해(분실제외) 특별약관 제4조(지급보험금의 계산) 제4항에도 불구하고 보험의 목적이 "
    "휴대폰일 경우 휴대폰 1개에 대하여 회사가 지급할 보험금은 100,000원을 한도로 합니다. "
    "그 외 보험의 목적에 대하여 1개 또는 1조, 1쌍당 회사가 지급할 보험금은 200,000원을 한도로 합니다."
)

# --- p.126-128: 여행중 중대사고 구조송환비용 특별약관 ---
RESCUE_CLAUSE1_TEXT = (
    "회사는 아래의 사유로 계약자, 피보험자 또는 피보험자의 법정상속인이 부담하는 비용을 "
    "이 특별약관에 따라 보상하여 드립니다. "
    "1. 피보험자가 여행 도중에 탑승한 항공기 또는 선박이 행방불명 또는 조난된 경우 또는 "
    "산악등반 중에 조난된 경우 "
    "2. 여행 도중에 급격하고도 우연한 외래의 사고에 따라 긴급수색구조 등이 필요한 상태로 된 경우 "
    "3. 상해를 직접원인으로 사고일부터 1년 이내 사망 또는 규정된 일수 이상 계속 입원한 경우 "
    "4. 질병을 직접 원인으로 여행 도중 사망 또는 규정된 일수 이상 계속 입원한 경우"
)

RESCUE_CLAUSE2_TEXT = (
    "회사가 보상하는 비용의 범위는 아래와 같습니다. "
    "1. 수색구조비용 - 조난당한 피보험자를 수색, 구조 또는 이송하는 활동에 필요한 비용 "
    "2. 항공운임 등 교통비 - 사고발생지 또는 법정상속인의 현지 왕복교통비(2명분 한도) "
    "3. 숙박비 - 현지에서의 구원자 숙박비(2명분, 1명당 14박 한도) "
    "4. 이송비용 - 피보험자 유해 또는 피보험자 이송 비용 "
    "5. 제잡비 - 출입국 절차 필요 비용 등(10만원 한도)"
)

# --- p.129-130: 항공기납치 특별약관 ---
HIJACK_CLAUSE1_TEXT = (
    "회사는 피보험자가 여행 도중에 피보험자가 승객으로서 탑승한 항공기가 납치됨에 따라 "
    "예정목적지에 도착할 수 없게 된 동안에 대하여 매일 70,000원씩 지급하여 드립니다. "
    "항공기의 납치라 함은 부당한 의도를 가진 폭력, 폭행 또는 폭력이나 폭행의 위협으로서 "
    "항공기를 탈취하거나 지배권을 행사하는 것을 말합니다."
)

HIJACK_CLAUSE2_TEXT = (
    "회사는 당해 항공기의 목적지 도착예정시간에서 12시간이 경과된 이후부터 시작되는 24시간을 "
    "1일로 보아 20일을 한도로 보험금을 지급하여 드립니다."
)

# --- p.131-132: 해외여행중 여권분실후 재발급비용 특별약관 ---
PASSPORT_LOSS_CLAUSE1_TEXT = (
    "회사는 피보험자가 해외여행 도중에 여권을 분실하거나 도난당하여 재외공관에 여권분실신고를 하고 "
    "여행증명서(T/C)를 발급받은 경우 여행증명서 발급비용과 여권 재발급비용을 보험수익자에게 지급합니다."
)

PASSPORT_LOSS_CLAUSE2_TEXT = (
    "여행증명서 발급비용 및 여권 재발급비용이란 여행증명서 및 여권 재발급에 관한 수수료로 "
    "여권법 제22조 제1항에서 정한 수수료 및 국제교류기여금을 합한 금액을 말하며 "
    "교통비 및 사진촬영비는 포함되지 않습니다."
)

# --- p.133-135: 해외여행중 항공기 및 수하물 지연비용 특별약관 ---
FLIGHT_DELAY_CLAUSE1_TEXT = (
    "회사는 피보험자가 탑승한 항공기의 출발이 4시간 이상 지연되거나 또는 운항이 취소되거나 "
    "운항편이 변경되어 다음 운항편에 탑승한 경우 또는 항공기 탑승 후 짐(수하물)의 배송이 3일 이상 "
    "지연된 경우에 대하여 이 특별약관에 따라 보상하여 드립니다."
)

FLIGHT_DELAY_CLAUSE2_TEXT = (
    "회사가 보상하는 손해는 다음과 같습니다. "
    "1. 항공기 지연으로 인한 추가 숙박비, 식사비, 교통비, 통신료 등의 손해 "
    "2. 수하물 지연으로 인한 의류, 세면도구 등 필수품 구입비"
)

# --- p.136-137: 해외여행중 중단사고발생 추가비용 특별약관 ---
TRIP_INTERRUPTION_CLAUSE1_TEXT = (
    "회사는 피보험자가 여행을 출발한 후 여행 도중에 급격하고도 우연한 외래의 사고(피보험자 또는 "
    "피보험자의 가족의 질병, 사망 등)으로 인하여 계획된 여행을 중단하고 귀국하여야 하는 경우에 "
    "이 특별약관의 한도 내에서 피보험자가 입은 손해를 이 특별약관에 따라 보상하여 드립니다."
)

TRIP_INTERRUPTION_CLAUSE2_TEXT = (
    "회사가 보상하는 손해는 다음과 같습니다. "
    "1. 여행을 중단하고 귀국하기 위하여 새로 구입한 항공권 등 교통비 "
    "2. 이미 지불한 여행상품대금 중 사용하지 않은 부분"
)

# --- p.138-139: 해외여행중 식중독입원일당 특별약관 ---
FOOD_POISONING_CLAUSE1_TEXT = (
    "회사는 피보험자가 여행 도중에 식중독으로 인하여 4일 이상 입원한 경우에 대하여 "
    "이 특별약관의 보험가입금액을 1일당 보험금으로 하여 최고 120일을 한도로 지급합니다."
)

# --- p.140-141: 해외여행중 특정전염병치료비 특별약관 ---
INFECTIOUS_DISEASE_CLAUSE1_TEXT = (
    "회사는 피보험자가 여행 도중에 감염되어 진단확정된 감염병(신종인플루엔자, 중증급성호흡기증후군, "
    "중동호흡기증후군, 레지오넬라증, 백일해, 성홍열, 파라티푸스, 장티푸스 등)을 직접원인으로 "
    "의료비가 발생한 경우에 이 특별약관에 따라 치료비를 보상하여 드립니다."
)

# --- p.141-142: 해외여행 상해입원일당(1일 이상 180일 한도) 특별약관 ---
INJ_HOSPITAL_ALLOWANCE_CLAUSE1_TEXT = (
    "회사는 피보험자가 여행 도중에 상해를 입어 의사의 치료를 받기 위하여 병원, 한방병원 또는 요양소에 "
    "입원한 경우에 입원일로부터 최고 180일을 한도로 입원 1일에 대하여 "
    "이 특별약관의 보험가입금액을 해외여행 상해입원일당으로 보험수익자에게 지급합니다."
)

# --- p.145-146: 해외여행 질병입원일당(1일 이상 180일 한도) 특별약관 ---
ILL_HOSPITAL_ALLOWANCE_CLAUSE1_TEXT = (
    "회사는 피보험자가 여행 도중에 질병으로 인하여 의사의 치료를 받기 위하여 병원, 한방병원 또는 요양소에 "
    "입원한 경우에 입원일로부터 최고 180일을 한도로 입원 1일에 대하여 "
    "이 특별약관의 보험가입금액을 해외여행 질병입원일당으로 보험수익자에게 지급합니다."
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
        insurer = db.query(Insurer).filter_by(code="MERITZ").first()
        if not insurer:
            print("메리츠화재가 시딩되지 않았습니다. seed_meritz를 먼저 실행하세요.")
            return

        pv = (
            db.query(PolicyVersion)
            .join(Product, Product.product_id == PolicyVersion.product_id)
            .filter(Product.insurer_id == insurer.insurer_id)
            .first()
        )
        if not pv:
            print("메리츠화재 policy_version을 찾을 수 없습니다.")
            return

        types = {t.l2_code: t for t in db.query(IncidentType).all()}
        required = [
            "ILL_DEATH_DISABILITY", "LIA_PERSONAL", "LIA_PROPERTY", "PROP_THEFT", "PROP_DAMAGE", "EMG_RESCUE",
            "TRV_HIJACK", "PROP_PASSPORT_LOSS", "TRV_FLIGHT_DELAY", "CHG_INTERRUPTION",
            "ILL_NEW_1", "ILL_INFECTIOUS"
        ]
        missing = [c for c in required if c not in types]
        if missing:
            print(f"incident_type 사전에 없는 코드: {missing}. seed_incident_types를 확인하세요.")
            return

        # CoverageStd 생성 또는 재사용
        std_ill_death = get_or_create_coverage_std(db, "ILL_DEATH", "질병사망·고도후유장해", "질병", False)
        std_liability = get_or_create_coverage_std(db, "LIABILITY", "배상책임", "배상책임", False)
        std_personal_effects = get_or_create_coverage_std(db, "PERSONAL_EFFECTS", "휴대품손해(분실제외)", "휴대품", False)
        std_rescue = get_or_create_coverage_std(db, "RESCUE", "중대사고 구조송환비용", "구조", False)
        std_hijack = get_or_create_coverage_std(db, "HIJACK", "항공기납치", "특수", False)
        std_passport_loss = get_or_create_coverage_std(db, "PASSPORT_LOSS", "여권분실 재발급비용", "여행변경", False)
        std_flight_delay = get_or_create_coverage_std(db, "FLIGHT_DELAY", "항공기 및 수하물 지연비용", "운송", False)
        std_trip_interruption = get_or_create_coverage_std(db, "TRIP_INTERRUPTION", "여행중단 추가비용", "여행변경", False)
        std_food_poisoning = get_or_create_coverage_std(db, "FOOD_POISONING", "식중독보상금", "질병", False)
        std_infectious_disease = get_or_create_coverage_std(db, "INFECTIOUS_DISEASE", "특정감염병보상금", "질병", False)
        std_inj_hospital = get_or_create_coverage_std(db, "INJ_HOSPITAL_ALLOWANCE", "상해입원일당", "상해", False)
        std_ill_hospital = get_or_create_coverage_std(db, "ILL_HOSPITAL_ALLOWANCE", "질병입원일당", "질병", False)

        clause_created = map_created = coverage_created = 0

        # ===================================================================
        # 1) 질병사망 및 질병 80%이상 후유장해 특별약관 (p.108-112)
        # ===================================================================
        cov_ill_death = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "질병사망 및 질병 80%이상 후유장해 특별약관",
            )
            .first()
        )
        if not cov_ill_death:
            cov_ill_death = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_ill_death.coverage_std_id,
                raw_name="질병사망 및 질병 80%이상 후유장해 특별약관",
                definition=ILL_DEATH_CLAUSE1_TEXT,
                limit_amount="질병사망 또는 질병 80% 이상 고도후유장해",
                deductible=None,
                waiting_condition=None,
            )
            db.add(cov_ill_death)
            db.flush()
            coverage_created += 1

        clause_ill_death_1, c1 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_ill_death.coverage_id,
            clause_type="보장정의", article_no="[질병사망 및 질병 80%이상 후유장해 특별약관] 제1조(보험금의 지급사유)",
            text=ILL_DEATH_CLAUSE1_TEXT, page_ref="p.108", default_color="파랑",
        )
        clause_ill_death_2, c2 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_ill_death.coverage_id,
            clause_type="제한", article_no="[질병사망 및 질병 80%이상 후유장해 특별약관] 제2조(지급세부규정)",
            text=ILL_DEATH_CLAUSE2_TEXT, page_ref="p.108", default_color="초록",
        )
        clause_created += sum([c1, c2])

        ill_death_type = types["ILL_DEATH_DISABILITY"]
        map_created += sum([
            _get_or_create_map(db, clause_id=clause_ill_death_1.clause_id, type_id=ill_death_type.type_id, relevance="직접", confidence=1.0),
            _get_or_create_map(db, clause_id=clause_ill_death_2.clause_id, type_id=ill_death_type.type_id, relevance="조건부", confidence=0.9),
        ])

        # ===================================================================
        # 2) 배상책임 특별약관 (p.113-120)
        # ===================================================================
        cov_liability = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "배상책임 특별약관",
            )
            .first()
        )
        if not cov_liability:
            cov_liability = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_liability.coverage_std_id,
                raw_name="배상책임 특별약관",
                definition=LIABILITY_CLAUSE1_TEXT,
                limit_amount="보험증권 기재 보상한도액",
                deductible=None,
                waiting_condition=None,
            )
            db.add(cov_liability)
            db.flush()
            coverage_created += 1

        clause_lia_1, l1 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_liability.coverage_id,
            clause_type="보장정의", article_no="[배상책임 특별약관] 제1조(보상하는 손해)",
            text=LIABILITY_CLAUSE1_TEXT, page_ref="p.113", default_color="파랑",
        )
        clause_lia_2, l2 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_liability.coverage_id,
            clause_type="보장정의", article_no="[배상책임 특별약관] 제2조(보상범위)",
            text=LIABILITY_CLAUSE2_TEXT, page_ref="p.113", default_color="파랑",
        )
        clause_lia_3, l3 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_liability.coverage_id,
            clause_type="면책", article_no="[배상책임 특별약관] 제3조(보상하지 않는 손해)",
            text=LIABILITY_CLAUSE3_TEXT, page_ref="p.115", default_color="빨강",
        )
        clause_created += sum([l1, l2, l3])

        lia_personal_type = types["LIA_PERSONAL"]
        lia_property_type = types["LIA_PROPERTY"]
        map_created += sum([
            _get_or_create_map(db, clause_id=clause_lia_1.clause_id, type_id=lia_personal_type.type_id, relevance="직접", confidence=1.0),
            _get_or_create_map(db, clause_id=clause_lia_1.clause_id, type_id=lia_property_type.type_id, relevance="직접", confidence=1.0),
            _get_or_create_map(db, clause_id=clause_lia_2.clause_id, type_id=lia_personal_type.type_id, relevance="직접", confidence=1.0),
            _get_or_create_map(db, clause_id=clause_lia_2.clause_id, type_id=lia_property_type.type_id, relevance="직접", confidence=1.0),
            _get_or_create_map(db, clause_id=clause_lia_3.clause_id, type_id=lia_personal_type.type_id, relevance="면책", confidence=0.95),
            _get_or_create_map(db, clause_id=clause_lia_3.clause_id, type_id=lia_property_type.type_id, relevance="면책", confidence=0.95),
        ])

        # ===================================================================
        # 3) 휴대품손해(분실제외) 특별약관 (p.121-124)
        # ===================================================================
        cov_personal_effects = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "휴대품손해(분실제외) 특별약관",
            )
            .first()
        )
        if not cov_personal_effects:
            cov_personal_effects = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_personal_effects.coverage_std_id,
                raw_name="휴대품손해(분실제외) 특별약관",
                definition=PERSONAL_EFFECTS_CLAUSE1_TEXT,
                limit_amount="품목별·1개당 200,000원 한도(휴대폰 100,000원)",
                deductible=None,
                waiting_condition="분실 제외",
            )
            db.add(cov_personal_effects)
            db.flush()
            coverage_created += 1

        clause_pe_1, pe1 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_personal_effects.coverage_id,
            clause_type="보장정의", article_no="[휴대품손해 특별약관] 제1조(보상범위)",
            text=PERSONAL_EFFECTS_CLAUSE1_TEXT, page_ref="p.121", default_color="파랑",
        )
        clause_pe_2, pe2 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_personal_effects.coverage_id,
            clause_type="보장정의", article_no="[휴대품손해 특별약관] 제2조(보상내용)",
            text=PERSONAL_EFFECTS_CLAUSE2_TEXT, page_ref="p.121", default_color="파랑",
        )
        clause_created += sum([pe1, pe2])

        prop_theft_type = types["PROP_THEFT"]
        prop_damage_type = types["PROP_DAMAGE"]
        map_created += sum([
            _get_or_create_map(db, clause_id=clause_pe_1.clause_id, type_id=prop_theft_type.type_id, relevance="직접", confidence=1.0),
            _get_or_create_map(db, clause_id=clause_pe_1.clause_id, type_id=prop_damage_type.type_id, relevance="직접", confidence=1.0),
            _get_or_create_map(db, clause_id=clause_pe_2.clause_id, type_id=prop_theft_type.type_id, relevance="직접", confidence=1.0),
            _get_or_create_map(db, clause_id=clause_pe_2.clause_id, type_id=prop_damage_type.type_id, relevance="직접", confidence=1.0),
        ])

        # ===================================================================
        # 4) 휴대품손해 휴대폰한도 감액 추가특별약관 (p.125)
        # ===================================================================
        cov_personal_effects_phone = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "휴대품손해(분실제외) 휴대폰한도 감액 추가특별약관",
            )
            .first()
        )
        if not cov_personal_effects_phone:
            cov_personal_effects_phone = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_personal_effects.coverage_std_id,
                raw_name="휴대품손해(분실제외) 휴대폰한도 감액 추가특별약관",
                definition=PERSONAL_EFFECTS_PHONE_CLAUSE1_TEXT,
                limit_amount="휴대폰 1개당 100,000원, 기타 물품 200,000원",
                deductible=None,
                waiting_condition=None,
            )
            db.add(cov_personal_effects_phone)
            db.flush()
            coverage_created += 1

        clause_pe_phone_1, pep1 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_personal_effects_phone.coverage_id,
            clause_type="제한", article_no="[휴대폰한도 감액 추가특별약관] 제1조(지급보험금 감액)",
            text=PERSONAL_EFFECTS_PHONE_CLAUSE1_TEXT, page_ref="p.125", default_color="초록",
        )
        clause_created += pep1

        map_created += sum([
            _get_or_create_map(db, clause_id=clause_pe_phone_1.clause_id, type_id=prop_theft_type.type_id, relevance="제한", confidence=0.9),
            _get_or_create_map(db, clause_id=clause_pe_phone_1.clause_id, type_id=prop_damage_type.type_id, relevance="제한", confidence=0.9),
        ])

        # ===================================================================
        # 5) 여행중 중대사고 구조송환비용 특별약관 (p.126-128)
        # ===================================================================
        cov_rescue = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "여행중 중대사고 구조송환비용 특별약관",
            )
            .first()
        )
        if not cov_rescue:
            cov_rescue = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_rescue.coverage_std_id,
                raw_name="여행중 중대사고 구조송환비용 특별약관",
                definition=RESCUE_CLAUSE1_TEXT,
                limit_amount="보험증권 기재 보상한도액(구원자 2명, 숙박 1명당 14박)",
                deductible="1사고당 10만원",
                waiting_condition=None,
            )
            db.add(cov_rescue)
            db.flush()
            coverage_created += 1

        clause_rescue_1, r1 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_rescue.coverage_id,
            clause_type="보장정의", article_no="[여행중 중대사고 구조송환비용 특별약관] 제1조(지급사유)",
            text=RESCUE_CLAUSE1_TEXT, page_ref="p.126", default_color="파랑",
        )
        clause_rescue_2, r2 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_rescue.coverage_id,
            clause_type="보장정의", article_no="[여행중 중대사고 구조송환비용 특별약관] 제2조(비용범위)",
            text=RESCUE_CLAUSE2_TEXT, page_ref="p.126-127", default_color="파랑",
        )
        clause_created += sum([r1, r2])

        rescue_type = types["EMG_RESCUE"]
        map_created += sum([
            _get_or_create_map(db, clause_id=clause_rescue_1.clause_id, type_id=rescue_type.type_id, relevance="직접", confidence=1.0),
            _get_or_create_map(db, clause_id=clause_rescue_2.clause_id, type_id=rescue_type.type_id, relevance="직접", confidence=0.95),
        ])

        # ===================================================================
        # 6) 항공기납치 특별약관 (p.129-130)
        # ===================================================================
        cov_hijack = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "항공기납치 특별약관",
            )
            .first()
        )
        if not cov_hijack:
            cov_hijack = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_hijack.coverage_std_id,
                raw_name="항공기납치 특별약관",
                definition=HIJACK_CLAUSE1_TEXT,
                limit_amount="1일 70,000원 x 20일 한도(최대 1,400,000원)",
                deductible=None,
                waiting_condition="목적지 도착예정시간에서 12시간 경과 후부터",
            )
            db.add(cov_hijack)
            db.flush()
            coverage_created += 1

        clause_hijack_1, h1 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_hijack.coverage_id,
            clause_type="보장정의", article_no="[항공기납치 특별약관] 제1조(지급사유)",
            text=HIJACK_CLAUSE1_TEXT, page_ref="p.129", default_color="파랑",
        )
        clause_hijack_2, h2 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_hijack.coverage_id,
            clause_type="보장정의", article_no="[항공기납치 특별약관] 제2조(보장범위)",
            text=HIJACK_CLAUSE2_TEXT, page_ref="p.129", default_color="파랑",
        )
        clause_created += sum([h1, h2])

        hijack_type = types["TRV_HIJACK"]
        map_created += sum([
            _get_or_create_map(db, clause_id=clause_hijack_1.clause_id, type_id=hijack_type.type_id, relevance="직접", confidence=1.0),
            _get_or_create_map(db, clause_id=clause_hijack_2.clause_id, type_id=hijack_type.type_id, relevance="직접", confidence=0.95),
        ])

        # ===================================================================
        # 7) 해외여행중 여권분실후 재발급비용 특별약관 (p.131-132)
        # ===================================================================
        cov_passport_loss = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "해외여행중 여권분실후 재발급비용 특별약관",
            )
            .first()
        )
        if not cov_passport_loss:
            cov_passport_loss = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_passport_loss.coverage_std_id,
                raw_name="해외여행중 여권분실후 재발급비용 특별약관",
                definition=PASSPORT_LOSS_CLAUSE1_TEXT,
                limit_amount="여행증명서 및 여권 재발급 수수료 + 국제교류기여금",
                deductible=None,
                waiting_condition=None,
            )
            db.add(cov_passport_loss)
            db.flush()
            coverage_created += 1

        clause_passport_1, p1 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_passport_loss.coverage_id,
            clause_type="보장정의", article_no="[여권분실 재발급비용 특별약관] 제1조(보상하는 손해)",
            text=PASSPORT_LOSS_CLAUSE1_TEXT, page_ref="p.131", default_color="파랑",
        )
        clause_passport_2, p2 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_passport_loss.coverage_id,
            clause_type="보장정의", article_no="[여권분실 재발급비용 특별약관] 제2조(비용 정의)",
            text=PASSPORT_LOSS_CLAUSE2_TEXT, page_ref="p.131", default_color="파랑",
        )
        clause_created += sum([p1, p2])

        passport_loss_type = types["PROP_PASSPORT_LOSS"]
        map_created += sum([
            _get_or_create_map(db, clause_id=clause_passport_1.clause_id, type_id=passport_loss_type.type_id, relevance="직접", confidence=1.0),
            _get_or_create_map(db, clause_id=clause_passport_2.clause_id, type_id=passport_loss_type.type_id, relevance="조건부", confidence=0.95),
        ])

        # ===================================================================
        # 8) 해외여행중 항공기 및 수하물 지연비용 특별약관 (p.133-135)
        # ===================================================================
        cov_flight_delay = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "해외여행중 항공기 및 수하물 지연비용 특별약관",
            )
            .first()
        )
        if not cov_flight_delay:
            cov_flight_delay = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_flight_delay.coverage_std_id,
                raw_name="해외여행중 항공기 및 수하물 지연비용 특별약관",
                definition=FLIGHT_DELAY_CLAUSE1_TEXT,
                limit_amount="보험증권 기재 보상한도액(항공기 4시간 지연, 수하물 3일 지연)",
                deductible=None,
                waiting_condition=None,
            )
            db.add(cov_flight_delay)
            db.flush()
            coverage_created += 1

        clause_flight_delay_1, fd1 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_flight_delay.coverage_id,
            clause_type="보장정의", article_no="[항공기 수하물 지연비용 특별약관] 제1조(지급사유)",
            text=FLIGHT_DELAY_CLAUSE1_TEXT, page_ref="p.133", default_color="파랑",
        )
        clause_flight_delay_2, fd2 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_flight_delay.coverage_id,
            clause_type="보장정의", article_no="[항공기 수하물 지연비용 특별약관] 제2조(보상내용)",
            text=FLIGHT_DELAY_CLAUSE2_TEXT, page_ref="p.133", default_color="파랑",
        )
        clause_created += sum([fd1, fd2])

        flight_delay_type = types["TRV_FLIGHT_DELAY"]
        map_created += sum([
            _get_or_create_map(db, clause_id=clause_flight_delay_1.clause_id, type_id=flight_delay_type.type_id, relevance="직접", confidence=1.0),
            _get_or_create_map(db, clause_id=clause_flight_delay_2.clause_id, type_id=flight_delay_type.type_id, relevance="직접", confidence=0.95),
        ])

        # ===================================================================
        # 9) 해외여행중 중단사고발생 추가비용 특별약관 (p.136-137)
        # ===================================================================
        cov_trip_interruption = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "해외여행중 중단사고발생 추가비용 특별약관",
            )
            .first()
        )
        if not cov_trip_interruption:
            cov_trip_interruption = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_trip_interruption.coverage_std_id,
                raw_name="해외여행중 중단사고발생 추가비용 특별약관",
                definition=TRIP_INTERRUPTION_CLAUSE1_TEXT,
                limit_amount="보험증권 기재 보상한도액",
                deductible=None,
                waiting_condition=None,
            )
            db.add(cov_trip_interruption)
            db.flush()
            coverage_created += 1

        clause_trip_int_1, ti1 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_trip_interruption.coverage_id,
            clause_type="보장정의", article_no="[여행중단 추가비용 특별약관] 제1조(지급사유)",
            text=TRIP_INTERRUPTION_CLAUSE1_TEXT, page_ref="p.136", default_color="파랑",
        )
        clause_trip_int_2, ti2 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_trip_interruption.coverage_id,
            clause_type="보장정의", article_no="[여행중단 추가비용 특별약관] 제2조(보상내용)",
            text=TRIP_INTERRUPTION_CLAUSE2_TEXT, page_ref="p.136", default_color="파랑",
        )
        clause_created += sum([ti1, ti2])

        trip_interruption_type = types["CHG_INTERRUPTION"]
        map_created += sum([
            _get_or_create_map(db, clause_id=clause_trip_int_1.clause_id, type_id=trip_interruption_type.type_id, relevance="직접", confidence=1.0),
            _get_or_create_map(db, clause_id=clause_trip_int_2.clause_id, type_id=trip_interruption_type.type_id, relevance="직접", confidence=0.95),
        ])

        # ===================================================================
        # 10) 해외여행중 식중독입원일당 특별약관 (p.138-139)
        # ===================================================================
        cov_food_poisoning = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "해외여행중 식중독입원일당 특별약관",
            )
            .first()
        )
        if not cov_food_poisoning:
            cov_food_poisoning = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_food_poisoning.coverage_std_id,
                raw_name="해외여행중 식중독입원일당 특별약관",
                definition=FOOD_POISONING_CLAUSE1_TEXT,
                limit_amount="1일당 보험가입금액 x 120일 한도",
                deductible=None,
                waiting_condition="4일 이상 입원",
            )
            db.add(cov_food_poisoning)
            db.flush()
            coverage_created += 1

        clause_food_poisoning_1, fp1 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_food_poisoning.coverage_id,
            clause_type="보장정의", article_no="[식중독입원일당 특별약관] 제1조(지급사유)",
            text=FOOD_POISONING_CLAUSE1_TEXT, page_ref="p.138", default_color="파랑",
        )
        clause_created += fp1

        food_poisoning_type = types["ILL_NEW_1"]  # 삼성화재 딥다이브에서 만든 "식중독보상금(입원)" 재사용
        map_created += _get_or_create_map(db, clause_id=clause_food_poisoning_1.clause_id, type_id=food_poisoning_type.type_id, relevance="직접", confidence=1.0)

        # ===================================================================
        # 11) 해외여행중 특정전염병치료비 특별약관 (p.140-141)
        # ===================================================================
        cov_infectious_disease = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "해외여행중 특정전염병치료비 특별약관",
            )
            .first()
        )
        if not cov_infectious_disease:
            cov_infectious_disease = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_infectious_disease.coverage_std_id,
                raw_name="해외여행중 특정전염병치료비 특별약관",
                definition=INFECTIOUS_DISEASE_CLAUSE1_TEXT,
                limit_amount="보험증권 기재 보상한도액",
                deductible=None,
                waiting_condition=None,
            )
            db.add(cov_infectious_disease)
            db.flush()
            coverage_created += 1

        clause_infectious_disease_1, id1 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_infectious_disease.coverage_id,
            clause_type="보장정의", article_no="[특정전염병 치료비 특별약관] 제1조(지급사유)",
            text=INFECTIOUS_DISEASE_CLAUSE1_TEXT, page_ref="p.140", default_color="파랑",
        )
        clause_created += id1

        infectious_disease_type = types["ILL_INFECTIOUS"]
        map_created += _get_or_create_map(db, clause_id=clause_infectious_disease_1.clause_id, type_id=infectious_disease_type.type_id, relevance="직접", confidence=1.0)

        # ===================================================================
        # 12) 해외여행 상해입원일당(1일 이상 180일 한도) 특별약관 (p.141-142)
        # ===================================================================
        cov_inj_hospital_180 = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "해외여행 상해입원일당(1일 이상 180일 한도) 특별약관",
            )
            .first()
        )
        if not cov_inj_hospital_180:
            cov_inj_hospital_180 = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_inj_hospital.coverage_std_id,
                raw_name="해외여행 상해입원일당(1일 이상 180일 한도) 특별약관",
                definition=INJ_HOSPITAL_ALLOWANCE_CLAUSE1_TEXT,
                limit_amount="1일당 보험가입금액 x 180일 한도",
                deductible=None,
                waiting_condition="1일 이상 입원",
            )
            db.add(cov_inj_hospital_180)
            db.flush()
            coverage_created += 1

        clause_inj_hosp_180_1, ij1 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_inj_hospital_180.coverage_id,
            clause_type="보장정의", article_no="[상해입원일당(1일/180일) 특별약관] 제1조(지급사유)",
            text=INJ_HOSPITAL_ALLOWANCE_CLAUSE1_TEXT, page_ref="p.141", default_color="파랑",
        )
        clause_created += ij1

        inj_hospital_type = types.get("INJ_OVERSEAS_TREATMENT")  # 정액 입원일당 특약 - 조건부 지급구조 변형이라 기존 L2 재사용
        if inj_hospital_type:
            map_created += _get_or_create_map(db, clause_id=clause_inj_hosp_180_1.clause_id, type_id=inj_hospital_type.type_id, relevance="직접", confidence=1.0)

        # ===================================================================
        # 13) 해외여행 상해입원일당(4일 이상 30일 한도) 특별약관 (p.143-144)
        # ===================================================================
        cov_inj_hospital_30 = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "해외여행 상해입원일당(4일 이상 30일 한도) 특별약관",
            )
            .first()
        )
        if not cov_inj_hospital_30:
            cov_inj_hospital_30 = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_inj_hospital.coverage_std_id,
                raw_name="해외여행 상해입원일당(4일 이상 30일 한도) 특별약관",
                definition="피보험자가 여행 도중에 상해로 인하여 4일 이상 입원한 경우 입원일로부터 최고 30일을 한도로 입원 1일에 대하여 보험가입금액을 지급합니다.",
                limit_amount="1일당 보험가입금액 x 30일 한도",
                deductible=None,
                waiting_condition="4일 이상 입원",
            )
            db.add(cov_inj_hospital_30)
            db.flush()
            coverage_created += 1

        clause_inj_hosp_30_1, ij2 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_inj_hospital_30.coverage_id,
            clause_type="보장정의", article_no="[상해입원일당(4일/30일) 특별약관] 제1조(지급사유)",
            text="피보험자가 여행 도중에 상해로 인하여 4일 이상 입원한 경우 입원일로부터 최고 30일을 한도로 입원 1일에 대하여 보험가입금액을 지급합니다.",
            page_ref="p.143", default_color="파랑",
        )
        clause_created += ij2

        if inj_hospital_type:
            map_created += _get_or_create_map(db, clause_id=clause_inj_hosp_30_1.clause_id, type_id=inj_hospital_type.type_id, relevance="직접", confidence=1.0)

        # ===================================================================
        # 14) 해외여행 질병입원일당(1일 이상 180일 한도) 특별약관 (p.145-146)
        # ===================================================================
        cov_ill_hospital_180 = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "해외여행 질병입원일당(1일 이상 180일 한도) 특별약관",
            )
            .first()
        )
        if not cov_ill_hospital_180:
            cov_ill_hospital_180 = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_ill_hospital.coverage_std_id,
                raw_name="해외여행 질병입원일당(1일 이상 180일 한도) 특별약관",
                definition=ILL_HOSPITAL_ALLOWANCE_CLAUSE1_TEXT,
                limit_amount="1일당 보험가입금액 x 180일 한도",
                deductible=None,
                waiting_condition="1일 이상 입원",
            )
            db.add(cov_ill_hospital_180)
            db.flush()
            coverage_created += 1

        clause_ill_hosp_180_1, il1 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_ill_hospital_180.coverage_id,
            clause_type="보장정의", article_no="[질병입원일당(1일/180일) 특별약관] 제1조(지급사유)",
            text=ILL_HOSPITAL_ALLOWANCE_CLAUSE1_TEXT, page_ref="p.145", default_color="파랑",
        )
        clause_created += il1

        ill_hospital_type = types.get("ILL_OVERSEAS_TREATMENT")  # 정액 입원일당 특약 - 조건부 지급구조 변형이라 기존 L2 재사용
        if ill_hospital_type:
            map_created += _get_or_create_map(db, clause_id=clause_ill_hosp_180_1.clause_id, type_id=ill_hospital_type.type_id, relevance="직접", confidence=1.0)

        # ===================================================================
        # 15) 해외여행 질병입원일당(4일 이상 30일 한도) 특별약관 (p.147)
        # ===================================================================
        cov_ill_hospital_30 = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "해외여행 질병입원일당(4일 이상 30일 한도) 특별약관",
            )
            .first()
        )
        if not cov_ill_hospital_30:
            cov_ill_hospital_30 = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_ill_hospital.coverage_std_id,
                raw_name="해외여행 질병입원일당(4일 이상 30일 한도) 특별약관",
                definition="피보험자가 여행 도중에 질병으로 인하여 4일 이상 입원한 경우 입원일로부터 최고 30일을 한도로 입원 1일에 대하여 보험가입금액을 지급합니다.",
                limit_amount="1일당 보험가입금액 x 30일 한도",
                deductible=None,
                waiting_condition="4일 이상 입원",
            )
            db.add(cov_ill_hospital_30)
            db.flush()
            coverage_created += 1

        clause_ill_hosp_30_1, il2 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_ill_hospital_30.coverage_id,
            clause_type="보장정의", article_no="[질병입원일당(4일/30일) 특별약관] 제1조(지급사유)",
            text="피보험자가 여행 도중에 질병으로 인하여 4일 이상 입원한 경우 입원일로부터 최고 30일을 한도로 입원 1일에 대하여 보험가입금액을 지급합니다.",
            page_ref="p.147", default_color="파랑",
        )
        clause_created += il2

        if ill_hospital_type:
            map_created += _get_or_create_map(db, clause_id=clause_ill_hosp_30_1.clause_id, type_id=ill_hospital_type.type_id, relevance="직접", confidence=1.0)

        db.commit()
        print(f"메리츠 청크2 시딩 완료: Coverage {coverage_created}개, Clause {clause_created}개, ClauseIncidentMap {map_created}개")

    except Exception as e:
        db.rollback()
        print(f"오류 발생: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
