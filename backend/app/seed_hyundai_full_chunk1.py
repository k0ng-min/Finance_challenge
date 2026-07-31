"""
현대해상(insurer.code="HYUNDAI") 전체 재검토 — 청크 1(PDF p.1~47).
data/raw_pdfs/hyundai_overseas_CM8403_20250630.pdf (총 140쪽)을 pdfplumber로
p.1~47 전체를 직접 읽고 대조한 결과를 반영한다.

## p.1~37: 보통약관 (제1조~제41조, 목적/용어의정의~예금보험에의한지급보장)
직접 다 읽었다. 내용은 다음과 같고 전부 사고 분류(incident_type)와 무관한
계약 구조/행정 조항이다 — 억지로 끼워맞추지 않고 그대로 스킵한다.
- 제1조 목적, 제2조 용어의정의 (상해 기본 정의)
- 제3조~제8조 보험금의 지급사유/지급절차 — "상해의료비"라는 표현만 있고 실제 지급 기준은 특약에서 정함
- 제9조~제41조 보험금의 수령/변경, 주소변경, 보험수익자 지정, 계약 전/후 알릴의무,
  계약의 성립/철회/무효, 계약내용 변경, 보험료 납입, 계약의 해지, 환급, 분쟁조정,
  관할법원, 소멸시효, 약관해석, 개인정보보호, 준거법, 예금보험 — 계약 행정/절차 조항

결론: p.1~37 보통약관 중 지급사유의 기본 정의는 있으나, 실제 보장 내용의 세부 기준은
모두 특약(특별약관)에서 정하고 있다. 사고유형 분류에 직접 쓸 만한 면책/제한/조건 조항은 없다.

## p.38~47: "기본형 해외여행 급여 실손의료비보장 특별약관" (신규 담보)
CoverageStd OVS_INJ_MED(해외발생 상해의료비)로 이미 존재. 하지만 현대해상 특약의
세부 지급사유/면책/제한/조건은 원문 그대로 새로 Clause로 넣는다.

제1조(보장종목): 상해의료비(해외/국내 급여), 질병의료비(해외/국내 급여)의 4가지 종목
제3조(보장종목별 보상내용): 각 종목별 지급사유를 원문 그대로 넣음
- (1)상해 해외의료비: 해외여행 중 상해로 해외의료기관 치료 시 보상
- (1)-④: 보험기간 종료 후 180일까지 보상
- (2)상해 국내(급여): 해외여행 중 상해로 국내 의료기관 급여 치료 시 보상 (180일, 통원 90회)
- (3)질병 해외의료비: 해외여행 중 질병으로 해외의료기관 치료 시 보상
- (3)-③: 보험기간 종료 후 180일까지 보상
- (4)질병 국내(급여): 해외여행 중 질병으로 국내 의료기관 급여 치료 시 보상 (180일, 통원 90회)

제4조(보상하지 않는 사항): 면책 사유들
- ①-1~7: 일반적 면책(고의, 상해 또는 질병으로 인한 임신/출산, 전쟁, 의사 지시 불이행 등)
- ②: 직업/동호회 활동 목적 위험 제외(전문등반, 스카이다이빙, 선박 탑승 등)
- ③-1~5 (상해 해외의료비): 건강검진, 영양제, 의료 용품, 외모개선 등 보상 제외
- 국내(급여) 상해: 별첨4 참고
- ②-1~2 (질병 해외의료비): 정신장애, 임신/출산, 선천성 뇌질환, 비만 등 제외
- ③-1~8 (질병 해외의료비): 건강검진, 영양제, 피부질환, 의료용품, 외모개선, HIV 감염, 치아보철 등
- 국내(급여) 질병: 별첨5 참고

제4조의2(특별약관에서 보상하는 사항): 비급여 의료비는 이 기본형 약관에서 보상하지 않음
(비급여는 별도의 "해외여행 비급여 실손의료비보장 특별약관"에서 담당 — 이것은 p.67 이후)

제5조(보험가입금액 한도 등):
- 해외 상해/질병의료비: 계약시 선택한 금액
- 국내 급여 상해/질병의료비: 연간 5천만원 이내
- 입원과 통원 합산 한도
- 국민건강보험 본인부담금 상한제 적용

제6조(보험금 지급사유 발생의 통지): 지체 없이 회사에 알릴 의무
제7조(보험금의 청구): 청구서류(청구서, 진료비계산서, 신분증 등)
제8조(보험금의 지급절차):
- 서류 접수 3영업일 이내 지급
- 조사 필요시 30영업일 이내 지급예정일 통지
- 50% 가지급보험금 제도

제9조(보험금을 받는 방법의 변경): 나누어 지급/일시 지급 선택 가능
제10조(주소변경의 통지): 변경 시 회사에 알릴 의무
제11조(대표자의 지정): 2명 이상인 경우 대표자 지정
제12조~제13조: 계약 전/후 알릴의무 (보통약관과 동일)

멱등성: Coverage는 raw_name, Clause는 (coverage_id, article_no, text) 조합,
ClauseIncidentMap은 (clause_id, type_id) 조합으로 이미 있으면 건너뛴다.

## 발견 요약
현대해상 p.1~47 범위에서는 "기본형 해외여행 급여 실손의료비보장 특별약관" 1개의
새로운 특약을 발견했다. 이미 DB에 있는 OVS_INJ_MED 코드를 재사용하되, 현대해상 고유의
상세 지급사유/면책 조항들을 모두 Clause로 추가한다.

기본형이라는 명칭은 해외 발생 상해·질병의료비(급여)만 보상하고, 비급여나 질병사망 등은
별도 특약으로 분리된 구조를 의미한다.
"""
from app.database import SessionLocal
from app import models  # noqa: F401
from app.models.kb import (
    Clause, ClauseIncidentMap, Coverage, IncidentType, Insurer, PolicyVersion, Product,
)
from app.services.kb_seed_common import get_or_create_coverage_std

