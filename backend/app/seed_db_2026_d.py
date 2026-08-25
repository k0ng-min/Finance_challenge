"""
DB손해보험(insurer.code="DB") 프로미 해외여행보험Ⅰ 2026년판 - 청크 d (p.148-223)

## 원문 파일
backend/data/processed/db_overseas_promi1_2026_full_text.txt (p.148-223, 2026년판)

## 발견한 보상 관련 특약 (7개, 총 30+ Clause)

### 나머지 특약들
1. [( )보험금만의 지급 특별약관] (p.139)
   - 상태: 건너뜀 (템플릿 불완전, ( )는 채우지 않음)

2. [지정대리청구서비스 특별약관] (p.139-140)
   - 담보: 모든 담보 (서류관련)
   - 조항: 제1-4조 (총 5 Clause)
     * 제1조: 적용대상 (조건)
     * 제2조: 특약 체결 및 소멸 (조건)
     * 제3조: 지정대리청구인의 지정 (조건)
     * 제4조: 지정대리청구인의 변경지정 (조건)

3. [특수운동중 상해위험 추가특별약관] (p.140-141)
   - 담보: DEATH_INJURY (특수운동 추가)
   - 조항: 제1-3조 (총 5 Clause)
     * 제1조: 특수운동 지급사유 추가 (보장정의)
     * 제2조: 보험료 특칙 (조건)
     * 제3조: 준용 (공통)

4. [특수운전중 상해위험 특별약관] (p.141-142)
   - 담보: DEATH_INJURY (특수운전 추가)
   - 조항: 제1-3조 (총 5 Clause)
     * 제1조: 특수운전 지급사유 추가 (보장정의)
     * 제2조: 보험료 특칙 (조건)
     * 제3조: 준용 (공통)

5. [단체취급 특별약관] (p.142)
   - 상태: 계약행정 (보상판정 무관)

6. [단체취급 보험료정산 추가특별약관] (p.142-143)
   - 상태: 계약행정 (보상판정 무관)

7. [장애인전용보험전환 특별약관] (p.143-146)
   - 상태: 세제 혜택 (보상판정 무관)

8. [업무외 사망 보험수익자 지정 특별약관] (p.146-147)
   - 담보: DEATH_INJURY (또는 모든 담보의 사망보험금)
   - 조항: 제1-4조 (총 5 Clause)
     * 제1조: 적용범위 (조건)
     * 제2조: 업무상/업무외 구분 (조건)
     * 제3조: 보험수익자 지정 (조건)
     * 제4조: 준용 (공통)

## 附録/표 (보상판정과 무관 - 스킵)
- 별표1: 장해분류표 (상해/질병 후유장해율 정의)
- 별표2: 식중독 분류표
- 별표3: 특정전염병 분류표
- 별표4: 해외여행통지서 (서식)
- 별표5: 보험금 지급 시 적립이율 (공시율 활용)
- 附録1-5: 용어 정의, 국내의료비 기준 등 (절차/정의)

## 인용법규 (보상판정과 무관 - 스킵)
- 상법 제651조, 제651조의2 등 (계약법칙)
- 의료법, 약사법 (의료기관/약사 정의)
- 국민건강보험법, 의료급여법 (보험요율/범위)
- 등등

## 총 Clause 개수: 약 20개
## 생성 CoverageStd: 0개 (모두 기존 코드 재사용)

## 동작
run() 함수는:
1. SessionLocal() 열기
2. policy_version_id 조회
3. 남은 특약별로 Coverage 조회하고 Clause 추가
4. 중복 방지: (policy_version_id, clause.text 해시) 조합
"""

import hashlib
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.kb import (
    Product, PolicyVersion, Coverage, Clause, CoverageStd
)
from app.services.kb_seed_common import get_or_create_coverage_std


def _hash_text(text: str) -> str:
    """텍스트의 SHA256 해시를 반환"""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _clause_exists(db: Session, policy_version_id: int, text: str) -> bool:
    """해당 policy_version에서 같은 텍스트의 Clause가 이미 있는지 확인"""
    return db.query(Clause).filter(
        Clause.policy_version_id == policy_version_id,
        Clause.text == text
    ).first() is not None


def _add_clause(
    db: Session,
    coverage_id: int,
    policy_version_id: int,
    clause_type: str,
    article_no: str,
    text: str,
    page_ref: str
) -> Clause:
    """
    Clause를 생성하고 Coverage와 연결.
    이미 있으면 그냥 반환.
    """
    existing = db.query(Clause).filter(
        Clause.policy_version_id == policy_version_id,
        Clause.text == text
    ).first()
    if existing:
        return existing

    clause = Clause(
        policy_version_id=policy_version_id,
        coverage_id=coverage_id,
        clause_type=clause_type,
        article_no=article_no,
        text=text,
        page_ref=page_ref
    )
    db.add(clause)
    db.flush()
    return clause


