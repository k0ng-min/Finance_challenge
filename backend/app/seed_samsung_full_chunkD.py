"""
삼성화재 전체 정독 청크 D — PDF p.130~148 (소형 특약 9개 몰림 구간)
data/raw_pdfs/samsung_overseas_50002_0_20240401.pdf (전체 252쪽 중 일부)

담당 범위(작업 지시상 p.130~154였으나, 지정된 9개 특약은 실제로 p.148에서 끝난다.
p.149(여행중 자택 도난손해), p.153(의사상자 상해위험), p.154(전쟁위험), p.155(부부확장)는
지시에 나열된 9개 특약에 포함되지 않으므로 이 스크립트에서 다루지 않는다 — 다른 청크
담당 또는 후속 작업 대상).

발견 요약(9개 특약, PDF pdfplumber 1-based 페이지 번호 기준):

1. 항공기 및 수하물 지연∙결항 추가비용 특별약관 (p.130~133)
   - 제1조(보상하는 손해): 항공편 4시간이상 지연/결항/환승실패 + 위탁수하물 6시간지연/손실
     을 한 조항 안에서 같이 정의한다 → TRV_FLIGHT_DELAY·TRV_BAGGAGE_DELAY·TRV_BAGGAGE_LOSS
     세 유형 모두에 직접 매핑(위탁수하물이 24시간 내 미도착 시 "영구적으로 손실된 것으로
     간주"하는 항목이 있어 수하물분실도 포함됨).
   - 제2조(보상하지 않는 손해, p.131): 전쟁/불법행위/조종사직무/압수/수하물 미통보 등.

2. 항공기 지연비용 전자 바우처 보상 추가특별약관 (p.134)
   - 제1조: 1번 특약의 "4시간이상 지연" 사유에 한해 라운지 전자 바우처를 추가 제공.
   - 이 추가특별약관 자체에는 면책 조항이 없음(제3조 준용규정으로 1번 특약·보통약관을
     따름) — 새 면책 Clause를 만들지 않고 정직히 생략.

3. 출국 항공기 지연 손해 특별약관 (p.135~137)
   - 제1조: 국내공항 출발 국제선의 "출발 지연"(증권 기재 지연시간 이상, 결항 제외)
   - 제2조(p.135~136): 전쟁/불법행위/조종사직무/항공권 임의취소/간접손해 면책.

4. 출국 항공기 결항 손해보장 추가특별약관 (p.138)
   - 제1조: 3번 특약을 준용하되 "결항"으로 확장.
   - 이 추가특별약관 자체에는 면책 조항이 없음(제2조 준용규정 — 3번 특약 및 보통약관을
     따름) — 새 면책 Clause를 만들지 않고 정직히 생략.

5. 항공기 지연사고발생 반려견(묘) 돌봄서비스 추가비용 보상 특별약관 (p.139~141)
   - 제1조(p.139~140): 귀국 항공편이 4시간이상 지연/결항되어 위탁돌봄/펫시터 픽업을
     못한 경우 추가비용 보상 → SPC_PET_CARE.
   - 제2조(p.140): 고의/중과실, 천재지변, 전쟁, 방사능, 위탁업자 고의·부주의, 조종사
     직무, 계약전 발생·공지된 지연사유 면책.

6. 여행중 식중독보상금(2일이상 입원) 특별약관 (p.142~143)
   - 제1조(p.142): 식중독으로 2일이상 입원 시 정액 보상금(외래진료만은 제외).
   - ILL의 4개 기존 L2(사망·후유장해/해외치료/국내치료/감염병·격리) 중 정확히 맞는 게
     없다 — 이건 "정액 보상금"이지 치료비 실손이 아니고, 감염병도 아니다. 지시에 따라
     needs_review=True인 새 IncidentType(l1_code="ILL", name="식중독보상금(입원)")을
     incident_classify_gemini.create_reviewable_type과 같은 패턴으로 새로 만들어 매핑한다
     (조용히 빠뜨리지 않음).
   - 별도 면책(보상하지 않는 손해) 조항이 이 특약 자체에는 없음 — 제2조는 사망 시
     진단확정일 처리에 관한 지급 세부규정이라 clause_type="조건"으로 별도 수록.

7. 여행중 특정감염병보상금 특별약관 (p.143~144)
   - 제1조(p.143): 특정감염병으로 신고·진단확정 시 정액 보상금 → ILL_INFECTIOUS.
   - 이 특약 자체에는 면책(보상하지 않는 손해) 조항이 없음 — 제2조(사망 시 처리)·제3조
     (특정감염병 정의·진단확정 요건)를 clause_type="조건"으로 수록(진단확정 요건은
     실제 청구 판단에 필요).

8. 여행중 중단사고발생 추가비용 특별약관 (p.145~146)
   - 제1조(p.145): 본인/가족 3일이상 입원, 3촌이내 친족·동반자 사망, 천재지변, 전쟁 등
     사유로 불가피하게 여행을 중단·귀국할 때 추가비용 보상 → CHG_INTERRUPTION.
   - 제3조(p.145~146, 조건): 보상 비용 범위(교통비 차액, 2박 이내 숙박비 차액).
   - 제4조(p.146, 면책): 보통약관 제5조 제1항 제1호~제3호(고의) 사유 면책.

9. 여행중 여권분실 재발급비용 특별약관 (p.147~148)
   - 제1조(p.147): 해외에서 여권 분실·도난 → 재외공관 신고 + 여행증명서 발급 시 여행증명서
     발급비용·여권 재발급비용 지급 → PROP_PASSPORT_LOSS.
   - 제2조(p.147, 면책): 계약자/피보험자 고의, 동반친족·고용인의 고의, 공권력행사(화재·
     소방·피난 목적 제외), 선박·항공승무원의 직무중 분실·도난.

새 CoverageStd(충돌 방지용 신규 코드, 지시받은 6개):
  FLIGHT_DELAY(운송) / PET_CARE(특수) / FOOD_POISONING(질병) / INFECTIOUS_DISEASE(질병) /
  TRIP_INTERRUPTION(여행변경) / PASSPORT_LOSS(휴대품)
1~4번 특약은 위험이 겹치는 변형들이라 전부 FLIGHT_DELAY 하나로 묶되, Coverage 행은
PDF의 실제 특약명 그대로 4개 별도로 만든다(지시사항 그대로).

멱등성: Coverage는 (policy_version_id, raw_name)으로, Clause는 (coverage_id, text)로
중복 검사한다. 여러 번 실행해도 안전하다.
"""
from app.database import SessionLocal
from app import models  # noqa: F401
from app.models.kb import Clause, ClauseIncidentMap, Coverage, IncidentType, PolicyVersion, Product, Insurer
from app.services.kb_seed_common import get_or_create_coverage_std


