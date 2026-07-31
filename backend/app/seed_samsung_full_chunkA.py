"""
삼성화재(insurer.code="SAMSUNG") 전체 재검토 — 청크 A(PDF p.16~46).
data/raw_pdfs/samsung_overseas_50002_0_20240401.pdf (총 252쪽)을 pdfplumber로
p.16~46 전체를 직접 읽고 대조한 결과를 반영한다.

## p.16~38 (보통약관 제9조~제38조, "제2관 보험금 지급절차" 후반부 ~ "제7관 분쟁의 조정 등")
직접 다 읽었다. 내용은 다음과 같고 전부 "사고가 뭐였나"(incident_type)와 무관한
계약 구조/행정 조항이다 — 억지로 끼워맞추지 않고 그대로 스킵한다.
- 제9조 보험금 받는 방법의 변경, 제10조 주소변경통지, 제11조 보험수익자의 지정,
  제12조 대표자의 지정 (p.16-18)
- 제13조 계약 전 알릴 의무, 제14조 상해보험계약 후 알릴 의무, 제15조 알릴 의무 위반의 효과,
  제16조 사기에 의한 계약 (p.18-23) — 고지의무 위반/해지 절차. 사고유형이 아니라
  "계약이 유효한가"를 다룬다.
- 제17조 보험계약의 성립, 제18조 청약의 철회, 제19조 약관교부 및 설명 의무 등,
  제20조 계약의 무효, 제21조 계약내용의 변경 등, 제22조 보험나이 등, 제23조 계약의 소멸
  (p.23-28)
- 제24조 제1회 보험료 및 회사의 보장개시, 제25조 강제집행 등으로 인하여 해지된 계약의
  특별부활(효력회복) (p.28-30)
- 제26조 계약자의 임의해지 및 피보험자의 서면동의 철회, 제26조의2 위법계약의 해지,
  제27조 중대사유로 인한 해지, 제28조 회사의 파산선고와 해지, 제29조 보험료의 환급
  (p.30-33)
- 제30조 분쟁의 조정, 제31조 관할법원, 제32조 소멸시효, 제33조 약관의 해석,
  제34조 설명서 교부 및 보험안내자료 등의 효력, 제35조 회사의 손해배상책임,
  제36조 개인정보보호, 제37조 준거법, 제38조 예금보험에 의한 지급보장 (p.33-35)
결론: 이 27개 조항 중 사고유형 분류에 쓸 만한 내용은 하나도 없다(확인 완료, 억지 매핑
없음). 유일하게 사고와 살짝 맞닿는 제24조⑤~⑦(주거지 출발 전/도착 후 사고 면책,
교통편 지연시 보험기간 자동연장)도 "언제부터 보장이 시작/끝나는가"라는 계약 유효기간
문제이지 "무슨 사고인가"의 문제가 아니라서 분류 대상에서 제외했다.

## p.36~38: "여행중 질병사망 및 질병 80%이상 고도후유장해 특별약관" (신규 담보)
CoverageStd ILL_DEATH로 새로 추가. 제1조(지급사유)·제2조(지급 세부규정)를 원문 그대로
Clause로 넣었다. **면책 조항은 이 특약 안에 별도로 없다** — 제3조(준용규정)가
"이 특별약관에 정하지 않은 사항은 보통약관을 따릅니다"라고만 되어 있어, 면책은
보통약관 제5조를 그대로 준용하는 것으로 보인다(원문에 별도 면책 조항이 없다는 사실
그대로 보고 — 지어내지 않음).

## p.39~46: "여행중 배상책임 특별약관" (신규 담보)
CoverageStd LIABILITY로 새로 추가. 제1조~제2조(지급사유/보상범위), 제3조(면책),
제4조(의무보험과의 관계, 조건), 제5조(지급한도, 제한), 제7조(손해통지, 조건),
제8조(손해방지의무, 조건), 제10조①(청구서류)를 원문 그대로 넣었다.
확인 결과 **대인/대물을 명시적으로 구분하는 조문은 없다** — 제1조·제2조는
"법률상의 배상책임"을 뭉뚱그려 정의하고 있어 LIA_PERSONAL·LIA_PROPERTY 둘 다에
직접 매핑했다. 다만 제3조(면책) 7호에 "피보험자가 소유·사용·관리하는 재물의 파손에
대한 배상책임은 면책하되, 호텔의 객실이나 객실내 동산에 끼치는 손해는 예외로 한다"는
문구가 원문 그대로 있어 — 이게 LIA_LODGING(임차물·호텔객실)의 실제 보장 근거다.
그래서 제3조는 LIA_PERSONAL/LIA_PROPERTY에는 면책으로, LIA_LODGING에는 (그 안에 있는
호텔객실 예외 문구를 근거로) 직접 관련으로 매핑했다.
제6조(타인을 위한 계약)·제9조(손해배상청구에 대한 회사의 해결)·제11조(보험금의 분담)·
제12조(대위권)·제13조(합의·절충·중재·소송의 협조·대행 등)·제14조(양도)·제15조(조사)·
제16조(준용규정)는 보통약관의 계약행정 조항과 성격이 같아(대위권/양도/조사 등) 이번
청크에서는 넣지 않았다 — 사고유형 판단에 직접 쓰이는 지급사유/면책/제한/조건/서류만
우선 담았다.

멱등성: Coverage는 raw_name, Clause는 (coverage_id, article_no, text) 조합, ClauseIncidentMap은
(clause_id, type_id) 조합으로 이미 있으면 건너뛴다.
"""
from app.database import SessionLocal
from app import models  # noqa: F401
from app.models.kb import (
    Clause, ClauseIncidentMap, Coverage, IncidentType, Insurer, PolicyVersion, Product,
)
from app.services.kb_seed_common import get_or_create_coverage_std