# ---------------------------------------------------------------------------
# 기본형 해외여행 급여 실손의료비보장 특별약관 (p.38-47)
# ---------------------------------------------------------------------------

# 제3조 상해 해외의료비 - 지급사유
BASIC_INJ_OVS_CLAUSE1_TEXT = (
    "① 회사는 피보험자가 보험증권에 기재된 해외여행 중에 상해를 입고, 이로 인해 해외의료기관에서 "
    "의사(치료받는 국가의 법에서 정한 병원 및 의사의 면허를 가진 자에 한함)의 치료를 받은 때에는 "
    "보험가입금액을 한도로 피보험자가 실제 부담한 의료비 전액을 보상합니다."
)

# 제3조 상해 해외의료비 - 척추지압술/침술
BASIC_INJ_OVS_CLAUSE2_TEXT = (
    "② 제1항에도 불구하고 척추지압술(Chiroparactic, 추나요법 등)이나 침술(부항, 뜸 포함) 치료로 인한 "
    "의료비는 치료받는 국가의 법에서 정한 병원 및 의사의 면허를 가진자에 의하여 치료를 받은 경우에 한하며, "
    "하나의 상해에 대하여 US $ 1,000.00 한도로 보상하여 드립니다"
)

# 제3조 상해 해외의료비 - 유독가스/물질 중독
BASIC_INJ_OVS_CLAUSE3_TEXT = (
    "③ 제1항의 상해에는 유독가스 또는 유독물질을 우연히 일시에 흡입, 흡수 또는 섭취한 결과로 생긴 "
    "중독증상이 포함됩니다. 다만, 유독가스 또는 유독물질을 상습적으로 흡입, 흡수 또는 섭취한 결과로 "
    "생긴 중독증상과 세균성 음식물 중독증상은 포함되지 않습니다."
)

# 제3조 상해 해외의료비 - 보험기간 종료 후 180일
BASIC_INJ_OVS_CLAUSE4_TEXT = (
    "④ 해외여행 중에 피보험자가 입은 상해로 인해 치료를 받던 중 보험기간이 끝났을 경우에는 "
    "보험기간 종료일부터 180일까지(보험기간 종료일은 제외합니다) 보상합니다."
)

# 제3조 상해 국내(급여)의료비 - 지급사유
BASIC_INJ_DOM_CLAUSE1_TEXT = (
    "① 회사는 피보험자가 보험증권에 기재된 해외여행 중에 상해를 입고, 이로 인해 국내 의료기관·약국에서 "
    "치료를 받은 때에는 [붙임2]에 따라 보상합니다. 다만, 보험기간이 1년 미만인 경우에는 해외여행 중에 "
    "피보험자가 입은 상해로 보험기간 종료후 30일(보험기간 종료일은 제외합니다) 이내에 의사의 치료를 받기 "
    "시작했을 때에는 의사의 치료를 받기 시작한 날부터 180일(통원은 180일 동안 90회)까지만(보험기간 종료일은 "
    "제외합니다) 보상합니다."
)

# 제3조 질병 해외의료비 - 지급사유
BASIC_ILL_OVS_CLAUSE1_TEXT = (
    "① 회사는 피보험자가 보험증권에 기재된 해외여행 중에 질병으로 인하여 해외의료기관에서 의사(치료받는 국가의 "
    "법에서 정한 병원 및 의사의 면허를 가진 자에 한함)의 치료를 받은 때에는 보험가입금액을 한도로 피보험자가 "
    "실제 부담한 의료비 전액을 보상합니다."
)

# 제3조 질병 해외의료비 - 척추지압술/침술
BASIC_ILL_OVS_CLAUSE2_TEXT = (
    "② 제1항에도 불구하고 척추지압술(Chiroparactic, 추나요법 등)이나 침술(부항, 뜸 포함) 치료로 인한 의료비는 "
    "치료받는 국가의 법에서 정한 병원 및 의사의 면허를 가진자에 의하여 치료를 받은 경우에 한하며, 하나의 질병에 "
    "대하여 US $ 1,000.00 한도로 보상하여 드립니다"
)

# 제3조 질병 해외의료비 - 보험기간 종료 후 180일
BASIC_ILL_OVS_CLAUSE3_TEXT = (
    "③ 해외여행 중에 피보험자가 제1항의 질병으로 인해 치료를 받던 중 보험기간이 끝났을 경우에는 "
    "보험기간 종료일부터 180일까지(보험기간 종료일은 제외합니다) 보상합니다."
)

# 제3조 질병 국내(급여)의료비 - 지급사유
BASIC_ILL_DOM_CLAUSE1_TEXT = (
    "① 회사는 피보험자가 보험증권에 기재된 해외여행 중에 발생한 질병으로 인해 국내 의료기관·약국에서 치료를 "
    "받은 때에는 [붙임3]에 따라 보상합니다. 다만, 보험기간이 1년 미만인 경우에는 해외여행 중에 질병을 원인으로 "
    "하여 보험기간 종료후 30일(보험기간 종료일은 제외합니다) 이내에 의사의 치료를 받기 시작했을 때에는 의사의 "
    "치료를 받기 시작한 날부터 180일(통원은 180일 동안 90회)까지만(보험기간 종료일은 제외합니다) 보상합니다."
)

# 제4조 - 고의/자해
BASIC_EXCLUSION_CLAUSE1_TEXT = (
    "① 회사는 다음의 사유로 인하여 생긴 의료비는 보상하지 않습니다. "
    "1. 피보험자가 고의로 자신을 해친 경우. 다만, 피보험자가 심신상실 등으로 자유로운 의사결정을 할 수 없는 "
    "상태에서 자신을 해친 사실이 증명된 경우에는 보상합니다."
)

