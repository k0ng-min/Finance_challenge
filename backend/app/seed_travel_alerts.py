"""data/travel_alerts.json을 travel_alert 테이블에 적재한다.

    python -m app.seed_travel_alerts

스냅샷 파일이 없으면(=아직 수집 전) 아무것도 하지 않고 정상 종료한다. 경보 자료가 없다고
앱이 못 뜰 이유는 없고, 없는 데이터를 지어내지도 않는다 — 그 경우 경보 배지와 면책 안내만
나타나지 않는다.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.models.kb import TravelAlert

Base.metadata.create_all(bind=engine)

SNAPSHOT = Path(__file__).resolve().parents[1] / "data" / "travel_alerts.json"


def seed(db: Session, path: Path = SNAPSHOT) -> int:
    if not path.exists():
        return 0

    payload = json.loads(path.read_text(encoding="utf-8"))
    alerts = payload.get("alerts") or []
    if not alerts:
        return 0

    collected = payload.get("collected_at")
    collected_on = date.fromisoformat(collected) if collected else None

    # 통째로 갈아끼운다. 경보는 해제되기도 하므로, 남겨두면 이미 풀린 경보가 계속 뜬다.
    db.query(TravelAlert).delete()
    for row in alerts:
        db.add(TravelAlert(
            country_name=row["country_name"],
            country_en=row.get("country_en"),
            iso_code=row.get("iso_code"),
            level=int(row["level"]),
            region_type=row.get("region_type"),
            note=row.get("note"),
            issued_on=row.get("issued_on"),
            source=payload.get("source"),
            source_url=payload.get("source_url"),
            collected_at=collected_on,
        ))
    return len(alerts)


def main() -> None:
    db = SessionLocal()
    try:
        count = seed(db)
        db.commit()
        if count:
            print(f"travel_alert {count}개국 적재 완료")
        else:
            print(
                "여행경보 스냅샷이 없어 건너뜁니다. "
                "python -m app.crawl_travel_alerts 로 먼저 수집하세요(인증키 필요)."
            )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
