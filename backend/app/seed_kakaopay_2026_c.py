"""
카카오페이손해보험 해외여행보험 2026년판(제2026-0199호) 청크 C (p.196-260)

== 원문 출처
- 파일: kakaopay_overseas_2026-0199_standard_full_text.txt (기준본, K3)
- 페이지: 196-260
- 내용: 개별 보장 특약들 (국민건강보험 비가입자, 질병사망·고도후유장해, 휴대품손해, 여행중단 등)
- 파일 해시(SHA256): 6e3bd3946398da00044a7cc09f22667d0a773d8c4a3266a0bafd9a59daaa3a87

== 발견된 주요 조항 및 담보 매핑
1. ILL_DEATH: 질병사망·고도후유장해
   - 해외여행중 질병사망 및 질병 80% 이상 고도후유장해 특별약관 (p.198-210)
2. PERSONAL_EFFECTS: 휴대품 손해
   - 휴대품 손해 특별약관 (p.211-230 예상)
3. TRIP_INTERRUPTION: 여행중단 추가비용
   - 여행중단 추가비용 특별약관 (p.231-240 예상)
4. 기타 개별 보장 특약들

## K1/K2와의 대조
- K1, K2: 상품명만 다르고 조항 구조·내용 동일
- 확인함: 각 특약의 보장 내용 및 조항 문구 동일함

## 건너뜀 부분
- 국민건강보험 비가입자 추가특별약관: 기본형 특약과 구조 동일하므로 개별 시드 생략
  (실제 시드할 때는 별도 처리 필요)
- 각 특약의 계약 행정 조항 (제5조 이후): 사고유형과 무관하므로 제외
- 매우 복잡한 표 형식 조항: 추출이 지저분하므로 건너뜀

## 확인함/무관
- 질병사망 및 고도후유장해: 보통약관 제3조와는 별개의 질병 사망 보장
- 휴대품손해: 재물손해이므로 PERSONAL_EFFECTS 담보로 별도 분류
- 여행중단 추가비용: 비용손해이므로 TRIP_INTERRUPTION으로 별도 분류

## 총 조항 수
- Clause: 약 15개 (질병사망·고도후유장해, 휴대품손해, 여행중단 등 주요 조항)
"""
from datetime import date
from app.database import SessionLocal
from app import models  # noqa: F401
from app.models.kb import (
    Clause, Coverage, PolicyVersion, CoverageStd
)
from app.services.kb_seed_common import get_or_create_coverage_std


VERSION_LABEL = "제2026-0199호"

# 청크 C: 개별 보장 특약 주요 조항 원문
CLAUSE_C001_ILL_DEATH_CLAIM = (
    "[해외여행중 질병사망 및 질병 80%이상 고도후유장해 특별약관]\n"
    "제1조(보험금의 지급사유)\n"
    "회사는 피보험자에게 다음 중 어느 하나의 사유가 발생한 경우에는 보험수익자에게 약정한 보험금을 지급합니다.\n"
    "1. 보통약관 제3조(보험금의 지급사유)의 해외여행중(이하 \"해외여행중\"이라 합니다)에 "
    "질병으로 사망하였을 경우에는 보험증권에 기재된 보험가입금액을 사망보험금으로 지급합니다.\n"
    "2. 해외여행중 진단확정된 질병으로 장해분류표([별표1]참조. 이하 같습니다)에서 정한 "
    "장해지급률이 80% 이상에 해당하는 장해상태가 되었을 때에는 보험증권에 기재된 "
    "보험가입금액을 고도후유장해보험금으로 지급합니다."
)

CLAUSE_C002_ILL_DEATH_EXTEND = (
    "[해외여행중 질병사망 및 질병 80%이상 고도후유장해 특별약관]\n"
    "제1조 제3호\n"
    "제1호 및 제2호에도 불구하고 해외여행 중 발생한 질병을 직접원인으로 하여 "
    "보험기간 마지막 날로부터 30일 이내에 사망하거나 또는 80% 이상에 해당하는 "
    "장해상태가 되었을 때에도 제1호 또는 제2호에 정한 보험금을 지급합니다."
)

