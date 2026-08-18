"""보험사 다이렉트 사이트에서 사용자가 직접 조회한 실제 보험료를 적재한다.

2026-08-19 이전에는 보험다모아 비교공시(crawl_premiums.py → seed_premiums.py)를 썼다.
그건 "표준조건" 한 값이라 보험사가 실제로 파는 여러 등급(플랜)의 가격 차이를 보여주지
못했다. 이 스크립트는 그걸 완전히 대체한다 — 사용자가 각 사 다이렉트 계산기에서
나이·성별·등급별로 직접 조회한 실제 값(backend/data/source_files/insurer_premiums_*.xlsx)을
그대로 적재한다.

시트 구조가 보험사마다 다르다(카카오는 나이·성별·등급이 한 행씩인 세로형, 나머지는
등급 3개가 열로 나란한 가로형) — _rows_from_sheet()가 그 차이를 흡수해서 전부
(나이, 성별, 등급, 보험료) 튜플로 통일한다.

아직 실제 가격을 조회하지 못한 보험사(예: DB손해보험·메리츠화재)는 시트 자체가 없다.
그 보험사는 이 스크립트를 몇 번을 돌려도 그냥 조용히 건너뛴다 — 나중에 같은 형식의
시트를 엑셀에 추가해서 다시 돌리기만 하면 코드 변경 없이 채워진다.

Run from ``backend``::

    python -m app.seed_premiums_actual
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import openpyxl
from sqlalchemy import text

from app.database import Base, SessionLocal, engine
from app import models  # noqa: F401  (모델 등록)
from app.models.kb import Insurer, InsurerPremium


def _ensure_new_schema() -> None:
    """예전 스키마의 insurer_premium은 (insurer_id, sex, age)에 UNIQUE가 걸려 있어
    등급별로 여러 행을 못 넣는다. SQLite는 ALTER로 UNIQUE 제약을 못 바꾸므로,
    plan_name이 없는 옛 테이블이면 통째로 지우고 새 모델 정의로 다시 만든다 —
    사용자가 "예전 값 싹 다 지우고 바꿔달라"고 요청한 부분이라 데이터 손실 우려가 없다."""
    with engine.connect() as conn:
        existing = {row[1] for row in conn.execute(text("PRAGMA table_info(insurer_premium)"))}
        if existing and "plan_name" not in existing:
            conn.execute(text("DROP TABLE insurer_premium"))
        conn.commit()
    Base.metadata.create_all(bind=engine)

DEFAULT_PATH = Path(__file__).resolve().parents[1] / "data" / "source_files" / "insurer_premiums_2026-08.xlsx"

_SEX_MAP = {"남": "M", "여": "F"}

#: 시트 이름 -> (보험사 코드, 세로형 여부, 화면에 대표로 보여줄 표준 등급명)
_SHEET_CONFIG: dict[str, tuple[str, bool, str]] = {
    "카카오": ("KAKAOPAY", True, "베이직"),
    "현대해상": ("HYUNDAI", False, "표준"),
    "kb": ("KB", False, "표준형"),
    "삼성": ("SAMSUNG", False, "표준플랜"),
}

#: 조회 조건 — 보험사마다 산출 전제가 달라 각각 남긴다(근거 없이 숫자만 보여주지 않는다).
_BASIS: dict[str, str] = {
    "KAKAOPAY": "다이렉트 사이트 조회, 3일 보험료를 3으로 나눈 1일 환산가, 단독가입 기준",
    "HYUNDAI": "다이렉트 사이트 조회, 1일(24시간) 기준, 단독가입",
    "KB": "다이렉트 사이트 조회, 1일(24시간) 기준, 단독가입(만19세~만90세 가입 가능)",
    "SAMSUNG": "다이렉트 사이트 조회, 1일(24시간) 기준, 단독가입(항공지연 지수형 특약 2종 기본 포함)",
}
_SOURCE = "보험사 다이렉트 홈페이지 보험료 계산기(직접 조회)"
_COLLECTED_AT = date(2026, 8, 17)


def _find_header_row(rows: list[tuple]) -> int:
    """'성별' 열이 있는 행을 헤더로 본다 — 시트마다 그 위에 제목/주의문구 행 수가 다르다."""
    for i, row in enumerate(rows):
        if len(row) > 1 and row[1] == "성별":
            return i
    raise ValueError("헤더 행('성별' 열)을 찾지 못했습니다.")


def _rows_from_sheet(sheet_name: str, rows: list[tuple], vertical: bool) -> list[tuple[int, str, str, int]]:
    """시트 데이터를 (나이, 성별(M/F), 등급명, 보험료) 튜플 목록으로 통일한다."""
    header_idx = _find_header_row(rows)
    header = rows[header_idx]
    data_rows = rows[header_idx + 1:]
    out: list[tuple[int, str, str, int]] = []

    if vertical:
        # 카카오: 나이, 성별, 가입플랜, 3일보험료, 1일환산보험료 — 한 행에 등급 하나.
        for row in data_rows:
            if not row or not isinstance(row[0], (int, float)) or row[1] not in _SEX_MAP:
                continue
            age, sex_raw, plan_name, _three_day, one_day = row[0], row[1], row[2], row[3], row[4]
            if one_day is None:
                continue
            out.append((int(age), _SEX_MAP[sex_raw], plan_name, int(one_day)))
        return out

    # 현대해상/kb/삼성: 나이, 성별, 등급1, 등급2, 등급3[, 비고] — 등급이 열로 나란함.
    plan_names = [str(h).split("(")[0] for h in header[2:] if h and str(h) != "비고"]
    for row in data_rows:
        if not row or not isinstance(row[0], (int, float)) or row[1] not in _SEX_MAP:
            continue
        age, sex_raw = row[0], row[1]
        for col_offset, plan_name in enumerate(plan_names):
            premium = row[2 + col_offset]
            if premium is None:
                continue  # 가입연령 범위 밖 등 — 이 나이·등급은 조회 자체가 안 됨
            out.append((int(age), _SEX_MAP[sex_raw], plan_name, int(premium)))
    return out


def run(path: Path = DEFAULT_PATH) -> dict[str, int]:
    if not path.exists():
        raise SystemExit(f"{path} 가 없습니다. 실제 보험료 엑셀을 이 경로에 둔 뒤 다시 실행하세요.")

    _ensure_new_schema()

    wb = openpyxl.load_workbook(path, data_only=True)
    db = SessionLocal()
    try:
        code_to_id = {i.code: i.insurer_id for i in db.query(Insurer).all()}
        counts: dict[str, int] = {}

        for sheet_name, (insurer_code, vertical, standard_plan) in _SHEET_CONFIG.items():
            if sheet_name not in wb.sheetnames:
                continue
            insurer_id = code_to_id.get(insurer_code)
            if insurer_id is None:
                continue

            # 이 보험사분은 통째로 새로 채운다(등급이 늘거나 줄 수 있어 부분 갱신보다
            # 안전하다) — 사용자가 "원래 있던 가격 싹 다 지우고 이걸로 바꿔달라"고
            # 명시적으로 요청한 부분이다.
            db.query(InsurerPremium).filter(InsurerPremium.insurer_id == insurer_id).delete()

            rows = list(wb[sheet_name].iter_rows(values_only=True))
            parsed = _rows_from_sheet(sheet_name, rows, vertical)
            for age, sex, plan_name, premium in parsed:
                db.add(InsurerPremium(
                    insurer_id=insurer_id, sex=sex, age=age, plan_name=plan_name,
                    is_standard_tier=(plan_name == standard_plan),
                    premium=premium, period_days=1,
                    product_name=plan_name,
                    age_range=None,
                    basis=_BASIS[insurer_code], source=_SOURCE, source_url=None,
                    collected_at=_COLLECTED_AT,
                ))
            counts[insurer_code] = len(parsed)

        db.commit()
        for code, n in counts.items():
            print(f"{code}: {n}건 적재")
        all_codes = {i.code for i in db.query(Insurer).all()}
        missing = sorted(all_codes - set(counts))
        if missing:
            print(f"이 엑셀에 시트가 없어 건너뜀(아직 가격 미확보): {', '.join(missing)}")
        return counts
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(0 if run(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PATH) else 1)