def get_or_create_coverage(db, pv_id, raw_name, coverage_std_id, definition=None,
                            limit_amount=None, deductible=None, waiting_condition=None):
    existing = (
        db.query(Coverage)
        .filter(Coverage.policy_version_id == pv_id, Coverage.raw_name == raw_name)
        .first()
    )
    if existing:
        return existing, False
    cov = Coverage(
        policy_version_id=pv_id, coverage_std_id=coverage_std_id, raw_name=raw_name,
        definition=definition, limit_amount=limit_amount, deductible=deductible,
        waiting_condition=waiting_condition,
    )
    db.add(cov)
    db.flush()
    return cov, True


def get_or_create_clause(db, pv_id, coverage_id, clause_type, article_no, text, page_ref, default_color):
    existing = (
        db.query(Clause)
        .filter(Clause.coverage_id == coverage_id, Clause.text == text)
        .first()
    )
    if existing:
        return existing, False
    clause = Clause(
        policy_version_id=pv_id, coverage_id=coverage_id, clause_type=clause_type,
        article_no=article_no, text=text, page_ref=page_ref, default_color=default_color,
    )
    db.add(clause)
    db.flush()
    return clause, True


def get_or_create_map(db, clause_id, type_id, relevance, confidence=1.0):
    existing = (
        db.query(ClauseIncidentMap)
        .filter_by(clause_id=clause_id, type_id=type_id, relevance=relevance)
        .first()
    )
    if existing:
        return existing, False
    m = ClauseIncidentMap(
        clause_id=clause_id, type_id=type_id, relevance=relevance,
        mapped_by="human", confidence=confidence,
    )
    db.add(m)
    db.flush()
    return m, True


def get_or_create_food_poisoning_type(db):
    """ILL 기존 4개 L2 어디에도 정확히 맞지 않는 "식중독(정액 입원보상금)" 유형을
    incident_classify_gemini.create_reviewable_type과 같은 패턴으로 새로 만든다."""
    name = "식중독보상금(입원)"
    existing = db.query(IncidentType).filter_by(l1_code="ILL", name=name).first()
    if existing:
        return existing, False
    root = db.query(IncidentType).filter_by(l1_code="ILL", parent_id=None).first()
    n = (
        db.query(IncidentType)
        .filter(IncidentType.l1_code == "ILL", IncidentType.needs_review.is_(True))
        .count() + 1
    )
    new_type = IncidentType(
        l1_code="ILL", l2_code=f"ILL_NEW_{n}", name=name,
        parent_id=root.type_id if root else None, is_active=True, needs_review=True,
    )
    db.add(new_type)
    db.flush()
    return new_type, True


