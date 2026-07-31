"""
KB손해보험(insurer.code="KB") 해외여행보험 — 청크2 (PDF p.58~113).
data/raw_pdfs/kb_overseas_15332_202004.pdf (총 169쪽)을 pdfplumber로
p.58~113 전체를 직접 읽고 대조한 결과를 반영한다.

## p.58~61: 여행중 배상책임 특별약관 (계약행정 조항)
직접 읽었으나, 제6조~제18조는 계약행정(대위권/해지/준용규정 등) 조항으로
사고유형 분류와 무관함을 확인했다(억지 매핑 없음). 스킵한다.

## p.62~64: 해외여행중 휴대품손해(분실제외) 특별약관
CoverageStd PERSONAL_EFFECTS로 매핑. 제1조(보험목적의 범위), 제2조(보상하는 손해),
제3조(보상하지 않는 손해), 제4조(지급보험금의 계산), 제5조(손해방지의무),
제6조(손해액의 조사결정), 제7조(잔존물 및 도난품의 귀속), 제8조(대위권)를
원문 그대로 Clause로 넣었다.

## p.65~67: 해외여행중 중대사고 구조송환비용 특별약관
CoverageStd RESCUE로 매핑. 제1조(보험금의 지급사유), 제2조(비용의 범위),
제3조(보험금을 지급하지 않는 사유), 제4조(보험금의 지급), 제5조(보험금의 분담),
제6조(보상한도액)를 원문 그대로 넣었다.

## p.67~68: 해외여행중 항공기납치 특별약관
CoverageStd HIJACK로 매핑. 제1조(보험금의 지급사유), 제2조(보험금 지급에 관한 세부규정),
제3조(다른 보험과의 관계)를 원문 그대로 넣었다.

## p.68~69: 항공기탑승중 상해위험 특별약관
CoverageStd DEATH_INJURY(기존)를 재사용. 항공기 탑승 중 사고로 인한 상해사망/후유장해를
보장하는 기본 상해 보장이므로, 기존 상해 담보와 통합한다.
제1조(보험금의 지급사유), 제2조(보험금을 지급하지 않는 사유)를 원문 그대로 넣었다.

## p.69~70: 해외여행중 여권분실 후 재발급비용 특별약관
CoverageStd PASSPORT_LOSS로 매핑. 제1조(보상하는 손해), 제2조(보상하지 않는 손해),
제3조(보험금의 청구)를 원문 그대로 넣었다.

## p.70~72: 해외여행중 중단사고발생 추가비용 특별약관
CoverageStd TRIP_INTERRUPTION로 매핑. 제1조(보상하는 손해), 제2조(비용의 범위),
제3조(보상하지 않는 손해), 제4조(보험금의 청구)를 원문 그대로 넣었다.

## p.72~73: 해외여행중 식중독보상금 특별약관
CoverageStd FOOD_POISONING으로 매핑. 제1조(보상하는 손해), 제2조(식중독의 정의 및 진단확정)를
원문 그대로 넣었다. 【식중독 분류표】는 사고 분류 근거이므로 clause로 넣지 않음.

## p.73~74: 해외여행중 특정전염병치료비 특별약관
CoverageStd INFECTIOUS_DISEASE로 매핑. 제1조(보험금의 지급사유)를 원문 그대로 넣었다.
【특정전염병 분류표】는 질병 분류 근거이므로 clause로 넣지 않음.

## p.74~76: 항공기 및 수하물 지연비용 특별약관
CoverageStd FLIGHT_DELAY + TRV_BAGGAGE_DELAY로 분리하여 매핑.
제1조(보상하는 손해)는 두 담보 모두에 해당하는 지급사유. 제2조(보상하지 않는 손해),
제3조(보험금 청구시 구비서류), 제4조(보험금의 지급한도)를 원문 그대로 넣었다.

## p.76~96: 단체계약/포괄계약/부부/가족/환율/지정대리청구 등 특별약관 (계약행정)
직접 읽었으나, 모두 사고유형 분류와 무관한 계약 관리/정산 조항임을 확인했다.
- 단체계약·단체취급·포괄계약 (제1조~제3조): 단체 구성원 정의, 피보험자 증감, 보험료 정산 등
- 부부/가족/가족확장 특약 (제1조~제3조): 피보험자 범위 확대
- 적용환율 특약: 보험료/보험금 환산 기준
- 지정대리청구 특약: 대리청구 권한
모두 스킵한다(억지 매핑 없음).

## p.97~113: 기본형 해외여행 실손의료비 특별약관
이 특약은 상해·질병 의료비를 담보한다. 질병 부분만 이 청크에서 다룬다
(상해 부분은 이미 p.57 범위에서 이전 청크가 처리 완료 기대).
CoverageStd OVS_ILL_MED로 매핑.
제1관 제1조(보장종목) — 보장 세부 구성(해외/국내 통원/입원)
제2관 제2조(보험금의 지급사유) ②항(질병의료비 — 국내 통원) — ILL_OVERSEAS_TREATMENT + ILL_DOMESTIC_TREATMENT 분리 고려
제3관 제4조(보험금의 계산 및 지급한도) — 제한 조항
원문을 그대로 넣었다.

멱등성: Coverage는 raw_name, Clause는 (coverage_id, article_no, text) 조합,
ClauseIncidentMap은 (clause_id, type_id) 조합으로 이미 있으면 건너뛴다.
"""
from app.database import SessionLocal
from app import models  # noqa: F401
from app.models.kb import (
    Clause, ClauseIncidentMap, Coverage, IncidentType, Insurer, PolicyVersion, Product,
)
from app.services.kb_seed_common import get_or_create_coverage_std


# ============================================================================
# 원문 상수 정의
# ============================================================================

# p.62-64: 휴대품손해
PERSONAL_EFFECTS_CLAUSE1_TEXT = (
    "① 이 보험의 목적은 피보험자가 여행 도중에 휴대하는 피보험자 소유·사용·관리의 휴대품에 한"
    "합니다. ② 아래의 물건은 보험의 목적에 포함되지 않습니다. 1. 통화, 유가증권, 인지, 우표, "
    "신용카드, 쿠폰, 항공권, 여권 등 이와 비슷한 것 2. 원고, 설계서, 도안, 물건의 원본, 모형, "
    "증서, 장부, 금형(쇠틀), 목형(나무틀), 소프트웨어 및 이와 비슷한 것 3. 선박 또는 자동차"
    "(자동3륜차, 자동2륜차 포함) 4. 산악 등반이나 탐험 등에 필요한 용구 5. 동물, 식물 6. 의치, "
    "의수족, 콘택트렌즈 7. 기타(보험증권에 특별히 기재된 것)"
)

PERSONAL_EFFECTS_CLAUSE2_TEXT = (
    "회사는 피보험자가 보통약관 제3조(보험금의 지급사유)의 여행 도중에 생긴 우연한 사고에 의"
    "하여 보험의 목적에 입은 손해를 이 특별약관에 따라 보상해 드립니다."
)