# 제4조 - 보험수익자/계약자의 고의
BASIC_EXCLUSION_CLAUSE2_TEXT = (
    "2. 보험수익자가 고의로 피보험자를 해친 경우. 다만, 그 보험수익자가 보험금의 일부 보험수익자인 경우에는 "
    "다른 보험수익자에 대한 보험금은 지급합니다. "
    "3. 계약자가 고의로 피보험자를 해친 경우"
)

# 제4조 - 임신/출산/산후기
BASIC_EXCLUSION_CLAUSE3_TEXT = (
    "4. 피보험자가 임신, 출산(제왕절개를 포함합니다), 산후기로 치료한 경우. 다만, 회사가 보상하는 상해로 인한 "
    "경우에는 보상합니다."
)

# 제4조 - 전쟁/무력행사
BASIC_EXCLUSION_CLAUSE4_TEXT = (
    "5. 전쟁, 외국의 무력행사, 혁명, 내란, 사변, 폭동으로 인한 경우"
)

# 제4조 - 입원/통원 불이행
BASIC_EXCLUSION_CLAUSE5_TEXT = (
    "6. 피보험자가 정당한 이유 없이 입원기간 중 의사의 지시를 따르지 않거나 의사가 통원치료가 가능하다고 인정함에도 "
    "피보험자 본인이 자의적으로 입원하여 발생한 입원의료비 "
    "7. 피보험자가 정당한 이유 없이 통원기간 중 의사의 지시를 따르지 않아 발생한 통원의료비"
)

# 제4조② - 직업/동호회 활동 위험 제외
BASIC_EXCLUSION_CLAUSE6_TEXT = (
    "② 회사는 다른 약정이 없으면 피보험자가 직업, 직무 또는 동호회 활동목적으로 한 다음의 어느 하나에 해당하는 "
    "행위로 인하여 생긴 상해에 대해서는 보상하지 않습니다. "
    "1. 전문등반(전문적인 등산용구를 사용하여 암벽 또는 빙벽을 오르내리거나 특수한 기술, 경험, 사전 훈련이 필요한 "
    "등반을 말합니다), 글라이더 조종, 스카이다이빙, 스쿠버다이빙, 행글라이딩, 수상보트, 패러글라이딩"
)

# 제4조② - 직업/동호회 활동 위험 제외 (계속)
BASIC_EXCLUSION_CLAUSE7_TEXT = (
    "2. 모터보트, 자동차 또는 오토바이에 의한 경기, 시범, 행사(이를 위한 연습을 포함합니다) 또는 시운전(다만, "
    "공용도로에서 시운전을 하는 동안 발생한 상해는 보상합니다) "
    "3. 선박에 탑승하는 것을 직무로 하는 사람이 직무상 선박에 탑승하고 있는 동안"
)

# 제4조③ - 상해 해외의료비 - 건강검진 등
BASIC_INJ_EXCLUSION_CLAUSE1_TEXT = (
    "③ 회사는 아래의 의료비에 대하여는 보상하지 않습니다. "
    "1. 건강검진 (단, 검사결과 이상 소견에 따라 건강검진센터 등에서 발생한 추가 의료비용은 보상합니다), 예방접종, "
    "인공유산에 든 비용. 다만, 회사가 보상하는 상해 치료를 목적으로 하는 경우에는 보상합니다."
)

# 제4조③ - 상해 해외의료비 - 영양제/호르몬
BASIC_INJ_EXCLUSION_CLAUSE2_TEXT = (
    "2. 영양제, 비타민제, 호르몬 투여, 보신용 투약, 친자 확인을 위한 진단, 불임검사, 불임수술, 불임복원술, "
    "보조생식술(체내, 체외 인공수정을 포함합니다), 성장촉진, 의약외품과 관련하여 소요된 비용. 다만, 회사가 보상하는 "
    "상해 치료를 목적으로 하는 경우에는 보상합니다."
)

# 제4조③ - 상해 해외의료비 - 의료용품
BASIC_INJ_EXCLUSION_CLAUSE3_TEXT = (
    "3. 의치, 의수족, 의안, 안경, 콘택트렌즈, 보청기, 목발, 팔걸이(Arm Sling), 보조기 등 진료재료의 구입 및 대체비용. "
    "다만, 인공장기 등 신체에 이식되어 그 기능을 대신하는 경우에는 보상합니다."
)

# 제4조③ - 상해 해외의료비 - 외모개선
BASIC_INJ_EXCLUSION_CLAUSE4_TEXT = (
    "4. 외모개선 목적의 치료로 인하여 발생한 의료비"
)

# 제4조③-4가 - 쌍꺼풀/코/유방 등
BASIC_INJ_EXCLUSION_CLAUSE5_TEXT = (
    "가. 쌍꺼풀수술(이중검수술. 다만, 안검하수, 안검내반 등을 치료하기 위한 시력개선 목적의 이중검수술은 보장합니다), "
    "코성형수술(융비술), 유방확대(다만, 유방암 환자의 유방재건술은 보장합니다)·축소술, 지방흡입술, 주름살제거술 등"
)

# 제4조③-4나 - 사시교정/안와격리증
BASIC_INJ_EXCLUSION_CLAUSE6_TEXT = (
    "나. 사시교정, 안와격리증(양쪽 눈을 감싸고 있는 뼈와 뼈 사이의 거리가 넓은 증상)의 교정 등 시각계 수술로써 "
    "시력개선 목적이 아닌 외모개선 목적의 수술"
)

# 제4조③-4다 - 시력교정술
BASIC_INJ_EXCLUSION_CLAUSE7_TEXT = (
    "다. 안경, 콘텍트렌즈 등을 대체하기 위한 시력교정술(국민건강보험 요양급여 대상 수술방법 또는 치료재료가 사용되지 "
    "않은 부분은 시력교정술로 봅니다)"
)