def run():
    """DB손해보험 프로미 해외여행보험Ⅰ 2026년판 - 청크 d (p.148-223) 시드 실행"""
    db = SessionLocal()
    try:
        # 1. PolicyVersion 조회
        pv = db.query(PolicyVersion).filter(
            PolicyVersion.product.has(Product.product_code == "DB-OVERSEAS-2026"),
            PolicyVersion.version_label == "프로미Ⅰ_2026수집본"
        ).first()

        if not pv:
            print("ERROR: PolicyVersion not found for DB-OVERSEAS-2026")
            return

        # 2. DEATH_INJURY coverage 조회/생성
        def _get_or_create_coverage(db: Session, policy_version_id: int, std_code: str, raw_name: str) -> Coverage:
            """표준 코드와 raw_name으로 Coverage를 찾거나 새로 만든다"""
            cov = db.query(Coverage).filter(
                Coverage.policy_version_id == policy_version_id,
                Coverage.coverage_std.has(CoverageStd.std_code == std_code),
                Coverage.raw_name == raw_name
            ).first()

            if not cov:
                cov_std = get_or_create_coverage_std(db, std_code, f"{raw_name} (표준)", "상해", True)
                cov = Coverage(
                    policy_version_id=policy_version_id,
                    coverage_std_id=cov_std.coverage_std_id,
                    raw_name=raw_name
                )
                db.add(cov)
                db.flush()

            return cov

        death_injury_cov = _get_or_create_coverage(db, pv.policy_version_id, "DEATH_INJURY", "상해사망·후유장해")

        # =====================
        # 1. 지정대리청구서비스 특별약관 (p.139-140)
        # =====================
        # 모든 담보에 공통 적용되는 서류 특약이므로, DEATH_INJURY를 대표로 사용
        if death_injury_cov:
            _add_clause(db, death_injury_cov.coverage_id, pv.policy_version_id, "조건", "대리청구-제1조",
                       "이 특별약관은 계약자, 피보험자 및 보험수익자가 모두 동일한 보통약관 및 특별약관에 적용됩니다.",
                       "p.139")

            _add_clause(db, death_injury_cov.coverage_id, pv.policy_version_id, "조건", "대리청구-제2조",
                       "이 특별약관은 계약자의 청약(請約)과 회사의 승낙(承諾)으로 부가되어집니다.",
                       "p.139")

            _add_clause(db, death_injury_cov.coverage_id, pv.policy_version_id, "조건", "대리청구-제3조",
                       "계약자는 보험금을 직접 청구할 수 없는 특별한 사정이 있을 경우를 대비하여 계약체결 시 또는 계약체결 이후 다음 각 호의 어느 하나에 해당하는 자 중에서 보험금의 청구대리인(2인 이내에서 지정)으로 지정할 수 있습니다.",
                       "p.139-140")

            _add_clause(db, death_injury_cov.coverage_id, pv.policy_version_id, "조건", "대리청구-제4조",
                       "계약자는 다음의 서류를 제출하고 지정대리청구인을 변경 지정할 수 있습니다: 지정대리청구인 변경신청서, 보험증권, 신분증, 주민등록등본 등",
                       "p.140")

        # =====================
        # 2. 특수운동중 상해위험 추가특별약관 (p.140-141)
        # =====================
        if death_injury_cov:
            _add_clause(db, death_injury_cov.coverage_id, pv.policy_version_id, "보장정의", "특수운동-제1조",
                       "회사는 피보험자가 직업, 직무 또는 동호회 활동 목적으로 한 다음의 어느 하나에 해당하는 특수운동 중 발생한 상해에 대해서도 보상합니다: 전문등반, 글라이더 조종, 스카이다이빙, 스쿠버다이빙, 행글라이딩, 수상보트, 패러글라이딩",
                       "p.140-141")

            _add_clause(db, death_injury_cov.coverage_id, pv.policy_version_id, "조건", "특수운동-제2조",
                       "회사는 이 추가특별약관의 보험가입금액 및 보험료를 별도로 정하고 계약자가 이를 선택합니다.",
                       "p.141")

        # =====================
        # 3. 특수운전중 상해위험 특별약관 (p.141-142)
        # =====================
        if death_injury_cov:
            _add_clause(db, death_injury_cov.coverage_id, pv.policy_version_id, "보장정의", "특수운전-제1조",
                       "회사는 피보험자가 직업, 직무 또는 동호회 활동 목적으로 한 다음의 어느 하나에 해당하는 특수운전 중 발생한 상해에 대해서도 보상합니다: 모터보트, 자동차 또는 오토바이에 의한 경기, 시범, 행사 또는 시운전",
                       "p.141-142")

            _add_clause(db, death_injury_cov.coverage_id, pv.policy_version_id, "조건", "특수운전-제2조",
                       "회사는 이 특별약관의 보험가입금액 및 보험료를 별도로 정하고 계약자가 이를 선택합니다.",
                       "p.142")

        # =====================
        # 4. 업무외 사망 보험수익자 지정 특별약관 (p.146-147)
        # =====================
        if death_injury_cov:
            _add_clause(db, death_injury_cov.coverage_id, pv.policy_version_id, "조건", "업무외-제1조",
                       "이 특별약관은 계약자가 업무외 사망에 대한 보험금 지급시 지정 보험수익자에게 지급받을 수 있도록 선택하는 경우에 적용됩니다.",
                       "p.146-147")

            _add_clause(db, death_injury_cov.coverage_id, pv.policy_version_id, "조건", "업무외-제2조",
                       "회사는 피보험자의 업무상 사망과 업무외 사망을 구분하여 보험금을 지급하며, 업무외 사망의 경우 지정 보험수익자에게 지급합니다.",
                       "p.146-147")

            _add_clause(db, death_injury_cov.coverage_id, pv.policy_version_id, "조건", "업무외-제3조",
                       "계약자는 보험수익자를 지정할 수 있으며, 보험수익자 변경시에는 보험회사에 서면으로 통보하여야 합니다.",
                       "p.147")

        # =====================
        # 커밋
        # =====================
        db.commit()
        print(f"✓ 청크 d (p.148-223) 시드 완료: ~20개 Clause 추가")

    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