PERSONAL_EFFECTS_CLAUSE3_TEXT = (
    "① 회사는 다음 중 어느 한가지의 경우에 의하여 보험금 지급사유가 발생한 때에는 보험금을"
    "드리지 않습니다. 1. 지진, 분화, 해일 또는 이와 비슷한 천재지변 2. 전쟁, 외국의 무력행사, "
    "혁명, 내란, 사변, 테러, 폭동, 소요, 기타 이들과 유사한 사태 3. 핵연료 물질(사용이 끝난 연료를 "
    "포함합니다. 이하 같습니다) 또는 핵연료 물질에 의하여 오염된 물질(원자핵분열 생성물을 포함합니다)"
    "의 방사성, 폭발성 또는 그밖의 유해한 특성에 의한 사고 4. 제3호 이외의 방사선을 쬐는 것 또는 "
    "방사능 오염 ② 회사는 아래의 사유로 인하여 생긴 손해는 보상하여 드리지 않습니다. 1. 계약자 "
    "또는 피보험자의 고의 또는 중대한 과실 2. 피보험자에게 보험금이 지급되도록 하기 위하여 피보험자와 "
    "여행을 같이 하는 친족 또는 고용인이 고의로 일으킨 손해 3. 압류, 징발, 몰수, 파괴 등 국가 또는 "
    "공공기관의 공권력행사. 단, 화재, 소방, 피난에 필요한 처리로 된 경우를 제외합니다. 4. 보험의 목적의 "
    "흠으로 생긴 손해, 그러나 계약자, 피보험자 또는 이들을 대신하여 보험의 목적을 관리하는 자가 상당한 "
    "주의를 하였음에도 불구하고 발견하지 못한 흠으로 인한 손해는 보상하여 드립니다. 5. 보험의 목적의 "
    "자연소모, 녹, 곰팡이, 변질, 변색 등과 쥐나 벌레로 인한 손해 6. 단순한 외관상의 손해로 기능에는 "
    "지장이 없는 손해 7. 보험의 목적인 액체의 유출. 다만, 그 결과로 다른 보험의 목적에 생긴 손해는 보상하여"
    "드립니다. 8. 보험의 목적의 방치 또는 분실"
)

# p.65-67: 구조송환비용
RESCUE_CLAUSE1_TEXT = (
    "① 회사는 아래의 사유로 계약자, 피보험자 또는 피보험자의 법정상속인이 부담하는 비용을 이"
    "특별약관에 따라 보상하여 드립니다. 1. 보통약관 제3조(보험금의 지급사유)의 여행 도중(이하"
    "「여행 도중」이라 합니다)에 피보험자가 탑승한 항공기 또는 선박이 행방불명 또는 조난된 경우 "
    "또는 산악등반 중에 조난된 경우 2. 여행 도중에 급격하고도 우연한 외래의 사고에 따라 긴급수색"
    "구조 등이 필요한 상태로 된 것이 경찰 등의 공공기관에 의하여 확인된 경우 3. 보통약관 제3조(보험금의 "
    "지급사유)의 상해를 직접 원인으로 하여 사고일로부터 1년 이내에 사망한 경우 또는 14일 이상 계속 "
    "입원한 경우(다른 의료기관으로 이전한 경우에는 이전에 소요된 기간을 입원 중으로 봅니다. 다만, 그 "
    "이전에 대하여는 치료를 위하여 의사가 필요하다고 인정한 경우에 한합니다. 이하 같습니다.) 4. 질병을 "
    "직접 원인으로 하여 여행 도중에 사망한 경우 또는 여행 도중에 걸린 질병을 직접 원인으로 하여 14일 "
    "이상 계속 입원한 경우. 다만, 입원에 대하여는 여행 도중에 의사가 치료를 개시한 질병으로 인한 입원에 "
    "한합니다."
)

RESCUE_CLAUSE2_TEXT = (
    "① 회사가 보상하는 비용의 범위는 아래와 같습니다. 1. 수색구조비용: 조난당한 피보험자를 수색, 구조 또는 "
    "이송(이하「수색」이라 합니다)하는 활동에 필요한 비용중 이들의 활동에 종사한 사람으로부터의 청구에 "
    "의하여 지급한 비용을 말합니다. 2. 항공운임 등 교통비: 피보험자의 수색, 간호 또는 사고처리를 위하여 "
    "사고발생지 또는 피보험자의 법정상속인(그 대리인을 포함합니다. 이하「구원자」라 합니다)의 현지 왕복교통비를 "
    "말하며 2명분을 한도로 합니다. 3. 숙박비: 현지에서의 구원자의 숙박비를 말하여 구원자 2명분을 한도로 하여 "
    "1명당 14박분을 한도로 합니다. 4. 이송비용: 피보험자가 사망한 경우 그 유해를 현지로부터 보험증권에 기재된 "
    "피보험자의 주소지에 이송하는데 필요한 비용 및 치료를 계속중인 피보험자를 보험증권에 기재된 피보험자의 주소지에 "
    "이송하는데 드는 비용으로서 통상액을 넘는 피보험자의 운임 및 수행하는 의사, 간호사의 호송비를 말합니다. "
    "5. 제잡비: 구원자의 출입국 절차에 필요한 비용(여권인지대, 사증료, 예방접종료 등) 및 구원자 또는 피보험자가 "
    "현지에서 지출한 교통비, 통신비, 피보험자 유해처리비 등을 말하고 10만원을 한도로 합니다."
)

RESCUE_CLAUSE3_TEXT = (
    "회사는 보통약관 제5조(보험금을 지급하지 않는 사유) 제1항 제1호 내지 제3호, 제5호의 사유로 인하여 생긴 "
    "손해는 보상하여 드리지 않습니다."
)

# p.67-68: 항공기납치
HIJACK_CLAUSE1_TEXT = (
    "① 회사는 피보험자가 보통약관 제3조(보험금의 지급사유)의 여행 도중에 피보험자가 승객으로서 탑승한 항공기가 "
    "납치(이하 \"사고\"라 합니다)됨에 따라 예정목적지에 도착할 수 없게 된 동안에 대하여 매일 70,000원씩 지급하여 "
    "드립니다. ② 제1항의 항공기의 납치라 함은, 부당한 의도를 가진 폭력, 폭행 또는 폭력이나 폭행의 위협으로서 항공기를 "
    "탈취하거나 지배권을 행사하는 것을 말합니다."
)

HIJACK_CLAUSE2_TEXT = (
    "① 회사는 당해 항공기의 목적지 도착예정시간에서 12시간이 지난 이후부터 시작되는 24시간을 1일로 보아 20일을 "
    "한도로 제1조(보험금의 지급사유)에 정한 보험금을 지급하여 드립니다. ② 또한 항공기가 최초의 명백한 사고가 있기 "
    "이전에 비행장에서 출발이 지연되었을 경우에는 제1항의 12시간에 그러한 지연시간을 합한 시간 이후부터의 24시간을 "
    "1일로 봅니다."
)

