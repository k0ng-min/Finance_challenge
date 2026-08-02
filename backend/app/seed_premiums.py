"""crawl_premiums.py가 만든 premiums.json을 insurer_premium 테이블에 적재한다.

    python -m app.crawl_premiums     # 먼저 수집
    python -m app.seed_premiums      # 그 다음 적재

같은 (보험사, 성별, 나이) 조합이 이미 있으면 덮어쓴다 — 비교공시 보험료는 갱신되는
값이라 재수집 후 다시 돌리면 최신 값으로 맞춰진다.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

from app.database import Base, SessionLocal, engine
from app import models  # noqa: F401  (모델 등록)
from app.models.kb import Insurer, InsurerPremium

DEFAULT_PATH = Path(__file__).resolve().parents[1] / "data" / "premiums.json"


def run(path: Path = DEFAULT_PATH) -> None:
    if not path.exists():
        raise SystemExit(f"{path} 가 없습니다. 먼저 `python -m app.crawl_premiums`를 실행하세요.")

    Base.metadata.create_all(bind=engine)  # insurer_premium 테이블이 없으면 만든다

    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload["records"]
    collected_at = date.fromisoformat(payload["collected_at"])
    basis = payload["premium_basis"]
    source = payload["source"]
    source_url = payload["source_url"]

    db = SessionLocal()
    try:
        code_to_id = {i.code: i.insurer_id for i in db.query(Insurer).all()}
        existing = {
            (p.insurer_id, p.sex, p.age): p
            for p in db.query(InsurerPremium).all()
        }

        inserted = updated = skipped = 0
        for rec in records:
            insurer_id = code_to_id.get(rec["insurer_code"])
            if insurer_id is None:
                # DB에 없는 보험사는 건너뛴다(약관을 분석해 둔 6개사만 다룬다).
                skipped += 1
                continue
            key = (insurer_id, rec["sex"], rec["age"])
            row = existing.get(key)
            if row is None:
                row = InsurerPremium(insurer_id=insurer_id, sex=rec["sex"], age=rec["age"])
                db.add(row)
                existing[key] = row
                inserted += 1
            else:
                updated += 1
            row.premium = rec["premium"]
            row.product_name = rec.get("product_name")
            row.source_product_code = rec.get("prdt_cd")
            row.age_range = rec.get("age_range")
            row.basis = basis
            row.source = source
            row.source_url = source_url
            row.collected_at = collected_at

        db.commit()
        print(f"보험료 적재 완료 — 신규 {inserted}건, 갱신 {updated}건, 건너뜀 {skipped}건")
    finally:
        db.close()


if __name__ == "__main__":
    run(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PATH)