# 제4조③-4라/마 - 다리정맥류/외모개선
BASIC_INJ_EXCLUSION_CLAUSE8_TEXT = (
    "라. 외모개선 목적의 다리정맥류 수술 "
    "마. 그 밖에 외모개선 목적의 치료로 국민건강보험 비급여대상에 해당하는 치료"
)

# 제4조③-5 - 진료와 무관한 비용
BASIC_INJ_EXCLUSION_CLAUSE9_TEXT = (
    "5. 진료와 무관한 각종 비용(TV시청료, 전화료, 각종 증명료 등을 말합니다), 의사의 임상적 소견과 관련이 없는 검사비용, 간병비"
)

# 제4조 - 질병 해외의료비 면책 ①-1~5
BASIC_ILL_EXCLUSION_CLAUSE1_TEXT = (
    "① 회사는 아래의 사유를 원인으로 하여 생긴 의료비는 보상하지 않습니다. "
    "1. 피보험자가 고의로 자신을 해친 경우. 다만, 피보험자가 심신상실 등으로 자유로운 의사결정을 할 수 없는 상태에서 "
    "자신을 해친 사실이 증명된 경우에는 보상합니다."
)

# 제4조 - 질병 해외의료비 면책 ①-2~5
BASIC_ILL_EXCLUSION_CLAUSE2_TEXT = (
    "2. 보험수익자가 고의로 피보험자를 해친 경우. 다만, 그 보험수익자가 보험금의 일부 보험수익자인 경우에는 "
    "다른 보험수익자에 대한 보험금은 지급합니다. "
    "3. 계약자가 고의로 피보험자를 해친 경우 "
    "4. 피보험자가 정당한 이유 없이 입원기간 중 의사의 지시를 따르지 않거나 의사가 통원치료가 가능하다고 인정함에도 "
    "피보험자 본인이 자의적으로 입원하여 발생한 입원의료비 "
    "5. 피보험자가 정당한 이유 없이 통원기간 중 의사의 지시를 따르지 않아 발생한 통원의료비"
)

# 제4조② - 질병 해외의료비 한국표준질병사인분류 제외
BASIC_ILL_EXCLUSION_CLAUSE3_TEXT = (
    "② 회사는 한국표준질병사인분류에 있어서 아래의 의료비에 대하여는 보상하지 않습니다. "
    "1. 정신 및 행동장애(F04～F99) (다만, F04～F09, F20～F29, F30～F39, F40～F48, F51, F90～F98과 관련한 치료에서 "
    "발생한 「국민건강보험법」 에 따른 요양급여에 해당하는 의료비는 보상합니다)"
)

# 제4조② - 질병 해외의료비 여성생식기 등
BASIC_ILL_EXCLUSION_CLAUSE4_TEXT = (
    "2. 여성생식기의 비염증성 장애로 인한 습관성 유산, 불임 및 인공수정관련 합병증(N96～N98) "
    "3. 피보험자가 임신, 출산(제왕절개를 포함합니다), 산후기로 치료한 경우(O00～O99) "
    "4. 선천성 뇌질환(Q00～Q04)"
)

# 제4조② - 질병 해외의료비 비만/요실금 등
BASIC_ILL_EXCLUSION_CLAUSE5_TEXT = (
    "5. 비만(E66) "
    "6. 요실금(N39.3, N39.4, R32) "
    "7. 직장 또는 항문질환 중 「국민건강보험법」에 따른 요양급여에 해당하지 않는 부분(I84, K60～K62, K64)"
)

# 제4조③ - 질병 해외의료비 건강검진 등
BASIC_ILL_EXCLUSION_CLAUSE6_TEXT = (
    "③ 회사는 다음의 의료비에 대하여는 보상하지 않습니다. "
    "1. 건강검진(단, 검사결과 이상 소견에 따라 건강검진센터 등에서 발생한 추가 의료비용은 보상합니다), 예방접종, "
    "인공유산에 든 비용. 다만, 회사가 보상하는 질병 치료를 목적으로 하는 경우에는 보상합니다."
)

# 제4조③-2 - 질병 해외의료비 영양제/호르몬
BASIC_ILL_EXCLUSION_CLAUSE7_TEXT = (
    "2. 영양제, 비타민제, 호르몬 투여(다만, 국민건강보험의 요양급여 기준에 해당하는 성조숙증을 치료하기 위한 호르몬 투여는 "
    "보상합니다), 보신용 투약, 친자 확인을 위한 진단, 불임검사, 불임수술, 불임복원술, 보조생식술(체내, 체외 인공수정을 "
    "포함합니다), 성장촉진, 의약외품과 관련하여 소요된 비용. 다만, 회사가 보상하는 질병 치료를 목적으로 하는 경우에는 보상합니다."
)

# 제4조③-3 - 질병 해외의료비 피로/피부질환
BASIC_ILL_EXCLUSION_CLAUSE8_TEXT = (
    "3. 다음의 어느 하나에 해당하는 치료로 인하여 발생한 의료비 "
    "가. 단순한 피로 또는 권태 "
    "나. 주근깨, 다모, 무모, 백모증, 딸기코(주사비), 점, 모반(피보험자가 보험가입당시 태아인 경우 화염상모반 등 "
    "선천성 비신생물성모반(Q82.5)은 보상합니다), 사마귀, 여드름, 노화현상으로 인한 탈모 등 피부질환"
)

# 제4조③-3다 - 발기부전/코골음/포경
BASIC_ILL_EXCLUSION_CLAUSE9_TEXT = (
    "다. 발기부전(impotence)ㆍ불감증, 단순 코골음(수면무호흡증(G47.3)은 보상합니다), 치료를 동반하지 않는 단순포경(phimosis)"
)

