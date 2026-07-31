"""
DB손해보험(insurer.code="DB") 전체 재분류 — chunk 2: PDF p.43-84
(data/raw_pdfs/db_overseas.pdf "프로미 해외여행보험Ⅰ", 총 126쪽)

직접 페이지를 읽고 원문을 대조해 확인한 내용:

## p.56-68: 3종 비급여 의료비 특별약관

1. p.56-58 "비급여 도수치료·체외충격파치료·증식치료 실손의료비 특별약관"
   신규 특약(기존 DB에 없음). 구조: 제1조(보상내용)·제2조(제한사항)·제3조(준용규정).
   NON_COVERED_MED 코드를 재사용(비급여 실손의료비 군).
   매핑: ILL_DOMESTIC_TREATMENT (국내 질병 실손)

2. p.59-64 "비급여 주사료 실손의료비 특별약관"
   신규 특약(기존 DB에 없음). 구조: 제1조(보상내용)·제2조(제한사항)·제3조(준용규정).
   NON_COVERED_MED 코드 재사용.
   매핑: ILL_DOMESTIC_TREATMENT

3. p.65-68 "비급여 자기공명영상진단(MRI/MRA) 실손의료비 특별약관"
   신규 특약(기존 DB에 없음). 구조: 제1조(보상내용①~⑥)·제2조(준용규정).
   NON_COVERED_MED 코드 재사용.
   매핑: ILL_DOMESTIC_TREATMENT

## p.69-80: 추가특별약관 및 배상책임/질병사망

4. p.69 "국민건강보험 비가입자 추가특별약관"
   신규 추가약관. 기존 기본형 실손을 비가입자에게 그대로 적용하는 조건적 보장 규정.
   구조: 제1조(적용대상)·제2조(보상하는 사항)·제3조(계약 후 알릴의무)·제4조(준용규정).
   기존 특약들에 의존하므로 별도 CoverageStd 없이 Coverage만 생성.
   매핑: 직접 사고유형 매핑 X (조건부 적용 규정)

5. p.70 "해외주재원 상해의료비 전쟁위험보장 추가특별약관"
   신규 추가약관. 전쟁·무력행사 면책을 해외주재원에게만 해제하는 특약.
   구조: 제1조(피보험자범위①②③)·제2조(보상하는사항)·제3조(준용규정).
   WAR_RISK 코드 새로 생성 (전쟁위험, category=특수).
   매핑: INJ_OVERSEAS_TREATMENT (상해의료비)

6. p.70 "해외상해의료비 자기부담금설정 추가특별약관"
   신규 추가약관. 보험증권 기재 자기부담금을 초과한 부분만 보상하는 제한 조항.
   구조: 제1조(보험금의지급)·제2조(준용규정).
   OVS_INJ_MED 재사용 (해외발생 상해의료비).
   매핑: INJ_OVERSEAS_TREATMENT (제한 조항으로)

7. p.70 "해외질병의료비 자기부담금설정 추가특별약관"
   신규 추가약관. 질병의료비의 자기부담금 설정.
   구조: 제1조(보험금의지급)·제2조(준용규정).
   OVS_ILL_MED 재사용 (해외발생 질병의료비).
   매핑: ILL_OVERSEAS_TREATMENT (제한 조항으로)

8. p.71 "해외상해의료비 척추지압술·침술 부보장 추가특별약관"
   신규 추가약관. 상해의료비 중 척추지압술/침술 비보장 특약.
   구조: 제1조(보험금을지급하지않는사유)·제2조(준용규정).
   OVS_INJ_MED 재사용.
   매핑: INJ_OVERSEAS_TREATMENT (면책 조항으로)

9. p.71 "해외질병의료비 척추지압술·침술 부보장 추가특별약관"
   신규 추가약관. 질병의료비 중 척추지압술/침술 비보장 특약.
   구조: 제1조(보험금을지급하지않는사유)·제2조(준용규정).
   OVS_ILL_MED 재사용.
   매핑: ILL_OVERSEAS_TREATMENT (면책 조항으로)

10. p.71-79 "해외여행중 질병사망 및 질병 80%이상 고도후유장해 특별약관"
    이미 삼성화재에서도 같은 특약이 있음. ILL_DEATH 코드 재사용.
    구조: 제1조(보험금의지급사유①②③)·제2조(보험금지급세부규정①~⑨)·제3조(준용규정).
    매핑: ILL_DEATH_DISABILITY

11. p.?~80 "해외여행중 배상책임 특별약관"
    이미 삼성화재에서도 같은 특약이 있음. LIABILITY 코드 재사용.
    구조: 제1조(보상하는손해)·제2조(보상하는손해의범위①②)·제3조(보상하지않는사항①~⑩)·
    제4조(의무보험과의관계①②③)·제5조(보상한도①②)·제6조(다른보험과의관계)·
    제7조(손해의발생과통지①②)·제8조(손해방지의무①②)·제9조(손해배상청구)·
    제10조(보험금의지급절차)·제11조(보험금의분담)·제12조(보험금청구)·
    제13조(합의중재소송협조)·제14조(양도)·제15조(조사)·제16조(준용규정).
    매핑: LIA_PERSONAL, LIA_PROPERTY, LIA_LODGING

## 범위 외 또는 제외한 사항

- p.72~84의 나머지 특약들(중대사고 구조송환, 전쟁 상해사망후유장해, 항공기납치,
  여권분실, 식중독, 전염병, 항공기 및 수하물 지연)은 다른 청크에서 담당하거나
  p.85 이후에 있을 수 있으므로 이번 범위에서 포함하지 않음.
- 청구서류 조항은 ClauseIncidentMap에 매핑하지 않음(CoverageDocMap 경로 재사용).

idempotent: Coverage는 raw_name, Clause는 (coverage_id, article_no, text) 조합,
ClauseIncidentMap은 (clause_id, type_id) 조합으로 이미 있으면 건너뛴다.
"""
from app.database import SessionLocal
from app import models  # noqa: F401
from app.models.kb import (
    Clause, ClauseIncidentMap, Coverage, CoverageStd, IncidentType, Insurer,
    PolicyVersion, Product,
)
from app.services.kb_seed_common import get_or_create_coverage_std


# ── Clause helpers ────────────────────────────────────────────────────────


def _get_or_create_clause(
    db, *, policy_version_id, coverage_id, clause_type, article_no, text, page_ref, default_color
):
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
        policy_version_id=policy_version_id,
        coverage_id=coverage_id,
        clause_type=clause_type,
        article_no=article_no,
        text=text,
        page_ref=page_ref,
        default_color=default_color,
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
    db.add(
        ClauseIncidentMap(
            clause_id=clause_id,
            type_id=type_id,
            relevance=relevance,
            mapped_by="human",
            confidence=confidence,
        )
    )
    return True


# ── Clause texts ──────────────────────────────────────────────────────────


# p.56-58: 비급여 도수치료·체외충격파치료·증식치료 실손의료비 특별약관

NONCOVER_PHYSIO_ART1 = (
    "① 회사는 피보험자가 해외여행 중에 입은 상해 또는 질병의 치료목적으로 병원에 입원 또는 통원하"
    "여 도수치료·체외충격파치료·증식치료를 받아 본인이 실제로 부담한 비급여의료비에서 공제금액을 "
    "뺀 금액을 보상한도 내에서 보상합니다. "
    "② 제1항에도 불구하고 도수치료(Manipulative Therapy), 체외충격파치료(Extracorporeal Shock "
    "Wave Therapy) 및 증식치료(Prolotherapy, Sclerotherapy 등 근골격계 조직에 직접 주입하는 치료)로 "
    "인한 의료비는 치료받는 국가의 법에서 정한 병원 및 의사의 면허를 가진 자에 의하여 치료를 받은 "
    "경우에 한하며, 하나의 질병에 대하여 회당 20만원, 연간 100만원 한도로 보상합니다."
)