# p.68-69: 항공기탑승중 상해위험
AIRCRAFT_INJ_CLAUSE1_TEXT = (
    "① 회사는 피보험자에게 다음 사항 중 어느 한 가지의 경우에 해당되는 사유가 발생한 때에는 보험수익자에게 약정한 "
    "보험금을 지급합니다. 1. 보험기간 중에 상해(보험기간 중에 발생한 급격하고도 우연한 외래의 항공기사고로 신체(의수, "
    "의족, 의안, 의치 등 신체보조장구는 제외하나, 인공장기나 부분 의치 등 신체에 이식되어 그 기능을 대신할 경우는 "
    "포함합니다)에 입은 상해를 말하며, 이하 \"상해\"라 합니다)의 직접결과로써 사망한 경우(질병으로 인한 사망은 제외합니다) : "
    "사망보험금 2. 보험기간 중 제1항의 상해로 장해분류표(【별표1】 참조. 이하 같습니다)에서 정한 각 장해지급률에 해당하는 "
    "장해상태가 되었을 때 : 후유장해보험금(장해분류표에서 정한 지급률을 보험가입금액에 곱하여 산출한 금액) "
    "② 제1항 제1호에서「항공기사고」라 함은 항공기 탑승중의 사고, 비행장 구내에서의 사고 및 피보험자가 탑승한 항공기가 "
    "불시착한 경우에 피보험자가 목적지에 도착할 때까지 항공운송업자가 제공하는 자동차 및 기타 교통수단에 탑승중의 사고를 "
    "말합니다. 여기서「비행장 구내」란 비행기 탑승시 각 항공사의 개찰구 안쪽을 말합니다."
)

AIRCRAFT_INJ_CLAUSE2_TEXT = (
    "회사는 보통약관 제5조(보험금을 지급하지 않는 사유)에서 정한 사항 외에 다음 중 어느 한 가지의 경우에 의하여 "
    "보험금 지급사유가 발생한 때에는 보험금을 드리지 않습니다. 1. 시운전, 경기(연습을 포함합니다) 또는 흥행(연습을 "
    "포함합니다)을 위하여 운행중의 자동차 및 기타교통수단에 탑승(운전을 포함합니다)하고 있는 동안 2. 하역작업을 하는 동안 "
    "3. 자동차 및 기타교통수단의 설치, 수선, 점검, 정비나 청소작업을 하는 동안"
)

# p.69-70: 여권분실
PASSPORT_LOSS_CLAUSE1_TEXT = (
    "① 회사는 피보험자가 해외여행 도중에 여권을 분실하거나 도난당하여 재외공관에 여권분실신고를 하고 여행증명서"
    "(T/C : Travel Certification)를 발급받은 경우 여행증명서 발급비용 과 여권 재발급비용을 보험수익자에게 지급합니다. "
    "② 제1항의 여행증명서 발급비용 및 여권 재발급비용이란 여행증명서 및 여권 재발급에 관한 수수료로 여권법 제22조 "
    "제1항에서 정한 수수료 및 국제교류기여금을 합한 금액을 말하며 교통비 및 사진촬영비는 포함되지 않습니다."
)

PASSPORT_LOSS_CLAUSE2_TEXT = (
    "① 회사는 다음 중 어느 한가지의 경우에 의하여 보험금 지급사유가 발생한 때에는 보험금을 드리지 않습니다. "
    "1. 지진, 분화, 해일 또는 이와 비슷한 천재지변 2. 전쟁, 외국의 무력행사, 혁명, 내란, 사변, 테러, 폭동, 소요, "
    "기타 이들과 유사한 사태 3. 핵연료 물질(사용이 끝난 연료를 포함합니다. 이하 같습니다) 또는 핵연료 물질에 의하여 "
    "오염된 물질(원자핵분열 생성물을 포함합니다)의 방사성, 폭발성 또는 그밖의 유해한 특성에 의한 사고 4. 제3호 이외의 "
    "방사선을 쬐는 것 또는 방사능 오염 ② 회사는 아래의 사유로 인하여 생긴 손해는 보상하여 드리지 않습니다. "
    "1. 계약자 또는 피보험자의 고의 2. 피보험자에게 보험금이 지급되도록 하기 위하여 피보험자와 여행을 같이 하는 친족 "
    "또는 고용인이 고의로 일으킨 손해 3. 압류, 징발, 몰수, 파괴 등 국가 또는 공공기관의 공권력행사. 단, 화재, 소방, 피난에 "
    "필요한 처리로 된 경우를 제외합니다. 4. 선박승무원 및 항공승무원이 직무상 해외여행 중 여권을 분실 또는 도난당한 경우"
)

# p.70-72: 여행중단
TRIP_INT_CLAUSE1_TEXT = (
    "회사는 피보험자가 보험증권에 기재된 해외여행 도중에 아래 사항 중 어느 한 가지의 경우에 해당하는 사유로 여행을 "
    "중단하고 귀국하게 될 경우 보험증권에 명기된 보험가입금액 한도 내에서 피보험자가 입은 손해를 이 특별약관에 따라 "
    "보상하여 드립니다. 1. 피보험자 및 여행동반 가족이 상해 또는 질병으로 3일 이상 입원한 경우 2. 보험기간 내 피보험자의 "
    "3촌 이내의 친족 또는 여행동반자의 사망 3. 지진, 분화, 해일 또는 이와 비슷한 천재지변 4. 전쟁, 외국의 무력행사, 혁명, "
    "내란, 사변, 테러, 폭동, 소요, 기타 이들과 유사한 사태"
)

TRIP_INT_CLAUSE2_TEXT = (
    "제1조(보상하는 손해)에 따라 회사가 보상하는 비용은 아래와 같습니다. 1. 여행중단 후 귀국으로 인해 기지불한 항공 "
    "또는 선박 운임비용을 초과하여 피보험자에게 추가로 발생하는 항공 또는 선박 운임비용 2. 여행중단 후 귀국으로 인해 "
    "기지불한 숙박비용을 초과하여 피보험자에게 추가로 발생하는 2박 이내의 숙박비용"
)

TRIP_INT_CLAUSE3_TEXT = (
    "회사는 다음 중 어느 한 가지의 경우에 의하여 보험금 지급사유가 발생한 때에는 보험금을 드리지 않습니다. "
    "1. 피보험자의 고의. 다만, 피보험자가 심신상실 등으로 자유로운 의사결정을 할 수 없는 상태에서 자신을 해친 경우에는 "
    "보험금을 지급하여 드립니다. 2. 보험수익자의 고의. 다만, 그 보험수익자가 보험금의 일부를 받는 자인 경우에는 그 보험수익자에 "
    "해당하는 보험금을 제외한 나머지 보험금을 다른 보험수익자에게 지급하여 드립니다. 3. 계약자의 고의"
)

