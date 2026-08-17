"""원본 약관 PDF의 전체 텍스트를 data/processed/에 캐시한다.

정독 작업은 pdfplumber로 매번 PDF를 여는 대신 이 캐시를 읽는다(같은 파일을 수십 번
여는 비용을 줄이고, Clause.text가 어느 추출본에서 나왔는지 고정한다).
scripts/verify_clause_grounding.py가 같은 캐시로 대조하므로, 캐시를 다시 만들면
검증 기준도 함께 갱신된다.

Run from ``backend``::

    python -m scripts.extract_raw_pdf_text
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pdfplumber

BACKEND_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BACKEND_DIR / "data" / "raw_pdfs"
OUT_DIR = BACKEND_DIR / "data" / "processed"
CATALOG = RAW_DIR / "source_files.json"

# 보험사 코드 -> (page_ref 접두사, 파일명). 접두사가 None이면 page_ref에 접두사를 쓰지 않는다.
FILES: dict[str, list[tuple[str | None, str]]] = {
    "SAMSUNG": [(None, "samsung_overseas_2026.pdf")],
    "HYUNDAI": [(None, "hyundai_overseas_8403-0000-20260606.pdf")],
    "MERITZ": [(None, "meritz_overseas_2607A.pdf")],
    "KB": [(None, "kb_overseas_26-15505-1.pdf")],
    "DB": [(None, "db_overseas_promi1_2026.pdf")],
    "KAKAOPAY": [
        ("K1", "kakaopay_overseas_2026-0199_together1.pdf"),
        ("K2", "kakaopay_overseas_2026-0199_together2.pdf"),
        ("K3", "kakaopay_overseas_2026-0199_standard.pdf"),
    ],
}


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def extract(path: Path, destination: Path) -> int:
    parts = []
    with pdfplumber.open(path) as pdf:
        for index, page in enumerate(pdf.pages, start=1):
            parts.append(f"\n\n===PAGE {index}===\n" + (page.extract_text() or ""))
    destination.write_text("".join(parts), encoding="utf-8")
    return len(parts)


def run() -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    catalog: dict[str, list[dict]] = {}
    for insurer, entries in FILES.items():
        rows = []
        for prefix, filename in entries:
            pdf_path = RAW_DIR / filename
            if not pdf_path.exists():
                raise FileNotFoundError(f"raw PDF is missing: {pdf_path}")
            text_path = OUT_DIR / f"{pdf_path.stem}_full_text.txt"
            pages = extract(pdf_path, text_path)
            rows.append(
                {
                    "page_ref_prefix": prefix,
                    "pdf": filename,
                    "text": text_path.name,
                    "pages": pages,
                    "sha256": sha256_of(pdf_path),
                }
            )
            print(f"[{insurer}] {filename} -> {text_path.name} ({pages} pages)")
        catalog[insurer] = rows
    CATALOG.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"catalog written: {CATALOG}")
    return catalog


if __name__ == "__main__":
    run()
