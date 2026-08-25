"""data/nonpayment_rates.json을 nonpayment_rate 테이블에 적재한다.

    python -m app.seed_nonpayment_rates

TravelAlert·seed_premiums.py와 같은 관례 — 스냅샷이 없으면 아무것도 하지 않고
정상 종료한다. 회사명을 우리 insurer.code로 매칭하되, 매칭 안 되는 행(업계평균,
6개사 밖 손보사)도 insurer_id NULL로 그대로 저장한다 — 조용히 버리지 않는다.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.models.kb import Insurer, NonpaymentRate

Base.metadata.create_all(bind=engine)

SNAPSHOT = Path(__file__).resolve().parents[1] / "data" / "nonpayment_rates.json"


def seed(db: Session, path: Path = SNAPSHOT) -> int:
    if not path.exists():
        return 0

    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("rows") or []
    if not rows:
        return 0

    collected = payload.get("collected_at")
    collected_on = date.fromisoformat(collected) if collected else None
    period = payload["period"]

    insurers_by_code = {i.code: i for i in db.query(Insurer).all()}

    db.query(NonpaymentRate).filter(NonpaymentRate.period == period).delete()

    for row in rows:
        insurer = insurers_by_code.get(row.get("insurer_code")) if row.get("insurer_code") else None
        db.add(NonpaymentRate(
            insurer_id=insurer.insurer_id if insurer else None,
            company_name=row["company_name"],
            period=period,
            claim_count=row["claim_count"],
            paid_count=row["paid_count"],
            unpaid_count=row["unpaid_count"],
            unpaid_rate=row["unpaid_rate"],
            claim_contract_count=row.get("claim_contract_count"),
            post_claim_cancel_count=row.get("post_claim_cancel_count"),
            post_claim_cancel_rate=row.get("post_claim_cancel_rate"),
            source=payload.get("source"), source_url=payload.get("source_url"),
            scope_note=payload.get("scope_note"), collected_at=collected_on,
        ))
    return len(rows)


def main() -> None:
    db = SessionLocal()
    try:
        count = seed(db)
        db.commit()
        if count:
            print(f"nonpayment_rate {count}건 시드 완료.")
        else:
            print("스냅샷이 없어 건너뜁니다.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