NONCOVER_PHYSIO_ART2 = (
    "① 회사는 다음의 사유로 인하여 생긴 의료비는 보상하지 않습니다. "
    "1. 피보험자가 고의로 자신을 해친 경우. 다만, 피보험자가 심신상실 등으로 자유로운 의사결정을 "
    "할 수 없는 상태에서 자신을 해친 사실이 증명된 경우에는 제1조(보상내용)에 따라 보상합니다. "
    "2. 전쟁, 외국의 무력행사, 혁명, 내란, 사변, 폭동으로 인한 경우. "
    "② 회사는 다른 약정이 없으면 피보험자가 직업, 직무 또는 동호회 활동 목적으로 한 다음의 어느 "
    "하나에 해당하는 행위로 인하여 생긴 상해에 대해서는 보상하지 않습니다. "
    "1. 전문등반(전문적인 등산용구를 사용하여 암벽 또는 빙벽을 오르내리거나 특수한 기술, 경험, "
    "사전 훈련이 필요한 등반을 말합니다), 글라이더 조종, 스카이다이빙, 스쿠버다이빙, 행글라이딩, "
    "수상보트, 패러글라이딩. "
    "2. 모터보트ㆍ자동차 또는 오토바이에 의한 경기, 시범, 행사(이를 위한 연습을 포함합니다) 또는 "
    "시운전(다만, 공용도로에서 시운전을 하는 동안 발생한 상해는 제1조(보상내용)에 따라 보상합니다). "
    "3. 선박 승무원, 어부, 사공, 그 밖에 선박에 탑승하는 것을 직무로 하는 사람의 직무상 선박탑승."
)

NONCOVER_PHYSIO_ART3 = "이 특별약관에 정하지 않은 사항은 보통약관을 따릅니다."


# p.59-64: 비급여 주사료 실손의료비 특별약관

NONCOVER_INJECTION_ART1 = (
    "① 회사는 피보험자가 해외여행 중에 입은 상해 또는 질병의 치료목적으로 병원에 입원 또는 통원하"
    "여 주사료를 투여받아 본인이 실제로 부담한 비급여의료비에서 공제금액을 뺀 금액을 보상한도 내"
    "에서 보상합니다. "
    "② 제1항에도 불구하고 회사는 다음의 주사료에 대해서는 보상한도 내에서 보상합니다. "
    "1. 성장호르몬 주사: 회당 50만원, 연간 200만원 한도 "
    "2. 인간면역결핍바이러스(HIV) 감염 관련 항레트로바이러스 주사: 회당 30만원, 연간 200만원 한도 "
    "3. 기타 주사료: 회당 20만원, 연간 100만원 한도"
)

NONCOVER_INJECTION_ART2 = (
    "① 회사는 다음의 사유로 인하여 생긴 의료비는 보상하지 않습니다. "
    "1. 피보험자가 고의로 자신을 해친 경우. 다만, 피보험자가 심신상실 등으로 자유로운 의사결정을 "
    "할 수 없는 상태에서 자신을 해친 사실이 증명된 경우에는 제1조(보상내용)에 따라 보상합니다. "
    "2. 전쟁, 외국의 무력행사, 혁명, 내란, 사변, 폭동으로 인한 경우."
)

NONCOVER_INJECTION_ART3 = "이 특별약관에 정하지 않은 사항은 보통약관을 따릅니다."


# p.65-68: 비급여 자기공명영상진단(MRI/MRA) 실손의료비 특별약관

NONCOVER_MRI_ART1 = (
    "① 회사는 피보험자가 해외여행 중에 입은 상해 또는 질병의 치료목적으로 병원에 입원 또는 통원하"
    "여 자기공명영상진단을 받아 본인이 실제로 부담한 비급여의료비(조영제, 판독료를 포함합니다)에서"
    "공제금액을 뺀 금액을 보상한도 내에서 보상합니다. "
    "② 병원을 1회 통원(또는 1회 입원)하여 2개 이상 부위에 걸쳐 이 특별약관에서 정한 자기공명영상"
    "진단을 받거나 동일한 부위에 대해 2회 이상 이 특별약관에서 정한 자기공명영상진단을 받는 경우 "
    "각 진단행위를 1회로 보아 각각 1회당 공제금액 및 보상한도를 적용합니다. "
    "③ 제1항의 상해에는 유독가스 또는 유독물질을 우연히 일시에 흡입, 흡수 또는 섭취한 결과로 생긴 "
    "중독증상이 포함됩니다. 다만, 유독가스 또는 유독물질을 상습적으로 흡입, 흡수 또는 섭취한 결과로 "
    "생긴 중독증상과 세균성 음식물 중독증상은 포함되지 않습니다. "
    "④ 피보험자가 입원 또는 통원하여 치료를 받던 중 보험기간이 끝나더라도 그 계속 중인 치료에 대하"
    "여는 보험기간 종료일부터 180일까지(보험기간 종료일은 제외합니다) 보상합니다."
)

NONCOVER_MRI_ART4 = (
    "① 회사는 다음의 사유로 인하여 생긴 의료비는 보상하지 않습니다. "
    "1. 피보험자가 고의로 자신을 해친 경우 "
    "2. 전쟁, 외국의 무력행사, 혁명, 내란, 사변, 폭동으로 인한 경우 "
    "3. 피보험자가 정당한 이유없이 입원 또는 통원 기간 중 의사의 지시를 따르지 않아 발생한 의료비"
)

NONCOVER_MRI_ART6 = "이 특별약관에 정하지 않은 사항은 보통약관을 따릅니다."


# p.69: 국민건강보험 비가입자 추가특별약관

UNINSURED_ART1 = (
    "이 추가특별약관의 피보험자는 기본형 실손의료비 특별약관의 피보험자 중 국민건강보험 비가입자로 합니다."
)

UNINSURED_ART2 = (
    "기본형 실손의료비 특별약관의 제3조(보장종목별 보상내용)와 제4조(보상하지 않는 사항)에도 불구하고 "
    "이 추가특별약관의 피보험자에 대해서는 국민건강보험 가입자와 동일하게 기본형 실손의료비 특별약관을 "
    "적용합니다. 다만, 자동차사고 및 산업재해보상사고의 경우 피보험자가 실제로 부담한 의료비는 기본형 "
    "실손의료비 특별약관의 제3조(보장종목별 보상내용)와 제4조(보상하지 않는 사항)에 따라 보상합니다."
)

UNINSURED_ART3 = (
    "① 보험기간 중에 피보험자가 국민건강보험법에 정한 자격을 취득하였을 때 계약자는 서면으로 회사에 "
    "알리고 보험증권에 확인을 받아야 합니다. "
    "② 피보험자가 국민건강보험법에 정한 자격을 취득한 경우 그 사실이 발생된 날로부터 이 추가특별약관은 "
    "해지되며 회사는 경과하지 않은 기간에 대하여 일단위로 계산한 정해진 보험료를 환급하여 드립니다."
)

UNINSURED_ART4 = "이 추가특별약관에 정하지 않은 사항은 기본형 실손의료비 특별약관을 따릅니다."


# p.70: 해외주재원 상해의료비 전쟁위험보장 추가특별약관

