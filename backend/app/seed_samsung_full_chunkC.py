"""
삼성화재(기준 보험사) 청크C: p.102~129쪽 처리
1. p.102~105: 4개 추가특별약관 (기존 OVS_INJ_MED 담보 확장)
   - 해외발생 상해의료비 자기부담금설정 추가특별약관 (p.102)
   - 해외발생 질병의료비 자기부담금설정 추가특별약관 (p.103)
   - 해외발생 한방의료비 보상제외 추가특별약관 (p.104)
   - 국민건강보험 미가입자 추가특별약관 (p.105)
   => 모두 clause_type='조건'으로 OVS_INJ_MED coverage_id에 붙임

2. p.106~129: "해외여행 비급여 실손의료비 특별약관" (새 담보)
   - 새 CoverageStd: NON_COVERED_MED="해외여행 비급여 실손의료비"
   - 지급사유(보장정의) Clause 3개
   - 면책 Clause 4개 (상해, 질병, 3대비급여, 공통)
   - IncidentType 매핑: 상해→INJ_OVERSEAS_TREATMENT, 질병→ILL_OVERSEAS_TREATMENT
"""
from app.database import SessionLocal
from app import models  # noqa: F401
from app.models.kb import Clause, ClauseIncidentMap, Coverage, CoverageStd, IncidentType, PolicyVersion, Product, Insurer
from app.services.kb_seed_common import get_or_create_coverage_std


# ========== 자기부담금 설정 & 조건 관련 추가특약 4개 ==========

DEDUCTIBLE_INJ_OVERSEAS = (
    "① 회사는 기본형 해외여행 실손의료비 특별약관 제3조(보장종목별 보상내용) 담보종목 (1)상해"
    "의료비의 세부구성항목 해외 보상하는 사항 제1항에도 불구하고 하나의 상해에 대하여 피보험"
    "자가 실제로 부담한 의료비 중 보험증권에 기재된 자기부담금을 초과하는 금액을 보상하여 드"
    "립니다."
)

DEDUCTIBLE_ILL_OVERSEAS = (
    "① 회사는 기본형 해외여행 실손의료비 특별약관 제3조(보장종목별 보상내용) 담보종목 (2)질병"
    "의료비의 세부구성항목 해외 보상하는 사항 제1항에도 불구하고 하나의 질병에 대하여 피보험"
    "자가 실제로 부담한 의료비 중 보험증권에 기재된 자기부담금을 초과하는 금액을 보상하여 드"
    "립니다."
)

EXCLUSION_KOREAN_MED = (
    "① 회사는 기본형 해외여행 실손의료비 특별약관 제3조(보장종목별 보상내용) 담보종목 (1)상해"
    "의료비의 세부구성항목 해외 보상하는 사항 제2항 및 (2)질병의료비의 세부구성항목 해외 보"
    "상하는 사항 제2항에도 불구하고 척추지압술(Chiroparactic, 추나요법 등)이나 침술(부항, 뜸"
    "포함) 치료로 인한 의료비를 보상하지 않습니다."
)

NON_INSURED_UNINSURED = (
    "① 이 추가특별약관의 피보험자는 기본형 해외여행 실손의료비 특별약관에 가입한 피보험자 중"
    "국민건강보험법 또는 의료급여법의 적용을 받지 않는 자로 합니다.\n"
    "② 보험기간중에 피보험자가 국민건강보험법 또는 의료급여법에 정한 자격을 취득하였을 때"
    "계약자는 서면으로 회사에 알리고 보험증권에 확인을 받아야 합니다.\n"
    "② 피보험자가 국민건강보험법 또는 의료급여법에 정한 자격을 취득한 경우 그 사실이 발생된"
    "날로부터 이 추가특별약관은 해지되며 회사는 경과하지 않은 기간에 대하여 일단위로 계산한"
    "정해진 보험료를 환급하여 드립니다.\n"
    "③ 기본형 해외여행 실손의료비 특별약관 제3조(보장종목별 보상내용)의 각 보장종목(상해의료비"
    "국내(급여), 질병의료비 국내(급여)) 제3항 제1호에서 정한 \"피보험자가 「국민건강보험법」제5"
    "조, 제53조, 제54조에 따라 요양급여 또는 「의료급여법」제4조, 제15조, 제17조에 따라 의료급"
    "여를 적용받지 못하는 경우(국민건강보험법에서 정한 요양급여 또는 의료급여법에서 정한 의료"
    "급여 절차를 거치지 않은 경우도 포함합니다)\"에도 불구하고 동 특별약관 제3조(보장종목별"
    "보상내용)의 각 보장종목(상해의료비 국내(급여), 질병의료비 국내(급여))의 제1항에서 정한 바"
    "에 따라 보상하여 드립니다."
)


