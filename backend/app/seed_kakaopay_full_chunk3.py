"""
카카오페이손해보험(insurer.code="KAKAOPAY") 전체 재검토 — 청크 3(PDF p.133-198, 문서 끝까지).
data/raw_pdfs/kakaopay_overseas_20241101.pdf (총 198쪽)을 pdfplumber로 p.133-198 전체를
직접 읽고 대조한 결과를 반영한다.

## p.133-156 (사고유형 관련 특약들)
- p.133: 여권분실 특별약관 → PASSPORT_LOSS (기존 코드 사용)
- p.134: 식중독 입원 특별약관 → FOOD_POISONING (기존 코드 사용)
- p.135: 특정전염병 감염 특별약관 → INFECTIOUS_DISEASE (기존 코드 사용)
- p.136-139: 항공기/수하물 지연비용 특별약관 → FLIGHT_DELAY (기존 코드 사용)
- p.140-142: 국내공항 출국 항공기 지연 손해 특별약관 → FLIGHT_DELAY (기존 코드 사용, 중복)
- p.143-144: 해외병원 상해입원일당(1일이상 180일한도) 특별약관 → INJ_HOSPITAL_ALLOWANCE (신규 담보)
  정액 입원일당 구조로 지급 → 새 CoverageStd 필요
- p.145-146: 해외병원 질병입원일당(4일이상 30일한도) 특별약관 → ILL_HOSPITAL_ALLOWANCE (신규 담보)
  정액 입원일당 구조로 지급 → 새 CoverageStd 필요
- p.147-150: 해외여행중 자택 도난손해 특별약관 → HOME_THEFT (기존 코드 사용)
- p.151: 전쟁 상해사망후유장해 특별약관 → WAR_RISK (기존 코드 사용)
- p.152: 특수운동중 상해위험 특별약관 → INJ_SPECIAL_SPORTS (신규 담보)
  전문등반, 스카이다이빙, 스쿠버다이빙, 행글라이딩, 수상보트, 패러글라이딩 중 발생 상해
  → 새 CoverageStd 필요
- p.153: 특수운전중 상해위험 특별약관 → INJ_SPECIAL_DRIVING (신규 담보)
  모터보트, 자동차/오토바이 경기·시범·흥행·시운전 중 발생 상해
  → 새 CoverageStd 필요
- p.154-156: 안전귀국 환급 추가약관, 항공기 출발지연 알림 서비스 추가약관
  → 순수 계약행정/서비스로 사고유형과 무관. 클레임 판단에 사용 불가 (스킵)

## p.157-162+ (사고유형 무관 특약들)
- p.157: 적용환율 특별약관 → 순수 환율 계산, 무관 (확인함, 스킵)
- p.158: 보통약관 선택가입 특별약관 → 순수 계약선택, 무관 (확인함, 스킵)
- p.159+: 지정대리청구서비스/장애인전용보험전환 특별약관 등 → 순수 계약행정, 무관 (확인함, 스킵)
- p.163+: 장해분류표([별표1-4]) 등 → 별표 자료, 조항 매핑에서 제외

멱등성: Coverage는 raw_name, Clause는 (coverage_id, article_no, text) 조합,
ClauseIncidentMap은 (clause_id, type_id) 조합으로 이미 있으면 건너뛴다.
"""
from app.database import SessionLocal
from app import models  # noqa: F401
from app.models.kb import (
    Clause, ClauseIncidentMap, Coverage, CoverageStd, IncidentType, Insurer, PolicyVersion, Product,
)
from app.services.kb_seed_common import get_or_create_coverage_std

# ---------------------------------------------------------------------------
# 1) 해외병원 상해입원일당(1일이상 180일한도) 특별약관 (p.143-144)
# ---------------------------------------------------------------------------

