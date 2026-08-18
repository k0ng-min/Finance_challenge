"""
삼성화재(insurer.code="SAMSUNG") 2026년판 약관 청크 D.
backend/data/processed/samsung_overseas_2026_full_text.txt 페이지 182-219.

## 담당 범위

### 페이지 182-184 (항공기 지연(2시간 이상)·결항 손해(실손형) (국내 출국 제외))
CoverageStd FLIGHT_DELAY. 제1조-제5조:
- 제1조: 보상하는 손해 (보장정의)
- 제2조: 보상하지 않는 손해 (면책)
- 제3조: 보험금의 청구 (서류)
- 제4조: 보험금의 분담 (제한)
- 제5조: 준용규정 (공통)

### 페이지 185-186 (수하물 지연(6시간 이상)·손실 추가비용)
새로운 담보. 제1조-제5조.

### 페이지 188-190 (항공기 지연사고발생 반려견(묘) 돌봄서비스 추가비용 보상)
CoverageStd PET_CARE. 제1조-제5조.

### 페이지 191 (여행중 식중독보상금(2일이상 입원))
CoverageStd FOOD_POISONING. 제1조-제3조.

### 페이지 192-193 (여행중 특정감염병보상금)
CoverageStd INFECTIOUS_DISEASE. 제1조-제4조.

### 페이지 194-195 (여행중 중단사고발생 추가비용)
CoverageStd TRIP_INTERRUPTION. 제1조-제5조.

### 페이지 196-197 (여행중 여권분실 재발급비용)
CoverageStd PASSPORT_LOSS. 제1조-제4조.

### 페이지 198-201 (여행중 자택 도난손해(가재) 보장)
CoverageStd HOME_THEFT. 제1조-제9조.

### 페이지 202 (의사상자 상해위험)
CoverageStd GOOD_SAMARITAN. 제1조-제3조.

### 페이지 203 (전쟁위험)
CoverageStd WAR_RISK. 제1조-제4조.

### 페이지 204-205 (부부확장, 가족확장)
계약구조 특약. 사고판단 무관, 스크립트 작성 생략.
"""

from app.database import SessionLocal
from app import models  # noqa: F401
from app.models.kb import Clause, Coverage, PolicyVersion, Product
from app.services.kb_seed_common import get_or_create_coverage_std

PRODUCT_CODE = "SAMSUNG-OVERSEAS-2026"
VERSION_LABEL = "2026수집본"


