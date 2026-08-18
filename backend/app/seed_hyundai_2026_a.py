"""
현대해상 다이렉트 해외여행보험 2026년판 청크 a - Product/PolicyVersion 생성
파일 출처: backend/data/processed/hyundai_overseas_8403-0000-20260606_full_text.txt
담당 페이지: 1-39 (===PAGE 1=== ~ ===PAGE 39===)

## 페이지 범위 분석
- 페이지 1: 표지 (약관분류코드: 8403-0000-20260606)
- 페이지 2-14: 약관 사용 가이드, 간편 설명서, 계약자 유의사항
- 페이지 15-19: 상세 목차 (보통약관 및 특별약관 목록)
- 페이지 20-39: 다이렉트 해외여행보험 보통약관 (제1-41조)

## 보통약관 조항 (제1관-제6관)
제1관: 목적 및 용어의 정의
  - 제1조: 목적 - 상해보험계약의 목적 정의 (사고 분류 무관, 계약행정)
  - 제2조: 용어의 정의 - 계약관계/지급사유/이자율/기간/날짜 용어 (사고 분류 무관)

제2관: 보험금의 지급
  - 제3조: 보험금의 지급사유 - 사망/후유장해 기본 정의만 포함 (상세 지급사유는 특약에서 정함)
  - 제4조: 보험금 지급에 관한 세부규정 - 실종선고, 연명의료중단, 장해지급률 판정 등
  - 제5조: 보험금을 지급하지 않는 사유 - 고의, 임신/출산, 전쟁 등 기본 면책사유
  - 제6-11조: 지급사유 통지, 청구서류, 지급절차, 방법 변경, 주소변경, 보험수익자 지정, 대표자 지정

제3관: 계약자의 계약 전 알릴의무 등
  - 제13-16조: 계약전/후 알릴의무, 알릴의무 위반 효과, 사기에 의한 계약

제4관: 보험계약의 성립과 유지
  - 제17-23조: 계약의 성립, 청약철회, 약관교부, 계약무효, 내용변경, 계약소멸

제5관: 보험료의 납입
  - 제24-28조: 보험료 납입, 납입연체, 계약해지, 부활

제6관: 계약의 해지 및 환급
  - 제29-32조: 임의해지, 해지, 환급

제7관: 분쟁의 조정 등
  - 제33-41조: 분쟁조정, 관할법원, 소멸시효, 약관해석, 개인정보보호, 준거법, 예금보험

## 발견 요약
페이지 1-39는 표지, 안내사항, 보통약관으로 구성. 보통약관에서 기저 담보 DEATH_INJURY의
지급사유(제3조)와 면책(제5조) 조항을 발견했다. 나머지는 계약행정 조항.
- 제3조(보험금의 지급사유): 사망·후유장해 기본 정의 → Clause 추가 (보장정의)
- 제5조(보험금을 지급하지 않는 사유): 고의·임신출산·전쟁 등 → Clause 추가 (면책)
- 제1-2조, 제4조, 제6-41조: 계약행정 (확인함, 건너뜸)

실제 특별약관(상세 보장)은 페이지 40부터 시작.

## 확인함/무관 목록
- 제1-2조: 목적/용어정의 (확인함, 무관)
- 제4조: 보험금 지급에 관한 세부규정 (확인함, 무관)
- 제6-41조: 청구절차, 계약행정 등 (확인함, 무관)

## 새로 만드는 CoverageStd
없음 - DEATH_INJURY는 이미 있는 기준 코드

## 시드 전략
- idempotent: Insurer(HYUNDAI) 조회 후 없으면 생성
- Product 조회 후 없으면 생성
- PolicyVersion 조회 후 없으면 생성
- 같은 product_code/version_label 조합이 이미 있으면 건너뜀
"""
from datetime import date
from app.database import SessionLocal
from app import models  # noqa: F401
from app.models.kb import Clause, Coverage, Insurer, PolicyVersion, Product
from app.services.kb_seed_common import get_or_create_coverage_std

PRODUCT_CODE = "HYUNDAI-OVERSEAS-2026"
VERSION_LABEL = "8403-0000-20260606"
FILE_HASH = "19fcd2966b4d17fdca41bd8edfdfff028a4de3ba38ed3574e83406262ec3c878"

# 제3조 보험금의 지급사유 (보장정의)
CLAUSE_3_TEXT = (
    "회사는 피보험자가 보험증권에 기재된 여행을 목적으로 주거지를 출발하여 여행을 마치고 주거지에 도착할 때까지의 "
    "여행도중에 다음 중 어느 하나의 사유가 발생한 경우에는 보험수익자에게 약정한 보험금을 지급합니다. "
    "1. 보험기간 중에 상해의 직접결과로써 사망한 경우(질병으로 인한 사망은 제외합니다): 사망보험금 "
    "2. 보험기간 중 상해로 장해분류표(<별표1> 참조)에서 정한 각 장해지급률에 해당하는 장해상태가 되었을 때: 후유장해보험금"
)