# ========== 비급여 실손의료비 특약: 보장정의 ==========

NON_COVERED_DEF_INTRO = (
    "회사가 판매하는 해외여행 비급여 실손의료비 특별약관(이하 '특별약관'이라 합니다)은 상해"
    "비급여형(국내), 질병 비급여형(국내), 3대비급여형(국내)의 3개 보장종목으로 구성되어 있습니"
    "다."
)

# (1) 상해비급여 지급사유
NON_COVERED_INJ_PROVISION = (
    "① 회사는 피보험자가 상해로 인하여 의료기관에 입원 또는 통원(외래 및 처방조제)"
    "하여 치료를 받은 경우에는 비급여의료비(3대비급여는 제외합니다)를 제5조(보험가입금액의 한도 등)에서 정한 연간 보험가입금액의 한도 내에서 다음과 같이 보상합니다. 다만, 법령 등에 따라 의료비를 감면받거나 의료기관으로부터 의료비를 감면받은 경우(의료비를 납부하는 대가로 수수한 금액 등은 감면받은 의료비에 포함)에는 감면 후 실제 본인이 부담한 의료비 기준으로 계산하며, 감면받은 의료비가 근로소득에 포함된 경우, 「국가유공자 등 예우 및 지원에 관한 법률」및 「독립유공자 예우에 관한 법률」에 따라 의료비를 감면받은 경우에는 감면 전 의료비로 비급여 의료비를 계산합니다."
)

# (2) 질병비급여 지급사유
NON_COVERED_ILL_PROVISION = (
    "① 회사는 피보험자가 질병으로 의료기관에 입원 또는 통원(외래 및 처방조제)하여"
    "치료를 받은 경우에는 비급여의료비(3대비급여는 제외합니다)를 제5조(보험가입금액의 한도 등)에서 정한 연간 보험가입금액의 한도 내에서 다음과 같이 보상합니다. 다만, 법령 등에 따라 의료비를 감면받거나 의료기관으로부터 의료비를 감면받은 경우(의료비를 납부하는 대가로 수수한 금액 등은 감면받은 의료비에 포함)에는 감면 후 실제 본인이 부담한 의료비 기준으로 계산하며, 감면받은 의료비가 근로소득에 포함된 경우, 「국가유공자 등 예우 및 지원에 관한 법률」및 「독립유공자 예우에 관한 법률」에 따라 의료비를 감면받은 경우에는 감면 전 의료비로 비급여 의료비를 계산합니다."
)

# (3) 3대비급여 지급사유
NON_COVERED_3MAJOR_PROVISION = (
    "① 회사는 이 특별약관의 보험기간 중 상해 또는 질병의 치료목적으로 의료기관에"
    "입원 또는 통원하여 아래의 비급여 의료행위로 치료를 받은 경우에는 본인이 실제"
    "로 부담한 비급여의료비(행위료, 약제비, 치료재료대, 조영제, 판독료 포함)에서"
    "공제금액을 뺀 금액을 아래의 보장한도 범위 내에서 각각 보상합니다. 다만, 법령"
    "등에 따라 의료비를 감면받거나 의료기관으로부터 의료비를 감면받은 경우(의료비"
    "를 납부하는 대가로 수수한 금액 등은 감면받은 의료비에 포함)에는 감면 후 실제"
    "본인이 부담한 의료비 기준으로 계산하며, 감면받은 의료비가 근로소득에 포함된"
    "경우, 「국가유공자 등 예우 및 지원에 관한 법률」및 「독립유공자 예우에 관한"
    "법률」에 따라 의료비를 감면받은 경우에는 감면 전 의료비로 비급여 의료비를 계"
    "산합니다."
)


# ========== 비급여 실손의료비 특약: 면책 조항 ==========

