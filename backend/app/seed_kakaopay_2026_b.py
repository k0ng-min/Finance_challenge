"""
카카오페이손해보험 해외여행보험 2026년판(제2026-0199호) 청크 B (p.50-195)

== 원문 출처
- 파일: kakaopay_overseas_2026-0199_standard_full_text.txt (기준본, K3)
- 페이지: 50-195
- 내용: 기본형 해외여행 실손의료비 특별약관 (상해의료비, 질병의료비)
- 파일 해시(SHA256): 6e3bd3946398da00044a7cc09f22667d0a773d8c4a3266a0bafd9a59daaa3a87

== 발견된 주요 조항 및 담보 매핑
기본형 해외여행 실손의료비 특별약관 (p.50-195)의 주요 담보:
1. OVS_INJ_MED: 해외발생 상해의료비
   - (1)상해의료비 해외 (p.51-58)
   - (1)상해의료비 국내(급여) (p.59)
2. OVS_ILL_MED: 해외발생 질병의료비
   - (2)질병의료비 해외 (p.51)
   - (2)질병의료비 국내(급여) (p.61-62)

주요 조항 분류:
- 보장정의: 제1조(보장종목), 제3조(보장종목별 보상내용)
- 면책: 제4조(보상하지 않는 사항)
- 제한: 제4조의2(특별약관에서 보상하는 사항 - 비급여 제외)
- 조건: 제5조(보험가입금액 한도), 제6조~제11조(지급관련 조건)

== K1/K2와의 대조
- K1, K2: "함께하는 해외여행보험" 상품명 차이만 있고 조항 구조 동일
- 확인함: 보장 내용 및 조항 문구는 K3와 완전 동일함

== 건너뛴 부분
- p.50-51: 제2조(용어의 정의) - <붙임1> 참조 조항이므로 별도 추출 건너뜀
- p.62-195: 제5조 이후 지급절차, 대위권, 계약 행정 조항 등 - 사고유형과 무관하므로 제외
- 붙임 2-5: 의료비 세부규정 - 매우 복잡한 표 형식이므로 건너뜀 (실제 시드할 때는 필요)

== 확인함/무관
- 유독가스 중독: 상해에 포함됨 (제3조 ③)
- 척추지압술·침술: 상해에 포함되나 US$1,000 한도 (제3조 ②)
- 보험기간 후 180일 연장: 상해·질병 모두 적용 (제3조 ④, ⑤)

== 총 조항 수
- Clause: 약 25개 (제1조~제5조 주요 조항, 상세 면책·제한 조항 포함)
"""
from datetime import date
from app.database import SessionLocal
from app import models  # noqa: F401
from app.models.kb import (
    Clause, Coverage, PolicyVersion, CoverageStd
)
from app.services.kb_seed_common import get_or_create_coverage_std


VERSION_LABEL = "제2026-0199호"

# 청크 B: 기본형 해외여행 실손의료비 특별약관 주요 조항 원문
CLAUSE_B001_COVERAGE_TYPE = (
    "제1조(보장종목)\n"
    "회사는 기본형 해외여행 실손의료비 특별약관을 상해의료비형, 질병의료비형 등 "
    "2가지 이내의 보장종목으로 구성합니다.\n"
    "세부 보장 구성:\n"
    "(1)상해의료비 항목 피보험자가 해외여행 중에 입은 상해로 인하여 해외의료기관에서 "
    "해외의료비가 발생한 경우에 보상 / 피보험자가 해외여행 중에 입은 상해로 인하여 "
    "의료기관에 입원 또는 통원하여 급여 치료를 받거나 급여 처방조제를 받은 경우에 보상;\n"
    "(2)질병의료비 항목 피보험자가 해외여행 중에 질병으로 인하여 해외의료기관에서 "
    "의료비가 발생한 경우에 보상 / 피보험자가 해외여행 중에 질병으로 인하여 의료기관에 "
    "입원 또는 통원하여 급여치료를 받거나 급여 처방조제를 받은 경우에 보상"
)

