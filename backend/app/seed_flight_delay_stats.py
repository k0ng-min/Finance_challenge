"""data/flight_delay_stats.json을 flight_delay_stat 테이블에 적재한다.

    python -m app.seed_flight_delay_stats

스냅샷 파일이 없으면 아무것도 하지 않고 정상 종료한다(TravelAlert와 같은 관례) —
없는 데이터를 지어내지 않고, 이 자료가 없다고 앱이 못 뜨지도 않는다.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.models.kb import FlightDelayStat

Base.metadata.create_all(bind=engine)

SNAPSHOT = Path(__file__).resolve().parents[1] / "data" / "flight_delay_stats.json"


def seed(db: Session, path: Path = SNAPSHOT) -> int:
    if not path.exists():
        return 0

    payload = json.loads(path.read_text(encoding="utf-8"))
    collected = payload.get("collected_at")
    collected_on = date.fromisoformat(collected) if collected else None

    db.query(FlightDelayStat).delete()

    inserted = 0
    for row in payload.get("overall_by_kind_direction") or []:
        db.add(FlightDelayStat(
            year=None, kind=row["kind"], direction=row["direction"],
            delayed_flights=row["delayed_flights"], total_delay_minutes=row["total_delay_minutes"],
            avg_delay_minutes=row.get("avg_delay_minutes"), passengers_affected=row.get("passengers_affected"),
            source=payload.get("source"), source_url=payload.get("source_url"),
            scope_note=payload.get("scope_note"), collected_at=collected_on,
        ))
        inserted += 1
    for row in payload.get("yearly") or []:
        db.add(FlightDelayStat(
            year=row["year"], kind=row["kind"], direction=row["direction"],
            delayed_flights=row["delayed_flights"], total_delay_minutes=row["total_delay_minutes"],
            avg_delay_minutes=row.get("avg_delay_minutes"), passengers_affected=row.get("passengers_affected"),
            source=payload.get("source"), source_url=payload.get("source_url"),
            scope_note=payload.get("scope_note"), collected_at=collected_on,
        ))
        inserted += 1
    return inserted


def main() -> None:
    db = SessionLocal()
    try:
        count = seed(db)
        db.commit()
        if count:
            print(f"flight_delay_stat {count}건 시드 완료.")
        else:
            print("스냅샷이 없어 건너뜁니다.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