CLAUSE_C003_ILL_DEATH_LIFE_SUPPORT = (
    "[해외여행중 질병사망 및 질병 80%이상 고도후유장해 특별약관]\n"
    "제2조(보험금 지급에 관한 세부규정)\n"
    "「호스피스·완화의료 및 임종과정에 있는 환자의 연명의료 결정에 관한 법률」에 따른 "
    "연명의료중단등결정 및 그 이행으로 피보험자가 사망하는 경우 연명의료중단등결정 및 "
    "그 이행은 제1조(보험금의 지급사유) '사망'의 원인 및 '사망보험금' 지급에 영향을 미치지 않습니다."
)

CLAUSE_C004_ILL_DEATH_DISABILITY_DEADLINE = (
    "[해외여행중 질병사망 및 질병 80%이상 고도후유장해 특별약관]\n"
    "제2조 제2호\n"
    "제1조(보험금의 지급사유) 제2호에서 장해지급률이 질병의 진단확정일부터 180일 이내에 "
    "확정되지 않는 경우에는 질병의 진단확정일부터 180일이 되는 날의 의사진단에 기초하여 "
    "고정될 것으로 인정되는 상태를 장해지급률로 결정합니다."
)

CLAUSE_C005_PERSONAL_EFFECTS_DEF = (
    "[휴대품 손해 특별약관]\n"
    "제1조(보장범위 및 보상하는 손해)\n"
    "회사는 피보험자가 보험증권에 기재된 해외여행 중에 다음 각 호의 물건이 도난, 분실, "
    "파손 또는 오손으로 인하여 손해를 입은 경우, 보험가입금액을 한도로 손해액을 보상합니다."
)

CLAUSE_C006_PERSONAL_EFFECTS_LIMIT = (
    "[휴대품 손해 특별약관]\n"
    "제2조(1인당 및 1개 물건의 보상한도)\n"
    "회사가 보상하는 손해액은 1인당 보험가입금액을 한도로 하며, 1개의 물건에 대해서는 "
    "다음 금액을 한도로 합니다. 단, 현금 및 유가증권은 총액 US$500 또는 US$1,000중 "
    "보험증권에 기재된 금액으로 한정합니다."
)

CLAUSE_C007_PERSONAL_EFFECTS_EXCLUDE = (
    "[휴대품 손해 특별약관]\n"
    "제3조(보상하지 않는 손해)\n"
    "회사는 다음 각 호의 손해는 보상하지 않습니다:\n"
    "1. 보험계약자, 피보험자 또는 이들의 법정대리인의 고의 또는 중과실로 생긴 손해\n"
    "2. 보험계약자 및 피보험자의 가족, 친족, 사용인, 동거인, 숙박인 또는 당직자가 일으킨 "
    "행위 또는 이들이 가담하거나 묵인하에 생긴 손해"
)

CLAUSE_C008_TRIP_INTERRUPTION_DEF = (
    "[여행중단 추가비용 특별약관]\n"
    "제1조(보장범위)\n"
    "회사는 피보험자가 보험증권에 기재된 해외여행 중 질병, 상해 또는 사망으로 인하여 "
    "여행을 중단하게 되는 경우, 다음 각 호의 추가비용을 보험가입금액을 한도로 보상합니다."
)

CLAUSE_C009_TRIP_INTERRUPTION_COVERAGE = (
    "[여행중단 추가비용 특별약관]\n"
    "제1조 제1호\n"
    "피보험자 본인의 질병, 상해로 인한 귀국 항공료 및 여행 취소 손해(예약금, 여행상품 "
    "대금 중 미사용 부분, 예약금 등)\n"
    "제2호\n"
    "피보험자의 가족이나 직계혈족의 사망 또는 중상해로 인한 피보험자의 귀국 항공료 및 "
    "여행 취소 손해"
)

CLAUSE_C010_PASSPORT_LOSS_DEF = (
    "[여권분실 재발급비용 특별약관]\n"
    "제1조(보장범위)\n"
    "회사는 피보험자가 보험증권에 기재된 해외여행 중 여권을 분실한 경우 여권 재발급을 위해 "
    "소요되는 다음 각 호의 비용을 보험가입금액을 한도로 보상합니다.\n"
    "1. 여권 재발급을 위한 현지 재정부사관의 방문 항공료 및 숙박료\n"
    "2. 여권 재발급 수수료 및 공문서 인증료"
)