# (1) 상해비급여 면책
NON_COVERED_INJ_WAIVER = (
    "① 회사는 다음의 사유로 인하여 생긴 비급여 의료비는 보상하지 않습니다. "
    "1. 피보험자가 고의로 자신을 해친 경우. 다만, 피보험자가 심신상실 등으로 자유로운 의사결정을 할 수 없는 상태에서 자신을 해친 사실이 증명된 경우에는 보상합니다. "
    "2. 보험수익자가 고의로 피보험자를 해친 경우. 다만, 그 보험수익자가 보험금의 일부 보험수익자인 경우에는 다른 보험수익자에 대한 보험금은 지급합니다. "
    "3. 계약자가 고의로 피보험자를 해친 경우 "
    "4. 피보험자가 임신, 출산(제왕절개를 포함합니다), 산후기로 입원 또는 통원한 경우. 다만, 회사가 보상하는 상해로 인하여 입원 또는 통원한 경우에는 보상합니다. "
    "5. 전쟁, 외국의 무력행사, 혁명, 내란, 사변, 폭동으로 인한 경우 "
    "6. 피보험자가 정당한 이유없이 입원기간 중 의사의 지시를 따르지 않거나 의사가 통원치료가 가능하다고 인정함에도 피보험자 본인이 자의적으로 입원하여 발생한 입원의료비 "
    "7. 피보험자가 정당한 이유없이 통원기간 중 의사의 지시를 따르지 않아 발생한 통원의료비 "
    "② 회사는 다른 약정이 없으면 피보험자가 직업, 직무 또는 동호회 활동 목적으로 한 다음의 어느 하나에 해당하는 행위로 인하여 생긴 상해에 대해서는 보상하지 않습니다. "
    "1. 전문등반(전문적인 등산용구를 사용하여 암벽 또는 빙벽을 오르내리거나 특수한 기술, 경험, 사전 훈련이 필요한 등반을 말합니다), 글라이더 조종, 스카이다이빙, 스쿠버다이빙, 행글라이딩, 수상보트, 패러글라이딩 "
    "2. 모터보트ㆍ자동차 또는 오토바이에 의한 경기, 시범, 행사(이를 위한 연습을 포함합니다) 또는 시운전(다만, 공용도로에서 시운전을 하는 동안 발생한 상해는 보상합니다) "
    "3. 선박에 탑승하는 것을 직무로 하는 사람이 직무상 선박에 탑승하고 있는 동안 "
    "③ 회사는 다음의 비급여 의료비에 대해서는 보상하지 않습니다. "
    "1. 치과치료(다만 안면부 골절로 발생한 의료비는 치아관련 치료를 제외하고 보상합니다)ㆍ한방치료(다만, 「의료법」 제2조에 따른 한의사를 제외한 '의사'의 의료행위에 의해서 발생한 의료비는 보상합니다) "
    "2. 영양제, 비타민제 등의 약제와 관련하여 소요된 비용. 다만 약관상 보상하는 상해를 치료함에 있어 아래 각목에 해당하는 경우는 치료 목적으로 보아 보상합니다. "
    "가. 약사법령에 의하여 약제별 허가사항 또는 신고된 사항(효능/효과 및 용법/용량 등)대로 사용된 경우 "
    "나. 요양급여 약제가 관련 법령 또는 고시 등에서 정한 별도의 적용기준대로 비급여 약제로 사용된 경우 "
    "다. 요양급여 약제가 관련 법령에 따라 별도의 비급여사용승인 절차를 거쳐 그 승인 내용대로 사용된 경우 "
    "라. 상기 가목 부터 다목의 약제가 두 가지 이상 함께 사용된 경우(함께 사용된 약제중 어느 하나라도 상기 가목 부터 다목에 해당하지 않는 경우 제외) "
    "3. 호르몬 투여, 보신용 투약, 의약외품과 관련하여 소요된 비용 "
    "4. 의치, 의수족, 의안, 안경, 콘택트렌즈, 보청기, 목발, 팔걸이(Arm Sling), 보조기 등 진료 재료의 구입 및 대체 비용. 다만, 인공장기 등 신체에 이식되어 그 기능을 대신하는 경우에는 보상합니다. "
    "5. 진료와 무관한 각종 비용(TV시청료, 전화료, 각종 증명료 등을 말합니다), 의사의 임상적 소견과 관련이 없는 검사비용, 간병비 "
    "6. 자동차보험(공제를 포함합니다)에서 보상받는 치료관계비(과실상계 후 금액을 기준으로 합니다) 또는 산재보험에서 보상받는 의료비. 다만, 본인부담의료비(자동차보험 진료수가에 관한 기준 및 산재보험 요양급여 산정기준에 따라 발생한 실제 본인 부담의료비)는 제3조(보장종목별 보상내용) (1)상해비급여 제1항부터 제7항에 따라 보상합니다. "
    "7. 「국민건강보험법」 제42조의 요양기관이 아닌 외국에 있는 의료기관에서 발생한 의료비 "
    "8. 「응급의료에 관한 법률」 및 동법 시행규칙에서 정한 응급환자에 해당하지 않는 자가 동법 제26조 권역응급의료센터 또는 「의료법」제3조의4에 따른 상급종합병원 응급실을 이용하면서 발생한 응급의료관리료"
)