def run():
    db = SessionLocal()
    try:
        insurer = db.query(Insurer).filter_by(code="SAMSUNG").first()
        if not insurer:
            print("삼성화재가 아직 시딩되지 않았습니다. seed_samsung을 먼저 실행하세요.")
            return
        pv = (
            db.query(PolicyVersion)
            .join(Product, Product.product_id == PolicyVersion.product_id)
            .filter(Product.insurer_id == insurer.insurer_id)
            .first()
        )
        pv_id = pv.policy_version_id

        # --- 표준담보 6종 (신규 코드, get_or_create) ---
        std_flight_delay = get_or_create_coverage_std(db, "FLIGHT_DELAY", "항공기 지연·결항", "운송", False)
        std_pet_care = get_or_create_coverage_std(db, "PET_CARE", "반려동물 돌봄서비스", "특수", False)
        std_food_poisoning = get_or_create_coverage_std(db, "FOOD_POISONING", "식중독보상금", "질병", False)
        std_infectious = get_or_create_coverage_std(db, "INFECTIOUS_DISEASE", "특정감염병보상금", "질병", False)
        std_interruption = get_or_create_coverage_std(db, "TRIP_INTERRUPTION", "여행중단 추가비용", "여행변경", False)
        std_passport_loss = get_or_create_coverage_std(db, "PASSPORT_LOSS", "여권분실 재발급비용", "휴대품", False)

        # --- 사고유형 조회 ---
        it = {
            l2: db.query(IncidentType).filter_by(l2_code=l2).first()
            for l2 in [
                "TRV_FLIGHT_DELAY", "TRV_BAGGAGE_DELAY", "TRV_BAGGAGE_LOSS",
                "SPC_PET_CARE", "ILL_INFECTIOUS", "CHG_INTERRUPTION", "PROP_PASSPORT_LOSS",
            ]
        }
        missing = [k for k, v in it.items() if v is None]
        if missing:
            print(f"경고: incident_type 누락 {missing} — seed_incident_types를 먼저 실행하세요.")
            return

        food_poisoning_type, food_poisoning_type_created = get_or_create_food_poisoning_type(db)

        n_cov = n_clause = n_map = 0

        # =====================================================================
        # 1. 항공기 및 수하물 지연∙결항 추가비용 특별약관 (p.130~133)
        # =====================================================================
        cov1, created = get_or_create_coverage(
            db, pv_id, "항공기 및 수하물 지연∙결항 추가비용 특별약관", std_flight_delay.coverage_std_id,
            definition=(
                "회사는 피보험자가 보험기간 중 아래의 보험사고로 인하여 추가적으로 부담한 비용 "
                "손해를 이 특별약관에서 정한 바에 따라 보험가입금액 한도 내에서 보상합니다. "
                "(항공편 4시간이상 지연/결항/환승실패 및 위탁수하물 6시간지연·손실을 함께 정의)"
            ),
            limit_amount="보험가입금액 한도(항목별 비용 보상)",
            waiting_condition="유료승객으로서 정기항공편 이용 중 발생한 사고에 한함",
        )
        n_cov += created

        text1_def = (
            "① 회사는 피보험자가 보험기간 중 아래의 보험사고로 인하여 추가적으로 부담한 비용 손해를 "
            "이 특별약관에서 정한 바에 따라 보험가입금액 한도 내에서 보상합니다. 보장항목 보상하는 사항 "
            "1. 항공편이 4시간이상 지연되는 경우 "
            "2. 항공편이 결항되거나 피보험자가 과적에 의해 탑승이 거부되어 출발예정시각으로부터 4시간 "
            "내에 대체 항공편이 제공되지 못하는 경우 "
            "3. 항공편이 4시간이상 지연되고, 이로 인해 연결항공편으로의 환승에 필요한 시간이 부족하여"
            "(공항 도착시간으로부터 연결항공편 출발까지 항공기 남은 시간이 1시간 이하인 경우를 말합니다) "
            "탑승에 실패하는 경우 지연/결항 <용어 풀이> 결항: 항공기의 운항스케줄이 취소된 경우와 항공기가 "
            "회항하여 출발공항 또는 교체공항에 최종 착륙한 경우를 말합니다. 연결항공편: 직전 항공편이 "
            "도착한 시점으로부터 해당 공항에서 24시간 내에 출발하는 항공편으로 직전 항공편의 출발 전 예약이 "
            "확약되어있는 항공편을 말합니다. "
            "4. 피보험자의 위탁수하물이 항공편의 예정된 도착시각으로부터 6시간 이후에 피보험자에게 도착하는 경우 "
            "위탁수하물 5. 피보험자의 위탁수하물이 손실되거나 또는 피보험자가 목적지(주거지는 지연/손실 "
            "제외합니다)에 도착한 후 24시간 내에 등록된 수하물이 피보험자에게 도착하지 못하는 경우(이 경우 "
            "해당 수하물은 영구적으로 손실된 것으로 간주됩니다) "
            "② 제1항의 보험사고로 인하여 회사가 보상하는 손해는 아래와 같습니다. 보장항목 보상하는 사항 "
            "1. 지연된 항공편 또는 대체 항공편을 기다리는 동안 발생한 식사 및 간식, 항공기 전화 통화 비용 "
            "지연/결항 2. 지연된 항공편 또는 대체 항공편을 탑승하기 위해 숙박이 필요한 경우 숙박비 및 해당 "
            "숙박시설로 이동하기 위한 교통비 "
            "3. 위탁수하물 지연의 경우 비상 의복과 생활필수품의 구입에 소요되는 위탁수하물 비용 "
            "지연/손실 4. 위탁수하물 손실의 경우 비상 의복과 생활필수품 등에 대하여 예정된 도착지(주거지는 "
            "제외합니다)에 도착 후 120시간 내에 발생한 비용 "
            "③ 회사는 피보험자가 보험기간 중 유료승객으로서 정기항공편을 이용하던 중에 발생한 사고에 한하여 "
            "보상합니다."
        )
        clause1_def, created = get_or_create_clause(
            db, pv_id, cov1.coverage_id, "보장정의", "제1조(보상하는 손해)", text1_def, "p.130-131", "파랑",
        )
        n_clause += created
        if created:
            for l2 in ["TRV_FLIGHT_DELAY", "TRV_BAGGAGE_DELAY", "TRV_BAGGAGE_LOSS"]:
                _, mc = get_or_create_map(db, clause1_def.clause_id, it[l2].type_id, "직접")
                n_map += mc

        text1_waiver = (
            "회사는 아래의 사유로 생긴 손해는 보상하여 드리지 않습니다. "
            "1. 명시적 또는 실질적 형태의 정부의 육, 해, 공 군사력에 의한 선포 또는 비선포된 전쟁 또는 "
            "이에 따르는 행위 "
            "2. 피보험자 또는 그 수혜자들에 의하거나 또는 이들을 위해 행해진 불법적인 행동 "
            "3. 교통수단의 조작자 또는 조종자로 종사하는 상황에서 발생한 손실 "
            "4. 세관 또는 여타 정부기관에 의한 압수 또는 보관조치 "
            "5. 피보험자가 수하물을 회수하는 데에 필요한 합리적인 노력을 행하지 않은 경우 "
            "6. 목적지에서 수하물 손실에 관련된 항공사 또는 관련 기관에 통보하고 재산손실보고를 취하지 "
            "않은 경우 "
            "7. 항공사 또는 그 지정자나 대리인에 대해 수하물을 포기하는 경우 "
            "8. 보험사고로 인하여 피보험자가 직접적으로 부담한 비용이 아닌 모든 간접 손해 (예정되었던 "
            "여행일정(숙박, 다른 교통수단, 관광지의 입장권 등)의 취소에 따른 수수료 등) "
            "9. 대체항공편에 탑승한 이후에 발생하는 비용(대체항공편이 착륙한 지역에서의 비용 등)"
        )
        clause1_waiver, created = get_or_create_clause(
            db, pv_id, cov1.coverage_id, "면책", "제2조(보상하지 않는 손해)", text1_waiver, "p.131", "빨강",
        )
        n_clause += created
        if created:
            for l2 in ["TRV_FLIGHT_DELAY", "TRV_BAGGAGE_DELAY", "TRV_BAGGAGE_LOSS"]:
                _, mc = get_or_create_map(db, clause1_waiver.clause_id, it[l2].type_id, "면책")
                n_map += mc

        # =====================================================================
        # 2. 항공기 지연비용 전자 바우처 보상 추가특별약관 (p.134)
        # 면책 조항 없음(제3조 준용규정으로 1번 특약 및 보통약관을 따름) — 정직히 생략.
        # =====================================================================
        cov2, created = get_or_create_coverage(
            db, pv_id, "항공기 지연비용 전자 바우처 보상 추가특별약관", std_flight_delay.coverage_std_id,
            definition=(
                "항공기 및 수하물 지연∙결항 추가비용 특별약관의 '항공편 4시간이상 지연' 사유에 한해 "
                "라운지 이용 전자 바우처를 제공하고, 전자 바우처 사용으로 발생한 라운지 이용 비용을 "
                "식사·간식·숙박 비용에 준하여 보상"
            ),
            limit_amount="항공기 및 수하물 지연∙결항 추가비용 특별약관 보험가입금액 한도 내(해당 금액 차감)",
        )
        n_cov += created
        text2_def = (
            "① 회사는 항공기 및 수하물 지연∙결항 추가비용 특별약관 제1조(보상하는 손해) 제1항 보장 항목 "
            "항공기 지연/결항의 보상하는 사항 제1호에 따른 항공편이 4시간 이상 지연되는 경우에 한하여 이 "
            "추가특별약관을 적용합니다. "
            "② 회사는 항공기 및 수하물 지연∙결항 추가비용 특별약관 제1조(보상하는 손해) 제2항에 추가하여 "
            "지연된 항공편을 기다리는 동안 사용할 수 있는 라운지 이용 전자 바우처를 제공할 수 있으며, "
            "피보험자가 전자 바우처를 사용해 발생한 라운지 이용 비용을 식사, 간식, 숙박 비용에 준하는 "
            "비용으로 보아 보상하여 드립니다. "
            "<용어해설> 전자 바우처: 공항의 라운지를 별도의 비용 결제없이 이용할 수 있는 이용권으로 QR코드 "
            "및 바코드, URL 등의 형태로써 문자메시지 등의 전자적 방식으로 제공하는 것을 말합니다."
        )
        clause2_def, created = get_or_create_clause(
            db, pv_id, cov2.coverage_id, "보장정의", "제1조(보상하는 손해)", text2_def, "p.134", "파랑",
        )
        n_clause += created
        if created:
            _, mc = get_or_create_map(db, clause2_def.clause_id, it["TRV_FLIGHT_DELAY"].type_id, "직접")
            n_map += mc

        # =====================================================================
        # 3. 출국 항공기 지연 손해 특별약관 (p.135~137)
        # =====================================================================
        cov3, created = get_or_create_coverage(
            db, pv_id, "출국 항공기 지연 손해 특별약관", std_flight_delay.coverage_std_id,
            definition=(
                "국내공항에서 출발하는 국제선 항공편이 증권에 기재된 지연시간 이상 출발 지연된 경우"
                "(결항 제외) 지연 중 실제 지출한 식음료·편의시설 비용 및 교통비를 보상"
            ),
            limit_amount="보험가입금액 한도",
        )
        n_cov += created
        text3_def = (
            "① 회사는 피보험자가 보험기간 중 아래의 보험사고로 인하여 추가적으로 부담한 비용 손해를 이 "
            "특별약관에서 정한 바에 따라 보험가입금액 한도 내에서 보상합니다. "
            "1. 국내공항에서 출발하는 국제선 항공편(국내외 항공사를 모두 포함합니다)이 보험증권에 기재된 "
            "지연 시간에 해당되는 출발 지연이 발생한 경우(단, 항공편이 결항되는 경우는 제외합니다) "
            "<용어 풀이> 【출발 지연】 항공기 접속, 항공기 정비, 항로 혼잡, 기상 상황, 여객 처리 등의 사유로 "
            "인해 항공편이 출발계획시간 대비 실제출발시간까지 지연되는 것을 의미합니다. 【항공편의 출발계획"
            "시간】 항공사가 공항공사 등 관련기관에 항공편의 출발계획시간으로 등록한 시간을 기준으로 합니다. "
            "(원래의 출발계획시각 24시간 이전에 예정시각의 변경이 발생한 경우 변경된 시각을 출발계획시간으로 "
            "합니다) 【항공편의 실제출발시간】 공항공사 등 관련기관에 등록된 항공편의 실제출발시간을 의미합니다. "
            "【결항】 항공기의 운항스케줄이 취소된 경우와 항공기가 회항하여 출발공항 또는 교체공항에 최종 "
            "착륙한 경우를 말합니다. "
            "② 제1항의 보험사고로 인하여 회사가 보상하는 손해는 아래와 같습니다. "
            "1. 지연된 항공편을 기다리는 동안 피보험자가 실제로 지출한 식음료 비용(식당, 편의점 등) "
            "2. 지연된 항공편을 기다리는 동안 피보험자가 실제로 지출한 편의시설 비용(라운지, 숙박시설, "
            "휴게시설 등) 및 편의시설로의 이동을 위한 교통비"
        )
        clause3_def, created = get_or_create_clause(
            db, pv_id, cov3.coverage_id, "보장정의", "제1조(보상하는 손해)", text3_def, "p.135-136", "파랑",
        )
        n_clause += created
        if created:
            _, mc = get_or_create_map(db, clause3_def.clause_id, it["TRV_FLIGHT_DELAY"].type_id, "직접")
            n_map += mc

        text3_waiver = (
            "회사는 다음 중 어느 한 가지의 경우가 발생하거나 또는 해당 경우에 의하여 보험금 지급사유가 "
            "발생한 때에는 보험금을 지급하지 않습니다. "
            "1. 명시적 또는 실질적 형태의 정부의 육, 해, 공 군사력에 의한 선포 또는 비선포된 전쟁 또는 "
            "이에 따르는 행위 "
            "2. 피보험자 또는 그 수혜자들에 의하거나 또는 이들을 위해 행해진 불법적인 행동 "
            "3. 교통수단의 조작자 또는 조종자로 종사하는 상황에서 발생한 손실 "
            "4. 피보험자가 출발계획시간이 도래하기전에 구매한 항공권을 취소한 경우 "
            "5. 보험사고로 인하여 피보험자가 직접적으로 부담한 비용이 아닌 모든 간접 손해 (예정되었던 "
            "여행일정(숙박, 다른 교통수단, 관광지의 입장권 등)의 취소에 따른 수수료 등)"
        )
        clause3_waiver, created = get_or_create_clause(
            db, pv_id, cov3.coverage_id, "면책", "제2조(보상하지 않는 손해)", text3_waiver, "p.135-136", "빨강",
        )
        n_clause += created
        if created:
            _, mc = get_or_create_map(db, clause3_waiver.clause_id, it["TRV_FLIGHT_DELAY"].type_id, "면책")
            n_map += mc

        # =====================================================================
        # 4. 출국 항공기 결항 손해보장 추가특별약관 (p.138)
        # 면책 조항 없음(제2조 준용규정으로 3번 특약 및 보통약관을 따름) — 정직히 생략.
        # =====================================================================
        cov4, created = get_or_create_coverage(
            db, pv_id, "출국 항공기 결항 손해보장 추가특별약관", std_flight_delay.coverage_std_id,
            definition=(
                "출국 항공기 지연 손해 특별약관 제1조 제1항 제1호에도 불구하고, 국내공항 출발 국제선 "
                "항공편이 결항되는 경우 대체 항공편을 기다리는 동안 지출한 비용을 보상"
            ),
            limit_amount="보험가입금액 한도",
        )
        n_cov += created
        text4_def = (
            "① 출국 항공기 지연 손해 특별약관 제1조(보상하는 손해) 제1항 제1호에도 불구하고, 회사는 "
            "피보험자가 보험기간 중 국내공항에서 출발하는 국제선 항공편(국내외 항공사를 모두 포함합니다)이 "
            "결항되는 경우 추가적으로 부담한 비용 손해를 이 추가특별약관에서 정한 바에 따라 보험가입금액 "
            "한도 내에서 보상합니다. "
            "② 제1항의 보험사고로 인하여 회사가 보상하는 손해는 아래와 같습니다. "
            "1. 대체된 항공편을 기다리는 동안 피보험자가 실제로 지출한 식음료 비용(식당, 편의점 등) "
            "2. 대체된 항공편을 기다리는 동안 피보험자가 실제로 지출한 편의시설 비용(라운지, 숙박시설, "
            "휴게시설 등) 및 편의시설로의 이동을 위한 교통비"
        )
        clause4_def, created = get_or_create_clause(
            db, pv_id, cov4.coverage_id, "보장정의", "제1조(보상하는 손해)", text4_def, "p.138", "파랑",
        )
        n_clause += created
        if created:
            _, mc = get_or_create_map(db, clause4_def.clause_id, it["TRV_FLIGHT_DELAY"].type_id, "직접")
            n_map += mc

        # =====================================================================
        # 5. 항공기 지연사고발생 반려견(묘) 돌봄서비스 추가비용 보상 특별약관 (p.139~141)
        # =====================================================================
        cov5, created = get_or_create_coverage(
            db, pv_id, "항공기 지연사고발생 반려견(묘) 돌봄서비스 추가비용 보상 특별약관", std_pet_care.coverage_std_id,
            definition=(
                "귀국 항공편이 4시간이상 지연/결항되어 위탁돌봄서비스업자·펫시터가 예정된 시간에 반려견"
                "(묘)을 픽업하지 못해 발생한 서비스 추가비용을 보상(치료비·미용·목욕관리·영양제 등은 제외)"
            ),
            limit_amount="보험가입금액 한도, 지연된 도착시간에 상응하는 비용까지",
            waiting_condition="피보험자와 위탁돌봄서비스·펫시터 계약서상 반려견(묘) 소유자(위탁자)가 동일해야 함",
        )
        n_cov += created
        text5_def = (
            "① 회사는 보험기간 중 보험사고로 인하여 피보험자가 직접적으로 부담한 아래의 추가비용을 항공기 "
            "지연사고발생 반려견(묘) 돌봄서비스 추가비용 보상 특별약관(이하 “특별약관”이라 합니다)에서 "
            "정한 바에 따라 보험가입금액 한도 내에서 보상하여 드립니다. 단, 회사는 이 특별약관의 피보험자와 "
            "위탁돌봄서비스 또는 펫시터 서비스 계약서상 반려견(묘) 소유자(위탁자)가 동일한 경우에 한하여 "
            "보상하여 드립니다. "
            "1. 피보험자가 해외여행 기간 동안 위탁돌봄서비스업자(동물보호법에 따라 동물 위탁관리업으로 등록한 "
            "자에 한합니다)에게 위탁한 피보험자의 반려견(묘)을 예정된 시간에 픽업(Pick-up)하지 못하여 발생한 "
            "서비스 추가비용(단, 치료비, 미용 또는 목욕관리비용, 영양제 등은 제외) "
            "2. 피보험자가 해외여행 기간 동안 펫시터 서비스 이용중 피보험자의 반려견(묘)을 예정된 시간에 "
            "픽업(Pick-up)하지 못하여 발생한 서비스 추가비용 "
            "<용어 풀이> 【위탁돌봄서비스】‘위탁돌봄서비스’라 함은 동물보호법 제73조 제2호에서 정한 동물"
            "위탁관리업으로 영업 등록된 자가 제공하는 서비스를 말합니다. "
            "* 동물위탁관리업: 반려동물 소유자의 위탁을 받아 반려동물을 영업장 내에서 일시적으로 사육, 훈련 "
            "또는 보호하는 영업 【펫시터 서비스】‘펫시터 서비스’라 함은 펫시터가 가정을 방문하거나 펫시터의 "
            "집으로 이동하여 제공하는 펫돌봄서비스(산책서비스 포함)를 말합니다. "
            "② 위 제1항의 보험사고라 함은 피보험자가 해외여행을 마치고 거주국가로 돌아오기 위해 탑승하는 "
            "항공편이 지연 또는 결항되어 예정된 도착시간보다 4시간 이상 늦게 도착하는 경우를 말합니다. "
            "③ 회사는 항공기 지연 또는 결항으로 인하여 지연된 도착시간을 한도로 이에 상응하는 추가비용을 "
            "보상하여 드립니다. 지연된 도착시간은 항공편의 도착계획시간과 실제도착시간의 차이를 말합니다. "
            "<용어 풀이> 【항공편의 도착계획시간】 항공사가 공항공사 등 관련기관에 항공편의 도착계획시간으로 "
            "등록한 시간을 기준으로 합니다. 【항공편의 실제도착시간】공항공사 등 관련기관에 등록된 항공편의 "
            "실제 도착시간을 의미합니다."
        )
        clause5_def, created = get_or_create_clause(
            db, pv_id, cov5.coverage_id, "보장정의", "제1조(보상하는 손해)", text5_def, "p.139-140", "파랑",
        )
        n_clause += created
        if created:
            _, mc = get_or_create_map(db, clause5_def.clause_id, it["SPC_PET_CARE"].type_id, "직접")
            n_map += mc

        text5_waiver = (
            "회사는 아래의 사유로 생긴 손해는 보상하여 드리지 않습니다. "
            "1. 계약자나 또는 피보험자의 고의 또는 중대한 과실 "
            "2. 지진, 분화, 해일 또는 이와 비슷한 천재지변 "
            "3. 원인의 직접, 간접을 묻지 않고 지진, 분화 또는 전쟁, 혁명, 내란, 사변, 폭동, 소요, 노동쟁의, "
            "기타 이들과 유사한 사태로 생긴 손해 "
            "4. 핵연료물질 또는 핵연료물질에 의하여 오염된 물질의 방사성, 폭발성 그 밖의 유해한 특성 또는 "
            "이들의 특성에 의한 사고로 인한 손해 "
            "5. 위 제4호 이외의 방사선을 쬐는 것 또는 방사능 오염으로 인한 손해 "
            "6. 위탁돌봄서비스업자 또는 펫시터 서비스업자가 피보험자의 반려견(묘)을 보호하던 중 고의 또는 "
            "부주의로 인하여 발생한 사고로 인한 손해 "
            "7. 교통수단의 조작자 또는 조종자로 종사하는 상황에서 발생한 손실 "
            "8. 항공업자의 지연사유가 보험계약을 체결하기 전에 발생하였거나 공개적으로 알려진 경우"
        )
        clause5_waiver, created = get_or_create_clause(
            db, pv_id, cov5.coverage_id, "면책", "제2조(보상하지 않는 손해)", text5_waiver, "p.140", "빨강",
        )
        n_clause += created
        if created:
            _, mc = get_or_create_map(db, clause5_waiver.clause_id, it["SPC_PET_CARE"].type_id, "면책")
            n_map += mc

        # =====================================================================
        # 6. 여행중 식중독보상금(2일이상 입원) 특별약관 (p.142~143)
        # ILL 기존 L2 어디에도 정확히 안 맞아 needs_review 신규 유형으로 매핑.
        # 이 특약 자체에는 면책(보상하지 않는 손해) 조항이 없음 — 제2조는 지급 세부규정(조건).
        # =====================================================================
        cov6, created = get_or_create_coverage(
            db, pv_id, "여행중 식중독보상금(2일이상 입원) 특별약관", std_food_poisoning.coverage_std_id,
            definition=(
                "해외여행 중 음식물 섭취로 식중독이 발생하고 그 직접결과로 2일 이상 입원 치료를 받은 "
                "경우 보험가입금액을 정액으로 지급(외래진료만 받은 경우는 제외)"
            ),
            limit_amount="보험가입금액 정액 지급",
            waiting_condition="병원/의원(한방병원·한의원 포함)에 2일 이상 입원, 식중독 분류표(별표2) 해당 질병",
        )
        n_cov += created
        text6_def = (
            "① 회사는 피보험자가 해외여행 도중에 음식물의 섭취로 인해 중독(이하「식중독」이라 합니다)이 "
            "발생하고 그 직접적인 결과로 병원 또는 의원(한방병원 또는 한의원을 포함합니다)에 2일 이상 "
            "입원하여 치료를 받은 경우 이 특약의 보험가입금액을 보험수익자(보험수익자의 지정이 없을 때에는 "
            "피보험자)에게 식중독보상금으로 지급합니다. 다만, 입원하지 않고 외래진료만 받은 경우는 제외합니다. "
            "② 제1항에서 식중독이라 함은 음식물을 먹고 생기는 구토, 설사, 복통을 주요 증세로 하는 급성질환"
            "으로써 【별표2(식중독 분류표)】에 해당하는 질병으로 분류되는 경우를 말합니다."
        )
        clause6_def, created = get_or_create_clause(
            db, pv_id, cov6.coverage_id, "보장정의", "제1조(보험금의 종류 및 지급사유)", text6_def, "p.142", "파랑",
        )
        n_clause += created
        if created:
            _, mc = get_or_create_map(db, clause6_def.clause_id, food_poisoning_type.type_id, "직접")
            n_map += mc

        text6_cond = (
            "① 피보험자가 해외여행 도중에 사망하고, 그 후에 식중독을 직접적인 원인으로 사망한 사실이 확인된 "
            "경우에는 그 사망일을 진단 확정일로 보고 제1조(보험금의 종류 및 지급사유)에 해당하는 경우에 한하여 "
            "해당 보험금을 지급합니다. "
            "② 「호스피스·완화의료 및 임종과정에 있는 환자의 연명의료결정에 관한 법률」에 따른 연명의료중단 "
            "등 결정 및 그 이행으로 피보험자가 사망하는 경우 연명의료중단 등 결정 및 그 이행은 제1항 ‘사망’"
            "의 원인에 영향을 미치지 않습니다"
        )
        clause6_cond, created = get_or_create_clause(
            db, pv_id, cov6.coverage_id, "조건", "제2조(보험금 지급에 관한 세부규정)", text6_cond, "p.142", "노랑",
        )
        n_clause += created
        if created:
            _, mc = get_or_create_map(db, clause6_cond.clause_id, food_poisoning_type.type_id, "조건부")
            n_map += mc

        # =====================================================================
        # 7. 여행중 특정감염병보상금 특별약관 (p.143~144)
        # 이 특약 자체에는 면책 조항이 없음 — 제2조(사망시 처리)·제3조(정의·진단확정 요건)는 조건.
        # =====================================================================
        cov7, created = get_or_create_coverage(
            db, pv_id, "여행중 특정감염병보상금 특별약관", std_infectious.coverage_std_id,
            definition=(
                "해외여행 중 특정감염병(별표3)으로 감염병예방법 제11조에 따라 신고되어 특정감염병환자로 "
                "진단 확정된 경우 보험가입금액을 정액으로 지급"
            ),
            limit_amount="보험가입금액 정액 지급",
            waiting_condition="감염병예방법 시행규칙상 병원체 확인기관에서 감염병환자로 확진(병원체보유자는 제외)",
        )
        n_cov += created
        text7_def = (
            "① 회사는 피보험자가 해외여행 도중에 【별표3(특정감염병 분류표)】에서 정한 특정감염병으로 「감염병"
            "의 예방 및 관리에 관한 법률 제11조(의사 등의 신고)」에 따라 신고되어 특정감염병환자로 진단 "
            "확정되었을 때에는 이 특별약관의 보험가입금액을 보험수익자(보험수익자의 지정이 없을 때에는 "
            "피보험자)에게 특정감염병보상금으로 지급합니다."
        )
        clause7_def, created = get_or_create_clause(
            db, pv_id, cov7.coverage_id, "보장정의", "제1조(보상하는 손해)", text7_def, "p.143", "파랑",
        )
        n_clause += created
        if created:
            _, mc = get_or_create_map(db, clause7_def.clause_id, it["ILL_INFECTIOUS"].type_id, "직접")
            n_map += mc

        text7_cond1 = (
            "① 피보험자가 해외여행 도중에 사망하고, 그 후에 특정감염병을 직접적인 원인으로 사망한 사실이 "
            "확인된 경우에는 그 사망일을 진단 확정일로 보고 제1조(보상하는 손해)에 해당하는 경우에 한하여 "
            "해당 보험금을 지급합니다. "
            "② 「호스피스·완화의료 및 임종과정에 있는 환자의 연명의료결정에 관한 법률」에 따른 연명의료중단 "
            "등 결정 및 그 이행으로 피보험자가 사망하는 경우 연명의료중단 등 결정 및 그 이행은 제1항 ‘사망’"
            "의 원인에 영향을 미치지 않습니다."
        )
        clause7_cond1, created = get_or_create_clause(
            db, pv_id, cov7.coverage_id, "조건", "제2조(보험금 지급에 관한 세부규정)", text7_cond1, "p.143", "노랑",
        )
        n_clause += created
        if created:
            _, mc = get_or_create_map(db, clause7_cond1.clause_id, it["ILL_INFECTIOUS"].type_id, "조건부")
            n_map += mc

        text7_cond2 = (
            "① 이 특별약관에서 특정감염병이라 함은 【별표3(특정감염병 분류표)】에서 정한 질병을 말합니다. "
            "② 특정감염병의 진단확정은 「감염병의 예방 및 관리에 관한 법률 시행규칙」에서 정한 ‘감염병의 "
            "병원체를 확인할 수 있는 기관’에서 ‘감염병의 진단기준’에 따라 감염병환자로 확진된 경우를 "
            "말하며, 병원체보유자는 해당되지 않습니다. 그러나, 피보험자가 사망하여 상기 검사방법을 진단의 "
            "기초로 할 수 없는 경우에 한하여 피보험자가 특정감염병으로 진단 또는 치료를 받고 있었음을 증명할 "
            "수 있는 문서화된 기록 또는 증거를 진단확정의 기초로 할 수 있습니다. "
            "③ 향후 「감염병의 예방 및 관리에 관한 법률」등 관계 법령에서 제외되는 감염병이 생기는 경우 해당 "
            "감염병은 「의료법 제3조(의료기관)」에 규정한 국내의 병원, 의원 또는 국외의 의료관련법에서 정한 "
            "의료기관의 의사(치과의사 제외) 면허를 가진 자의 진단에 따릅니다."
        )
        clause7_cond2, created = get_or_create_clause(
            db, pv_id, cov7.coverage_id, "조건", "제3조(특정감염병의 정의 및 진단확정)", text7_cond2, "p.143", "노랑",
        )
        n_clause += created
        if created:
            _, mc = get_or_create_map(db, clause7_cond2.clause_id, it["ILL_INFECTIOUS"].type_id, "조건부")
            n_map += mc

        # =====================================================================
        # 8. 여행중 중단사고발생 추가비용 특별약관 (p.145~146)
        # =====================================================================
        cov8, created = get_or_create_coverage(
            db, pv_id, "여행중 중단사고발생 추가비용 특별약관", std_interruption.coverage_std_id,
            definition=(
                "본인/여행동반가족 3일이상 입원, 3촌이내 친족·동반자 사망, 천재지변, 전쟁 등의 사유로 "
                "여행일정을 불가피하게 중단(축소)·귀국할 때 추가로 발생한 항공(선박)운임·숙박비 차액을 보상"
            ),
            limit_amount="보험가입금액 한도",
        )
        n_cov += created
        text8_def = (
            "회사는 피보험자가 해외여행 도중에 아래의 사유로 여행일정을 불가피하게 중단(축소)하고 귀국하게 "
            "되었을 경우 피보험자가 추가적으로 부담한 비용을 이 특별약관에 따라 보험가입금액을 한도로 보상"
            "하여 드립니다. "
            "1. 피보험자 및 여행동반 가족이 상해 또는 질병으로 3일 이상 입원한 경우 "
            "2. 보험기간 내 피보험자의 3촌 이내의 친족 또는 여행동반자의 사망 "
            "3. 지진, 분화, 해일 또는 이와 비슷한 천재지변 "
            "4. 전쟁, 외국의 무력행사, 혁명, 내란, 사변, 폭동, 소요, 기타 이들과 유사한 사태"
        )
        clause8_def, created = get_or_create_clause(
            db, pv_id, cov8.coverage_id, "보장정의", "제1조(보상하는 손해)", text8_def, "p.145", "파랑",
        )
        n_clause += created
        if created:
            _, mc = get_or_create_map(db, clause8_def.clause_id, it["CHG_INTERRUPTION"].type_id, "직접")
            n_map += mc

        text8_cond = (
            "회사가 보상하는 비용은 아래와 같습니다. "
            "1. 피보험자가 여행중단 사유 발생 이전에 귀국항공 또는 선박 운임비용을 미리 지급한 경우에 한하여 "
            "여행중단 사유 발생으로 여행을 중단하고 일정을 변경하여 귀국함으로서 미리 지급한 항공 또는 선박 "
            "운임비용을 초과하여 피보험자에게 추가로 발생하는 항공 또는 선박 운임비용 "
            "2. 피보험자가 여행중단 사유 발생으로 여행중단 후 귀국으로 인해 여행중단 사유 발생 이전에 미리 "
            "지급한 숙박비용을 초과하여 피보험자에게 추가로 발생하는 2박 이내의 숙박비용"
        )
        clause8_cond, created = get_or_create_clause(
            db, pv_id, cov8.coverage_id, "조건", "제3조(보상하는 손해의 범위)", text8_cond, "p.145-146", "노랑",
        )
        n_clause += created
        if created:
            _, mc = get_or_create_map(db, clause8_cond.clause_id, it["CHG_INTERRUPTION"].type_id, "조건부")
            n_map += mc

        text8_waiver = (
            "회사는 보통약관 제5조(보험금을 지급하지 않는 사유) 제1항 제1호 내지 제3호의 사유를 원인으로 "
            "하여 생긴 손해는 보상하여 드리지 않습니다."
        )
        clause8_waiver, created = get_or_create_clause(
            db, pv_id, cov8.coverage_id, "면책", "제4조(보상하지 않는 손해)", text8_waiver, "p.146", "빨강",
        )
        n_clause += created
        if created:
            _, mc = get_or_create_map(db, clause8_waiver.clause_id, it["CHG_INTERRUPTION"].type_id, "면책")
            n_map += mc

        # =====================================================================
        # 9. 여행중 여권분실 재발급비용 특별약관 (p.147~148)
        # =====================================================================
        cov9, created = get_or_create_coverage(
            db, pv_id, "여행중 여권분실 재발급비용 특별약관", std_passport_loss.coverage_std_id,
            definition=(
                "해외여행 중 여권을 분실·도난당해 재외공관에 신고하고 여행증명서(T/C)를 발급받은 경우 "
                "여행증명서 발급비용과 여권 재발급비용(여권법 제22조 수수료+국제교류기여금, 교통비·사진촬영비 "
                "제외)을 지급"
            ),
            limit_amount="여권법 제22조 제1항 수수료 + 국제교류기여금 (교통비·사진촬영비 제외)",
        )
        n_cov += created
        text9_def = (
            "① 회사는 피보험자(보험대상자)가 해외여행 도중에 여권을 분실하거나 도난당하여 재외공관에 여권"
            "분실신고를 하고 여행증명서(T/C : Travel Certification)를 발급받은 경우 여행증명서 발급비용과 "
            "여권 재발급비용을 보험수익자(보험금을 받는 자)에게 지급합니다. "
            "② 제1항의 여행증명서 발급비용 및 여권 재발급비용이란 여행증명서 및 여권 재발급에 관한 수수료로 "
            "「여권법」 제22조 제1항에서 정한 수수료 및 국제교류기여금을 합한 금액을 말하며 교통비 및 "
            "사진촬영비는 포함되지 않습니다. "
            "③ 제1항에서 정한 비용에 대하여 보험금을 지급할 다른 계약(공제계약을 포함)이 체결되어 있고 각각의 "
            "계약에 대하여 다른 계약(공제계약을 포함)이 없는 것으로 하여 산출한 보상책임액의 합계액이 피보험자"
            "(보험대상자)가 부담하는 금액을 초과했을 때 회사는 이 계약에 따른 보상책임액의 상기 합계액에 대한 "
            "비율에 따라 보험금을 지급합니다."
        )
        clause9_def, created = get_or_create_clause(
            db, pv_id, cov9.coverage_id, "보장정의", "제1조(보상하는 손해)", text9_def, "p.147", "파랑",
        )
        n_clause += created
        if created:
            _, mc = get_or_create_map(db, clause9_def.clause_id, it["PROP_PASSPORT_LOSS"].type_id, "직접")
            n_map += mc

        text9_waiver = (
            "회사는 아래의 사유로 인하여 생긴 손해는 보상하지 않습니다. "
            "1. 계약자 또는 피보험자의 고의 "
            "2. 피보험자에게 보험금이 지급되도록 하기 위하여 피보험자와 여행을 같이하는 친족 또는 고용인이 "
            "고의로 일으킨 손해 "
            "3. 압류, 징발, 몰수, 파괴 등 국가 또는 공공기관의 공권력행사. 단, 화재, 소방, 피난에 필요한 "
            "처리로 된 경우를 제외합니다. "
            "4. 선박승무원 및 항공승무원이 직무상 해외여행 중 여권을 분실 또는 도난당한 경우"
        )
        clause9_waiver, created = get_or_create_clause(
            db, pv_id, cov9.coverage_id, "면책", "제2조(보상하지 않는 손해)", text9_waiver, "p.147", "빨강",
        )
        n_clause += created
        if created:
            _, mc = get_or_create_map(db, clause9_waiver.clause_id, it["PROP_PASSPORT_LOSS"].type_id, "면책")
            n_map += mc

        db.commit()
        print(
            "samsung 전체정독 청크D(p.130-148, 특약 9개) 완료: "
            f"coverage_std 신규 6종 보장, coverage 신규 {n_cov}건, clause 신규 {n_clause}건, "
            f"clause_incident_map 신규 {n_map}건, needs_review 신규유형 생성={food_poisoning_type_created} "
            f"(식중독보상금(입원), type_id={food_poisoning_type.type_id})"
        )
    finally:
        db.close()


if __name__ == "__main__":
    run()