# ---------------------------------------------------------------------------
# 여행중 질병사망 및 질병 80%이상 고도후유장해 특별약관 (p.36-38)
# ---------------------------------------------------------------------------

ILL_DEATH_CLAUSE1_TEXT = (
    "① 회사는 피보험자가 보통약관 제3조(보험금의 지급사유)의 해외여행 도중에 다음 사항 중 "
    "어느 한 가지의 경우에 해당되는 사유가 발생한 때에는 보험수익자에게 약정한 보험금을 "
    "지급합니다. "
    "1. 보험기간 중 질병으로 인하여 사망한 경우 : 사망보험금 "
    "2. 보험기간 중 진단확정된 질병으로 장해분류표([별표1] 참조. 이하 같습니다)에서 정한 "
    "장해지급률이 80% 이상에 해당하는 장해상태가 되었을 때 : 고도후유장해보험금 "
    "② 제1항에도 불구하고 해외여행 도중에 발생한 질병을 직접원인으로 하여 보험기간 마지막날"
    "로부터 30일 이내에 사망하거나 또는 80% 이상 후유장해가 남았을 경우에도 동일하게 보"
    "상하여 드립니다."
)

ILL_DEATH_CLAUSE2_TEXT = (
    "① 「호스피스·완화의료 및 임종과정에 있는 환자의 연명의료 결정에 관한 법률」에 따른 연명"
    "의료중단 등 결정 및 그 이행으로 피보험자가 사망하는 경우 연명의료중단 등 결정 및 그 "
    "이행은 제1조(보험금의 종류 및 지급사유) 제1항 제1호 ‘사망’의 원인 및 ‘사망보험금’ 지"
    "급에 영향을 미치지 않습니다. "
    "② 제1조(보험금의 종류 및 지급사유) 제1항 제2호에도 불구하고 영구히 고정된 증상은 아니"
    "지만 치료종결 후 한시적으로 나타나는 장해에 대하여는 그 기간이 5년 이상인 때에는 해"
    "당 장해 지급률의 20%를 후유장해지급률로 하여 제5항을 적용합니다. "
    "③ 제1조(보험금의 종류 및 지급사유) 제1항 제2호에서 장해지급률이 질병의 진단확정일부터 "
    "180일 이내에 확정되지 않는 경우에는 질병의 진단확정일부터 180일이 되는 날의 의사진"
    "단에 기초하여 고정될 것으로 인정되는 상태를 장해지급률로 결정합니다. 다만, 장해지급"
    "률이 결정된 이후 보장을 받을 수 있는 기간(계약의 효력이 없어진 경우에는 보험기간이 "
    "10년 이상인 계약은 질병의 진단확정일부터 2년 이내로 하고, 보험기간이 10년 미만인 계"
    "약은 질병의 진단확정일부터 1년)중에 장해상태가 더 악화되는 경우에는 그 악화된 장해상"
    "태를 기준으로 장해지급률을 결정하되 장해분류표에 장해판정 시기가 별도로 정해진 경우"
    "에는 그에 따릅니다. "
    "④ 장해분류표에 해당되지 않는 후유장해는 피보험자의 직업, 연령, 신분 또는 성별 등에 관"
    "계없이 신체의 장해정도에 따라 장해분류표의 구분에 준하여 지급액을 결정합니다. 다만, "
    "장해분류표의 각 장해분류별 최저 지급률 장해정도에 이르지 않는 후유장해에 대하여는 고"
    "도후유장해보험금을 지급하지 않습니다. "
    "⑤ 같은 질병으로 두 가지 이상의 후유장해가 생긴 경우에는 후유장해 지급률을 더하여 지급"
    "합니다. 다만, 장해분류표의 각 신체부위별 판정기준에 별도로 정한 경우에는 그 기준에 "
    "따릅니다. "
    "⑥ 제5항에도 불구하고 동일한 신체부위에 장해분류표상의 2가지 이상의 장해가 발생한 경우"
    "에는 더하지 않고 그 중 높은 지급률을 적용합니다. 다만, 장해분류표의 각 신체부위별 판"
    "정기준에서 별도로 정한 경우에는 그 기준에 따릅니다. "
    "⑦ 다른 질병으로 인하여 후유장해가 2회 이상 발생하였을 경우에는 그 때마다 이에 해당하는 "
    "후유장해지급률을 결정합니다. 그러나 그 후유장해가 이미 고도후유장해보험금을 지급받은 "
    "동일한 부위에 가중된 때에는 최종 장해상태에 해당하는 고도후유장해보험금에서 이미 지"
    "급받은 고도후유장해보험금을 차감하여 지급합니다. 다만, 장해분류표의 각 신체부위별 판"
    "정기준에서 별도로 정한 경우에는 그 기준에 따릅니다. "
    "⑧ 이미 다음 중 한가지의 경우에 해당하는 후유장해가 있었던 피보험자에게 그 신체의 동일"
    "부위에 또다시 제7항에 규정하는 후유장해상태가 발생하였을 경우에는 다음 중 한가지의 "
    "경우에 해당되는 후유장해에 대한 고도후유장해보험금이 지급된 것으로 보고 최종 후유장"
    "해상태에 해당되는 고도후유장해보험금에서 이미 지급받은 것으로 간주한 고도후유장해보"
    "험금을 차감하여 지급합니다. "
    "1. 이 계약의 보장개시 전의 원인에 의하거나 또는 그 이전에 발생한 후유장해로 고도후유"
    "장해보험금의 지급사유가 되지 않았던 후유장해 "
    "2. 제1호 이외에 이 계약의 규정에 의하여 고도후유장해보험금의 지급사유가 되지 않았던 "
    "후유장해 또는 고도후유장해보험금이 지급되지 않았던 후유장해 "
    "⑨ 피보험자와 회사가 피보험자의 장해지급률에 대해 합의에 도달하지 못하는 때에는 피보험"
    "자와 회사가 동의하는 제3자를 정하고 그 제3자의 의견에 따를 수 있습니다. 제3자는 "
    "「의료법 제3조(의료기관)」의 규정에 의한 종합병원 소속 전문의 중에 정하며, 장해판정"
    "에 소요되는 의료비용은 회사가 전액 부담합니다."
)

