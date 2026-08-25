"""순위 가중치 분석(R)에 넘길 입력을 KB에서 CSV로 뽑는다.

R에서 SQLite를 직접 읽으려면 RSQLite 패키지가 있어야 하는데, 분석 환경마다 있다는
보장이 없다. 그래서 파이썬이 KB를 읽어 CSV로 떨어뜨리고, R은 CSV만 읽는다 — R 쪽
의존성이 tidyverse·jsonlite 둘로 줄고, 중간 산출물이 파일로 남아 무엇을 넣어 무엇이
나왔는지 나중에 그대로 되짚을 수 있다.

    python analysis/export_ranking_inputs.py
"""
from __future__ import annotations

import csv
import pathlib
import sqlite3
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "backend" / "data" / "app.db"
OUT_DIR = ROOT / "analysis" / "data"

# backend/app/services/insurer_tiers.py의 TIER_PLAN_NAMES와 같은 대응을 쓴다.
# 여기서 어긋나면 분석이 보는 등급과 서비스가 보는 등급이 달라진다.
TIER_PLAN_NAMES = {
    "KAKAOPAY": ["라이트", "베이직", "플러스"],
    "HYUNDAI": ["실속형", "표준형", "고급형"],
    "KB": ["실속형", "표준형", "고급형"],
    "SAMSUNG": ["실속플랜", "표준플랜", "고급플랜"],
    "DB": ["실속형", "표준형", "고급형"],
    "MERITZ": ["실속플랜", "추천플랜", "보장이큰플랜"],
    # 신한EZ손보는 2등급이라 고급 자리가 비어 있다(_tier_of가 None을 돌려줘 그 행은 빠진다).
    "SHINHAN": ["실속케어", "안심케어", None],
}


def _tier_of(insurer_code: str, plan_name: str) -> int | None:
    names = TIER_PLAN_NAMES.get(insurer_code)
    if not names or plan_name not in names:
        return None
    return names.index(plan_name)


def _amount_to_number(value_text: str | None) -> float | None:
    """보장금액 칸을 숫자로. 숫자가 아니면(예: "-", "미보장") None."""
    if value_text is None:
        return None
    text = value_text.replace(",", "").strip()
    if not text or text in {"-", "미보장", "없음"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def export_coverage_amounts(conn: sqlite3.Connection) -> int:
    rows = conn.execute(
        """
        SELECT i.code, m.plan_name, m.category, m.metric_label, m.value_text, m.unit,
               m.category_order, m.sort_order
        FROM insurer_comparison_metric m
        JOIN insurer i ON i.insurer_id = m.insurer_id
        ORDER BY m.category_order, m.sort_order, i.code, m.plan_name
        """
    ).fetchall()

    out = OUT_DIR / "coverage_amounts.csv"
    written = 0
    with out.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow([
            "insurer_code", "plan_name", "plan_tier", "category", "metric_label",
            "amount", "unit", "category_order", "sort_order",
        ])
        for code, plan_name, category, label, value_text, unit, cat_order, sort_order in rows:
            tier = _tier_of(code, plan_name)
            amount = _amount_to_number(value_text)
            if tier is None or amount is None:
                # 등급 대응이 없거나 금액이 아닌 칸은 분석에 넣지 않는다. 억지로 0으로
                # 채우면 "보장 안 됨"과 "자료 없음"이 같은 값이 돼 버린다.
                continue
            writer.writerow([code, plan_name, tier, category, label, amount, unit, cat_order, sort_order])
            written += 1
    return written


def export_premiums(conn: sqlite3.Connection) -> int:
    rows = conn.execute(
        """
        SELECT i.code, p.plan_name, p.sex, p.age, p.premium, p.period_days
        FROM insurer_premium p
        JOIN insurer i ON i.insurer_id = p.insurer_id
        ORDER BY i.code, p.plan_name, p.sex, p.age
        """
    ).fetchall()

    out = OUT_DIR / "premiums.csv"
    written = 0
    with out.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["insurer_code", "plan_name", "plan_tier", "sex", "age", "premium", "period_days"])
        for code, plan_name, sex, age, premium, period_days in rows:
            tier = _tier_of(code, plan_name)
            if tier is None:
                continue
            writer.writerow([code, plan_name, tier, sex, age, premium, period_days])
            written += 1
    return written


def main() -> int:
    if not DB_PATH.exists():
        print(f"KB를 찾지 못했습니다: {DB_PATH}", file=sys.stderr)
        return 1
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True)
    try:
        amounts = export_coverage_amounts(conn)
        premiums = export_premiums(conn)
    finally:
        conn.close()
    print(f"coverage_amounts.csv {amounts}행, premiums.csv {premiums}행을 {OUT_DIR}에 썼습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