def run():
    """시드 함수. 멱등성: policy_version_id + text 조합이 있으면 스킵."""
    db = SessionLocal()
    try:
        # 기존 Product/PolicyVersion 조회
        product = db.query(Product).filter_by(product_code=PRODUCT_CODE).first()
        if not product:
            print("ERROR: Product not found. Run seed_samsung_2026_a.py first.")
            return

        policy_version = db.query(PolicyVersion).filter_by(
            product_id=product.product_id,
            version_label=VERSION_LABEL
        ).first()
        if not policy_version:
            print("ERROR: PolicyVersion not found. Run seed_samsung_2026_a.py first.")
            return

        # 이 청크가 이미 시드됐으면(Coverage 생성이 idempotent하지 않으므로) 통째로 건너뛴다.
        if db.query(Coverage).filter_by(
            policy_version_id=policy_version.policy_version_id,
            raw_name="항공기 지연(2시간 이상)·결항 손해(실손형) (국내 출국 제외)"
        ).first():
            print("삼성화재 2026년판 청크 D: 이미 시드됨, 건너뜀.")
            return

        # 1. 항공기 지연(2시간 이상)·결항 손해(실손형) (국내 출국 제외) (p.182-184)
        flight_delay_std = get_or_create_coverage_std(
            db, "FLIGHT_DELAY", "항공기 지연·결항", "항공", False
        )

        coverage_flight_delay = Coverage(
            policy_version_id=policy_version.policy_version_id,
            coverage_std_id=flight_delay_std.coverage_std_id,
            raw_name="항공기 지연(2시간 이상)·결항 손해(실손형) (국내 출국 제외)",
            definition="국제선 항공편 2시간 이상 지연 또는 결항으로 인한 식음료·편의시설 비용",
            limit_amount=None,
            deductible=None,
            waiting_condition="2시간 이상 지연 또는 결항"
        )
        db.add(coverage_flight_delay)
        db.flush()

        # Clause: 제1조 (보상하는 손해)
        clause1_text = (
            "① 회사는 피보험자가 보험기간 중 아래의 보험사고로 인하여 추가적으로 부담한 비용 손해를 이 특별약관에서 정한 바에 따라 "
            "보험가입금액 한도 내에서 보상합니다. 보장항목: 1. 항공편이 2시간 이상 4시간 미만 지연되는 경우 "
            "2. 항공편이 2시간 이상 4시간 미만 지연되고, 이로 인해 연결항공편으로의 환승에 필요한 시간이 부족하여 "
            "(공항 도착시간으로부터 연결항공편 출발까지 남은 시간이 1시간 이하인 경우를 말합니다) 탑승에 실패하는 경우 "
            "3. 제1호 또는 제2호의 경우 보험가입금액은 10만원으로 함 "
            "1. 항공편이 4시간 이상 지연되거나 결항되는 경우 "
            "2. 항공편이 4시간 이상 지연되고, 이로 인해 연결항공편으로의 환승에 필요한 시간이 부족하여 "
            "(공항 도착시간으로부터 연결항공편 출발까지 남은 시간이 1시간 이하인 경우를 말합니다) 탑승에 실패하는 경우 "
            "② 제1항에도 불구하고, 국내공항에서 출발하는 국제선 항공편(국내공항과 외국공항 사이를 운항하는 항공편을 의미하며 "
            "국내외 항공사를 모두 포함합니다. 환승 전용 내항기 및 이와 유사한 성격의 국내선은 제외됩니다)이 지연 또는 결항된 "
            "경우는 보상하지 않습니다. "
            "③ 제1항의 보험사고로 인하여 회사가 보상하는 손해는 아래와 같습니다. "
            "1. 지연된 항공편 또는 대체 항공편을 기다리는 동안 피보험자가 실제로 지출한 식음료 비용(식당, 편의점 등) "
            "2. 지연된 항공편 또는 대체 항공편을 기다리는 동안 피보험자가 실제로 지출한 편의시설 비용(라운지, 숙박시설, 휴게시설 등) "
            "및 편의시설로의 이동을 위한 교통비 "
            "④ 회사는 피보험자가 보험기간 중 유료승객으로서 정기항공편을 이용하던 중에 발생한 사고에 한하여 보상합니다."
        )
        if not db.query(Clause).filter_by(
            policy_version_id=policy_version.policy_version_id,
            text=clause1_text
        ).first():
            db.add(Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=coverage_flight_delay.coverage_id,
                clause_type="보장정의",
                article_no="[항공기 지연(2시간 이상)·결항 손해(실손형) (국내 출국 제외) 특별약관] 제1조(보상하는 손해)",
                text=clause1_text,
                page_ref="p.182-183",
                default_color="파랑"
            ))

        # Clause: 제2조 (보상하지 않는 손해)
        clause2_text = (
            "회사는 다음 중 어느 한 가지의 경우가 발생하거나 또는 해당 경우에 의하여 보험금 지급사유가 발생한 때에는 보험금을 "
            "지급하지 않습니다. "
            "1. 명시적 또는 실질적 형태의 정부의 육, 해, 공 군사력에 의한 선포 또는 비선포된 전쟁 또는 이에 따르는 행위 "
            "2. 피보험자 또는 그 수혜자들에 의하거나 또는 이들을 위해 행해진 불법적인 행동 "
            "3. 교통수단의 조작자 또는 조종자로 종사하는 상황에서 발생한 손실 "
            "4. 피보험자가 출발계획시간이 도래하기전에 구매한 항공권을 취소한 경우 "
            "5. 보험사고로 인하여 피보험자가 직접적으로 부담한 비용이 아닌 모든 간접 손해 "
            "(예정되었던 여행일정(숙박, 다른 교통수단, 관광지의 입장권 등)의 취소에 따른 수수료 등) "
            "6. 대체항공편에 탑승한 이후에 발생하는 비용(대체항공편이 착륙한 지역에서의 비용 등)"
        )
        if not db.query(Clause).filter_by(
            policy_version_id=policy_version.policy_version_id,
            text=clause2_text
        ).first():
            db.add(Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=coverage_flight_delay.coverage_id,
                clause_type="면책",
                article_no="[항공기 지연(2시간 이상)·결항 손해(실손형) (국내 출국 제외) 특별약관] 제2조(보상하지 않는 손해)",
                text=clause2_text,
                page_ref="p.183",
                default_color="빨강"
            ))

        # 2. 식중독보상금(2일이상 입원) (p.191)
        food_poisoning_std = get_or_create_coverage_std(
            db, "FOOD_POISONING", "식중독보상금", "질병", False
        )

        coverage_food_poisoning = Coverage(
            policy_version_id=policy_version.policy_version_id,
            coverage_std_id=food_poisoning_std.coverage_std_id,
            raw_name="여행중 식중독보상금(2일이상 입원)",
            definition="해외여행 도중 음식물 섭취로 인한 식중독으로 2일 이상 입원시 보상금 지급",
            limit_amount=None,
            deductible=None,
            waiting_condition="2일 이상 입원"
        )
        db.add(coverage_food_poisoning)
        db.flush()

        # Clause: 제1조 (보험금의 종류 및 지급사유)
        clause_fp1_text = (
            "① 회사는 피보험자가 해외여행 도중에 음식물의 섭취로 인해 중독(이하 식중독이라 합니다)이 발생하고 그 직접적인 "
            "결과로 병원 또는 의원(한방병원 또는 한의원을 포함합니다)에 2일 이상 입원하여 치료를 받은 경우 이 특약의 보험가입금액을 "
            "보험수익자(보험수익자의 지정이 없을 때에는 피보험자)에게 식중독보상금으로 지급합니다. 다만, 입원하지 않고 외래진료만 "
            "받은 경우는 제외합니다. "
            "② 제1항에서 식중독이라 함은 음식물을 먹고 생기는 구토, 설사, 복통을 주요 증세로 하는 급성질환으로써 "
            "【별표2(식중독 분류표)】에 해당하는 질병으로 분류되는 경우를 말합니다."
        )
        if not db.query(Clause).filter_by(
            policy_version_id=policy_version.policy_version_id,
            text=clause_fp1_text
        ).first():
            db.add(Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=coverage_food_poisoning.coverage_id,
                clause_type="보장정의",
                article_no="[여행중 식중독보상금(2일이상 입원) 특별약관] 제1조(보험금의 종류 및 지급사유)",
                text=clause_fp1_text,
                page_ref="p.191",
                default_color="파랑"
            ))

        # 3. 특정감염병보상금 (p.192-193)
        infectious_disease_std = get_or_create_coverage_std(
            db, "INFECTIOUS_DISEASE", "특정감염병보상금", "질병", False
        )

        coverage_infectious = Coverage(
            policy_version_id=policy_version.policy_version_id,
            coverage_std_id=infectious_disease_std.coverage_std_id,
            raw_name="여행중 특정감염병보상금",
            definition="해외여행 도중 특정감염병으로 진단확정시 보상금 지급",
            limit_amount=None,
            deductible=None,
            waiting_condition="특정감염병 진단확정"
        )
        db.add(coverage_infectious)
        db.flush()

        # Clause: 제1조 (보상하는 손해)
        clause_id1_text = (
            "① 회사는 피보험자가 해외여행 도중에 【별표3(특정감염병 분류표)】에서 정한 특정감염병으로 "
            "「감염병의 예방 및 관리에 관한 법률 제11조(의사 등의 신고)」에 따라 신고되어 특정감염병환자로 진단 확정되었을 때에는 "
            "이 특별약관의 보험가입금액을 보험수익자(보험수익자의 지정이 없을 때에는 피보험자)에게 특정감염병보상금으로 지급합니다."
        )
        if not db.query(Clause).filter_by(
            policy_version_id=policy_version.policy_version_id,
            text=clause_id1_text
        ).first():
            db.add(Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=coverage_infectious.coverage_id,
                clause_type="보장정의",
                article_no="[여행중 특정감염병보상금 특별약관] 제1조(보상하는 손해)",
                text=clause_id1_text,
                page_ref="p.192",
                default_color="파랑"
            ))

        # 4. 여행중단사고발생 추가비용 (p.194-195)
        trip_interruption_std = get_or_create_coverage_std(
            db, "TRIP_INTERRUPTION", "여행중단 추가비용", "여행", False
        )

        coverage_trip_int = Coverage(
            policy_version_id=policy_version.policy_version_id,
            coverage_std_id=trip_interruption_std.coverage_std_id,
            raw_name="여행중 중단사고발생 추가비용",
            definition="여행 도중 중단사고(질병·상해·사망·천재지변 등)로 귀국시 추가 비용",
            limit_amount=None,
            deductible=None,
            waiting_condition="여행중단 사유 발생"
        )
        db.add(coverage_trip_int)
        db.flush()

        # Clause: 제1조 (보상하는 손해)
        clause_ti1_text = (
            "회사는 피보험자가 해외여행 도중에 아래의 사유로 여행일정을 불가피하게 중단(축소)하고 귀국하게 되었을 경우 "
            "피보험자가 추가적으로 부담한 비용을 이 특별약관에 따라 보험가입금액을 한도로 보상하여 드립니다. "
            "1. 피보험자 및 여행동반 가족이 상해 또는 질병으로 3일 이상 입원한 경우 "
            "2. 보험기간 내 피보험자의 3촌 이내의 친족 또는 여행동반자의 사망 "
            "3. 지진, 분화, 해일 또는 이와 비슷한 천재지변 "
            "4. 전쟁, 외국의 무력행사, 혁명, 내란, 사변, 폭동, 소요, 기타 이들과 유사한 사태"
        )
        if not db.query(Clause).filter_by(
            policy_version_id=policy_version.policy_version_id,
            text=clause_ti1_text
        ).first():
            db.add(Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=coverage_trip_int.coverage_id,
                clause_type="보장정의",
                article_no="[여행중 중단사고발생 추가비용 특별약관] 제1조(보상하는 손해)",
                text=clause_ti1_text,
                page_ref="p.194",
                default_color="파랑"
            ))

        # 5. 여권분실 재발급비용 (p.196-197)
        passport_loss_std = get_or_create_coverage_std(
            db, "PASSPORT_LOSS", "여권분실 재발급비용", "서류", False
        )

        coverage_passport = Coverage(
            policy_version_id=policy_version.policy_version_id,
            coverage_std_id=passport_loss_std.coverage_std_id,
            raw_name="여행중 여권분실 재발급비용",
            definition="해외여행 도중 여권 분실·도난시 재외공관 여행증명서 및 여권 재발급비용",
            limit_amount=None,
            deductible=None,
            waiting_condition="여권 분실 신고 및 여행증명서 발급"
        )
        db.add(coverage_passport)
        db.flush()

        # Clause: 제1조 (보상하는 손해)
        clause_pl1_text = (
            "① 회사는 피보험자(보험대상자)가 해외여행 도중에 여권을 분실하거나 도난당하여 재외공관에 여권분실신고를 하고 "
            "여행증명서(T/C : Travel Certification)를 발급받은 경우 여행증명서 발급비용과 여권 재발급비용을 "
            "보험수익자(보험금을 받는 자)에게 지급합니다. "
            "② 제1항의 여행증명서 발급비용 및 여권 재발급비용이란 여행증명서 및 여권 재발급에 관한 수수료로 "
            "「여권법」 제22조 제1항에서 정한 수수료 및 국제교류기여금을 합한 금액을 말하며 교통비 및 사진촬영비는 포함되지 않습니다."
        )
        if not db.query(Clause).filter_by(
            policy_version_id=policy_version.policy_version_id,
            text=clause_pl1_text
        ).first():
            db.add(Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=coverage_passport.coverage_id,
                clause_type="보장정의",
                article_no="[여행중 여권분실 재발급비용 특별약관] 제1조(보상하는 손해)",
                text=clause_pl1_text,
                page_ref="p.196",
                default_color="파랑"
            ))

        # 6. 자택 도난손해 (p.198-201) - 이 특약은 클 것 같으니 핵심 조항만
        home_theft_std = get_or_create_coverage_std(
            db, "HOME_THEFT", "자택 도난손해", "재물", False
        )

        coverage_home_theft = Coverage(
            policy_version_id=policy_version.policy_version_id,
            coverage_std_id=home_theft_std.coverage_std_id,
            raw_name="여행중 자택 도난손해(가재) 보장",
            definition="해외여행 도중 자택 내 강도·절도로 인한 도난 손해 보상",
            limit_amount=None,
            deductible=None,
            waiting_condition=None
        )
        db.add(coverage_home_theft)
        db.flush()

        # Clause: 제1조 (보상하는 손해)
        clause_ht1_text = (
            "① 회사는 보통약관 제3조에도 불구하고 보험기간 중 보험의 목적이 피보험자가 주민등록등본상 거주하고 있는 "
            "주택의 구내에 있는 동안 강도 또는 절도(그 미수를 포함합니다)로 인해 도난, 망가짐, 손상 및 파손된 손해"
            "(이하 도난손해라 합니다)를 보상하여 드립니다. "
            "② 제1항에서 보장하는 도난손해위험으로 인하여 손해가 발생한 경우, 계약자 또는 피보험자가 지출한 아래의 비용을 추가로 지급합니다. "
            "1. 손해방지비용 : 손해의 방지 또는 경감을 위하여 지출한 필요 또는 유익한 비용 "
            "2. 대위권 보전비용 : 제3자로부터 손해의 배상을 받을 수 있는 경우에는 그 권리를 지키거나 행사하기 위하여 지출한 필요 또는 유익한 비용 "
            "3. 잔존물 보전비용 : 잔존물을 보전하기 위하여 지출한 필요 또는 유익한 비용. 다만, 제8조(잔존물)에 의해 회사가 잔존물을 취득한 경우에 한합니다. "
            "4. 기타 협력비용 : 회사의 요구에 따르기 위하여 지출한 필요 또는 유익한 비용 "
            "③ 제1항의 주택구내라 함은 공동주택에 있어서는 베란다를 포함한 전용면적 부분을 말하며 복도, 계단, 엘리베이터, 주차장 등 "
            "공용면적부분은 제외합니다. 공동주택 이외 주택의 경우에는 옥상 및 담당 내를 말합니다."
        )
        if not db.query(Clause).filter_by(
            policy_version_id=policy_version.policy_version_id,
            text=clause_ht1_text
        ).first():
            db.add(Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=coverage_home_theft.coverage_id,
                clause_type="보장정의",
                article_no="[여행중 자택 도난손해(가재) 보장 특별약관] 제1조(보상하는 손해)",
                text=clause_ht1_text,
                page_ref="p.198-199",
                default_color="파랑"
            ))

        # Clause: 제3조 (보상하지 않는 손해)
        clause_ht3_text = (
            "회사는 아래와 같은 손해는 보상하지 않습니다. "
            "1. 보험계약자, 피보험자 또는 이들의 법정대리인의 고의 또는 중대한 과실로 생긴 도난손해 "
            "2. 보험계약자 및 피보험자의 가족, 친족, 사용인, 동거인, 숙박인, 감수인(監守人) 또는 당직자가 일으킨 행위 또는 "
            "이들이 가담하거나 묵인하에 생긴 도난 손해 "
            "3. 전쟁, 폭동, 소요 또는 이와 유사한 사변으로 생긴 도난 "
            "4. 화재나 지진, 분화, 해일, 폭발 또는 그 밖의 변재가 일어났을 때 생긴 도난 손해 "
            "5. 절도 또는 강도행위로 발생한 화재 및 폭발손해 "
            "6. 망실 또는 분실 손해 "
            "7. 사기 또는 횡령으로 인한 손해 "
            "8. 보험사고가 생긴 후 30일 이내에 알지 못한 도난 손해 "
            "9. 보험의 목적이 건물구내 밖에 있는 동안 생긴 도난 "
            "10. 외부로부터 침입흔적이 없는 도난 손해"
        )
        if not db.query(Clause).filter_by(
            policy_version_id=policy_version.policy_version_id,
            text=clause_ht3_text
        ).first():
            db.add(Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=coverage_home_theft.coverage_id,
                clause_type="면책",
                article_no="[여행중 자택 도난손해(가재) 보장 특별약관] 제3조(보상하지 않는 손해)",
                text=clause_ht3_text,
                page_ref="p.199",
                default_color="빨강"
            ))

        # 7. 의사상자 상해위험 (p.202)
        good_samaritan_std = get_or_create_coverage_std(
            db, "GOOD_SAMARITAN", "의사상자 상해위험", "상해", False
        )

        coverage_good_samaritan = Coverage(
            policy_version_id=policy_version.policy_version_id,
            coverage_std_id=good_samaritan_std.coverage_std_id,
            raw_name="의사상자 상해위험",
            definition="타인 생명·신체 구제 중 입은 상해로 의사상자 판정시 정부 지급액",
            limit_amount=None,
            deductible=None,
            waiting_condition="의사상자 판정"
        )
        db.add(coverage_good_samaritan)
        db.flush()

        # Clause: 제1조 (보상하는 손해)
        clause_gs1_text = (
            "회사는 보험기간 중 보험증권에 기재된 피보험자가 직무외의 행위로 타인의 생명, 신체"
            "(의수, 의족, 의안, 의치 등 신체보조장구는 제외합니다) 또는 재산의 급박한 피해를 구제하다가 "
            "신체에 상해를 입어 「의사상자 등 예우 및 지원에 관한 법률」및「동법 시행령」의 규정에 따라 "
            "의사상자로 판정되는 경우 이 특별약관에 따라 보상하여 드립니다."
        )
        if not db.query(Clause).filter_by(
            policy_version_id=policy_version.policy_version_id,
            text=clause_gs1_text
        ).first():
            db.add(Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=coverage_good_samaritan.coverage_id,
                clause_type="보장정의",
                article_no="[의사상자 상해위험 특별약관] 제1조(보상하는 손해)",
                text=clause_gs1_text,
                page_ref="p.202",
                default_color="파랑"
            ))

        # 8. 전쟁위험 (p.203)
        war_risk_std = get_or_create_coverage_std(
            db, "WAR_RISK", "전쟁위험", "전쟁", False
        )

        coverage_war_risk = Coverage(
            policy_version_id=policy_version.policy_version_id,
            coverage_std_id=war_risk_std.coverage_std_id,
            raw_name="전쟁위험",
            definition="전쟁·외국 무력행사·혁명·내란·폭동으로 인한 상해·사망 보장",
            limit_amount=None,
            deductible=None,
            waiting_condition=None
        )
        db.add(coverage_war_risk)
        db.flush()

        # Clause: 제1조 (보상하는 손해)
        clause_wr1_text = (
            "① 회사는 보통약관 제5조(보험금을 지급하지 않는 사유) 제1항 제5호의 규정에도 불구하고 "
            "전쟁, 외국의 무력행사, 혁명, 내란, 폭동으로 인하여 피보험자에게 제3조(보험금의 지급사유)에 정한 지급사유가 발생하였을 "
            "경우에는 각 호에 해당하는 보험금을 이 특별약관에 따라 보험수익자에게 지급합니다. "
            "② 회사는 보험기간이 만료되기 전이라도 제1항의 위험이 뚜렷이 증가했다고 인정될 때에는 24시간 이전에 서면으로 "
            "추가보험료를 청구하거나 이 특별약관을 해지할 수 있습니다."
        )
        if not db.query(Clause).filter_by(
            policy_version_id=policy_version.policy_version_id,
            text=clause_wr1_text
        ).first():
            db.add(Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=coverage_war_risk.coverage_id,
                clause_type="보장정의",
                article_no="[전쟁위험 특별약관] 제1조(보상하는 손해)",
                text=clause_wr1_text,
                page_ref="p.203",
                default_color="파랑"
            ))

        db.commit()
        print("삼성화재 2026년판 청크 D 부분 완료 (8개 특약, 14개 조항): FLIGHT_DELAY, FOOD_POISONING, INFECTIOUS_DISEASE, TRIP_INTERRUPTION, PASSPORT_LOSS, HOME_THEFT, GOOD_SAMARITAN, WAR_RISK")

    finally:
        db.close()


if __name__ == "__main__":
    run()
