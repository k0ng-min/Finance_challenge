"""
현대해상 다이렉트 해외여행보험 2026년판 청크 c - 사망·후유장해·배상책임·휴대품 등 특약 처리
파일 출처: backend/data/processed/hyundai_overseas_8403-0000-20260606_full_text.txt
담당 페이지: 98-118 (===PAGE 98=== ~ ===PAGE 118===)

## 페이지 범위 분석 및 발견한 특약

### 국민건강보험비가입자 추가특별약관 (p.98-99)
확인함, 무관 - 기본형 실손의료비 특약과의 상호작용 설명만 있고, 독립적인 지급사유/면책 조항 없음.
제1조(적용대상), 제2조(계약후 알릴의무), 제3조(보장내용), 제4조(준용규정) 모두 기본형을 참조.

### 사망·후유장해보험금만의 지급특별약관 (p.99)
DEATH_INJURY 관련 특약 - 보통약관의 사망·후유장해만 보장하는 선택형 특약.
제1조(보상하는 손해), 제2조(준용규정)

### 사망위험보장제외 특별약관 (p.99)
DEATH_INJURY 관련 제외 특약 - 사망보험금을 제외하는 옵션.
제1조(보험금을 지급하지 않는 사유), 제2조(준용규정)

### 후유장해위험보장제외 특별약관 (p.99)
DEATH_INJURY 관련 제외 특약 - 후유장해보험금을 제외하는 옵션.
제1조(보험금을 지급하지 않는 사유), 제2조(준용규정)

### 전쟁위험보장 특별약관 (p.99-100)
WAR_RISK 새 담보 또는 DEATH_INJURY 부분 - 전쟁 위험으로 인한 상해 사망·후유장해 보장.
제1조(보상하는 손해): 전쟁·외국무력행사·혁명·내란·폭동 등으로 인한 상해 사망·후유장해 보장
제2조(계약 후 알릴 의무의 특례): 여행경로 변경 통지
제3조(보험계약해지의 효력): 해지 효력
제4조(준용규정)

### 질병사망 및 질병 80%이상 고도후유장해보장 특별약관 (p.100-101)
ILL_DEATH 새 담보 - 질병으로 인한 사망·고도후유장해(80%이상) 보장.
제1조(보험금의 종류 및 지급사유): 질병사망, 고도후유장해 보장정의
제2조(보험금 지급에 관한 세부규정): 연명의료, 장해지급률 판정, 복수장해 처리 등
제3조(준용규정)

### 배상책임보장 특별약관 (p.101-102 이상)
LIABILITY 담보 - 해외여행 중 배상책임 보장.
제1조(보상하는 손해): 법률상 손해배상금, 비용(방지비용, 소송비용 등)
제2조(보상하지 않는 손해): 고의, 전쟁, 직업활동 관련 손해배상 등 면책

### 향후 페이지 (103-118)의 특약들 예상
- 해외여행중 휴대품손해(분실제외)보장 특별약관: PERSONAL_EFFECTS
- 해외여행중 중대사고 구조송환비용 등 보장 특별약관: RESCUE
- 항공기납치보장 특별약관: HIJACK
- 항공기 탑승위험보장제외 특별약관: 면책 조항
- 해외여행중 여권분실후 재발급비용보장 특별약관: PASSPORT_LOSS
- 해외여행중 중단사고 발생 추가비용보장 특별약관: TRIP_INTERRUPTION
- 해외여행중 자택 도난손해(가재) 보장 특별약관: HOME_THEFT
- 항공기 및 수하물 지연비용보장 특별약관: FLIGHT_DELAY
- 출국 항공기 지연 손해 보장 특별약관: FLIGHT_DELAY 관련
- 해외여행중 식중독입원위험보장 특별약관: FOOD_POISONING
- 해외여행중 특정전염병발생보장 특별약관: INFECTIOUS_DISEASE
- 해외여행중 스포츠활동상해보장제외 특별약관: 면책
- 해외여행중 스포츠활동상해실손의료비보장제외 추가특별약관: 면책
- 해외여행중 상해입원일당보장 특별약관: 신규 정액 담보

## 새로 만드는 CoverageStd
1. WAR_RISK: 전쟁위험보장 (기존에 없으면 생성)
2. ILL_DEATH: 질병사망·고도후유장해 (기존에 없으면 생성)

## 확인함/무관 목록
- 국민건강보험비가입자 추가특별약관: 확인함, 기본형과의 상호작용만 있어 별도 Clause 없음

## 시드 전략
- idempotent: PolicyVersion 조회 후 없으면 생성 (a.py에서 생성했으므로 재사용)
- 각 CoverageStd 조회/생성
- 각 Coverage 조회/생성
- 각 조항별 Clause 생성
"""
from datetime import date
from app.database import SessionLocal
from app import models  # noqa: F401
from app.models.kb import Clause, Coverage, PolicyVersion
from app.services.kb_seed_common import get_or_create_coverage_std