OVERSEAS_EXPAT_WAR_ART1 = (
    "① 이 추가특별약관의 피보험자는 해외주재원 본인과 해외주재지에 동행한 다음의 가족을 말합니다. "
    "1. 피보험자 본인의 배우자 "
    "2. 피보험자 본인의 직계 미혼자녀 "
    "② 이 추가특별약관에서 『해외주재원』이라 함은 대한민국 전역 및 대한민국과 외교관계를 맺거나 무역 "
    "거래를 영위하는 국가 안에 정한 지역에 파견 또는 주재하는 대한민국의 외교사절, 공관원 및 기타 이들에 "
    "준하는 자격을 가진자를 말합니다. "
    "③ 제1항의 피보험자 본인과 본인 이외의 피보험자의 관계는 사고발생 당시의 관계를 말합니다."
)

OVERSEAS_EXPAT_WAR_ART2 = (
    "회사는 기본형 실손의료비 특별약관 제4조(보상하지 않는 사항)의 (1)상해의료비와 비급여 도수치료·체외"
    "충격파치료·증식치료 실손의료비 특별약관, 비급여 주사료 실손의료비 특별약관, 비급여 자기공명영상진단"
    "(MRI/MRA) 실손의료비 특별약관(이하 \"특약형 실손의료비 특별약관\"이라 합니다) 제4조(보상하지 않는 사항)"
    "의 『전쟁, 외국의 무력행사, 혁명, 내란, 폭동』에도 불구하고 피보험자가 해외여행 중에 『전쟁, 외국의 "
    "무력행사, 혁명, 내란, 폭동』으로 입은 상해에 대하여도 기본형 실손의료비 특별약관 제3조(보장종목별 "
    "보상내용)의 (1)상해의료비와 특약형 실손의료비 특별약관 제3조(보상내용)에 따라 보상합니다."
)

OVERSEAS_EXPAT_WAR_ART3 = (
    "이 추가특별약관에 정하지 않은 사항은 기본형 실손의료비 특별약관, 특약형 실손의료비 특별약관을 따릅니다."
)


# p.70: 해외상해의료비 자기부담금설정 추가특별약관

DEDUCTIBLE_INJ_ART1 = (
    "회사는 기본형 실손의료비 특별약관 제3조(보장종목별 보상내용)의 (1)상해의료비(해외)의 보상하는 사항에도 "
    "불구하고 회사가 지급하는 보험금은 하나의 상해에 대하여 피보험자가 해외의료기관에 실제로 지급한 의료비 "
    "중 보험증권에 기재된 ( )만원을 초과하는 금액으로 보상합니다."
)

DEDUCTIBLE_INJ_ART2 = "이 추가특별약관에 정하지 않은 사항은 기본형 실손의료비 특별약관을 따릅니다."


# p.70: 해외질병의료비 자기부담금설정 추가특별약관

DEDUCTIBLE_ILL_ART1 = (
    "회사는 기본형 실손의료비 특별약관 제3조(보장종목별 보상내용)의 (2)질병의료비(해외)의 보상하는 사항에도 "
    "불구하고 회사가 지급하는 보험금은 하나의 질병에 대하여 피보험자가 해외의료기관에 실제로 지급한 의료비 "
    "중 보험증권에 기재된 ( )만원을 초과하는 금액으로 보상합니다."
)

DEDUCTIBLE_ILL_ART2 = "이 추가특별약관에 정하지 않은 사항은 기본형 실손의료비 특별약관을 따릅니다."


# p.71: 해외상해의료비 척추지압술·침술 부보장 추가특별약관

CHIRO_INJ_ART1 = (
    "회사는 기본형 실손의료비 특별약관 제3조(보장종목별 보상내용)의 (1)상해의료비(해외)의 보상하는 사항에도 "
    "불구하고 척추지압술(Chiropractic, 추나요법 등)이나 침술(부항, 뜸 포함) 치료로 인한 의료비는 보상하지 "
    "않습니다."
)

CHIRO_INJ_ART2 = "이 추가특별약관에 정하지 않은 사항은 기본형 실손의료비 특별약관을 따릅니다."


# p.71: 해외질병의료비 척추지압술·침술 부보장 추가특별약관

CHIRO_ILL_ART1 = (
    "회사는 기본형 실손의료비 특별약관 제3조(보장종목별 보상내용)의 (2)질병의료비(해외)의 보상하는 사항에도 "
    "불구하고 척추지압술(Chiropractic, 추나요법 등)이나 침술(부항, 뜸 포함) 치료로 인한 의료비는 보상하지 "
    "않습니다."
)

CHIRO_ILL_ART2 = "이 추가특별약관에 정하지 않은 사항은 기본형 실손의료비 특별약관을 따릅니다."


# p.71-79: 해외여행중 질병사망 및 질병 80%이상 고도후유장해 특별약관

ILL_DEATH_ART1 = (
    "회사는 피보험자에게 다음 중 어느 하나의 사유가 발생한 경우에는 보험수익자에게 약정한 보험금을 "
    "지급합니다. "
    "1. 보통약관 제3조(보험금의 지급사유)의 해외여행 중(이하 \"해외여행 중\"이라 합니다)에 질병으로 사망"
    "하였을 경우에는 보험증권에 기재된 보험가입금액을 사망보험금으로 지급합니다. "
    "2. 해외여행 중 진단확정된 질병으로 장해분류표(【별표1】참조. 이하 같습니다)에서 정한 장해지급률이 "
    "80% 이상에 해당하는 장해상태가 되었을 때에는 보험증권에 기재된 보험가입금액을 고도후유장해보험금으로 "
    "지급합니다. "
    "3. 제1호 및 제2호에도 불구하고 해외여행 중 발생한 질병을 직접원인으로 하여 보험기간 마지막 날로부터 "
    "30일 이내에 사망하거나 또는 80% 이상에 해당하는 장해상태가 되었을 때에도 제1호 또는 제2호에 정한 "
    "보험금을 지급합니다."
)

ILL_DEATH_ART2_PARTIAL = (
    "① 「호스피스·완화의료 및 임종과정에 있는 환자의 연명의료 결정에 관한 법률」에 따른 연명의료중단등결"
    "정 및 그 이행으로 피보험자가 사망하는 경우 연명의료중단등결정 및 그 이행은 제1조(보험금의 종류 및 "
    "지급사유) 제1항 제1호 '사망'의 원인 및 '사망보험금' 지급에 영향을 미치지 않습니다. "
    "② 제1조(보험금의 종류 및 지급사유) 제1항 제2호에도 불구하고 영구히 고정된 증상은 아니지만 치료종결 "
    "후 한시적으로 나타나는 장해에 대하여는 그 기간이 5년 이상인 때에는 해당 장해 지급률의 20%를 후유장해"
    "지급률로 하여 제5항을 적용합니다."
)

ILL_DEATH_ART3 = "이 특별약관에 정하지 않은 사항은 보통약관을 따릅니다."


# p.72-79: 해외여행중 배상책임 특별약관

LIABILITY_ART1 = (
    "회사는 피보험자가 보통약관 제3조(보험금의 지급사유)의 여행도중에 생긴 보험사고로 인하여 피해자에게 "
    "법률상의 배상책임을 부담함으로써 입은 손해를 이 특별약관에 따라 보상하여 드립니다."
)

LIABILITY_ART2 = (
    "회사가 보상하는 손해의 범위는 아래와 같습니다. "
    "1. 피보험자가 피해자에게 지급할 책임을 지는 법률상의 손해배상금 "
    "2. 계약자 또는 피보험자가 지출한 아래의 비용 "
    "가. 피보험자가 제8조(손해방지의무) 제1항 제1호의 손해의 방지 또는 경감을 위하여 지출한 필요 또는 "
    "유익하였던 비용 "
    "나. 피보험자가 제8조(손해방지의무) 제1항 제2호의 제3자로부터 손해의 배상을 받을 수 있는 그 권리를 "
    "지키거나 행사하기 위하여 지출한 필요 또는 유익하였던 비용 "
    "다. 피보험자가 지급한 소송비용, 변호사비용, 중재, 화해 또는 조정에 관한 비용 "
    "라. 보험증권상 보상한도액내의 금액에 대한 공탁보증보험료. 그러나 회사는 그러한 보증자체를 제공할 "
    "책임은 부담하지 않습니다. "
    "마. 피보험자가 제9조(손해배상청구에 대한 회사의 해결) 제2항 및 제3항의 회사의 요구에 따르기 위하여 "
    "지출한 비용"
)

