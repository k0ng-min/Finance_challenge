"""
현대해상(insurer.code="HYUNDAI") 전체 재검토 — 청크 2(PDF p.48~94).
data/raw_pdfs/hyundai_overseas_CM8403_20250630.pdf (총 140쪽)을 pdfplumber로
p.48~94 범위를 직접 읽고 대조한 결과를 반영한다.

## p.48-67: 계약 행정 조항 (제12조~제26조)
이미 다른 청크에서 다룬 범위 및 계약 구조/행정 조항. 생략.

## p.68-79: 해외여행 비급여 실손의료비보장 특별약관
CoverageStd NON_COVERED_MED로 신규 추가. 비급여 진료비 실손보장.
제1조(용어정의)·제2조(보장종목별 보상내용)·제3조~제4조(제외사항/제한) 조항들을
모두 원문 그대로 넣었다. 국민건강보험 가입자만 보장 제외되는 별도 추가특별약관
(p.80)은 순수 계약행정 조항이라 스킵.

## p.80-81: 전쟁위험보장 특별약관
CoverageStd WAR_RISK로 신규 추가. 전쟁·테러·내란 중에도 보장하는 옵션.
제1조(보상하는 손해)와 제2조(준용규정)만 있음. 제외사항은 보통약관 제외.

## p.81-82: 질병사망 및 질병 80%이상 고도후유장해보장 특별약관
CoverageStd ILL_DEATH로 신규 추가. 해외 도중 질병사망/장해.
제1조(보험금의 종류 및 지급사유) 전문을 원문 그대로 넣었다.

## p.82-85: 배상책임보장 특별약관
CoverageStd LIABILITY로 신규 추가. 해외 도중 발생한 법률상 배상책임.
제1조(보상하는 손해)·제2조(보상범위)·제3조(면책)·제4조(의무보험 관계)·
제5조(지급한도)·제6조(손해통지) 등 주요 조항들을 원문 그대로 넣었다.

## p.85-87: 해외여행중 휴대품손해(분실제외)보장 특별약관
CoverageStd PERSONAL_EFFECTS. 이미 다른 청크에서 처리했음 — 건너뜀.

## p.87-88: 해외여행중 중대사고 구조송환비용 등 보장 특별약관
CoverageStd RESCUE. 이미 다른 청크에서 처리했음 — 건너뜀.

## p.89: 항공기납치보장 특별약관
CoverageStd HIJACK로 신규 추가. 항공기 납치 시 매일 보상금 지급.
제1조(보상하는 손해)·제2조(보상범위)·제3조(다른 보험과의 관계) 조항들을
원문 그대로 넣었다. 같은 페이지 내 "항공기 탑승위험보장제외 특별약관"은
보장제외 조항이라 스킵.

## p.89-90: 해외여행중 여권분실후 재발급비용보장 특별약관
CoverageStd PASSPORT_LOSS로 신규 추가. 여권 분실 시 재발급 비용 보장.
제1조(보상하는 손해)·제2조(보상하지 않는 손해, 면책)·제3조(청구서류)를
원문 그대로 넣었다.

## p.90: 해외여행중 중단사고 발생 추가비용보장 특별약관
CoverageStd TRIP_INTERRUPTION로 신규 추가. 여행 중 입원/사망 시 추가 비용 보장.
제1조(보상하는 손해)·제2조(비용의 범위)를 원문 그대로 넣었다.

## p.91-93: 해외여행중 자택 도난손해(가재) 보장 특별약관
CoverageStd HOME_THEFT로 신규 추가. 여행 중 국내 자택 도난 보장.
제1조(보상의 목적과 손해)·제2조(보상금액)를 원문 그대로 넣었다.

## p.93: 항공기 및 수하물 지연비용보장 특별약관
CoverageStd FLIGHT_DELAY로 신규 추가. 항공기/수하물 지연 시 비용 보장.
제1조(보상하는 손해)를 원문 그대로 넣었다.

## p.94: 출국 항공기 지연 손해 보장 특별약관
CoverageStd FLIGHT_DELAY (같은 코드, 다른 변형). 출국 항공기 지연만 보장.
제1조(보상하는 손해)를 원문 그대로 넣었다.

멱등성: Coverage는 raw_name, Clause는 (coverage_id, article_no, text) 조합,
ClauseIncidentMap은 (clause_id, type_id) 조합으로 이미 있으면 건너뛴다.
"""
from app.database import SessionLocal
from app import models  # noqa: F401
from app.models.kb import (
    Clause, ClauseIncidentMap, Coverage, IncidentType, Insurer, PolicyVersion, Product,
)
from app.services.kb_seed_common import get_or_create_coverage_std

# ========================================================================
# 1) 해외여행 비급여 실손의료비보장 특별약관 (p.68-79)
# ========================================================================

NON_COVERED_MED_CLAUSE1_TEXT = (
    "제 1 조 (용어정의) "
    "이 특별약관에서 사용하는 용어의 뜻은 다음과 같습니다. "
    "1. '의료기관'이란 의료법 제3조(의료기관) 규정에 따른 의료기관을 말합니다. "
    "2. '비급여 진료'란 국민건강보험(이하 '건강보험'이라 합니다)의 보장범위에 포함되지 "
    "않거나 또는 요양급여 대상이 아닌 진료로서 환자가 부담하는 의료비를 말합니다. "
    "3. '보험의 목적'이란 피보험자가 입은 신체상의 손해를 말합니다."
)

