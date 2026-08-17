"""약관 전체 텍스트에서 보통약관·특별약관 제목과 시작 페이지를 뽑는다.

정독 청크를 나눌 때 쓴다. 제목처럼 보이지만 본문 인용인 줄(조사로 시작하거나 문장이
중간에서 끊긴 줄)은 걸러낸다 - 오탐을 청크 경계로 쓰면 담당 범위가 어긋난다.

Run from ``backend``::

    python -m scripts.map_terms_structure
    python -m scripts.map_terms_structure --insurer DB
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = BACKEND_DIR / "data" / "raw_pdfs" / "source_files.json"
DEFAULT_PROCESSED = BACKEND_DIR / "data" / "processed"

# 줄 전체가 제목인 경우만 잡는다.
_TITLE = re.compile(
    r"^\s*(?:\[\s*)?([가-힣][가-힣A-Za-z0-9·()\[\]/,\.\-Ⅰ-Ⅹ ]{3,44}"
    r"(?:추가특별약관|특별약관|보통약관))(?:\s*\])?\s*$",
    re.M,
)
# 제목 앞에 붙으면 본문 인용인 신호(조사·접속사로 시작하거나 지시어가 들어간 경우).
_REFERENCE_HINT = re.compile(r"^(?:이|그|해당|동|위|같은|또는|및|을|를|은|는|에|의)\s")


def headings(text: str) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for chunk in text.split("===PAGE ")[1:]:
        number, _, body = chunk.partition("===\n")
        try:
            page = int(number.strip())
        except ValueError:
            continue
        for match in _TITLE.finditer(body):
            title = match.group(1).strip()
            if _REFERENCE_HINT.match(title):
                continue
            if title.endswith(("이 특별약관", "이 추가특별약관", "해당 특별약관")):
                continue
            found.append((page, title))
    return found


def run(insurer: str | None = None, catalog_path: Path = DEFAULT_CATALOG,
        processed_dir: Path = DEFAULT_PROCESSED) -> dict[str, list[dict]]:
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    report: dict[str, list[dict]] = {}
    for code, entries in catalog.items():
        if insurer and code != insurer:
            continue
        rows = []
        for entry in entries:
            text = (processed_dir / entry["text"]).read_text(encoding="utf-8")
            first_seen: dict[str, int] = {}
            for page, title in headings(text):
                first_seen.setdefault(title, page)
            rows.append({"pdf": entry["pdf"], "prefix": entry["page_ref_prefix"],
                         "pages": entry["pages"],
                         "headings": [{"page": page, "title": title}
                                      for title, page in sorted(first_seen.items(), key=lambda kv: kv[1])]})
        report[code] = rows
        for row in rows:
            print(f"=== {code} {row['pdf']} ({row['pages']} pages)")
            for heading in row["headings"]:
                print(f"   p.{heading['page']:>4}  {heading['title']}")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--insurer")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--processed", type=Path, default=DEFAULT_PROCESSED)
    args = parser.parse_args(argv)
    run(args.insurer, args.catalog, args.processed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