INJ_HOSPITAL_CLAUSE1_TEXT = (
    "① 회사는 피보험자가 해외여행 도중에 발생한 상해의 직접결과로써 해외 의료기관에 "
    "1 일이상 입원하여 치료를 받은 경우에는 1 일째 입원일로부터 입원 1 일당 이 "
    "특별약관의 보험가입금액을 상해입원일당으로 지급하여 드립니다. 다만, "
    "상해입원일당의 지급 일수는 1 회 입원당 180 일을 한도로 합니다. "
    "② 동일한 상해의 치료를 목적으로 2 회 이상 입원한 경우 이를 1 회 입원으로 보아 각 "
    "입원일 수를 더합니다. "
    "③ 제 1 항의 경우 피보험자가 보장개시일(책임개시일)이후 입원하여 치료를 받던 중 "
    "보험기간이 만료되었을 때에도 퇴원하기 전까지의 계속중인 입원에 대하여는 제 1 항의 "
    "상해입원일당을 계속 지급하여 드립니다. "
    "④ 피보험자가 정당한 이유없이 입원기간 중 의사의 지시를 따르지 않은 때에는 회사는 "
    "상해입원일당의 전부 또는 일부를 지급하지 않습니다. "
    "⑤ 피보험자가 병원 또는 의원을 이전하여 입원한 경우에도 동일한 상해의 치료를 "
    "목적으로 2 회이상 입원한 경우에는 계속하여 입원한 것으로 보아 각 입원일수를 "
    "더합니다."
)

INJ_HOSPITAL_CLAUSE2_TEXT = (
    "① 회사는 다음 중 어느 한가지로 보험금 지급사유가 발생한 때에는 보험금을 지급하지 "
    "않습니다. "
    "1. 피보험자가 고의로 자신을 해친 경우. 다만, 피보험자가 심신상실 등으로 자유로운 "
    "의사 결정을 할 수 없는 상태에서 자신을 해친 경우에는 보험금을 지급합니다. "
    "2. 보험수익자가 고의로 피보험자를 해친 경우. 다만, 그 보험수익자가 보험금의 일부 "
    "보험 수익자인 경우에는 다른 보험수익자에 대한 보험금은 지급합니다. "
    "3. 계약자가 고의로 피보험자를 해친 경우 "
    "4. 피보험자의 임신, 출산(제왕절개를 포함합니다), 산후기. 그러나, 회사가 보장하는 "
    "보험금 지급사유로 인한 경우에는 보험금을 지급합니다. "
    "5. 전쟁, 외국의 무력행사, 혁명, 내란, 사변, 폭동 "
    "② 회사는 다른 약정이 없으면 피보험자가 직업, 직무 또는 동호회 활동목적으로 아래에 "
    "열거 된 행위로 인하여 제 3 조(보험금의 지급사유)의 상해 관련 보험금 지급사유가 "
    "발생한 때에는 해당 보험금을 지급하지 않습니다. "
    "1. 전문등반(전문적인 등산용구를 사용하여 암벽 또는 빙벽을 오르내리거나 특수한 "
    "기술, 경험, 사전훈련을 필요로 하는 등반을 말합니다), 글라이더 조종, 스카이다이빙, "
    "스쿠버다이빙, 행글라이딩, 수상보트, 패러글라이딩 "
    "2. 모터보트, 자동차 또는 오토바이에 의한 경기, 시범, 흥행(이를 위한 연습을 "
    "포함합니다) 또는 시운전(다만, 공용도로상에서 시운전을 하는 동안 보험금 지급사유가 "
    "발생한 경우 에는 보장합니다) "
    "3. 선박에 탑승하는 것을 직무로 하는 사람이 직무상 선박에 탑승하고 있는 동안 "
    "③ 국내 의료기관에 입원한 기간에 대한 보험금은 지급하지 않습니다."
)

INJ_HOSPITAL_CLAUSE3_TEXT = "이 특별약관에 정하지 않은 사항은 보통약관을 따릅니다."

# ---------------------------------------------------------------------------
# 2) 해외병원 질병입원일당(4일이상 30일한도) 특별약관 (p.145-146)
# ---------------------------------------------------------------------------

