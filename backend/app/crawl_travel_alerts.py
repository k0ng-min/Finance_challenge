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

import html
import json
import os
import sys
from datetime import date
from pathlib import Path

import httpx
from dotenv import load_dotenv

# 이 스크립트는 앱을 거치지 않고 단독 실행되므로 .env를 직접 읽어야 한다 —
# 없으면 위 docstring대로 .env에 키를 넣어도 os.getenv가 계속 빈 값을 본다.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

API_URL ="http://apis.data.go.kr/1262000/TravelAlarmService2/getTravelAlarmList2"
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
    # 실제 응답은 snake_case다(alarm_lvl, country_nm …). 포털 문서와 표기가 다른 경우가
    # 있어 camelCase도 같이 본다 — 어느 쪽이 와도 읽히게.
    level = raw.get("alarm_lvl") or raw.get("alarmLvl") or raw.get("level")
    try:
        level = int(str(level).strip())
    except (TypeError, ValueError):
        return None
    if level not in (1, 2, 3, 4):
        return None

    name = html.unescape(
        raw.get("country_nm") or raw.get("countryName") or raw.get("countryNm") or ""
    ).strip()
    if not name:
        return None

    def _text(*keys: str) -> str | None:
        for key in keys:
            value = raw.get(key)
            if value and str(value).strip():
                # 응답에 &middot; &bull; &ccedil; 같은 HTML 엔티티가 섞여 온다. 그대로 두면
                # 화면에 "로스토프&middot;벨고로드"로 보인다(React가 이스케이프하므로).
                return html.unescape(str(value)).strip()
        return None

    return {
        "country_name": name,
        "country_en": _text("country_eng_nm", "countryEnName", "countryEngNm"),
        "iso_code": _text("country_iso_alp2", "isoCode", "countryIsoAlp2"),
        "level": level,
        "region_type": _text("region_ty", "regionType"),
        "note": _text("remark", "alarmContent"),
        "issued_on": _text("written_dt", "writngDe", "createDate"),
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

    # 나라별로 접지 않고 받은 행을 그대로 둔다.
    #
    # 처음에는 "같은 나라가 여러 지역으로 나뉘어 오면 가장 높은 단계를 대표로 쓴다"였다.
    # 실제 데이터를 받아보니 그 규칙으로는 일본이 3단계(후쿠시마 원전 30km), 필리핀이
    # 4단계(민다나오 일부)가 되어 도쿄·세부 여행자에게 출국권고가 뜬다. 3·4단계 72개국
    # 중 52개국이 일부 지역 경보라 예외가 아니라 다수다.
    #
    # 어느 행이 그 나라의 기본 단계인지는 서비스(services/travel_alert.py)가 판단한다.
    # 여기서 접어버리면 지역 정보가 사라져서 판단할 재료 자체가 없어진다.
    return {
        "source": SOURCE_NAME,
        "source_url": SOURCE_URL,
        "collected_at": date.today().isoformat(),
        "levels": {"1": "여행유의", "2": "여행자제", "3": "출국권고", "4": "여행금지"},
        "alerts": sorted(collected, key=lambda r: (r["country_name"], -r["level"])),
    }


def main() -> None:
    payload = crawl()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    counts: dict[int, int] = {}
    for row in payload["alerts"]:
        counts[row["level"]] = counts.get(row["level"], 0) + 1
    countries = {row["country_name"] for row in payload["alerts"]}
    print(f"여행경보 {len(payload['alerts'])}건 / {len(countries)}개국 저장 → {OUTPUT}")
    for level in sorted(counts, reverse=True):
        print(f"  {level}단계({payload['levels'][str(level)]}): {counts[level]}건")


if __name__ == "__main__":
    main()