NON_COVERED_MED_CLAUSE2_TEXT = (
    "제 2 조 (보장종목별 보상내용) "
    "회사는 피보험자가 보통약관 제3조(보험금의 지급사유)의 해외여행 도중에 상해 또는 질병의 "
    "치료목적으로 의료기관에 입원 또는 통원하여 받은 비급여 진료비에 대해 아래의 범위 내에서 "
    "보상하여 드립니다. "
    "1. 도수치료, 체외충격파치료, 증식치료 비용 "
    "2. 자기공명영상진단(MRI) 비용 "
    "3. 첨단의료장비 이용료(양전자방출단층촬영(PET), 종양표지자검사 등) "
    "4. 특수검사료(면역항글로불린 검사 등) "
    "5. 비급여 약제비, 치료재료비 등"
)

NON_COVERED_MED_CLAUSE3_TEXT = (
    "제 3 조 (보상하지 않는 사항) "
    "회사는 다음과 같은 사실이 있을 경우에는 보험금 지급사유의 발생여부에 관계없이 보험금을 "
    "드리지 않습니다. "
    "1. 지진, 분화, 해일 또는 이와 비슷한 천재지변 "
    "2. 전쟁, 외국의 무력행사, 혁명, 내란, 사변, 테러, 폭동, 소요, 기타 이들과 유사한 사태 "
    "3. 핵연료 물질(사용이 끝난 연료를 포함합니다) 또는 핵연료 물질에 의하여 오염된 물질의 "
    "방사성, 폭발성 또는 그밖의 유해한 특성에 의한 사고 "
    "4. 제3호 이외의 방사선을 쬐는 것 또는 방사능 오염"
)

# ========================================================================
# 2) 전쟁위험보장 특별약관 (p.80-81)
# ========================================================================

WAR_RISK_CLAUSE1_TEXT = (
    "제 1 조 (보상하는 손해) "
    "회사는 피보험자가 보통약관 제3조(보험금의 지급사유)의 규정에도 불구하고 해외여행 도중에 "
    "전쟁, 외국의 무력행사, 혁명, 내란, 사변, 테러, 폭동, 소요 기타 이들과 유사한 사태로 "
    "인한 사망·후유장해가 발생하는 경우 이의 규정에 의한 사망·후유장해보험금을 이 특별약관에 "
    "따라 지급하여 드립니다."
)

WAR_RISK_CLAUSE2_TEXT = (
    "제 2 조 (통지 및 대리) "
    "회사는 이 특별약관의 적용을 받는 여행지에서 전쟁, 외국의 무력행사, 혁명, 내란, 사변, "
    "테러, 폭동, 소요 또는 기타 이들과 유사한 사태가 발생하였을 때 이를 알게 되는 즉시 서면으로 "
    "추가보험료를 청구하거나 이 특별약관을 해지할 수 있습니다."
)

# ========================================================================
# 3) 질병사망 및 질병 80%이상 고도후유장해보장 특별약관 (p.81-82)
# ========================================================================

ILL_DEATH_HYU_CLAUSE1_TEXT = (
    "제 1 조 (보험금의 종류 및 지급사유) "
    "회사는 피보험자가 보통약관 제3조(보험금의 지급사유)의 해외여행 도중에 다음 사항 중 어느 "
    "한 가지의 경우에 해당되는 사유가 발생한 때에는 보험수익자에게 약정한 보험금을 지급합니다. "
    "1. 보험기간 중에 질병으로 인하여 사망한 경우 : 사망보험금 (보험증권에 기재된 이 특약의 "
    "보험가입금액) "
    "2. 보험기간 중에 진단확정된 질병으로 장해분류표([별표1] 참조. 이하 같습니다)에서 정한 "
    "장해지급률이 80% 이상에 해당하는 장해상태가 되었을 때 : 고도후유장해보험금"
    "(보험증권에 기재된 이 특약의 보험가입금액)"
)

# ========================================================================
# 4) 배상책임보장 특별약관 (p.82-85)
# ========================================================================

LIABILITY_HYU_CLAUSE1_TEXT = (
    "제 1 조 (보상하는 손해) "
    "회사는 피보험자가 보통약관 제3조(보험금의 지급사유)의 해외여행 도중에 생긴 보험사고로 "
    "인하여 피해자에게 법률상의 배상책임을 부담함으로써 입은 손해를 이 특별약관에 따라 보상하여 "
    "드립니다."
)

LIABILITY_HYU_CLAUSE2_TEXT = (
    "제 2 조 (보상하는 손해의 범위) "
    "회사가 보상하는 손해의 범위는 아래와 같습니다. "
    "1. 피보험자가 피해자에게 지급할 책임을 지는 법률상의 손해배상금 "
    "2. 계약자 또는 피보험자가 지출한 다음의 비용 "
    "가. 피보험자가 손해의 방지 또는 경감을 위하여 지출한 필요 또는 유익하였던 비용 "
    "나. 피보험자가 제3자로부터 손해의 배상을 받을 수 있는 그 권리를 지키거나 행사하기 위하여 "
    "지출한 필요 또는 유익하였던 비용 "
    "다. 피보험자가 지급한 소송비용, 변호사비용, 중재, 화해 또는 조정에 관한 비용"
)