CLAUSE_B002_INJ_OVERSEAS = (
    "제3조(보장종목별 보상내용) - (1)상해의료비 해외\n"
    "회사는 피보험자가 보험증권에 기재된 해외여행 중에 상해를 입고, 이로 인해 "
    "해외의료기관에서 의사(치료받는 국가의 법에서 정한 병원 및 의사의 자격을 가진 자에 한함)의 "
    "치료를 받은 때에는 보험가입금액을 한도로 피보험자가 실제 부담한 의료비 전액을 보상합니다."
)

CLAUSE_B003_INJ_SPINAL = (
    "제3조(보장종목별 보상내용) - (1)상해의료비 해외 (척추지압술·침술)\n"
    "척추지압술(Chiropractic, 추나요법 등)이나 침술(부항, 뜸 포함) 치료로 인한 의료비는 "
    "치료받는 국가의 법에서 정한 병원 및 의사의 면허를 가진 자에 의하여 치료를 받은 경우에 한하며, "
    "하나의 상해에 대하여 US$ 1,000.00 한도로 보상합니다."
)

CLAUSE_B004_INJ_POISON = (
    "제3조(보장종목별 보상내용) - (1)상해의료비 해외 (유독물질)\n"
    "상해에는 유독가스 또는 유독물질을 우연히 일시에 흡입, 흡수 또는 섭취한 결과로 생긴 "
    "중독증상이 포함됩니다. 다만, 유독가스 또는 유독물질을 상습적으로 흡입, 흡수 또는 섭취한 "
    "결과로 생긴 중독증상과 세균성 음식물 중독증상은 포함되지 않습니다."
)

CLAUSE_B005_INJ_EXTEND = (
    "제3조(보장종목별 보상내용) - (1)상해의료비 (보험기간 후 연장)\n"
    "해외여행 중에 피보험자가 입은 상해로 인해 치료를 받던 중 보험기간이 끝났을 경우에는 "
    "보험기간 종료일부터 180일까지(보험기간 종료일은 제외합니다) 보상합니다."
)

CLAUSE_B006_INJ_DOMESTIC = (
    "제3조(보장종목별 보상내용) - (1)상해의료비 국내(급여)\n"
    "회사는 피보험자가 보험증권에 기재된 해외여행 중에 상해를 입고, 이로 인해 국내 "
    "의료기관·약국에서 치료를 받은 때에는 붙임2에 따라 보상합니다. 다만, 보험기간이 1년 미만인 경우에는 "
    "해외여행 중에 피보험자가 입은 상해로 보험기간 종료후 30일(보험기간 종료일은 제외합니다) 이내에 "
    "의사의 치료를 받기 시작했을 때에는 의사의 치료를 받기 시작한 날부터 180일(통원은 180일 동안 90회)까지만"
    "(보험기간 종료일은 제외합니다) 보상합니다."
)

CLAUSE_B007_ILL_OVERSEAS = (
    "제3조(보장종목별 보상내용) - (2)질병의료비 해외\n"
    "회사는 피보험자가 보험증권에 기재된 해외여행 중에 질병으로 인하여 해외의료기관에서 "
    "의사(치료받는 국가의 법에서 정한 병원 및 의사의 자격을 가진 자에 한함)의 치료를 받은 때에는 "
    "보험가입금액을 한도로 피보험자가 실제 부담한 의료비 전액을 보상합니다."
)

CLAUSE_B008_ILL_EXTEND = (
    "제3조(보장종목별 보상내용) - (2)질병의료비 (보험기간 후 연장)\n"
    "해외여행 중에 피보험자가 발생한 질병으로 인해 치료를 받던 중 보험기간이 끝났을 경우에는 "
    "보험기간 종료일부터 180일까지(보험기간 종료일은 제외합니다) 보상합니다."
)