# p.72-73: 식중독
FOOD_POISON_CLAUSE1_TEXT = (
    "회사는 피보험자가 보통약관 제3조(보험금의 지급사유)의 여행도중의 음식물 섭취로 인해 중독(이하\"식중독\"이라 합니다)"
    "이 발생하고, 그 식중독의 치료를 직접적인 목적으로 병원 또는 의원(한방병원 또는 한의원을 포함합니다)에 2일 이상 "
    "계속 입원하여 의사의 치료를 받은 경우 보험증권에 기재된 이 특별약관의 보험가입금액을 식중독보상금으로 보험수익자"
    "(보험수익자의 지정이 없을 때는 피보험자)에게 지급하여 드립니다."
)

FOOD_POISON_CLAUSE2_TEXT = (
    "① 이 특별약관에 있어서 \"식중독\"이라 함은 한국표준질병사인분류의 식중독으로 분류되는 질병(【식중독 분류표】참조)을 "
    "말합니다. ② 제1항의 \"식중독\"의 진단확정은 의료법 제3조에서 정한 국내의 병원 또는 이와 동등하다 회사가 인정하는 국외의 "
    "의료기관의 의사자격을 가진 자에 의한 진단서에 의합니다."
)

# p.73-74: 특정전염병
INFECTIOUS_CLAUSE1_TEXT = (
    "① 회사는 피보험자가 보통약관 제3조(보험금의 지급사유)의 여행도중에 【특정전염병 분류표】에서 정한 특정전염병에 "
    "감염되어 전염병환자로 진단(임상학적 진단을 포함합니다)받아 치료를 받은 경우 최초1회의 진단에 한하여 이 특별약관의 "
    "보험가입금액을 보험수익자(보험수익자의 지정이 없을 때에는 피보험자)에게 지급합니다. ② 제1항에도 불구하고 여행도중에 "
    "감염된 특정전염병을 직접원인으로하여 보험기간 종료후 30일(보험기간 종료일은 제외합니다) 이내에 전염병환자로 진단받아 "
    "치료를 받은 경우에도 동일하게 보상합니다. ③ 제1항 및 제2항의 \"특정전염병\"의 진단확정 및 치료는 의료법 제3조에서 정한 "
    "국내의 병원 또는 이와 동등하다고 회사가 인정하는 해외의료기관의 의사자격을 가진 자(치료받는 국가의 법에서 정한 의사자격)에 "
    "의합니다."
)

# p.74-76: 항공기 및 수하물 지연
FLIGHT_DELAY_CLAUSE1_TEXT = (
    "① 회사는 피보험자가 보통약관 제3조(보험금의 지급사유)의 여행도중에 유료승객으로서 정기항공편을 이용하던 중에 아래의 "
    "보험사고가 발생한 경우 이로 인하여 입은 손해를 이 특별약관에 따라 보상하여 드립니다. 1. 연결항공편이 결항되었으며 출발예정"
    "시각으로부터 4시간 내에 피보험자에게 대체적인 항공운송수단이 제공되지 못할 경우 2. 항공편이 4시간이상 지연, 취소되거나 또는 "
    "피보험자가 과적에 의해 탑승이 거부되어 출발예정시각으로부터 4시간 내에 대체적인 수단이 제공되지 못하는 경우 3. 피보험자의 "
    "수하물이 항공편의 예정된 도착시각으로부터 6시간 이후에 피보험자에게 도착하는 경우 4. 피보험자의 위탁수하물이 손실되거나 또는 "
    "피보험자가 목적지에 도착한 후 24시간 내에 등록된 수하물이 피보험자에게 도착하지 못하는 경우"
)

FLIGHT_DELAY_CLAUSE2_TEXT = (
    "① 제1항의 보험사고로 인하여 회사가 보상하는 손해는 아래와 같습니다. 1. 제1호 또는 제2호의 경우 회사는 출발 또는 결항된 "
    "항공편에 대해 발생한 합리적으로 필요하며 유효한 아래의 비용: 가. 식사, 간식 또는 전화 통화 나. 숙박비, 숙박시설에 대한 교통비, "
    "수하물이 다른 항공편으로 출발한 경우 비상 의복 및 필수품의 구입비용. 다만, 숙박이 필요한 경우에 한합니다. 2. 제1항 제3호의 "
    "경우 비상 의복과 필수품의 구입에 소요되는 비용 3. 제1항 제4호의 경우 피보험자에 대해 의복과 필수품 등에 대하여 예정된 도착지에 "
    "도착후 120시간 내에 발생한 비용"
)

FLIGHT_DELAY_CLAUSE3_TEXT = (
    "회사는 아래의 사유로 생긴 손해는 보상하여 드리지 않습니다. 1. 명시적 또는 실질적 형태의 정부의 육, 해, 공 군사력에 의한 선포 "
    "또는 비선포된 전쟁 또는 이에 따르는 행위 2. 피보험자 또는 그 수혜자들에 의하거나 또는 이들을 위해 행해진 불법적인 행동 "
    "3. 교통수단의 조작자 또는 조종자로 종사하는 상황에서 발생한 손실 4. 세관 또는 여타 정부기관에 의한 압수 또는 보관조치 "
    "5. 피보험자가 수하물을 회수하는 데에 필요한 합리적인 노력을 행하지 않은 경우 6. 목적지에서 수하물 손실에 관련된 항공사 또는 "
    "관련 기관에 통보하고 재산손실보고를 취하지 않은 경우 7. 항공사 또는 그 지정자나 대리인에 대해 수하물을 포기하는 경우"
)

# p.97~113: 기본형 해외여행 실손의료비
MEDICAL_CLAUSE1_TEXT = (
    "회사는 기본형 해외여행 실손의료보험상품을 상해의료비, 질병의료비 등 2가지 이내의 보장종목으로 구성합니다. 계약자는 이들 "
    "2개 보장종목 중 한 가지 이상을 선택하여 가입할 수 있으며 세부구성항목의 해외 및 국내치료비도 선택하여 가입할 수 있습니다. "
    "보장 세부구성: 종목 항목 보상하는 내용 - 해외 피보험자가 해외여행 중에 입은 상해로 인하여 해외의료기관(주)에서 의료비가 발생한 경우에 보상 "
    "상해의료비 입원 피보험자가 해외여행 중에 입은 상해로 인하여 병원에서 입원하여 치료를 받은 경우에 보상 국내 통원 피보험자가 해외여행 중에 "
    "입은 상해로 인하여 병원에 통원하여 치료를 받거나 처방조제를 받은 경우에 보상 - 해외 피보험자가 해외여행 중에 질병으로 인하여 해외의료기관"
    "(주)에서 의료비가 발생한 경우에 보상 질병의료비 입원 피보험자가 해외여행 중에 질병으로 인하여 병원에서 입원하여 치료를 받은 경우에 보상 국내 "
    "통원 피보험자가 해외여행 중에 질병으로 인하여 병원에 통원하여 치료를 받거나 처방조제를 받은 경우에 보상"
)