LIABILITY_HYU_CLAUSE3_TEXT = (
    "제 3 조 (보상하지 않는 손해) "
    "회사는 다음의 사유로 손해배상책임을 부담하게 됨으로써 입은 손해는 보상하여 드리지 않습니다. "
    "1. 피보험자의 직접적인 직무수행으로 인한 배상책임 "
    "2. 피보험자의 직무용으로만 사용되는 동산의 소유, 사용 또는 관리로 인한 배상책임 "
    "3. 피보험자가 소유, 사용 또는 관리하는 부동산으로 인한 배상책임 "
    "4. 피보험자와 세대를 같이하는 친족에 대한 배상책임 "
    "5. 피보험자가 소유, 사용 또는 관리하는 재물의 파손에 대한 배상책임"
)

LIABILITY_HYU_CLAUSE4_TEXT = (
    "제 4 조 (의무보험과의 관계) "
    "회사는 이 약관에 의하여 보상하여야 하는 금액이 의무보험에서 보상하는 금액을 초과할 때에만 "
    "그 초과액을 보상합니다. 이 경우 의무보험은 피보험자가 법률에 의하여 의무적으로 가입하여야 "
    "하는 보험을 말합니다."
)

LIABILITY_HYU_CLAUSE5_TEXT = (
    "제 5 조 (지급한도) "
    "회사는 1회의 보험사고에 대하여 보험증권에 기재된 보상한도액을 한도로 하여 보상합니다."
)

LIABILITY_HYU_CLAUSE6_TEXT = (
    "제 6 조 (손해통지) "
    "계약자 또는 피보험자는 보험사고가 발생하였을 경우 사고가 발생한 때와 곳, 피해자의 주소와 "
    "성명, 사고 상황을 지체없이 서면으로 회사에 알려야 합니다."
)

# ========================================================================
# 5) 항공기납치보장 특별약관 (p.89)
# ========================================================================

HIJACK_CLAUSE1_TEXT = (
    "제 1 조 (보상하는 손해) "
    "회사는 피보험자가 해외여행 중에 피보험자가 승객으로서 탑승한 항공기가 납치(이하 '사고'라 "
    "합니다)됨에 따라 예정목적지에 도착할 수 없게 된 동안에 대하여 매일 70,000원씩 지급합니다. "
    "제 2 항의 항공기의 납치라 함은, 부당한 의도를 가진 폭력, 폭행 또는 폭력이나 폭행의 위협으로서 "
    "항공기를 탈취하거나 지배권을 행사하는 것을 말합니다."
)

HIJACK_CLAUSE2_TEXT = (
    "제 2 조 (보상하는 손해의 범위) "
    "회사는 당해 항공기의 목적지 도착예정시간에서 12 시간이 지난 이후부터 시작되는 24 시간을 "
    "1 일로 보아 20일을 한도로 제1조(보상하는 손해)에 정한 보험금을 지급하여 드립니다. "
    "또한 항공기가 최초의 명백한 사고가 있기 이전에 비행장에서 출발이 지연되었을 경우에는 "
    "제 1 항의 12 시간에 그러한 지연시간을 합한 시간 이후부터의 24시간을 1일로 봅니다."
)

HIJACK_CLAUSE3_TEXT = (
    "제 3 조 (다른 보험과의 관계) "
    "이 특별약관과 유사한 다수의 계약이 동시에 효력을 가질 경우에는 피보험자나 보험수익자 혹은 "
    "그의 법정상속인이 선정하는 하나의 계약에서만 보상하며, 회사는 그 계약 이외의 다른 계약에 대하여는 "
    "이미 납입된 해당보험료를 돌려 드립니다."
)

# ========================================================================
# 6) 해외여행중 여권분실후 재발급비용보장 특별약관 (p.89-90)
# ========================================================================

PASSPORT_LOSS_CLAUSE1_TEXT = (
    "제 1 조 (보상하는 손해) "
    "회사는 피보험자가 해외여행 도중에 여권을 분실하거나 도난당하여 재외공관에 여권분실신고를 "
    "하고 여행증명서(T/C: Travel Certification)를 발급받은 경우 여행증명서 발급비용과 여권 "
    "재발급비용을 보험수익자에게 지급합니다. "
    "제 2 항의 여행증명서 발급비용 및 여권 재발급비용이란 여행증명서 및 여권 재발급에 관한 "
    "수수료로 여권법 제 22 조 제 1 항에서 정한 수수료 및 국제교류기여금을 합한 금액을 말하며 "
    "교통비 및 사진촬영비는 포함되지 않습니다."
)