# (2) 질병비급여 면책
NON_COVERED_ILL_WAIVER = (
    "① 회사는 다음의 사유로 인하여 생긴 비급여 의료비는 보상하지 않습니다. "
    "1. 피보험자가 고의로 자신을 해친 경우. 다만, 피보험자가 심신상실 등으로 자유로운 의사결정을 할 수 없는 상태에서 자신을 해친 사실이 증명된 경우에는 보상합니다. "
    "2. 보험수익자가 고의로 피보험자를 해친 경우. 다만, 그 보험수익자가 보험금의 일부 보험수익자인 경우에는 다른 보험수익자에 대한 보험금은 지급합니다. "
    "3. 계약자가 고의로 피보험자를 해친 경우 "
    "4. 피보험자가 정당한 이유 없이 입원기간 중 의사의 지시를 따르지 않거나 의사가 통원치료가 가능하다고 인정함에도 피보험자 본인이 자의적으로 입원하여 발생한 입원의료비 "
    "5. 피보험자가 정당한 이유 없이 통원기간 중 의사의 지시를 따르지 않아 발생한 통원의료비 "
    "② 회사는 '한국표준질병사인분류'에 따른 다음의 비급여 의료비에 대해서는 보상하지 않습니다. "
    "1. 정신 및 행동장애(F04∼F99) "
    "2. 여성생식기의 비염증성 장애로 인한 습관성 유산, 불임 및 인공수정관련 합병증(N96∼N98) "
    "3. 피보험자가 임신, 출산(제왕절개를 포함합니다), 산후기로 입원또는 통원한 경우(O00∼O99) "
    "4. 선천성 뇌질환(Q00∼Q04) "
    "5. 비만(E66) "
    "6. 요실금(N39.3, N39.4, R32) "
    "7. 직장 또는 항문 질환(K60∼K62, K64) "
    "③ 회사는 다음의 비급여 의료비에 대해서는 보상하지 않습니다. "
    "1. 치과치료(K00∼K08) 및 한방치료(다만, 「의료법」 제2조에 따른 한의사를 제외한 '의사'의 의료행위에 의해서 발생한 의료비는 보상합니다) "
    "2. 영양제, 비타민제 등의 약제와 관련하여 소요된 비용. 다만 약관상 보상하는 질병을 치료함에 있어 아래 각목에 해당하는 경우는 치료 목적으로 보아 보상합니다. "
    "가. 약사법령에 의하여 약제별 허가사항 또는 신고된 사항(효능/효과 및 용법/용량등)대로 사용된 경우 "
    "나. 요양급여 약제가 관련 법령 또는 고시 등에서 정한 별도의 적용기준대로 비급여 약제로 사용된 경우 "
    "다. 요양급여 약제가 관련 법령에 따라 별도의 비급여사용승인 절차를 거쳐 그 승인 내용대로 사용된 경우 "
    "라. 상기 가목 부터 다목의 약제가 두 가지 이상 함께 사용된 경우(함께 사용된약제중 어느 하나라도 상기 가목 부터 다목에 해당하지 않는 경우 제외) "
    "3. 호르몬 투여, 보신용 투약, 의약외품과 관련하여 소요된 비용 "
    "4. 의치, 의수족, 의안, 안경, 콘택트렌즈, 보청기, 목발, 팔걸이(Arm Sling), 보조기 등 진료 재료의 구입 및 대체 비용. 다만, 인공장기 등 신체에 이식되어 그 기능을 대신하는 경우에는 보상합니다. "
    "5. 진료와 무관한 각종 비용(TV시청료, 전화료, 각종 증명료 등을 말합니다), 의사의 임상적 소견과 관련이 없는 검사비용, 간병비 "
    "6. 산재보험에서 보상받는 의료비. 다만, 본인부담의료비(산재보험 요양급여 산정기준에 따라 발생한 실제 본인 부담의료비)는 제3조(보장종목별 보상내용) (2)질병비급여 제1항부터 제7항에 따라 보상합니다. "
    "7. 사람면역결핍바이러스(HIV) 감염으로 인한 치료비(다만, 「의료법」에서 정한 의료인의 진료상 또는 치료중 혈액에 의한 HIV 감염은 해당 진료기록을 통해 객관적으로 확인되는 경우는 보상합니다) "
    "8.「국민건강보험법」 제42조의 요양기관이 아닌 외국에 있는 의료기관에서 발생한 의료비 "
    "9. 「응급의료에 관한 법률」 및 동법 시행규칙에서 정한 응급환자에 해당하지 않는 자가 동법 제26조 권역응급의료센터 또는 「의료법」제3조의4에 따른 상급종합병원 응급실을 이용하면서 발생한 응급의료관리료"
)