CLAUSE_B009_ILL_DOMESTIC = (
    "제3조(보장종목별 보상내용) - (2)질병의료비 국내(급여)\n"
    "회사는 피보험자가 보험증권에 기재된 해외여행 중에 발생한 질병으로 인해 국내 의료기관·약국에서 "
    "치료를 받은 때에는 붙임3에 따라 보상합니다. 다만, 보험기간이 1년 미만인 경우에는 해외여행 중에 "
    "질병을 원인으로 하여 보험기간 종료후 30일(보험기간 종료일은 제외합니다) 이내에 의사의 치료를 받기 시작했을 때에는 "
    "의사의 치료를 받기 시작한 날부터 180일(통원은 180일 동안 90회)까지만(보험기간 종료일은 제외합니다) 보상합니다."
)

CLAUSE_B010_EXCEPTION_FATIGUE = (
    "제4조(보상하지 않는 사항) - (1)상해의료비 해외/국내\n"
    "다음 각 호의 질병으로 발생한 의료비는 보상하지 않습니다:\n"
    "가. 단순한 피로 또는 권태"
)

CLAUSE_B011_EXCEPTION_SKIN = (
    "제4조(보상하지 않는 사항) - (1)상해의료비 해외/국내\n"
    "나. 주근깨, 다모, 무모, 백모증, 딸기코(주사비), 점, 모반(피보험자가 보험가입당시 태아인 경우 "
    "화염상모반 등 선천성 비신생물성모반(Q82.5)은 보상합니다), 사마귀, 여드름, 노화현상으로 인한 탈모 등 피부질환"
)

CLAUSE_B012_EXCEPTION_SEXUAL = (
    "제4조(보상하지 않는 사항) - (1)상해의료비 해외/국내\n"
    "다. 발기부전(impotence)ㆍ불감증, 단순 코골음(수면무호흡증(G47.3)은 보상합니다), "
    "치료를 동반하지 않는 단순포경(phimosis)"
)

CLAUSE_B013_EXCEPTION_DENTAL = (
    "제4조(보상하지 않는 사항)\n"
    "8. 치아보철, 보존, 금관, 틀니, 의치 및 임플란트로 인한 의료비"
)

CLAUSE_B014_EXCEPTION_COSMETIC = (
    "제4조(보상하지 않는 사항)\n"
    "5. 외모개선 목적의 치료로 인하여 발생한 의료비:\n"
    "가. 쌍꺼풀수술(이중검수술. 다만, 안검하수, 안검내반 등을 치료하기 위한 시력개선 목적의 이중검수술은 보상합니다), "
    "코성형수술(융비술), 유방확대(다만, 유방암 환자의 유방재건술은 보상합니다)·축소술, 지방흡입술, 주름살제거술 등"
)

CLAUSE_B015_EXCEPTION_NONINSURED = (
    "제4조의2(특별약관에서 보상하는 사항)\n"
    "제3조 및 제4조에도 불구하고 다음 각 호에 해당하는 국내 상해의료비 및 국내 질병의료비는 "
    "기본형 해외여행 실손의료비 특별약관에서 보상하지 않습니다:\n"
    "1. 비급여의료비\n"
    "2. 제1호와 관련하여 자동차보험(공제를 포함합니다) 또는 산재보험에서 발생한 본인부담의료비"
)

CLAUSE_B016_LIMIT_ANNUAL = (
    "제5조(보험가입금액 한도 등)\n"
    "이 계약의 보험가입금액은 (1)상해의료비 해외, (2)질병의료비 해외의 경우 각각에 대하여 "
    "계약시 계약자가 선택한 금액, (1)상해의료비 국내(급여), (2)질병의료비 국내(급여)의 경우 연간 "
    "(1)상해의료비 국내(급여)에 대하여 입원과 통원의 보상금액을 합산하여 5천만원 이내에서, "
    "(2)질병의료비 국내(급여)에 대하여 입원과 통원의 보상금액을 합산하여 5천만원 이내에서 "
    "회사가 정한 금액 중 계약자가 선택한 금액을 말하며, 제3조(보장종목별 보상내용)에 의한 의료비를 "
    "이 금액 한도 내에서 보상합니다."
)