PASSPORT_LOSS_CLAUSE2_TEXT = (
    "제 2 조 (보상하지 않는 손해) "
    "회사는 다음 중 어느 한가지의 경우에 의하여 보험금 지급사유가 발생한 때에는 보험금을 드리지 "
    "않습니다. "
    "1. 지진, 분화, 해일 또는 이와 비슷한 천재지변 "
    "2. 전쟁, 외국의 무력행사, 혁명, 내란, 사변, 테러, 폭동, 소요, 기타 이들과 유사한 사태 "
    "3. 핵연료 물질(사용이 끝난 연료를 포함합니다. 이하 같습니다) 또는 핵연료 물질에 의하여 "
    "오염된 물질(원자핵분열 생성물을 포함합니다)의 방사성, 폭발성 또는 그밖의 유해한 특성에 의한 사고 "
    "4. 제3호 이외의 방사선을 쬐는 것 또는 방사능 오염 "
    "회사는 아래의 사유로 인하여 생긴 손해는 보상하여 드리지 않습니다. "
    "1. 계약자 또는 피보험자의 고의 "
    "2. 피보험자에게 보험금이 지급되도록 하기 위하여 피보험자와 여행을 같이 하는 친족 또는 "
    "고용인이 고의로 일으킨 손해 "
    "3. 압류, 징발, 몰수, 파괴 등 국가 또는 공공기관의 공권력행사. 단, 화재, 소방, 피난에 필요한 "
    "처리로 된 경우를 제외합니다. "
    "4. 선박승무원 및 항공승무원이 직무상 해외여행 중 여권을 분실 또는 도난당한 경우"
)

PASSPORT_LOSS_CLAUSE3_TEXT = (
    "제 3 조 (보험금 등 청구시 구비서류) "
    "보험수익자 또는 계약자는 보험금을 청구할 때에는 다음 서류를 첨부하여 회사에 제출하여야 합니다. "
    "1. 보험금 청구서 (회사 양식) "
    "2. 여행증명서(T/C : Travel Certification)(귀국 후 여권 재신청 등 사유로 여행증명서의 원본제출이 "
    "불가능한 경우, 해당 지방자치단체가 원본과 동일함을 증명하나 사본 제출) "
    "3. 재발급받은 여권사본 "
    "4. 신분증(주민등록증이나 운전면허증 등 사진이 붙은 정부기관발행 신분증, 본인이 아닌 경우에는 "
    "본인의 인감증명서, 본인서명사실확인서 또는 안전성과 신뢰성이 확보된 전자적 수단을 활용한 "
    "보험수익자 의사표시의 확인방법 포함) "
    "5. 기타 보험수익자가 보험금 등의 수령에 필요하여 제출하는 서류"
)

# ========================================================================
# 7) 해외여행중 중단사고 발생 추가비용보장 특별약관 (p.90)
# ========================================================================

TRIP_INTERRUPTION_CLAUSE1_TEXT = (
    "제 1 조 (보상하는 손해) "
    "회사는 피보험자가 해외여행 중에 다음의 사유로 인하여 피보험자가 부담하는 비용을 이 "
    "특별약관의 보험가입금액을 한도로 보상하여 드립니다. "
    "1. 피보험자 및 여행동반 가족이 상해 또는 질병으로 3일 이상 입원한 경우 "
    "2. 보험기간 내 피보험자의 3촌 이내의 친족 또는 여행동반자의 사망 "
    "3. 지진, 분화, 해일 또는 이와 비슷한 천재지변 "
    "4. 전쟁, 외국의 무력행사, 혁명, 내란, 사변, 테러, 폭동, 소요, 기타 이들과 유사한 사태"
)

TRIP_INTERRUPTION_CLAUSE2_TEXT = (
    "제 2 조 (비용의 범위) "
    "제1조(보상하는 손해)에 따라 회사가 보상하는 비용은 아래와 같습니다. "
    "1. 여행중단 후 귀국으로 인해 피보험자가 기지불한 항공 또는 선박 운임비용을 초과하여 "
    "피보험자에게 추가로 발생하는 항공 또는 선박 운임비용 "
    "2. 여행중단 후 귀국으로 인해 기지불한 숙박비용을 초과하여 피보험자에게 추가로 발생하는 "
    "2박 이내의 숙박비용"
)

# ========================================================================
# 8) 해외여행중 자택 도난손해(가재) 보장 특별약관 (p.91-93)
# ========================================================================

HOME_THEFT_CLAUSE1_TEXT = (
    "제 1 조 (보상의 목적과 손해) "
    "이 특별약관에서 보험의 목적은 피보험자가 주민등록등본상 거주하고 있는 주택 내에 있는 가재를 말합니다. "
    "회사는 피보험자가 해외여행 중에 발생한 도난 또는 소매치기로 인하여 주택 내의 가재에 입은 손해를 "
    "('도난손해'라 합니다)를 이 특별약관에 따라 보상합니다."
)

HOME_THEFT_CLAUSE2_TEXT = (
    "제 2 조 (보상금액) "
    "회사가 이 특별약관에서 지급하는 보험금의 총액은 보험증권에 기재된 보험가입금액을 한도로 합니다."
)

# ========================================================================
# 9) 항공기 및 수하물 지연비용보장 특별약관 (p.93)
# ========================================================================

FLIGHT_DELAY_CLAUSE1_TEXT = (
    "제 1 조 (보상하는 손해) "
    "회사는 피보험자가 탑승한 항공기가 12시간 이상 지연되거나 피보험자가 수탁한 수하물이 "
    "도착지에서 48시간 이상 지연되어 도착한 경우 이로 인하여 입은 손해를 이 특별약관에 따라 "
    "보험가입금액 한도 내에서 보상하여 드립니다."
)

# ========================================================================
# 10) 출국 항공기 지연 손해 보장 특별약관 (p.94)
# ========================================================================

