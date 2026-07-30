"""
6개 보험사 공통: "여행중 휴대품손해(분실제외) 특별약관" KB 추가 시드.

원문 출처(각 보험사 원문 PDF, data/raw_pdfs/*.pdf 및 data/processed/*_full_text.txt):
- 삼성화재: 여행중 휴대품손해(분실제외) 특별약관 (p.47-50)
- 현대해상: 해외여행중 휴대품손해(분실제외)보장 특별약관 (p.84-87)
- 메리츠화재: 휴대품손해(분실제외) 특별약관 (p.103-)
- KB손해보험: 해외여행중 휴대품손해(분실제외) 특별약관 (p.44-)
- DB손해보험: 해외여행중 휴대품손해(분실제외) 특별약관 (p.77-79)
- 카카오페이손해보험: 해외여행중 휴대물품손해(분실제외/1개당 20만원 한도) 특별약관 (p.122-124)

이전에는 이 담보가 KB에 전혀 없어서(rules.py의 NOT_YET_IN_KB), "휴대폰을 잃어버렸어요"
같은 사고가 엉뚱하게 상해사망·상해의료비 담보로 잘못 연결되는 문제가 있었다. 6개 보험사
원문을 실제로 확인해보니 전부 동일한 업계 표준 특별약관 문구(200,000원/1개·1조·1쌍 한도,
자기부담금 공제)를 쓰고 있고, 공통적으로 "분실은 보상하지 않는다"는 명시적 면책 조항과
"분실"과 "도난"을 구분하는 용어풀이가 있다 — 이 구분이 실제로 매우 중요해서
(사용자가 "잃어버렸어요"라고 표현해도 실제로는 도난·강취인지, 단순 부주의로 인한 분실인지에
따라 보장 여부가 갈린다), 담보 정의 문구에도 이 구분을 그대로 살려서 넣는다.

주의: 삼성화재 PDF에는 이 특별약관과 전혀 무관한 "주택 도난위험담보 특별약관"(가정용
도난보험, p.149-151)도 같은 문서에 섞여 있어서 "관할경찰서의 도난신고확인서" 같은 문구가
검색되는데, 이건 여행자보험 휴대품손해 조항이 아니라 별개 상품이므로 이 시드에는 반영하지
않는다(문맥을 확인하지 않고 검색어만 보고 가져다 쓰면 근거 없는 결과가 된다).

메리츠화재는 "휴대폰한도 감액 추가특별약관"(선택 시 휴대폰만 100,000원으로 축소)도
있으나, 이건 플랜별 선택 특약이라 이 MVP의 단일 플랜 가정과 맞지 않아 시드하지 않고
deductible 필드에 참고용으로만 언급한다.
"""
from app.database import SessionLocal
from app.models.kb import Coverage, Clause, CoverageDocMap, Clause as ClauseModel
from app.services.kb_seed_common import get_or_create_coverage_std, get_or_create_doc_std

# (insurer_code, policy_version_id, common_claim_clause_id) — 이미 시드된 각 보험사의
# 정책버전과, 이미 존재하는 "보험금의 청구" 공통 조항(clause_type='서류') id.
# (다른 담보 시드 때 이미 만들어둔 것을 그대로 재사용 — 같은 서류 절차를 따르므로.)
_TARGETS = {
    "SAMSUNG": {"policy_version_id": 1, "claim_clause_id": 3},
    "HYUNDAI": {"policy_version_id": 2, "claim_clause_id": 12},
    "MERITZ": {"policy_version_id": 3, "claim_clause_id": 19},
    "KB": {"policy_version_id": 4, "claim_clause_id": 25},
    "DB": {"policy_version_id": 5, "claim_clause_id": 31},
    "KAKAOPAY": {"policy_version_id": 6, "claim_clause_id": 37},
}

_DEFINITION = (
    "이 보험의 목적은 피보험자가 여행 도중에 휴대하는 피보험자 소유·사용·관리의 휴대품에 "
    "한합니다(통화·유가증권·신용카드·항공권·여권, 원고·설계서·증서 등 서류, 선박·자동차, "
    "동식물, 의치·의수족·콘택트렌즈 등은 제외). 회사는 피보험자가 여행 도중에 생긴 우연한 "
    "사고로 이 휴대품에 입은 손해를 보상합니다."
)

_EXCLUSION_TEXT = (
    "회사는 다음의 사유로 생긴 손해는 보상하지 않습니다: 계약자·피보험자의 고의·중대한 과실, "
    "국가·공공기관의 압류·징발·몰수(화재·소방·피난 목적 제외), 보험목적 자체의 흠·자연소모·"
    "녹·곰팡이·변질·쥐/벌레로 인한 손해, 단순 외관상 손해(기능 지장 없음), 액체 유출, "
    "전쟁·천재지변·방사능 관련 사고, 그리고 보험의 목적의 방치 또는 분실. "
    "[용어풀이] 분실이란 피보험자 본인의 관리 부주의·실수·과실로 물건이 없어지거나 잃어버린 "
    "상태(유실·망실 포함)를 말하며, 통상의 주의의무를 기울였음에도 절취·강취당하는 도난과는 "
    "구별됩니다 — 즉 이 특약은 '분실'은 보상하지 않고, '도난'이나 '파손'만 보상 대상입니다."
)


