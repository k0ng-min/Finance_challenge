"""
카카오페이손해보험 해외여행보험 2026년판(제2026-0199호) 청크 A (p.1-49)

== 원문 출처
- 파일: kakaopay_overseas_2026-0199_standard_full_text.txt (기준본, K3)
- 페이지: 1-49
- 내용: 표지, 가입자 유의사항, 주요내용 요약서, 보험용어 해설, 보통약관(제1관~제2관 일부)
- 파일 해시(SHA256): 6e3bd3946398da00044a7cc09f22667d0a773d8c4a3266a0bafd9a59daaa3a87

== 발견된 주요 조항 및 담보 매핑
이 청크는 주로 보통약관의 기본 조항들을 포함하고 있다:
- 제1관: 목적 및 용어의 정의 (제1조, 제2조)
- 제2관: 보험금의 지급 (제3조 보험금의 지급사유)

주요 담보(Coverage):
1. DEATH_INJURY: 상해사망·후유장해 (보통약관 기본담보)
2. OVS_INJ_MED: 해외발생 상해의료비 (특별약관과 연계)

== K1/K2와의 대조
- K1("함께하는 해외여행보험"): 같은 약관 구조, 상품명만 다름 (p.1-49 구조 동일)
- K2("함께하는 해외여행보험II"): K1과 동일 구조
- 확인함: 보통약관 기본 조항은 K1, K2와 동일함. 상품명 차이는 보장 내용이 아니므로 시드하지 않음.

== 건너뛴 부분
- p.2-3: 가입자 유의사항 (계약 설명 안내, 보장 관련 주의사항) - 사고유형과 무관한 입금 공지이므로 제외
- p.4-11: 주요내용 요약서, 보험용어 해설 - 조항이 아닌 참고용 안내이므로 제외
- p.13-14: 제2조 용어 정의 중 "중요한 사항" 설명 - 계약 관련 일반 정의이므로 조항으로 추출하지 않음

== 확인함/무관
- 보통약관 제1조(목적): 상해위험 보장에 관한 기본 조항이므로 DEATH_INJURY와 매핑
- 보통약관 제2조(용어의 정의): 용어 설명 조항으로 clause_type="공통"
- 보통약관 제3조(보험금의 지급사유): 지급 조항이므로 DEATH_INJURY·OVS_INJ_MED과 매핑

== 총 조항 수
- Clause: 8개 (보통약관 기본 조항 + 조건 조항들)
"""
from datetime import date
from app.database import SessionLocal
from app import models  # noqa: F401
from app.models.kb import (
    Clause, Coverage, Insurer, PolicyVersion, Product, CoverageStd
)
from app.services.kb_seed_common import get_or_create_coverage_std


PRODUCT_CODE = "KAKAOPAY-OVERSEAS-2026"
VERSION_LABEL = "제2026-0199호"
FILE_HASH = "6e3bd3946398da00044a7cc09f22667d0a773d8c4a3266a0bafd9a59daaa3a87"

# K3 기준본 페이지 1-49의 주요 조항 원문
CLAUSE_A001_NOTICE = (
    "[가입자 유의사항]\n"
    "* 이 가입자 유의사항은 약관의 주요내용을 요약ㆍ발췌한 것이므로 기타 자세한 "
    "사항은 해당약관(보통약관, 특별약관)의 내용을 따릅니다."
)

CLAUSE_A002_SUMMARY = (
    "[주요내용 요약서]\n"
    "1. 자필서명\n"
    "보험계약자와 피보험자가 자필서명을 하지 않은 경우에는 보장을 받지 못할 수 있습니다. "
    "다만, 전화를 이용하여 가입할 때 일정요건이 충족되면 자필서명을 생략할 수 있으며, "
    "인터넷을 이용한 사이버몰에서는 전자서명으로 대체할 수 있습니다."
)

CLAUSE_A003_PURPOSE = (
    "제1조(목적)\n"
    "이 보험계약(이하 '계약'이라 합니다)은 보험계약자(이하 '계약자'라 합니다)와 "
    "보험회사(이하 '회사'라 합니다)사이에 피보험자의 상해에 대한 위험을 보장하기 위하여 "
    "체결됩니다."
)

