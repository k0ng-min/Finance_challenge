"""
현대해상 다이렉트 해외여행보험 2026년판 청크 d - 특약 및 부록 처리
파일 출처: backend/data/processed/hyundai_overseas_8403-0000-20260606_full_text.txt
담당 페이지: 119-162 (===PAGE 119=== ~ ===PAGE 162===)

## 페이지 범위 분석
- 페이지 119-121: 장애인전용보험 전환 특별약관
- 페이지 122: 여행 동반인 보장 특별약관
- 페이지 124: 공동인수 특별약관
- 페이지 124: () 보험금만의 지급 특별약관
- 페이지 124-125: 지정대리청구서비스 특별약관
- 페이지 125-126: 환율 특별약관
- 페이지 126-144: 지수형 출국항공기 지연보장 특별약관 (보장내용, 지급절차 등)
- 페이지 125-144: 별표1 - 장해분류표 (참고용 정표 데이터, Clause 추가 안함)
- 페이지 144-145: 별표2 - 해외여행통지 (양식 서식, Clause 추가 안함)
- 페이지 145-146: 별표3 - 식중독 분류표 (참고용 정표 데이터, Clause 추가 안함)
- 페이지 146-147: 별표4 - 특정전염병 분류표 (참고용 정표 데이터, Clause 추가 안함)
- 페이지 147-162: 법규 (개인정보보호법, 보험업법, 신용정보법 등 관련법, Clause 추가 안함)

## 발견 요약
페이지 119-162는 특별약관 6개와 부록(별표, 법규)으로 구성:

### 특별약관 (Clause로 추가)
1. 장애인전용보험 전환 특별약관: 소득세법상 특혜 적용을 위한 전환약관
   - 제1조(특별약관의 적용범위)
   - 제2조(제출서류)
   - 제3조(장애인전용보험으로의 전환)
   - 제4조(전환 취소)
   - 제5조(준용규정)

2. 여행 동반인 보장 특별약관: 피보험자 동행인도 보장
   - 제1조(피보험자의 범위)
   - 제2조(준용규정)

3. 공동인수 특별약관: 여러 보험사 공동 인수
   - 제1조(책임의 분담)
   - 제2조(준용규정)

4. () 보험금만의 지급 특별약관: 특정 보험금만 지급 (구체적 내용 없음, 빈칸)
   - 제1조(보상하는 손해)
   - 제2조(준용규정)

5. 지정대리청구서비스 특별약관: 지정된 대리인이 보험금 청구 가능
   - 제1조(적용대상)
   - 제2조(특약의 체결 및 소멸)
   - 제3조(지정대리청구인의 지정)
   - 제4조(지정대리청구인의 변경지정)
   - 제5조(보험금 지급 등의 절차)
   - 제6조(보험금 등 청구시 구비서류)
   - 제7조(준용규정)

6. 환율 특별약관: 외화 보험료/보험금의 환율 적용 기준
   - 제1조(보험료 적용기준)
   - 제2조(보험금 지급기준)

7. 지수형 출국항공기 지연보장 특별약관: 국제선 항공기 지연 시 보험금 지급
   - 제1조(보상하는 손해): 누적지연시간별 보험금 지급표 포함
   - 제2조(보상하지 않는 손해): 고의/사기, 사전통보 등 6가지 면책사유
   - 제3조(보험금 청구시 구비서류)
   - 제4조(다른 보험과의 관계)
   - 제5조(특별약관의 소멸)
   - 제6조(보험료의 환급)
   - 제7조(준용규정)

### 부록 (Clause로 추가 안함, 확인 기록만)
- 별표1(장해분류표): 장해의 정의, 신체부위, 13개 부위별 장해지급률 정표 (확인함, 참고용 표라 건너뜸)
- 별표2(해외여행통지): 여행통지 양식 폼 (확인함, 양식 폼이라 건너뜸)
- 별표3(식중독분류표): 보장 질병 분류코드 정표 (확인함, 참고용 표라 건너뜸)
- 별표4(특정전염병분류표): 제1~3군 전염병 분류코드 정표 (확인함, 참고용 표라 건너뜸)
- 법규 섹션(법규1~18): 개인정보보호법, 보험업법, 신용정보법 등 관련법 인용 (확인함, 원본 법규 인용이라 건너뜸)

## 새로 만드는 CoverageStd
1. DISABILITY_CONVERSION: 장애인전용보험 전환
2. TRAVEL_COMPANION: 여행 동반인 보장
3. DELEGATION_CLAIM: 지정대리청구서비스
4. FLIGHT_DELAY: 출국항공기 지연보장

공동인수 특약과 환율 특약은 계약행정성이므로 CoverageStd 생성 안함.
() 보험금만의 지급 특약은 구체적 내용이 없으므로 처리 안함.

## 시드 전략
- idempotent: PolicyVersion 확인 후 없으면 생성
- 각 CoverageStd 조회/생성
- 각 Coverage 조회/생성
- 각 조항별 Clause 생성 (기존 조항과 중복 확인)
"""
from datetime import date
from app.database import SessionLocal
from app import models  # noqa: F401
from app.models.kb import Clause, Coverage, PolicyVersion
from app.services.kb_seed_common import get_or_create_coverage_std