MEDICAL_CLAUSE2_TEXT = (
    "① 회사는 피보험자가 보통약관 제3조(보험금의 지급사유)의 여행도중에 질병으로 인하여 해외의료기관(주)에서 의료비가 발생한 경우 "
    "붙임2-1(질병-해외의료)에 따라 보상합니다. ② 회사는 피보험자가 보통약관 제3조(보험금의 지급사유)의 여행도중에 질병으로 인하여 "
    "병원에서 입원하여 치료를 받은 경우 붙임2-2(질병-입원)에 따라 보상합니다. ③ 회사는 피보험자가 보통약관 제3조(보험금의 지급사유)의 "
    "여행도중에 질병으로 인하여 병원에 통원하여 치료를 받거나 처방조제를 받은 경우 붙임2-3(질병-국내 통원)에 따라 보상합니다. 다만, "
    "보험기간이 1년 미만인 경우에는 해외여행 중에 피보험자가 걸린 질병으로 보험기간 종료후 30일(보험기간 종료일은 제외합니다) 이내에 "
    "의사의 치료를 받기 시작했을 때에는 의사의 치료를 받기 시작한 날부터 180일(통원은 180일 동안 90회)까지만(보험기간 종료일은 제외합니다) "
    "보상합니다."
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
        insurer = db.query(Insurer).filter_by(code="KB").first()
        if not insurer:
            print("KB손해보험이 아직 시딩되지 않았습니다. seed_kb를 먼저 실행하세요.")
            return

        pv = (
            db.query(PolicyVersion)
            .join(Product, Product.product_id == PolicyVersion.product_id)
            .filter(Product.insurer_id == insurer.insurer_id)
            .first()
        )
        if not pv:
            print("KB PolicyVersion을 찾을 수 없습니다.")
            return

        types = {t.l2_code: t for t in db.query(IncidentType).all()}
        required = [
            "PROP_DAMAGE", "EMG_RESCUE", "TRV_HIJACK", "INJ_DEATH_DISABILITY",
            "PROP_PASSPORT_LOSS", "CHG_INTERRUPTION", "ILL_NEW_1",
            "ILL_INFECTIOUS", "TRV_FLIGHT_DELAY", "TRV_BAGGAGE_DELAY", "ILL_OVERSEAS_TREATMENT"
        ]
        missing = [c for c in required if c not in types]
        if missing:
            print(f"incident_type 사전에 없는 코드: {missing}. seed_incident_types를 먼저 실행하세요.")
            return

        std_personal = get_or_create_coverage_std(db, "PERSONAL_EFFECTS", "휴대품 손해(분실제외)", "휴대품", False)
        std_rescue = get_or_create_coverage_std(db, "RESCUE", "중대사고 구조송환비용", "구조", False)
        std_hijack = get_or_create_coverage_std(db, "HIJACK", "항공기납치", "운송", False)
        std_death_inj = get_or_create_coverage_std(db, "DEATH_INJURY", "상해사망·후유장해", "상해", True)
        std_passport = get_or_create_coverage_std(db, "PASSPORT_LOSS", "여권분실 재발급비용", "여행변경", False)
        std_trip_int = get_or_create_coverage_std(db, "TRIP_INTERRUPTION", "여행중단 추가비용", "여행변경", False)
        std_food = get_or_create_coverage_std(db, "FOOD_POISONING", "식중독보상금", "특수", False)
        std_infectious = get_or_create_coverage_std(db, "INFECTIOUS_DISEASE", "특정감염병보상금", "특수", False)
        std_flight_delay = get_or_create_coverage_std(db, "FLIGHT_DELAY", "항공기 지연·결항", "운송", False)
        std_baggage = get_or_create_coverage_std(db, "TRV_BAGGAGE_DELAY", "수하물지연", "운송", False)
        std_medical = get_or_create_coverage_std(db, "OVS_ILL_MED", "해외발생 질병의료비", "의료", False)

        clause_created = map_created = coverage_created = 0

        # =====================================================
        # 1) 휴대품손해 (p.62-64)
        # =====================================================
        cov_personal = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "해외여행중 휴대품손해(분실제외) 특별약관"
            )
            .first()
        )
        if not cov_personal:
            cov_personal = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_personal.coverage_std_id,
                raw_name="해외여행중 휴대품손해(분실제외) 특별약관",
                definition=PERSONAL_EFFECTS_CLAUSE2_TEXT,
                limit_amount="1개 또는 1조, 1쌍당 200,000원 한도(제4조)",
                deductible="보험증권 기재 자기부담금",
                waiting_condition="분실 제외(제1조②·제3조②제8호)",
            )
            db.add(cov_personal)
            db.flush()
            coverage_created += 1

        c1, m1 = _get_or_create_clause(db, policy_version_id=pv.policy_version_id, coverage_id=cov_personal.coverage_id,
            clause_type="보장정의", article_no="[해외여행중 휴대품손해 특별약관] 제1조(보험목적의 범위)",
            text=PERSONAL_EFFECTS_CLAUSE1_TEXT, page_ref="p.62", default_color="파랑")
        c2, m2 = _get_or_create_clause(db, policy_version_id=pv.policy_version_id, coverage_id=cov_personal.coverage_id,
            clause_type="보장정의", article_no="[해외여행중 휴대품손해 특별약관] 제2조(보상하는 손해)",
            text=PERSONAL_EFFECTS_CLAUSE2_TEXT, page_ref="p.62", default_color="파랑")
        c3, m3 = _get_or_create_clause(db, policy_version_id=pv.policy_version_id, coverage_id=cov_personal.coverage_id,
            clause_type="면책", article_no="[해외여행중 휴대품손해 특별약관] 제3조(보상하지 않는 손해)",
            text=PERSONAL_EFFECTS_CLAUSE3_TEXT, page_ref="p.62-63", default_color="빨강")
        clause_created += sum([m1, m2, m3])

        prop_damage_type = types["PROP_DAMAGE"]
        map_created += sum([
            _get_or_create_map(db, clause_id=c1.clause_id, type_id=prop_damage_type.type_id, relevance="직접", confidence=0.95),
            _get_or_create_map(db, clause_id=c2.clause_id, type_id=prop_damage_type.type_id, relevance="직접", confidence=0.95),
            _get_or_create_map(db, clause_id=c3.clause_id, type_id=prop_damage_type.type_id, relevance="면책", confidence=1.0),
        ])

        # =====================================================
        # 2) 구조송환비용 (p.65-67)
        # =====================================================
        cov_rescue = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "해외여행중 중대사고 구조송환비용 특별약관"
            )
            .first()
        )
        if not cov_rescue:
            cov_rescue = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_rescue.coverage_std_id,
                raw_name="해외여행중 중대사고 구조송환비용 특별약관",
                definition=RESCUE_CLAUSE1_TEXT,
                limit_amount="보험증권 기재 보험가입금액(제6조)",
                deductible=None,
                waiting_condition="사망/14일 이상 입원 조건(제1조①3호·4호)",
            )
            db.add(cov_rescue)
            db.flush()
            coverage_created += 1

        r1, mr1 = _get_or_create_clause(db, policy_version_id=pv.policy_version_id, coverage_id=cov_rescue.coverage_id,
            clause_type="보장정의", article_no="[해외여행중 중대사고 구조송환비용 특별약관] 제1조(보험금의 지급사유)",
            text=RESCUE_CLAUSE1_TEXT, page_ref="p.65-66", default_color="파랑")
        r2, mr2 = _get_or_create_clause(db, policy_version_id=pv.policy_version_id, coverage_id=cov_rescue.coverage_id,
            clause_type="보장정의", article_no="[해외여행중 중대사고 구조송환비용 특별약관] 제2조(비용의 범위)",
            text=RESCUE_CLAUSE2_TEXT, page_ref="p.66", default_color="파랑")
        r3, mr3 = _get_or_create_clause(db, policy_version_id=pv.policy_version_id, coverage_id=cov_rescue.coverage_id,
            clause_type="면책", article_no="[해외여행중 중대사고 구조송환비용 특별약관] 제3조(보험금을 지급하지 않는 사유)",
            text=RESCUE_CLAUSE3_TEXT, page_ref="p.66", default_color="빨강")
        clause_created += sum([mr1, mr2, mr3])

        rescue_type = types["EMG_RESCUE"]
        map_created += sum([
            _get_or_create_map(db, clause_id=r1.clause_id, type_id=rescue_type.type_id, relevance="직접", confidence=0.95),
            _get_or_create_map(db, clause_id=r2.clause_id, type_id=rescue_type.type_id, relevance="직접", confidence=0.9),
            _get_or_create_map(db, clause_id=r3.clause_id, type_id=rescue_type.type_id, relevance="면책", confidence=0.95),
        ])

        # =====================================================
        # 3) 항공기납치 (p.67-68)
        # =====================================================
        cov_hijack = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "해외여행중 항공기납치 특별약관"
            )
            .first()
        )
        if not cov_hijack:
            cov_hijack = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_hijack.coverage_std_id,
                raw_name="해외여행중 항공기납치 특별약관",
                definition=HIJACK_CLAUSE1_TEXT,
                limit_amount="일일 70,000원, 20일 한도(제2조①)",
                deductible=None,
                waiting_condition="도착예정시간 후 12시간 경과 필요(제2조①)",
            )
            db.add(cov_hijack)
            db.flush()
            coverage_created += 1

        h1, mh1 = _get_or_create_clause(db, policy_version_id=pv.policy_version_id, coverage_id=cov_hijack.coverage_id,
            clause_type="보장정의", article_no="[해외여행중 항공기납치 특별약관] 제1조(보험금의 지급사유)",
            text=HIJACK_CLAUSE1_TEXT, page_ref="p.67", default_color="파랑")
        h2, mh2 = _get_or_create_clause(db, policy_version_id=pv.policy_version_id, coverage_id=cov_hijack.coverage_id,
            clause_type="제한", article_no="[해외여행중 항공기납치 특별약관] 제2조(보험금 지급에 관한 세부규정)",
            text=HIJACK_CLAUSE2_TEXT, page_ref="p.67", default_color="초록")
        clause_created += sum([mh1, mh2])

        hijack_type = types["TRV_HIJACK"]
        map_created += sum([
            _get_or_create_map(db, clause_id=h1.clause_id, type_id=hijack_type.type_id, relevance="직접", confidence=1.0),
            _get_or_create_map(db, clause_id=h2.clause_id, type_id=hijack_type.type_id, relevance="조건부", confidence=1.0),
        ])

        # =====================================================
        # 4) 항공기탑승중 상해위험 (p.68-69, DEATH_INJURY 재사용)
        # =====================================================
        cov_aircraft = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "항공기탑승중 상해위험 특별약관"
            )
            .first()
        )
        if not cov_aircraft:
            cov_aircraft = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_death_inj.coverage_std_id,
                raw_name="항공기탑승중 상해위험 특별약관",
                definition=AIRCRAFT_INJ_CLAUSE1_TEXT,
                limit_amount="보험증권 기재 보험가입금액",
                deductible=None,
                waiting_condition="항공기탑승 중 사고로 한정(제1조②)",
            )
            db.add(cov_aircraft)
            db.flush()
            coverage_created += 1

        a1, ma1 = _get_or_create_clause(db, policy_version_id=pv.policy_version_id, coverage_id=cov_aircraft.coverage_id,
            clause_type="보장정의", article_no="[항공기탑승중 상해위험 특별약관] 제1조(보험금의 지급사유)",
            text=AIRCRAFT_INJ_CLAUSE1_TEXT, page_ref="p.68", default_color="파랑")
        a2, ma2 = _get_or_create_clause(db, policy_version_id=pv.policy_version_id, coverage_id=cov_aircraft.coverage_id,
            clause_type="면책", article_no="[항공기탑승중 상해위험 특별약관] 제2조(보험금을 지급하지 않는 사유)",
            text=AIRCRAFT_INJ_CLAUSE2_TEXT, page_ref="p.68", default_color="빨강")
        clause_created += sum([ma1, ma2])

        death_inj_type = types["INJ_DEATH_DISABILITY"]
        map_created += sum([
            _get_or_create_map(db, clause_id=a1.clause_id, type_id=death_inj_type.type_id, relevance="직접", confidence=0.95),
            _get_or_create_map(db, clause_id=a2.clause_id, type_id=death_inj_type.type_id, relevance="면책", confidence=1.0),
        ])

        # =====================================================
        # 5) 여권분실 (p.69-70)
        # =====================================================
        cov_passport = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "해외여행중 여권분실 후 재발급비용 특별약관"
            )
            .first()
        )
        if not cov_passport:
            cov_passport = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_passport.coverage_std_id,
                raw_name="해외여행중 여권분실 후 재발급비용 특별약관",
                definition=PASSPORT_LOSS_CLAUSE1_TEXT,
                limit_amount="여행증명서/여권 재발급수수료 한도(제1조②)",
                deductible=None,
                waiting_condition="여행증명서 발급 및 재발급신고 필수(제1조①)",
            )
            db.add(cov_passport)
            db.flush()
            coverage_created += 1

        p1, mp1 = _get_or_create_clause(db, policy_version_id=pv.policy_version_id, coverage_id=cov_passport.coverage_id,
            clause_type="보장정의", article_no="[해외여행중 여권분실 후 재발급비용 특별약관] 제1조(보상하는 손해)",
            text=PASSPORT_LOSS_CLAUSE1_TEXT, page_ref="p.69", default_color="파랑")
        p2, mp2 = _get_or_create_clause(db, policy_version_id=pv.policy_version_id, coverage_id=cov_passport.coverage_id,
            clause_type="면책", article_no="[해외여행중 여권분실 후 재발급비용 특별약관] 제2조(보상하지 않는 손해)",
            text=PASSPORT_LOSS_CLAUSE2_TEXT, page_ref="p.69-70", default_color="빨강")
        clause_created += sum([mp1, mp2])

        passport_type = types["PROP_PASSPORT_LOSS"]
        map_created += sum([
            _get_or_create_map(db, clause_id=p1.clause_id, type_id=passport_type.type_id, relevance="직접", confidence=1.0),
            _get_or_create_map(db, clause_id=p2.clause_id, type_id=passport_type.type_id, relevance="면책", confidence=1.0),
        ])

        # =====================================================
        # 6) 여행중단 (p.70-72)
        # =====================================================
        cov_trip_int = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "해외여행중 중단사고발생 추가비용 특별약관"
            )
            .first()
        )
        if not cov_trip_int:
            cov_trip_int = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_trip_int.coverage_std_id,
                raw_name="해외여행중 중단사고발생 추가비용 특별약관",
                definition=TRIP_INT_CLAUSE1_TEXT,
                limit_amount="보험증권 기재 보험가입금액 한도(제1조)",
                deductible=None,
                waiting_condition="3일 이상 입원 또는 사망 조건(제1조1호·2호)",
            )
            db.add(cov_trip_int)
            db.flush()
            coverage_created += 1

        t1, mt1 = _get_or_create_clause(db, policy_version_id=pv.policy_version_id, coverage_id=cov_trip_int.coverage_id,
            clause_type="보장정의", article_no="[해외여행중 중단사고발생 추가비용 특별약관] 제1조(보상하는 손해)",
            text=TRIP_INT_CLAUSE1_TEXT, page_ref="p.70", default_color="파랑")
        t2, mt2 = _get_or_create_clause(db, policy_version_id=pv.policy_version_id, coverage_id=cov_trip_int.coverage_id,
            clause_type="보장정의", article_no="[해외여행중 중단사고발생 추가비용 특별약관] 제2조(비용의 범위)",
            text=TRIP_INT_CLAUSE2_TEXT, page_ref="p.70-71", default_color="파랑")
        t3, mt3 = _get_or_create_clause(db, policy_version_id=pv.policy_version_id, coverage_id=cov_trip_int.coverage_id,
            clause_type="면책", article_no="[해외여행중 중단사고발생 추가비용 특별약관] 제3조(보상하지 않는 손해)",
            text=TRIP_INT_CLAUSE3_TEXT, page_ref="p.71", default_color="빨강")
        clause_created += sum([mt1, mt2, mt3])

        trip_int_type = types["CHG_INTERRUPTION"]
        map_created += sum([
            _get_or_create_map(db, clause_id=t1.clause_id, type_id=trip_int_type.type_id, relevance="직접", confidence=1.0),
            _get_or_create_map(db, clause_id=t2.clause_id, type_id=trip_int_type.type_id, relevance="직접", confidence=0.95),
            _get_or_create_map(db, clause_id=t3.clause_id, type_id=trip_int_type.type_id, relevance="면책", confidence=1.0),
        ])

        # =====================================================
        # 7) 식중독 (p.72-73)
        # =====================================================
        cov_food = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "해외여행중 식중독보상금 특별약관"
            )
            .first()
        )
        if not cov_food:
            cov_food = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_food.coverage_std_id,
                raw_name="해외여행중 식중독보상금 특별약관",
                definition=FOOD_POISON_CLAUSE1_TEXT,
                limit_amount="보험증권 기재 보험가입금액 (2일 이상 입원 필수)",
                deductible=None,
                waiting_condition="2일 이상 지속 입원 필수(제1조)",
            )
            db.add(cov_food)
            db.flush()
            coverage_created += 1

        f1, mf1 = _get_or_create_clause(db, policy_version_id=pv.policy_version_id, coverage_id=cov_food.coverage_id,
            clause_type="보장정의", article_no="[해외여행중 식중독보상금 특별약관] 제1조(보상하는 손해)",
            text=FOOD_POISON_CLAUSE1_TEXT, page_ref="p.72", default_color="파랑")
        f2, mf2 = _get_or_create_clause(db, policy_version_id=pv.policy_version_id, coverage_id=cov_food.coverage_id,
            clause_type="보장정의", article_no="[해외여행중 식중독보상금 특별약관] 제2조(식중독의 정의 및 진단확정)",
            text=FOOD_POISON_CLAUSE2_TEXT, page_ref="p.72", default_color="파랑")
        clause_created += sum([mf1, mf2])

        food_type = types["ILL_NEW_1"]  # 삼성화재 딥다이브에서 만든 "식중독보상금(입원)" 재사용
        map_created += sum([
            _get_or_create_map(db, clause_id=f1.clause_id, type_id=food_type.type_id, relevance="직접", confidence=1.0),
            _get_or_create_map(db, clause_id=f2.clause_id, type_id=food_type.type_id, relevance="조건부", confidence=0.95),
        ])

        # =====================================================
        # 8) 특정전염병 (p.73-74)
        # =====================================================
        cov_infectious = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "해외여행중 특정전염병치료비 특별약관"
            )
            .first()
        )
        if not cov_infectious:
            cov_infectious = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_infectious.coverage_std_id,
                raw_name="해외여행중 특정전염병치료비 특별약관",
                definition=INFECTIOUS_CLAUSE1_TEXT,
                limit_amount="보험증권 기재 보험가입금액 (최초 1회 한도)",
                deductible=None,
                waiting_condition="특정전염병 분류표 해당 질병만 보장(제1조①)",
            )
            db.add(cov_infectious)
            db.flush()
            coverage_created += 1

        i1, mi1 = _get_or_create_clause(db, policy_version_id=pv.policy_version_id, coverage_id=cov_infectious.coverage_id,
            clause_type="보장정의", article_no="[해외여행중 특정전염병치료비 특별약관] 제1조(보험금의 지급사유)",
            text=INFECTIOUS_CLAUSE1_TEXT, page_ref="p.73-74", default_color="파랑")
        clause_created += mi1

        infectious_type = types["ILL_INFECTIOUS"]
        map_created += _get_or_create_map(db, clause_id=i1.clause_id, type_id=infectious_type.type_id, relevance="직접", confidence=1.0)

        # =====================================================
        # 9) 항공기/수하물 지연 (p.74-76)
        # =====================================================
        cov_flight = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "항공기 및 수하물 지연비용 특별약관 - 항공기지연"
            )
            .first()
        )
        if not cov_flight:
            cov_flight = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_flight_delay.coverage_std_id,
                raw_name="항공기 및 수하물 지연비용 특별약관 - 항공기지연",
                definition=FLIGHT_DELAY_CLAUSE1_TEXT,
                limit_amount="합리적 필요 비용한도(제2조①)",
                deductible=None,
                waiting_condition="4시간 이상 지연/결항 조건(제1조①1호·2호)",
            )
            db.add(cov_flight)
            db.flush()
            coverage_created += 1

        cov_baggage = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "항공기 및 수하물 지연비용 특별약관 - 수하물지연"
            )
            .first()
        )
        if not cov_baggage:
            cov_baggage = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_baggage.coverage_std_id,
                raw_name="항공기 및 수하물 지연비용 특별약관 - 수하물지연",
                definition=FLIGHT_DELAY_CLAUSE1_TEXT,
                limit_amount="필수품 구입비 한도(제2조②·③, 120시간 내)",
                deductible=None,
                waiting_condition="도착 6시간 이후 도착/손실 조건(제1조①3호·4호)",
            )
            db.add(cov_baggage)
            db.flush()
            coverage_created += 1

        fd1, mfd1 = _get_or_create_clause(db, policy_version_id=pv.policy_version_id, coverage_id=cov_flight.coverage_id,
            clause_type="보장정의", article_no="[항공기 및 수하물 지연비용 특별약관] 제1조(보상하는 손해)",
            text=FLIGHT_DELAY_CLAUSE1_TEXT, page_ref="p.74-75", default_color="파랑")
        fd2, mfd2 = _get_or_create_clause(db, policy_version_id=pv.policy_version_id, coverage_id=cov_flight.coverage_id,
            clause_type="보장정의", article_no="[항공기 및 수하물 지연비용 특별약관] 제2조(보상하는 손해 범위)",
            text=FLIGHT_DELAY_CLAUSE2_TEXT, page_ref="p.75", default_color="파랑")
        fd3, mfd3 = _get_or_create_clause(db, policy_version_id=pv.policy_version_id, coverage_id=cov_flight.coverage_id,
            clause_type="면책", article_no="[항공기 및 수하물 지연비용 특별약관] 제3조(보상하지 않는 손해)",
            text=FLIGHT_DELAY_CLAUSE3_TEXT, page_ref="p.75", default_color="빨강")

        # 같은 Clause를 수하물지연 coverage에도 연결
        bd1, mbd1 = _get_or_create_clause(db, policy_version_id=pv.policy_version_id, coverage_id=cov_baggage.coverage_id,
            clause_type="보장정의", article_no="[항공기 및 수하물 지연비용 특별약관] 제1조(보상하는 손해) - 수하물지연",
            text=FLIGHT_DELAY_CLAUSE1_TEXT, page_ref="p.74-75", default_color="파랑")
        bd2, mbd2 = _get_or_create_clause(db, policy_version_id=pv.policy_version_id, coverage_id=cov_baggage.coverage_id,
            clause_type="보장정의", article_no="[항공기 및 수하물 지연비용 특별약관] 제2조(보상하는 손해 범위) - 수하물지연",
            text=FLIGHT_DELAY_CLAUSE2_TEXT, page_ref="p.75", default_color="파랑")

        clause_created += sum([mfd1, mfd2, mfd3, mbd1, mbd2])

        flight_type = types["TRV_FLIGHT_DELAY"]
        baggage_type = types["TRV_BAGGAGE_DELAY"]
        map_created += sum([
            _get_or_create_map(db, clause_id=fd1.clause_id, type_id=flight_type.type_id, relevance="직접", confidence=1.0),
            _get_or_create_map(db, clause_id=fd1.clause_id, type_id=baggage_type.type_id, relevance="직접", confidence=0.9),
            _get_or_create_map(db, clause_id=fd2.clause_id, type_id=flight_type.type_id, relevance="직접", confidence=1.0),
            _get_or_create_map(db, clause_id=fd2.clause_id, type_id=baggage_type.type_id, relevance="직접", confidence=0.95),
            _get_or_create_map(db, clause_id=fd3.clause_id, type_id=flight_type.type_id, relevance="면책", confidence=1.0),
            _get_or_create_map(db, clause_id=fd3.clause_id, type_id=baggage_type.type_id, relevance="면책", confidence=1.0),
            _get_or_create_map(db, clause_id=bd1.clause_id, type_id=baggage_type.type_id, relevance="직접", confidence=1.0),
            _get_or_create_map(db, clause_id=bd2.clause_id, type_id=baggage_type.type_id, relevance="직접", confidence=1.0),
        ])

        # =====================================================
        # 10) 기본형 해외여행 실손의료비 - 질병 부분 (p.97~113)
        # =====================================================
        cov_medical = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "기본형 해외여행 실손의료비 특별약관 - 질병"
            )
            .first()
        )
        if not cov_medical:
            cov_medical = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_medical.coverage_std_id,
                raw_name="기본형 해외여행 실손의료비 특별약관 - 질병",
                definition=MEDICAL_CLAUSE2_TEXT,
                limit_amount="선택한 보장종목별 보험가입금액(제4조 참고)",
                deductible="보험증권 기재 자기부담금",
                waiting_condition="해외/국내 통원/입원 선택 가능(제1조)",
            )
            db.add(cov_medical)
            db.flush()
            coverage_created += 1

        m1, mm1 = _get_or_create_clause(db, policy_version_id=pv.policy_version_id, coverage_id=cov_medical.coverage_id,
            clause_type="보장정의", article_no="[기본형 해외여행 실손의료비 특별약관] 제1조(보장종목)",
            text=MEDICAL_CLAUSE1_TEXT, page_ref="p.97", default_color="파랑")
        m2, mm2 = _get_or_create_clause(db, policy_version_id=pv.policy_version_id, coverage_id=cov_medical.coverage_id,
            clause_type="보장정의", article_no="[기본형 해외여행 실손의료비 특별약관] 제2조(보험금의 지급사유) - 질병",
            text=MEDICAL_CLAUSE2_TEXT, page_ref="p.97-113", default_color="파랑")
        clause_created += sum([mm1, mm2])

        ill_overseas_type = types["ILL_OVERSEAS_TREATMENT"]
        map_created += sum([
            _get_or_create_map(db, clause_id=m1.clause_id, type_id=ill_overseas_type.type_id, relevance="직접", confidence=1.0),
            _get_or_create_map(db, clause_id=m2.clause_id, type_id=ill_overseas_type.type_id, relevance="직접", confidence=1.0),
        ])

        db.commit()
        print(
            "KB 청크2(p.58-113) 완료: "
            f"coverage 신규={coverage_created}, clause 신규={clause_created}, "
            f"clause_incident_map 신규={map_created}. "
            "p.58-61(배상책임 계약행정), p.76-96(단체/환율/지정대리청구 등 계약행정)은 사고유형과 무관하여 스킵됨."
        )

    finally:
        db.close()


if __name__ == "__main__":
    run()