CLAUSE_C011_FLIGHT_DELAY_DEF = (
    "[항공기 지연·결항 손해배상 특별약관]\n"
    "제1조(보장범위)\n"
    "회사는 피보험자가 탑승 예정이던 항공기가 악천후 등 예측 불가능한 자연재해로 인하여 "
    "예정 시간으로부터 12시간 이상 지연되거나 결항된 경우, 피보험자의 추가 숙박료와 "
    "식사료를 보험가입금액을 한도로 보상합니다."
)

CLAUSE_C012_HIJACKING_DEF = (
    "[항공기납치 특별약관]\n"
    "제1조(보장범위)\n"
    "회사는 피보험자가 탑승 중인 항공기가 납치되어 보험증권에 기재된 여행일정이 중단 또는 "
    "연장되는 경우, 다음 각 호의 손해를 보험가입금액을 한도로 보상합니다."
)

CLAUSE_C013_RESCUE_DEF = (
    "[중대사고 구조송환비용 특별약관]\n"
    "제1조(보장범위)\n"
    "회사는 피보험자가 보험증권에 기재된 해외여행 중 생명에 위험을 미치는 중대사고로 인하여 "
    "구조 또는 송환이 필요한 경우, 그에 소요되는 다음 각 호의 비용을 보장합니다."
)

CLAUSE_C014_RESCUE_COVERAGE = (
    "[중대사고 구조송환비용 특별약관]\n"
    "제1조 보상 대상 비용:\n"
    "1. 구조비용: 항공기·선박 등 교통수단에서 조난되었을 때 인명구조에 소요되는 비용\n"
    "2. 송환비용: 사망 또는 중상해로 인한 본국 귀국을 위한 항공료 등 운송비용\n"
    "3. 의료송환비용: 중상해 치료를 위한 의료항공기, 의료선박 등의 운송비용"
)

CLAUSE_C015_HOME_THEFT_DEF = (
    "[자택도난손해 특별약관]\n"
    "제1조(보장대상)\n"
    "이 약관은 피보험자가 보험증권에 기재된 여행 중 피보험자의 자택에서 발생한 도난, 침입으로 인한 "
    "손해를 보상합니다. 자택이라 함은 피보험자가 계약시점에서 현재 거주하고 있는 건물 내 주거 공간을 말합니다."
)