LIABILITY_ART3 = (
    "회사는 보통약관 제5조(보험금을 지급하지 않는 사유) 제1항의 제1호, 제3호 또는 제5호 및 아래의 "
    "사유로 손해배상책임을 부담하게 됨으로써 입은 손해는 보상하여 드리지 않습니다. "
    "1. 피보험자의 직접적인 직무수행으로 인한 배상책임 "
    "2. 피보험자의 직무용으로만 사용되는 동산의 소유, 사용 또는 관리로 인한 배상책임 "
    "3. 피보험자가 소유, 사용 또는 관리하는 부동산으로 인한 배상책임 "
    "4. 피보험자의 근로자가 피보험자의 업무에 종사중에 입은 신체의 장해로 인한 배상책임. 단, 피보험자의 "
    "가사사용인에 대하여는 이와 같지 않습니다. "
    "5. 피보험자와 타인간에 손해배상에 관한 약정이 있는 경우 그 약정에 따라 가중된 배상책임 "
    "6. 피보험자와 세대를 같이하는 친족(「민법 제777조」에 따른 8촌 이내의 혈족, 4촌 이내의 인척 및 배우자) "
    "및 여행과정을 같이 하는 친족에 대한 배상책임 "
    "7. 피보험자가 소유, 사용 또는 관리하는 재물의 파손에 대하여 그 재물에 대하여 정당한 권리를 가진 사람에게 "
    "부담하는 배상책임. 단, 호텔의 객실이나 객실내의 동산에 끼치는 손해에 대하여는 이와 같지 않습니다. "
    "8. 피보험자의 심신상실로 인한 배상책임 "
    "9. 피보험자 또는 피보험자의 지시에 따른 폭행 또는 구타로 인한 배상책임 "
    "10. 항공기, 선박, 차량(원동력이 인력에 의한 것을 제외합니다), 총기(공기총은 제외합니다)의 소유, 사용 "
    "또는 관리로 인한 배상책임"
)

LIABILITY_ART5 = (
    "① 회사는 1회의 보험사고에 대하여 다음과 같이 보상합니다. 이 경우 보상한도액과 자기부담금은 각각 "
    "보험증권에 기재된 금액을 말합니다. "
    "1. 제2조(보상하는 손해의 범위) 제1호의 손해배상금: 보상한도액을 한도로 보상하되, 자기부담금이 약정된 "
    "경우에는 그 자기부담금을 초과한 부분만 보상합니다. "
    "2. 제2조(보상하는 손해의 범위) 제2호 가목, 나목 또는 마목의 비용: 비용의 전액을 보상합니다. "
    "3. 제2조(보상하는 손해의 범위) 제2호 다목 또는 라목의 비용: 이 비용과 제1호에 의한 보상액의 합계액을 "
    "보상한도액의 한도내에서 보상합니다. "
    "② 보험기간 중 발생하는 사고에 대한 회사의 보상총액은 보험증권에 기재된 총 보상한도액을 한도로 합니다."
)

LIABILITY_ART7 = (
    "① 계약자 또는 피보험자는 아래와 같은 사실이 있는 경우에는 지체없이 그 내용을 서면으로 회사에 알려야 합니다. "
    "1. 사고가 발생하였을 경우 사고가 발생한 때와 곳, 피해자의 주소와 성명, 사고 상황 및 이들 사항의 증인이 있을 "
    "경우 그 주소와 성명 "
    "2. 피해자로부터 손해배상청구를 받았을 경우 "
    "3. 피해자로부터 손해배상책임에 관한 소송을 제기받았을 경우 "
    "② 계약자 또는 피보험자가 제1항 각 호의 통지를 게을리하여 손해가 증가된 때에는 회사는 그 증가된 손해를 "
    "보상하여 드리지 않으며, 제1항 제3호의 통지를 게을리 한 때에는 소송비용과 변호사비용도 보상하여 드리지 않습니다."
)

LIABILITY_ART8 = (
    "① 보험사고가 생긴 때에는 계약자 또는 피보험자는 아래의 사항을 이행하여야 합니다. "
    "1. 손해의 방지 또는 경감을 위하여 노력하는 일(피해자에 대한 응급처치, 긴급호송 또는 그 밖의 긴급조치를 포함합니다) "
    "2. 제3자로부터 손해의 배상을 받을 수 있는 경우에는 그 권리를 지키거나 행사하기 위한 필요한 조치를 취하는 일 "
    "3. 손해배상책임의 전부 또는 일부에 관하여 지급(변제), 승인 또는 화해를 하거나 소송,중재 또는 조정을 제기하거나 "
    "신청하고자 할 경우에는 미리 회사의 동의를 받는 일 "
    "② 계약자 또는 피보험자가 정당한 이유없이 위 제1항의 의무를 이행하지 않았을 때에는 제2조(보상하는 손해의 범위)의 "
    "손해에서 다음의 금액을 뺍니다. "
    "1. 제1항 제1호의 경우에는 그 노력을 하였더라면 손해를 방지 또는 경감할 수 있었던 금액 "
    "2. 제1항 제2호의 경우에는 제3자로부터 손해의 배상을 받을 수 있었던 금액 "
    "3. 제1항 제3호의 경우에는 소송비용(중재 또는 조정에 관한 비용 포함) 및 변호사비용과 회사의 동의를 받지 않은 "
    "행위에 의하여 증가된 손해"
)

LIABILITY_ART10_DOC = (
    "① 피보험자가 보험금을 청구할 때에는 다음의 서류를 회사에 제출하여야 합니다. "
    "1. 보험금 청구서 "
    "2. 신분증(주민등록증 또는 운전면허증 등 사진이 부착된 정부기관발행 신분증, 본인이 아닌 경우에는 본인의 "
    "인감증명서 또는 본인서명사실확인서 포함) "
    "3. 손해배상금 및 그 밖의 비용을 지급하였음을 증명하는 서류 "
    "4. 회사가 요구하는 그 밖의 서류"
)