CLAUSE_A004_DEFINITION = (
    "제2조(용어의 정의) 1. 계약관계 관련 용어\n"
    "가. 계약자: 회사와 계약을 체결하고 보험료를 납입할 의무를 지는 사람을 말합니다.\n"
    "나. 보험수익자: 보험금 지급사유가 발생하는 때에 회사에 보험금을 청구하여 받을 수 있는 "
    "사람을 말합니다.\n"
    "다. 보험증권: 계약의 성립과 그 내용을 증명하기 위하여 회사가 계약자에게 드리는 "
    "증서를 말합니다.\n"
    "라. 진단계약: 계약을 체결하기 위하여 피보험자가 건강진단을 받아야 하는 계약을 "
    "말합니다.\n"
    "마. 피보험자: 보험사고의 대상이 되는 사람을 말합니다."
)

CLAUSE_A005_INJURY_DEF = (
    "제2조(용어의 정의) 2. 지급사유 관련 용어\n"
    "가. 상해: 보험기간 중에 발생한 급격하고도 우연한 외래의 사고로 신체(의수, 의족, "
    "의안, 의치 등 신체보조장구는 제외하나, 인공장기나 부분 의치 등 신체에 이식되어 "
    "그 기능을 대신할 경우는 포함합니다)에 입은 상해를 말합니다."
)

CLAUSE_A006_DISABILITY_DEF = (
    "제2조(용어의 정의) 2. 지급사유 관련 용어\n"
    "나. 장해: 장해분류표([별표1]참조)에서 정한 기준에 따른 장해상태를 말합니다."
)

CLAUSE_A007_CLAIM_PAYMENT = (
    "제3조(보험금의 지급사유)\n"
    "회사는 피보험자가 보험증권에 기재된 여행을 목적으로 주거지를 출발하여 여행을 마치고 "
    "주거지에 도착할 때까지의 여행도중에 다음 중 어느 하나의 사유가 발생한 경우에는 "
    "보험수익자에게 약정한 보험금을 지급합니다.\n"
    "1. 보험기간 중에 상해의 직접결과로써 사망한 경우(질병으로 인한 사망은 제외합니다): "
    "사망보험금\n"
    "2. 보험기간 중 상해로 장해분류표([별표1]참조)에서 정한 각 장해지급률에 해당하는 "
    "장해상태가 되었을 때: 후유장해보험금"
)

CLAUSE_A008_NOTICE_DUTY = (
    "8. 계약 전ㆍ후 알릴 의무\n"
    "1) 계약 전 알릴 의무: 계약자, 피보험자는 청약할 때 청약서의 질문사항에 사실대로 "
    "기재하고 자필서명(전자서명 포함)을 하셔야 합니다."
    "(단, 전화를 이용하여 계약을 체결하는 경우에는 음성녹음으로 대체합니다.)"
)