def run():
    """
    청크 B: 기본형 해외여행 실손의료비 특별약관 시드
    - PolicyVersion 조회 (첫 청크에서 생성됨)
    - OVS_INJ_MED, OVS_ILL_MED 담보 및 조항 추가
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
        coverage_std_inj = get_or_create_coverage_std(
            db, "OVS_INJ_MED", "해외발생 상해의료비", "의료", is_base=False
        )
        coverage_std_ill = get_or_create_coverage_std(
            db, "OVS_ILL_MED", "해외발생 질병의료비", "의료", is_base=False
        )

        # 3. Coverage 생성 또는 재사용
        coverage_inj = db.query(Coverage).filter(
            Coverage.policy_version_id == policy_version.policy_version_id,
            Coverage.raw_name == "기본형 해외여행 실손의료비 특별약관 - 상해의료비"
        ).first()
        if not coverage_inj:
            coverage_inj = Coverage(
                policy_version_id=policy_version.policy_version_id,
                coverage_std_id=coverage_std_inj.coverage_std_id,
                raw_name="기본형 해외여행 실손의료비 특별약관 - 상해의료비",
                definition="해외여행 중 상해로 인한 해외 및 국내 의료비 보상",
                limit_amount=None,
                deductible=None,
                waiting_condition=None
            )
            db.add(coverage_inj)
            db.flush()

        coverage_ill = db.query(Coverage).filter(
            Coverage.policy_version_id == policy_version.policy_version_id,
            Coverage.raw_name == "기본형 해외여행 실손의료비 특별약관 - 질병의료비"
        ).first()
        if not coverage_ill:
            coverage_ill = Coverage(
                policy_version_id=policy_version.policy_version_id,
                coverage_std_id=coverage_std_ill.coverage_std_id,
                raw_name="기본형 해외여행 실손의료비 특별약관 - 질병의료비",
                definition="해외여행 중 질병으로 인한 해외 및 국내 의료비 보상",
                limit_amount=None,
                deductible=None,
                waiting_condition=None
            )
            db.add(coverage_ill)
            db.flush()

        # 4. Clause 생성
        clauses_to_add = [
            # 상해의료비 관련
            {
                "coverage_id": coverage_inj.coverage_id,
                "clause_type": "보장정의",
                "article_no": "[기본형 해외여행 실손의료비 특별약관] 제1조(보장종목)",
                "text": CLAUSE_B001_COVERAGE_TYPE,
                "page_ref": "K3 p.50",
                "default_color": "파랑"
            },
            {
                "coverage_id": coverage_inj.coverage_id,
                "clause_type": "보장정의",
                "article_no": "[기본형 해외여행 실손의료비 특별약관] 제3조(보장종목별 보상내용) - 상해 해외",
                "text": CLAUSE_B002_INJ_OVERSEAS,
                "page_ref": "K3 p.51",
                "default_color": "파랑"
            },
            {
                "coverage_id": coverage_inj.coverage_id,
                "clause_type": "제한",
                "article_no": "[기본형 해외여행 실손의료비 특별약관] 제3조 - 척추지압술·침술",
                "text": CLAUSE_B003_INJ_SPINAL,
                "page_ref": "K3 p.51-52",
                "default_color": "초록"
            },
            {
                "coverage_id": coverage_inj.coverage_id,
                "clause_type": "보장정의",
                "article_no": "[기본형 해외여행 실손의료비 특별약관] 제3조 - 유독물질 중독",
                "text": CLAUSE_B004_INJ_POISON,
                "page_ref": "K3 p.52",
                "default_color": "파랑"
            },
            {
                "coverage_id": coverage_inj.coverage_id,
                "clause_type": "조건",
                "article_no": "[기본형 해외여행 실손의료비 특별약관] 제3조 - 보험기간 후 연장",
                "text": CLAUSE_B005_INJ_EXTEND,
                "page_ref": "K3 p.52",
                "default_color": "노랑"
            },
            {
                "coverage_id": coverage_inj.coverage_id,
                "clause_type": "보장정의",
                "article_no": "[기본형 해외여행 실손의료비 특별약관] 제3조 - 상해 국내(급여)",
                "text": CLAUSE_B006_INJ_DOMESTIC,
                "page_ref": "K3 p.59",
                "default_color": "파랑"
            },
            # 질병의료비 관련
            {
                "coverage_id": coverage_ill.coverage_id,
                "clause_type": "보장정의",
                "article_no": "[기본형 해외여행 실손의료비 특별약관] 제3조 - 질병 해외",
                "text": CLAUSE_B007_ILL_OVERSEAS,
                "page_ref": "K3 p.51",
                "default_color": "파랑"
            },
            {
                "coverage_id": coverage_ill.coverage_id,
                "clause_type": "조건",
                "article_no": "[기본형 해외여행 실손의료비 특별약관] 제3조 - 질병 보험기간 후 연장",
                "text": CLAUSE_B008_ILL_EXTEND,
                "page_ref": "K3 p.52",
                "default_color": "노랑"
            },
            {
                "coverage_id": coverage_ill.coverage_id,
                "clause_type": "보장정의",
                "article_no": "[기본형 해외여행 실손의료비 특별약관] 제3조 - 질병 국내(급여)",
                "text": CLAUSE_B009_ILL_DOMESTIC,
                "page_ref": "K3 p.61",
                "default_color": "파랑"
            },
            # 면책 조항
            {
                "coverage_id": coverage_inj.coverage_id,
                "clause_type": "면책",
                "article_no": "[기본형 해외여행 실손의료비 특별약관] 제4조 - 피로·권태",
                "text": CLAUSE_B010_EXCEPTION_FATIGUE,
                "page_ref": "K3 p.60",
                "default_color": "빨강"
            },
            {
                "coverage_id": coverage_inj.coverage_id,
                "clause_type": "면책",
                "article_no": "[기본형 해외여행 실손의료비 특별약관] 제4조 - 피부질환",
                "text": CLAUSE_B011_EXCEPTION_SKIN,
                "page_ref": "K3 p.60",
                "default_color": "빨강"
            },
            {
                "coverage_id": coverage_inj.coverage_id,
                "clause_type": "면책",
                "article_no": "[기본형 해외여행 실손의료비 특별약관] 제4조 - 성병관련",
                "text": CLAUSE_B012_EXCEPTION_SEXUAL,
                "page_ref": "K3 p.60",
                "default_color": "빨강"
            },
            {
                "coverage_id": coverage_inj.coverage_id,
                "clause_type": "면책",
                "article_no": "[기본형 해외여행 실손의료비 특별약관] 제4조 - 치아보철",
                "text": CLAUSE_B013_EXCEPTION_DENTAL,
                "page_ref": "K3 p.61",
                "default_color": "빨강"
            },
            {
                "coverage_id": coverage_inj.coverage_id,
                "clause_type": "면책",
                "article_no": "[기본형 해외여행 실손의료비 특별약관] 제4조 - 외모개선",
                "text": CLAUSE_B014_EXCEPTION_COSMETIC,
                "page_ref": "K3 p.60-61",
                "default_color": "빨강"
            },
            {
                "coverage_id": coverage_inj.coverage_id,
                "clause_type": "제한",
                "article_no": "[기본형 해외여행 실손의료비 특별약관] 제4조의2 - 비급여 제외",
                "text": CLAUSE_B015_EXCEPTION_NONINSURED,
                "page_ref": "K3 p.62",
                "default_color": "초록"
            },
            # 제한 조항
            {
                "coverage_id": coverage_inj.coverage_id,
                "clause_type": "제한",
                "article_no": "[기본형 해외여행 실손의료비 특별약관] 제5조 - 보험가입금액 한도",
                "text": CLAUSE_B016_LIMIT_ANNUAL,
                "page_ref": "K3 p.62",
                "default_color": "초록"
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
        print("Chunk B seeding complete - OK")

    except Exception as e:
        db.rollback()
        print(f"Chunk B seeding failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("run() 함수를 직접 호출하여 실행하세요.")