# (3) 3대비급여 면책
NON_COVERED_3MAJOR_WAIVER = (
    "① 회사는 다음의 사유로 인하여 생긴 비급여 의료비는 보상하지 않습니다. "
    "1. 피보험자가 고의로 자신을 해친 경우. 다만, 피보험자가 심신상실 등으로 자유로운 의사결정을 할 수 없는 상태에서 자신을 해친 사실이 증명된 경우에는 제3조(보장종목별 보상내용)에 따라 보상합니다. "
    "2. 보험수익자가 고의로 피보험자를 해친 경우. 다만, 그 보험수익자가 보험금의 일부 보험수익자인 경우에는 다른 보험수익자에 대한 보험금은 제3조(보장종목별 보상내용)에 따라 지급합니다. "
    "3. 계약자가 고의로 피보험자를 해친 경우 "
    "4. 전쟁, 외국의 무력행사, 혁명, 내란, 사변, 폭동으로 인한 경우 "
    "5. 피보험자가 정당한 이유없이 입원 또는 통원 기간 중 의사의 지시를 따르지 않아 발생한 의료비 "
    "② 회사는 다른 약정이 없으면 피보험자가 직업, 직무 또는 동호회 활동 목적으로 한 다음의 어느 하나에 해당하는 행위로 인하여 생긴 상해에 대해서는 보상하지 않습니다. "
    "1. 전문등반(전문적인 등산용구를 사용하여 암벽 또는 빙벽을 오르내리거나 특수한 기술, 경험, 사전 훈련이 필요한 등반을 말합니다), 글라이더 조종, 스카이다이빙, 스쿠버다이빙, 행글라이딩, 수상보트, 패러글라이딩 "
    "2. 모터보트ㆍ자동차 또는 오토바이에 의한 경기, 시범, 행사(이를 위한 연습을 포함합니다) 또는 시운전(다만, 공용도로에서 시운전을 하는 동안 발생한 상해는 제3조(보장종목별 보상내용)에 따라 보상합니다) "
    "3. 선박에 탑승하는 것을 직무로 하는 사람이 직무상 선박에 탑승하고 있는 동안 "
    "③ 회사는 '한국표준질병사인분류'에 따른 다음의 비급여 의료비에 대해서는 보상하지 않습니다. "
    "1. 정신 및 행동장애(F04∼F99) "
    "2. 여성생식기의 비염증성 장애로 인한 습관성 유산, 불임 및 인공수정관련 합병증(N96∼N98) "
    "3. 피보험자가 임신, 출산(제왕절개를 포함합니다), 산후기로 입원 또는 통원한 경우(O00∼O99). 다만, 회사가 보상하는 상해로 인하여 입원 또는 통원한 경우에는 제3조(보장종목별 보상내용)에 따라 보상합니다. "
    "4. 선천성 뇌질환(Q00∼Q04) "
    "5. 비만(E66) "
    "6. 요실금(N39.3, N39.4, R32) "
    "7. 직장 또는 항문 질환(K60∼K62, K64) "
    "④ 회사는 다음의 비급여 의료비에 대해서는 보상하지 않습니다. "
    "1. 치과치료(다만, 안면부 골절로 발생한 의료비는 치아관련 치료를 제외하고 제3조(보장종목별 보상내용)에 따라 보상하며, K00~K08과 무관한 질병으로 인한 의료비는 제3조(보장종목별 보상내용)에 따라 보상합니다)ㆍ한방치료(다만, 「의료법」 제2조에 따른 한의사를 제외한 '의사'의 의료행위에 의해서 발생한 의료비는 제3조(보장종목별 보상내용)에 따라 보상합니다) "
    "2. 영양제, 비타민제 등의 약제와 관련하여 소요된 비용. 다만 약관상 보상하는 상해 또는 질병을 치료함에 있어 아래 각목에 해당하는 경우는 치료 목적으로 보아 보상합니다. "
    "가. 약사법령에 의하여 약제별 허가사항 또는 신고된 사항(효능/효과 및 용법/용량등)대로 사용된 경우 "
    "나. 요양급여 약제가 관련 법령 또는 고시 등에서 정한 별도의 적용기준대로 비급여 약제로 사용된 경우 "
    "다. 요양급여 약제가 관련 법령에 따라 별도의 비급여사용승인 절차를 거쳐 그 승인 내용대로 사용된 경우 "
    "라. 상기 가목 부터 다목의 약제가 두 가지 이상 함께 사용된 경우(함께 사용된약제중 어느 하나라도 상기 가목 부터 다목에 해당하지 않는 경우 제외) "
    "3. 호르몬 투여, 보신용 투약, 의약외품과 관련하여 소요된 비용 "
    "4. 의치, 의수족, 의안, 안경, 콘택트렌즈, 보청기, 목발, 팔걸이(Arm Sling), 보조기 등 진료 재료의 구입 및 대체 비용. 다만, 인공장기 등 신체에 이식되어 그 기능을 대신하는 경우에는 보상합니다. "
    "5. 진료와 무관한 각종 비용(TV시청료, 전화료, 각종 증명료 등을 말합니다), 의사의 임상적 소견과 관련이 없는 검사비용, 간병비 "
    "6. 자동차보험(공제를 포함합니다)에서 보상받는 치료관계비(과실상계 후 금액을 기준으로 합니다) 또는 산재보험에서 보상받는 의료비. 다만, 본인부담의료비(자동차보험 진료수가에 관한 기준 및 산재보험 요양급여 산정기준에 따라 발생한 실제 본인 부담의료비)는 제3조(보장종목별 보상내용) (3)3대비급여 제1항부터 제7항에 따라 보상합니다. "
    "7. 사람면역결핍바이러스(HIV) 감염으로 인한 치료비(다만, 「의료법」에서 정한 의료인의 진료상 또는 치료중 혈액에 의한 HIV 감염은 해당 진료기록을 통해 객관적으로 확인되는 경우는 제3조(보장종목별 보상내용)에 따라 보상합니다) "
    "8. 「국민건강보험법」 제42조의 요양기관이 아닌 외국에 있는 의료기관에서 발생한 의료비 "
    "9. 「응급의료에 관한 법률」 및 동법 시행규칙에서 정한 응급환자에 해당하지 않는 자가 동법 제26조 권역응급의료센터 또는 「의료법」제3조의4에 따른 상급종합병원 응급실을 이용하면서 발생한 응급의료관리료"
)