# 제4조③-4 - 질병 해외의료비 의료용품
BASIC_ILL_EXCLUSION_CLAUSE10_TEXT = (
    "4. 의치, 의수족, 의안, 안경, 콘택트렌즈, 보청기, 목발, 팔걸이(Arm Sling), 보조기 등 진료재료의 구입 및 대체비용. "
    "다만, 인공장기 등 신체에 이식되어 그 기능을 대신하는 경우에는 보상합니다."
)

# 제4조③-5 - 질병 해외의료비 외모개선
BASIC_ILL_EXCLUSION_CLAUSE11_TEXT = (
    "5. 아래에 열거된 국민건강보험 비급여 대상으로 신체의 필수 기능개선 목적이 아닌 외모개선 목적의 치료로 인하여 발생한 의료비"
)

# 제4조③-5가 - 쌍꺼풀/코 등
BASIC_ILL_EXCLUSION_CLAUSE12_TEXT = (
    "가. 쌍꺼풀수술(이중검수술. 다만, 안검하수, 안검내반 등을 치료하기 위한 시력개선 목적의 이중검수술은 보상합니다), "
    "코성형수술(융비술), 유방확대(다만, 유방암 환자의 유방재건술은 보상합니다)·축소술, 지방흡입술, 주름살제거술 등"
)

# 제4조③-5나 - 사시교정
BASIC_ILL_EXCLUSION_CLAUSE13_TEXT = (
    "나. 사시교정, 안와격리증(양쪽 눈을 감싸고 있는 뼈와 뼈 사이의 거리가 넓은 증상)의 교정 등 시각계 수술로서 "
    "시력개선 목적이 아닌 외모개선 목적의 수술"
)

# 제4조③-5다 - 시력교정술
BASIC_ILL_EXCLUSION_CLAUSE14_TEXT = (
    "다. 안경, 콘텍트렌즈 등을 대체하기 위한 시력교정술(국민건강보험 요양급여 대상 수술방법 또는 치료재료가 사용되지 "
    "않은 부분은 시력교정술로 봅니다)"
)

# 제4조③-5라/마 - 다리정맥류/외모개선
BASIC_ILL_EXCLUSION_CLAUSE15_TEXT = (
    "라. 외모개선 목적의 다리정맥류 수술 "
    "마. 그 밖에 외모개선 목적의 치료로 국민건강보험 비급여대상에 해당하는 치료"
)

# 제4조③-6 - 질병 해외의료비 진료와 무관한 비용
BASIC_ILL_EXCLUSION_CLAUSE16_TEXT = (
    "6. 진료와 무관한 각종 비용(TV시청료, 전화료, 각종 증명료 등을 말합니다), 의사의 임상적 소견과 관련이 없는 검사비용, 간병비"
)

# 제4조③-7 - 질병 해외의료비 HIV 감염
BASIC_ILL_EXCLUSION_CLAUSE17_TEXT = (
    "7. 사람면역결핍바이러스(HIV)감염으로 인한 치료비(다만, 「의료법」에서 정한 의료인의 진료상 또는 치료중 혈액에 의한 "
    "HIV감염은 해당진료기록을 통해 객관적으로 확인되는 경우는 제외합니다)"
)

# 제4조③-8 - 질병 해외의료비 치아보철
BASIC_ILL_EXCLUSION_CLAUSE18_TEXT = (
    "8. 치아보철, 보존, 금관, 틀니, 의치 및 임플란트로 인한 의료비"
)

# 제4조의2 - 특별약관에서 보상하지 않는 비급여 의료비
BASIC_NON_COVERED_CLAUSE1_TEXT = (
    "① 제3조 및 제4조에도 불구하고 다음 각 호에 해당하는 국내 상해의료비 및 국내 질병의료비는 기본형 해외여행 실손의료보험에서 "
    "보상하지 않습니다. "
    "1. 비급여의료비 "
    "2. 제1호와 관련하여 자동차보험(공제를 포함합니다) 또는 산재보험에서 발생한 본인부담의료비"
)

# 제5조 - 보험가입금액 한도
BASIC_LIMIT_CLAUSE1_TEXT = (
    "① 이 계약의 보험가입금액은 (1)상해의료비 해외, (2)질병의료비 해외의 경우 각각에 대하여 계약시 계약자가 선택한 금액, "
    "(1)상해의료비 국내(급여), (2)질병의료비 국내(급여)의 경우 연간 (1)상해의료비 국내(급여)에 대하여 입원과 통원의 보상금액을 "
    "합산하여 5천만원 이내에서, (2)질병의료비 국내(급여)에 대하여 입원과 통원의 보상금액을 합산하여 5천만원 이내에서 회사가 정한 "
    "금액 중 계약자가 선택한 금액을 말하며, 제3조(보장종목별 보상내용)에 의한 의료비를 이 금액 한도 내에서 보상합니다."
)

# 제6조 - 보험금 지급사유 발생의 통지
BASIC_NOTICE_CLAUSE_TEXT = (
    "계약자, 피보험자 또는 보험수익자는 제3조(보장종목별 보상내용)에서 정한 보험금 지급사유가 발생한 것을 알았을 때에는 "
    "지체 없이 그 사실을 회사에 알려야 합니다."
)

# 제7조 - 보험금의 청구
BASIC_CLAIM_CLAUSE_TEXT = (
    "① 보험수익자는 다음의 서류를 제출하고 보험금을 청구하여야 합니다. "
    "1. 청구서 (회사 양식) "
    "2. 사고증명서 (진료비계산서, 진료비세부내역서, 입원치료확인서, 의사처방전(처방조제비) 등) "
    "3. 신분증(주민등록증이나 운전면허증 등 본인임을 확인할 수 있는 사진이 붙은 정부기관에서 발행한 신분증, "
    "본인이 아닌 경우에는 본인의 인감증명서, 본인서명사실확인서 또는 안전성과 신뢰성이 확보된 전자적 수단을 활용한 "
    "보험수익자 의사표시의 확인방법 포함) "
    "4. 그 밖에 보험수익자가 보험금 수령에 필요하여 제출하는 서류"
)