PRODUCT_CODE = "HYUNDAI-OVERSEAS-2026"
VERSION_LABEL = "8403-0000-20260606"

# ===== 1. 장애인전용보험 전환 특별약관 =====
DISABILITY_CONVERSION_TITLE = "장애인전용보험 전환 특별약관"

CLAUSE_D_1_1_TEXT = (
    "제1조 (특별약관의 적용범위) "
    "① 회사는 다음 각 호의 조건을 모두 만족하는 전환대상계약에 대하여 이 특별약관을 적용합니다. "
    "1. 다이렉트 해외여행보험의 계약 "
    "2. 모든 피보험자 또는 모든 보험수익자가 소득세법 시행령 제107조 제1항에서 규정하는 장애인 "
    "② 전환대상계약이 해지 또는 기타 사유로 효력이 없게 된 경우 또는 전환대상계약이 제1항에서 정한 조건을 "
    "만족하지 않게 된 경우 이 특약은 그 때부터 효력이 없습니다. "
    "③ 제2조 제1항에 따라 제출된 장애인증명서상 장애예상기간(또는 장애기간)이 종료된 경우에는 제3조 제1항에도 "
    "불구하고 이 특약은 그때부터 효력이 없습니다. "
    "④ 이 특약의 계약자는 전환대상계약의 계약자와 동일하여야 합니다."
)

CLAUSE_D_1_2_TEXT = (
    "제2조 (제출서류) "
    "① 이 특약에 가입하고자 하는 계약자는 모든 피보험자 또는 모든 보험수익자의 「소득세법 시행규칙 별지 제38호 "
    "서식에 의한 장애인증명서의 원본 또는 사본」(이하, \"장애인증명서\"라 합니다)을 제출하여 제1조(특별약관의 적용범위) "
    "제1항 제2호에서 정한 조건에 해당함을 회사에 알려야 합니다. "
    "② 제 1 항에도 불구하고 「국가유공자 등 예우 및 지원에 관한 법률」에 따른 상이자의 증명을 받은 사람 또는 "
    "「장애인복지법」에 따른 장애인등록증을 발급받은 사람에 대해서는 해당 증명서·장애인등록증의 사본이나 그 밖의 "
    "장애 사실을 증명하는 서류를 제출하는 경우에는 제 1항의 장애인증명서는 제출하지 않을 수 있습니다. "
    "③ 장애인으로서 그 장애기간이 기재된 장애인증명서를 제 1 항에 따라 회사에 제출한 때에는 그 장애기간 동안은 "
    "이를 다시 제출하지 않을 수 있습니다. "
    "④ 제 1 항에 따라 제출한 장애인증명서의 장애기간이 변경되는 경우 계약자는 이를 회사에 알리고 변경된 "
    "장애기간이 기재된 장애인증명서를 제출하여야 합니다."
)

