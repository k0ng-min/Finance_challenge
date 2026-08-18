"""배포 전 게스트 사용자 데이터만 지운다(약관 KB는 건드리지 않는다).

reset_kb.py와 다른 점: reset_kb.py는 약관 KB까지 통째로 지우는 재구축용 스크립트다.
이 스크립트는 그 절반만 한다 — 개발·QA 중 쌓인 게스트 계정·여행·사고·분석 기록만
지우고 조항·담보·사고유형 매핑 등 약관 데이터는 그대로 둔다. 커밋되는 backend/data/app.db에
남의 테스트 흔적(사용자 730명 등)이 그대로 보이는 문제(2026-08-19 지적)를 배포 전에
반복적으로 해소하기 위한 것이다.

Run from ``backend``::

    python -m app.reset_guest_data            # 삭제 대상 행 수만 출력
    python -m app.reset_guest_data --confirm   # 실제 삭제
"""
from __future__ import annotations

import argparse
import sys

from sqlalchemy import text

from app.database import SessionLocal

# 외래키 역순: 자식 -> 부모.
DELETE_ORDER: tuple[str, ...] = (
    "finding_evidence_link",
    "analysis_finding",
    "validation_result",
    "user_question_log",
    "eval_log",
    "evidence",
    "analysis_run",
    "incident",
    "trip",
    "user_coverage",
    "user_policy",
    "external_coverage",
    "external_policy",
    "app_user",
)


def counts(db) -> dict[str, int]:
    return {table: db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar() or 0 for table in DELETE_ORDER}


def run(confirm: bool = False) -> dict[str, int]:
    db = SessionLocal()
    try:
        before = counts(db)
        total = sum(before.values())
        for table, rows in before.items():
            if rows:
                print(f"  {table}: {rows}")
        print(f"삭제 대상 합계: {total}행 (약관 KB는 건드리지 않음)")
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
