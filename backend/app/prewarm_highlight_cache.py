"""보험형광펜(조항 색상 하이라이트) Gemini 캐시를 배포 전에 미리 채운다.

Clause.highlight_spans는 최초로 그 조항을 누가 열어볼 때 Gemini를 호출해서
채워지는 지연 캐시다(clause_spans_gemini.get_highlight_spans). 그래서 배포
직후에는 사용자가 실제로 열어본 조항만 캐시가 있고(2026-08-19 점검 시점
363개 중 6개), 나머지는 처음 여는 사용자가 Gemini 응답을 기다려야 하고
그 요청이 실패하면 단색 폴백으로 보인다. 배포 전에 이 스크립트로 전부
미리 채워두면 사용자는 항상 캐시만 읽는다.

GEMINI_API_KEY가 없거나(.env) 무효하면 각 조항이 예외 로그만 남기고
None을 반환한다(clause_spans_gemini.get_highlight_spans의 폴백 규칙) —
이 스크립트는 그 실패를 개수로 세어 보여주고, API 키 문제인지 조항
자체 문제인지 사람이 구분할 수 있게 첫 실패의 로그를 그대로 보여준다.

Run from ``backend``::

    python -m app.prewarm_highlight_cache            # 대상 개수만 확인
    python -m app.prewarm_highlight_cache --confirm   # 실제로 채운다
"""
from __future__ import annotations

import argparse
import logging
import sys
import time

from app.database import SessionLocal
from app.models.kb import Clause
from app.services.clause_spans_gemini import get_highlight_spans

logger = logging.getLogger(__name__)

# 무료 등급 기준 분당 요청 한도를 넘지 않도록 호출 사이에 잠깐 쉰다.
REQUEST_INTERVAL_SEC = 2.0


def run(confirm: bool = False) -> dict[str, int]:
    db = SessionLocal()
    try:
        total = db.query(Clause).count()
        missing = db.query(Clause).filter(Clause.highlight_spans.is_(None)).all()
        print(f"전체 조항 {total}개 중 캐시 없음: {len(missing)}개")
        if not confirm:
            print("--confirm 없이 실행했으므로 아무것도 호출하지 않았다.")
            return {"total": total, "missing": len(missing), "filled": 0, "failed": 0}

        filled = 0
        failed = 0
        for i, clause in enumerate(missing, start=1):
            spans = get_highlight_spans(db, clause)
            if spans is not None:
                filled += 1
            else:
                failed += 1
                if failed == 1:
                    print(f"  clause {clause.clause_id}: 첫 실패 — 위 로그(logger.exception)를 확인하세요.")
            print(f"  [{i}/{len(missing)}] clause {clause.clause_id}: {'OK' if spans is not None else 'FAIL'}")
            if i < len(missing):
                time.sleep(REQUEST_INTERVAL_SEC)

        print(f"완료. 새로 채움: {filled}, 실패: {failed}")
        return {"total": total, "missing": len(missing), "filled": filled, "failed": failed}
    finally:
        db.close()


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.WARNING)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm", action="store_true", help="실제로 Gemini를 호출해 캐시를 채운다")
    args = parser.parse_args(argv)
    result = run(confirm=args.confirm)
    return 1 if args.confirm and result["failed"] == result["missing"] and result["missing"] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
