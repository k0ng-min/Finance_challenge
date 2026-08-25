"""모든 Clause.text가 원본 PDF 추출본에 문자 그대로 존재하는지 검사한다.

2026-08-18에 원본 약관이 교체되면서, 기존 조항 363개 중 새 판본에 원문 그대로 남은
것이 130개(36%)뿐이라는 사실을 뒤늦게 발견했다. 조항 원문이 근거의 뿌리이고
ClauseTerm.raw_text 같은 파생물이 전부 그 부분 문자열이어야 하므로, 원문 드리프트는
데이터 전체를 무효로 만든다. 이 검사를 상시로 돌려 다음 교체를 즉시 잡는다.

Run from ``backend``::

    python -m scripts.verify_clause_grounding
    python -m scripts.verify_clause_grounding --json
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = BACKEND_DIR / "data" / "app.db"
DEFAULT_CATALOG = BACKEND_DIR / "data" / "raw_pdfs" / "source_files.json"
DEFAULT_PROCESSED = BACKEND_DIR / "data" / "processed"

_PAGE_MARKER = re.compile(r"===PAGE \d+===")
_WHITESPACE = re.compile(r"\s+")


def normalize(text: str) -> str:
    """대조용 정규화: 페이지 마커를 지우고 모든 공백을 제거한다.

    pdfplumber는 같은 문장을 조판 폭에 따라 다른 위치에서 줄바꿈한다. 조항을 옮겨
    담을 때 줄바꿈이 공백 하나로 바뀌는 일이 흔하므로, 공백은 대조 대상에서 뺀다.
    글자 자체가 다르면 잡힌다.
    """
    return _WHITESPACE.sub("", _PAGE_MARKER.sub(" ", text or ""))


def load_haystacks(catalog_path: Path, processed_dir: Path) -> dict[str, str]:
    """보험사 코드 -> 그 보험사 원본 파일 전체를 이어붙인 정규화 텍스트."""
    catalog = json.loads(Path(catalog_path).read_text(encoding="utf-8"))
    haystacks: dict[str, str] = {}
    for insurer, entries in catalog.items():
        chunks = []
        for entry in entries:
            text_path = Path(processed_dir) / entry["text"]
            if not text_path.exists():
                raise FileNotFoundError(
                    f"extracted text is missing: {text_path}. Run scripts.extract_raw_pdf_text first."
                )
            chunks.append(text_path.read_text(encoding="utf-8"))
        haystacks[insurer] = normalize("\n".join(chunks))
    return haystacks


def check(
    db_path: Path = DEFAULT_DATABASE,
    catalog_path: Path = DEFAULT_CATALOG,
    processed_dir: Path = DEFAULT_PROCESSED,
) -> list[dict]:
    """원본에 없는 조항 목록을 돌려준다. 빈 리스트면 100% 일치."""
    haystacks = load_haystacks(catalog_path, processed_dir)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            """SELECT i.code AS insurer, c.clause_id, c.article_no, c.page_ref, c.text
                 FROM clause c
                 JOIN policy_version pv USING(policy_version_id)
                 JOIN product p USING(product_id)
                 JOIN insurer i USING(insurer_id)
                ORDER BY i.code, c.clause_id"""
        ).fetchall()
    finally:
        connection.close()

    failures = []
    for row in rows:
        haystack = haystacks.get(row["insurer"])
        if haystack is None:
            failures.append(
                {
                    "insurer": row["insurer"],
                    "clause_id": row["clause_id"],
                    "article_no": row["article_no"],
                    "page_ref": row["page_ref"],
                    "reason": "원본 파일 목록에 이 보험사가 없다",
                }
            )
            continue
        if normalize(row["text"]) not in haystack:
            failures.append(
                {
                    "insurer": row["insurer"],
                    "clause_id": row["clause_id"],
                    "article_no": row["article_no"],
                    "page_ref": row["page_ref"],
                    "reason": "원본 추출본에 이 문구가 없다",
                    "head": (row["text"] or "")[:80],
                }
            )
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--processed", type=Path, default=DEFAULT_PROCESSED)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)

    failures = check(args.database, args.catalog, args.processed)
    if args.as_json:
        print(json.dumps(failures, ensure_ascii=False, indent=2))
    elif failures:
        print(f"grounding FAIL: {len(failures)}건이 원본과 어긋난다")
        for failure in failures:
            print(f"  [{failure['insurer']}] clause_id={failure['clause_id']} "
                  f"{failure['article_no']} ({failure.get('page_ref')}) - {failure['reason']}")
            if failure.get("head"):
                print(f"      {failure['head']}")
    else:
        print("grounding OK: 모든 조항이 원본 추출본에 존재한다")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