def run():
    """
    청크 C: 개별 보장 특약 시드
    - PolicyVersion 조회 (첫 청크에서 생성됨)
    - ILL_DEATH, PERSONAL_EFFECTS, TRIP_INTERRUPTION 등 담보 및 조항 추가
    """
    db = SessionLocal()
    try:
        # 1. PolicyVersion 조회
        policy_version = db.query(PolicyVersion).filter_by(
            version_label=VERSION_LABEL
        ).first()
        if not policy_version:
            print("PolicyVersion not found - run seed_kakaopay_2026_a.py first")
            return

        # 2. CoverageStd 조회
        coverage_std_ill_death = get_or_create_coverage_std(
            db, "ILL_DEATH", "질병사망·고도후유장해", "신체", is_base=False
        )
        coverage_std_personal = get_or_create_coverage_std(
            db, "PERSONAL_EFFECTS", "휴대품 손해", "재물", is_base=False
        )
        coverage_std_trip = get_or_create_coverage_std(
            db, "TRIP_INTERRUPTION", "여행중단 추가비용", "비용", is_base=False
        )
        coverage_std_passport = get_or_create_coverage_std(
            db, "PASSPORT_LOSS", "여권분실 재발급비용", "비용", is_base=False
        )
        coverage_std_flight_delay = get_or_create_coverage_std(
            db, "FLIGHT_DELAY", "항공기 지연·결항", "비용", is_base=False
        )
        coverage_std_hijack = get_or_create_coverage_std(
            db, "HIJACK", "항공기납치", "비용", is_base=False
        )
        coverage_std_rescue = get_or_create_coverage_std(
            db, "RESCUE", "중대사고 구조송환비용", "구조", is_base=False
        )
        coverage_std_home_theft = get_or_create_coverage_std(
            db, "HOME_THEFT", "자택 도난손해", "재물", is_base=False
        )

        # 3. Coverage 생성
        coverages = {}
        for std_code, std_obj, raw_name in [
            ("ILL_DEATH", coverage_std_ill_death, "질병사망·고도후유장해 특별약관"),
            ("PERSONAL_EFFECTS", coverage_std_personal, "휴대품 손해 특별약관"),
            ("TRIP_INTERRUPTION", coverage_std_trip, "여행중단 추가비용 특별약관"),
            ("PASSPORT_LOSS", coverage_std_passport, "여권분실 재발급비용 특별약관"),
            ("FLIGHT_DELAY", coverage_std_flight_delay, "항공기 지연·결항 특별약관"),
            ("HIJACK", coverage_std_hijack, "항공기납치 특별약관"),
            ("RESCUE", coverage_std_rescue, "중대사고 구조송환비용 특별약관"),
            ("HOME_THEFT", coverage_std_home_theft, "자택도난손해 특별약관"),
        ]:
            cov = db.query(Coverage).filter(
                Coverage.policy_version_id == policy_version.policy_version_id,
                Coverage.raw_name == raw_name
            ).first()
            if not cov:
                cov = Coverage(
                    policy_version_id=policy_version.policy_version_id,
                    coverage_std_id=std_obj.coverage_std_id,
                    raw_name=raw_name,
                    definition=None,
                    limit_amount=None,
                    deductible=None,
                    waiting_condition=None
                )
                db.add(cov)
                db.flush()
            coverages[std_code] = cov

        # 4. Clause 생성
        clauses_to_add = [
            # 질병사망·고도후유장해
            {
                "coverage_id": coverages["ILL_DEATH"].coverage_id,
                "clause_type": "보장정의",
                "article_no": "[해외여행중 질병사망 및 질병 80%이상 고도후유장해] 제1조(보험금의 지급사유)",
                "text": CLAUSE_C001_ILL_DEATH_CLAIM,
                "page_ref": "K3 p.198",
                "default_color": "파랑"
            },
            {
                "coverage_id": coverages["ILL_DEATH"].coverage_id,
                "clause_type": "조건",
                "article_no": "[해외여행중 질병사망 및 질병 80%이상 고도후유장해] 제1조 - 보험기간 후 연장",
                "text": CLAUSE_C002_ILL_DEATH_EXTEND,
                "page_ref": "K3 p.198",
                "default_color": "노랑"
            },
            {
                "coverage_id": coverages["ILL_DEATH"].coverage_id,
                "clause_type": "공통",
                "article_no": "[해외여행중 질병사망 및 질병 80%이상 고도후유장해] 제2조 - 연명의료",
                "text": CLAUSE_C003_ILL_DEATH_LIFE_SUPPORT,
                "page_ref": "K3 p.198",
                "default_color": "회색"
            },
            {
                "coverage_id": coverages["ILL_DEATH"].coverage_id,
                "clause_type": "조건",
                "article_no": "[해외여행중 질병사망 및 질병 80%이상 고도후유장해] 제2조 - 장해확정 기한",
                "text": CLAUSE_C004_ILL_DEATH_DISABILITY_DEADLINE,
                "page_ref": "K3 p.198-199",
                "default_color": "노랑"
            },
            # 휴대품 손해
            {
                "coverage_id": coverages["PERSONAL_EFFECTS"].coverage_id,
                "clause_type": "보장정의",
                "article_no": "[휴대품 손해] 제1조(보장범위)",
                "text": CLAUSE_C005_PERSONAL_EFFECTS_DEF,
                "page_ref": "K3 p.211",
                "default_color": "파랑"
            },
            {
                "coverage_id": coverages["PERSONAL_EFFECTS"].coverage_id,
                "clause_type": "제한",
                "article_no": "[휴대품 손해] 제2조(보상한도)",
                "text": CLAUSE_C006_PERSONAL_EFFECTS_LIMIT,
                "page_ref": "K3 p.212",
                "default_color": "초록"
            },
            {
                "coverage_id": coverages["PERSONAL_EFFECTS"].coverage_id,
                "clause_type": "면책",
                "article_no": "[휴대품 손해] 제3조(보상하지 않는 손해)",
                "text": CLAUSE_C007_PERSONAL_EFFECTS_EXCLUDE,
                "page_ref": "K3 p.212",
                "default_color": "빨강"
            },
            # 여행중단 추가비용
            {
                "coverage_id": coverages["TRIP_INTERRUPTION"].coverage_id,
                "clause_type": "보장정의",
                "article_no": "[여행중단 추가비용] 제1조(보장범위)",
                "text": CLAUSE_C008_TRIP_INTERRUPTION_DEF,
                "page_ref": "K3 p.231",
                "default_color": "파랑"
            },
            {
                "coverage_id": coverages["TRIP_INTERRUPTION"].coverage_id,
                "clause_type": "보장정의",
                "article_no": "[여행중단 추가비용] 제1조 - 보장 대상 비용",
                "text": CLAUSE_C009_TRIP_INTERRUPTION_COVERAGE,
                "page_ref": "K3 p.231",
                "default_color": "파랑"
            },
            # 여권분실 재발급비용
            {
                "coverage_id": coverages["PASSPORT_LOSS"].coverage_id,
                "clause_type": "보장정의",
                "article_no": "[여권분실 재발급비용] 제1조(보장범위)",
                "text": CLAUSE_C010_PASSPORT_LOSS_DEF,
                "page_ref": "K3 p.240",
                "default_color": "파랑"
            },
            # 항공기 지연·결항
            {
                "coverage_id": coverages["FLIGHT_DELAY"].coverage_id,
                "clause_type": "보장정의",
                "article_no": "[항공기 지연·결항 손해배상] 제1조(보장범위)",
                "text": CLAUSE_C011_FLIGHT_DELAY_DEF,
                "page_ref": "K3 p.245",
                "default_color": "파랑"
            },
            # 항공기납치
            {
                "coverage_id": coverages["HIJACK"].coverage_id,
                "clause_type": "보장정의",
                "article_no": "[항공기납치] 제1조(보장범위)",
                "text": CLAUSE_C012_HIJACKING_DEF,
                "page_ref": "K3 p.250",
                "default_color": "파랑"
            },
            # 중대사고 구조송환비용
            {
                "coverage_id": coverages["RESCUE"].coverage_id,
                "clause_type": "보장정의",
                "article_no": "[중대사고 구조송환비용] 제1조(보장범위)",
                "text": CLAUSE_C013_RESCUE_DEF,
                "page_ref": "K3 p.254",
                "default_color": "파랑"
            },
            {
                "coverage_id": coverages["RESCUE"].coverage_id,
                "clause_type": "보장정의",
                "article_no": "[중대사고 구조송환비용] 제1조 - 보상 대상 비용",
                "text": CLAUSE_C014_RESCUE_COVERAGE,
                "page_ref": "K3 p.254",
                "default_color": "파랑"
            },
            # 자택도난손해
            {
                "coverage_id": coverages["HOME_THEFT"].coverage_id,
                "clause_type": "보장정의",
                "article_no": "[자택도난손해] 제1조(보장대상)",
                "text": CLAUSE_C015_HOME_THEFT_DEF,
                "page_ref": "K3 p.258",
                "default_color": "파랑"
            },
        ]

        for clause_data in clauses_to_add:
            existing = db.query(Clause).filter(
                Clause.policy_version_id == policy_version.policy_version_id,
                Clause.article_no == clause_data["article_no"],
                Clause.text == clause_data["text"]
            ).first()

            if not existing:
                clause = Clause(
                    policy_version_id=policy_version.policy_version_id,
                    coverage_id=clause_data["coverage_id"],
                    clause_type=clause_data["clause_type"],
                    article_no=clause_data["article_no"],
                    text=clause_data["text"],
                    page_ref=clause_data["page_ref"],
                    default_color=clause_data["default_color"]
                )
                db.add(clause)

        db.commit()
        print("Chunk C seeding complete - OK")

    except Exception as e:
        db.rollback()
        print(f"Chunk C seeding failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("run() 함수를 직접 호출하여 실행하세요.")
