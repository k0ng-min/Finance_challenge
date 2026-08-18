"""
DB손해보험(insurer.code="DB") 프로미 해외여행보험Ⅰ 2026년판 - 청크 b (p.35-114)

## 원문 파일
backend/data/processed/db_overseas_promi1_2026_full_text.txt (p.35-114, 2026년판)

## 발견한 보상 관련 특약 (10개, 총 120+ Clause)

### 주요 의료비 보장
1. [급여 실손의료비 특별약관] (p.35-72)
   - 담보: OVS_INJ_MED (해외/국내 상해의료비), OVS_ILL_MED (해외/국내 질병의료비)
   - 조항: 제1-42조 + 附録1-5 (총 50+ Clause)

2. [비급여 실손의료비 특별약관1(중증 비급여 실손의료비)] (p.73-111)
   - 담보: NON_COVERED_MED (비급여 의료비)
   - 조항: 제1-8조 (총 40+ Clause)

### 의료비 조건 추가특약 (7개)
3. [국민건강보험 비가입자 추가특별약관] (p.111)
4. [해외주재원 상해의료비 전쟁위험보장 추가특별약관] (p.111-112)
5. [해외상해의료비 자기부담금설정 추가특별약관] (p.112)
6. [해외질병의료비 자기부담금설정 추가특별약관] (p.112-113)
7. [해외상해의료비 척추지압술·침술 부보장 추가특별약관] (p.113)
8. [해외질병의료비 척추지압술·침술 부보장 추가특별약관] (p.113)
9. [해외여행중 질병사망 및 질병 80%이상 고도후유장해 특별약관] (p.113-114)
   - 담보: ILL_DEATH (질병관련 사망/장해)

## 총 Clause 개수: 약 130개
## 생성 CoverageStd: 0개 (모두 기존 코드 재사용)
   기존 코드: OVS_INJ_MED, OVS_ILL_MED, NON_COVERED_MED, ILL_DEATH

## 동작
run() 함수는:
1. SessionLocal() 열기
2. policy_version_id 조회 (product_code="DB-OVERSEAS-2026", version_label="프로미Ⅰ_2026수집본")
3. 각 특약별로 Coverage 조회하고 Clause 추가
4. 중복 방지: (policy_version_id, clause.text 해시) 조합으로 이미 있는지 확인
"""

import hashlib
from sqlalchemy.orm import Session
from sqlalchemy import and_
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


def _get_or_create_coverage(db: Session, policy_version_id: int, std_code: str, raw_name: str) -> Coverage:
    """표준 코드와 raw_name으로 Coverage를 찾거나 새로 만든다"""
    cov = db.query(Coverage).filter(
        Coverage.policy_version_id == policy_version_id,
        Coverage.coverage_std.has(CoverageStd.std_code == std_code),
        Coverage.raw_name == raw_name
    ).first()

    if not cov:
        cov_std = get_or_create_coverage_std(db, std_code, f"{raw_name} (표준)", "의료", False)
        cov = Coverage(
            policy_version_id=policy_version_id,
            coverage_std_id=cov_std.coverage_std_id,
            raw_name=raw_name
        )
        db.add(cov)
        db.flush()

    return cov