CLAUSE_D_1_3_TEXT = (
    "제3조 (장애인전용보험으로의 전환) "
    "① 회사는 이 특약이 부가된 전환대상계약을 「소득세법 제59조의4(특별세액공제) 제1항 제1호」에 해당하는 "
    "장애인전용보험으로 전환하여 드립니다. "
    "② 제 1 항에 따라 전환대상계약이 장애인전용보험으로 전환된 후부터 납입된 전환대상계약 보험료는 보험료 납입영수증에 "
    "장애인전용 보장성보험료로 표시됩니다. "
    "③ 제2항에도 불구하고, 「 전환대상계약이 장애인전용보험으로 전환된 당해년도에 제4조(전환 취소)에 따라 전환을 취소하는 경우」에는 "
    "당해년도에 납입한 모든 전환대상계약보험료가 보험료 납입영수증에 장애인전용보장성보험료로 표시되지 않습니다. "
    "다만, 제2조(제출서류)제1항에 따라 제출된 장애인증명서상 장애예상기간(또는 장애기간)이 종료됨에 따라 제1 조(특별약관의 적용범위) "
    "제 1 항 제 2 호에서 정한 조건을 만족하지 않게 된 경우에는 이 조항이 적용되지 않습니다. "
    "④ 전환대상계약에 이 특약이 부가된 이후 제 4 조(전환 취소)에 따라 전환을 취소한 경우 또는 전환대상계약이 "
    "제 1 조(특별약관의 적용범위)제 1 항 제 2 호에서 정한 조건을 만족하지 않아 이 특약의 효력이 없어진 경우 "
    "해당 전환대상계약에는 이 특약을 다시 부가할 수 없습니다. 다만, 제 2 조(제출서류) 제 1 항에 따라 제출된 "
    "장애인증명서상 장애예상기간(또는 장애기간)이 종료됨에 따라 전환대상계약이 제 1 조 (특별약관의 적용범위 ) "
    "제 1 항 제 2 호에서 정한 조건을 만족하지 않게 된 경우에는 이 조항이 적용되지 않습니다."
)

CLAUSE_D_1_4_TEXT = (
    "제4조 (전환 취소) "
    "계약자는 전환대상계약에 대하여 장애인전용보험으로의 전환을 취소할 수 있으며, 이 경우 전환취소 신청서를 "
    "회사에 제출하여야 합니다."
)

CLAUSE_D_1_5_TEXT = (
    "제5조 (준용규정) "
    "① 이 특약에서 정하지 않은 사항에 대하여는 전환대상계약 약관, 소득세법 등 관련법규에서 정하는 바에 따릅니다. "
    "② 소득세법 등 관련법규가 제·개정 또는 폐지되는 경우 변경된 법령을 따릅니다."
)

# ===== 2. 여행 동반인 보장 특별약관 =====
TRAVEL_COMPANION_TITLE = "여행 동반인 보장 특별약관"

CLAUSE_D_2_1_TEXT = (
    "제 1 조 (피보험자의 범위) "
    "회사는 이 특별약관에 의하여 피보험자 본인 및 보험증권에 기재된 피보험자의 여행 동반인을 보통약관(해당 특별약관을 "
    "포함합니다)의 피보험자로 합니다."
)

CLAUSE_D_2_2_TEXT = (
    "제 2 조 (준용규정) "
    "이 특별약관에 정하지 않은 사항은 보통약관 및 해당 특별약관을 따릅니다."
)

# ===== 3. 공동인수 특별약관 =====
CO_INSURANCE_TITLE = "공동인수 특별약관"

CLAUSE_D_3_1_TEXT = (
    "제 1 조 (책임의 분담) "
    "이 보험증권은 아래의 회사들을 대리하여 ( )가 발행하며 각 회사는 아래에 명기된 인수비율에 따라 그 책임을 부담합니다. "
    "회 사 인수비율(금액)"
)

CLAUSE_D_3_2_TEXT = (
    "제 2 조 (준용규정) "
    "이 특별약관에서 정하지 않은 사항은 보통약관에 따릅니다"
)

# ===== 4. () 보험금만의 지급 특별약관 =====
SPECIFIC_BENEFIT_TITLE = "() 보험금만의 지급 특별약관"

CLAUSE_D_4_1_TEXT = (
    "제 1 조 (보상하는 손해) "
    "회사는 ( )약관에 관계없이 ( )보험금만을 지급합니다."
)

CLAUSE_D_4_2_TEXT = (
    "제 2 조 (준용규정) "
    "이 특별약관에 정하지 않은 사항은 ( )약관을 따릅니다."
)