# 제5조 보험금을 지급하지 않는 사유 (면책)
CLAUSE_5_TEXT = (
    "① 회사는 다음 중 어느 한가지로 보험금 지급사유가 발생한 때에는 보험금을 지급하지 않습니다. "
    "1. 피보험자가 고의로 자신을 해친 경우. 다만, 피보험자가 심신상실 등으로 자유로운 의사결정을 할 수 없는 상태에서 "
    "자신을 해친 경우에는 보험금을 지급합니다. "
    "2. 보험수익자가 고의로 피보험자를 해친 경우. 다만, 그 보험수익자가 보험금의 일부 보험수익자인 경우에는 "
    "다른 보험수익자에 대한 보험금은 지급합니다. "
    "3. 계약자가 고의로 피보험자를 해친 경우 "
    "4. 피보험자의 임신, 출산(제왕절개를 포함합니다), 산후기. 그러나, 회사가 보장하는 보험금 지급사유와 보장개시일부터 "
    "2년이 지난 후에 발생한 습관성 유산, 불임 및 인공수정 관련 합병증으로 인한 경우에는 보험금을 지급합니다. "
    "5. 전쟁, 외국의 무력행사, 혁명, 내란, 사변, 폭동 "
    "② 회사는 다른 약정이 없으면 피보험자가 직업, 직무 또는 동호회 활동목적으로 아래에 열거된 행위로 인하여 "
    "제3조(보험금의 지급사유)의 상해 관련 보험금 지급사유가 발생한 때에는 해당 보험금을 지급하지 않습니다. "
    "1. 전문등반(전문적인 등산용구를 사용하여 암벽 또는 빙벽을 오르내리거나 특수한 기술, 경험, 사전훈련을 "
    "필요로 하는 등반을 말합니다), 글라이더 조종, 스카이다이빙, 스쿠버다이빙, 행글라이딩, 수상보트, 패러글라이딩 "
    "2. 모터보트, 자동차 또는 오토바이에 의한 경기, 시범, 흥행(이를 위한 연습을 포함합니다) 또는 시운전(다만, "
    "공용도로상에서 시운전을 하는 동안 보험금 지급사유가 발생한 경우에는 보장합니다) "
    "3. 선박에 탑승하는 것을 직무로 하는 사람이 직무상 선박에 탑승하고 있는 동안"
)


def run():
    """현대해상 다이렉트 해외여행보험 Product/PolicyVersion 및 기본 담보 생성."""
    db = SessionLocal()

    try:
        # Insurer 조회/생성
        insurer = db.query(Insurer).filter(Insurer.code == 'HYUNDAI').first()
        if not insurer:
            insurer = Insurer(
                name='현대해상',
                code='HYUNDAI',
                is_underwriter=True,
                official_url='https://www.hi.co.kr'
            )
            db.add(insurer)
            db.flush()
            print("Created Insurer: HYUNDAI")

        # Product 조회/생성
        product = db.query(Product).filter(
            Product.insurer_id == insurer.insurer_id,
            Product.product_code == PRODUCT_CODE
        ).first()
        if not product:
            product = Product(
                insurer_id=insurer.insurer_id,
                name='다이렉트 해외여행보험',
                product_code=PRODUCT_CODE,
                channel='다이렉트',
                sale_start=date(2026, 6, 6),
                sale_end=None,
                collected_at=date(2026, 6, 6),
                review_status='raw'
            )
            db.add(product)
            db.flush()
            print(f"Created Product: {PRODUCT_CODE}")

        # PolicyVersion 조회/생성
        pv = db.query(PolicyVersion).filter(
            PolicyVersion.product_id == product.product_id,
            PolicyVersion.version_label == VERSION_LABEL
        ).first()
        if not pv:
            pv = PolicyVersion(
                product_id=product.product_id,
                version_label=VERSION_LABEL,
                effective_date=date(2026, 6, 6),
                approval_no='8403-0000-20260606',
                source_url=None,
                file_hash=FILE_HASH
            )
            db.add(pv)
            db.flush()
            print(f"Created PolicyVersion: {VERSION_LABEL}")
        else:
            print(f"PolicyVersion already exists: {VERSION_LABEL}")

        # DEATH_INJURY Coverage (기저 담보) 조회/생성
        coverage_std = get_or_create_coverage_std(
            db, 'DEATH_INJURY', '상해사망·후유장해', '상해', is_base=True
        )

        coverage = db.query(Coverage).filter(
            Coverage.policy_version_id == pv.policy_version_id,
            Coverage.raw_name == '상해사망 및 후유장해'
        ).first()
        if not coverage:
            coverage = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=coverage_std.coverage_std_id,
                raw_name='상해사망 및 후유장해',
                definition='상해로 인한 사망 및 후유장해 보상'
            )
            db.add(coverage)
            db.flush()
            print("Created Coverage: DEATH_INJURY")

        # 제3조 보장정의 Clause
        existing_clause3 = db.query(Clause).filter(
            Clause.coverage_id == coverage.coverage_id,
            Clause.text == CLAUSE_3_TEXT
        ).first()
        if not existing_clause3:
            clause3 = Clause(
                policy_version_id=pv.policy_version_id,
                coverage_id=coverage.coverage_id,
                article_no='제3조(보험금의 지급사유)',
                text=CLAUSE_3_TEXT,
                clause_type='보장정의',
                default_color='파랑',
                page_ref='p.20-21'
            )
            db.add(clause3)
            print("Created Clause: 제3조(보험금의 지급사유)")

        # 제5조 면책 Clause
        existing_clause5 = db.query(Clause).filter(
            Clause.coverage_id == coverage.coverage_id,
            Clause.text == CLAUSE_5_TEXT
        ).first()
        if not existing_clause5:
            clause5 = Clause(
                policy_version_id=pv.policy_version_id,
                coverage_id=coverage.coverage_id,
                article_no='제5조(보험금을 지급하지 않는 사유)',
                text=CLAUSE_5_TEXT,
                clause_type='면책',
                default_color='빨강',
                page_ref='p.23-24'
            )
            db.add(clause5)
            print("Created Clause: 제5조(보험금을 지급하지 않는 사유)")

        db.commit()
        print("Successfully seeded HYUNDAI Product/PolicyVersion/Coverage/Clause")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == '__main__':
    run()