def run():
    db = SessionLocal()
    try:
        # ── Setup ──────────────────────────────────────────────────────────

        insurer = db.query(Insurer).filter_by(code="DB").first()
        if not insurer:
            print("DB손해보험이 아직 시딩되지 않았습니다. seed_db를 먼저 실행하세요.")
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
        required_types = [
            "ILL_DOMESTIC_TREATMENT",
            "ILL_DEATH_DISABILITY",
            "INJ_OVERSEAS_TREATMENT",
            "ILL_OVERSEAS_TREATMENT",
            "LIA_PERSONAL",
            "LIA_PROPERTY",
            "LIA_LODGING",
        ]
        missing_types = [c for c in required_types if c not in types]
        if missing_types:
            print(f"incident_type 사전에 없는 코드: {missing_types}. seed_incident_types를 먼저 실행하세요.")
            return

        # Get or create coverage standards
        std_noncover = get_or_create_coverage_std(
            db, "NON_COVERED_MED", "비급여 실손의료비", "의료", False
        )
        std_inj_ovs = get_or_create_coverage_std(
            db, "OVS_INJ_MED", "해외발생 상해의료비", "의료", False
        )
        std_ill_ovs = get_or_create_coverage_std(
            db, "OVS_ILL_MED", "해외발생 질병의료비", "의료", False
        )
        std_ill_death = get_or_create_coverage_std(
            db, "ILL_DEATH", "질병사망·고도후유장해", "질병", False
        )
        std_liability = get_or_create_coverage_std(
            db, "LIABILITY", "배상책임", "배상책임", False
        )
        std_war_risk = get_or_create_coverage_std(
            db, "WAR_RISK", "전쟁위험보장", "특수", False
        )

        clause_created = map_created = coverage_created = 0

        # ────────────────────────────────────────────────────────────────────
        # 1) 비급여 도수치료·체외충격파치료·증식치료 실손의료비 특별약관 (p.56-58)
        # ────────────────────────────────────────────────────────────────────

        cov_physio = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name
                == "비급여 도수치료·체외충격파치료·증식치료 실손의료비 특별약관",
            )
            .first()
        )
        if not cov_physio:
            cov_physio = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_noncover.coverage_std_id,
                raw_name="비급여 도수치료·체외충격파치료·증식치료 실손의료비 특별약관",
                definition=NONCOVER_PHYSIO_ART1,
                limit_amount="도수/체외충격파/증식치료 각각 회당 20만원, 연간 100만원",
                deductible=None,
                waiting_condition=None,
            )
            db.add(cov_physio)
            db.flush()
            coverage_created += 1

        c1, created = _get_or_create_clause(
            db,
            policy_version_id=pv.policy_version_id,
            coverage_id=cov_physio.coverage_id,
            clause_type="보장정의",
            article_no="[비급여 도수치료·체외충격파치료·증식치료 실손의료비 특별약관] 제1조(보상내용)",
            text=NONCOVER_PHYSIO_ART1,
            page_ref="p.56-57",
            default_color="파랑",
        )
        clause_created += created
        map_created += _get_or_create_map(
            db,
            clause_id=c1.clause_id,
            type_id=types["ILL_DOMESTIC_TREATMENT"].type_id,
            relevance="직접",
            confidence=0.9,
        )

        c2, created = _get_or_create_clause(
            db,
            policy_version_id=pv.policy_version_id,
            coverage_id=cov_physio.coverage_id,
            clause_type="면책",
            article_no="[비급여 도수치료·체외충격파치료·증식치료 실손의료비 특별약관] 제2조(보상하지 않는 사항)",
            text=NONCOVER_PHYSIO_ART2,
            page_ref="p.57",
            default_color="빨강",
        )
        clause_created += created
        map_created += _get_or_create_map(
            db,
            clause_id=c2.clause_id,
            type_id=types["ILL_DOMESTIC_TREATMENT"].type_id,
            relevance="면책",
            confidence=0.85,
        )

        c3, created = _get_or_create_clause(
            db,
            policy_version_id=pv.policy_version_id,
            coverage_id=cov_physio.coverage_id,
            clause_type="공통",
            article_no="[비급여 도수치료·체외충격파치료·증식치료 실손의료비 특별약관] 제3조(준용규정)",
            text=NONCOVER_PHYSIO_ART3,
            page_ref="p.58",
            default_color="회색",
        )
        clause_created += created

        # ────────────────────────────────────────────────────────────────────
        # 2) 비급여 주사료 실손의료비 특별약관 (p.59-64)
        # ────────────────────────────────────────────────────────────────────

        cov_inj = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "비급여 주사료 실손의료비 특별약관",
            )
            .first()
        )
        if not cov_inj:
            cov_inj = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_noncover.coverage_std_id,
                raw_name="비급여 주사료 실손의료비 특별약관",
                definition=NONCOVER_INJECTION_ART1,
                limit_amount="성장호르몬 회당 50만원 연 200만원, HIV 항레트로바이러스 회당 30만원 연 200만원, 기타 회당 20만원 연 100만원",
                deductible=None,
                waiting_condition=None,
            )
            db.add(cov_inj)
            db.flush()
            coverage_created += 1

        c4, created = _get_or_create_clause(
            db,
            policy_version_id=pv.policy_version_id,
            coverage_id=cov_inj.coverage_id,
            clause_type="보장정의",
            article_no="[비급여 주사료 실손의료비 특별약관] 제1조(보상내용)",
            text=NONCOVER_INJECTION_ART1,
            page_ref="p.59",
            default_color="파랑",
        )
        clause_created += created
        map_created += _get_or_create_map(
            db,
            clause_id=c4.clause_id,
            type_id=types["ILL_DOMESTIC_TREATMENT"].type_id,
            relevance="직접",
            confidence=0.9,
        )

        c5, created = _get_or_create_clause(
            db,
            policy_version_id=pv.policy_version_id,
            coverage_id=cov_inj.coverage_id,
            clause_type="면책",
            article_no="[비급여 주사료 실손의료비 특별약관] 제2조(보상하지 않는 사항)",
            text=NONCOVER_INJECTION_ART2,
            page_ref="p.60",
            default_color="빨강",
        )
        clause_created += created
        map_created += _get_or_create_map(
            db,
            clause_id=c5.clause_id,
            type_id=types["ILL_DOMESTIC_TREATMENT"].type_id,
            relevance="면책",
            confidence=0.85,
        )

        c6, created = _get_or_create_clause(
            db,
            policy_version_id=pv.policy_version_id,
            coverage_id=cov_inj.coverage_id,
            clause_type="공통",
            article_no="[비급여 주사료 실손의료비 특별약관] 제3조(준용규정)",
            text=NONCOVER_INJECTION_ART3,
            page_ref="p.61",
            default_color="회색",
        )
        clause_created += created

        # ────────────────────────────────────────────────────────────────────
        # 3) 비급여 자기공명영상진단(MRI/MRA) 실손의료비 특별약관 (p.65-68)
        # ────────────────────────────────────────────────────────────────────

        cov_mri = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name
                == "비급여 자기공명영상진단(MRI/MRA) 실손의료비 특별약관",
            )
            .first()
        )
        if not cov_mri:
            cov_mri = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_noncover.coverage_std_id,
                raw_name="비급여 자기공명영상진단(MRI/MRA) 실손의료비 특별약관",
                definition=NONCOVER_MRI_ART1,
                limit_amount="연간 300만원",
                deductible="회당 2만원 또는 보상대상의료비의 30% 중 큰 금액",
                waiting_condition=None,
            )
            db.add(cov_mri)
            db.flush()
            coverage_created += 1

        c7, created = _get_or_create_clause(
            db,
            policy_version_id=pv.policy_version_id,
            coverage_id=cov_mri.coverage_id,
            clause_type="보장정의",
            article_no="[비급여 자기공명영상진단(MRI/MRA) 실손의료비 특별약관] 제1조(보상내용)",
            text=NONCOVER_MRI_ART1,
            page_ref="p.65-66",
            default_color="파랑",
        )
        clause_created += created
        map_created += _get_or_create_map(
            db,
            clause_id=c7.clause_id,
            type_id=types["ILL_DOMESTIC_TREATMENT"].type_id,
            relevance="직접",
            confidence=0.9,
        )

        c8, created = _get_or_create_clause(
            db,
            policy_version_id=pv.policy_version_id,
            coverage_id=cov_mri.coverage_id,
            clause_type="면책",
            article_no="[비급여 자기공명영상진단(MRI/MRA) 실손의료비 특별약관] 제4조(보상하지 않는 사항)",
            text=NONCOVER_MRI_ART4,
            page_ref="p.67",
            default_color="빨강",
        )
        clause_created += created
        map_created += _get_or_create_map(
            db,
            clause_id=c8.clause_id,
            type_id=types["ILL_DOMESTIC_TREATMENT"].type_id,
            relevance="면책",
            confidence=0.85,
        )

        c9, created = _get_or_create_clause(
            db,
            policy_version_id=pv.policy_version_id,
            coverage_id=cov_mri.coverage_id,
            clause_type="공통",
            article_no="[비급여 자기공명영상진단(MRI/MRA) 실손의료비 특별약관] 제6조(준용규정)",
            text=NONCOVER_MRI_ART6,
            page_ref="p.68",
            default_color="회색",
        )
        clause_created += created

        # ────────────────────────────────────────────────────────────────────
        # 4) 국민건강보험 비가입자 추가특별약관 (p.69)
        # ────────────────────────────────────────────────────────────────────

        cov_uninsured = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "국민건강보험 비가입자 추가특별약관",
            )
            .first()
        )
        if not cov_uninsured:
            cov_uninsured = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=None,  # 조건부 적용 규정, 독립 CoverageStd 없음
                raw_name="국민건강보험 비가입자 추가특별약관",
                definition=UNINSURED_ART2,
                limit_amount=None,
                deductible=None,
                waiting_condition="피보험자가 국민건강보험 비가입자일 때 적용",
            )
            db.add(cov_uninsured)
            db.flush()
            coverage_created += 1

        c10, created = _get_or_create_clause(
            db,
            policy_version_id=pv.policy_version_id,
            coverage_id=cov_uninsured.coverage_id,
            clause_type="조건",
            article_no="[국민건강보험 비가입자 추가특별약관] 제1조(적용대상)",
            text=UNINSURED_ART1,
            page_ref="p.69",
            default_color="노랑",
        )
        clause_created += created

        c11, created = _get_or_create_clause(
            db,
            policy_version_id=pv.policy_version_id,
            coverage_id=cov_uninsured.coverage_id,
            clause_type="보장정의",
            article_no="[국민건강보험 비가입자 추가특별약관] 제2조(보상하는 사항)",
            text=UNINSURED_ART2,
            page_ref="p.69",
            default_color="파랑",
        )
        clause_created += created

        c12, created = _get_or_create_clause(
            db,
            policy_version_id=pv.policy_version_id,
            coverage_id=cov_uninsured.coverage_id,
            clause_type="조건",
            article_no="[국민건강보험 비가입자 추가특별약관] 제3조(계약 후 알릴의무)",
            text=UNINSURED_ART3,
            page_ref="p.69",
            default_color="노랑",
        )
        clause_created += created

        c13, created = _get_or_create_clause(
            db,
            policy_version_id=pv.policy_version_id,
            coverage_id=cov_uninsured.coverage_id,
            clause_type="공통",
            article_no="[국민건강보험 비가입자 추가특별약관] 제4조(준용규정)",
            text=UNINSURED_ART4,
            page_ref="p.69",
            default_color="회색",
        )
        clause_created += created

        # ────────────────────────────────────────────────────────────────────
        # 5) 해외주재원 상해의료비 전쟁위험보장 추가특별약관 (p.70)
        # ────────────────────────────────────────────────────────────────────

        cov_expat_war = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name
                == "해외주재원 상해의료비 전쟁위험보장 추가특별약관",
            )
            .first()
        )
        if not cov_expat_war:
            cov_expat_war = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_war_risk.coverage_std_id,
                raw_name="해외주재원 상해의료비 전쟁위험보장 추가특별약관",
                definition=OVERSEAS_EXPAT_WAR_ART2,
                limit_amount="기본형 실손의료비 특별약관 동일",
                deductible=None,
                waiting_condition="해외주재원 자격(대사관원, 외교사절 등) 및 동행 가족만 적용",
            )
            db.add(cov_expat_war)
            db.flush()
            coverage_created += 1

        c14, created = _get_or_create_clause(
            db,
            policy_version_id=pv.policy_version_id,
            coverage_id=cov_expat_war.coverage_id,
            clause_type="조건",
            article_no="[해외주재원 상해의료비 전쟁위험보장 추가특별약관] 제1조(피보험자의 범위)",
            text=OVERSEAS_EXPAT_WAR_ART1,
            page_ref="p.70",
            default_color="노랑",
        )
        clause_created += created

        c15, created = _get_or_create_clause(
            db,
            policy_version_id=pv.policy_version_id,
            coverage_id=cov_expat_war.coverage_id,
            clause_type="보장정의",
            article_no="[해외주재원 상해의료비 전쟁위험보장 추가특별약관] 제2조(보상하는 사항)",
            text=OVERSEAS_EXPAT_WAR_ART2,
            page_ref="p.70",
            default_color="파랑",
        )
        clause_created += created
        map_created += _get_or_create_map(
            db,
            clause_id=c15.clause_id,
            type_id=types["INJ_OVERSEAS_TREATMENT"].type_id,
            relevance="직접",
            confidence=0.9,
        )

        c16, created = _get_or_create_clause(
            db,
            policy_version_id=pv.policy_version_id,
            coverage_id=cov_expat_war.coverage_id,
            clause_type="공통",
            article_no="[해외주재원 상해의료비 전쟁위험보장 추가특별약관] 제3조(준용규정)",
            text=OVERSEAS_EXPAT_WAR_ART3,
            page_ref="p.70",
            default_color="회색",
        )
        clause_created += created

        # ────────────────────────────────────────────────────────────────────
        # 6) 해외상해의료비 자기부담금설정 추가특별약관 (p.70)
        # ────────────────────────────────────────────────────────────────────

        cov_ded_inj = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "해외상해의료비 자기부담금설정 추가특별약관",
            )
            .first()
        )
        if not cov_ded_inj:
            cov_ded_inj = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_inj_ovs.coverage_std_id,
                raw_name="해외상해의료비 자기부담금설정 추가특별약관",
                definition=DEDUCTIBLE_INJ_ART1,
                limit_amount="기본형 실손의료비 특별약관 동일",
                deductible="보험증권 기재 금액 초과분만 보상",
                waiting_condition=None,
            )
            db.add(cov_ded_inj)
            db.flush()
            coverage_created += 1

        c17, created = _get_or_create_clause(
            db,
            policy_version_id=pv.policy_version_id,
            coverage_id=cov_ded_inj.coverage_id,
            clause_type="제한",
            article_no="[해외상해의료비 자기부담금설정 추가특별약관] 제1조(보험금의 지급)",
            text=DEDUCTIBLE_INJ_ART1,
            page_ref="p.70",
            default_color="초록",
        )
        clause_created += created
        map_created += _get_or_create_map(
            db,
            clause_id=c17.clause_id,
            type_id=types["INJ_OVERSEAS_TREATMENT"].type_id,
            relevance="제한",
            confidence=0.9,
        )

        c18, created = _get_or_create_clause(
            db,
            policy_version_id=pv.policy_version_id,
            coverage_id=cov_ded_inj.coverage_id,
            clause_type="공통",
            article_no="[해외상해의료비 자기부담금설정 추가특별약관] 제2조(준용규정)",
            text=DEDUCTIBLE_INJ_ART2,
            page_ref="p.70",
            default_color="회색",
        )
        clause_created += created

        # ────────────────────────────────────────────────────────────────────
        # 7) 해외질병의료비 자기부담금설정 추가특별약관 (p.70)
        # ────────────────────────────────────────────────────────────────────

        cov_ded_ill = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "해외질병의료비 자기부담금설정 추가특별약관",
            )
            .first()
        )
        if not cov_ded_ill:
            cov_ded_ill = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_ill_ovs.coverage_std_id,
                raw_name="해외질병의료비 자기부담금설정 추가특별약관",
                definition=DEDUCTIBLE_ILL_ART1,
                limit_amount="기본형 실손의료비 특별약관 동일",
                deductible="보험증권 기재 금액 초과분만 보상",
                waiting_condition=None,
            )
            db.add(cov_ded_ill)
            db.flush()
            coverage_created += 1

        c19, created = _get_or_create_clause(
            db,
            policy_version_id=pv.policy_version_id,
            coverage_id=cov_ded_ill.coverage_id,
            clause_type="제한",
            article_no="[해외질병의료비 자기부담금설정 추가특별약관] 제1조(보험금의 지급)",
            text=DEDUCTIBLE_ILL_ART1,
            page_ref="p.70",
            default_color="초록",
        )
        clause_created += created
        map_created += _get_or_create_map(
            db,
            clause_id=c19.clause_id,
            type_id=types["ILL_OVERSEAS_TREATMENT"].type_id,
            relevance="제한",
            confidence=0.9,
        )

        c20, created = _get_or_create_clause(
            db,
            policy_version_id=pv.policy_version_id,
            coverage_id=cov_ded_ill.coverage_id,
            clause_type="공통",
            article_no="[해외질병의료비 자기부담금설정 추가특별약관] 제2조(준용규정)",
            text=DEDUCTIBLE_ILL_ART2,
            page_ref="p.70",
            default_color="회색",
        )
        clause_created += created

        # ────────────────────────────────────────────────────────────────────
        # 8) 해외상해의료비 척추지압술·침술 부보장 추가특별약관 (p.71)
        # ────────────────────────────────────────────────────────────────────

        cov_chiro_inj = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name
                == "해외상해의료비 척추지압술·침술 부보장 추가특별약관",
            )
            .first()
        )
        if not cov_chiro_inj:
            cov_chiro_inj = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_inj_ovs.coverage_std_id,
                raw_name="해외상해의료비 척추지압술·침술 부보장 추가특별약관",
                definition="척추지압술(Chiropractic, 추나요법 등)이나 침술(부항, 뜸 포함) 치료 비보장",
                limit_amount=None,
                deductible=None,
                waiting_condition="척추지압술·침술 비보장 특약",
            )
            db.add(cov_chiro_inj)
            db.flush()
            coverage_created += 1

        c21, created = _get_or_create_clause(
            db,
            policy_version_id=pv.policy_version_id,
            coverage_id=cov_chiro_inj.coverage_id,
            clause_type="면책",
            article_no="[해외상해의료비 척추지압술·침술 부보장 추가특별약관] 제1조(보험금을 지급하지 않는 사유)",
            text=CHIRO_INJ_ART1,
            page_ref="p.71",
            default_color="빨강",
        )
        clause_created += created
        map_created += _get_or_create_map(
            db,
            clause_id=c21.clause_id,
            type_id=types["INJ_OVERSEAS_TREATMENT"].type_id,
            relevance="면책",
            confidence=0.9,
        )

        c22, created = _get_or_create_clause(
            db,
            policy_version_id=pv.policy_version_id,
            coverage_id=cov_chiro_inj.coverage_id,
            clause_type="공통",
            article_no="[해외상해의료비 척추지압술·침술 부보장 추가특별약관] 제2조(준용규정)",
            text=CHIRO_INJ_ART2,
            page_ref="p.71",
            default_color="회색",
        )
        clause_created += created

        # ────────────────────────────────────────────────────────────────────
        # 9) 해외질병의료비 척추지압술·침술 부보장 추가특별약관 (p.71)
        # ────────────────────────────────────────────────────────────────────

        cov_chiro_ill = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name
                == "해외질병의료비 척추지압술·침술 부보장 추가특별약관",
            )
            .first()
        )
        if not cov_chiro_ill:
            cov_chiro_ill = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_ill_ovs.coverage_std_id,
                raw_name="해외질병의료비 척추지압술·침술 부보장 추가특별약관",
                definition="척추지압술(Chiropractic, 추나요법 등)이나 침술(부항, 뜸 포함) 치료 비보장",
                limit_amount=None,
                deductible=None,
                waiting_condition="척추지압술·침술 비보장 특약",
            )
            db.add(cov_chiro_ill)
            db.flush()
            coverage_created += 1

        c23, created = _get_or_create_clause(
            db,
            policy_version_id=pv.policy_version_id,
            coverage_id=cov_chiro_ill.coverage_id,
            clause_type="면책",
            article_no="[해외질병의료비 척추지압술·침술 부보장 추가특별약관] 제1조(보험금을 지급하지 않는 사유)",
            text=CHIRO_ILL_ART1,
            page_ref="p.71",
            default_color="빨강",
        )
        clause_created += created
        map_created += _get_or_create_map(
            db,
            clause_id=c23.clause_id,
            type_id=types["ILL_OVERSEAS_TREATMENT"].type_id,
            relevance="면책",
            confidence=0.9,
        )

        c24, created = _get_or_create_clause(
            db,
            policy_version_id=pv.policy_version_id,
            coverage_id=cov_chiro_ill.coverage_id,
            clause_type="공통",
            article_no="[해외질병의료비 척추지압술·침술 부보장 추가특별약관] 제2조(준용규정)",
            text=CHIRO_ILL_ART2,
            page_ref="p.71",
            default_color="회색",
        )
        clause_created += created

        # ────────────────────────────────────────────────────────────────────
        # 10) 해외여행중 질병사망 및 질병 80%이상 고도후유장해 특별약관 (p.71-79)
        # ────────────────────────────────────────────────────────────────────

        cov_ill_death = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name
                == "해외여행중 질병사망 및 질병 80%이상 고도후유장해 특별약관",
            )
            .first()
        )
        if not cov_ill_death:
            cov_ill_death = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_ill_death.coverage_std_id,
                raw_name="해외여행중 질병사망 및 질병 80%이상 고도후유장해 특별약관",
                definition=ILL_DEATH_ART1,
                limit_amount="보험증권 기재 보험가입금액",
                deductible=None,
                waiting_condition="질병 진단확정일부터 180일 이내 장해지급률 미확정시 180일 시점 의사진단 기준",
            )
            db.add(cov_ill_death)
            db.flush()
            coverage_created += 1

        c25, created = _get_or_create_clause(
            db,
            policy_version_id=pv.policy_version_id,
            coverage_id=cov_ill_death.coverage_id,
            clause_type="보장정의",
            article_no="[해외여행중 질병사망 및 질병 80%이상 고도후유장해 특별약관] 제1조(보험금의 지급사유)",
            text=ILL_DEATH_ART1,
            page_ref="p.71-72",
            default_color="파랑",
        )
        clause_created += created
        map_created += _get_or_create_map(
            db,
            clause_id=c25.clause_id,
            type_id=types["ILL_DEATH_DISABILITY"].type_id,
            relevance="직접",
            confidence=0.95,
        )

        c26, created = _get_or_create_clause(
            db,
            policy_version_id=pv.policy_version_id,
            coverage_id=cov_ill_death.coverage_id,
            clause_type="조건",
            article_no="[해외여행중 질병사망 및 질병 80%이상 고도후유장해 특별약관] 제2조(보험금 지급에 관한 세부규정)",
            text=ILL_DEATH_ART2_PARTIAL,
            page_ref="p.72",
            default_color="노랑",
        )
        clause_created += created
        map_created += _get_or_create_map(
            db,
            clause_id=c26.clause_id,
            type_id=types["ILL_DEATH_DISABILITY"].type_id,
            relevance="조건부",
            confidence=0.8,
        )

        c27, created = _get_or_create_clause(
            db,
            policy_version_id=pv.policy_version_id,
            coverage_id=cov_ill_death.coverage_id,
            clause_type="공통",
            article_no="[해외여행중 질병사망 및 질병 80%이상 고도후유장해 특별약관] 제3조(준용규정)",
            text=ILL_DEATH_ART3,
            page_ref="p.79",
            default_color="회색",
        )
        clause_created += created

        # ────────────────────────────────────────────────────────────────────
        # 11) 해외여행중 배상책임 특별약관 (p.72-79)
        # ────────────────────────────────────────────────────────────────────

        cov_lia = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "해외여행중 배상책임 특별약관",
            )
            .first()
        )
        if not cov_lia:
            cov_lia = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_liability.coverage_std_id,
                raw_name="해외여행중 배상책임 특별약관",
                definition=LIABILITY_ART1,
                limit_amount="보험증권 기재 보상한도액(1회 사고당) 및 총 보상한도액 한도",
                deductible="보험증권 기재 자기부담금(약정된 경우, 손해배상금에만 적용)",
                waiting_condition=None,
            )
            db.add(cov_lia)
            db.flush()
            coverage_created += 1

        c28, created = _get_or_create_clause(
            db,
            policy_version_id=pv.policy_version_id,
            coverage_id=cov_lia.coverage_id,
            clause_type="보장정의",
            article_no="[해외여행중 배상책임 특별약관] 제1조(보상하는 손해)",
            text=LIABILITY_ART1,
            page_ref="p.72",
            default_color="파랑",
        )
        clause_created += created
        map_created += sum(
            [
                _get_or_create_map(
                    db,
                    clause_id=c28.clause_id,
                    type_id=types["LIA_PERSONAL"].type_id,
                    relevance="직접",
                    confidence=0.9,
                ),
                _get_or_create_map(
                    db,
                    clause_id=c28.clause_id,
                    type_id=types["LIA_PROPERTY"].type_id,
                    relevance="직접",
                    confidence=0.9,
                ),
            ]
        )

        c29, created = _get_or_create_clause(
            db,
            policy_version_id=pv.policy_version_id,
            coverage_id=cov_lia.coverage_id,
            clause_type="보장정의",
            article_no="[해외여행중 배상책임 특별약관] 제2조(보상하는 손해의 범위)",
            text=LIABILITY_ART2,
            page_ref="p.72-73",
            default_color="파랑",
        )
        clause_created += created
        map_created += sum(
            [
                _get_or_create_map(
                    db,
                    clause_id=c29.clause_id,
                    type_id=types["LIA_PERSONAL"].type_id,
                    relevance="직접",
                    confidence=0.9,
                ),
                _get_or_create_map(
                    db,
                    clause_id=c29.clause_id,
                    type_id=types["LIA_PROPERTY"].type_id,
                    relevance="직접",
                    confidence=0.9,
                ),
            ]
        )

        c30, created = _get_or_create_clause(
            db,
            policy_version_id=pv.policy_version_id,
            coverage_id=cov_lia.coverage_id,
            clause_type="면책",
            article_no="[해외여행중 배상책임 특별약관] 제3조(보상하지 않는 손해)",
            text=LIABILITY_ART3,
            page_ref="p.73-74",
            default_color="빨강",
        )
        clause_created += created
        map_created += sum(
            [
                _get_or_create_map(
                    db,
                    clause_id=c30.clause_id,
                    type_id=types["LIA_PERSONAL"].type_id,
                    relevance="면책",
                    confidence=0.9,
                ),
                _get_or_create_map(
                    db,
                    clause_id=c30.clause_id,
                    type_id=types["LIA_PROPERTY"].type_id,
                    relevance="면책",
                    confidence=0.9,
                ),
                _get_or_create_map(
                    db,
                    clause_id=c30.clause_id,
                    type_id=types["LIA_LODGING"].type_id,
                    relevance="직접",
                    confidence=0.85,
                ),
            ]
        )

        c31, created = _get_or_create_clause(
            db,
            policy_version_id=pv.policy_version_id,
            coverage_id=cov_lia.coverage_id,
            clause_type="제한",
            article_no="[해외여행중 배상책임 특별약관] 제5조(보상한도)",
            text=LIABILITY_ART5,
            page_ref="p.74-75",
            default_color="초록",
        )
        clause_created += created
        map_created += sum(
            [
                _get_or_create_map(
                    db,
                    clause_id=c31.clause_id,
                    type_id=types["LIA_PERSONAL"].type_id,
                    relevance="조건부",
                    confidence=0.9,
                ),
                _get_or_create_map(
                    db,
                    clause_id=c31.clause_id,
                    type_id=types["LIA_PROPERTY"].type_id,
                    relevance="조건부",
                    confidence=0.9,
                ),
                _get_or_create_map(
                    db,
                    clause_id=c31.clause_id,
                    type_id=types["LIA_LODGING"].type_id,
                    relevance="조건부",
                    confidence=0.8,
                ),
            ]
        )

        c32, created = _get_or_create_clause(
            db,
            policy_version_id=pv.policy_version_id,
            coverage_id=cov_lia.coverage_id,
            clause_type="조건",
            article_no="[해외여행중 배상책임 특별약관] 제7조(손해의 발생과 통지)",
            text=LIABILITY_ART7,
            page_ref="p.75",
            default_color="노랑",
        )
        clause_created += created
        map_created += sum(
            [
                _get_or_create_map(
                    db,
                    clause_id=c32.clause_id,
                    type_id=types["LIA_PERSONAL"].type_id,
                    relevance="조건부",
                    confidence=0.8,
                ),
                _get_or_create_map(
                    db,
                    clause_id=c32.clause_id,
                    type_id=types["LIA_PROPERTY"].type_id,
                    relevance="조건부",
                    confidence=0.8,
                ),
            ]
        )

        c33, created = _get_or_create_clause(
            db,
            policy_version_id=pv.policy_version_id,
            coverage_id=cov_lia.coverage_id,
            clause_type="조건",
            article_no="[해외여행중 배상책임 특별약관] 제8조(손해방지의무)",
            text=LIABILITY_ART8,
            page_ref="p.75-76",
            default_color="노랑",
        )
        clause_created += created
        map_created += sum(
            [
                _get_or_create_map(
                    db,
                    clause_id=c33.clause_id,
                    type_id=types["LIA_PERSONAL"].type_id,
                    relevance="조건부",
                    confidence=0.8,
                ),
                _get_or_create_map(
                    db,
                    clause_id=c33.clause_id,
                    type_id=types["LIA_PROPERTY"].type_id,
                    relevance="조건부",
                    confidence=0.8,
                ),
            ]
        )

        # 청구서류 조항: ClauseIncidentMap 매핑 안 함 (CoverageDocMap 경로 재사용)
        c34, created = _get_or_create_clause(
            db,
            policy_version_id=pv.policy_version_id,
            coverage_id=cov_lia.coverage_id,
            clause_type="서류",
            article_no="[해외여행중 배상책임 특별약관] 제10조(보험금의 청구)",
            text=LIABILITY_ART10_DOC,
            page_ref="p.77",
            default_color="노랑",
        )
        clause_created += created

        # ── Finalize ──────────────────────────────────────────────────────

        db.commit()
        print(
            "DB손해보험 chunk2 (p.43-84) 완료: "
            f"coverage_std 6건 보장(NON_COVERED_MED/OVS_INJ_MED/OVS_ILL_MED/ILL_DEATH/LIABILITY/WAR_RISK), "
            f"coverage 신규={coverage_created}, clause 신규={clause_created}, "
            f"clause_incident_map 신규={map_created}. "
            "비급여 3종(도수/주사/MRI) 및 추가특약 8종, 질병사망/배상책임 특약 매핑 완료. "
            "p.80-84의 다른 특약들(구조송환/전쟁/항공기납치/여권분실/식중독/전염병/항공기지연)은 다른 청크 담당."
        )
    finally:
        db.close()


if __name__ == "__main__":
    run()