ILL_HOSPITAL_CLAUSE1_TEXT = (
    "① 회사는 피보험자가 해외여행 도중에 진단확정된 질병으로 인하여 해외 의료기관에 "
    "4 일 이상 계속 입원하여 치료를 받은 경우에는 3 일 초과 입원 1 일당 이 특별약관의 "
    "보험가입금액을 해외병원 질병입원일당(이하 '질병입원일당'이라 합니다 )으로 "
    "지급합니다. "
    "② 제 1 항의 질병입원일당의 지급일수는 1 회 입원당 30 일을 최고한도로 합니다. "
    "③ 제 1 항의 경우 피보험자가 동일한 질병의 치료를 직접적인 목적으로 2 회 이상 "
    "입원한 경우 이를 1 회 입원으로 보아 각 입원일수를 더하여 제 2 항을 적용합니다. "
    "④ 제 3 항에도 불구하고 동일한 질병에 대한 입원이라도 입원일당이 지급된 최종입원의 "
    "퇴원일부터 180 일이 경과하여 개시한 입원은 새로운 입원으로 봅니다. 다만, 아래와 "
    "같이 입원일당이 지급된 최종입원일부터 180 일이 경과하도록 퇴원없이 계속 입원중인 "
    "경우에는 입원일당이 지급된 최종입원일의 그 다음날을 퇴원일로 봅니다. "
    "⑤ 제 1 항의 경우 피보험자가 질병에 대한 보장개시일 이후 입원하여 치료를 받던 중 "
    "보험기간이 만료되었을 때에도 퇴원하기 전까지의 계속중인 입원기간에 대하여는 "
    "제 2 항의 규정에 따라 입원일당은 계속 보상합니다. "
    "⑥ 피보험자가 정당한 이유없이 입원기간 중 의사의 지시를 따르지 아니한 때에는 "
    "회사는 입원일당의 전부 또는 일부를 지급하지 않습니다. "
    "⑦ 피보험자가 병원 또는 의원을 이전하여 입원한 경우에도 동일한 질병의 치료를 "
    "목적으로 2 회이상 입원한 경우에는 계속하여 입원한 것으로 보아 각 입원일수를 "
    "더합니다."
)

ILL_HOSPITAL_CLAUSE2_TEXT = (
    "① 회사는 다음 중 어느 한 가지의 경우에 의하여 보험금 지급사유가 발생한 때에는 "
    "보험금을 지급하지 않습니다. "
    "1. 피보험자가 고의로 자신을 해친 경우. 다만, 피보험자가 심신상실 등으로 자유로운 "
    "의사결정을 할 수 없는 상태에서 자신을 해친 경우에는 보험금을 지급하여 드립니다. "
    "2. 피보험자의 기질성 치매를 제외한 정신적 기능장해, 선천성 뇌질환 및 심신상실 "
    "3. 피보험자의 임신, 출산(제왕절개를 포함합니다), 산후기. 그러나 회사가 보장하는 "
    "보험금 지급사유로 인한 경우에는 보험금을 지급하여 드립니다. "
    "4. 성병 "
    "5. 알콜중독, 습관성 약품 또는 환각제의 복용 및 사용 "
    "6. 전쟁, 외국의 무력행사, 혁명, 내란, 사변, 폭동 "
    "② 회사는 아래에 정한 사유로 발생한 손해는 보상하지 않습니다. "
    "1. 질병을 원인으로 하지 않는 신체검사, 예방접종, 인공유산, 불임시술, 제왕절개수술 "
    "2. 피로, 권태, 심신허약 등을 치료하기 위한 안정치료 "
    "3. 위생관리, 미모를 위한 성형수술 "
    "4. 정상분만, 치과질환"
)

ILL_HOSPITAL_CLAUSE3_TEXT = "이 특별약관에 정하지 않은 사항은 보통약관을 따릅니다."

# ---------------------------------------------------------------------------
# 3) 전쟁 상해사망후유장해 특별약관 (p.151)
# ---------------------------------------------------------------------------