ILL_DEATH_CLAUSE3_TEXT = "이 특별약관에 정하지 않은 사항은 보통약관을 따릅니다."


# ---------------------------------------------------------------------------
# 여행중 배상책임 특별약관 (p.39-46)
# ---------------------------------------------------------------------------

LIA_CLAUSE1_TEXT = (
    "회사는 피보험자가 보통약관 제3조(보험금의 지급사유)의 여행도중에 생긴 보험사고로 인하여 "
    "피해자에게 법률상의 배상책임을 부담함으로써 입은 손해를 이 특별약관에 따라 보상하여 드립니다."
)

LIA_CLAUSE2_TEXT = (
    "회사가 보상하는 손해의 범위는 아래와 같습니다. "
    "1. 피보험자가 피해자에게 지급할 책임을 지는 법률상의 손해배상금 "
    "2. 계약자 또는 피보험자가 지출한 아래의 비용 "
    "가. 피보험자가 제8조(손해방지의무) 제1항 제1호의 손해의 방지 또는 경감을 위하여 지"
    "출한 필요 또는 유익하였던 비용 "
    "나. 피보험자가 제8조(손해방지의무) 제1항 제2호의 제3자로부터 손해의 배상을 받을 수 "
    "있는 그 권리를 지키거나 행사하기 위하여 지출한 필요 또는 유익하였던 비용 "
    "다. 피보험자가 지급한 소송비용, 변호사비용, 중재, 화해 또는 조정에 관한 비용 "
    "라. 보험증권상 보상한도액내의 금액에 대한 공탁보증보험료. 그러나 회사는 그러한 보증"
    "자체를 제공할 책임은 부담하지 않습니다. "
    "마. 피보험자가 제9조(손해배상청구에 대한 회사의 해결) 제2항 및 제3항의 회사의 요구"
    "에 따르기 위하여 지출한 비용"
)

