"""2026년 약관으로 갈아엎기 전에 구 KB와 개발용 사용자 데이터를 지운다.

되돌릴 수 없다. 구 원본 PDF는 저장소에 없고(.gitignore) 디스크에도 남아 있지 않아
구 조항을 다시 만들 방법이 없다. 그래서 --confirm 없이는 세는 것만 하고 끝낸다.

계정(app_user)도 함께 지운다 - 개발 중 쌓인 테스트 계정이라 남길 이유가 없다는
사용자 지시에 따른 것이다.

남기는 것은 약관과 무관한 사전·외부 자료다(coverage_std, incident_type,
required_doc_std, standard_clause, 보험료·여행경보·부지급률·지연통계 등).
insurer 6행도 남긴다 - 회사 자체는 바뀌지 않았다.

Run from ``backend``::

    python -m app.reset_kb            # 삭제 대상 행 수만 출력
    python -m app.reset_kb --confirm  # 실제 삭제
"""
from __future__ import annotations

import argparse
import sys

from sqlalchemy import text

from app.database import SessionLocal

# 외래키 역순: 자식 -> 부모. 순서를 바꾸면 SQLite가 참조 오류를 낸다.
DELETE_ORDER: tuple[str, ...] = (
    # 분석 결과와 근거 링크
    "finding_evidence_link",
    "analysis_finding",
    "validation_result",
    "user_question_log",
    "eval_log",
    "evidence",
    "analysis_run",
    # 사용자 여행·사고·보유 계약
    "incident",
    "trip",
    "user_coverage",
    "user_policy",
    "external_coverage",
    "external_policy",
    "app_user",
    # 조항 파생
    "clause_standard_map",
    "overlap_rule",
    "doc_requirement",
    "coverage_doc_map",
    "clause_term",
    "clause_incident_map",
    # 조항과 담보, 상품
    "clause",
    "coverage",
    "policy_version",
    "product",
)

KEEP_TABLES: frozenset[str] = frozenset(
    {
        "insurer",
        "coverage_std",
        "incident_type",
        "required_doc_std",
        "standard_clause",
        "insurer_premium",
        "travel_alert",
        "nonpayment_rate",
        "flight_delay_stat",
        "country_language",
        "onsite_phrase_i18n",
        "question_bank",
        "simulation_scenario",
        "validation_rule",
    }
)


def counts(db) -> dict[str, int]:
    result = {}
    for table in DELETE_ORDER:
        result[table] = db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar() or 0
    return result


def run(confirm: bool = False) -> dict[str, int]:
    db = SessionLocal()
    try:
        before = counts(db)
        total = sum(before.values())
        for table, rows in before.items():
            if rows:
                print(f"  {table}: {rows}")
        print(f"삭제 대상 합계: {total}행")
        if not confirm:
            print("--confirm 없이 실행했으므로 아무것도 지우지 않았다.")
            return before
        for table in DELETE_ORDER:
            db.execute(text(f"DELETE FROM {table}"))
        db.commit()
        after = counts(db)
        remaining = sum(after.values())
        print(f"삭제 완료. 남은 행: {remaining}")
        if remaining:
            raise RuntimeError(f"삭제되지 않은 행이 있다: { {k: v for k, v in after.items() if v} }")
        return before
    finally:
        db.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm", action="store_true", help="실제로 삭제한다")
    args = parser.parse_args(argv)
    run(confirm=args.confirm)
    return 0


if __name__ == "__main__":
    sys.exit(main())