# ===== 5. 지정대리청구서비스 특별약관 =====
DELEGATION_CLAIM_TITLE = "지정대리청구서비스 특별약관"

CLAUSE_D_5_1_TEXT = (
    "제1조(적용대상) "
    "이 특별약관(이하 \"특약\")은 계약자, 피보험자 및 보험수익자가 모두 동일한 보통약관 및 특별약관에 적용됩니다."
)

CLAUSE_D_5_2_TEXT = (
    "제2조(특약의 체결 및 소멸) "
    "① 이 특약은 계약자의 청약(請約)과 회사의 승낙(承諾)으로 부가되어집니다. "
    "② 제1조(적용대상)의 계약이 해지(解止) 또는 기타 사유에 의하여 효력을 가지지 않게 되는 경우에는 이 특약은 "
    "더 이상 효력을 가지지 않습니다."
)

CLAUSE_D_5_3_TEXT = (
    "제3조(지정대리청구인의 지정) "
    "① 계약자는 보험계약에서 정한 보험금을 직접 청구할 수 없는 특별한 사정이 있을 경우를 대비하여 계약체결시 또는 "
    "계약체결 이후 다음 각 호의 어느 하나에 해당하는 자 중에서 보험금의 대리청구인(2인 이내에서 지정하되, 2인 지정시 "
    "대표대리인을 지정)(이하 \"지정대리청구인\"이라 합니다)을 지정할 수 있습니다. 또한 지정대리청구인은 제4조(지정대리청구인의 "
    "변경지정)에 의한 변경 지정 또는 보험금 청구시에도 다음 각호의 어느 하나에 해당하여야 합니다. "
    "1. 피보험자의 가족관계등록부상의 배우자 "
    "2. 피보험자의 3촌 이내의 친족 "
    "② 제1항에도 불구하고, 지정대리청구인이 지정된 이후에 제1조(적용대상)의 보험수익자가 변경되는 경우에는 "
    "이미 지정된 지정대리청구인의 자격은 자동적으로 상실된 것으로 봅니다."
)

CLAUSE_D_5_4_TEXT = (
    "제4조(지정대리청구인의 변경지정) "
    "계약자는 다음의 서류를 제출하고 지정대리청구인을 변경 지정할 수 있습니다. 이 경우 회사는 변경 지정을 서면으로 "
    "알리거나 보험증권의 뒷면에 기재하여 드립니다. "
    "1. 지정대리청구인 변경신청서(회사양식) "
    "2. 지정대리청구인의 주민등록등본, 가족관계등록부(기본증명서 등) "
    "3. 신분증(주민등록증이나 운전면허증 등 사진이 붙은 정부기관발행 신분증, 본인이 아닌 경우에는 본인의 인감증명서, "
    "본인서명사실확인서 또는 안전성과 신뢰성이 확보된 전자적 수단을 활용한 보험수익자 의사표시의 확인방법 포함)"
)

CLAUSE_D_5_5_TEXT = (
    "제5조(보험금 지급 등의 절차) "
    "① 지정대리청구인은 제6조(보험금 등 청구시 구비서류)에 정한 구비서류 및 제1조(적용대상)의 피보험자가 보험금을 "
    "직접 청구할 수 없는 특별한 사정이 있음을 증명하는 서류를 제출하고 회사의 승낙을 얻어 제1조(적용대상)의 피보험자의 "
    "대리인으로서 보험금(사망보험금 제외)을 청구하고 수령할 수 있습니다. 다만, 2인의 대리청구인이 지정된 경우에는 그 중 "
    "대표대리인이 보험금을 청구하고 수령할 수 있으며, 대표대리인이 사망 등의 사유로 보험금 청구가 불가능한 경우에는 "
    "대표가 아닌 대리청구인도 보험금을 청구하고 수령할 수 있습니다. "
    "② 회사가 보험금을 지정대리청구인에게 지급한 경우에는 그 이후 보험금 청구를 받더라도 회사는 이를 지급하지 않습니다."
)