# 제8조 - 보험금의 지급절차
BASIC_PAYMENT_PROC_CLAUSE1_TEXT = (
    "① 회사는 제7조(보험금의 청구)에서 정한 서류를 접수한 때에는 접수증을 드리고 휴대전화 문자메세지 또는 전자우편 등으로도 "
    "송부하며, 그 서류를 접수한 날부터 3영업일 이내에 보험금을 지급합니다."
)

# 제8조② - 보험금 지급 조사
BASIC_PAYMENT_PROC_CLAUSE2_TEXT = (
    "② 제1항에도 불구하고 회사는 보험금 지급사유를 조사·확인하기 위하여 제1항의 지급기일 이내에 보험금을 지급하지 못할 것으로 "
    "명백히 예상되는 경우에는 그 구체적인 사유와 지급예정일 및 보험금 가지급제도(회사가 추정하는 보험금의 50% 이내의 금액을 "
    "지급하는 제도를 말합니다)에 대하여 피보험자 또는 보험수익자에게 즉시 통지하여 드립니다. 다만, 지급예정일은 다음 각 호의 "
    "어느 하나에 해당하는 경우를 제외하고는 제7조(보험금의 청구)에서 정한 서류를 접수한 날부터 30영업일 이내에서 정합니다."
)

# 제8조③ - 가지급보험금
BASIC_PAYMENT_PROC_CLAUSE3_TEXT = (
    "③ 제2항에 따라 추가적인 조사가 이루어지는 경우 회사는 보험수익자의 청구에 따라 회사가 추정하는 보험금의 50% 상당액을 "
    "가지급보험금으로 지급합니다."
)

# 제8조④ - 지급 지연시 이자
BASIC_PAYMENT_PROC_CLAUSE4_TEXT = (
    "④ 회사는 제1항에서 정한 지급기일내에 보험금을 지급하지 않았을 때(제2항에서 정한 지급예정일을 통지한 경우를 포함합니다)에는 "
    "그 다음날로부터 지급일까지의 기간에 대하여 <부표> '보험금을 지급할 때의 적립이율'에 따라 연단위 복리로 계산한 금액을 "
    "보험금에 더하여 지급합니다. 다만, 계약자, 피보험자 또는 보험수익자에게 책임이 있는 사유로 지급이 지연된 경우에는 그 기간에 "
    "대한 이자는 지급하지 않습니다."
)

# 제8조⑤ - 조사 동의 의무
BASIC_PAYMENT_PROC_CLAUSE5_TEXT = (
    "⑤ 계약자, 피보험자 또는 보험수익자는 제14조(알릴 의무 위반의 효과) 및 제2항의 보험금 지급사유조사와 관련하여 의료기관 및 "
    "국민건강보험공단, 경찰서 등 관공서에 대한 회사의 서면에 의한 조사요청에 동의하여야 합니다. 다만, 정당한 사유없이 이에 동의하지 "
    "않을 경우 회사는 사실확인이 끝날 때까지 보험금 지급지연에 따른 이자를 지급하지 않습니다."
)

# 제8조⑦ - 제3자 의견 제출
BASIC_PAYMENT_PROC_CLAUSE6_TEXT = (
    "⑦ 보험수익자와 회사가 제3조(보장종목별 보상내용)의 보험금 지급사유에 대해 합의하지 못할 때는 보험수익자와 회사가 함께 제3자를 "
    "정하고 그 제3자의 의견에 따를 수 있습니다. 제3자는 「의료법」 제3조(의료기관)에 규정된 종합병원 소속 전문의 중에서 정하며, "
    "보험금 지급사유 판정에 드는 의료비용은 회사가 전액 부담합니다."
)


