"""외교부 국가·지역별 여행경보를 받아 data/travel_alerts.json으로 저장한다.

    python -m app.crawl_travel_alerts

공공데이터포털 인증키가 필요하다(무료). 발급 후 .env에 넣는다.

    DATA_GO_KR_SERVICE_KEY=...

보험료(crawl_premiums.py)와 같은 방식이다 — 런타임에 매번 외부 API를 부르지 않고, 받아둔
스냅샷을 저장소에 커밋해서 쓴다. 키가 없거나 API가 죽어도 앱은 그대로 돌고, 경보가
바뀌었을 때만 이 스크립트를 다시 돌린다.

받은 값을 가공하지 않는다. 국가명·단계·작성일을 원문 그대로 담고 출처와 수집일을 같이
남긴다 — 나중에 "이 숫자 어디서 났냐"를 되짚을 수 있어야 한다.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path

import httpx

API_URL = "http://apis.data.go.kr/1262000/TravelAlarmService2/getTravelAlarmList2"
SOURCE_NAME = "외교부 국가·지역별 여행경보 (공공데이터포털)"
SOURCE_URL = "https://www.data.go.kr/data/15076237/openapi.do"
OUTPUT = Path(__file__).resolve().parents[1] / "data" / "travel_alerts.json"

_PAGE_SIZE = 100
_MAX_PAGES = 30  # 국가 수를 크게 웃도는 상한 — 응답이 이상할 때 무한 루프를 막는다


def _service_key() -> str:
    key = os.getenv("DATA_GO_KR_SERVICE_KEY", "").strip()
    if not key:
        print(
            "DATA_GO_KR_SERVICE_KEY가 없습니다.\n"
            "공공데이터포털(data.go.kr)에서 '외교부_국가∙지역별 여행경보' 활용신청 후\n"
            "발급받은 키를 backend/.env에 넣어주세요.",
            file=sys.stderr,
        )
        raise SystemExit(1)
    return key


def _fetch_page(client: httpx.Client, key: str, page: int) -> tuple[list[dict], int]:
    res = client.get(API_URL, params={
        "serviceKey": key, "numOfRows": _PAGE_SIZE, "pageNo": page, "returnType": "JSON",
    }, timeout=20)
    res.raise_for_status()
    body = res.json()
    # 포털 응답은 서비스마다 감싸는 모양이 조금씩 다르다. 항목 배열과 총 건수만 찾아 쓴다.
    data = body.get("response", {}).get("body", body.get("body", body))
    items = data.get("items") or []
    if isinstance(items, dict):
        items = items.get("item") or []
    total = int(data.get("totalCount") or 0)
    return items, total


def _normalize(raw: dict) -> dict | None:
    """응답 한 건을 우리가 쓰는 모양으로 옮긴다. 단계를 못 읽으면 버린다 —
    단계가 이 데이터의 전부라, 없으면 아무 판단도 할 수 없다."""
    level = raw.get("alarmLvl") or raw.get("almLvl") or raw.get("level")
    try:
        level = int(str(level).strip())
    except (TypeError, ValueError):
        return None
    if level not in (1, 2, 3, 4):
        return None

    name = (raw.get("countryName") or raw.get("countryNm") or "").strip()
    if not name:
        return None

    return {
        "country_name": name,
        "country_en": (raw.get("countryEnName") or raw.get("countryEngNm") or "").strip() or None,
        "iso_code": (raw.get("isoCode") or raw.get("countryIsoAlp2") or "").strip() or None,
        "level": level,
        "region_type": (raw.get("regionType") or raw.get("dangMapDownloadUrl") and None or "") or None,
        "note": (raw.get("remark") or raw.get("alarmContent") or "").strip() or None,
        "issued_on": (raw.get("writngDe") or raw.get("createDate") or "").strip() or None,
    }


def crawl() -> dict:
    key = _service_key()
    collected: list[dict] = []
    with httpx.Client() as client:
        page = 1
        while page <= _MAX_PAGES:
            items, total = _fetch_page(client, key, page)
            if not items:
                break
            for raw in items:
                row = _normalize(raw)
                if row:
                    collected.append(row)
            if total and len(collected) >= total:
                break
            page += 1

    # 같은 나라가 여러 지역으로 나뉘어 오면 가장 높은 단계를 대표로 쓴다 — 낮은 쪽을
    # 대표로 삼으면 실제보다 안전해 보이게 된다.
    by_country: dict[str, dict] = {}
    for row in collected:
        prev = by_country.get(row["country_name"])
        if prev is None or row["level"] > prev["level"]:
            by_country[row["country_name"]] = row

    return {
        "source": SOURCE_NAME,
        "source_url": SOURCE_URL,
        "collected_at": date.today().isoformat(),
        "levels": {"1": "여행유의", "2": "여행자제", "3": "출국권고", "4": "여행금지"},
        "alerts": sorted(by_country.values(), key=lambda r: (-r["level"], r["country_name"])),
    }


def main() -> None:
    payload = crawl()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    counts: dict[int, int] = {}
    for row in payload["alerts"]:
        counts[row["level"]] = counts.get(row["level"], 0) + 1
    print(f"여행경보 {len(payload['alerts'])}개국 저장 → {OUTPUT}")
    for level in sorted(counts, reverse=True):
        print(f"  {level}단계({payload['levels'][str(level)]}): {counts[level]}개국")


if __name__ == "__main__":
    main()