CLAUSE_D_5_6_TEXT = (
    "제6조(보험금 등 청구시 구비서류) "
    "지정대리청구인은 회사가 정하는 방법에 따라 다음의 서류를 제출하고 보험금을 청구하여야 합니다. "
    "1. 청구서(회사양식) "
    "2. 사고증명서 "
    "3. 신분증(주민등록증 또는 운전면허증 등 사진이 부착된 정부기관 발행 신분증) "
    "4. 피보험자 및 지정대리청구인의 가족관계등록부(가족관계증명서) 및 주민등록등본 "
    "5. 기타 지정대리청구인이 보험금 등의 수령에 필요하여 제출하는 서류"
)

CLAUSE_D_5_7_TEXT = (
    "제7조(준용규정) "
    "이 특약에서 정하지 않은 사항에 대하여는 보통약관의 규정을 따릅니다."
)

# ===== 6. 환율 특별약관 =====
EXCHANGE_RATE_TITLE = "환율 특별약관"

CLAUSE_D_6_1_TEXT = (
    "제1조(보험료 적용기준) "
    "회사는 보험료를 원화로 영수 또는 환급할 때에는 청약일 또는 배서일의 하나은행 1차고시 전신환대고객매도율로 환산한 "
    "원화로 합니다. "
    "1.보험료 : 청약일 "
    "2.추가 및 환급보험료 : 배서일 "
    "3.해지환급보험료 : 해지일 "
    "4.분납보험료 : 납입해당일"
)

CLAUSE_D_6_2_TEXT = (
    "제2조(보험금 지급기준) "
    "보험금은 지급일의 하나은행 1차고시 전신환대고객매도율로 환산한 원화 또는 ( )화에 해당하는 외환증서로 "
    "지급하여 드립니다."
)

# ===== 7. 지수형 출국항공기 지연보장 특별약관 =====
FLIGHT_DELAY_TITLE = "지수형 출국항공기 지연보장 특별약관"

CLAUSE_D_7_1_TEXT = (
    "제 1 조 (보상하는 손해) "
    "회사는 피보험자가 보험기간 중에 아래의 보험사고가 발생한 경우 아래의 표와 같이 보험금을 지급하여 드립니다. "
    "1. 국내국제공항에서 출발하는 국제선 여객기의 실제 출발시각이 출발계획시각보다 2시간 이상 지연되거나 결항된 경우 "
    "(단위: 원) "
    "누적지연시간 / 최초 지연시간 / 3시간 이상 4시간미만 / 4시간 이상 6시간미만 / 6시간 이상 누적최대 "
    "2시간 / 40,000 / - / - / - "
    "3시간 / 60,000 / 20,000 / - / 20,000 "
    "4시간 / 80,000 / 20,000 / 20,000 / 100,000 "
    "6시간 / 100,000 / - / - / 결항 "
    "보험금액"
)

CLAUSE_D_7_1_DEFINITION = (
    "【별표1】 지수형 출국항공기 지연보장 특별약관의 용어해설 "
    "<실제 출발시각> "
    "공항공사 등 관련기관에 등록된 항공편(대체 항공편이 제공되는 경우 대체 항공편)이 게이트에서 실제 출발하는 시각을 "
    "의미합니다. "
    "<출발계획시각> "
    "항공사가 인천공항공사 등 관련기관에 항공편의 출발계획시각으로 등록한 시각을 기준으로 합니다."
)

CLAUSE_D_7_2_TEXT = (
    "제 2 조 (보상하지 않는 손해) "
    "회사는 아래의 사유로 생긴 손해는 보상하여 드리지 않습니다. "
    "1. 명시적 또는 실질적 형태의 정부의 육, 해, 공 군사력에 의한 선포 또는 비선포된 전쟁 또는 이에 따르는 행위 "
    "2. 피보험자 또는 그 수혜자들에 의하거나 또는 이들을 위해 행해진 불법적인 행동 "
    "3. 교통수단의 조작자 또는 조종자로 종사하는 상황에서 발생한 손실 "
    "4. 피보험자가 출발계획시각 이전에 항공권 구매를 취소한 경우 "
    "5. 피보험자가 구매한 항공권이 최초 출발계획시간 이전 24시간 전에 결항이 확정된 경우 "
    "6. 피보험자가 탑승하려는 항공편이 지연됨을 사전 통보 받았으나, 최종적으로 탑승권에 기재된 출발계획시각 대비 "
    "2시간 지나기 전에 출발한 경우"
)