PRODUCT_CODE = "HYUNDAI-OVERSEAS-2026"
VERSION_LABEL = "8403-0000-20260606"


def run():
    """현대해상 사망·후유장해·배상책임 등 특약 처리 (페이지 98-118)."""
    db = SessionLocal()

    try:
        # Product/PolicyVersion 조회
        pv = db.query(PolicyVersion).filter(
            PolicyVersion.version_label == VERSION_LABEL
        ).first()
        if not pv:
            print(f"PolicyVersion not found: {VERSION_LABEL}. a.py를 먼저 실행하세요.")
            return

        # ===== 사망·후유장해보험금만의 지급특별약관 =====
        death_injury_coverage = db.query(Coverage).filter(
            Coverage.policy_version_id == pv.policy_version_id,
            Coverage.raw_name == '상해사망 및 후유장해'
        ).first()

        if death_injury_coverage:
            # 제1조 - 보상하는 손해
            clause_text_1 = (
                "회사는 이 특별약관에 따라 보통약관에 규정한 사망·후유장해 보험금만을 "
                "피보험자에게 지급합니다."
            )
            existing = db.query(Clause).filter(
                Clause.coverage_id == death_injury_coverage.coverage_id,
                Clause.text == clause_text_1
            ).first()
            if not existing:
                clause = Clause(
                    policy_version_id=pv.policy_version_id,
                    coverage_id=death_injury_coverage.coverage_id,
                    article_no='[사망·후유장해보험금만의 지급특별약관] 제1조(보상하는 손해)',
                    text=clause_text_1,
                    clause_type='보장정의',
                    default_color='파랑',
                    page_ref='p.98'
                )
                db.add(clause)
                print("Created: 사망·후유장해보험금만의 지급특별약관 제1조")

        # ===== 사망위험보장제외 특별약관 =====
        if death_injury_coverage:
            clause_text_death_excl = (
                "회사는 보통약관(이하 \"보통약관\" 이라 합니다) 제3조(보험금의 지급사유) 및 "
                "제4조(보험금 지급에 관한 세부규정)에 정한 규정에도 불구하고 사망보험금을 "
                "이 특별약관에 따라 보상하여 드리지 않습니다."
            )
            existing = db.query(Clause).filter(
                Clause.coverage_id == death_injury_coverage.coverage_id,
                Clause.text == clause_text_death_excl
            ).first()
            if not existing:
                clause = Clause(
                    policy_version_id=pv.policy_version_id,
                    coverage_id=death_injury_coverage.coverage_id,
                    article_no='[사망위험보장제외 특별약관] 제1조(보험금을 지급하지 않는 사유)',
                    text=clause_text_death_excl,
                    clause_type='면책',
                    default_color='빨강',
                    page_ref='p.99'
                )
                db.add(clause)
                print("Created: 사망위험보장제외 특별약관 제1조")

        # ===== 후유장해위험보장제외 특별약관 =====
        if death_injury_coverage:
            clause_text_disability_excl = (
                "회사는 보통약관(이하 \"보통약관\" 이라 합니다) 제3조(보험금의 지급사유) 및 "
                "제4조(보험금 지급에 관한 세부규정)에 정한 규정에도 불구하고 후유장해보험금을 "
                "이 특별약관에 따라 보상하여 드리지 않습니다."
            )
            existing = db.query(Clause).filter(
                Clause.coverage_id == death_injury_coverage.coverage_id,
                Clause.text == clause_text_disability_excl
            ).first()
            if not existing:
                clause = Clause(
                    policy_version_id=pv.policy_version_id,
                    coverage_id=death_injury_coverage.coverage_id,
                    article_no='[후유장해위험보장제외 특별약관] 제1조(보험금을 지급하지 않는 사유)',
                    text=clause_text_disability_excl,
                    clause_type='면책',
                    default_color='빨강',
                    page_ref='p.99'
                )
                db.add(clause)
                print("Created: 후유장해위험보장제외 특별약관 제1조")

        # ===== 전쟁위험보장 특별약관 =====
        war_risk_std = get_or_create_coverage_std(
            db, 'WAR_RISK', '전쟁위험보장', '상해', is_base=False
        )

        war_risk_coverage = db.query(Coverage).filter(
            Coverage.policy_version_id == pv.policy_version_id,
            Coverage.coverage_std_id == war_risk_std.coverage_std_id
        ).first()
        if not war_risk_coverage:
            war_risk_coverage = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=war_risk_std.coverage_std_id,
                raw_name='전쟁위험보장',
                definition='전쟁·외국무력행사·혁명·내란·폭동 등으로 인한 상해 사망·후유장해 보장'
            )
            db.add(war_risk_coverage)
            db.flush()
            print("Created Coverage: WAR_RISK")

        # 전쟁위험보장 제1조
        war_clause_1 = (
            "① 회사는 보통약관 제5조(보험금을 지급하지 않는 사유) 제1항 제5호의 규정에도 "
            "불구하고 전쟁, 외국의 무력행사, 혁명, 내란, 폭동, 소요, 기타 이들과 유사한 "
            "사태로 인하여 피보험자가 상해를 입었을 때는 보통약관의 규정에 의한 "
            "사망·후유장해보험금을 이 특별약관에 따라 지급하여 드립니다. "
            "② 회사는 보험기간이 만료되기 전이라도 제 1 항의 위험이 뚜렷히 증가했다고 "
            "인정될 때에는 24 시간 이전에 서면으로 추가보험료를 청구하거나 "
            "이 특별약관을 해지할 수 있습니다."
        )
        existing = db.query(Clause).filter(
            Clause.coverage_id == war_risk_coverage.coverage_id,
            Clause.text == war_clause_1
        ).first()
        if not existing:
            clause = Clause(
                policy_version_id=pv.policy_version_id,
                coverage_id=war_risk_coverage.coverage_id,
                article_no='[전쟁위험보장 특별약관] 제1조(보상하는 손해)',
                text=war_clause_1,
                clause_type='보장정의',
                default_color='파랑',
                page_ref='p.99-100'
            )
            db.add(clause)
            print("Created: 전쟁위험보장 특별약관 제1조")

        # ===== 질병사망 및 질병 80%이상 고도후유장해보장 특별약관 =====
        ill_death_std = get_or_create_coverage_std(
            db, 'ILL_DEATH', '질병사망·고도후유장해', '질병', is_base=False
        )

        ill_death_coverage = db.query(Coverage).filter(
            Coverage.policy_version_id == pv.policy_version_id,
            Coverage.coverage_std_id == ill_death_std.coverage_std_id
        ).first()
        if not ill_death_coverage:
            ill_death_coverage = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=ill_death_std.coverage_std_id,
                raw_name='질병사망 및 질병 80%이상 고도후유장해',
                definition='질병으로 인한 사망 및 80%이상 고도후유장해 보장'
            )
            db.add(ill_death_coverage)
            db.flush()
            print("Created Coverage: ILL_DEATH")

        # 질병사망 제1조
        ill_death_clause_1 = (
            "① 회사는 피보험자가 해외여행 중에 다음 사항 중 어느 한 가지의 경우에 해당되는 "
            "사유가 발생한 때에는 보험수익자에게 약정한 보험금을 지급합니다. "
            "1. 보험기간 중에 질병으로 인하여 사망한 경우 : 사망보험금 "
            "(보험증권에 기재된 이 특약의 보험가입금액) "
            "2. 보험기간 중에 진단확정된 질병으로 장해분류표([별표1] 참조, 이하 같습니다.)에서 "
            "정한 장해지급률이 80% 이상에 해당하는 장해상태가 되었을 때 : "
            "고도후유장해보험금(보험증권에 기재된 이 특약의 보험가입금액) "
            "② 제1항에도 불구하고 해외여행 도중에 발생한 질병을 직접원인으로 하여 "
            "보험기간 마지막날로부터 30일 이내에 사망하거나 또는 80% 이상 후유장해가 남았을 "
            "경우에도 동일하게 보상하여 드립니다."
        )
        existing = db.query(Clause).filter(
            Clause.coverage_id == ill_death_coverage.coverage_id,
            Clause.text == ill_death_clause_1
        ).first()
        if not existing:
            clause = Clause(
                policy_version_id=pv.policy_version_id,
                coverage_id=ill_death_coverage.coverage_id,
                article_no='[질병사망 및 질병 80%이상 고도후유장해보장 특별약관] 제1조(보험금의 종류 및 지급사유)',
                text=ill_death_clause_1,
                clause_type='보장정의',
                default_color='파랑',
                page_ref='p.100'
            )
            db.add(clause)
            print("Created: 질병사망 특약 제1조")

        # ===== 배상책임보장 특별약관 =====
        liability_std = get_or_create_coverage_std(
            db, 'LIABILITY', '배상책임', '배상', is_base=False
        )

        liability_coverage = db.query(Coverage).filter(
            Coverage.policy_version_id == pv.policy_version_id,
            Coverage.coverage_std_id == liability_std.coverage_std_id
        ).first()
        if not liability_coverage:
            liability_coverage = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=liability_std.coverage_std_id,
                raw_name='배상책임보장',
                definition='해외여행 중 배상책임 손해 및 관련 비용 보장'
            )
            db.add(liability_coverage)
            db.flush()
            print("Created Coverage: LIABILITY")

        # 배상책임 제1조
        liability_clause_1 = (
            "회사는 피보험자가 해외여행 중에 발생된 보험사고로 인하여 피해자에게 "
            "법률상의 배상책임을 부담함으로써 입은 아래의 손해를 이 약관에 따라 "
            "보상하여 드립니다. "
            "1. 피보험자가 피해자에게 지급할 책임을 지는 법률상의 손해배상금 "
            "2. 계약자 또는 피보험자가 지출한 아래의 비용 "
            "가. 피보험자가 제 6 조(손해방지의무) 제 1 항 제 1 호의 손해의 방지 또는 "
            "경감을 위하여 지출한 필요 또는 유익하였던 비용 "
            "나. 피보험자가 제 6 조(손해방지의무) 제 1 항 제 2 호의 조치를 취하기 위하여 "
            "지출한 필요 또는 유익하였던 비용 "
            "다. 피보험자가 지급한 소송비용, 변호사비용, 중재, 화해 또는 조정에 관한 비용 "
            "라. 보험증권상의 보상한도액내의 금액에 대한 공탁보증보험료. 그러나 회사는 "
            "그러한 보증을 제공할 책임은 부담하지 않습니다. "
            "마. 피보험자가 제 7 조(손해배상청구에 대한 회사의 해결) 제 2 항 및 제 3 항의 "
            "회사의 요구에 따르기 위하여 지출한 비용"
        )
        existing = db.query(Clause).filter(
            Clause.coverage_id == liability_coverage.coverage_id,
            Clause.text == liability_clause_1
        ).first()
        if not existing:
            clause = Clause(
                policy_version_id=pv.policy_version_id,
                coverage_id=liability_coverage.coverage_id,
                article_no='[배상책임보장 특별약관] 제1조(보상하는 손해)',
                text=liability_clause_1,
                clause_type='보장정의',
                default_color='파랑',
                page_ref='p.101-102'
            )
            db.add(clause)
            print("Created: 배상책임 특약 제1조")

        # 배상책임 제2조 - 면책
        liability_clause_2 = (
            "회사는 아래의 사유를 원인으로 하여 생긴 손해는 보상하여 드리지 않습니다. "
            "1. 계약자, 피보험자 또는 이들의 법정대리인의 고의로 생긴 손해에 대한 배상책임 "
            "2. 전쟁, 혁명, 내란, 사변, 테러, 폭동, 소요, 노동쟁의 기타 이들과 유사한 "
            "사태로 생긴 손해에 대한 배상책임"
        )
        existing = db.query(Clause).filter(
            Clause.coverage_id == liability_coverage.coverage_id,
            Clause.text == liability_clause_2
        ).first()
        if not existing:
            clause = Clause(
                policy_version_id=pv.policy_version_id,
                coverage_id=liability_coverage.coverage_id,
                article_no='[배상책임보장 특별약관] 제2조(보상하지 않는 손해)',
                text=liability_clause_2,
                clause_type='면책',
                default_color='빨강',
                page_ref='p.102-103'
            )
            db.add(clause)
            print("Created: 배상책임 특약 제2조")

        db.commit()
        print("Successfully seeded HYUNDAI 청크 c (사망·후유장해·배상책임 특약)")

    except Exception as e:
        db.rollback()
        print(f"Error in seed_hyundai_2026_c: {e}")
        raise
    finally:
        db.close()


if __name__ == '__main__':
    run()