WAR_RISK_CLAUSE1_TEXT = (
    "① 회사는 피보험자에게 다음 중 어느 하나의 사유가 발생한 경우에는 보험수익자에게 "
    "약정한 보험금을 지급합니다. "
    "1. \"보통약관 제 3 조(보험금의 지급사유)의 해외여행 중(이하 '해외여행 중'이라 "
    "합니다)에 보통약관 제 5 조(보험금을 지급하지 않는 사유) 제 1 항제 5 호에도 불구하고 "
    "전쟁, 외국의 무력행사, 혁명, 내란, 사변, 폭동으로 인하여 발생한 상해\"(이하 "
    "'상해'라 합니다)의 직접결과로써 사망한 경우(질병으로 인한 사망은 제외합니다) : "
    "사망보험금 "
    "2. 해외여행 중 상해로 장해분류표([별표 1]참조)에서 정한 각 장해지급률에 해당하는 "
    "장해상태가 되었을 때 : 후유장해보험금(장해분류표에서 정한 지급률을 보험가입금액에 "
    "곱하여 산출한 금액) "
    "② 회사는 보험기간이 만료되기 전이라도 제 1 항의 위험이 뚜렷이 증가했다고 인정될 "
    "때에는 24 시간 이전에 서면으로 추가보험료를 청구하거나 이 특별약관을 해지할 수 "
    "있습니다."
)

WAR_RISK_CLAUSE2_TEXT = (
    "① 피보험자가 여행경로를 변경하는 경우에는 계약자 또는 피보험자는 미리 그 내용을 "
    "서면으로 회사에 제출하여야 합니다. "
    "② 회사는 제 1 항의 통지를 받은 경우에는 회사가 정한 바에 의하여 추가보험료를 "
    "청구하거나 이 특별약관을 해지할 수 있습니다. "
    "③ 계약자 또는 피보험자가 제 1 항의 계약 후 알릴 의무를 이행하지 않은 경우에는 "
    "회사는 피보험자가 여행경로를 변경한 이후의 사고로 인한 상해에 대해서는 보상하지 "
    "않습니다."
)

WAR_RISK_CLAUSE3_TEXT = (
    "제 1 조(보험금의 지급사유) 제 2 항 및 제 2 조(계약 후 알릴 의무의 특례) 제 2 항의 "
    "해지는 장래에 대해서만 그 효력이 있습니다."
)

WAR_RISK_CLAUSE4_TEXT = "이 특별약관에 정하지 않은 사항은 보통약관을 따릅니다."

# ---------------------------------------------------------------------------
# 4) 특수운동중 상해위험 특별약관 (p.152)
# ---------------------------------------------------------------------------

SPORTS_INJURY_CLAUSE1_TEXT = (
    "회사는 피보험자에게 다음 중 어느 하나의 사유가 발생한 경우에는 보험수익자에게 "
    "약정한 보험금을 지급합니다. "
    "1. \"보통약관 제 3 조(보험금의 지급사유)의 해외여행 중(이하 '해외여행 중'이라 "
    "합니다)에 보통약관 제 5 조(보험금을 지급하지 않는 사유) 및 기본형 해외여행 "
    "실손의료비 특별약관 제 4 조(보상하지 않는 사항) 및 비급여 해외여행 실손의료비 "
    "특별약관의 제 4 조(보상하지 않는 사항) 및 해외여행중 중대사고 구조/송환비용 "
    "특별약관의 제 3 조(보험금을 지급하지 않는 사유)에도 불구하고 전문등반(전문적인 "
    "등산용구를 사용하여 암벽 또는 빙벽을 오르내리거나 특수한 기술, 경험, 사전훈련을 "
    "필요로 하는 등반을 말합니다), 글라이더 조종, 스카이다이빙, 스쿠버다이빙, 행글라이딩, "
    "수상보트, 패러글라이딩을 하는 동안에 발생한 상해\"(이하 '상해'라 합니다)의 "
    "직접결과로써 사망한 경우(질병으로 인한 사망은 제외합니다) : 사망보험금 "
    "2. 해외여행 중 상해로 장해분류표([별표 1]참조)에서 정한 각 장해지급률에 해당하는 "
    "장해상태가 되었을 때 : 후유장해보험금(장해분류표에서 정한 지급률을 보험가입금액에 "
    "곱하여 산출한 금액) "
    "3. 해외여행 중에 입은 상해로 인하여 병원에 입원 또는 통원하여 발생한 의료비를 "
    "기본형 해외여행 실손의료비 특별약관 제 3 조(보장종목별 보상내용)의 (1) 상해의료비 "
    "및 비급여 해외여행 실손의료비 특별약관 제 3 조(보장종목별 보상내용)의 (1) "
    "상해비급여 및 (3) 3 대비급여에서 정한 바에 따라 보상합니다. 단, 기본형 해외여행 "
    "실손의료비 특별약관과 비급여 해외여행 실손의료비 특별약관을 동시에 가입한 계약에 "
    "한해 적용합니다. "
    "4. 해외여행 중 상해로 해외여행중 중대사고 구조/송환비용 특별약관 제 1 조(보험금의 "
    "지급사유)가 발생하였을 때에는 그로 인하여 생긴 손해를 보상하여 드립니다."
)