CLAUSE_D_7_3_TEXT = (
    "제 3 조 (보험금 청구시 구비서류) "
    "계약자, 피보험자(또는 수익자)는 청구의 원인이 되는 사건 발생 후 30일 이내에 다음의 서류를 제출하고 보험금을 청구하여야 합니다. "
    "1. 보험금 청구서(회사양식) "
    "2. 신분증(주민등록증이나 운전면허증 등 사진이 붙은 정부기관발행 신분증, 본인이 아닌 경우에는 본인의 인감증명서 "
    "또는 본인서명사실확인서 포함) "
    "3. 피보험자의 항공사 탑승권 사본 "
    "4. 회사측에서 손실 또는 불편발생에 대한 사실여부를 확인하는 데에 도움이 될 수 있는 추가정보(항공기 지연 확인서 등)"
)

CLAUSE_D_7_4_TEXT = (
    "제4조(다른 보험과의 관계) "
    "이 특별약관의 청약 이전에 이 특별약관과 같은 위험을 보장하는 다른 계약(단체계약 포함)을 이미 가입하여(다수의 계약을 "
    "청약한 경우에는 가장 먼저 가입 완료한 계약을 '이미 가입한 계약'으로 봅니다) 이미 가입한 계약에서 보상하는 손해에 "
    "대해서는 보험금 지급이 거절 될 수 있습니다. 단, 계약자의 청약을 회사가 승낙하기 전에 회사가 중복 계약을 알았거나 "
    "알 수 있었으나 회사의 고의 또는 과실로 그 청약을 승낙한 경우에는 이를 적용하지 않습니다."
)

CLAUSE_D_7_5_TEXT = (
    "제 5조 (특별약관의 소멸) "
    "회사가 제1조(보상하는 손해)에 따라 보험기간 중 최초 1회의 보험사고에 대해 보상한 경우에는 이 특별약관은 "
    "그 때부터 효력이 없습니다."
)

CLAUSE_D_7_6_TEXT = (
    "제 6조 (보험료의 환급) "
    "회사는 보통약관 제29조(보험료의 환급) 제1항에도 불구하고, 이 특별약관이 효력 상실, 해지 또는 소멸된 때에는 "
    "이 특별약관의 보험료를 돌려드리지 않습니다. 단, 보장개시 전에 보험계약이 해지된 경우에는 보험료를 돌려드립니다."
)

CLAUSE_D_7_7_TEXT = (
    "제7조 (준용규정) "
    "이 특별약관에 정하지 않은 사항은 보통약관을 따릅니다."
)