def run():
    db = SessionLocal()
    try:
        std = get_or_create_coverage_std(
            db, "PERSONAL_EFFECTS", "휴대품 손해(분실제외)", "휴대품", False,
        )
        theft_report = get_or_create_doc_std(
            db, "THEFT_LOSS_STATEMENT", "손해명세서/사고경위서(도난·파손 경위)",
            "귀국가능",
            "현지 경찰 신고서를 받을 수 없는 경우가 많아 필수서류로 못박지 않고, 사고 경위를 "
            "직접 설명하는 서류로 대체 — 실제 요건은 보험사·현지 상황에 따라 다르므로 반드시 "
            "가입 보험사에 재확인이 필요합니다.",
        )

        insurer_names = {
            "SAMSUNG": ("삼성화재", "여행중 휴대품손해(분실제외) 특별약관"),
            "HYUNDAI": ("현대해상", "해외여행중 휴대품손해(분실제외)보장 특별약관"),
            "MERITZ": ("메리츠화재", "휴대품손해(분실제외) 특별약관"),
            "KB": ("KB손해보험", "해외여행중 휴대품손해(분실제외) 특별약관"),
            "DB": ("DB손해보험", "해외여행중 휴대품손해(분실제외) 특별약관"),
            "KAKAOPAY": ("카카오페이손해보험", "해외여행중 휴대물품손해(분실제외/1개당 20만원 한도) 특별약관"),
        }

        created = 0
        for code, info in _TARGETS.items():
            pv_id = info["policy_version_id"]
            claim_clause_id = info["claim_clause_id"]

            existing = (
                db.query(Coverage)
                .filter(Coverage.policy_version_id == pv_id, Coverage.coverage_std_id == std.coverage_std_id)
                .first()
            )
            if existing:
                print(f"이미 시드됨 ({code} 휴대품손해). 스킵합니다.")
                continue

            _, raw_name = insurer_names[code]
            deductible = "보험증권에 기재된 자기부담금 공제(가입 플랜별 상이, 약관/증권 확인 필요)"
            if code == "MERITZ":
                deductible += (
                    " — 메리츠는 '휴대폰한도 감액 추가특별약관' 선택 시 휴대폰 1개 한도가 "
                    "100,000원으로 줄어들 수 있음(선택 특약, 가입 여부 확인 필요)"
                )
            limit_amount = "보험의 목적 1개 또는 1조·1쌍당 200,000원 한도(전체 보험가입금액 한도 내)"

            cov = Coverage(
                policy_version_id=pv_id, coverage_std_id=std.coverage_std_id,
                raw_name=raw_name, definition=_DEFINITION,
                limit_amount=limit_amount, deductible=deductible,
                waiting_condition="분실(단순 부주의로 잃어버린 경우)은 보상하지 않음 — 도난·파손만 대상",
            )
            db.add(cov)
            db.flush()

            clause_def = Clause(
                policy_version_id=pv_id, coverage_id=cov.coverage_id,
                clause_type="보장정의", article_no=f"{raw_name} 제1조~제2조",
                text=_DEFINITION, page_ref=None, embedding_id=None, default_color="파랑",
            )
            clause_excl = Clause(
                policy_version_id=pv_id, coverage_id=cov.coverage_id,
                clause_type="면책", article_no=f"{raw_name} 보상하지 않는 손해",
                text=_EXCLUSION_TEXT, page_ref=None, embedding_id=None, default_color="빨강",
            )
            db.add_all([clause_def, clause_excl])
            db.flush()

            claim_clause = db.get(ClauseModel, claim_clause_id)
            doc_maps = [
                CoverageDocMap(
                    coverage_id=cov.coverage_id,
                    required_doc_std_id=get_or_create_doc_std(
                        db, "CLAIM_FORM", "보험금 청구서(회사 양식)", "귀국가능",
                        "보험사 홈페이지/앱에서 양식 다운로드 가능",
                    ).required_doc_std_id,
                    is_mandatory=True, clause_id=claim_clause.clause_id if claim_clause else None,
                ),
                CoverageDocMap(
                    coverage_id=cov.coverage_id,
                    required_doc_std_id=get_or_create_doc_std(
                        db, "ID_CARD", "신분증(청구인)", "공통",
                        "본인이 아닌 경우 인감증명서 또는 본인서명사실확인서 포함",
                    ).required_doc_std_id,
                    is_mandatory=True, clause_id=claim_clause.clause_id if claim_clause else None,
                ),
                CoverageDocMap(
                    coverage_id=cov.coverage_id,
                    required_doc_std_id=theft_report.required_doc_std_id,
                    is_mandatory=False, clause_id=clause_excl.clause_id,
                ),
            ]
            db.add_all(doc_maps)
            created += 1

        db.commit()
        print(f"휴대품손해(분실제외) 특약 시드 완료: {created}개 보험사")
    finally:
        db.close()


if __name__ == "__main__":
    run()