LIA_CLAUSE3_TEXT = (
    "회사는 보통약관 제5조(보험금을 지급하지 않는 사유) 제1항의 제1호, 제3호 또는 제5호 및 "
    "아래의 사유로 손해배상책임을 부담하게 됨으로써 입은 손해는 보상하여 드리지 않습니다. "
    "1. 피보험자의 직접적인 직무수행으로 인한 배상책임 "
    "2. 피보험자의 직무용으로만 사용되는 동산의 소유, 사용 또는 관리로 인한 배상책임 "
    "3. 피보험자가 소유, 사용 또는 관리하는 부동산으로 인한 배상책임 "
    "4. 피보험자의 근로자가 피보험자의 업무에 종사중에 입은 신체의 장해로 인한 배상책임. "
    "단, 피보험자의 가사사용인에 대하여는 이와 같지 않습니다. "
    "5. 피보험자와 타인간에 손해배상에 관한 약정이 있는 경우 그 약정에 따라 가중된 배상책"
    "임 "
    "6. 피보험자와 세대를 같이하는 친족(「민법 제777조」에 따른 8촌 이내의 혈족, 4촌 이내"
    "의 인척 및 배우자) 및 여행과정을 같이 하는 친족에 대한 배상책임 "
    "7. 피보험자가 소유, 사용 또는 관리하는 재물의 파손에 대하여 그 재물에 대하여 정당한 "
    "권리를 가진 사람에게 부담하는 배상책임. 단, 호텔의 객실이나 객실내의 동산에 끼치"
    "는 손해에 대하여는 이와 같지 않습니다. "
    "8. 피보험자의 심신상실로 인한 배상책임 "
    "9. 피보험자 또는 피보험자의 지시에 따른 폭행 또는 구타로 인한 배상책임 "
    "10. 항공기, 선박, 차량(원동력이 인력에 의한 것을 제외합니다), 총기(공기총은 제외합니"
    "다)의 소유, 사용 또는 관리로 인한 배상책임"
)