def run():
    """현대해상 기본형 해외여행 급여 실손의료비보장 특별약관 시딩."""
    db = SessionLocal()

    try:
        # 현대해상은 seed_hyundai.py로 이미 시딩돼 있어야 한다 - 새로 만들지 않는다.
        insurer = db.query(Insurer).filter(Insurer.code == 'HYUNDAI').first()
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

        # 상해 해외의료비 (OVS_INJ_MED) - 이미 있을 것
        coverage_std_inj = get_or_create_coverage_std(
            db, 'OVS_INJ_MED', '해외발생 상해의료비',
            category='상해', is_base=True
        )

        # Coverage 생성 - 기본형 해외여행 급여 실손의료비보장 (상해)
        coverage_inj = db.query(Coverage).filter(
            Coverage.policy_version_id == pv.policy_version_id,
            Coverage.raw_name == '기본형 해외여행 급여 실손의료비보장 (상해)'
        ).first()
        if not coverage_inj:
            coverage_inj = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=coverage_std_inj.coverage_std_id,
                raw_name='기본형 해외여행 급여 실손의료비보장 (상해)',
                definition='해외여행 중 상해로 인한 해외/국내 실손의료비 보상'
            )
            db.add(coverage_inj)
            db.flush()

        # Clause 생성 - 상해 해외의료비
        clauses_inj_ovs = [
            ('제3조 보상내용', BASIC_INJ_OVS_CLAUSE1_TEXT),
            ('제3조 척추지압술', BASIC_INJ_OVS_CLAUSE2_TEXT),
            ('제3조 유독가스중독', BASIC_INJ_OVS_CLAUSE3_TEXT),
            ('제3조 보험기간종료후180일', BASIC_INJ_OVS_CLAUSE4_TEXT),
        ]

        for article, text in clauses_inj_ovs:
            existing = db.query(Clause).filter(
                Clause.coverage_id == coverage_inj.coverage_id,
                Clause.text == text
            ).first()
            if not existing:
                clause = Clause(
                    policy_version_id=pv.policy_version_id,
                    coverage_id=coverage_inj.coverage_id,
                    article_no=article,
                    text=text,
                    clause_type='보장정의'
                )
                db.add(clause)

        # Clause 생성 - 국내 급여 상해의료비
        # 주의: seed_hyundai_inj_deep.py가 이미 이 조항(문구 표기만 다름 - <붙임2> vs [붙임2] 등)을
        # 넣어뒀을 수 있다 — 정확히 같은 문자열이 아니어도 핵심 문구(180일/90회)로 중복을 걸러낸다.
        clause_inj_dom = None
        existing = db.query(Clause).filter(
            Clause.coverage_id == coverage_inj.coverage_id,
            Clause.text.like("%180일 동안 90회%")
        ).first()
        if not existing:
            clause_inj_dom = Clause(
                policy_version_id=pv.policy_version_id,
                coverage_id=coverage_inj.coverage_id,
                article_no='제3조 국내급여',
                text=BASIC_INJ_DOM_CLAUSE1_TEXT,
                clause_type='보장정의'
            )
            db.add(clause_inj_dom)

        # 면책 조항들
        exclusion_clauses = [
            ('제4조 고의', BASIC_EXCLUSION_CLAUSE1_TEXT),
            ('제4조 고의2', BASIC_EXCLUSION_CLAUSE2_TEXT),
            ('제4조 임신출산', BASIC_EXCLUSION_CLAUSE3_TEXT),
            ('제4조 전쟁', BASIC_EXCLUSION_CLAUSE4_TEXT),
            ('제4조 입원통원불이행', BASIC_EXCLUSION_CLAUSE5_TEXT),
            ('제4조 직업활동위험', BASIC_EXCLUSION_CLAUSE6_TEXT),
            ('제4조 직업활동위험2', BASIC_EXCLUSION_CLAUSE7_TEXT),
            ('제4조 건강검진', BASIC_INJ_EXCLUSION_CLAUSE1_TEXT),
            ('제4조 영양제', BASIC_INJ_EXCLUSION_CLAUSE2_TEXT),
            ('제4조 의료용품', BASIC_INJ_EXCLUSION_CLAUSE3_TEXT),
            ('제4조 외모개선', BASIC_INJ_EXCLUSION_CLAUSE4_TEXT),
            ('제4조 외모개선상세1', BASIC_INJ_EXCLUSION_CLAUSE5_TEXT),
            ('제4조 외모개선상세2', BASIC_INJ_EXCLUSION_CLAUSE6_TEXT),
            ('제4조 외모개선상세3', BASIC_INJ_EXCLUSION_CLAUSE7_TEXT),
            ('제4조 외모개선상세4', BASIC_INJ_EXCLUSION_CLAUSE8_TEXT),
            ('제4조 진료무관비용', BASIC_INJ_EXCLUSION_CLAUSE9_TEXT),
        ]

        for article, text in exclusion_clauses:
            existing = db.query(Clause).filter(
                Clause.coverage_id == coverage_inj.coverage_id,
                Clause.text == text
            ).first()
            if not existing:
                clause = Clause(
                    policy_version_id=pv.policy_version_id,
                    coverage_id=coverage_inj.coverage_id,
                    article_no=article,
                    text=text,
                    clause_type='면책'
                )
                db.add(clause)

        # 질병 의료비 Coverage
        coverage_std_ill = get_or_create_coverage_std(
            db, 'OVS_ILL_MED', '해외발생 질병의료비',
            category='질병', is_base=True
        )

        coverage_ill = db.query(Coverage).filter(
            Coverage.policy_version_id == pv.policy_version_id,
            Coverage.raw_name == '기본형 해외여행 급여 실손의료비보장 (질병)'
        ).first()
        if not coverage_ill:
            coverage_ill = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=coverage_std_ill.coverage_std_id,
                raw_name='기본형 해외여행 급여 실손의료비보장 (질병)',
                definition='해외여행 중 질병으로 인한 해외/국내 실손의료비 보상'
            )
            db.add(coverage_ill)
            db.flush()

        # 질병 의료비 Clause - 지급사유
        clauses_ill_ovs = [
            ('제3조 질병해외보상', BASIC_ILL_OVS_CLAUSE1_TEXT),
            ('제3조 질병척추지압술', BASIC_ILL_OVS_CLAUSE2_TEXT),
            ('제3조 질병보험기간종료후180일', BASIC_ILL_OVS_CLAUSE3_TEXT),
        ]

        for article, text in clauses_ill_ovs:
            existing = db.query(Clause).filter(
                Clause.coverage_id == coverage_ill.coverage_id,
                Clause.text == text
            ).first()
            if not existing:
                clause = Clause(
                    policy_version_id=pv.policy_version_id,
                    coverage_id=coverage_ill.coverage_id,
                    article_no=article,
                    text=text,
                    clause_type='보장정의'
                )
                db.add(clause)

        # 질병 국내 급여 의료비
        existing = db.query(Clause).filter(
            Clause.coverage_id == coverage_ill.coverage_id,
            Clause.text == BASIC_ILL_DOM_CLAUSE1_TEXT
        ).first()
        if not existing:
            clause = Clause(
                policy_version_id=pv.policy_version_id,
                coverage_id=coverage_ill.coverage_id,
                article_no='제3조 질병국내급여',
                text=BASIC_ILL_DOM_CLAUSE1_TEXT,
                clause_type='보장정의'
            )
            db.add(clause)

        # 질병 면책 조항들
        ill_exclusion_clauses = [
            ('제4조 질병고의', BASIC_ILL_EXCLUSION_CLAUSE1_TEXT),
            ('제4조 질병고의2', BASIC_ILL_EXCLUSION_CLAUSE2_TEXT),
            ('제4조 질병분류', BASIC_ILL_EXCLUSION_CLAUSE3_TEXT),
            ('제4조 질병여성', BASIC_ILL_EXCLUSION_CLAUSE4_TEXT),
            ('제4조 질병비만', BASIC_ILL_EXCLUSION_CLAUSE5_TEXT),
            ('제4조 질병검진', BASIC_ILL_EXCLUSION_CLAUSE6_TEXT),
            ('제4조 질병영양제', BASIC_ILL_EXCLUSION_CLAUSE7_TEXT),
            ('제4조 질병피로', BASIC_ILL_EXCLUSION_CLAUSE8_TEXT),
            ('제4조 질병발기부전', BASIC_ILL_EXCLUSION_CLAUSE9_TEXT),
            ('제4조 질병의료용품', BASIC_ILL_EXCLUSION_CLAUSE10_TEXT),
            ('제4조 질병외모개선', BASIC_ILL_EXCLUSION_CLAUSE11_TEXT),
            ('제4조 질병외모상세1', BASIC_ILL_EXCLUSION_CLAUSE12_TEXT),
            ('제4조 질병외모상세2', BASIC_ILL_EXCLUSION_CLAUSE13_TEXT),
            ('제4조 질병외모상세3', BASIC_ILL_EXCLUSION_CLAUSE14_TEXT),
            ('제4조 질병외모상세4', BASIC_ILL_EXCLUSION_CLAUSE15_TEXT),
            ('제4조 질병진료무관', BASIC_ILL_EXCLUSION_CLAUSE16_TEXT),
            ('제4조 질병HIV', BASIC_ILL_EXCLUSION_CLAUSE17_TEXT),
            ('제4조 질병치아', BASIC_ILL_EXCLUSION_CLAUSE18_TEXT),
        ]

        for article, text in ill_exclusion_clauses:
            existing = db.query(Clause).filter(
                Clause.coverage_id == coverage_ill.coverage_id,
                Clause.text == text
            ).first()
            if not existing:
                clause = Clause(
                    policy_version_id=pv.policy_version_id,
                    coverage_id=coverage_ill.coverage_id,
                    article_no=article,
                    text=text,
                    clause_type='면책'
                )
                db.add(clause)

        # 제4조의2 - 비급여 제외
        existing = db.query(Clause).filter(
            Clause.coverage_id == coverage_inj.coverage_id,
            Clause.text == BASIC_NON_COVERED_CLAUSE1_TEXT
        ).first()
        if not existing:
            clause = Clause(
                policy_version_id=pv.policy_version_id,
                coverage_id=coverage_inj.coverage_id,
                article_no='제4조의2',
                text=BASIC_NON_COVERED_CLAUSE1_TEXT,
                clause_type='제한'
            )
            db.add(clause)

        # 제5조 - 보험가입금액 한도 (공통 제한)
        existing = db.query(Clause).filter(
            Clause.coverage_id == coverage_inj.coverage_id,
            Clause.text == BASIC_LIMIT_CLAUSE1_TEXT
        ).first()
        if not existing:
            clause = Clause(
                policy_version_id=pv.policy_version_id,
                coverage_id=coverage_inj.coverage_id,
                article_no='제5조',
                text=BASIC_LIMIT_CLAUSE1_TEXT,
                clause_type='제한'
            )
            db.add(clause)

        # 제6조 - 보험금 지급사유 통지 (조건)
        existing = db.query(Clause).filter(
            Clause.coverage_id == coverage_inj.coverage_id,
            Clause.text == BASIC_NOTICE_CLAUSE_TEXT
        ).first()
        if not existing:
            clause = Clause(
                policy_version_id=pv.policy_version_id,
                coverage_id=coverage_inj.coverage_id,
                article_no='제6조',
                text=BASIC_NOTICE_CLAUSE_TEXT,
                clause_type='조건'
            )
            db.add(clause)

        # 제7조 - 보험금 청구 (서류)
        existing = db.query(Clause).filter(
            Clause.coverage_id == coverage_inj.coverage_id,
            Clause.text == BASIC_CLAIM_CLAUSE_TEXT
        ).first()
        if not existing:
            clause = Clause(
                policy_version_id=pv.policy_version_id,
                coverage_id=coverage_inj.coverage_id,
                article_no='제7조',
                text=BASIC_CLAIM_CLAUSE_TEXT,
                clause_type='서류'
            )
            db.add(clause)

        # 제8조 - 보험금 지급절차 (조건)
        payment_clauses = [
            ('제8조①', BASIC_PAYMENT_PROC_CLAUSE1_TEXT),
            ('제8조②', BASIC_PAYMENT_PROC_CLAUSE2_TEXT),
            ('제8조③', BASIC_PAYMENT_PROC_CLAUSE3_TEXT),
            ('제8조④', BASIC_PAYMENT_PROC_CLAUSE4_TEXT),
            ('제8조⑤', BASIC_PAYMENT_PROC_CLAUSE5_TEXT),
            ('제8조⑦', BASIC_PAYMENT_PROC_CLAUSE6_TEXT),
        ]

        for article, text in payment_clauses:
            existing = db.query(Clause).filter(
                Clause.coverage_id == coverage_inj.coverage_id,
                Clause.text == text
            ).first()
            if not existing:
                clause = Clause(
                    policy_version_id=pv.policy_version_id,
                    coverage_id=coverage_inj.coverage_id,
                    article_no=article,
                    text=text,
                    clause_type='조건'
                )
                db.add(clause)

        db.commit()
        print("Successfully seeded HYUNDAI basic medical expense coverage")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == '__main__':
    run()