SPORTS_INJURY_CLAUSE2_TEXT = (
    "이 특별약관에 정하지 않은 사항은 보통약관 또는 기본형 해외여행 실손의료비 "
    "특별약관, 비급여 해외여행 실손의료비 특별약관, 해외여행중 중대사고 구조/송환비용 "
    "특별약관을 따릅니다."
)

# ---------------------------------------------------------------------------
# 5) 특수운전중 상해위험 특별약관 (p.153)
# ---------------------------------------------------------------------------

DRIVING_INJURY_CLAUSE1_TEXT = (
    "회사는 피보험자에게 다음 중 어느 하나의 사유가 발생한 경우에는 보험수익자에게 "
    "약정한 보험금을 지급합니다. "
    "1. \"보통약관 제 3 조(보험금의 지급사유)의 해외여행 중(이하 '해외여행 중'이라 "
    "합니다)에 보통약관 제 5 조(보험금을 지급하지 않는 사유) 및 기본형 해외여행 "
    "실손의료비 특별약관 제 4 조(보상하지 않는 사항) 및 비급여 해외여행 실손의료비 "
    "특별약관의 제 4 조(보상하지 않는 사항) 및 해외여행중 중대사고 구조/송환비용 "
    "특별약관의 제 3 조(보험금을 지급하지 않는 사유)에도 불구하고 모터보트, 자동차 또는 "
    "오토바이에 의한 경기, 시범, 흥행(이를 위한 연습을 포함합니다) 또는 시운전을 하는 "
    "동안에 발생한 상해\"(이하 '상해'라 합니다)의 직접결과로써 사망한 경우(질병으로 인한 "
    "사망은 제외합니다) : 사망보험금 "
    "2. 해외여행 중 상해로 장해분류표([별표 1]참조)에서 정한 각 장해지급률에 해당하는 "
    "장해상태가 되었을 때 : 후유장해보험금(장해분류표에서 정한 지급률을 보험가입금액에 "
    "곱하여 산출한 금액) "
    "3. 해외여행 중에 입은 상해로 인하여 병원에 입원 또는 통원하여 발생한 의료비를 "
    "기본형 해외여행 실손의료비 특별약관 제 3 조(보장종목별 보상내용)의 (1) 상해의료비 "
    "및 비급여 해외여행 실손의료비 특별약관 제 3 조(보장종목별 보상내용)의 (1) "
    "상해비급여 및 (3) 3 대비급여에서 정한 바에 따라 보상합니다. 단, 기본형 해외여행 "
    "실손의료비 특별약관과 비급여 해외여행 실손의료비 특별약관을 동시에 가입한 계약에 "
    "한해 적용합니다. "
    "4. 해외여행 중 상해로 해외여행중 중대사고 구조/송환비용 특별약관 제 1 조(보험금의 "
    "지급사유)가 발생하였을 때에는 그로 인하여 생긴 손해를 보상하여 드립니다."
)