LIA_CLAUSE4_TEXT = (
    "① 회사는 이 약관에 의하여 보상하여야 하는 금액이 의무보험에서 보상하는 금액을 초과할 "
    "때에 한하여 그 초과액만을 보상합니다. 다만, 의무보험이 다수인 경우에는 제11조(보험금"
    "의 분담)를 따릅니다. "
    "② 제1항의 의무보험은 피보험자가 법률에 의하여 의무적으로 가입하여야 하는 보험으로서 공"
    "제계약(각종 공제회에 가입되어 있는 계약)을 포함합니다. "
    "③ 피보험자가 의무보험에 가입하여야 함에도 불구하고 가입하지 않은 경우에는 그가 가입했"
    "더라면 의무보험에서 보상했을 금액을 제1항의 “의무보험에서 보상하는 금액”으로 봅니다."
)

LIA_CLAUSE5_TEXT = (
    "① 회사는 1회의 보험사고에 대하여 다음과 같이 보상합니다. 이 경우 보상한도액과 자기부담"
    "금은 각각 보험증권에 기재된 금액을 말합니다. "
    "1. 제2조(보상하는 손해의 범위) 제1호의 손해배상금: 보상한도액을 한도로 보상하되, 자"
    "기부담금이 약정된 경우에는 그 자기부담금을 초과한 부분만 보상합니다. "
    "2. 제2조(보상하는 손해의 범위) 제2호 가목, 나목 또는 마목의 비용: 비용의 전액을 보상"
    "합니다. "
    "3. 제2조(보상하는 손해의 범위) 제2호 다목 또는 라목의 비용: 이 비용과 제1호에 의한 "
    "보상액의 합계액을 보상한도액의 한도내에서 보상합니다. "
    "② 보험기간 중 발생하는 사고에 대한 회사의 보상총액은 보험증권에 기재된 총 보상한도액을 "
    "한도로 합니다."
)

LIA_CLAUSE7_TEXT = (
    "① 계약자 또는 피보험자는 아래와 같은 사실이 있는 경우에는 지체없이 그 내용을 서면으로 "
    "회사에 알려야 합니다. "
    "1. 사고가 발생하였을 경우 사고가 발생한 때와 곳, 피해자의 주소와 성명, 사고 상황 및 "
    "이들 사항의 증인이 있을 경우 그 주소와 성명 "
    "2. 피해자로부터 손해배상청구를 받았을 경우 "
    "3. 피해자로부터 손해배상책임에 관한 소송을 제기받았을 경우 "
    "② 계약자 또는 피보험자가 제1항 각 호의 통지를 게을리하여 손해가 증가된 때에는 회사는 "
    "그 증가된 손해를 보상하여 드리지 않으며, 제1항 제3호의 통지를 게을리 한 때에는 소송"
    "비용과 변호사비용도 보상하여 드리지 않습니다."
)

LIA_CLAUSE8_TEXT = (
    "① 보험사고가 생긴 때에는 계약자 또는 피보험자는 아래의 사항을 이행하여야 합니다. "
    "1. 손해의 방지 또는 경감을 위하여 노력하는 일(피해자에 대한 응급처치, 긴급호송 또는 "
    "그 밖의 긴급조치를 포함합니다) "
    "2. 제3자로부터 손해의 배상을 받을 수 있는 경우에는 그 권리를 지키거나 행사하기 위한 "
    "필요한 조치를 취하는 일 "
    "3. 손해배상책임의 전부 또는 일부에 관하여 지급(변제), 승인 또는 화해를 하거나 소송,중"
    "재 또는 조정을 제기하거나 신청하고자 할 경우에는 미리 회사의 동의를 받는 일 "
    "② 계약자 또는 피보험자가 정당한 이유없이 위 제1항의 의무를 이행하지 않았을 때에는 제2"
    "조(보상하는 손해의 범위)의 손해에서 다음의 금액을 뺍니다. "
    "1. 제1항 제1호의 경우에는 그 노력을 하였더라면 손해를 방지 또는 경감할 수 있었던 금"
    "액 "
    "2. 제1항 제2호의 경우에는 제3자로부터 손해의 배상을 받을 수 있었던 금액 "
    "3. 제1항 제3호의 경우에는 소송비용(중재 또는 조정에 관한 비용 포함) 및 변호사비용과 "
    "회사의 동의를 받지 않은 행위에 의하여 증가된 손해"
)