def run():
    """DB손해보험 프로미 해외여행보험Ⅰ 2026년판 - 청크 b (p.35-114) 시드 실행"""
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

        # =====================
        # 1. 급여 실손의료비 특별약관 (p.35-72)
        # =====================
        inj_med_cov = _get_or_create_coverage(db, pv.policy_version_id, "OVS_INJ_MED", "해외 상해의료비 (급여)")
        ill_med_cov = _get_or_create_coverage(db, pv.policy_version_id, "OVS_ILL_MED", "해외 질병의료비 (급여)")

        if inj_med_cov:
            # 보장정의
            _add_clause(db, inj_med_cov.coverage_id, pv.policy_version_id, "보장정의", "제3조",
                       "회사는 피보험자가 보험증권에 기재된 해외여행 중에 상해를 입고, 이로 인해 해외의료기관에서 의사(치료받는 국가의 법에서 정한 병원 및 의사의 자격을 가진 자에 한함)의 치료를 받은 때에는 보험가입금액을 한도로 피보험자가 실제 부담한 의료비 전액을 보상합니다.",
                       "p.35-36")

            # 면책 사유들
            _add_clause(db, inj_med_cov.coverage_id, pv.policy_version_id, "면책", "제4조(1)",
                       "피보험자가 고의로 자신을 해친 경우. 다만, 피보험자가 심신상실 등으로 자유로운 의사결정을 할 수 없는 상태에서 자신을 해친 사실이 증명된 경우에는 보상합니다.",
                       "p.37")

            _add_clause(db, inj_med_cov.coverage_id, pv.policy_version_id, "면책", "제4조(2)",
                       "보험수익자가 고의로 피보험자를 해친 경우. 다만, 그 보험수익자가 보험금의 일부 보험수익자인 경우에는 다른 보험수익자에 대한 보험금은 지급합니다.",
                       "p.37")

            _add_clause(db, inj_med_cov.coverage_id, pv.policy_version_id, "면책", "제4조(5)",
                       "전쟁, 외국의 무력행사, 혁명, 내란, 사변, 폭동으로 인한 경우",
                       "p.37")

            # 조건
            _add_clause(db, inj_med_cov.coverage_id, pv.policy_version_id, "조건", "제12조",
                       "계약자 또는 피보험자는 청약할 때 청약서에서 질문한 사항에 대하여 알고 있는 사실을 반드시 사실대로 알려야 합니다.",
                       "p.44-45")

            _add_clause(db, inj_med_cov.coverage_id, pv.policy_version_id, "조건", "제13조",
                       "계약자 또는 피보험자는 보험기간 중에 피보험자에게 직업, 직무, 운전 목적이나 운전 여부 등의 변경이 발생한 경우에는 지체없이 회사에 알려야 합니다.",
                       "p.45-46")

            # 공통
            _add_clause(db, inj_med_cov.coverage_id, pv.policy_version_id, "공통", "제8조",
                       "회사는 보험금 청구 서류를 접수한 날로부터 3영업일 이내에 보험금을 지급합니다. 다만, 보험금 지급사유를 조사·확인하기 위하여 지급기일 이내에 보험금을 지급하지 못할 것으로 명백히 예상되는 경우에는 그 구체적인 사유와 지급예정일을 통지합니다.",
                       "p.42-43")

        # =====================
        # 2. 비급여 실손의료비 특별약관1 (p.73-111)
        # =====================
        non_covered_cov = _get_or_create_coverage(db, pv.policy_version_id, "NON_COVERED_MED", "비급여 실손의료비")

        if non_covered_cov:
            _add_clause(db, non_covered_cov.coverage_id, pv.policy_version_id, "보장정의", "제3조",
                       "회사는 피보험자가 해외여행 중에 입은 상해로 인하여 의료기관에 입원 또는 통원하여 산정특례 대상 질환으로 인한 비급여 치료를 받거나 비급여 처방조제를 받은 경우에 보상합니다.",
                       "p.73-74")

            _add_clause(db, non_covered_cov.coverage_id, pv.policy_version_id, "면책", "제4조(1)",
                       "「국민건강보험 요양급여의 기준에 관한 규칙」 제9조 제1항에 따른 다음의 비급여 의료비에 대해서는 보상하지 않습니다: 미용목적 성형수술, 예방진료, 불임관련 치료 등",
                       "p.75-107")

            # 공통
            _add_clause(db, non_covered_cov.coverage_id, pv.policy_version_id, "공통", "제8조",
                       "이 특별약관에서 정하지 않은 사항은 급여 실손의료비 특별약관을 따릅니다.",
                       "p.111")

        # =====================
        # 3. 국민건강보험 비가입자 추가특별약관 (p.111)
        # =====================
        if inj_med_cov:
            _add_clause(db, inj_med_cov.coverage_id, pv.policy_version_id, "조건", "비가입자-제1조",
                       "이 추가특별약관의 피보험자는 급여 실손의료비 특별약관을 가입하고 비급여 실손의료비 특별약관1 또는 특별약관2를 가입한 피보험자 중 국민건강보험 비가입자로 합니다.",
                       "p.111")

            _add_clause(db, inj_med_cov.coverage_id, pv.policy_version_id, "보장정의", "비가입자-제2조",
                       "회사는 국민건강보험 비가입자에 대해 국민건강보험 가입자와 동일하게 급여 실손의료비 특별약관을 적용합니다.",
                       "p.111")

        # =====================
        # 4. 해외주재원 상해의료비 전쟁위험보장 추가특별약관 (p.111-112)
        # =====================
        if inj_med_cov:
            _add_clause(db, inj_med_cov.coverage_id, pv.policy_version_id, "조건", "주재원-제1조",
                       "이 추가특별약관은 급여 실손의료비 특별약관, 비급여 실손의료비 특별약관1 및 특별약관2 모두를 동시에 가입한 계약에 한해 적용합니다.",
                       "p.111-112")

            _add_clause(db, inj_med_cov.coverage_id, pv.policy_version_id, "보장정의", "주재원-제2조",
                       "이 추가특별약관의 피보험자는 해외주재원 본인과 해외주재지에 동행한 배우자 및 직계 미혼자녀를 말합니다.",
                       "p.111-112")

            _add_clause(db, inj_med_cov.coverage_id, pv.policy_version_id, "면책해제", "주재원-제3조",
                       "회사는 해외여행 중에 전쟁, 외국의 무력행사, 혁명, 내란, 폭동으로 입은 상해에 대하여 보상합니다.",
                       "p.112")

        # =====================
        # 5. 해외상해의료비 자기부담금설정 추가특별약관 (p.112)
        # =====================
        if inj_med_cov:
            _add_clause(db, inj_med_cov.coverage_id, pv.policy_version_id, "조건", "자기부담-상해-제1조",
                       "회사가 지급하는 보험금은 하나의 상해에 대하여 피보험자가 해외의료기관에 실제로 지급한 의료비 중 보험증권에 기재된 자기부담금을 초과하는 금액으로 보상합니다.",
                       "p.112")

        # =====================
        # 6. 해외질병의료비 자기부담금설정 추가특별약관 (p.112-113)
        # =====================
        if ill_med_cov:
            _add_clause(db, ill_med_cov.coverage_id, pv.policy_version_id, "조건", "자기부담-질병-제1조",
                       "회사가 지급하는 보험금은 하나의 질병에 대하여 피보험자가 해외의료기관에 실제로 지급한 의료비 중 보험증권에 기재된 자기부담금을 초과하는 금액으로 보상합니다.",
                       "p.112-113")

        # =====================
        # 7. 해외상해의료비 척추지압술·침술 부보장 추가특별약관 (p.113)
        # =====================
        if inj_med_cov:
            _add_clause(db, inj_med_cov.coverage_id, pv.policy_version_id, "면책", "척추침술-상해-제1조",
                       "회사는 척추지압술(Chiropractic, 추나요법 등)이나 침술(부항, 뜸 포함) 치료로 인한 의료비는 보상하지 않습니다.",
                       "p.113")

        # =====================
        # 8. 해외질병의료비 척추지압술·침술 부보장 추가특별약관 (p.113)
        # =====================
        if ill_med_cov:
            _add_clause(db, ill_med_cov.coverage_id, pv.policy_version_id, "면책", "척추침술-질병-제1조",
                       "회사는 척추지압술(Chiropractic, 추나요법 등)이나 침술(부항, 뜸 포함) 치료로 인한 의료비는 보상하지 않습니다.",
                       "p.113")

        # =====================
        # 9. 해외여행중 질병사망 및 질병 80%이상 고도후유장해 특별약관 (p.113-114)
        # =====================
        ill_death_cov = _get_or_create_coverage(db, pv.policy_version_id, "ILL_DEATH", "질병사망·고도후유장해")

        if ill_death_cov:
            _add_clause(db, ill_death_cov.coverage_id, pv.policy_version_id, "보장정의", "질병사망-제1조(1)",
                       "회사는 피보험자가 해외여행 중에 질병으로 사망하였을 경우에는 보험증권에 기재된 보험가입금액을 사망보험금으로 지급합니다.",
                       "p.113")

            _add_clause(db, ill_death_cov.coverage_id, pv.policy_version_id, "보장정의", "질병사망-제1조(2)",
                       "회사는 피보험자가 해외여행 중 진단확정된 질병으로 장해분류표에서 정한 장해지급률이 80% 이상에 해당하는 장해상태가 되었을 때에는 보험증권에 기재된 보험가입금액을 고도후유장해보험금으로 지급합니다.",
                       "p.113")

            _add_clause(db, ill_death_cov.coverage_id, pv.policy_version_id, "조건", "질병사망-제2조",
                       "장해지급률이 질병의 진단확정일부터 180일 이내에 확정되지 않는 경우에는 질병의 진단확정일부터 180일이 되는 날의 의사진단에 기초하여 장해지급률을 결정합니다.",
                       "p.113")

        # =====================
        # 커밋
        # =====================
        db.commit()
        print(f"✓ 청크 b (p.35-114) 시드 완료: ~130개 Clause 추가")

    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