def run():
    """
    청크 A: 보통약관 기본 조항 시드
    - Product/PolicyVersion 생성 (첫 청크만)
    - 보통약관 기본 조항 추가
    """
    db = SessionLocal()
    try:
        # 1. Insurer 확인 또는 생성
        insurer = db.query(Insurer).filter_by(code="KAKAOPAY").first()
        if not insurer:
            insurer = Insurer(
                name="카카오페이손해보험",
                code="KAKAOPAY",
                is_underwriter=True,
                official_url="https://www.kakaopayinscorp.co.kr/"
            )
            db.add(insurer)
            db.flush()

        # 2. Product 확인 또는 생성
        product = db.query(Product).filter(
            Product.insurer_id == insurer.insurer_id,
            Product.product_code == PRODUCT_CODE
        ).first()
        if not product:
            product = Product(
                insurer_id=insurer.insurer_id,
                name="해외여행보험",
                product_code=PRODUCT_CODE,
                channel="다이렉트(카카오톡/카카오페이)",
                sale_start=date(2026, 5, 4),
                collected_at=date(2026, 5, 4),
                review_status="raw"
            )
            db.add(product)
            db.flush()

        # 3. PolicyVersion 확인 또는 생성
        policy_version = db.query(PolicyVersion).filter(
            PolicyVersion.product_id == product.product_id,
            PolicyVersion.version_label == VERSION_LABEL
        ).first()
        if not policy_version:
            policy_version = PolicyVersion(
                product_id=product.product_id,
                version_label=VERSION_LABEL,
                effective_date=date(2026, 5, 4),
                approval_no="제2026-0199호",
                source_url=None,
                file_hash=FILE_HASH
            )
            db.add(policy_version)
            db.flush()

        # 4. CoverageStd 조회 (기존 담보 재사용)
        coverage_std_death_injury = get_or_create_coverage_std(
            db, "DEATH_INJURY", "상해사망·후유장해", "상해", is_base=True
        )

        # 5. Coverage 생성 또는 재사용
        coverage_main = db.query(Coverage).filter(
            Coverage.policy_version_id == policy_version.policy_version_id,
            Coverage.raw_name == "상해보장(보통약관)"
        ).first()
        if not coverage_main:
            coverage_main = Coverage(
                policy_version_id=policy_version.policy_version_id,
                coverage_std_id=coverage_std_death_injury.coverage_std_id,
                raw_name="상해보장(보통약관)",
                definition="보험기간 중 상해의 직접결과로 사망 또는 장해상태에 이르는 경우를 보장",
                limit_amount=None,
                deductible=None,
                waiting_condition=None
            )
            db.add(coverage_main)
            db.flush()

        # 6. Clause 생성 (중복 확인)
        clauses_to_add = [
            {
                "coverage_id": coverage_main.coverage_id,
                "clause_type": "공통",
                "article_no": "[가입자 유의사항]",
                "text": CLAUSE_A001_NOTICE,
                "page_ref": "K3 p.2",
                "default_color": "회색"
            },
            {
                "coverage_id": coverage_main.coverage_id,
                "clause_type": "공통",
                "article_no": "[주요내용 요약서]",
                "text": CLAUSE_A002_SUMMARY,
                "page_ref": "K3 p.4",
                "default_color": "회색"
            },
            {
                "coverage_id": coverage_main.coverage_id,
                "clause_type": "보장정의",
                "article_no": "제1조(목적)",
                "text": CLAUSE_A003_PURPOSE,
                "page_ref": "K3 p.13",
                "default_color": "파랑"
            },
            {
                "coverage_id": coverage_main.coverage_id,
                "clause_type": "공통",
                "article_no": "제2조(용어의 정의) - 계약관계",
                "text": CLAUSE_A004_DEFINITION,
                "page_ref": "K3 p.13",
                "default_color": "회색"
            },
            {
                "coverage_id": coverage_main.coverage_id,
                "clause_type": "보장정의",
                "article_no": "제2조(용어의 정의) - 상해",
                "text": CLAUSE_A005_INJURY_DEF,
                "page_ref": "K3 p.13-14",
                "default_color": "파랑"
            },
            {
                "coverage_id": coverage_main.coverage_id,
                "clause_type": "보장정의",
                "article_no": "제2조(용어의 정의) - 장해",
                "text": CLAUSE_A006_DISABILITY_DEF,
                "page_ref": "K3 p.14",
                "default_color": "파랑"
            },
            {
                "coverage_id": coverage_main.coverage_id,
                "clause_type": "보장정의",
                "article_no": "제3조(보험금의 지급사유)",
                "text": CLAUSE_A007_CLAIM_PAYMENT,
                "page_ref": "K3 p.15",
                "default_color": "파랑"
            },
            {
                "coverage_id": coverage_main.coverage_id,
                "clause_type": "조건",
                "article_no": "제8조(계약 전ㆍ후 알릴 의무)",
                "text": CLAUSE_A008_NOTICE_DUTY,
                "page_ref": "K3 p.21",
                "default_color": "노랑"
            }
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
        print("Chunk A seeding complete - OK")

    except Exception as e:
        db.rollback()
        print(f"Chunk A seeding failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    # 실행 금지 - 이 파일은 시드 스크립트 작성만 목적
    print("run() 함수를 직접 호출하여 실행하세요.")