def run():
    """현대해상 다이렉트 해외여행보험 특약 Clause 생성 (페이지 119-162)."""
    db = SessionLocal()

    try:
        # PolicyVersion 조회
        pv = db.query(PolicyVersion).filter(
            PolicyVersion.version_label == VERSION_LABEL
        ).first()

        if not pv:
            print(f"PolicyVersion not found: {VERSION_LABEL}")
            return

        # 1. 장애인전용보험 전환 특별약관
        print("\n=== 1. 장애인전용보험 전환 특별약관 ===")
        coverage_std_disability = get_or_create_coverage_std(
            db, 'DISABILITY_CONVERSION', '장애인전용보험 전환', '계약특약', is_base=False
        )

        coverage_disability = db.query(Coverage).filter(
            Coverage.policy_version_id == pv.policy_version_id,
            Coverage.raw_name == '장애인전용보험 전환'
        ).first()
        if not coverage_disability:
            coverage_disability = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=coverage_std_disability.coverage_std_id,
                raw_name='장애인전용보험 전환',
                definition='소득세법상 장애인전용보험으로의 전환 서비스'
            )
            db.add(coverage_disability)
            db.flush()
            print("Created Coverage: DISABILITY_CONVERSION")

        # 장애인전용 Clause들
        clauses_disability = [
            ('제1조(특별약관의 적용범위)', CLAUSE_D_1_1_TEXT, '보장조건'),
            ('제2조(제출서류)', CLAUSE_D_1_2_TEXT, '청구절차'),
            ('제3조(장애인전용보험으로의 전환)', CLAUSE_D_1_3_TEXT, '보장내용'),
            ('제4조(전환 취소)', CLAUSE_D_1_4_TEXT, '보장변경'),
            ('제5조(준용규정)', CLAUSE_D_1_5_TEXT, '기타'),
        ]
        for article_no, text, clause_type in clauses_disability:
            existing = db.query(Clause).filter(
                Clause.coverage_id == coverage_disability.coverage_id,
                Clause.article_no == article_no
            ).first()
            if not existing:
                clause = Clause(
                    policy_version_id=pv.policy_version_id,
                    coverage_id=coverage_disability.coverage_id,
                    article_no=article_no,
                    text=text,
                    clause_type=clause_type,
                    default_color='파랑',
                    page_ref='p.119-121'
                )
                db.add(clause)
                print(f"  Created Clause: {article_no}")

        # 2. 여행 동반인 보장 특별약관
        print("\n=== 2. 여행 동반인 보장 특별약관 ===")
        coverage_std_companion = get_or_create_coverage_std(
            db, 'TRAVEL_COMPANION', '여행 동반인 보장', '특약', is_base=False
        )

        coverage_companion = db.query(Coverage).filter(
            Coverage.policy_version_id == pv.policy_version_id,
            Coverage.raw_name == '여행 동반인 보장'
        ).first()
        if not coverage_companion:
            coverage_companion = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=coverage_std_companion.coverage_std_id,
                raw_name='여행 동반인 보장',
                definition='피보험자의 여행 동반인도 보장 대상 포함'
            )
            db.add(coverage_companion)
            db.flush()
            print("Created Coverage: TRAVEL_COMPANION")

        clauses_companion = [
            ('제1조(피보험자의 범위)', CLAUSE_D_2_1_TEXT, '보장조건'),
            ('제2조(준용규정)', CLAUSE_D_2_2_TEXT, '기타'),
        ]
        for article_no, text, clause_type in clauses_companion:
            existing = db.query(Clause).filter(
                Clause.coverage_id == coverage_companion.coverage_id,
                Clause.article_no == article_no
            ).first()
            if not existing:
                clause = Clause(
                    policy_version_id=pv.policy_version_id,
                    coverage_id=coverage_companion.coverage_id,
                    article_no=article_no,
                    text=text,
                    clause_type=clause_type,
                    default_color='파랑',
                    page_ref='p.122'
                )
                db.add(clause)
                print(f"  Created Clause: {article_no}")

        # 3. 공동인수 특별약관 (계약행정성이므로 클레임만 추가, CoverageStd는 생성 안함)
        print("\n=== 3. 공동인수 특별약관 ===")
        print("  건너뜀 — 계약행정성 특약 (인수비율 분담), 실제 보장과 무관")

        # 4. () 보험금만의 지급 특별약관 (구체적 내용 없음)
        print("\n=== 4. () 보험금만의 지급 특별약관 ===")
        print("  건너뜀 — 구체적 내용 없음 (빈칸, 회사별로 지정할 항목)")

        # 5. 지정대리청구서비스 특별약관
        print("\n=== 5. 지정대리청구서비스 특별약관 ===")
        coverage_std_delegation = get_or_create_coverage_std(
            db, 'DELEGATION_CLAIM', '지정대리청구서비스', '계약특약', is_base=False
        )

        coverage_delegation = db.query(Coverage).filter(
            Coverage.policy_version_id == pv.policy_version_id,
            Coverage.raw_name == '지정대리청구서비스'
        ).first()
        if not coverage_delegation:
            coverage_delegation = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=coverage_std_delegation.coverage_std_id,
                raw_name='지정대리청구서비스',
                definition='지정된 대리인이 보험금 청구 가능한 서비스'
            )
            db.add(coverage_delegation)
            db.flush()
            print("Created Coverage: DELEGATION_CLAIM")

        clauses_delegation = [
            ('제1조(적용대상)', CLAUSE_D_5_1_TEXT, '보장조건'),
            ('제2조(특약의 체결 및 소멸)', CLAUSE_D_5_2_TEXT, '보장조건'),
            ('제3조(지정대리청구인의 지정)', CLAUSE_D_5_3_TEXT, '청구절차'),
            ('제4조(지정대리청구인의 변경지정)', CLAUSE_D_5_4_TEXT, '청구절차'),
            ('제5조(보험금 지급 등의 절차)', CLAUSE_D_5_5_TEXT, '청구절차'),
            ('제6조(보험금 등 청구시 구비서류)', CLAUSE_D_5_6_TEXT, '청구절차'),
            ('제7조(준용규정)', CLAUSE_D_5_7_TEXT, '기타'),
        ]
        for article_no, text, clause_type in clauses_delegation:
            existing = db.query(Clause).filter(
                Clause.coverage_id == coverage_delegation.coverage_id,
                Clause.article_no == article_no
            ).first()
            if not existing:
                clause = Clause(
                    policy_version_id=pv.policy_version_id,
                    coverage_id=coverage_delegation.coverage_id,
                    article_no=article_no,
                    text=text,
                    clause_type=clause_type,
                    default_color='파랑',
                    page_ref='p.124-125'
                )
                db.add(clause)
                print(f"  Created Clause: {article_no}")

        # 6. 환율 특별약관 (계약행정성이므로 클레임만 추가, CoverageStd는 생성 안함)
        print("\n=== 6. 환율 특별약관 ===")
        print("  건너뜀 — 계약행정성 특약 (외화 환율 적용 기준), 실제 보장과 무관")

        # 7. 지수형 출국항공기 지연보장 특별약관
        print("\n=== 7. 지수형 출국항공기 지연보장 특별약관 ===")
        coverage_std_flight = get_or_create_coverage_std(
            db, 'FLIGHT_DELAY', '출국항공기 지연보장', '특약', is_base=False
        )

        coverage_flight = db.query(Coverage).filter(
            Coverage.policy_version_id == pv.policy_version_id,
            Coverage.raw_name == '지수형 출국항공기 지연보장'
        ).first()
        if not coverage_flight:
            coverage_flight = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=coverage_std_flight.coverage_std_id,
                raw_name='지수형 출국항공기 지연보장',
                definition='국제선 출국 항공기 지연 시 누적지연시간별 보험금 지급'
            )
            db.add(coverage_flight)
            db.flush()
            print("Created Coverage: FLIGHT_DELAY")

        clauses_flight = [
            ('제1조(보상하는 손해)', CLAUSE_D_7_1_TEXT, '보장내용'),
            ('제1조용어해설', CLAUSE_D_7_1_DEFINITION, '기타'),
            ('제2조(보상하지 않는 손해)', CLAUSE_D_7_2_TEXT, '면책'),
            ('제3조(보험금 청구시 구비서류)', CLAUSE_D_7_3_TEXT, '청구절차'),
            ('제4조(다른 보험과의 관계)', CLAUSE_D_7_4_TEXT, '기타'),
            ('제5조(특별약관의 소멸)', CLAUSE_D_7_5_TEXT, '보장변경'),
            ('제6조(보험료의 환급)', CLAUSE_D_7_6_TEXT, '기타'),
            ('제7조(준용규정)', CLAUSE_D_7_7_TEXT, '기타'),
        ]
        for article_no, text, clause_type in clauses_flight:
            existing = db.query(Clause).filter(
                Clause.coverage_id == coverage_flight.coverage_id,
                Clause.article_no == article_no
            ).first()
            if not existing:
                clause = Clause(
                    policy_version_id=pv.policy_version_id,
                    coverage_id=coverage_flight.coverage_id,
                    article_no=article_no,
                    text=text,
                    clause_type=clause_type,
                    default_color='파랑',
                    page_ref='p.126-144'
                )
                db.add(clause)
                print(f"  Created Clause: {article_no}")

        db.commit()
        print("\n✓ Successfully seeded HYUNDAI PolicyVersion special clauses (pages 119-162)")
        print("  - 장애인전용보험 전환: 5 clauses")
        print("  - 여행 동반인 보장: 2 clauses")
        print("  - 지정대리청구서비스: 7 clauses")
        print("  - 지수형 출국항공기 지연보장: 8 clauses")
        print("  - 별표/법규: 확인함, 참고용 표 및 원본 법규이라 건너뜸")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == '__main__':
    run()