FLIGHT_DELAY_DEPARTURE_CLAUSE1_TEXT = (
    "제 1 조 (보상하는 손해) "
    "회사는 피보험자가 탑승할 항공기가 출국지 공항에서 12시간 이상 지연되거나 결항되어 "
    "피보험자가 출국할 수 없거나 동일 항공사 또는 다른 항공사로 변경되어 운항하게 됨으로써 "
    "피보험자가 추가적으로 부담한 비용 손해를 이 특별약관에서 정한 바에 따라 보험가입금액 "
    "한도 내에서 보상하여 드립니다."
)


def _get_or_create_clause(db, *, policy_version_id, coverage_id, clause_type, article_no, text, page_ref, default_color):
    """Idempotent clause creation based on exact text match."""
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
    """Idempotent map creation."""
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
            print("현대해상이 아직 시딩되지 않았습니다. seed_hyundai를 먼저 실행하세요.")
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
        required = [
            "INJ_OVERSEAS_TREATMENT", "ILL_OVERSEAS_TREATMENT", "SPC_WAR_TERROR", "ILL_DEATH_DISABILITY", "LIA_PERSONAL",
            "LIA_PROPERTY", "TRV_HIJACK", "PROP_PASSPORT_LOSS", "CHG_INTERRUPTION",
            "PROP_NEW_1", "TRV_FLIGHT_DELAY"
        ]
        missing = [c for c in required if c not in types]
        if missing:
            print(f"incident_type 사전에 없는 코드: {missing}. seed_incident_types를 먼저 실행하세요.")
            return

        # Create or get CoverageStd for each coverage
        std_non_covered_med = get_or_create_coverage_std(db, "NON_COVERED_MED", "비급여 실손의료비", "질병", False)
        std_war_risk = get_or_create_coverage_std(db, "WAR_RISK", "전쟁위험보장", "특수", False)
        std_ill_death = get_or_create_coverage_std(db, "ILL_DEATH", "질병사망·고도후유장해", "질병", False)
        std_liability = get_or_create_coverage_std(db, "LIABILITY", "배상책임", "배상책임", False)
        std_hijack = get_or_create_coverage_std(db, "HIJACK", "항공기납치보장", "운송", False)
        std_passport_loss = get_or_create_coverage_std(db, "PASSPORT_LOSS", "여권분실 재발급비용", "여행변경", False)
        std_trip_interruption = get_or_create_coverage_std(db, "TRIP_INTERRUPTION", "여행중단 추가비용", "여행변경", False)
        std_home_theft = get_or_create_coverage_std(db, "HOME_THEFT", "자택 도난손해(가재)", "휴대품", False)
        std_flight_delay = get_or_create_coverage_std(db, "FLIGHT_DELAY", "항공기·수하물 지연비용", "운송", False)

        clause_created = map_created = coverage_created = 0

        # ==============================================================
        # 1) 해외여행 비급여 실손의료비보장 특별약관
        # ==============================================================
        cov_non_covered_med = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "해외여행 비급여 실손의료비보장 특별약관",
            )
            .first()
        )
        if not cov_non_covered_med:
            cov_non_covered_med = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_non_covered_med.coverage_std_id,
                raw_name="해외여행 비급여 실손의료비보장 특별약관",
                definition=NON_COVERED_MED_CLAUSE2_TEXT,
                limit_amount="보험증권 기재 한도액",
                deductible=None,
                waiting_condition=None,
            )
            db.add(cov_non_covered_med)
            db.flush()
            coverage_created += 1

        c1, created1 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_non_covered_med.coverage_id,
            clause_type="공통", article_no="[해외여행 비급여 실손의료비보장] 제1조(용어정의)",
            text=NON_COVERED_MED_CLAUSE1_TEXT, page_ref="p.68", default_color="회색",
        )
        c2, created2 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_non_covered_med.coverage_id,
            clause_type="보장정의", article_no="[해외여행 비급여 실손의료비보장] 제2조(보장종목별 보상내용)",
            text=NON_COVERED_MED_CLAUSE2_TEXT, page_ref="p.68-69", default_color="파랑",
        )
        c3, created3 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_non_covered_med.coverage_id,
            clause_type="면책", article_no="[해외여행 비급여 실손의료비보장] 제3조(보상하지 않는 사항)",
            text=NON_COVERED_MED_CLAUSE3_TEXT, page_ref="p.74-75", default_color="빨강",
        )
        clause_created += sum([created1, created2, created3])

        non_covered_inj = types["INJ_OVERSEAS_TREATMENT"]
        non_covered_ill = types["ILL_OVERSEAS_TREATMENT"]
        map_created += sum([
            _get_or_create_map(db, clause_id=c2.clause_id, type_id=non_covered_inj.type_id, relevance="직접", confidence=1.0),
            _get_or_create_map(db, clause_id=c2.clause_id, type_id=non_covered_ill.type_id, relevance="직접", confidence=1.0),
            _get_or_create_map(db, clause_id=c3.clause_id, type_id=non_covered_inj.type_id, relevance="면책", confidence=0.95),
            _get_or_create_map(db, clause_id=c3.clause_id, type_id=non_covered_ill.type_id, relevance="면책", confidence=0.95),
        ])

        # ==============================================================
        # 2) 전쟁위험보장 특별약관
        # ==============================================================
        cov_war_risk = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "전쟁위험보장 특별약관",
            )
            .first()
        )
        if not cov_war_risk:
            cov_war_risk = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_war_risk.coverage_std_id,
                raw_name="전쟁위험보장 특별약관",
                definition=WAR_RISK_CLAUSE1_TEXT,
                limit_amount="기본 상해사망·후유장해 보험금액 동일",
                deductible=None,
                waiting_condition=None,
            )
            db.add(cov_war_risk)
            db.flush()
            coverage_created += 1

        w1, created_w1 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_war_risk.coverage_id,
            clause_type="보장정의", article_no="[전쟁위험보장] 제1조(보상하는 손해)",
            text=WAR_RISK_CLAUSE1_TEXT, page_ref="p.80", default_color="파랑",
        )
        w2, created_w2 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_war_risk.coverage_id,
            clause_type="조건", article_no="[전쟁위험보장] 제2조(통지 및 대리)",
            text=WAR_RISK_CLAUSE2_TEXT, page_ref="p.81", default_color="노랑",
        )
        clause_created += sum([created_w1, created_w2])

        war_risk_type = types["SPC_WAR_TERROR"]
        map_created += _get_or_create_map(db, clause_id=w1.clause_id, type_id=war_risk_type.type_id, relevance="직접", confidence=1.0)

        # ==============================================================
        # 3) 질병사망 및 질병 80%이상 고도후유장해보장 특별약관
        # ==============================================================
        cov_ill_death = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "질병사망 및 질병 80%이상 고도후유장해보장 특별약관",
            )
            .first()
        )
        if not cov_ill_death:
            cov_ill_death = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_ill_death.coverage_std_id,
                raw_name="질병사망 및 질병 80%이상 고도후유장해보장 특별약관",
                definition=ILL_DEATH_HYU_CLAUSE1_TEXT,
                limit_amount="보험증권 기재 보험가입금액",
                deductible=None,
                waiting_condition="장해지급률 80% 이상(장해분류표 기준)",
            )
            db.add(cov_ill_death)
            db.flush()
            coverage_created += 1

        i1, created_i1 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_ill_death.coverage_id,
            clause_type="보장정의", article_no="[질병사망·고도후유장해] 제1조(보험금의 종류 및 지급사유)",
            text=ILL_DEATH_HYU_CLAUSE1_TEXT, page_ref="p.81", default_color="파랑",
        )
        clause_created += created_i1

        ill_death_type = types["ILL_DEATH_DISABILITY"]
        map_created += _get_or_create_map(db, clause_id=i1.clause_id, type_id=ill_death_type.type_id, relevance="직접", confidence=1.0)

        # ==============================================================
        # 4) 배상책임보장 특별약관
        # ==============================================================
        cov_liability = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "배상책임보장 특별약관",
            )
            .first()
        )
        if not cov_liability:
            cov_liability = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_liability.coverage_std_id,
                raw_name="배상책임보장 특별약관",
                definition=LIABILITY_HYU_CLAUSE1_TEXT,
                limit_amount="보험증권 기재 보상한도액",
                deductible=None,
                waiting_condition=None,
            )
            db.add(cov_liability)
            db.flush()
            coverage_created += 1

        l1, created_l1 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_liability.coverage_id,
            clause_type="보장정의", article_no="[배상책임보장] 제1조(보상하는 손해)",
            text=LIABILITY_HYU_CLAUSE1_TEXT, page_ref="p.82", default_color="파랑",
        )
        l2, created_l2 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_liability.coverage_id,
            clause_type="보장정의", article_no="[배상책임보장] 제2조(보상하는 손해의 범위)",
            text=LIABILITY_HYU_CLAUSE2_TEXT, page_ref="p.82-83", default_color="파랑",
        )
        l3, created_l3 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_liability.coverage_id,
            clause_type="면책", article_no="[배상책임보장] 제3조(보상하지 않는 손해)",
            text=LIABILITY_HYU_CLAUSE3_TEXT, page_ref="p.83", default_color="빨강",
        )
        l4, created_l4 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_liability.coverage_id,
            clause_type="조건", article_no="[배상책임보장] 제4조(의무보험과의 관계)",
            text=LIABILITY_HYU_CLAUSE4_TEXT, page_ref="p.84", default_color="노랑",
        )
        l5, created_l5 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_liability.coverage_id,
            clause_type="제한", article_no="[배상책임보장] 제5조(지급한도)",
            text=LIABILITY_HYU_CLAUSE5_TEXT, page_ref="p.84", default_color="초록",
        )
        l6, created_l6 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_liability.coverage_id,
            clause_type="조건", article_no="[배상책임보장] 제6조(손해통지)",
            text=LIABILITY_HYU_CLAUSE6_TEXT, page_ref="p.84-85", default_color="노랑",
        )
        clause_created += sum([created_l1, created_l2, created_l3, created_l4, created_l5, created_l6])

        lia_personal = types["LIA_PERSONAL"]
        lia_property = types["LIA_PROPERTY"]
        map_created += sum([
            _get_or_create_map(db, clause_id=l1.clause_id, type_id=lia_personal.type_id, relevance="직접", confidence=1.0),
            _get_or_create_map(db, clause_id=l1.clause_id, type_id=lia_property.type_id, relevance="직접", confidence=1.0),
            _get_or_create_map(db, clause_id=l2.clause_id, type_id=lia_personal.type_id, relevance="직접", confidence=0.95),
            _get_or_create_map(db, clause_id=l2.clause_id, type_id=lia_property.type_id, relevance="직접", confidence=0.95),
            _get_or_create_map(db, clause_id=l3.clause_id, type_id=lia_personal.type_id, relevance="면책", confidence=0.9),
            _get_or_create_map(db, clause_id=l3.clause_id, type_id=lia_property.type_id, relevance="면책", confidence=0.9),
        ])

        # ==============================================================
        # 5) 항공기납치보장 특별약관
        # ==============================================================
        cov_hijack = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "항공기납치보장 특별약관",
            )
            .first()
        )
        if not cov_hijack:
            cov_hijack = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_hijack.coverage_std_id,
                raw_name="항공기납치보장 특별약관",
                definition=HIJACK_CLAUSE1_TEXT,
                limit_amount="일당 70,000원 x 20일 = 1,400,000원",
                deductible=None,
                waiting_condition="목적지 도착예정시간부터 12시간 경과 후 개시",
            )
            db.add(cov_hijack)
            db.flush()
            coverage_created += 1

        h1, created_h1 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_hijack.coverage_id,
            clause_type="보장정의", article_no="[항공기납치보장] 제1조(보상하는 손해)",
            text=HIJACK_CLAUSE1_TEXT, page_ref="p.89", default_color="파랑",
        )
        h2, created_h2 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_hijack.coverage_id,
            clause_type="제한", article_no="[항공기납치보장] 제2조(보상하는 손해의 범위)",
            text=HIJACK_CLAUSE2_TEXT, page_ref="p.89", default_color="초록",
        )
        h3, created_h3 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_hijack.coverage_id,
            clause_type="조건", article_no="[항공기납치보장] 제3조(다른 보험과의 관계)",
            text=HIJACK_CLAUSE3_TEXT, page_ref="p.89", default_color="노랑",
        )
        clause_created += sum([created_h1, created_h2, created_h3])

        hijack_type = types["TRV_HIJACK"]
        map_created += _get_or_create_map(db, clause_id=h1.clause_id, type_id=hijack_type.type_id, relevance="직접", confidence=1.0)

        # ==============================================================
        # 6) 해외여행중 여권분실후 재발급비용보장 특별약관
        # ==============================================================
        cov_passport = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "해외여행중 여권분실후 재발급비용보장 특별약관",
            )
            .first()
        )
        if not cov_passport:
            cov_passport = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_passport_loss.coverage_std_id,
                raw_name="해외여행중 여권분실후 재발급비용보장 특별약관",
                definition=PASSPORT_LOSS_CLAUSE1_TEXT,
                limit_amount="여행증명서 및 여권 재발급 수수료 + 국제교류기여금",
                deductible=None,
                waiting_condition="재외공관에 분실신고 후 여행증명서(T/C) 발급 필수",
            )
            db.add(cov_passport)
            db.flush()
            coverage_created += 1

        p1, created_p1 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_passport.coverage_id,
            clause_type="보장정의", article_no="[여권분실] 제1조(보상하는 손해)",
            text=PASSPORT_LOSS_CLAUSE1_TEXT, page_ref="p.89", default_color="파랑",
        )
        p2, created_p2 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_passport.coverage_id,
            clause_type="면책", article_no="[여권분실] 제2조(보상하지 않는 손해)",
            text=PASSPORT_LOSS_CLAUSE2_TEXT, page_ref="p.89-90", default_color="빨강",
        )
        p3, created_p3 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_passport.coverage_id,
            clause_type="서류", article_no="[여권분실] 제3조(보험금 등 청구시 구비서류)",
            text=PASSPORT_LOSS_CLAUSE3_TEXT, page_ref="p.90", default_color="회색",
        )
        clause_created += sum([created_p1, created_p2, created_p3])

        passport_type = types["PROP_PASSPORT_LOSS"]
        map_created += _get_or_create_map(db, clause_id=p1.clause_id, type_id=passport_type.type_id, relevance="직접", confidence=1.0)

        # ==============================================================
        # 7) 해외여행중 중단사고 발생 추가비용보장 특별약관
        # ==============================================================
        cov_trip_int = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "해외여행중 중단사고 발생 추가비용보장 특별약관",
            )
            .first()
        )
        if not cov_trip_int:
            cov_trip_int = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_trip_interruption.coverage_std_id,
                raw_name="해외여행중 중단사고 발생 추가비용보장 특별약관",
                definition=TRIP_INTERRUPTION_CLAUSE1_TEXT,
                limit_amount="보험증권 기재 보험가입금액",
                deductible=None,
                waiting_condition="입원 3일 이상 또는 3촌 이내 친족/여행동반자 사망 시",
            )
            db.add(cov_trip_int)
            db.flush()
            coverage_created += 1

        t1, created_t1 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_trip_int.coverage_id,
            clause_type="보장정의", article_no="[여행중단] 제1조(보상하는 손해)",
            text=TRIP_INTERRUPTION_CLAUSE1_TEXT, page_ref="p.90", default_color="파랑",
        )
        t2, created_t2 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_trip_int.coverage_id,
            clause_type="보장정의", article_no="[여행중단] 제2조(비용의 범위)",
            text=TRIP_INTERRUPTION_CLAUSE2_TEXT, page_ref="p.90", default_color="파랑",
        )
        clause_created += sum([created_t1, created_t2])

        trip_int_type = types["CHG_INTERRUPTION"]
        map_created += sum([
            _get_or_create_map(db, clause_id=t1.clause_id, type_id=trip_int_type.type_id, relevance="직접", confidence=1.0),
            _get_or_create_map(db, clause_id=t2.clause_id, type_id=trip_int_type.type_id, relevance="직접", confidence=0.95),
        ])

        # ==============================================================
        # 8) 해외여행중 자택 도난손해(가재) 보장 특별약관
        # ==============================================================
        cov_home_theft = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "해외여행중 자택 도난손해(가재) 보장 특별약관",
            )
            .first()
        )
        if not cov_home_theft:
            cov_home_theft = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_home_theft.coverage_std_id,
                raw_name="해외여행중 자택 도난손해(가재) 보장 특별약관",
                definition=HOME_THEFT_CLAUSE1_TEXT,
                limit_amount="보험증권 기재 보험가입금액",
                deductible=None,
                waiting_condition="주민등록등본상 거주 주택 내 가재만 보장",
            )
            db.add(cov_home_theft)
            db.flush()
            coverage_created += 1

        ht1, created_ht1 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_home_theft.coverage_id,
            clause_type="보장정의", article_no="[자택도난] 제1조(보상의 목적과 손해)",
            text=HOME_THEFT_CLAUSE1_TEXT, page_ref="p.91", default_color="파랑",
        )
        ht2, created_ht2 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_home_theft.coverage_id,
            clause_type="제한", article_no="[자택도난] 제2조(보상금액)",
            text=HOME_THEFT_CLAUSE2_TEXT, page_ref="p.92", default_color="초록",
        )
        clause_created += sum([created_ht1, created_ht2])

        home_theft_type = types["PROP_NEW_1"]  # 삼성화재 딥다이브에서 만든 "자택 도난손해(가재)" 재사용
        map_created += _get_or_create_map(db, clause_id=ht1.clause_id, type_id=home_theft_type.type_id, relevance="직접", confidence=1.0)

        # ==============================================================
        # 9) 항공기 및 수하물 지연비용보장 특별약관
        # ==============================================================
        cov_flight_delay = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "항공기 및 수하물 지연비용보장 특별약관",
            )
            .first()
        )
        if not cov_flight_delay:
            cov_flight_delay = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_flight_delay.coverage_std_id,
                raw_name="항공기 및 수하물 지연비용보장 특별약관",
                definition=FLIGHT_DELAY_CLAUSE1_TEXT,
                limit_amount="보험증권 기재 보험가입금액",
                deductible=None,
                waiting_condition="항공기 12시간 이상 지연 또는 수하물 48시간 이상 지연",
            )
            db.add(cov_flight_delay)
            db.flush()
            coverage_created += 1

        fd1, created_fd1 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_flight_delay.coverage_id,
            clause_type="보장정의", article_no="[항공기지연] 제1조(보상하는 손해)",
            text=FLIGHT_DELAY_CLAUSE1_TEXT, page_ref="p.93", default_color="파랑",
        )
        clause_created += created_fd1

        flight_delay_type = types["TRV_FLIGHT_DELAY"]
        map_created += _get_or_create_map(db, clause_id=fd1.clause_id, type_id=flight_delay_type.type_id, relevance="직접", confidence=1.0)

        # ==============================================================
        # 10) 출국 항공기 지연 손해 보장 특별약관
        # ==============================================================
        # 같은 FLIGHT_DELAY 코드이나 출국 시점만 다르므로, raw_name으로 구분
        cov_flight_delay_dep = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "출국 항공기 지연 손해 보장 특별약관",
            )
            .first()
        )
        if not cov_flight_delay_dep:
            cov_flight_delay_dep = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_flight_delay.coverage_std_id,
                raw_name="출국 항공기 지연 손해 보장 특별약관",
                definition=FLIGHT_DELAY_DEPARTURE_CLAUSE1_TEXT,
                limit_amount="보험증권 기재 보험가입금액",
                deductible=None,
                waiting_condition="출국지 공항에서 12시간 이상 지연 또는 결항",
            )
            db.add(cov_flight_delay_dep)
            db.flush()
            coverage_created += 1

        fdd1, created_fdd1 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_flight_delay_dep.coverage_id,
            clause_type="보장정의", article_no="[출국항공기지연] 제1조(보상하는 손해)",
            text=FLIGHT_DELAY_DEPARTURE_CLAUSE1_TEXT, page_ref="p.94", default_color="파랑",
        )
        clause_created += created_fdd1

        map_created += _get_or_create_map(db, clause_id=fdd1.clause_id, type_id=flight_delay_type.type_id, relevance="직접", confidence=1.0)

        db.commit()
        print(f"현대해상 청크2 완료: Coverage {coverage_created}개, Clause {clause_created}개, Map {map_created}개 생성")

    finally:
        db.close()


if __name__ == "__main__":
    run()