LIA_CLAUSE10_DOC_TEXT = (
    "① 피보험자가 보험금을 청구할 때에는 다음의 서류를 회사에 제출하여야 합니다. "
    "1. 보험금 청구서 "
    "2. 신분증(주민등록증 또는 운전면허증 등 사진이 부착된 정부기관발행 신분증, 본인이 아"
    "닌 경우에는 본인의 인감증명서 또는 본인서명사실확인서 포함) "
    "3. 손해배상금 및 그 밖의 비용을 지급하였음을 증명하는 서류 "
    "4. 회사가 요구하는 그 밖의 서류"
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
        if not pv:
            print("삼성화재 policy_version을 찾을 수 없습니다.")
            return

        types = {t.l2_code: t for t in db.query(IncidentType).all()}
        required = ["ILL_DEATH_DISABILITY", "LIA_PERSONAL", "LIA_PROPERTY", "LIA_LODGING"]
        missing = [c for c in required if c not in types]
        if missing:
            print(f"incident_type 사전에 없는 코드: {missing}. seed_incident_types를 먼저 실행하세요.")
            return

        std_ill_death = get_or_create_coverage_std(db, "ILL_DEATH", "질병사망·고도후유장해", "질병", False)
        std_liability = get_or_create_coverage_std(db, "LIABILITY", "배상책임", "배상책임", False)

        clause_created = map_created = coverage_created = 0

        # ------------------------------------------------------------------
        # 1) 여행중 질병사망 및 질병 80%이상 고도후유장해 특별약관
        # ------------------------------------------------------------------
        cov_ill = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "여행중 질병사망 및 질병 80%이상 고도후유장해 특별약관",
            )
            .first()
        )
        if not cov_ill:
            cov_ill = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_ill_death.coverage_std_id,
                raw_name="여행중 질병사망 및 질병 80%이상 고도후유장해 특별약관",
                definition=ILL_DEATH_CLAUSE1_TEXT,
                limit_amount="장해분류표([별표1]) 기준 장해지급률 80% 이상일 때 고도후유장해보험금 지급",
                deductible=None,
                waiting_condition="장해지급률이 질병 진단확정일부터 180일 이내 미확정 시 180일 시점 의사진단 기준(제2조③)",
            )
            db.add(cov_ill)
            db.flush()
            coverage_created += 1

        clause_ill_1, c1 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_ill.coverage_id,
            clause_type="보장정의", article_no="[여행중 질병사망 및 질병 80%이상 고도후유장해 특별약관] 제1조(보험금의 종류 및 지급사유)",
            text=ILL_DEATH_CLAUSE1_TEXT, page_ref="p.36", default_color="파랑",
        )
        clause_ill_2, c2 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_ill.coverage_id,
            clause_type="제한", article_no="[여행중 질병사망 및 질병 80%이상 고도후유장해 특별약관] 제2조(보험금 지급에 관한 세부규정)",
            text=ILL_DEATH_CLAUSE2_TEXT, page_ref="p.36-37", default_color="초록",
        )
        # 제3조(준용규정)는 사고유형과 무관한 순수 참조조항이라 clause_incident_map에 걸지 않는다.
        clause_ill_3, c3 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_ill.coverage_id,
            clause_type="공통", article_no="[여행중 질병사망 및 질병 80%이상 고도후유장해 특별약관] 제3조(준용규정)",
            text=ILL_DEATH_CLAUSE3_TEXT, page_ref="p.38", default_color="회색",
        )
        clause_created += sum([c1, c2, c3])

        ill_death_type = types["ILL_DEATH_DISABILITY"]
        map_created += sum([
            _get_or_create_map(db, clause_id=clause_ill_1.clause_id, type_id=ill_death_type.type_id, relevance="직접", confidence=1.0),
            _get_or_create_map(db, clause_id=clause_ill_2.clause_id, type_id=ill_death_type.type_id, relevance="조건부", confidence=0.9),
        ])

        # ------------------------------------------------------------------
        # 2) 여행중 배상책임 특별약관
        # ------------------------------------------------------------------
        cov_lia = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "여행중 배상책임 특별약관",
            )
            .first()
        )
        if not cov_lia:
            cov_lia = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_liability.coverage_std_id,
                raw_name="여행중 배상책임 특별약관",
                definition=LIA_CLAUSE1_TEXT,
                limit_amount="보험증권 기재 보상한도액(1회 사고당) 및 총 보상한도액 한도(제5조)",
                deductible="보험증권 기재 자기부담금(약정된 경우, 손해배상금에만 적용)",
                waiting_condition=None,
            )
            db.add(cov_lia)
            db.flush()
            coverage_created += 1

        clause_lia_1, l1 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_lia.coverage_id,
            clause_type="보장정의", article_no="[여행중 배상책임 특별약관] 제1조(보상하는 손해)",
            text=LIA_CLAUSE1_TEXT, page_ref="p.39", default_color="파랑",
        )
        clause_lia_2, l2 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_lia.coverage_id,
            clause_type="보장정의", article_no="[여행중 배상책임 특별약관] 제2조(보상하는 손해의 범위)",
            text=LIA_CLAUSE2_TEXT, page_ref="p.39-40", default_color="파랑",
        )
        clause_lia_3, l3 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_lia.coverage_id,
            clause_type="면책", article_no="[여행중 배상책임 특별약관] 제3조(보상하지 않는 손해)",
            text=LIA_CLAUSE3_TEXT, page_ref="p.40", default_color="빨강",
        )
        clause_lia_4, l4 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_lia.coverage_id,
            clause_type="조건", article_no="[여행중 배상책임 특별약관] 제4조(의무보험과의 관계)",
            text=LIA_CLAUSE4_TEXT, page_ref="p.40-41", default_color="노랑",
        )
        clause_lia_5, l5 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_lia.coverage_id,
            clause_type="제한", article_no="[여행중 배상책임 특별약관] 제5조(보험금 등의 지급한도)",
            text=LIA_CLAUSE5_TEXT, page_ref="p.41", default_color="초록",
        )
        clause_lia_7, l7 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_lia.coverage_id,
            clause_type="조건", article_no="[여행중 배상책임 특별약관] 제7조(손해의 발생과 통지)",
            text=LIA_CLAUSE7_TEXT, page_ref="p.41-42", default_color="노랑",
        )
        clause_lia_8, l8 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_lia.coverage_id,
            clause_type="조건", article_no="[여행중 배상책임 특별약관] 제8조(손해방지의무)",
            text=LIA_CLAUSE8_TEXT, page_ref="p.42", default_color="노랑",
        )
        # 청구서류 조항: ClauseIncidentMap에는 매핑하지 않는다(seed_clause_incident_map.py의
        # SKIP_CLAUSE_TYPES 원칙과 동일 — CoverageDocMap 경로로 별도 소비).
        clause_lia_10doc, l10 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_lia.coverage_id,
            clause_type="서류", article_no="[여행중 배상책임 특별약관] 제10조(보험금의 지급절차) ①항",
            text=LIA_CLAUSE10_DOC_TEXT, page_ref="p.43", default_color="노랑",
        )
        clause_created += sum([l1, l2, l3, l4, l5, l7, l8, l10])

        lia_personal = types["LIA_PERSONAL"]
        lia_property = types["LIA_PROPERTY"]
        lia_lodging = types["LIA_LODGING"]

        map_created += sum([
            # 제1조·제2조: 지급사유가 대인/대물을 명시적으로 구분하지 않고 "법률상 배상책임"을
            # 뭉뚱그려 정의하므로 둘 다에 직접 매핑한다(임차물은 이 조항에 문구가 없어 제외).
            _get_or_create_map(db, clause_id=clause_lia_1.clause_id, type_id=lia_personal.type_id, relevance="직접", confidence=0.9),
            _get_or_create_map(db, clause_id=clause_lia_1.clause_id, type_id=lia_property.type_id, relevance="직접", confidence=0.9),
            _get_or_create_map(db, clause_id=clause_lia_2.clause_id, type_id=lia_personal.type_id, relevance="직접", confidence=0.9),
            _get_or_create_map(db, clause_id=clause_lia_2.clause_id, type_id=lia_property.type_id, relevance="직접", confidence=0.9),
            # 제3조(면책): 전반적으로 대인/대물 면책 사유를 담고 있어 두 유형 모두에 면책으로
            # 매핑한다. 다만 7호에 "호텔의 객실이나 객실내의 동산에 끼치는 손해는 이와 같지
            # 않습니다"(=면책 예외=보장한다)라는 원문 그대로의 문구가 있어, 이 조항이
            # LIA_LODGING(임차물·호텔객실)의 실제 보장 근거이기도 하다 — 직접 관련으로도 건다.
            _get_or_create_map(db, clause_id=clause_lia_3.clause_id, type_id=lia_personal.type_id, relevance="면책", confidence=1.0),
            _get_or_create_map(db, clause_id=clause_lia_3.clause_id, type_id=lia_property.type_id, relevance="면책", confidence=1.0),
            _get_or_create_map(db, clause_id=clause_lia_3.clause_id, type_id=lia_lodging.type_id, relevance="직접", confidence=0.85),
            # 제4조(의무보험과의 관계, 조건부 지급규정)
            _get_or_create_map(db, clause_id=clause_lia_4.clause_id, type_id=lia_personal.type_id, relevance="조건부", confidence=0.8),
            _get_or_create_map(db, clause_id=clause_lia_4.clause_id, type_id=lia_property.type_id, relevance="조건부", confidence=0.8),
            # 제5조(지급한도) — 대인/대물/임차물 모두에 공통 적용되는 한도 규정
            _get_or_create_map(db, clause_id=clause_lia_5.clause_id, type_id=lia_personal.type_id, relevance="조건부", confidence=0.9),
            _get_or_create_map(db, clause_id=clause_lia_5.clause_id, type_id=lia_property.type_id, relevance="조건부", confidence=0.9),
            _get_or_create_map(db, clause_id=clause_lia_5.clause_id, type_id=lia_lodging.type_id, relevance="조건부", confidence=0.8),
            # 제7조(손해통지 의무), 제8조(손해방지의무) — 지급 조건
            _get_or_create_map(db, clause_id=clause_lia_7.clause_id, type_id=lia_personal.type_id, relevance="조건부", confidence=0.8),
            _get_or_create_map(db, clause_id=clause_lia_7.clause_id, type_id=lia_property.type_id, relevance="조건부", confidence=0.8),
            _get_or_create_map(db, clause_id=clause_lia_8.clause_id, type_id=lia_personal.type_id, relevance="조건부", confidence=0.8),
            _get_or_create_map(db, clause_id=clause_lia_8.clause_id, type_id=lia_property.type_id, relevance="조건부", confidence=0.8),
        ])

        db.commit()
        print(
            "samsung 전체 재검토 청크A(p.16-46) 완료: "
            f"coverage_std 2건 확보(ILL_DEATH/LIABILITY), coverage 신규={coverage_created}, "
            f"clause 신규={clause_created}, clause_incident_map 신규={map_created}. "
            "p.16-38(보통약관 제9조~제38조)는 전부 사고유형과 무관한 계약행정 조항으로 확인(매핑 없음)."
        )
    finally:
        db.close()


if __name__ == "__main__":
    run()