def run():
    db = SessionLocal()
    try:
        insurer = db.query(Insurer).filter_by(code="SAMSUNG").first()
        if not insurer:
            print("삼성화재가 아직 시딩되지 않았습니다. seed_samsung을 먼저 실행하세요.")
            return

        policy_version = (
            db.query(PolicyVersion)
            .join(Product, Product.product_id == PolicyVersion.product_id)
            .filter(Product.insurer_id == insurer.insurer_id)
            .first()
        )

        if not policy_version:
            print("정책 버전이 없습니다.")
            return

        # ========== 1. p.102~105: 4개 추가특별약관을 OVS_INJ_MED에 추가 ==========

        ovs_inj_med = (
            db.query(Coverage)
            .filter(Coverage.policy_version_id == policy_version.policy_version_id,
                    Coverage.raw_name.like("%상해 해외의료비%"))
            .first()
        )

        added_deductible_clauses = 0

        if ovs_inj_med:
            # 1-1. 해외발생 상해의료비 자기부담금설정
            clause_exists = db.query(Clause).filter(
                Clause.coverage_id == ovs_inj_med.coverage_id,
                Clause.text == DEDUCTIBLE_INJ_OVERSEAS
            ).first()
            if not clause_exists:
                db.add(Clause(
                    policy_version_id=policy_version.policy_version_id,
                    coverage_id=ovs_inj_med.coverage_id,
                    clause_type="조건",
                    article_no="해외발생 상해의료비 자기부담금설정 추가특별약관 제1조",
                    text=DEDUCTIBLE_INJ_OVERSEAS,
                    page_ref="p.102",
                    default_color="파랑",
                ))
                added_deductible_clauses += 1

            # 1-2. 해외발생 질병의료비 자기부담금설정
            clause_exists = db.query(Clause).filter(
                Clause.coverage_id == ovs_inj_med.coverage_id,
                Clause.text == DEDUCTIBLE_ILL_OVERSEAS
            ).first()
            if not clause_exists:
                db.add(Clause(
                    policy_version_id=policy_version.policy_version_id,
                    coverage_id=ovs_inj_med.coverage_id,
                    clause_type="조건",
                    article_no="해외발생 질병의료비 자기부담금설정 추가특별약관 제1조",
                    text=DEDUCTIBLE_ILL_OVERSEAS,
                    page_ref="p.103",
                    default_color="파랑",
                ))
                added_deductible_clauses += 1

            # 1-3. 해외발생 한방의료비 보상제외
            clause_exists = db.query(Clause).filter(
                Clause.coverage_id == ovs_inj_med.coverage_id,
                Clause.text == EXCLUSION_KOREAN_MED
            ).first()
            if not clause_exists:
                db.add(Clause(
                    policy_version_id=policy_version.policy_version_id,
                    coverage_id=ovs_inj_med.coverage_id,
                    clause_type="면책",
                    article_no="해외발생 한방의료비 보상제외 추가특별약관 제1조",
                    text=EXCLUSION_KOREAN_MED,
                    page_ref="p.104",
                    default_color="빨강",
                ))
                added_deductible_clauses += 1

            # 1-4. 국민건강보험 미가입자 추가특별약관
            clause_exists = db.query(Clause).filter(
                Clause.coverage_id == ovs_inj_med.coverage_id,
                Clause.text == NON_INSURED_UNINSURED
            ).first()
            if not clause_exists:
                db.add(Clause(
                    policy_version_id=policy_version.policy_version_id,
                    coverage_id=ovs_inj_med.coverage_id,
                    clause_type="조건",
                    article_no="국민건강보험 미가입자 추가특별약관 제1~3조",
                    text=NON_INSURED_UNINSURED,
                    page_ref="p.105",
                    default_color="초록",
                ))
                added_deductible_clauses += 1

        # ========== 2. p.106~129: 새 담보 NON_COVERED_MED ==========

        # 2-1. CoverageStd 생성
        non_covered_std = get_or_create_coverage_std(
            db, "NON_COVERED_MED", "해외여행 비급여 실손의료비", "의료", False
        )

        # 2-2. Coverage 생성
        existing_coverage = db.query(Coverage).filter(
            Coverage.policy_version_id == policy_version.policy_version_id,
            Coverage.coverage_std_id == non_covered_std.coverage_std_id
        ).first()

        if not existing_coverage:
            non_covered_coverage = Coverage(
                policy_version_id=policy_version.policy_version_id,
                coverage_std_id=non_covered_std.coverage_std_id,
                raw_name="해외여행 비급여 실손의료비 특별약관",
                definition=NON_COVERED_DEF_INTRO,
            )
            db.add(non_covered_coverage)
            db.flush()
        else:
            non_covered_coverage = existing_coverage

        added_non_covered_clauses = 0

        # 2-3. 지급사유 Clause 3개

        # (1) 상해비급여 보장정의
        clause_exists = db.query(Clause).filter(
            Clause.coverage_id == non_covered_coverage.coverage_id,
            Clause.text == NON_COVERED_INJ_PROVISION
        ).first()
        if not clause_exists:
            inj_clause = Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=non_covered_coverage.coverage_id,
                clause_type="보장정의",
                article_no="제3조(보장종목별 보상내용) (1)상해비급여",
                text=NON_COVERED_INJ_PROVISION,
                page_ref="p.108-111",
                default_color="파랑",
            )
            db.add(inj_clause)
            db.flush()

            # INJ_OVERSEAS_TREATMENT 매핑
            inj_type = db.query(IncidentType).filter_by(l2_code="INJ_OVERSEAS_TREATMENT").first()
            if inj_type:
                db.add(ClauseIncidentMap(
                    clause_id=inj_clause.clause_id,
                    type_id=inj_type.type_id,
                    relevance="직접",
                    mapped_by="human",
                    confidence=1.0,
                ))
            added_non_covered_clauses += 1

        # (2) 질병비급여 보장정의
        clause_exists = db.query(Clause).filter(
            Clause.coverage_id == non_covered_coverage.coverage_id,
            Clause.text == NON_COVERED_ILL_PROVISION
        ).first()
        if not clause_exists:
            ill_clause = Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=non_covered_coverage.coverage_id,
                clause_type="보장정의",
                article_no="제3조(보장종목별 보상내용) (2)질병비급여",
                text=NON_COVERED_ILL_PROVISION,
                page_ref="p.111-113",
                default_color="파랑",
            )
            db.add(ill_clause)
            db.flush()

            # ILL_OVERSEAS_TREATMENT 매핑
            ill_type = db.query(IncidentType).filter_by(l2_code="ILL_OVERSEAS_TREATMENT").first()
            if ill_type:
                db.add(ClauseIncidentMap(
                    clause_id=ill_clause.clause_id,
                    type_id=ill_type.type_id,
                    relevance="직접",
                    mapped_by="human",
                    confidence=1.0,
                ))
            added_non_covered_clauses += 1

        # (3) 3대비급여 보장정의
        clause_exists = db.query(Clause).filter(
            Clause.coverage_id == non_covered_coverage.coverage_id,
            Clause.text == NON_COVERED_3MAJOR_PROVISION
        ).first()
        if not clause_exists:
            major3_clause = Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=non_covered_coverage.coverage_id,
                clause_type="보장정의",
                article_no="제3조(보장종목별 보상내용) (3)3대비급여",
                text=NON_COVERED_3MAJOR_PROVISION,
                page_ref="p.114-117",
                default_color="파랑",
            )
            db.add(major3_clause)
            db.flush()

            # 3대비급여는 상해와 질병 모두 포함하므로 둘 다 매핑
            inj_type = db.query(IncidentType).filter_by(l2_code="INJ_OVERSEAS_TREATMENT").first()
            ill_type = db.query(IncidentType).filter_by(l2_code="ILL_OVERSEAS_TREATMENT").first()
            if inj_type:
                db.add(ClauseIncidentMap(
                    clause_id=major3_clause.clause_id,
                    type_id=inj_type.type_id,
                    relevance="직접",
                    mapped_by="human",
                    confidence=1.0,
                ))
            if ill_type:
                db.add(ClauseIncidentMap(
                    clause_id=major3_clause.clause_id,
                    type_id=ill_type.type_id,
                    relevance="직접",
                    mapped_by="human",
                    confidence=1.0,
                ))
            added_non_covered_clauses += 1

        # 2-4. 면책 Clause 4개

        # (1) 상해비급여 면책
        clause_exists = db.query(Clause).filter(
            Clause.coverage_id == non_covered_coverage.coverage_id,
            Clause.text == NON_COVERED_INJ_WAIVER
        ).first()
        if not clause_exists:
            inj_waiver = Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=non_covered_coverage.coverage_id,
                clause_type="면책",
                article_no="제4조(보상하지 않는 사항) (1)상해비급여",
                text=NON_COVERED_INJ_WAIVER,
                page_ref="p.119-120",
                default_color="빨강",
            )
            db.add(inj_waiver)
            db.flush()

            inj_type = db.query(IncidentType).filter_by(l2_code="INJ_OVERSEAS_TREATMENT").first()
            if inj_type:
                db.add(ClauseIncidentMap(
                    clause_id=inj_waiver.clause_id,
                    type_id=inj_type.type_id,
                    relevance="면책",
                    mapped_by="human",
                    confidence=1.0,
                ))
            added_non_covered_clauses += 1

        # (2) 질병비급여 면책
        clause_exists = db.query(Clause).filter(
            Clause.coverage_id == non_covered_coverage.coverage_id,
            Clause.text == NON_COVERED_ILL_WAIVER
        ).first()
        if not clause_exists:
            ill_waiver = Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=non_covered_coverage.coverage_id,
                clause_type="면책",
                article_no="제4조(보상하지 않는 사항) (2)질병비급여",
                text=NON_COVERED_ILL_WAIVER,
                page_ref="p.121-122",
                default_color="빨강",
            )
            db.add(ill_waiver)
            db.flush()

            ill_type = db.query(IncidentType).filter_by(l2_code="ILL_OVERSEAS_TREATMENT").first()
            if ill_type:
                db.add(ClauseIncidentMap(
                    clause_id=ill_waiver.clause_id,
                    type_id=ill_type.type_id,
                    relevance="면책",
                    mapped_by="human",
                    confidence=1.0,
                ))
            added_non_covered_clauses += 1

        # (3) 3대비급여 면책
        clause_exists = db.query(Clause).filter(
            Clause.coverage_id == non_covered_coverage.coverage_id,
            Clause.text == NON_COVERED_3MAJOR_WAIVER
        ).first()
        if not clause_exists:
            major3_waiver = Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=non_covered_coverage.coverage_id,
                clause_type="면책",
                article_no="제4조(보상하지 않는 사항) (3)3대비급여",
                text=NON_COVERED_3MAJOR_WAIVER,
                page_ref="p.124-126",
                default_color="빨강",
            )
            db.add(major3_waiver)
            db.flush()

            inj_type = db.query(IncidentType).filter_by(l2_code="INJ_OVERSEAS_TREATMENT").first()
            ill_type = db.query(IncidentType).filter_by(l2_code="ILL_OVERSEAS_TREATMENT").first()
            if inj_type:
                db.add(ClauseIncidentMap(
                    clause_id=major3_waiver.clause_id,
                    type_id=inj_type.type_id,
                    relevance="면책",
                    mapped_by="human",
                    confidence=1.0,
                ))
            if ill_type:
                db.add(ClauseIncidentMap(
                    clause_id=major3_waiver.clause_id,
                    type_id=ill_type.type_id,
                    relevance="면책",
                    mapped_by="human",
                    confidence=1.0,
                ))
            added_non_covered_clauses += 1

        db.commit()
        print(f"samsung 청크C(p.102~129): 추가특약 조건={added_deductible_clauses}, 비급여실손={added_non_covered_clauses}")

    finally:
        db.close()


if __name__ == "__main__":
    run()