DRIVING_INJURY_CLAUSE2_TEXT = (
    "이 특별약관에 정하지 않은 사항은 보통약관 또는 기본형 해외여행 실손의료비 "
    "특별약관, 비급여 해외여행 실손의료비 특별약관, 해외여행중 중대사고 구조/송환비용 "
    "특별약관을 따릅니다."
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
        insurer = db.query(Insurer).filter_by(code="KAKAOPAY").first()
        if not insurer:
            print("카카오페이가 아직 시딩되지 않았습니다. seed_kakaopay를 먼저 실행하세요.")
            return
        pv = (
            db.query(PolicyVersion)
            .join(Product, Product.product_id == PolicyVersion.product_id)
            .filter(Product.insurer_id == insurer.insurer_id)
            .first()
        )
        if not pv:
            print("카카오페이 policy_version을 찾을 수 없습니다.")
            return

        types = {t.l2_code: t for t in db.query(IncidentType).all()}
        required = [
            "INJ_OVERSEAS_TREATMENT", "INJ_DEATH_DISABILITY",
            "ILL_OVERSEAS_TREATMENT",
        ]
        missing = [c for c in required if c not in types]
        if missing:
            print(f"incident_type 사전에 없는 코드: {missing}. seed_incident_types를 먼저 실행하세요.")
            return

        # 신규 CoverageStd 생성
        std_inj_hospital = get_or_create_coverage_std(
            db, "INJ_HOSPITAL_ALLOWANCE", "상해입원일당(1일이상 180일한도)",
            "상해", False
        )
        std_ill_hospital = get_or_create_coverage_std(
            db, "ILL_HOSPITAL_ALLOWANCE", "질병입원일당(4일이상 30일한도)",
            "질병", False
        )
        std_sports_injury = get_or_create_coverage_std(
            db, "INJ_SPECIAL_SPORTS", "특수운동중 상해위험",
            "상해", False
        )
        std_driving_injury = get_or_create_coverage_std(
            db, "INJ_SPECIAL_DRIVING", "특수운전중 상해위험",
            "상해", False
        )
        # 기존 CoverageStd 조회
        std_war = db.query(CoverageStd).filter_by(std_code="WAR_RISK").first()

        clause_created = map_created = coverage_created = 0

        # ------------------------------------------------------------------
        # 1) 해외병원 상해입원일당(1일이상 180일한도) 특별약관 (p.143-144)
        # ------------------------------------------------------------------
        cov_inj_hospital = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "해외병원 상해입원일당(1일이상 180일한도) 특별약관",
            )
            .first()
        )
        if not cov_inj_hospital:
            cov_inj_hospital = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_inj_hospital.coverage_std_id,
                raw_name="해외병원 상해입원일당(1일이상 180일한도) 특별약관",
                definition=INJ_HOSPITAL_CLAUSE1_TEXT,
                limit_amount="1회 입원당 180일 한도, 1일당 보험가입금액",
                deductible=None,
                waiting_condition="1일 이상 입원 시 1일째부터 지급",
            )
            db.add(cov_inj_hospital)
            db.flush()
            coverage_created += 1

        clause_inj_1, c1 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_inj_hospital.coverage_id,
            clause_type="보장정의", article_no="[해외병원 상해입원일당 특별약관] 제1조(보험금의 지급사유)",
            text=INJ_HOSPITAL_CLAUSE1_TEXT, page_ref="p.143", default_color="파랑",
        )
        clause_inj_2, c2 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_inj_hospital.coverage_id,
            clause_type="면책", article_no="[해외병원 상해입원일당 특별약관] 제2조(보험금을 지급하지 않는 사유)",
            text=INJ_HOSPITAL_CLAUSE2_TEXT, page_ref="p.144", default_color="빨강",
        )
        clause_inj_3, c3 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_inj_hospital.coverage_id,
            clause_type="공통", article_no="[해외병원 상해입원일당 특별약관] 제3조(준용규정)",
            text=INJ_HOSPITAL_CLAUSE3_TEXT, page_ref="p.144", default_color="회색",
        )
        clause_created += sum([c1, c2, c3])

        inj_treatment = types["INJ_OVERSEAS_TREATMENT"]
        map_created += sum([
            _get_or_create_map(db, clause_id=clause_inj_1.clause_id, type_id=inj_treatment.type_id, relevance="직접", confidence=1.0),
            _get_or_create_map(db, clause_id=clause_inj_2.clause_id, type_id=inj_treatment.type_id, relevance="면책", confidence=0.9),
        ])

        # ------------------------------------------------------------------
        # 2) 해외병원 질병입원일당(4일이상 30일한도) 특별약관 (p.145-146)
        # ------------------------------------------------------------------
        cov_ill_hospital = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "해외병원 질병입원일당(4일이상 30일한도) 특별약관",
            )
            .first()
        )
        if not cov_ill_hospital:
            cov_ill_hospital = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_ill_hospital.coverage_std_id,
                raw_name="해외병원 질병입원일당(4일이상 30일한도) 특별약관",
                definition=ILL_HOSPITAL_CLAUSE1_TEXT,
                limit_amount="1회 입원당 30일 한도, 4일 이상만 보상(3일 초과부터 지급)",
                deductible=None,
                waiting_condition="4일 이상 계속 입원 시 3일 초과분부터 지급",
            )
            db.add(cov_ill_hospital)
            db.flush()
            coverage_created += 1

        clause_ill_1, i1 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_ill_hospital.coverage_id,
            clause_type="보장정의", article_no="[해외병원 질병입원일당 특별약관] 제1조(보험금의 지급사유)",
            text=ILL_HOSPITAL_CLAUSE1_TEXT, page_ref="p.145", default_color="파랑",
        )
        clause_ill_2, i2 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_ill_hospital.coverage_id,
            clause_type="면책", article_no="[해외병원 질병입원일당 특별약관] 제2조(보험금을 지급하지 않는 사유)",
            text=ILL_HOSPITAL_CLAUSE2_TEXT, page_ref="p.146", default_color="빨강",
        )
        clause_ill_3, i3 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_ill_hospital.coverage_id,
            clause_type="공통", article_no="[해외병원 질병입원일당 특별약관] 제3조(준용규정)",
            text=ILL_HOSPITAL_CLAUSE3_TEXT, page_ref="p.146", default_color="회색",
        )
        clause_created += sum([i1, i2, i3])

        ill_treatment = types["ILL_OVERSEAS_TREATMENT"]
        map_created += sum([
            _get_or_create_map(db, clause_id=clause_ill_1.clause_id, type_id=ill_treatment.type_id, relevance="직접", confidence=1.0),
            _get_or_create_map(db, clause_id=clause_ill_2.clause_id, type_id=ill_treatment.type_id, relevance="면책", confidence=0.9),
        ])

        # ------------------------------------------------------------------
        # 3) 전쟁 상해사망후유장해 특별약관 (p.151)
        # ------------------------------------------------------------------
        cov_war = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "전쟁 상해사망후유장해 특별약관",
            )
            .first()
        )
        if not cov_war:
            cov_war = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_war.coverage_std_id,
                raw_name="전쟁 상해사망후유장해 특별약관",
                definition=WAR_RISK_CLAUSE1_TEXT,
                limit_amount="장해분류표 기준 지급률 × 보험가입금액",
                deductible=None,
                waiting_condition="해외여행 중 발생한 상해로 인한 사망 또는 후유장해",
            )
            db.add(cov_war)
            db.flush()
            coverage_created += 1

        clause_war_1, w1 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_war.coverage_id,
            clause_type="보장정의", article_no="[전쟁 상해사망후유장해 특별약관] 제1조(보험금의 지급사유)",
            text=WAR_RISK_CLAUSE1_TEXT, page_ref="p.151", default_color="파랑",
        )
        clause_war_2, w2 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_war.coverage_id,
            clause_type="조건", article_no="[전쟁 상해사망후유장해 특별약관] 제2조(계약 후 알릴 의무의 특례)",
            text=WAR_RISK_CLAUSE2_TEXT, page_ref="p.151", default_color="노랑",
        )
        clause_war_3, w3 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_war.coverage_id,
            clause_type="조건", article_no="[전쟁 상해사망후유장해 특별약관] 제3조(보험계약해지의 효력)",
            text=WAR_RISK_CLAUSE3_TEXT, page_ref="p.151", default_color="노랑",
        )
        clause_war_4, w4 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_war.coverage_id,
            clause_type="공통", article_no="[전쟁 상해사망후유장해 특별약관] 제4조(준용규정)",
            text=WAR_RISK_CLAUSE4_TEXT, page_ref="p.151", default_color="회색",
        )
        clause_created += sum([w1, w2, w3, w4])

        inj_death = types["INJ_DEATH_DISABILITY"]
        map_created += sum([
            _get_or_create_map(db, clause_id=clause_war_1.clause_id, type_id=inj_death.type_id, relevance="직접", confidence=0.95),
            _get_or_create_map(db, clause_id=clause_war_2.clause_id, type_id=inj_death.type_id, relevance="조건부", confidence=0.8),
        ])

        # ------------------------------------------------------------------
        # 4) 특수운동중 상해위험 특별약관 (p.152)
        # ------------------------------------------------------------------
        cov_sports = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "특수운동중 상해위험 특별약관",
            )
            .first()
        )
        if not cov_sports:
            cov_sports = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_sports_injury.coverage_std_id,
                raw_name="특수운동중 상해위험 특별약관",
                definition=SPORTS_INJURY_CLAUSE1_TEXT,
                limit_amount="보험가입금액(사망/후유장해/의료비 각각)",
                deductible=None,
                waiting_condition="전문등반, 글라이더 조종, 스카이다이빙, 스쿠버다이빙, 행글라이딩, 수상보트, 패러글라이딩 중 발생 상해",
            )
            db.add(cov_sports)
            db.flush()
            coverage_created += 1

        clause_sports_1, s1 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_sports.coverage_id,
            clause_type="보장정의", article_no="[특수운동중 상해위험 특별약관] 제1조(보험금의 지급사유)",
            text=SPORTS_INJURY_CLAUSE1_TEXT, page_ref="p.152", default_color="파랑",
        )
        clause_sports_2, s2 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_sports.coverage_id,
            clause_type="공통", article_no="[특수운동중 상해위험 특별약관] 제2조(준용규정)",
            text=SPORTS_INJURY_CLAUSE2_TEXT, page_ref="p.152", default_color="회색",
        )
        clause_created += sum([s1, s2])

        map_created += sum([
            _get_or_create_map(db, clause_id=clause_sports_1.clause_id, type_id=inj_death.type_id, relevance="직접", confidence=0.95),
            _get_or_create_map(db, clause_id=clause_sports_1.clause_id, type_id=inj_treatment.type_id, relevance="직접", confidence=0.9),
        ])

        # ------------------------------------------------------------------
        # 5) 특수운전중 상해위험 특별약관 (p.153)
        # ------------------------------------------------------------------
        cov_driving = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "특수운전중 상해위험 특별약관",
            )
            .first()
        )
        if not cov_driving:
            cov_driving = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_driving_injury.coverage_std_id,
                raw_name="특수운전중 상해위험 특별약관",
                definition=DRIVING_INJURY_CLAUSE1_TEXT,
                limit_amount="보험가입금액(사망/후유장해/의료비 각각)",
                deductible=None,
                waiting_condition="모터보트, 자동차/오토바이 경기, 시범, 흥행, 시운전(공용도로 제외) 중 발생 상해",
            )
            db.add(cov_driving)
            db.flush()
            coverage_created += 1

        clause_driving_1, d1 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_driving.coverage_id,
            clause_type="보장정의", article_no="[특수운전중 상해위험 특별약관] 제1조(보험금의 지급사유)",
            text=DRIVING_INJURY_CLAUSE1_TEXT, page_ref="p.153", default_color="파랑",
        )
        clause_driving_2, d2 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_driving.coverage_id,
            clause_type="공통", article_no="[특수운전중 상해위험 특별약관] 제2조(준용규정)",
            text=DRIVING_INJURY_CLAUSE2_TEXT, page_ref="p.153", default_color="회색",
        )
        clause_created += sum([d1, d2])

        map_created += sum([
            _get_or_create_map(db, clause_id=clause_driving_1.clause_id, type_id=inj_death.type_id, relevance="직접", confidence=0.95),
            _get_or_create_map(db, clause_id=clause_driving_1.clause_id, type_id=inj_treatment.type_id, relevance="직접", confidence=0.9),
        ])

        db.commit()
        print(
            "카카오페이 전체 재검토 청크3(p.133-198) 완료: "
            f"coverage_std 4건 신규(INJ_HOSPITAL_ALLOWANCE/ILL_HOSPITAL_ALLOWANCE/INJ_SPECIAL_SPORTS/INJ_SPECIAL_DRIVING), "
            f"coverage 신규={coverage_created}, clause 신규={clause_created}, clause_incident_map 신규={map_created}. "
            f"p.154-156 (안전귀국 환급/항공기 지연 알림), p.157-162+ (적용환율/선택가입/지정대리청구/장애인전환) "
            f"= 순수 계약행정/서비스로 사고유형 무관 (확인함, 매핑 없음)."
        )
    finally:
        db.close()


if __name__ == "__main__":
    run()
